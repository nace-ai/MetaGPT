PAGE_CLASSIFIER_PROMPT = """Analyze this document page and determine if it contains a receipt or invoice. Extract key receipt information.

Return your response in the following JSON format:
```json
{
  "is_receipt": true/false,
  "confidence": 0.0-1.0,
  "extracted_data": "Key details from the receipt including date, vendor name, total amount, receipt/invoice number, and listed items if present",
  "has_receipt_markers": true/false,
  "receipt_type": "RECEIPT/INVOICE/SUMMARY/OTHER"
}
```

Receipt indicators include:
- Total amount or sum
- Itemized purchases with prices
- Date of purchase
- Merchant/vendor information
- Receipt or invoice number
- Payment method details
- Tax information

Return is_receipt=false for cover pages, summary pages, expense reports, or any other non-receipt content.
"""

RECEIPT_CONTINUITY_PROMPT = """Determine if the current page is a continuation of the previous receipt page by comparing the content.

Previous page data: 
{Previous page data provided}

Current page data:
{Current page data provided}

Analyze both pages and determine if they represent the same receipt that continues across pages.

Return your response in the following JSON format:
```json
{
  "is_continuation": true/false,
  "reasoning": "Brief explanation of why these pages are or aren't part of the same receipt",
  "matching_elements": ["List any matching elements like receipt numbers, dates, or vendor names"]
}
```

Signs that pages are part of the same receipt:
- Same vendor/merchant name
- Sequential items or continued itemization
- Page numbers or "continued" indicators
- Matching receipt or invoice numbers
- Continued totals calculation
"""

RECEIPT_VALIDATION_PROMPT = """Validate whether the provided page group represents a valid receipt or invoice.

Page content:
{Page content provided}

Carefully review the content from all pages in this group to confirm whether they collectively form a valid receipt or invoice.

Return your response in the following JSON format:
```json
{
  "is_valid_receipt": true/false,
  "confidence": 0.0-1.0,
  "receipt_elements": ["List of receipt elements detected across all pages"],
  "missing_elements": ["List of expected receipt elements that are missing, if any"],
  "receipt_id": "Receipt or invoice number if identified"
}
```

Key receipt elements to look for:
- Date of purchase/transaction
- Vendor/merchant information
- Transaction total amount
- Itemized purchases or services
- Payment method
- Receipt/invoice number
- Tax information
"""