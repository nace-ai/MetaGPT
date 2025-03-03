from typing import Literal
import metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.template.operator as operator
import metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.round_15.prompt as prompt_custom
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
        pages_info = []
        
        # First pass: Extract and classify all pages with confidence
        for i in range(pdf_summary['num_pages']):
            page_number = i + 1
            pdf_bytes = self.pdf_page_extraction(pdf_file_path=file_path, page_numbers=[page_number])
            response = await self.document_inlining(instruction=prompt_custom.PAGE_CLASSIFIER_PROMPT, document_bytes=pdf_bytes)
            page_classification = self.json_extraction(response['response'])
            pages_info.append({
                "page_number": page_number,
                "classification": page_classification,
                "pdf_bytes": pdf_bytes
            })
        
        # Second pass: Deep analysis for receipt pages and continuity detection
        receipt_groups = []
        current_group = []
        
        for i, page in enumerate(pages_info):
            # Skip pages with low confidence or clearly not receipts
            if not page["classification"]["is_receipt"] or page["classification"]["confidence"] < 0.6:
                if current_group:
                    receipt_groups.append(current_group)
                    current_group = []
                continue
                
            # For pages likely to be receipts, perform deeper analysis
            if i > 0 and pages_info[i-1]["classification"]["is_receipt"]:
                # Check if current receipt is continuation of previous
                prev_data = pages_info[i-1]["classification"]["extracted_data"]
                curr_data = page["classification"]["extracted_data"]
                continuity_check = await self.custom(
                    instruction=prompt_custom.RECEIPT_CONTINUITY_PROMPT,
                    input=f"Previous page data: {prev_data}\nCurrent page data: {curr_data}"
                )
                continuity_result = self.json_extraction(continuity_check['response'])
                
                if continuity_result["is_continuation"]:
                    current_group.append(page["page_number"])
                else:
                    if current_group:
                        receipt_groups.append(current_group)
                    current_group = [page["page_number"]]
            else:
                # Start new receipt group
                if current_group:
                    receipt_groups.append(current_group)
                current_group = [page["page_number"]]
        
        # Add the last group if not empty
        if current_group:
            receipt_groups.append(current_group)
        
        # Validation pass: Verify each group contains valid receipts
        verified_groups = []
        for group in receipt_groups:
            if len(group) > 0:  # Skip empty groups
                # Create validation request with page group content
                validation_content = ""
                for page_num in group:
                    page_idx = page_num - 1
                    if 0 <= page_idx < len(pages_info):
                        page_data = pages_info[page_idx]["classification"]["extracted_data"]
                        validation_content += f"Page {page_num}: {page_data}\n"
                
                # Verify this is a receipt group
                validation_response = await self.custom(
                    instruction=prompt_custom.RECEIPT_VALIDATION_PROMPT,
                    input=validation_content
                )
                validation_result = self.json_extraction(validation_response['response'])
                
                if validation_result["is_valid_receipt"]:
                    verified_groups.append(group)
        
        # Final cleanup: Ensure proper formatting and structure
        final_result = []
        for group in verified_groups:
            if group:  # Ensure no empty groups
                final_result.append(group)
        
        # Use ensemble method to review the final result
        ensemble_input = f"PDF has {pdf_summary['num_pages']} pages. Extracted receipt groups: {final_result}"
        ensemble_solutions = [
            str(final_result),
            str(self.receipt_recognition_result_formatting({"receipts": final_result}))
        ]
        ensemble_result = self.sc_ensemble(solutions=ensemble_solutions, problem=ensemble_input)
        final_output = self.json_extraction(ensemble_result['response'])
        
        return final_output, self.llm.cost_manager.total_cost
