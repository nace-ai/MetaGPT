import concurrent
import sys
import io
import traceback
from typing import List, Optional, Dict

import base64

from tenacity import retry, stop_after_attempt, wait_fixed

from metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.template.operator_an import *
from metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.template.op_prompt import *
from metagpt.actions.action_node import ActionNode
from metagpt.llm import LLM
import asyncio
import logging
import json
import re

from metagpt.provider.llm_provider_registry import create_llm_instance
from metagpt.configs.llm_config import LLMConfig
from PyPDF2 import PdfReader, PdfWriter

logger = logging.getLogger(__name__)

class Operator:
    def __init__(self, llm: LLM, name: str):
        self.name = name
        self.llm = llm

    def __call__(self, *args, **kwargs):
        raise NotImplementedError

    async def _fill_node(self, op_class, prompt, mode=None, **extra_kwargs):
        fill_kwargs = {"context": prompt, "llm": self.llm}
        if mode:
            fill_kwargs["mode"] = mode
        fill_kwargs.update(extra_kwargs)
        node = await ActionNode.from_pydantic(op_class).fill(**fill_kwargs)
        return node.instruct_content.model_dump()


class Custom(Operator):
    def __init__(self, llm: LLM, name: str = "Custom"):
        super().__init__(llm, name)

    async def __call__(self, input, instruction):
        prompt = instruction + input
        response = await self._fill_node(GenerateOp, prompt, mode="single_fill")
        return response

def run_code(code):
    try:
        # Create a new global namespace
        global_namespace = {}

        disallowed_imports = [
            "os", "sys", "subprocess", "multiprocessing",
            "matplotlib", "seaborn", "plotly", "bokeh", "ggplot",
            "pylab", "tkinter", "PyQt5", "wx", "pyglet"
        ]

        # Check for prohibited imports
        for lib in disallowed_imports:
            if f"import {lib}" in code or f"from {lib}" in code:
                logger.info("Detected prohibited import: %s", lib)
                return "Error", f"Prohibited import: {lib} and graphing functionalities"

        # Use exec to execute the code
        exec(code, global_namespace)
        # Assume the code defines a function named 'solve'
        if 'solve' in global_namespace and callable(global_namespace['solve']):
            result = global_namespace['solve']()
            return "Success", str(result)
        else:
            return "Error", "Function 'solve' not found"
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb_str = traceback.format_exception(exc_type, exc_value, exc_traceback)
        return "Error", f"Execution error: {str(e)}\n{''.join(tb_str)}"
    

class Programmer(Operator):
    def __init__(self, llm: LLM, name: str = "Programmer"):
        super().__init__(llm, name)

    async def exec_code(self, code, timeout=30):
        """
        Asynchronously execute code and return an error if timeout occurs.
        """
        loop = asyncio.get_running_loop()
        with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
            try:
                # Submit run_code task to the process pool
                future = loop.run_in_executor(executor, run_code, code)
                # Wait for the task to complete or timeout
                result = await asyncio.wait_for(future, timeout=timeout)
                return result
            except asyncio.TimeoutError:
                # Timeout, attempt to shut down the process pool
                executor.shutdown(wait=False, cancel_futures=True)
                return "Error", "Code execution timed out"
            except Exception as e:
                return "Error", f"Unknown error: {str(e)}"

    async def code_generate(self, problem, analysis, feedback, mode):
        """
        Asynchronous method to generate code.
        """
        prompt = PYTHON_CODE_VERIFIER_PROMPT.format(
            problem=problem,
            analysis=analysis,
            feedback=feedback
        )
        response = await self._fill_node(CodeGenerateOp, prompt, mode, function_name="solve")
        return response

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def __call__(self, problem: str, analysis: str = "None"):
        """
        Call method, generate code and execute, retry up to 3 times.
        """
        code = None
        output = None
        feedback = ""
        for i in range(3):
            code_response = await self.code_generate(problem, analysis, feedback, mode="code_fill")
            code = code_response.get("code")
            if not code:
                return {"code": code, "output": "No code generated"}
            status, output = await self.exec_code(code)
            if status == "Success":
                return {"code": code, "output": output}
            else:
                print(f"Execution error on attempt {i + 1}, error message: {output}")
                feedback = (
                    f"\nThe result of the error from the code you wrote in the previous round:\n"
                    f"Code: {code}\n\nStatus: {status}, {output}"
                )
        return {"code": code, "output": output}


class ScEnsemble(Operator):
    """
    Paper: Self-Consistency Improves Chain of Thought Reasoning in Language Models
    Link: https://arxiv.org/abs/2203.11171
    Paper: Universal Self-Consistency for Large Language Model Generation
    Link: https://arxiv.org/abs/2311.17311
    """

    def __init__(self, llm: LLM, name: str = "ScEnsemble"):
        super().__init__(llm, name)

    async def __call__(self, solutions: List[str], problem: str):
        answer_mapping = {}
        solution_text = ""
        for index, solution in enumerate(solutions):
            answer_mapping[chr(65 + index)] = index
            solution_text += f"{chr(65 + index)}: \n{str(solution)}\n\n\n"

        prompt = SC_ENSEMBLE_PROMPT.format(problem=problem, solutions=solution_text)
        response = await self._fill_node(ScEnsembleOp, prompt, mode="xml_fill")

        answer = response.get("solution_letter", "")
        answer = answer.strip().upper()

        return {"response": solutions[answer_mapping[answer]]}
    
