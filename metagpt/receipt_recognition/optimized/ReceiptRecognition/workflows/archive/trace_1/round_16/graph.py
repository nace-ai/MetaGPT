from typing import Literal
import metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.template.operator as operator
import metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.round_16.prompt as prompt_custom
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

    def clean_empty_lists(self, receipt_pages):
        """Remove empty lists and filter out non-receipt pages"""
        return [pages for pages in receipt_pages if len(pages) > 0]

    def validate_receipt_pages(self, receipt_pages, extracted_information_list):
        """Additional validation of receipt pages based on content"""
        validated_receipts = []
        for page_group in receipt_pages:
            if len(page_group) > 0:
                # Check confidence scores for all pages in the group
                confidence_sum = sum(extracted_information_list[p-1].get("confidence_score", 0) for p in page_group)
                avg_confidence = confidence_sum / len(page_group) if len(page_group) > 0 else 0
                # Only include groups with sufficient confidence
                if avg_confidence >= 0.6:
                    validated_receipts.append(page_group)
        return validated_receipts

    async def __call__(self, file_path: str):
        """
        Implementation of the workflow
        """
        pdf_summary = self.pdf_summary(pdf_file_path=file_path)
        extracted_information_list = []
        
        # First pass: Extract information and classify pages
        for i in range(pdf_summary['num_pages']):
            page_number = i + 1
            pdf_bytes = self.pdf_page_extraction(pdf_file_path=file_path, page_numbers=[page_number])
            
            # Enhanced document analysis with more specific receipt indicators
            response = await self.document_inlining(instruction=prompt_custom.ENHANCED_DOCUMENT_INFO_EXTRACTION, document_bytes=pdf_bytes)
            try:
                extracted_info = self.json_extraction(response['response'])
                # Ensure the extracted_info has required fields
                if "is_receipt" not in extracted_info:
                    extracted_info["is_receipt"] = False
                if "extracted_information" not in extracted_info:
                    extracted_info["extracted_information"] = ""
                if "confidence_score" not in extracted_info:
                    extracted_info["confidence_score"] = 0.0
                
                extracted_information_list.append(extracted_info)
            except Exception as e:
                # Handle extraction errors gracefully
                extracted_information_list.append({
                    "is_receipt": False,
                    "extracted_information": "",
                    "confidence_score": 0.0,
                    "error": str(e)
                })
        
        # Second pass: Group receipt pages with context window
        receipt_page_groups = []
        current_group = []
        context_window = 3  # Look at surrounding pages for better continuity detection
        
        for i in range(pdf_summary['num_pages']):
            page_number = i + 1
            current_info = extracted_information_list[i]
            
            # Skip pages with very low confidence
            if current_info.get("confidence_score", 0) < 0.4:
                if len(current_group) > 0:
                    receipt_page_groups.append(current_group)
                    current_group = []
                continue
                
            # Check if this is a receipt page
            if current_info["is_receipt"]:
                # If this is the first page or previous page wasn't a receipt
                if not current_group:
                    current_group = [page_number]
                else:
                    # Check if this is a continuation of previous receipt
                    prev_context = ""
                    if len(current_group) > 0:
                        prev_idx = current_group[-1] - 1
                        prev_context = extracted_information_list[prev_idx]["extracted_information"]
                    
                    # Enhanced continuity check with surrounding context
                    continuity_check_input = f"Previous page: {prev_context}\nCurrent page: {current_info['extracted_information']}\n"
                    
                    # Get surrounding pages for context if available
                    if i > 0 and i < pdf_summary['num_pages'] - 1:
                        before_page = extracted_information_list[i-1]["extracted_information"]
                        after_page = extracted_information_list[i+1]["extracted_information"]
                        continuity_check_input += f"Before context: {before_page}\nAfter context: {after_page}"
                    
                    continuity_response = await self.custom(
                        instruction=prompt_custom.ENHANCED_CONTINUITY_CHECK_PROMPT, 
                        input=continuity_check_input
                    )
                    
                    try:
                        continuity_result = self.json_extraction(continuity_response['response'])
                        # Use ensemble method for more robust decision
                        ensemble_input = [
                            f"is_continuation: {continuity_result.get('is_continuation', False)}",
                            f"confidence: {continuity_result.get('confidence', 0.0)}",
                            f"reasoning: {continuity_result.get('reasoning', '')}"
                        ]
                        ensemble_response = self.sc_ensemble(
                            solutions=ensemble_input,
                            problem=f"Determine if page {page_number} is a continuation of the previous receipt"
                        )
                        
                        # Process the ensemble response
                        is_continuation = "true" in ensemble_response['response'].lower() and "continuation" in ensemble_response['response'].lower()
                        
                        if is_continuation:
                            current_group.append(page_number)
                        else:
                            if current_group:
                                receipt_page_groups.append(current_group)
                            current_group = [page_number]
                    except Exception:
                        # Fallback to simpler logic if extraction fails
                        if i > 0 and extracted_information_list[i-1]["is_receipt"]:
                            current_group.append(page_number)
                        else:
                            if current_group:
                                receipt_page_groups.append(current_group)
                            current_group = [page_number]
            else:
                # Not a receipt page - end current group if exists
                if current_group:
                    receipt_page_groups.append(current_group)
                    current_group = []
        
        # Add the final group if it exists
        if current_group:
            receipt_page_groups.append(current_group)
        
        # Clean and validate results
        cleaned_groups = self.clean_empty_lists(receipt_page_groups)
        validated_groups = self.validate_receipt_pages(cleaned_groups, extracted_information_list)
        
        # Final formatting using the dedicated operator
        formatted_result = self.receipt_recognition_result_formatting({'receipts': validated_groups})
        
        # Fall back to original result if formatting fails
        if not formatted_result or len(formatted_result) == 0:
            formatted_result = validated_groups
            
        return formatted_result, self.llm.cost_manager.total_cost
