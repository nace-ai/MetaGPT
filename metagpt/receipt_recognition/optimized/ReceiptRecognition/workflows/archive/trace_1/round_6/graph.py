from typing import Literal
import metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.template.operator as operator
import metagpt.receipt_recognition.optimized.ReceiptRecognition.workflows.round_6.prompt as prompt_custom
from metagpt.provider.llm_provider_registry import create_llm_instance
from metagpt.utils.cost_manager import CostManager

DatasetType = Literal["ReceiptRecognition"]

import logging
from typing import List, Dict, Optional

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
        self.logger = logging.getLogger(__name__)

    async def preprocess_pdf(self, file_path: str):
        """Initial scan of PDF to identify potential receipt pages"""
        pdf_summary = self.pdf_summary(pdf_file_path=file_path)
        page_candidates = []
        
        for i in range(pdf_summary['num_pages']):
            page_number = i + 1
            try:
                pdf_bytes = self.pdf_page_extraction(pdf_file_path=file_path, page_numbers=[page_number])
                response = await self.document_inlining(
                    instruction=prompt_custom.INITIAL_PAGE_CLASSIFICATION, 
                    document_bytes=pdf_bytes
                )
                classification_result = self.json_extraction(response['response'])
                classification_result["page_number"] = page_number
                page_candidates.append(classification_result)
            except Exception as e:
                self.logger.warning(f"Error preprocessing page {page_number}: {str(e)}")
                page_candidates.append({"page_number": page_number, "is_receipt": False, "confidence": 0.0})
                
        return page_candidates, pdf_summary['num_pages']

    async def verify_receipt_pages(self, file_path: str, page_candidates: List[Dict]):
        """Secondary verification of receipt pages with detailed analysis"""
        verified_pages = []
        
        for candidate in page_candidates:
            if candidate["is_receipt"] and candidate["confidence"] > 0.4:
                page_number = candidate["page_number"]
                try:
                    pdf_bytes = self.pdf_page_extraction(pdf_file_path=file_path, page_numbers=[page_number])
                    response = await self.document_inlining(
                        instruction=prompt_custom.DETAILED_RECEIPT_VERIFICATION, 
                        document_bytes=pdf_bytes
                    )
                    verification_result = self.json_extraction(response['response'])
                    verification_result["page_number"] = page_number
                    verified_pages.append(verification_result)
                except Exception as e:
                    self.logger.warning(f"Error verifying page {page_number}: {str(e)}")
                    verified_pages.append({"page_number": page_number, "is_receipt": candidate["is_receipt"], 
                                          "receipt_metadata": {}, "extracted_information": ""})
            else:
                verified_pages.append({"page_number": candidate["page_number"], "is_receipt": False, 
                                      "receipt_metadata": {}, "extracted_information": ""})
                
        return verified_pages

    async def group_receipt_pages(self, file_path: str, verified_pages: List[Dict]):
        """Group consecutive receipt pages that belong to the same receipt"""
        receipt_groups = []
        current_group = []
        
        for i, page in enumerate(verified_pages):
            if page["is_receipt"]:
                if not current_group:
                    # Start a new group
                    current_group.append(page["page_number"])
                else:
                    # Check if current page is continuation of previous receipt
                    prev_idx = verified_pages.index(next(p for p in verified_pages if p["page_number"] == current_group[-1]))
                    prev_page = verified_pages[prev_idx]
                    
                    input_text = (f"Previous page metadata: {prev_page['receipt_metadata']}\n"
                                 f"Previous page content: {prev_page['extracted_information']}\n"
                                 f"Current page metadata: {page['receipt_metadata']}\n"
                                 f"Current page content: {page['extracted_information']}")
                    
                    solutions = []
                    # Generate multiple analyses for ensemble decision
                    for _ in range(3):
                        response = await self.custom(
                            instruction=prompt_custom.RECEIPT_CONTINUITY_CHECK, 
                            input=input_text
                        )
                        solutions.append(response['response'])
                    
                    ensemble_result = await self.sc_ensemble(
                        solutions=solutions, 
                        problem="Determine if these pages are part of the same receipt"
                    )
                    
                    continuity_result = self.json_extraction(ensemble_result['response'])
                    
                    if continuity_result.get("is_same_receipt", False):
                        current_group.append(page["page_number"])
                    else:
                        # Complete current group and start a new one
                        if current_group:
                            receipt_groups.append(current_group)
                        current_group = [page["page_number"]]
            else:
                # Complete current group if exists
                if current_group:
                    receipt_groups.append(current_group)
                    current_group = []
        
        # Add the last group if it exists
        if current_group:
            receipt_groups.append(current_group)
            
        return receipt_groups

    def post_process_results(self, receipt_groups: List[List[int]]):
        """Clean up the final output by removing empty lists and validating results"""
        # Remove any empty lists
        filtered_groups = [group for group in receipt_groups if group]
        
        # Ensure no duplicates in page numbers across groups
        seen_pages = set()
        unique_groups = []
        
        for group in filtered_groups:
            unique_group = []
            for page in group:
                if page not in seen_pages:
                    seen_pages.add(page)
                    unique_group.append(page)
            if unique_group:
                unique_groups.append(unique_group)
                
        return unique_groups

    async def __call__(self, file_path: str):
        """
        Implementation of the workflow
        """
        try:
            # Step 1: Initial scan to identify potential receipt pages
            page_candidates, _ = await self.preprocess_pdf(file_path)
            
            # Step 2: Detailed verification of receipt pages
            verified_pages = await self.verify_receipt_pages(file_path, page_candidates)
            
            # Step 3: Group consecutive receipt pages
            receipt_groups = await self.group_receipt_pages(file_path, verified_pages)
            
            # Step 4: Post-process the results
            final_groups = self.post_process_results(receipt_groups)
            
            # Step 5: Use receipt recognition formatter to standardize output
            standardized_results = self.receipt_recognition_result_formatting({"receipt_pages": final_groups})
            
            return standardized_results, self.llm.cost_manager.total_cost
            
        except Exception as e:
            self.logger.error(f"Error in receipt recognition workflow: {str(e)}")
            # Return empty list to avoid None output
            return [], self.llm.cost_manager.total_cost