class DocumentInlining(Operator):
    def __init__(self, llm: LLM, name: str = "DocumentInlining"):
        super().__init__(llm, name)
    
    async def __call__(self, instruction: str, document_bytes: Optional[bytes] = None):
        
        image_url_str = None
        if document_bytes:
            # encode document file bytes to base64
            document_base64 = base64.b64encode(document_bytes).decode("utf-8")
            image_url_str = f"data:application/pdf;base64,{document_base64}#transform=inline"
        
        fill_kwargs = {
            "context": instruction,
            "images": image_url_str,
            "llm": self.llm,
            "mode": "single_fill"
        }
        # needs to be modified to use xml_fill mode
        node = await ActionNode.from_pydantic(GenerateOp).fill(**fill_kwargs)
        return node.instruct_content.model_dump()
    
class PDFSummary(Operator):
    def __init__(self, llm: LLM, name: str = "PDFSummary"):
        super().__init__(llm, name)
    
    def __call__(self, pdf_file_path: str):
        pdf_reader = PdfReader(pdf_file_path)
        num_pages = len(pdf_reader.pages)
        
        return {
            "num_pages": num_pages
        }
        
    
class PDFPageExtraction(Operator):
    def __init__(self, llm: LLM, name: str = "PDFPageExtraction"):
        super().__init__(llm, name)
    
    def __call__(self, pdf_file_path: str, page_numbers: List[int]) -> bytes:
        pdf_reader = PdfReader(pdf_file_path)
        pdf_writer = PdfWriter()
        for page_number in page_numbers:
            pdf_writer.add_page(pdf_reader.pages[page_number-1])
            
        pdf_bytes = io.BytesIO()
        pdf_writer.write(pdf_bytes)
        
        return pdf_bytes.getvalue()

def extract_json_string(text: str) -> str:
            last_index = text.rfind("```json")
            text = text[last_index:]
            pattern = r'```json\s*\n(.*?)\n```'
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1)
            return None

def extract_json_object(text: str) -> Optional[Dict]:
    json_string = extract_json_string(text)
    if json_string:
        try:
            return json.loads(json_string)
        except json.JSONDecodeError:
            return None
    return None

class JSONExtraction(Operator):
    def __init__(self, llm: LLM, name: str = "PDFPageExtraction"):
        super().__init__(llm, name)
    
    def __call__(self, response: str) -> Optional[Dict]:
        return extract_json_object(response)
        
    
class ReceiptRecognitionResultFormatting(Operator):
    def __init__(self, llm: LLM, name: str = "ReceiptRecognitionResultFormat"):
        super().__init__(llm, name)
    
    async def __call__(self, recognition_result: Dict) -> Dict:
        prompt = RECEIPT_RECOGNITION_RESULT_FORMATTING_PROMPT.replace("{{recognition_result}}", json.dumps(recognition_result, indent=4))
        response = await self._fill_node(GenerateOp, prompt, mode="single_fill")
        reformatted_result = extract_json_object(response["response"])
        return reformatted_result

class SummarizeLLMConversation(Operator):
    def __init__(self, llm: LLM, name: str = "SummarizeLLMConversation"):
        super().__init__(llm, name)
    
    async def __call__(self, conversations: List[List[Dict]]) -> List[Dict]:
        summaries = []
        for conversation in conversations:
            prompt = CONVERSATION_SUMMARIZATION_PROMPT.replace("{{conversation}}", json.dumps(conversation, indent=4))
            response = await self._fill_node(GenerateOp, prompt, mode="single_fill")
            summary = extract_json_object(response["response"])
            summaries.append(summary)
        return summaries   
    
# if __name__ == "__main__":
    # test document inlining operator
    # llm_config = LLMConfig(**{
    #     "api_type": "fireworks",
    #     "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
    #     "base_url": "https://api.fireworks.ai/inference/v1",
    #     "api_key": "66HLNg1EPQOKgHocAYi2xaBQT8Dig7yVDbCQNlFPd7EO0W0u"
    # })
    # llm = create_llm_instance(llm_config)
    # document_inlining_op = DocumentInliningOp(llm)
    # document_path = "/Users/zhengwang/Documents/projects/MetaGPT/metagpt/receipt_recognition/Dominic_Miceli_R00G6o7yOemJ_2023_09_26.pdf"
    # instruction = "Please extract the text from this document"
    # result = asyncio.run(document_inlining_op(document_path, instruction))
    # print(result)
    
    # test PDF page extraction operator
    # pdf_page_extraction_op = PDFPageExtractionOp()
    # pdf_path = "/Users/zhengwang/Documents/projects/MetaGPT/metagpt/receipt_recognition/Dominic_Miceli_R00G6o7yOemJ_2023_09_26.pdf"
    # page_numbers = [0, 1]
    # pdf_bytes = pdf_page_extraction_op(pdf_path, page_numbers)
    # with open("output.pdf", "wb") as f:
    #     f.write(pdf_bytes)
    
    # test receipt recognition result formatting operator
    # ...