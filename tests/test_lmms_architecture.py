"""Unit tests for LMMs Unified Architecture in GDR-AI:
- CodeSandbox (subprocess execution, timeout, security guardrails)
- ToolCallParser (XML & JSON extraction, observation blocks)
- ContextManager (sliding window, token budget, pinning)
- SessionGraph (undo, redo, checkpoints, rollback)
- VectorStore (keyword TF-IDF & FAISS fallback, directory indexing)
- AirEngine & ModelOrchestrator
"""

from pathlib import Path
import pytest
import tempfile
import time

from gdr.core.sandbox import CodeSandbox, ToolCallParser, SandboxResult
from gdr.core.context_manager import ContextManager
from gdr.core.session_graph import SessionGraph, SessionNode
from gdr.memory.vector_store import VectorStore
from gdr.models.manager import ModelOrchestrator, AirEngine


def test_code_sandbox_python():
    sandbox = CodeSandbox(default_timeout=5)
    res = sandbox.execute("print(21 * 2)", language="python")
    assert res.success is True
    assert res.stdout.strip() == "42"
    assert res.exit_code == 0
    assert res.timed_out is False


def test_code_sandbox_bash():
    sandbox = CodeSandbox(default_timeout=5)
    res = sandbox.execute("echo 'gdr_ai_test'", language="bash")
    assert res.success is True
    assert "gdr_ai_test" in res.stdout


def test_code_sandbox_blocks_dangerous_commands():
    sandbox = CodeSandbox(default_timeout=5)
    res = sandbox.execute("rm -rf /tmp/test", language="bash")
    assert res.success is False
    assert "Blocked" in res.stderr or "disallowed" in res.stderr or res.exit_code != 0


def test_tool_call_parser_and_observation():
    xml_text = '<tool_call>{"name": "fetch_weather", "arguments": {"city": "Delhi"}}</tool_call>'
    parser = ToolCallParser()
    calls = parser.parse_tool_calls(xml_text)
    assert len(calls) == 1
    assert calls[0]["name"] == "fetch_weather"
    assert calls[0]["arguments"]["city"] == "Delhi"

    result = SandboxResult(
        stdout="Sunny 28C",
        stderr="",
        exit_code=0,
        timed_out=False,
        language="python",
        duration_ms=45.0
    )
    obs = ToolCallParser.format_observation(result)
    assert '<observation' in obs
    assert "Sunny 28C" in obs


def test_context_manager_sliding_window():
    cm = ContextManager(max_tokens=60, reserve_for_completion=10)
    for i in range(10):
        cm.add_message("user" if i % 2 == 0 else "assistant", f"Message number {i} with some extra padding text")

    ctx = cm.get_context(system_prompt="You are GDR AI.")
    # System prompt must always be first
    assert ctx[0]["role"] == "system"
    assert ctx[0]["content"] == "You are GDR AI."
    # Most recent message must be retained
    assert "Message number 9" in ctx[-1]["content"]


def test_session_graph_undo_redo_checkpoints():
    sg = SessionGraph(max_history=10)
    
    # 1. Turn 1
    sg.commit([{"role": "user", "content": "hello"}], label="Greeting")
    assert len(sg.history) == 1
    assert sg.can_undo is False
    assert sg.can_redo is False

    # 2. Turn 2
    sg.commit([{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}], label="Reply")
    assert len(sg.history) == 2
    assert sg.can_undo is True

    # 3. Create named checkpoint
    cp = sg.create_checkpoint("stable_state")
    assert "id" in cp
    checkpoints = sg.list_checkpoints()
    assert len(checkpoints) >= 1
    assert checkpoints[0]["label"] == "stable_state"

    # 4. Undo
    prev = sg.undo()
    assert prev is not None
    assert sg.can_redo is True

    # 5. Redo
    fwd = sg.redo()
    assert fwd is not None
    assert sg.can_redo is False


def test_vector_store_tfidf_search():
    vs = VectorStore()
    docs = [
        "Python is a versatile programming language for AI and machine learning.",
        "Linux kernel powers Android devices and enterprise servers.",
        "Sarvam AI specializes in Indic language models and speech recognition.",
        "Quantum computing relies on superposition and quantum entanglement."
    ]
    metas = [{"topic": "python"}, {"topic": "linux"}, {"topic": "sarvam"}, {"topic": "quantum"}]
    vs.add_documents(docs, metas)
    assert vs.count == 4

    # Search for language / machine learning
    res = vs.search("python programming", top_k=1)
    assert len(res) == 1
    assert "Python" in res[0]["text"]
    assert res[0]["metadata"]["topic"] == "python"

    # Search for Sarvam
    res2 = vs.search("Indic speech recognition", top_k=1)
    assert len(res2) == 1
    assert "Sarvam" in res2[0]["text"]


def test_vector_store_directory_indexing(tmp_path):
    f1 = tmp_path / "main.py"
    f1.write_text("def hello():\n    print('welcome to gdr ai')\n")
    f2 = tmp_path / "notes.md"
    f2.write_text("# GDR AI Notes\nPersonal companion assistant architecture.\n")

    vs = VectorStore()
    indexed_count = vs.index_directory(tmp_path)
    assert indexed_count >= 2
    res = vs.search("personal companion", top_k=1)
    assert len(res) == 1
    assert "GDR AI Notes" in res[0]["text"]


def test_model_orchestrator_routing():
    orchestrator = ModelOrchestrator()
    # Simple greetings -> fast
    assert orchestrator.select_engine("hi there", {}) == "fast"
    # Coding keywords -> heavy
    assert orchestrator.select_engine("write a python function to implement quicksort code", {}) == "heavy"
    # Large context -> air
    assert orchestrator.select_engine("x" * 5000, {}) == "air"


def test_gdr_ide_personal_terminal_and_files_api(tmp_path):
    from fastapi.testclient import TestClient
    from gdr.web.server import app

    client = TestClient(app)

    # 1. Personal terminal command execution
    r_term = client.post("/api/terminal/exec", json={"command": "echo 'gdr-ide-terminal-active'"})
    assert r_term.status_code == 200
    assert "gdr-ide-terminal-active" in r_term.json()["stdout"]

    # 2. Files tree exploration
    r_tree = client.get("/api/files/tree")
    assert r_tree.status_code == 200
    assert "items" in r_tree.json()
    assert len(r_tree.json()["items"]) > 0

    # 3. File save & content read
    test_file = tmp_path / "ide_test.py"
    r_save = client.post("/api/files/save", json={"path": str(test_file), "content": "x = 42\n"})
    assert r_save.status_code == 200
    assert r_save.json()["success"] is True

    r_read = client.get(f"/api/files/content?path={test_file}")
    assert r_read.status_code == 200
    assert "x = 42" in r_read.json()["content"]

