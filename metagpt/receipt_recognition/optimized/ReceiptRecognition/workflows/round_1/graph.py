from typing import Literal
import metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.template.operator as operator
import metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.round_1.prompt as prompt_custom
from metagpt.provider.llm_provider_registry import create_llm_instance
from metagpt.utils.cost_manager import CostManager


DatasetType = Literal["ReceiptRecognition"]

class Workflow:
    def __init__(
        self,
        name: str,
        llm_config,
        dataset: DatasetType,
    ) -> None:
        self.name = name
        self.llm = create_llm_instance(llm_config)
        self.llm.cost_manager = CostManager()
        self.document_inlining = operator.DocumentInlining(self.llm)
        self.pdf_summary = operator.PDFSummary(self.llm)
        self.pdf_page_extraction = operator.PDFPageExtraction(self.llm)
        self.receipt_recognition_result_formatting = operator.ReceiptRecognitionResultFormatting(self.llm)
        self.json_extraction = operator.JSONExtraction(self.llm)
        self.custom = operator.Custom(self.llm)

    async def __call__(self, file_path: str):
        """
        Implementation of the workflow
        """
        pdf_summary = self.pdf_summary(pdf_file_path=file_path)
        extracted_information_list = []
        extracted_receipt_page_numbers = []
        current_page_numbers = []
        for i in range(pdf_summary['num_pages']):
            page_number = i + 1
            pdf_bytes = self.pdf_page_extraction(pdf_file_path=file_path, page_numbers=[page_number])
            response = await self.document_inlining(instruction=prompt_custom.DOCUMENT_INFO_EXTRACTION, document_bytes=pdf_bytes)
            extracted_info = self.json_extraction(response['response'])
            extracted_information_list.append(extracted_info)
            
            # If current page belongs to a receipt, start checking if it is a continuation of the previous receipt
            if extracted_information_list[i]["is_receipt"]:
                if i > 0 and extracted_information_list[i - 1]["is_receipt"]:
                    previous_page_extracted_info = extracted_information_list[i - 1]["extracted_information"]
                else:
                    previous_page_extracted_info =  ""
                current_page_extracted_info = extracted_information_list[i]["extracted_information"]
                response = await self.custom(instruction=prompt_custom.RECEIPT_RECOGNITION_PROMPT, input=f"Previous page: {previous_page_extracted_info}\nCurrent page: {current_page_extracted_info}\n\n")
                recognition_result = self.json_extraction(response['response'])
                # If the current page is a continuation of the previous receipt, add the page number to the current receipt
                if recognition_result["is_single_receipt"]:
                    current_page_numbers.append(page_number)
                else:
                    extracted_receipt_page_numbers.append(current_page_numbers)
                    current_page_numbers = [page_number]
            else:
                if len(current_page_numbers) > 0:
                    extracted_receipt_page_numbers.append(current_page_numbers)
                    current_page_numbers = []
        # Add the last receipt to the list
        if len(current_page_numbers) > 0:
            extracted_receipt_page_numbers.append(current_page_numbers)
            
        # summarize the LLM conversations
        # summaries = 
        return extracted_receipt_page_numbers, self.llm.cost_manager.total_cost