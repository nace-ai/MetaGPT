DOCUMENT_INFO_EXTRACTION = """Analyze the provided document page and determine if it's a receipt or invoice. 
Extract all available information and return the result in JSON format.

Pay special attention to:
- Headers containing store names, addresses, or transaction information
- Line items with products/services and prices
- Total amounts, subtotals, tax information
- Dates, transaction IDs, and payment methods
- Any other indicators of a financial transaction document

The output should be structured in the following format:
```json
{
  "extracted_information": "extracted information in markdown format with all important receipt details",
  "is_receipt": true/false
}
```

A receipt or invoice typically contains:
- Business name and contact information
- Transaction date and time
- Itemized list of purchases with prices
- Tax information
- Total amount
- Payment method
- Receipt/invoice number

Return is_receipt=true ONLY if the page definitively contains the characteristics of a receipt or invoice."""

RECEIPT_VERIFICATION = """Perform detailed analysis of the potential receipt/invoice page content to verify if it's truly a receipt or invoice.

Analyze the provided content and assess:
1. The presence of key receipt elements (store name, date, items, prices, totals)
2. The formatting and structure typical of receipts/invoices
3. Distinguishing features that separate it from other document types
4. Any metadata that provides context about the document type

Return the following JSON:
```json
{
  "is_receipt": true/false,
  "confidence": 0.0-1.0,
  "metadata": {
    "date": "date if found",
    "vendor": "vendor/store name if found",
    "total": "total amount if found",
    "receipt_id": "receipt/invoice ID if found"
  }
}
```

The confidence score should reflect how certain you are that this is a receipt/invoice page (0.0 = definitely not, 1.0 = definitely is)."""

RECEIPT_RELATIONSHIP_ANALYSIS = """Determine if two pages belong to the same receipt or invoice document.

Analyze both pages to check if:
1. They appear to be a continuation of the same transaction
2. They have matching header information (same vendor, date, receipt number)
3. They have a logical continuation of line items or information
4. The second page appears to be a continuation page (with "continued" markers)
5. The formatting and styling are consistent between pages

Return the following JSON:
```json
{
  "is_single_receipt": true/false,
  "confidence": 0.0-1.0,
  "reasons": ["List of reasons for your decision"]
}
```

Return is_single_receipt=true if you are confident that both pages belong to the same receipt document.
The confidence score should reflect how certain you are of your answer (0.0 = very uncertain, 1.0 = absolutely certain)."""