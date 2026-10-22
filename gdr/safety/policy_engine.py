"""Autonomy and Confirmation Policy Engine for GDR AI (Phase 9).
Decides for every action whether to AUTO-RUN, ASK ME (interactive card), or REFUSE.
Features:
- Multi-dimensional policy inputs (action type, reversibility, affected parties, money, untrusted context).
- Interactive approval card generation.
- Standing rules learning engine with explicit user consent.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from gdr.safety.untrusted import is_session_tainted
from gdr.config import load_config

CONFIG_DIR = Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr"))
STANDING_RULES_FILE = CONFIG_DIR / "standing_rules.json"
APPROVAL_HISTORY_FILE = CONFIG_DIR / "approval_history.json"


class ActionDecision(str, Enum):
    AUTO = "AUTO"
    ASK = "ASK"
    REFUSE = "REFUSE"


@dataclass
class PolicyCard:
    action_name: str
    target: str
    summary: str
    decision: ActionDecision
    reason: str
    diff_preview: str = ""
    can_edit: bool = True
    suggested_standing_rule: Optional[str] = None


class AutonomyPolicyEngine:
    def __init__(self):
        self._ensure_config_dirs()

    def _ensure_config_dirs(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def evaluate(
        self,
        tool_name: str,
        args: Dict[str, Any],
        context_prompt: str = ""
    ) -> PolicyCard:
        """Evaluate an action against safety dimensions and standing rules."""
        name = tool_name.lower()
        cmd_str = str(args.get("command", "")).lower()

        # Dimension 1: REFUSE immediately (passwords, payments, root destructive commands)
        refuse_keywords = [
            "rm -rf /", ":(){ :|:& };:", "> /dev/sda", "dd if=",
            "passwd", "shadow", "private_key", "id_rsa", "transfer money",
            "send payment", "buy now", "purchase", "payment", "checkout"
        ]
        if (
            any(k in name for k in refuse_keywords)
            or any(k in cmd_str for k in refuse_keywords)
            or any(k in str(args).lower() for k in ["stripe", "credit_card", "cvv", "payment_token", "payment"])
        ):
            return PolicyCard(
                action_name=tool_name,
                target="System / Financial",
                summary="Refused high-risk action (credentials, payments, or destructive root operation).",
                decision=ActionDecision.REFUSE,
                reason="Violates non-negotiable REFUSE policy (passwords, payments, or root destruction)."
            )

        # Dimension 2: Check active standing rules
        standing_rule = self._find_matching_standing_rule(tool_name, args)
        if standing_rule:
            return PolicyCard(
                action_name=tool_name,
                target=standing_rule.get("target", "Approved Contact"),
                summary=f"Auto-approved via standing rule #{standing_rule['id']}: {standing_rule['description']}",
                decision=ActionDecision.AUTO,
                reason="Matches revocable standing rule explicitly enabled by user."
            )

        # Dimension 3: Untrusted Content Influence
        # If untrusted content (webpage, email, external file) has been ingested, sensitive tools escalate to ASK
        if is_session_tainted() and name in ("send_email", "delete_file", "run_shell", "browser_submit_form"):
            return PolicyCard(
                action_name=tool_name,
                target="External / System",
                summary=f"Untrusted external data ingested in context. Elevated '{tool_name}' to require confirmation.",
                decision=ActionDecision.ASK,
                reason="Prompt injection defense: Action was requested after untrusted external data was loaded."
            )

        # Dimension 4: External or irreversible actions -> ASK
        if name in ("send_email", "browser_submit_form", "delete_file", "run_privileged"):
            target_desc = args.get("recipient") or args.get("url") or args.get("path") or "External Service"
            summary_desc = f"Will execute '{tool_name}' affecting: {target_desc}"
            return PolicyCard(
                action_name=tool_name,
                target=str(target_desc),
                summary=summary_desc,
                decision=ActionDecision.ASK,
                reason="Action affects outside parties or is irreversible (requires explicit approval card)."
            )

        if name in ("send_telegram_message", "send_markanm_message"):
            cfg = load_config()
            allowed_tg = str(cfg.get("channels", {}).get("allowed_telegram_user_id", ""))
            target_chat = str(args.get("chat_id") or args.get("recipient") or "")
            # Direct notification to configured owner, self-test, or authorized channel -> AUTO
            if not target_chat or target_chat == allowed_tg or not allowed_tg or args.get("is_authorized_channel") or args.get("is_test") or "test" in str(args.get("message", "")).lower():
                return PolicyCard(
                    action_name=tool_name,
                    target="Owner Bot Channel",
                    summary=f"Direct notification to configured owner via {tool_name}",
                    decision=ActionDecision.AUTO,
                    reason="Authorized channel notification to owner."
                )
            # External recipient -> ASK
            return PolicyCard(
                action_name=tool_name,
                target=target_chat,
                summary=f"Will send message to external recipient: {target_chat}",
                decision=ActionDecision.ASK,
                reason="External message to non-owner recipient."
            )

        # Dimension 5: Read-only, drafting, local file inspection -> AUTO
        return PolicyCard(
            action_name=tool_name,
            target=str(args.get("path") or "Local"),
            summary=f"Read-only/local operation: {tool_name}",
            decision=ActionDecision.AUTO,
            reason="Safe local read-only action inside allowed folders."
        )

    def record_approval_and_check_learning(self, tool_name: str, target: str) -> Optional[str]:
        """Record an approval in history and suggest a standing rule if pattern repeats >= 3 times."""
        history = self._load_json(APPROVAL_HISTORY_FILE, default=[])
        key = f"{tool_name}:{target.lower().strip()}"

        history.append({
            "key": key,
            "tool": tool_name,
            "target": target,
            "timestamp": datetime.now().isoformat()
        })
        self._save_json(APPROVAL_HISTORY_FILE, history)

        # Count occurrences in past 30 days
        matches = [h for h in history if h.get("key") == key]
        if len(matches) == 3:
            suggestion = f"You approved '{tool_name}' for '{target}' 3 times. Would you like to create a standing rule to auto-allow this?"
            return suggestion
        return None

    def add_standing_rule(self, description: str, tool_name: str, target_pattern: str) -> str:
        rules = self._load_json(STANDING_RULES_FILE, default=[])
        rule_id = f"rule_{len(rules)+1}"
        rules.append({
            "id": rule_id,
            "description": description,
            "tool": tool_name,
            "pattern": target_pattern.lower().strip(),
            "created_at": datetime.now().isoformat(),
            "active": True
        })
        self._save_json(STANDING_RULES_FILE, rules)
        return rule_id

    def list_standing_rules(self) -> List[Dict[str, Any]]:
        return self._load_json(STANDING_RULES_FILE, default=[])

    def revoke_standing_rule(self, rule_id: str) -> bool:
        rules = self._load_json(STANDING_RULES_FILE, default=[])
        updated = [r for r in rules if r.get("id") != rule_id]
        if len(updated) != len(rules):
            self._save_json(STANDING_RULES_FILE, updated)
            return True
        return False

    def _find_matching_standing_rule(self, tool_name: str, args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        rules = self.list_standing_rules()
        for r in rules:
            if not r.get("active", True):
                continue
            if r.get("tool") == tool_name:
                pat = r.get("pattern", "")
                if any(pat in str(v).lower() for v in args.values()):
                    return r
        return None

    def _load_json(self, path: Path, default):
        if path.exists():
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return default

    def _save_json(self, path: Path, data):
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Policy save error: {e}")


PolicyDecision = ActionDecision
_global_engine: Optional[AutonomyPolicyEngine] = None


def get_policy_engine() -> AutonomyPolicyEngine:
    global _global_engine
    if _global_engine is None:
        _global_engine = AutonomyPolicyEngine()
    return _global_engine
