"""Model execution, budget management, and 3-lane engine for blockbrain AI."""

from blockbrain.models.budget import VRAMBudgetManager, get_budget_manager
from blockbrain.models.manager import LocalModelManager, GenerationResult
from blockbrain.models.router import PrivacyRouter, ModelRouter, meeting_mode_transcribe_and_summarize
from blockbrain.models.benchmark import run_model_benchmarks, print_benchmark_table

__all__ = [
    "VRAMBudgetManager",
    "get_budget_manager",
    "LocalModelManager",
    "GenerationResult",
    "PrivacyRouter",
    "ModelRouter",
    "meeting_mode_transcribe_and_summarize",
    "run_model_benchmarks",
    "print_benchmark_table",
]

