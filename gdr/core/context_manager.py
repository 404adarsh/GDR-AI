"""
gdr.core.context_manager
~~~~~~~~~~~~~~~~~~~~~~~~

Sliding-window context manager for LLM conversation history.

Keeps a rolling buffer of messages that fits within a configurable token
budget.  The system prompt is always pinned as the first element, and the
two most-recent user messages are always retained even when the window is
tight.  Oldest non-pinned messages are evicted first.

Token counting uses *tiktoken* when available and falls back to a simple
``len(text) // 4`` heuristic otherwise.
"""

from __future__ import annotations

import copy
import json
import time
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Optional tiktoken import
# ---------------------------------------------------------------------------
try:
    import tiktoken as _tiktoken

    _TIKTOKEN_ENC = _tiktoken.get_encoding("cl100k_base")
    _TIKTOKEN_AVAILABLE = True
except Exception:  # noqa: BLE001
    _tiktoken = None  # type: ignore[assignment]
    _TIKTOKEN_ENC = None
    _TIKTOKEN_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_tokens_for_message(msg: dict) -> int:
    """Estimate token count for a single chat message dict."""
    # Each message has a small fixed overhead in OpenAI-style APIs.
    overhead = 4
    content = msg.get("content", "") or ""
    role = msg.get("role", "") or ""
    if _TIKTOKEN_AVAILABLE and _TIKTOKEN_ENC is not None:
        return overhead + len(_TIKTOKEN_ENC.encode(content)) + len(_TIKTOKEN_ENC.encode(role))
    return overhead + (len(content) + len(role)) // 4


# ---------------------------------------------------------------------------
# ContextManager
# ---------------------------------------------------------------------------

class ContextManager:
    """
    Sliding-window manager for LLM conversation contexts.

    Parameters
    ----------
    max_tokens:
        Hard upper limit on total tokens in the returned context window.
    reserve_for_completion:
        Tokens reserved for the model's response; excluded from the budget
        available for history.

    Attributes
    ----------
    is_tiktoken_available:
        ``True`` when tiktoken was successfully imported.
    """

    def __init__(
        self,
        max_tokens: int = 8192,
        reserve_for_completion: int = 1024,
    ) -> None:
        self.max_tokens = max_tokens
        self.reserve_for_completion = reserve_for_completion
        self._messages: list[dict[str, Any]] = []
        self.is_tiktoken_available: bool = _TIKTOKEN_AVAILABLE

    # ------------------------------------------------------------------
    # Token counting
    # ------------------------------------------------------------------

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in *text*.

        Uses tiktoken (cl100k_base encoding) when available; falls back to
        ``len(text) // 4``.

        Parameters
        ----------
        text:
            Arbitrary string to tokenise.

        Returns
        -------
        int
            Estimated token count.
        """
        if _TIKTOKEN_AVAILABLE and _TIKTOKEN_ENC is not None:
            return len(_TIKTOKEN_ENC.encode(text))
        return max(1, len(text) // 4)

    # ------------------------------------------------------------------
    # Message management
    # ------------------------------------------------------------------

    def add_message(self, role: str, content: str) -> None:
        """
        Append a message to the internal history.

        Parameters
        ----------
        role:
            Chat role, e.g. ``"user"``, ``"assistant"``, ``"system"``.
        content:
            Message body.
        """
        self._messages.append({
            "role": role,
            "content": content,
            "_ts": time.time(),
        })

    def get_context(self, system_prompt: str) -> list[dict[str, Any]]:
        """
        Return a list of message dicts that fit within the token budget.

        Strategy
        --------
        1. Always pin the ``system`` message (system_prompt) first.
        2. Always pin the two most-recent messages.
        3. Fill remaining budget with messages from newest to oldest,
           evicting oldest non-pinned messages when the budget is exceeded.

        Parameters
        ----------
        system_prompt:
            The system instruction to always prepend.

        Returns
        -------
        list of ``{"role": str, "content": str}`` dicts (no ``_ts`` key).
        """
        budget = self.max_tokens - self.reserve_for_completion
        system_msg = {"role": "system", "content": system_prompt}
        system_tokens = _count_tokens_for_message(system_msg)
        budget -= system_tokens

        if not self._messages:
            return [system_msg]

        # Pinned: last 2 messages
        pinned = self._messages[-2:]
        pinned_tokens = sum(_count_tokens_for_message(m) for m in pinned)
        budget -= pinned_tokens

        # Remaining messages (oldest first), reversed for greedy newest-first fill
        remaining = self._messages[:-2] if len(self._messages) > 2 else []
        included: list[dict] = []
        for msg in reversed(remaining):
            cost = _count_tokens_for_message(msg)
            if budget - cost >= 0:
                included.append(msg)
                budget -= cost
            # If message doesn't fit, keep trying smaller ones (skip, don't break)

        # Reconstruct chronological order: pinned-tail is always at the end
        ordered = list(reversed(included)) + pinned

        # Strip internal _ts key from output
        result = [system_msg]
        for m in ordered:
            result.append({"role": m["role"], "content": m.get("content", "")})
        return result

    def clear(self) -> None:
        """Remove all stored messages."""
        self._messages.clear()

    # ------------------------------------------------------------------
    # Checkpoint / restore
    # ------------------------------------------------------------------

    def checkpoint(self) -> dict:
        """
        Snapshot the current message history.

        Returns
        -------
        dict
            JSON-serialisable snapshot containing ``max_tokens``,
            ``reserve_for_completion``, and ``messages``.
        """
        return {
            "max_tokens": self.max_tokens,
            "reserve_for_completion": self.reserve_for_completion,
            "messages": copy.deepcopy(self._messages),
        }

    def restore(self, snapshot: dict) -> None:
        """
        Restore state from a previously taken snapshot.

        Parameters
        ----------
        snapshot:
            A dict as produced by :meth:`checkpoint`.
        """
        self.max_tokens = snapshot.get("max_tokens", self.max_tokens)
        self.reserve_for_completion = snapshot.get(
            "reserve_for_completion", self.reserve_for_completion
        )
        self._messages = copy.deepcopy(snapshot.get("messages", []))

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def token_count_estimate(self) -> int:
        """Current estimated token usage across all stored messages."""
        return sum(_count_tokens_for_message(m) for m in self._messages)

    @property
    def message_count(self) -> int:
        """Number of messages currently stored."""
        return len(self._messages)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._messages)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ContextManager messages={len(self._messages)} "
            f"~tokens={self.token_count_estimate} "
            f"max={self.max_tokens} tiktoken={self.is_tiktoken_available}>"
        )


__all__ = ["ContextManager"]
