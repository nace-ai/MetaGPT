ENHANCED_DOCUMENT_INFO_EXTRACTION = """Analyze this document page carefully to determine if it's a receipt or invoice.

Please look for the following receipt/invoice indicators:
1. Total amount due/paid
2. Line items with prices
3. Date of purchase/transaction
4. Merchant/vendor name
5. Payment method details
6. Tax information
7. Receipt/invoice numbers
8. Itemized charges
9. Subtotals and totals

Please ignore these NON-receipt features:
- Cover pages
- Summary sheets
- Expense report forms
- Table of contents
- General correspondence
- Policy documents
- User information

Extract the text content as accurately as possible and then determine if this is a receipt/invoice page.

Return your analysis in this exact JSON format:
```json
{
  "extracted_information": "extracted information in markdown format",
  "is_receipt": true/false,
  "confidence_score": 0.0-1.0,
  "receipt_indicators": ["list any receipt indicators found"],
  "non_receipt_indicators": ["list any non-receipt indicators found"]
}
```

The confidence_score should reflect how certain you are that this is a receipt, with 1.0 being absolutely certain.
"""

ENHANCED_CONTINUITY_CHECK_PROMPT = """Analyze whether the current page is a continuation of the previous receipt/invoice page.

Consider these factors:
1. Matching merchant/vendor names
2. Continuation of itemized charges
3. Page numbering
4. Running subtotals that connect across pages
5. Matching receipt/invoice numbers
6. Consistent formatting and style
7. Date consistency
8. Related transaction details

Return your analysis in this exact JSON format:
```json
{
  "is_continuation": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation of your decision"
}
```

If there is strong evidence this is the same receipt continuing across pages, answer true.
If it appears to be a new, separate receipt or invoice, answer false.
If the previous page content is empty or not provided, this cannot be a continuation, so answer false.
"""