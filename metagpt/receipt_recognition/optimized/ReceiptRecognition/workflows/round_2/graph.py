from typing import Literal
import metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.template.operator as operator
import metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.round_2.prompt as prompt_custom
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
        self.sc_ensemble = operator.ScEnsemble(self.llm)

    async def __call__(self, file_path: str):
        """
        Implementation of the workflow
        """
        pdf_summary = self.pdf_summary(pdf_file_path=file_path)
        extracted_information_list = []
        extracted_receipt_page_numbers = []
        current_page_numbers = []
        
        # First pass: Extract information from each page
        for i in range(pdf_summary['num_pages']):
            page_number = i + 1
            pdf_bytes = self.pdf_page_extraction(pdf_file_path=file_path, page_numbers=[page_number])
            response = await self.document_inlining(instruction=prompt_custom.DOCUMENT_INFO_EXTRACTION, document_bytes=pdf_bytes)
            extracted_info = self.json_extraction(response['response'])
            extracted_information_list.append(extracted_info)
            
        # Second pass: Analyze continuity and group receipts
        for i in range(len(extracted_information_list)):
            page_number = i + 1
            
            # If current page is identified as a receipt
            if extracted_information_list[i]["is_receipt"]:
                current_page_extracted_info = extracted_information_list[i]["extracted_information"]
                
                # Check if this is a continuation of previous receipt
                if len(current_page_numbers) > 0 and i > 0 and extracted_information_list[i-1]["is_receipt"]:
                    previous_page_extracted_info = extracted_information_list[i-1]["extracted_information"]
                    
                    # Use more context for continuity check
                    response = await self.custom(
                        instruction=prompt_custom.RECEIPT_CONTINUITY_CHECK,
                        input=f"Previous page number: {i}\nPrevious page content: {previous_page_extracted_info}\nCurrent page number: {page_number}\nCurrent page content: {current_page_extracted_info}"
                    )
                    continuity_result = self.json_extraction(response['response'])
                    
                    # If continuation of previous receipt
                    if continuity_result["is_same_receipt"]:
                        current_page_numbers.append(page_number)
                    else:
                        # If not a continuation, finalize previous receipt group and start new one
                        if len(current_page_numbers) > 0:
                            extracted_receipt_page_numbers.append(current_page_numbers)
                        current_page_numbers = [page_number]
                else:
                    # Start a new receipt group
                    if len(current_page_numbers) > 0:
                        extracted_receipt_page_numbers.append(current_page_numbers)
                    current_page_numbers = [page_number]
            else:
                # If current page is not a receipt, finalize current receipt group if any
                if len(current_page_numbers) > 0:
                    extracted_receipt_page_numbers.append(current_page_numbers)
                    current_page_numbers = []
                    
        # Add the last receipt group if exists
        if len(current_page_numbers) > 0:
            extracted_receipt_page_numbers.append(current_page_numbers)
        
        # Verification step to ensure no receipt pages were missed
        receipt_verification_text = f"Extracted receipt pages: {extracted_receipt_page_numbers}\nPage info summary: "
        for i, info in enumerate(extracted_information_list):
            receipt_verification_text += f"Page {i+1}: {'Receipt' if info['is_receipt'] else 'Not Receipt'}, "
        
        response = await self.custom(
            instruction=prompt_custom.RECEIPT_VERIFICATION,
            input=receipt_verification_text
        )
        verification_result = self.json_extraction(response['response'])
        
        final_receipt_pages = verification_result.get("corrected_groupings", extracted_receipt_page_numbers)
        
        return final_receipt_pages, self.llm.cost_manager.total_cost
