DOCUMENT_INFO_EXTRACTION = """Extract the information from the provided document page and return the result in Markdown format.
Pay special attention to identify if this page contains a receipt or invoice by looking for:
1. Date of purchase/transaction
2. Merchant/vendor name
3. Total amount
4. Itemized list of purchases
5. Payment method information
6. Receipt/invoice numbers or identifiers

The output should be structured in the following format:
```json
{
  "extracted_information": "extracted information in markdown format, including all key details found",
  "is_receipt": true/false, # whether the information corresponds to receipts or invoices
  "confidence_level": "high/medium/low" # your confidence in the receipt classification
}
```"""

RECEIPT_CONTINUITY_CHECK = """Analyze whether the information from the previous page and the current page belongs to the same receipt/invoice.

Consider the following key factors:
1. Check if header information (vendor, date) is repeated or continued
2. Look for page numbers or "continued" indicators
3. Check if the current page starts with item entries continuing from previous page
4. Verify if the previous page ended without a total/final amount
5. Look for matching receipt/invoice numbers across pages

The output should be structured in the following JSON format:
```json
{
  "is_same_receipt": true/false, # whether the pages belong to the same receipt/invoice
  "reasoning": "brief explanation for the decision"
}
```
"""

RECEIPT_VERIFICATION = """Review the extracted receipt page groupings and verify they are correctly identified.
Look for any inconsistencies or missed receipt pages by comparing the extracted groupings with the page information summary.

Consider the following:
1. Check if any pages marked as receipts are missing from the groupings
2. Verify if multi-page receipts are properly grouped together
3. Look for any unusual gaps or illogical groupings

The output should be structured in the following JSON format:
```json
{
  "analysis": "Your analysis of the current groupings",
  "issues_detected": true/false,
  "corrected_groupings": [[page_numbers], [page_numbers], ...], # Provide the corrected groupings if issues found, otherwise return the original groupings
  "confidence": "high/medium/low"
}
```
"""