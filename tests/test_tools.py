"""Tests for GDR tools and registry schema generation."""

import pytest
from gdr.tools.registry import tool, get_all_tool_schemas, execute_tool, get_tool_metadata
from gdr.tools.files import write_file, read_file, list_directory
from gdr.tools.shell import run_shell


def test_tool_decorator_and_schema():
    @tool(name="test_addition", description="Add two integers.", category="math")
    def add(a: int, b: int = 1) -> int:
        return a + b

    meta = get_tool_metadata("test_addition")
    assert meta is not None
    assert meta["name"] == "test_addition"
    assert meta["category"] == "math"

    schema = meta["schema"]
    fn = schema["function"]
    assert fn["name"] == "test_addition"
    assert "a" in fn["parameters"]["properties"]
    assert fn["parameters"]["properties"]["a"]["type"] == "integer"
    assert "a" in fn["parameters"]["required"]
    assert "b" not in fn["parameters"]["required"]

    # Test execution
    res = execute_tool("test_addition", a=5, b=10)
    assert res == 15


def test_file_tools(tmp_path):
    test_file = str(tmp_path / "hello.txt")
    write_res = write_file(test_file, "Hello GDR World\nLine 2")
    assert "wrote" in write_res.lower()

    content = read_file(test_file)
    assert "Hello GDR World" in content
    assert "Line 2" in content

    listing = list_directory(str(tmp_path))
    assert "hello.txt" in listing


def test_shell_execution():
    out = run_shell("echo 'gdr_shell_test'")
    assert "gdr_shell_test" in out
    assert "[exit code: 0]" in out

