"""Integrations package for GDR-AI."""
from gdr.integrations.registry import IntegrationRegistry, get_integration_registry
from gdr.integrations.email_assistant import EmailAssistantService, get_email_assistant

__all__ = [
    "IntegrationRegistry",
    "get_integration_registry",
    "EmailAssistantService",
    "get_email_assistant"
]

