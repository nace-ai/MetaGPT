# -*- coding: utf-8 -*-
# @Date    : 8/23/2024 10:00 AM
# @Author  : all
# @Desc    : Evaluation for different datasets

from typing import Dict, Literal, Tuple

from metagpt.ext.aflow.benchmark.benchmark import BaseBenchmark
from metagpt.receipt_recognition.receipt_recognition_benchmark import ReceiptRecognitionBenchmark
DatasetType = Literal["ReceiptRecognition"]


class Evaluator:
    """
    Complete the evaluation for different datasets here
    """

    def __init__(self, eval_path: str):
        self.eval_path = eval_path
        self.dataset_configs: Dict[DatasetType, BaseBenchmark] = {
            "ReceiptRecognition": ReceiptRecognitionBenchmark
        }

    async def graph_evaluate(
        self, dataset: DatasetType, graph, params: dict, path: str, is_test: bool = False
    ) -> Tuple[float, float, float]:
        if dataset not in self.dataset_configs:
            raise ValueError(f"Unsupported dataset: {dataset}")

        data_path = self._get_data_path(dataset, is_test)
        benchmark_class = self.dataset_configs[dataset]
        benchmark = benchmark_class(name=dataset, file_path=data_path, log_path=path)

        # Use params to configure the graph and benchmark
        configured_graph = await self._configure_graph(dataset, graph, params)
        if is_test:
            va_list = None  # For test data, generally use None to test all
        else:
            va_list = None  # Use None to test all Validation data, or set va_list (e.g., [1, 2, 3]) to use partial data
        return await benchmark.run_evaluation(configured_graph, va_list)

    async def _configure_graph(self, dataset, graph, params: dict):
        # Here you can configure the graph based on params
        # For example: set LLM configuration, dataset configuration, etc.
        dataset_config = params.get("dataset", {})
        llm_config = params.get("llm_config", {})
        return graph(name=dataset, llm_config=llm_config, dataset=dataset_config)

    def _get_data_path(self, dataset: DatasetType, test: bool) -> str:
        base_path = f"metagpt/receipt_recognition/data/{dataset.lower()}"
        return f"{base_path}_test.jsonl" if test else f"{base_path}_validate.jsonl"
