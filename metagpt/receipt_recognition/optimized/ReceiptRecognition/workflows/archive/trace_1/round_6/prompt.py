INITIAL_PAGE_CLASSIFICATION = """Analyze this PDF page and determine if it contains a receipt or invoice with the following characteristics:
- Contains items, quantities, prices, dates, merchant information
- Has a clear payment total or amount
- Shows transaction details like payment method
- May include tax information
- Often has a merchant logo, name, or business information

Return your analysis in the following JSON format:
```json
{
  "is_receipt": true/false, 
  "confidence": 0.0-1.0,
  "page_type": "receipt" or "invoice" or "cover_page" or "summary" or "other",
  "reasoning": "brief explanation of your classification"
}
```
Be conservative in your classification. Only mark as receipt/invoice if you're confident."""

DETAILED_RECEIPT_VERIFICATION = """Conduct a detailed analysis of this page to verify if it's a receipt or invoice.

Extract the following information and return in JSON format:
```json
{
  "is_receipt": true/false,
  "receipt_metadata": {
    "date": "extracted date or null",
    "total_amount": "extracted total amount or null",
    "merchant_name": "extracted merchant name or null",
    "receipt_number": "extracted receipt/invoice number or null"
  },
  "extracted_information": "full extracted text content in markdown format"
}
```

Focus on identifying these receipt characteristics:
1. Line items with prices/quantities
2. Total amount paid
3. Transaction date
4. Merchant or vendor information
5. Payment method details
6. Tax information

Pay special attention to distinguishing actual receipts from summary pages, cover sheets, or document headers that might contain similar information but aren't actual receipts."""

RECEIPT_CONTINUITY_CHECK = """Determine if these two pages are part of the same receipt/invoice.

Consider the following factors:
1. Visual formatting continuity
2. Continuation of line items
3. Matching merchant information
4. Continuous numbering or pagination
5. Matching receipt/invoice numbers
6. Related transaction details
7. Matching dates
8. Matching or complementary totals

Return your analysis in the following JSON format:
```json
{
  "is_same_receipt": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "explanation of your decision with specific evidence from both pages"
}
```"""