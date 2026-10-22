"""Safety subsystem for blockbrain AI.
Provides secrets isolation, permission tiers, audit logging, untrusted data guards,
kill switch, and spending limits.
"""

from blockbrain.safety.secrets import get_secret, set_keyring_secret, mask_secret, sanitize_text
from blockbrain.safety.tiers import PermissionTier, classify_action
from blockbrain.safety.audit import log_action, get_recent_audit_logs
from blockbrain.safety.untrusted import wrap_untrusted_content, mark_session_tainted, is_session_tainted
from blockbrain.safety.panic import trigger_panic, clear_panic, is_panicked
from blockbrain.safety.limits import record_cost, check_spending_cap

__all__ = [
    "get_secret",
    "set_keyring_secret",
    "mask_secret",
    "sanitize_text",
    "PermissionTier",
    "classify_action",
    "log_action",
    "get_recent_audit_logs",
    "wrap_untrusted_content",
    "mark_session_tainted",
    "is_session_tainted",
    "trigger_panic",
    "clear_panic",
    "is_panicked",
    "record_cost",
    "check_spending_cap",
]

