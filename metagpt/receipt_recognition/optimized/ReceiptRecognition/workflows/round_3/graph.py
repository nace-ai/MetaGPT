from typing import Literal
import metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.template.operator as operator
import metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.round_3.prompt as prompt_custom
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
        
        # First pass: Extract information from all pages
        for i in range(pdf_summary['num_pages']):
            page_number = i + 1
            pdf_bytes = self.pdf_page_extraction(pdf_file_path=file_path, page_numbers=[page_number])
            response = await self.document_inlining(instruction=prompt_custom.DOCUMENT_INFO_EXTRACTION, document_bytes=pdf_bytes)
            extracted_info = self.json_extraction(response['response'])
            extracted_information_list.append({
                "page_number": page_number,
                "is_receipt": extracted_info.get("is_receipt", False),
                "extracted_information": extracted_info.get("extracted_information", ""),
                "receipt_indicators": extracted_info.get("receipt_indicators", [])
            })
        
        # Second pass: Group receipts considering page continuity
        receipt_page_groups = []
        current_group = []
        
        for i, page_info in enumerate(extracted_information_list):
            if page_info["is_receipt"]:
                # If this is the first receipt page or we need to check continuity
                if not current_group:
                    current_group.append(page_info["page_number"])
                else:
                    # Check if this page is a continuation of the previous receipt
                    prev_idx = i - 1
                    prev_info = extracted_information_list[prev_idx]
                    
                    continuity_input = f"Previous page content: {prev_info['extracted_information']}\n\nCurrent page content: {page_info['extracted_information']}\n\nPrevious page indicators: {prev_info['receipt_indicators']}\n\nCurrent page indicators: {page_info['receipt_indicators']}"
                    
                    response = await self.custom(instruction=prompt_custom.RECEIPT_CONTINUITY_PROMPT, input=continuity_input)
                    continuity_result = self.json_extraction(response['response'])
                    
                    if continuity_result.get("is_continuation", False):
                        current_group.append(page_info["page_number"])
                    else:
                        # This is a new receipt
                        if current_group:
                            receipt_page_groups.append(current_group)
                        current_group = [page_info["page_number"]]
            else:
                # Not a receipt page, finalize the current group if it exists
                if current_group:
                    receipt_page_groups.append(current_group)
                    current_group = []
        
        # Add the last group if it's not empty
        if current_group:
            receipt_page_groups.append(current_group)
        
        # Final verification pass to ensure correct grouping
        verified_groups_input = f"All receipt groups: {receipt_page_groups}\nPage information: {extracted_information_list}"
        response = await self.custom(instruction=prompt_custom.VERIFY_RECEIPT_GROUPS, input=verified_groups_input)
        verification_result = self.json_extraction(response['response'])
        
        final_receipt_groups = verification_result.get("verified_groups", receipt_page_groups)
        
        # Ensure the output format matches expected structure
        formatted_result = []
        for group in final_receipt_groups:
            if group and isinstance(group, list):
                formatted_result.append(group)
        
        return formatted_result, self.llm.cost_manager.total_cost
