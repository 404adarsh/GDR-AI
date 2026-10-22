"""GDR Tools package.
Imports all built-in tool modules to ensure automatic registration.
"""

from gdr.tools.registry import (
    tool,
    get_all_tool_schemas,
    get_tool_metadata,
    execute_tool,
    list_tools,
)

# Import all tool modules so the @tool decorator registers them
import gdr.tools.shell
import gdr.tools.files
import gdr.tools.browser
import gdr.tools.system
import gdr.tools.screen
import gdr.tools.research
import gdr.tools.developer
import gdr.tools.email_tool
import gdr.tools.google_workspace
import gdr.tools.coding_agent
import gdr.tools.skills
import gdr.tools.desktop
import gdr.tools.android_tool
import gdr.tools.contacts
import gdr.mesh.router

__all__ = [
    "tool",
    "get_all_tool_schemas",
    "get_tool_metadata",
    "execute_tool",
    "list_tools",
]

