DOCUMENT_INFO_EXTRACTION = """Extract the information from the provided document page and return the result in Markdown format.
The output should be structured in the following format:
```json
{
  "extracted_information": "extracted information in markdown format"
  "is_receipt": true/false, # whether the information corresponds to receipts or invoices
}
```"""
RECEIPT_RECOGNITION_PROMPT = """Check whether the given information from the previous page and the current page corresponds to a single receipt or invoice. 
If the information from the previous page is not provided, the result should be based on the information from the current page only.
The output should be structured in the following JSON format:
```json
{
  "is_single_receipt": true/false, # whether the information from the previous and current page corresponds to a single receipt or invoice
}
```
"""