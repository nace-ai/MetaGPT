from typing import Literal
import metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.template.operator as operator
import metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.round_2.prompt as prompt_custom
from metagpt.provider.llm_provider_registry import create_llm_instance
from metagpt.utils.cost_manager import CostManager

DatasetType = Literal["ReceiptRecognition"]

import re
from typing import List, Dict, Optional, Tuple

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
        
    def _clean_receipt_pages(self, raw_pages: List[List[int]]) -> List[List[int]]:
        """Clean the receipt pages by removing empty lists and sorting."""
        # Remove empty lists
        filtered_pages = [page_list for page_list in raw_pages if page_list]
        # Sort by the first page number in each list
        filtered_pages.sort(key=lambda x: x[0] if x else float('inf'))
        return filtered_pages
        
    async def _validate_receipt_page(self, page_number: int, extracted_info: Dict, file_path: str) -> Tuple[bool, Dict]:
        """Perform additional validation to determine if a page is truly a receipt."""
        pdf_bytes = self.pdf_page_extraction(pdf_file_path=file_path, page_numbers=[page_number])
        
        # Get more detailed metadata about the page
        validation_response = await self.document_inlining(
            instruction=prompt_custom.RECEIPT_VALIDATION_PROMPT, 
            document_bytes=pdf_bytes
        )
        
        validation_result = self.json_extraction(validation_response['response'])
        
        # Combine the original extraction with validation results
        confidence = validation_result.get("confidence_score", 0)
        is_receipt = validation_result.get("is_receipt", False)
        
        # Only consider high-confidence receipt detections
        return (is_receipt and confidence > 0.7), validation_result

    async def __call__(self, file_path: str):
        """Implementation of the optimized workflow"""
        pdf_summary = self.pdf_summary(pdf_file_path=file_path)
        extracted_information_list = []
        validation_results = []
        
        # First pass: Extract and validate all pages
        for i in range(pdf_summary['num_pages']):
            page_number = i + 1
            pdf_bytes = self.pdf_page_extraction(pdf_file_path=file_path, page_numbers=[page_number])
            
            # Extract basic information
            response = await self.document_inlining(
                instruction=prompt_custom.DOCUMENT_INFO_EXTRACTION, 
                document_bytes=pdf_bytes
            )
            extracted_info = self.json_extraction(response['response'])
            extracted_information_list.append(extracted_info)
            
            # Validate receipt pages with more detailed analysis
            if extracted_info.get("is_receipt", False):
                is_valid, validation_info = await self._validate_receipt_page(page_number, extracted_info, file_path)
                validation_results.append({
                    "page_number": page_number,
                    "is_valid_receipt": is_valid,
                    "metadata": validation_info
                })
            else:
                validation_results.append({
                    "page_number": page_number,
                    "is_valid_receipt": False,
                    "metadata": {}
                })
        
        # Second pass: Group receipt pages
        extracted_receipt_page_numbers = []
        current_page_numbers = []
        
        for i in range(pdf_summary['num_pages']):
            page_number = i + 1
            current_validation = next((v for v in validation_results if v["page_number"] == page_number), None)
            
            # Skip if not a valid receipt
            if not current_validation or not current_validation["is_valid_receipt"]:
                if len(current_page_numbers) > 0:
                    extracted_receipt_page_numbers.append(current_page_numbers)
                    current_page_numbers = []
                continue
                
            # Check if this is a continuation of previous receipt
            if i > 0 and len(current_page_numbers) > 0:
                previous_page_extracted_info = extracted_information_list[i - 1].get("extracted_information", "")
                current_page_extracted_info = extracted_information_list[i].get("extracted_information", "")
                
                continuation_check = await self.custom(
                    instruction=prompt_custom.RECEIPT_CONTINUATION_PROMPT,
                    input=f"Previous page number: {i}\nPrevious page content: {previous_page_extracted_info}\nCurrent page number: {page_number}\nCurrent page content: {current_page_extracted_info}\n\n"
                )
                
                continuation_result = self.json_extraction(continuation_check['response'])
                
                if continuation_result.get("is_single_receipt", False):
                    current_page_numbers.append(page_number)
                else:
                    extracted_receipt_page_numbers.append(current_page_numbers)
                    current_page_numbers = [page_number]
            else:
                # First valid receipt page
                current_page_numbers = [page_number]
        
        # Add the last receipt to the list if any
        if len(current_page_numbers) > 0:
            extracted_receipt_page_numbers.append(current_page_numbers)
        
        # Final verification of all detected receipt groups
        verification_results = []
        for page_group in extracted_receipt_page_numbers:
            if not page_group:  # Skip empty groups
                continue
                
            # Get sample data from the group for verification
            sample_page = page_group[0]
            pdf_bytes = self.pdf_page_extraction(pdf_file_path=file_path, page_numbers=[sample_page])
            
            verify_response = await self.document_inlining(
                instruction=prompt_custom.FINAL_VERIFICATION_PROMPT,
                document_bytes=pdf_bytes
            )
            
            verification = self.json_extraction(verify_response['response'])
            
            if verification.get("is_valid_receipt_group", True):
                verification_results.append(page_group)
                
        # Clean and finalize results
        final_result = self._clean_receipt_pages(verification_results)
            
        return final_result, self.llm.cost_manager.total_cost
