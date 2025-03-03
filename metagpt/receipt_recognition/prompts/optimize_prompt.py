WORKFLOW_OPTIMIZE_PROMPT = """You are constructing a Graph and a corresponding Prompt to tackle the receipt recognition problem, where the input is a PDF file, and the output consists of a list of lists, each containing page numbers corresponding to a single complete receipt.

Referring to the provided graph and prompt as a fundamental example of a receipt recognition approach, your task is to reconstruct and optimize them. You may add, modify, or remove nodes, parameters, or prompts as necessary.

Enclose any single modification within XML tags in your response. Ensure all elements are complete and correct to prevent runtime failures.

When optimizing, leverage critical thinking strategies such as review, revision, ensemble methods (e.g., generating multiple responses using different or similar prompts, then integrating, voting, or verifying the majority answer), and self-asking techniques.

For document processing, consider strategies like splitting, merging, and extracting relevant information as needed.

Utilize Python programming constructs such as loops (for, while, list comprehensions), conditional statements (if-elif-else, ternary operators), and machine learning techniques (e.g., linear regression, decision trees, neural networks, clustering).

Keep the graph complexity within 10 nodes, ensuring logical and control flow enhancements using constructs like IF-ELSE and loops for a structured representation.

All necessary prompts required by the current graph from prompt_custom must be included, while any extraneous prompts should be removed. Only generate prompts required for prompt_custom, and exclude those already embedded in other methods. The generated prompt should not contain placeholders.

While complex graphs may enhance results by minimizing information loss, inadequate information flow can lead to omissions. Ensure that essential context is preserved throughout the process."""


WORKFLOW_INPUT = """
Below is a graph and its corresponding prompt (used as inputs for operators like custom and document_inlining) that achieved excellent performance in a previous iteration (maximum score: 1). Your task is to further optimize and improve this graph.

The modified graph must be distinct from the provided example, and all specific changes should be enclosed within <modification>...</modification> tags.

Format for submission:
<sample>
    <experience>{experience}</experience>
    <modification>(e.g., add / delete / modify / ...)</modification>
    <score>{score}</score>
    <graph>{graph}</graph>
    <prompt>{prompt}</prompt> (only prompt_custom)
    <operator_description>{operator_description}</operator_description>
</sample>
Below are logs of previous results where this Graph performed well but encountered errors. These logs can serve as references for further optimization:
{log}

Optimization Guidelines:
1. Propose optimization ideas first.
2. Modify only one detail at a time.
3. Each modification must not exceed five lines of code.
4. Extensive changes are strictly prohibited to maintain project focus.
5. If introducing new functionality in the graph, ensure necessary libraries or modules are imported (except for operator, prompt_custom, create_llm_instance, and CostManage, which are pre-imported).
6. Graph output must never be None for any field.
7. Use custom methods to enforce output formatting instead of relying on inline code.
8. Ensure proper Graph output formatting, referring to the standard format found in the logs.
"""

# 2. Modify only one detail at a time.
# 3. Each modification must not exceed five lines of code.
# 4. Extensive changes are strictly prohibited to maintain project focus.

WORKFLOW_CUSTOM_USE = """\nHere's an example of using the `custom` method in graph:
```
# You can write your own prompt in <prompt>prompt_custom</prompt> and then use it in the Custom method in the graph
response = await self.custom(input=problem, instruction=prompt_custom.XXX_PROMPT)
# You can also concatenate previously generated string results in the input to provide more comprehensive contextual information.
# response = await self.custom(input=problem+f"xxx:{xxx}, xxx:{xxx}", instruction=prompt_custom.XXX_PROMPT)
# The output from the Custom method can be placed anywhere you need it, as shown in the example below
solution = await self.generate(problem=f"question:{problem}, xxx:{response['response']}")
```
Note: In custom, the input and instruction are directly concatenated(instruction+input), and placeholders are not supported. Please ensure to add comments and handle the concatenation externally.\n

**Introducing multiple operators at appropriate points can enhance performance. If you find that some provided operators are not yet used in the graph, try incorporating them.**
"""

WORKFLOW_TEMPLATE = """from typing import Literal
import metagpt.receipt_recognition.optimized.{dataset}.workflows.template.operator as operator
import metagpt.receipt_recognition.optimized.{dataset}.workflows.round_{round}.prompt as prompt_custom
from metagpt.provider.llm_provider_registry import create_llm_instance
from metagpt.utils.cost_manager import CostManager

DatasetType = Literal["ReceiptRecognition"]

{graph}
"""
