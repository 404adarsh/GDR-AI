"""blockbrain Tools package.
Imports all built-in tool modules to ensure automatic registration.
"""

from blockbrain.tools.registry import (
    tool,
    get_all_tool_schemas,
    get_tool_metadata,
    execute_tool,
    list_tools,
)

# Import all tool modules so the @tool decorator registers them
import blockbrain.tools.shell
import blockbrain.tools.files
import blockbrain.tools.browser
import blockbrain.tools.system
import blockbrain.tools.screen
import blockbrain.tools.research
import blockbrain.tools.developer
import blockbrain.tools.email_tool
import blockbrain.tools.google_workspace
import blockbrain.tools.coding_agent
import blockbrain.tools.skills
import blockbrain.tools.desktop

__all__ = [
    "tool",
    "get_all_tool_schemas",
    "get_tool_metadata",
    "execute_tool",
    "list_tools",
]

