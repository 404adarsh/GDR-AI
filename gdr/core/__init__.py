"""Core agent loop, LLM providers, and events for GDR AI.
"""

from gdr.core.agent import Agent
from gdr.core.providers import get_provider, BaseLLMProvider, ToolCall, LLMResponse
from gdr.core.events import (
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

