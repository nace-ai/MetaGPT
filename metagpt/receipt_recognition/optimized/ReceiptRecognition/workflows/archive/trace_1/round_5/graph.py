from typing import Literal
import metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.template.operator as operator
import metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.round_5.prompt as prompt_custom
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

    def _clean_output(self, page_groups):
        """Clean the output by removing empty lists and normalizing page numbers"""
        cleaned_groups = [group for group in page_groups if group]
        return cleaned_groups

    def _verify_receipt_page(self, extracted_info, page_content, page_number):
        """Verify if a page is a receipt with confidence score"""
        verification_data = {
            "extracted_info": extracted_info,
            "page_content": page_content,
            "page_number": page_number
        }
        return verification_data

    async def _analyze_page_relationship(self, current_page_info, previous_page_info=None):
        """Analyze if pages belong to the same receipt with multiple signals"""
        if not previous_page_info:
            return {"is_single_receipt": False, "confidence": 1.0}
            
        analysis_input = f"Previous page info: {previous_page_info}\nCurrent page info: {current_page_info}"
        response = await self.custom(instruction=prompt_custom.RECEIPT_RELATIONSHIP_ANALYSIS, input=analysis_input)
        result = self.json_extraction(response['response'])
        return result
    
    async def __call__(self, file_path: str):
        """
        Implementation of the workflow
        """
        pdf_summary = self.pdf_summary(pdf_file_path=file_path)
        total_pages = pdf_summary['num_pages']
        
        # First pass: Extract information and classify pages
        page_information = []
        for i in range(total_pages):
            page_number = i + 1
            pdf_bytes = self.pdf_page_extraction(pdf_file_path=file_path, page_numbers=[page_number])
            
            # First stage detection - basic receipt classification
            initial_response = await self.document_inlining(instruction=prompt_custom.DOCUMENT_INFO_EXTRACTION, document_bytes=pdf_bytes)
            initial_extracted_info = self.json_extraction(initial_response['response'])
            
            # Second stage verification - more detailed analysis
            if initial_extracted_info.get("is_receipt", False):
                verification_response = await self.custom(
                    instruction=prompt_custom.RECEIPT_VERIFICATION,
                    input=f"Page content: {initial_extracted_info.get('extracted_information', '')}\nPage number: {page_number}"
                )
                verification_result = self.json_extraction(verification_response['response'])
                
                # Ensemble method for increased accuracy
                classifications = [
                    initial_extracted_info.get("is_receipt", False),
                    verification_result.get("is_receipt", False)
                ]
                is_receipt = all(classifications) or (sum(classifications) >= 1 and verification_result.get("confidence", 0) > 0.7)
                
                metadata = verification_result.get("metadata", {})
                page_info = {
                    "page_number": page_number,
                    "is_receipt": is_receipt,
                    "content": initial_extracted_info.get("extracted_information", ""),
                    "metadata": metadata,
                    "confidence": verification_result.get("confidence", 0)
                }
            else:
                page_info = {
                    "page_number": page_number,
                    "is_receipt": False,
                    "content": initial_extracted_info.get("extracted_information", ""),
                    "metadata": {},
                    "confidence": 0
                }
            
            page_information.append(page_info)
        
        # Second pass: Group receipt pages using enhanced continuity detection
        receipt_page_groups = []
        current_group = []
        
        for i, page_info in enumerate(page_information):
            if page_info["is_receipt"]:
                # Check if this is a continuation of previous receipt
                previous_page_info = page_information[i-1] if i > 0 else None
                
                if previous_page_info and previous_page_info["is_receipt"] and current_group:
                    relationship_result = await self._analyze_page_relationship(
                        page_info["content"],
                        previous_page_info["content"]
                    )
                    
                    if relationship_result.get("is_single_receipt", False):
                        # Continue current receipt group
                        current_group.append(page_info["page_number"])
                    else:
                        # Start new receipt group
                        if current_group:
                            receipt_page_groups.append(current_group)
                        current_group = [page_info["page_number"]]
                else:
                    # Start new receipt group
                    if current_group and not (previous_page_info and previous_page_info["is_receipt"]):
                        receipt_page_groups.append(current_group)
                        current_group = []
                    current_group.append(page_info["page_number"])
            else:
                # Not a receipt page, close current group if exists
                if current_group:
                    receipt_page_groups.append(current_group)
                    current_group = []
        
        # Add the last group if it exists
        if current_group:
            receipt_page_groups.append(current_group)
        
        # Cleanup and validation
        clean_groups = self._clean_output(receipt_page_groups)
        
        # Format result using the dedicated operator
        formatted_result = clean_groups
        
        return formatted_result, self.llm.cost_manager.total_cost
