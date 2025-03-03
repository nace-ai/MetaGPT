from typing import List
from pydantic import BaseModel, Field


class GenerateOp(BaseModel):
    response: str = Field(default="", description="Your solution for this problem")


class CodeGenerateOp(BaseModel):
    code: str = Field(default="", description="Your complete code solution for this problem")

class ScEnsembleOp(BaseModel):
    solution_letter: str = Field(default="", description="The letter of most consistent solution.")

class DocumentInliningOp(BaseModel):
    response: str = Field(default="", description="The response from the model")
    
class ReceiptRecognitionResultFormattingOp(BaseModel):
    page_groups: List[List[int]] = Field(default=[], description="The page groups of the receipt")