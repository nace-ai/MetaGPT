SC_ENSEMBLE_PROMPT = """
Given the question described as follows: {problem}
Several solutions have been generated to address the given question. They are as follows:
{solutions}

Carefully evaluate these solutions and identify the answer that appears most frequently across them. This consistency in answers is crucial for determining the most reliable solution.

In the "thought" field, provide a detailed explanation of your thought process. In the "solution_letter" field, output only the single letter ID (A, B, C, etc.) corresponding to the most consistent solution. Do not include any additional text or explanation in the "solution_letter" field.
"""

PYTHON_CODE_VERIFIER_PROMPT = """
You are a professional Python programmer. Your task is to write complete, self-contained code based on a given mathematical problem and output the answer. The code should include all necessary imports and dependencies, and be ready to run without additional setup or environment configuration.

Problem description: {problem}
Other analysis: {analysis}
{feedback}

Your code should:
1. Implement the calculation steps described in the problem.
2. Define a function named `solve` that performs the calculation and returns the result. The `solve` function should not require any input parameters; instead, it should obtain all necessary inputs from within the function or from globally defined variables.
3. `solve` function return the final calculation result.

Please ensure your code is efficient, well-commented, and follows Python best practices. The output should be limited to basic data types such as strings, integers, and floats. It is prohibited to transmit images or other file formats. The code output is intended for a text-based language model.
"""

RECEIPT_RECOGNITION_RESULT_FORMATTING_PROMPT = """Format receipt recognition result into a JSON array of page index groups for valid receipts/invoices.  

Here is the recognition result: 

{{recognition_result}}

Filter input entries and output their original page groupings as JSON arrays, preserving input order.  

# Steps  
1. **Identify Valid Entries**: Include objects where:  
   - `category`/`type`/`doc_class` is "Receipt" or "Invoice" **OR**  
   - Any metadata field (e.g., `notes`, `description`) contains explicit receipt/invoice indicators (e.g., "fuel receipt", "hotel invoice")  
   - Exclude entries with non-receipt categories like "Expense Line Items" or "Report Log"  

2. **Extract Page Groups**:  
   - Preserve the original `pages` array grouping from each valid entry  
   - Maintain the input's entry order in the output  

# Output Format  
A JSON array of integer arrays:  
```json  
[[page_indices], [page_indices], ...]  
```  
- Single-page receipts: `[5]` (not `5`)  
- Multi-page receipts: `[16,17,18]`  
- Empty if no matches: `[]`  

# Examples  
**Input:**  
```json  
[{"pages": [0,1], "category": "Cover Page"}, {"pages": [2], "notes": "Invoice for supplies"}]  
```  
**Output:**  
```json  
[[2]]  
```  

**Input:**  
```json  
[{"pages": [7], "summary": "Hotel document"}, {"pages": [8], "tags": ["expense_report"]}]  
```  
**Output:**  
```json  
[]  
```  

# Notes  
- **Field Agnosticism**: Metadata fields may vary (e.g., `category`, `type`, `notes`, `description`, `tags`). Prioritize semantic content over field names.  
- **Group Integrity**: Never split/merge original `pages` arrays (e.g., input `[10,11]` → output `[10,11]`)  
- **Validation**: Ignore entries without clear receipt/invoice indicators  
- **Order Preservation**: Maintain the input's entry sequence in the output  
- **Index Formatting**: Always return integers in ascending order within subarrays"""

CONVERSATION_SUMMARIZATION_PROMPT = """Analyze the conversation between a user and an LLM to generate a structured summary of the user's intent and the LLM's core reasoning.  

# Steps  
1. **Identify User Intention**: Determine the primary goal, question, or underlying need from explicit/implicit requests (e.g., problem-solving, information-seeking).  
2. **Extract LLM Reasoning**: Isolate logical steps, evidence, explanations, and analytical processes used to address the request. Prioritize cause-effect relationships, comparisons, or critical deductions.  
3. **Condense Findings**: Summarize conclusions while preserving their connection to reasoning steps. Exclude minor details, greetings, and redundant explanations.  

# Output Format  
Return a JSON object with these fields:  
```json
{
  "user_intention": "A 5-15 word phrase describing the user's core objective",
  "llm_findings": "A 20-40 word summary of the LLM's rationale, explicitly tied to stated reasoning steps"
}
```   

# Examples  
**Input Conversation**  
User: "What caused the 2008 financial crisis?"  
LLM: "The collapse of subprime mortgages led to... [detailed explanation of housing bubble, Lehman Brothers, credit default swaps]"  

**Output**  
```json
{
  "user_intention": "Understand root causes of 2008 crisis",
  "llm_findings": "Identified subprime mortgage collapse as catalyst, explained interconnected factors including housing bubble burst, Lehman Brothers bankruptcy, and credit default swap risks."
}
```  

**Input Conversation**  
User: *"[User question about troubleshooting a network error]"*  
LLM: *"[Step-by-step analysis of potential causes, elimination of irrelevant factors, final diagnosis]"*  

**Output**  
```json
{
  "user_intention": "Resolve a network connectivity issue",
  "llm_findings": "Identified DNS misconfiguration as the root cause by testing local connectivity, ruling out hardware failures, and analyzing error logs."
}
```  

# Notes  
- **Ambiguity**: If intent is unclear, infer using repeated themes or contextual clues (e.g., "Likely seeking...").  
- **Reasoning Verbs**: Prioritize terms like "analyzed," "contrasted," or "demonstrated" from the LLM's response.  
- **Omissions**: Exclude technical jargon, raw data, greetings, and off-topic remarks unless critical.  
- **Accuracy**: Never invent reasoning steps not present in the original conversation.

Here is the conversation to be summarized:
{conversation}"""
