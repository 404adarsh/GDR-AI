"""Tool registry with automatic JSON schema generation from Python type hints.
Decorate any function with @tool to automatically expose it to GDR AI.
"""

import functools
import inspect
from typing import Callable, Dict, Any, List, Optional, get_type_hints, get_origin, get_args, Tuple, Union

_TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}


def _python_type_to_json_type(py_type: Any) -> Tuple[str, Optional[str]]:
    """Convert a Python type hint to JSON schema type and optional format."""
    origin = get_origin(py_type)
    if origin is Union:
        args = [a for a in get_args(py_type) if a is not type(None)]
        if len(args) == 1:
            return _python_type_to_json_type(args[0])
        return "string", None

    if py_type in (str, Optional[str]):
        return "string", None
    if py_type in (int, Optional[int]):
        return "integer", None
    if py_type in (float, Optional[float]):
        return "number", None
    if py_type in (bool, Optional[bool]):
        return "boolean", None
    if py_type in (list, List) or origin in (list, List):
        return "array", None
    if py_type in (dict, Dict) or origin in (dict, Dict):
        return "object", None
    return "string", None


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: str = "general",
    tier: str = "AUTO",  # AUTO, APPROVAL, NEVER
    requires_approval: bool = False
):
    """Decorator to register a tool and auto-generate its JSON schema."""
    def decorator(func: Callable):
        tool_name = name or func.__name__
        tool_desc = (description or inspect.getdoc(func) or f"Execute {tool_name}").strip()
        sig = inspect.signature(func)
        try:
            type_hints = get_type_hints(func)
        except Exception:
            type_hints = {}

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = type_hints.get(param_name, str)
            json_type, fmt = _python_type_to_json_type(param_type)

            param_prop: Dict[str, Any] = {"type": json_type}
            if fmt:
                param_prop["format"] = fmt

            # Extract param docstring if available
            param_prop["description"] = f"Parameter {param_name}"

            if param.default is inspect.Parameter.empty:
                required.append(param_name)
            else:
                param_prop["default"] = param.default

            properties[param_name] = param_prop

        schema = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_desc,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

        # Store in registry
        _TOOL_REGISTRY[tool_name] = {
            "name": tool_name,
            "description": tool_desc,
            "category": category,
            "tier": "APPROVAL" if requires_approval else tier,
            "requires_approval": requires_approval or (tier == "APPROVAL"),
            "schema": schema,
            "func": func,
        }

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper._tool_name = tool_name
        wrapper._schema = schema
        return wrapper

    return decorator


def get_all_tool_schemas() -> List[Dict[str, Any]]:
    """Return list of all registered tool schemas formatted for LLM."""
    return [t["schema"] for t in _TOOL_REGISTRY.values()]


def get_tool_metadata(name: str) -> Optional[Dict[str, Any]]:
    """Retrieve metadata for a registered tool."""
    return _TOOL_REGISTRY.get(name)


def execute_tool(name: str, **kwargs) -> Any:
    """Execute registered tool by name with arguments."""
    t = _TOOL_REGISTRY.get(name)
    if not t:
        raise ValueError(f"Unknown tool: '{name}'")
    return t["func"](**kwargs)


def list_tools() -> Dict[str, Dict[str, Any]]:
    """Return dictionary of all registered tools."""
    return dict(_TOOL_REGISTRY)
