"""Core agent loop, LLM providers, and events for blockbrain AI.
"""

from blockbrain.core.agent import Agent
from blockbrain.core.providers import get_provider, BaseLLMProvider, ToolCall, LLMResponse
from blockbrain.core.events import (
    STOP_EVENT,
    setup_signal_handlers,
    reset_stop_event,
    save_checkpoint,
    load_checkpoint,
    clear_checkpoint,
)

__all__ = [
    "Agent",
    "get_provider",
    "BaseLLMProvider",
    "ToolCall",
    "LLMResponse",
    "STOP_EVENT",
    "setup_signal_handlers",
    "reset_stop_event",
    "save_checkpoint",
    "load_checkpoint",
    "clear_checkpoint",
]

