# Security Policy

The GDR AI team takes software security, user privacy, and system safety seriously. Because GDR AI automates desktop workflows, executes shell commands, and connects with cloud AI APIs and messaging bots, we follow strict defense-in-depth security principles.

---

## 🛡️ Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | :white_check_mark: |
| 1.x     | :x:                |

---

## 🔒 Security Design Principles

1. **Local-First & Principle of Least Privilege:**
   - Secrets are loaded strictly from system keyring, `GDR_CONFIG_DIR`, or environment variables. Secrets are never saved in source code or configuration files.
   - All API endpoints mask tokens and keys; plaintext secrets are never sent to the browser or logged.
   - Dangerous system commands (e.g. `rm`, `mkfs`, systemctl changes) trigger explicit human authorization prompts before execution.

2. **Deduplication & Concurrency Protection:**
   - Bot channels (Telegram, MarkanM) enforce an inter-process file lock (`BotProcessLock`) to ensure only one polling listener runs per token.
   - Incoming events and webhooks are tracked via an SQLite WAL-backed idempotency deduplicator (`EventDeduplicator`) to prevent duplicate processing or spam replies.

3. **No Involuntary Model Downloads:**
   - Local weights and heavy models are never downloaded without user confirmation. Sarvam cloud inference (`sarvam-105b-conversations`) is prioritized for lightweight, zero-download operation.

---

## 🚨 Reporting a Vulnerability

If you discover a security vulnerability or sensitive information leak in GDR AI:

1. **Do not open a public GitHub issue.**
2. Report the vulnerability privately by emailing the maintainer or opening a [GitHub Security Advisory](https://github.com/404adarsh/GDR-AI/security/advisories).
3. Include:
   - Description of the vulnerability and attack vector.
   - Reproduction steps or proof of concept (PoC).
   - Any suggested remediations or patches.

We will acknowledge receipt within 48 hours and work with you to release a coordinated security update.

