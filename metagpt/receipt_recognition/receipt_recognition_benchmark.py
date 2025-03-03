from typing import Dict, Literal, Tuple, Callable, Any, List

from metagpt.ext.aflow.benchmark.benchmark import BaseBenchmark

class ReceiptRecognitionBenchmark(BaseBenchmark):
    def __init__(self, name: str, file_path: str, log_path: str):
        super().__init__(name, file_path, log_path)
        
    async def evaluate_problem(self, problem: dict, graph: Callable) -> Tuple[Any, ...]:
        file_path = "metagpt/receipt_recognition/data/expense_reports/" + problem["file_path"]
        expected_output = problem["expected_output"]
        try:
            prediction, cost = await graph(file_path)
            
            score = self.calculate_score(expected_output, prediction)
            
            if score == 0:
                self.log_mismatch(problem=file_path, expected_output=str(expected_output), prediction=str(prediction), extracted_output=str(prediction))
                
            return file_path, str(prediction), str(expected_output), score, cost
        except Exception as e:
            return file_path, str(e), str(expected_output), 0.0, 0.0

    def calculate_score(self, expected_output: List[List[int]], prediction: List[List[int]]) -> float:
        if len(expected_output) != len(prediction):
            return 0.0
        
        for sublist in expected_output:
            if sublist not in prediction:
                return 0.0
        return 1.0

    def get_result_columns(self) -> List[str]:
        return ["file_path", "prediction", "expected_output", "score", "cost"]