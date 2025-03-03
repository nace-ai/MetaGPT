DOCUMENT_INFO_EXTRACTION = """Analyze the provided document page thoroughly and extract all information that can help determine if this is a receipt or invoice.
Pay special attention to:
1. The presence of items, prices, totals, tax amounts
2. Whether there are company names, logos, or receipt headers
3. Dates of purchase or transaction
4. Payment methods
5. Receipt/invoice numbers or identifiers

The output should be structured in the following JSON format:
```json
{
  "extracted_information": "detailed extraction of all key information from the page in markdown format",
  "is_receipt": true/false, 
  "confidence_level": 0-1,
  "detected_fields": ["list of receipt fields detected like 'total', 'date', 'items', etc"]
}
```

Be precise in your analysis, as this will determine whether the page is considered a receipt/invoice page."""

RECEIPT_VALIDATION_PROMPT = """Given the document page, perform a detailed validation to confirm if this is truly a receipt or invoice.

Look for definitive evidence such as:
1. Transaction details (items purchased, services rendered)
2. Financial values (prices, subtotals, taxes, final amounts)
3. Merchant information (name, address, contact information)
4. Transaction date and time
5. Payment method information
6. Receipt/invoice numbering or transaction IDs

Analyze the layout and formatting typical of receipts/invoices.

Return your analysis in the following JSON format:
```json
{
  "is_receipt": true/false,
  "confidence_score": 0-1,
  "receipt_type": "detailed receipt", "summary receipt", "invoice", "not a receipt", etc.,
  "key_evidence": ["list of features that support your determination"],
  "missing_elements": ["list of standard receipt elements that are missing"]
}
```

Err on the side of caution - if it resembles documentation, cover pages, or explanatory pages rather than actual receipts/invoices, mark it as not a receipt."""

RECEIPT_CONTINUATION_PROMPT = """Determine if the current page is a continuation of the previous receipt/invoice page or a new, separate receipt/invoice.

Consider these factors:
1. Do they share the same transaction date?
2. Do they appear to be from the same merchant/vendor?
3. Does the current page continue itemization from the previous page?
4. Are there any "continued from previous page" indicators?
5. Does the current page contain summary information (totals) from items on the previous page?
6. Do they have matching receipt/invoice numbers?
7. Does the formatting and style match between pages?

Return your determination in the following JSON format:
```json
{
  "is_single_receipt": true/false,
  "reasoning": "detailed explanation of why these pages are or are not part of the same receipt",
  "confidence": "high", "medium", or "low"
}
```

If the pages are completely unrelated or from different merchants/transactions, indicate 'false' for is_single_receipt."""

FINAL_VERIFICATION_PROMPT = """Verify if this document is a genuine receipt or invoice page that should be included in the final analysis.

Examine the document for:
1. Whether this is a cover page, summary page, or explanation page (not a receipt)
2. If this contains actual transaction details rather than just receipt policies or notes
3. Whether this page contains meaningful financial information related to a purchase or service

Return your verification in the following JSON format:
```json
{
  "is_valid_receipt_group": true/false,
  "justification": "detailed explanation of your determination",
  "page_type": "receipt", "invoice", "cover page", "summary page", "explanation page", etc.
}
```

Be strict in your assessment - only pages that actually contain receipt or invoice information should be marked as valid."""