"""Model execution, budget management, and 3-lane engine for GDR AI."""

from gdr.models.budget import VRAMBudgetManager, get_budget_manager
from gdr.models.manager import LocalModelManager, GenerationResult, AirEngine, ModelOrchestrator
from gdr.models.router import PrivacyRouter, ModelRouter, meeting_mode_transcribe_and_summarize
from gdr.models.benchmark import run_model_benchmarks, print_benchmark_table

__all__ = [
    "VRAMBudgetManager",
    "get_budget_manager",
    "LocalModelManager",
    "GenerationResult",
    "AirEngine",
    "ModelOrchestrator",
    "PrivacyRouter",
    "ModelRouter",
    "meeting_mode_transcribe_and_summarize",
    "run_model_benchmarks",
    "print_benchmark_table",
]

