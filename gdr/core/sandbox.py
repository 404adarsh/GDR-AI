"""
gdr.core.sandbox
~~~~~~~~~~~~~~~~

Code execution sandbox with safety guardrails and LLM tool-call parsing.

Supports Python, Bash/Shell, and JavaScript (if Node.js is available).
All execution happens in isolated subprocesses with configurable timeouts.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import tempfile
import textwrap
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, List, Optional


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class SandboxResult:
    """Holds the outcome of a sandboxed code execution."""

    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    language: str
    duration_ms: float

    @property
    def success(self) -> bool:
        """True when exit_code is 0 and execution was not timed out."""
        return self.exit_code == 0 and not self.timed_out

    def __repr__(self) -> str:  # pragma: no cover
        status = "TIMEOUT" if self.timed_out else f"exit={self.exit_code}"
        return (
            f"<SandboxResult lang={self.language} {status} "
            f"duration={self.duration_ms:.1f}ms>"
        )


# ---------------------------------------------------------------------------
# Safety patterns
# ---------------------------------------------------------------------------

_PYTHON_BLOCKED: list[re.Pattern] = [
    re.compile(r"\bos\.system\s*\("),
    re.compile(r"\bsubprocess\s*\."),
    re.compile(r"\beval\s*\("),
    re.compile(r"\bexec\s*\("),
    re.compile(r"__import__\s*\("),
    re.compile(r"\bopen\s*\([^)]*['\"]w['\"]"),        # open(..., "w")
    re.compile(r"\bshutil\.rmtree\b"),
    re.compile(r"\bpickle\.loads\b"),
]

_BASH_BLOCKED: list[re.Pattern] = [
    re.compile(r"rm\s+-[^\s]*r", re.IGNORECASE),       # rm -rf / rm -r
    re.compile(r":\s*\(\s*\)\s*\{.*\}\s*;.*:"),        # fork bomb
    re.compile(r"mkfs\b"),
    re.compile(r"dd\s+.*of=/dev/"),
    re.compile(r">\s*/dev/sd[a-z]"),
    re.compile(r"shutdown|reboot|halt", re.IGNORECASE),
    re.compile(r"curl\s.*\|\s*(?:ba)?sh", re.IGNORECASE),
    re.compile(r"wget\s.*\|\s*(?:ba)?sh", re.IGNORECASE),
]

_JS_BLOCKED: list[re.Pattern] = [
    re.compile(r"require\s*\(\s*['\"]child_process['\"]"),
    re.compile(r"require\s*\(\s*['\"]fs['\"]"),
    re.compile(r"process\.exit"),
]


def _check_safety(code: str, language: str) -> Optional[str]:
    """Return an error message if *code* matches any blocked pattern, else None."""
    patterns: list[re.Pattern] = []
    if language == "python":
        patterns = _PYTHON_BLOCKED
    elif language in ("bash", "shell", "sh"):
        patterns = _BASH_BLOCKED
    elif language in ("javascript", "js"):
        patterns = _JS_BLOCKED

    for pat in patterns:
        if pat.search(code):
            return f"Blocked: code matches disallowed pattern `{pat.pattern}`"
    return None


# ---------------------------------------------------------------------------
# Sandbox
# ---------------------------------------------------------------------------

class CodeSandbox:
    """
    Executes untrusted code snippets in isolated subprocesses.

    Supported languages
    -------------------
    * ``python``  — written to a temp file and run with a restricted wrapper
    * ``bash`` / ``shell`` / ``sh``  — run via ``/bin/bash -c``
    * ``javascript`` / ``js``        — run via ``node`` (if installed)

    Parameters
    ----------
    default_timeout:
        Default execution timeout in seconds (overridable per-call).
    allowed_python_builtins:
        If non-None, replaces the default restricted builtin allowlist.
    """

    _DEFAULT_BUILTINS = (
        "print", "len", "range", "int", "float", "str", "bool", "list",
        "dict", "set", "tuple", "sum", "min", "max", "abs", "round",
        "sorted", "enumerate", "zip", "map", "filter", "isinstance",
        "issubclass", "type", "repr", "hash", "id", "dir",
        "hasattr", "getattr", "setattr", "delattr",
        "any", "all", "iter", "next", "reversed", "chr", "ord",
        "hex", "oct", "bin", "format", "divmod", "pow",
    )

    def __init__(
        self,
        default_timeout: float = 10.0,
        allowed_python_builtins: Optional[tuple[str, ...]] = None,
    ) -> None:
        self.default_timeout = default_timeout
        self._python_builtins: tuple[str, ...] = (
            allowed_python_builtins
            if allowed_python_builtins is not None
            else self._DEFAULT_BUILTINS
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        code: str,
        language: str,
        timeout: Optional[float] = None,
    ) -> SandboxResult:
        """
        Execute *code* in the requested *language* sandbox.

        Parameters
        ----------
        code:
            Source code to execute.
        language:
            One of ``"python"``, ``"bash"``, ``"shell"``, ``"sh"``,
            ``"javascript"``, ``"js"``.
        timeout:
            Execution timeout in seconds; defaults to ``self.default_timeout``.

        Returns
        -------
        SandboxResult
        """
        language = language.lower().strip()
        timeout = timeout if timeout is not None else self.default_timeout

        blocked = _check_safety(code, language)
        if blocked:
            return SandboxResult(
                stdout="",
                stderr=blocked,
                exit_code=1,
                timed_out=False,
                language=language,
                duration_ms=0.0,
            )

        if language == "python":
            return self._run_python(code, timeout)
        elif language in ("bash", "shell", "sh"):
            return self._run_bash(code, timeout)
        elif language in ("javascript", "js"):
            return self._run_javascript(code, timeout)
        else:
            return SandboxResult(
                stdout="",
                stderr=f"Unsupported language: {language!r}",
                exit_code=1,
                timed_out=False,
                language=language,
                duration_ms=0.0,
            )

    # ------------------------------------------------------------------
    # Internal runners
    # ------------------------------------------------------------------

    def _run_python(self, code: str, timeout: float) -> SandboxResult:
        """Run Python code via a restricted wrapper in a subprocess."""
        # Build a wrapper that replaces __builtins__ with the allowlist.
        allowed_str = ", ".join(f'"{b}": {b}' for b in self._python_builtins)
        wrapper = textwrap.dedent(f"""\
            import builtins as _builtins
            _safe_builtins = {{{allowed_str}}}
            # Patch builtins for the user script
            import sys as _sys
            _real_builtins = dict(vars(_builtins))

            _user_globals = {{
                '__builtins__': _safe_builtins,
                '__name__': '__sandbox__',
            }}

            _code = compile(open(_sys.argv[1]).read(), _sys.argv[1], 'exec')
            exec(_code, _user_globals)
        """)

        with (
            tempfile.NamedTemporaryFile(
                suffix=".py", mode="w", delete=False
            ) as code_file,
            tempfile.NamedTemporaryFile(
                suffix="_runner.py", mode="w", delete=False
            ) as runner_file,
        ):
            code_file.write(code)
            code_file.flush()
            runner_file.write(wrapper)
            runner_file.flush()
            code_path = code_file.name
            runner_path = runner_file.name

        try:
            return self._subprocess_run(
                ["python3", runner_path, code_path],
                timeout=timeout,
                language="python",
            )
        finally:
            for p in (code_path, runner_path):
                try:
                    os.unlink(p)
                except OSError:
                    pass

    def _run_bash(self, code: str, timeout: float) -> SandboxResult:
        """Run bash code in a subprocess."""
        with tempfile.NamedTemporaryFile(
            suffix=".sh", mode="w", delete=False
        ) as f:
            f.write("#!/bin/bash\nset -euo pipefail\n")
            f.write(code)
            f.flush()
            script_path = f.name

        try:
            os.chmod(script_path, 0o700)
            return self._subprocess_run(
                ["/bin/bash", script_path],
                timeout=timeout,
                language="bash",
            )
        finally:
            try:
                os.unlink(script_path)
            except OSError:
                pass

    def _run_javascript(self, code: str, timeout: float) -> SandboxResult:
        """Run JavaScript via node (if available)."""
        node_bin = self._find_node()
        if node_bin is None:
            return SandboxResult(
                stdout="",
                stderr="Node.js is not available on this system.",
                exit_code=1,
                timed_out=False,
                language="javascript",
                duration_ms=0.0,
            )

        with tempfile.NamedTemporaryFile(
            suffix=".js", mode="w", delete=False
        ) as f:
            f.write(code)
            f.flush()
            script_path = f.name

        try:
            return self._subprocess_run(
                [node_bin, script_path],
                timeout=timeout,
                language="javascript",
            )
        finally:
            try:
                os.unlink(script_path)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _subprocess_run(
        cmd: list[str],
        timeout: float,
        language: str,
    ) -> SandboxResult:
        """Low-level subprocess executor."""
        start = time.perf_counter()
        timed_out = False
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            stdout, stderr, exit_code = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode(errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
            exit_code = -1
        except Exception as exc:  # noqa: BLE001
            stdout = ""
            stderr = str(exc)
            exit_code = -1

        duration_ms = (time.perf_counter() - start) * 1000
        return SandboxResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            timed_out=timed_out,
            language=language,
            duration_ms=duration_ms,
        )

    @staticmethod
    def _find_node() -> Optional[str]:
        """Return path to node binary or None."""
        for candidate in ("node", "nodejs"):
            try:
                result = subprocess.run(
                    ["which", candidate],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:  # noqa: BLE001
                pass
        return None


# ---------------------------------------------------------------------------
# Tool call parsing
# ---------------------------------------------------------------------------

class ToolCallParser:
    """
    Parses tool/function calls embedded in LLM-generated text.

    Recognises two formats:

    1. **XML blocks** — ``<tool_call>...</tool_call>`` where the body is
       either a JSON object ``{"name": ..., "arguments": {...}}`` or plain
       ``<name>`` / ``<arguments>`` XML children.
    2. **Bare JSON objects** — a top-level ``{"name": ..., "arguments": {...}}``
       JSON object appearing anywhere in the text.

    All results are normalised to ``{"name": str, "arguments": dict}``.
    """

    # Match <tool_call>...</tool_call> blocks (non-greedy, DOTALL)
    _XML_TAG_RE = re.compile(
        r"<tool_call>(.*?)</tool_call>",
        re.DOTALL | re.IGNORECASE,
    )
    # Match JSON objects that look like tool calls at the top level
    _JSON_CALL_RE = re.compile(
        r'\{[^{}]*"name"\s*:\s*"[^"]+"\s*,[^{}]*"arguments"\s*:\s*\{.*?\}[^{}]*\}',
        re.DOTALL,
    )

    def parse_tool_calls(self, text: str) -> list[dict[str, Any]]:
        """
        Extract all tool calls from *text*.

        Parameters
        ----------
        text:
            Raw LLM output that may contain tool call markup.

        Returns
        -------
        list of ``{"name": str, "arguments": dict}`` dicts.
        """
        results: list[dict[str, Any]] = []
        seen_names: set[str] = set()

        # 1. XML-wrapped blocks first (highest priority)
        for match in self._XML_TAG_RE.finditer(text):
            body = match.group(1).strip()
            parsed = self._parse_body(body)
            if parsed and parsed.get("name"):
                key = (parsed["name"], json.dumps(parsed.get("arguments", {}), sort_keys=True))
                if key not in seen_names:
                    seen_names.add(key)
                    results.append(parsed)

        # 2. Bare JSON objects anywhere in text
        for match in self._JSON_CALL_RE.finditer(text):
            try:
                obj = json.loads(match.group(0))
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and "name" in obj:
                parsed = self._normalise(obj)
                key = (parsed["name"], json.dumps(parsed.get("arguments", {}), sort_keys=True))
                if key not in seen_names:
                    seen_names.add(key)
                    results.append(parsed)

        return results

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    @staticmethod
    def format_observation(result: SandboxResult) -> str:
        """
        Wrap a :class:`SandboxResult` in ``<observation>`` tags for re-injection
        into the LLM context.

        Parameters
        ----------
        result:
            The completed sandbox result to format.

        Returns
        -------
        str
            An ``<observation>...</observation>`` XML string.
        """
        parts = [
            f'<observation language="{result.language}" '
            f'exit_code="{result.exit_code}" '
            f'duration_ms="{result.duration_ms:.1f}" '
            f'timed_out="{str(result.timed_out).lower()}">',
        ]
        if result.stdout:
            parts.append(f"<stdout>\n{result.stdout.rstrip()}\n</stdout>")
        if result.stderr:
            parts.append(f"<stderr>\n{result.stderr.rstrip()}\n</stderr>")
        if result.timed_out:
            parts.append("<note>Execution timed out.</note>")
        parts.append("</observation>")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_body(self, body: str) -> Optional[dict[str, Any]]:
        """Try JSON parse first, then XML child parse."""
        # Attempt JSON parse
        try:
            obj = json.loads(body)
            if isinstance(obj, dict):
                return self._normalise(obj)
        except json.JSONDecodeError:
            pass

        # Attempt minimal XML parse
        try:
            wrapped = f"<root>{body}</root>"
            root = ET.fromstring(wrapped)
            name_el = root.find("name")
            args_el = root.find("arguments")
            if name_el is not None and name_el.text:
                arguments: dict = {}
                if args_el is not None and args_el.text:
                    try:
                        arguments = json.loads(args_el.text.strip())
                    except json.JSONDecodeError:
                        pass
                return {"name": name_el.text.strip(), "arguments": arguments}
        except ET.ParseError:
            pass

        return None

    @staticmethod
    def _normalise(obj: dict) -> dict[str, Any]:
        """Normalise a raw dict to ``{"name": str, "arguments": dict}``."""
        name = obj.get("name", obj.get("function", obj.get("tool", "")))
        arguments = obj.get("arguments", obj.get("parameters", obj.get("args", {})))
        if not isinstance(arguments, dict):
            try:
                arguments = json.loads(str(arguments))
            except (json.JSONDecodeError, TypeError):
                arguments = {"raw": arguments}
        return {"name": str(name), "arguments": arguments}


__all__ = [
    "CodeSandbox",
    "SandboxResult",
    "ToolCallParser",
]
