"""Session Graph with Undo/Redo and Checkpointing for GDR AI.
Maintains an immutable tree of conversation turns and state nodes,
enabling non-destructive undo, redo, named checkpoints, and rollbacks.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class SessionNode:
    id: str
    timestamp: float
    messages: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "messages": self.messages,
            "metadata": self.metadata,
            "parent_id": self.parent_id,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SessionNode:
        return cls(
            id=data["id"],
            timestamp=data["timestamp"],
            messages=data["messages"],
            metadata=data.get("metadata", {}),
            parent_id=data.get("parent_id"),
            label=data.get("label", ""),
        )


class SessionGraph:
    """Manages an undo/redo linear history and branching session tree."""

    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self.nodes: Dict[str, SessionNode] = {}
        self.history: List[str] = []  # Ordered list of node IDs in active branch
        self.cursor: int = -1  # Pointer into self.history

    @property
    def current_node(self) -> Optional[SessionNode]:
        if 0 <= self.cursor < len(self.history):
            node_id = self.history[self.cursor]
            return self.nodes.get(node_id)
        return None

    @property
    def current_messages(self) -> List[Dict[str, Any]]:
        node = self.current_node
        return list(node.messages) if node else []

    @property
    def can_undo(self) -> bool:
        return self.cursor > 0

    @property
    def can_redo(self) -> bool:
        return self.cursor < len(self.history) - 1

    def commit(
        self,
        messages: List[Dict[str, Any]],
        label: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new node after current cursor, dropping forward redo branch."""
        node_id = str(uuid.uuid4())[:8]
        parent_id = self.history[self.cursor] if (0 <= self.cursor < len(self.history)) else None

        node = SessionNode(
            id=node_id,
            timestamp=time.time(),
            messages=list(messages),
            metadata=dict(metadata or {}),
            parent_id=parent_id,
            label=label or f"Turn {len(self.history) + 1}",
        )

        self.nodes[node_id] = node

        # Truncate forward history if we branched from middle
        if self.cursor < len(self.history) - 1:
            self.history = self.history[: self.cursor + 1]

        self.history.append(node_id)
        self.cursor = len(self.history) - 1

        # Prune oldest if exceeds max_history
        if len(self.history) > self.max_history:
            pruned_id = self.history.pop(0)
            self.cursor -= 1
            # Only delete if not a checkpoint
            if pruned_id in self.nodes and not self.nodes[pruned_id].metadata.get("is_checkpoint"):
                del self.nodes[pruned_id]

        return node_id

    def checkpoint(self, label: str = "") -> str:
        """Create a named permanent checkpoint of current state."""
        msgs = self.current_messages
        lbl = label or f"Checkpoint @ {datetime.now().strftime('%H:%M:%S')}"
        return self.commit(msgs, label=lbl, metadata={"is_checkpoint": True})

    def create_checkpoint(self, label: str = "") -> Dict[str, Any]:
        """Alias returning a dict for REST API compatibility."""
        cp_id = self.checkpoint(label=label)
        return {"id": cp_id, "label": label}

    def undo(self) -> Optional[SessionNode]:
        """Step backward one turn in history."""
        if not self.can_undo:
            return None
        self.cursor -= 1
        return self.current_node

    def redo(self) -> Optional[SessionNode]:
        """Step forward one turn in history."""
        if not self.can_redo:
            return None
        self.cursor += 1
        return self.current_node

    def rollback(self, node_id: str) -> Optional[SessionNode]:
        """Jump to a specific node by ID."""
        if node_id not in self.nodes:
            return None

        # If it's already in the active history, just move cursor
        if node_id in self.history:
            self.cursor = self.history.index(node_id)
            return self.nodes[node_id]

        # Reconstruct path from root to node_id
        path = []
        curr: Optional[str] = node_id
        while curr and curr in self.nodes:
            path.append(curr)
            curr = self.nodes[curr].parent_id
        path.reverse()

        self.history = path
        self.cursor = len(self.history) - 1
        return self.nodes[node_id]

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """Return all nodes tagged as checkpoints."""
        res = []
        for nid, n in self.nodes.items():
            if n.metadata.get("is_checkpoint"):
                res.append({
                    "id": n.id,
                    "label": n.label,
                    "timestamp": n.timestamp,
                    "formatted_time": datetime.fromtimestamp(n.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
                    "message_count": len(n.messages)
                })
        res.sort(key=lambda x: x["timestamp"], reverse=True)
        return res

    def save(self, path: Path) -> None:
        """Persist graph to JSON."""
        data = {
            "cursor": self.cursor,
            "history": self.history,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()}
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))

    def load(self, path: Path) -> None:
        """Load graph from JSON."""
        if not path.exists():
            return
        data = json.loads(path.read_text())
        self.cursor = data.get("cursor", -1)
        self.history = data.get("history", [])
        self.nodes = {
            nid: SessionNode.from_dict(d)
            for nid, d in data.get("nodes", {}).items()
        }
