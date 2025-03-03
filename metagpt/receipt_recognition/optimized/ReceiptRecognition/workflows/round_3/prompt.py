DOCUMENT_INFO_EXTRACTION = """Extract the information from the provided document page and return the result in JSON format.

Analyze the content carefully to determine if this page is part of a receipt or invoice. Look for indicators such as:
1. Itemized lists with prices
2. Total amount fields
3. Payment method information
4. Merchant/vendor names
5. Transaction dates
6. Receipt/invoice numbers
7. Tax information
8. "Receipt" or "Invoice" keywords

The output should be structured in the following format:
```json
{
  "extracted_information": "detailed extracted information in markdown format",
  "is_receipt": true/false, 
  "receipt_indicators": ["list", "of", "receipt", "indicators", "found", "on", "page"]
}
```

A page is considered a receipt/invoice if it contains at least 2 of the receipt indicators listed above.
"""

RECEIPT_CONTINUITY_PROMPT = """Determine if the current page is a continuation of the previous receipt/invoice page.

Analyze both page contents and look for:
1. Continuation of item listings from previous page
2. Page numbers or "continued" indicators
3. Matching header/footer information
4. Similar formatting and styling
5. Matching receipt/invoice numbers
6. Continuation of a transaction that was split across pages

The output should be structured in the following JSON format:
```json
{
  "is_continuation": true/false,
  "explanation": "brief explanation of why pages are considered continuous or separate"
}
```

Pages should be considered part of the same receipt only if there is clear evidence they belong together.
"""

VERIFY_RECEIPT_GROUPS = """Review and verify the grouped receipt pages to ensure accurate receipt identification.

The input contains:
1. Current receipt page groupings
2. Extracted information for each page

For each group, verify:
1. Each group contains only pages from a single receipt
2. No pages from the same receipt are in different groups
3. All receipt pages are included in some group
4. Non-receipt pages are not included in any group

The output should be structured in the following JSON format:
```json
{
  "verified_groups": [[page_numbers], [page_numbers], ...],
  "corrections_made": ["description of any corrections made"]
}
```

If the original grouping is correct, return it unchanged. Otherwise, provide the corrected groupings.
"""