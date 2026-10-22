"""Command Line Interface for GDR AI.
Provides CLI modes: interactive REPL, one-shot prompt, --voice, --gui, --resume, doctor, panic, and setup.
"""

import argparse
import json
import os
import subprocess
import sys
import time

# Ensure repository root is always at the head of sys.path, even if executed from a subfolder
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_PKG_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from typing import List, Optional

from gdr.config import load_config, save_config
from gdr.core.agent import Agent
from gdr.core.events import setup_signal_handlers, reset_stop_event, load_checkpoint
from gdr.doctor import run_doctor
from gdr.safety.panic import trigger_panic, clear_panic, is_panicked
from gdr.safety.secrets import set_keyring_secret, get_secret

# ---------------------------------------------------------------------------
# Optional heavyweight imports — fail gracefully when modules don't exist yet
# ---------------------------------------------------------------------------
try:
    from gdr.core.session_graph import SessionGraph
    _HAS_SESSION_GRAPH = True
except ImportError:
    _HAS_SESSION_GRAPH = False
    SessionGraph = None  # type: ignore[assignment,misc]

try:
    from gdr.memory.vector_store import VectorStore
    _HAS_VECTOR_STORE = True
except ImportError:
    _HAS_VECTOR_STORE = False
    VectorStore = None  # type: ignore[assignment,misc]

try:
    from rich.console import Console as _RichConsole
    from rich.markup import escape as _rich_escape
    _rich_console = _RichConsole()

    def _print_rich(text: str, style: str = "") -> None:
        _rich_console.print(text, style=style)

    def _print_info(text: str) -> None:
        _rich_console.print(text, style="bold cyan")

    def _print_success(text: str) -> None:
        _rich_console.print(text, style="bold green")

    def _print_warn(text: str) -> None:
        _rich_console.print(text, style="bold yellow")

    def _print_error(text: str) -> None:
        _rich_console.print(text, style="bold red")

    def _print_reply(text: str) -> None:
        _rich_console.print(text, style="bright_white")

    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

    # Fallback ANSI helpers
    _ANSI = {
        "cyan":   "\033[96m",
        "green":  "\033[92m",
        "yellow": "\033[93m",
        "red":    "\033[91m",
        "reset":  "\033[0m",
        "bold":   "\033[1m",
    }

    def _print_rich(text: str, style: str = "") -> None:
        print(text)

    def _print_info(text: str) -> None:
        print(f"{_ANSI['cyan']}{text}{_ANSI['reset']}")

    def _print_success(text: str) -> None:
        print(f"{_ANSI['green']}{text}{_ANSI['reset']}")

    def _print_warn(text: str) -> None:
        print(f"{_ANSI['yellow']}{text}{_ANSI['reset']}")

    def _print_error(text: str) -> None:
        print(f"{_ANSI['red']}{text}{_ANSI['reset']}")

    def _print_reply(text: str) -> None:
        print(text)


def setup_wizard():
    """First-run setup wizard collecting API keys, phone number, and timezone."""
    print("\n" + "=" * 55)
    print("🧙 GDR AI First-Run Setup Wizard")
    print("=" * 55)

    cfg = load_config()

    # Timezone
    import time
    sys_tz = time.tzname[0] if time.tzname else "Asia/Kolkata"
    tz = input(f"Timezone [{cfg['general'].get('timezone', sys_tz)}]: ").strip()
    if tz:
        cfg['general']['timezone'] = tz

    # User Name
    user_name = input(f"Your Name [{cfg['general'].get('user_name', 'GDR')}]: ").strip()
    if user_name:
        cfg['general']['user_name'] = user_name

    # Sarvam API Key
    existing_key = get_secret("SARVAM_API_KEY")
    prompt_str = f"Sarvam API Key (sk_...) [{'configured' if existing_key else 'unset'}]: "
    key = input(prompt_str).strip()
    if key:
        set_keyring_secret("SARVAM_API_KEY", key)
        print("  ✅ Sarvam API key saved securely to system keyring.")

    # Phone Number for Alarms/Briefings
    phone = input(f"Your Phone Number (e.g. +91XXXXXXXXXX) [{get_secret('USER_PHONE_NUMBER', '')}]: ").strip()
    if phone:
        set_keyring_secret("USER_PHONE_NUMBER", phone)

    save_config(cfg)
    print("\n🎉 Setup complete! Configuration saved to ~/.config/gdr/config.toml.\n")


def _build_prompt(mode: str, scope: Optional[str]) -> str:
    """Return the REPL prompt string with mode indicator."""
    mode_icon = {
        "normal": "●",
        "fast":   "⚡",
        "deep":   "🧠",
        "code":   "💻",
        "pair":   "🤝",
    }.get(mode, "●")
    scope_part = f"  📁 {scope}" if scope else ""
    return f"GDR [{mode_icon} {mode.upper()}]{scope_part} ❯ "


def _show_help() -> None:
    lines = [
        "",
        "╔══════════════════════════════════════════════════════════════╗",
        "║              GDR AI — Slash Command Reference                ║",
        "╠══════════════════════════════════════════════════════════════╣",
        "║  MODE / MODEL                                                ║",
        "║  /fast              Switch to fast mode (small/fast model)  ║",
        "║  /deep              Switch to deep thinking mode            ║",
        "║  /model [name]      Show or set current model               ║",
        "║  /ml -l             List all available local models         ║",
        "║  /ml -s <name>      Switch to a specific local model        ║",
        "║  /code              Enter code mode (code + explanation)    ║",
        "║  /pair              Toggle pair programming mode            ║",
        "║──────────────────────────────────────────────────────────────║",
        "║  MEMORY / CONTEXT                                            ║",
        "║  /folder <path>     Index directory into vector store (RAG)  ║",
        "║  /scope <path>      Set working directory scope             ║",
        "║  /clear             Clear conversation history              ║",
        "║──────────────────────────────────────────────────────────────║",
        "║  SESSION GRAPH                                               ║",
        "║  /undo              Undo last message exchange              ║",
        "║  /redo              Redo undone exchange                    ║",
        "║  /checkpoint [lbl]  Save named checkpoint                   ║",
        "║  /rollback <id>     Rollback to checkpoint by id            ║",
        "║  /checkpoints       List all checkpoints                    ║",
        "║  /reset             Full reset (history + session graph)    ║",
        "║──────────────────────────────────────────────────────────────║",
        "║  TOOLS                                                       ║",
        "║  /agent             Show agent status                       ║",
        "║  /research <topic>  Deep multi-step web research            ║",
        "║  /git [cmd]         Run git command in scoped directory     ║",
        "║──────────────────────────────────────────────────────────────║",
        "║  NAVIGATION                                                  ║",
        "║  /help              Show this help                          ║",
        "║  /exit  /quit       Exit REPL                               ║",
        "╚══════════════════════════════════════════════════════════════╝",
        "",
    ]
    _print_info("\n".join(lines))


def interactive_session(agent: "Agent") -> None:
    """Enhanced interactive REPL with slash commands and session graph support."""
    cfg = load_config()
    agent_name = cfg.get("general", {}).get("agent_name", "GDR AI")
    user_name = cfg.get("general", {}).get("user_name", "GDR")

    # Session state
    mode: str = "normal"
    scope: Optional[str] = None
    pair_mode: bool = False

    # Session graph (optional)
    session_graph = None
    if _HAS_SESSION_GRAPH and SessionGraph is not None:
        try:
            session_graph = SessionGraph()
        except Exception:
            pass

    _print_info(f"\n⚡ {agent_name} — Enhanced REPL  (type /help for commands)")
    _print_info(f"   User: {user_name}   Session graph: {'✅' if session_graph else '❌ (unavailable)'}\n")

    while True:
        try:
            reset_stop_event()
            prompt = _build_prompt(mode, scope)
            try:
                user_input = input(prompt).strip()
            except EOFError:
                _print_warn("\nGoodbye!")
                break

            if not user_input:
                continue

            # ----------------------------------------------------------------
            # Slash-command dispatch
            # ----------------------------------------------------------------
            if user_input.startswith("/"):
                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()
                rest = parts[1].strip() if len(parts) > 1 else ""

                # ── /exit /quit ────────────────────────────────────────────
                if cmd in ("/exit", "/quit"):
                    _print_success("Goodbye! 👋")
                    break

                # ── /help ──────────────────────────────────────────────────
                elif cmd == "/help":
                    _show_help()

                # ── /fast ──────────────────────────────────────────────────
                elif cmd == "/fast":
                    mode = "fast"
                    try:
                        agent.set_mode("fast")
                    except AttributeError:
                        pass
                    _print_success("⚡ Switched to FAST mode (small/quick model).")

                # ── /deep ──────────────────────────────────────────────────
                elif cmd == "/deep":
                    mode = "deep"
                    try:
                        agent.set_mode("deep")
                    except AttributeError:
                        pass
                    _print_success("🧠 Switched to DEEP mode (heavy model, more reasoning).")

                # ── /model [name] ──────────────────────────────────────────
                elif cmd == "/model":
                    if rest:
                        try:
                            agent.set_model(rest)
                            _print_success(f"🔀 Model switched to: {rest}")
                        except AttributeError:
                            _print_warn(f"Agent does not support set_model(); model arg: {rest}")
                    else:
                        try:
                            current = agent.get_model()
                        except AttributeError:
                            current = getattr(agent, "model", "unknown")
                        _print_info(f"Current model: {current}")

                # ── /ml ────────────────────────────────────────────────────
                elif cmd == "/ml":
                    ml_parts = rest.split(maxsplit=1)
                    flag = ml_parts[0] if ml_parts else ""
                    ml_arg = ml_parts[1].strip() if len(ml_parts) > 1 else ""
                    if flag == "-l":
                        try:
                            models = agent.list_local_models()
                            if models:
                                _print_info("Available local models:")
                                for m in models:
                                    print(f"  • {m}")
                            else:
                                _print_warn("No local models found.")
                        except AttributeError:
                            _print_warn("Agent does not support list_local_models().")
                    elif flag == "-s" and ml_arg:
                        try:
                            agent.set_model(ml_arg)
                            _print_success(f"🔀 Switched to local model: {ml_arg}")
                        except AttributeError:
                            _print_warn(f"Agent does not support set_model(); wanted: {ml_arg}")
                    else:
                        _print_error("Usage: /ml -l  (list)   or   /ml -s <model_name>  (switch)")

                # ── /folder <path> ─────────────────────────────────────────
                elif cmd == "/folder":
                    if not rest:
                        _print_error("Usage: /folder <path>")
                    elif not _HAS_VECTOR_STORE or VectorStore is None:
                        _print_warn("⚠️  VectorStore module not available. Cannot index folder.")
                    else:
                        folder_path = os.path.expanduser(rest)
                        if not os.path.isdir(folder_path):
                            _print_error(f"Directory not found: {folder_path}")
                        else:
                            try:
                                _print_info(f"📂 Indexing {folder_path} into vector store…")
                                vs = VectorStore()
                                vs.index_directory(folder_path)
                                _print_success(f"✅ Indexed: {folder_path}")
                            except Exception as exc:
                                _print_error(f"Indexing failed: {exc}")

                # ── /code ──────────────────────────────────────────────────
                elif cmd == "/code":
                    mode = "code"
                    try:
                        agent.set_mode("code")
                    except AttributeError:
                        pass
                    _print_success("💻 Code mode enabled — responses will include code with explanation.")

                # ── /pair ──────────────────────────────────────────────────
                elif cmd == "/pair":
                    pair_mode = not pair_mode
                    state = "ON 🤝" if pair_mode else "OFF"
                    mode = "pair" if pair_mode else "normal"
                    try:
                        agent.set_mode(mode)
                    except AttributeError:
                        pass
                    _print_success(f"Pair programming mode: {state}")

                # ── /undo ──────────────────────────────────────────────────
                elif cmd == "/undo":
                    if session_graph is None:
                        _print_warn("Session graph not available.")
                    else:
                        try:
                            prev = session_graph.undo()
                            if prev is not None:
                                if hasattr(agent, "conversation"):
                                    agent.conversation = prev.get("conversation", agent.conversation)
                                _print_success("↩️  Undone last exchange.")
                            else:
                                _print_warn("Nothing to undo.")
                        except Exception as exc:
                            _print_error(f"Undo failed: {exc}")

                # ── /redo ──────────────────────────────────────────────────
                elif cmd == "/redo":
                    if session_graph is None:
                        _print_warn("Session graph not available.")
                    else:
                        try:
                            nxt = session_graph.redo()
                            if nxt is not None:
                                if hasattr(agent, "conversation"):
                                    agent.conversation = nxt.get("conversation", agent.conversation)
                                _print_success("↪️  Redone exchange.")
                            else:
                                _print_warn("Nothing to redo.")
                        except Exception as exc:
                            _print_error(f"Redo failed: {exc}")

                # ── /checkpoint [label] ────────────────────────────────────
                elif cmd == "/checkpoint":
                    if session_graph is None:
                        _print_warn("Session graph not available.")
                    else:
                        label = rest if rest else None
                        try:
                            state = {}
                            if hasattr(agent, "conversation"):
                                state["conversation"] = list(agent.conversation)
                            cp_id = session_graph.save_checkpoint(state, label=label)
                            _print_success(f"💾 Checkpoint saved: {cp_id}" + (f" [{label}]" if label else ""))
                        except Exception as exc:
                            _print_error(f"Checkpoint failed: {exc}")

                # ── /rollback <id> ─────────────────────────────────────────
                elif cmd == "/rollback":
                    if session_graph is None:
                        _print_warn("Session graph not available.")
                    elif not rest:
                        _print_error("Usage: /rollback <checkpoint_id>")
                    else:
                        try:
                            state = session_graph.load_checkpoint(rest)
                            if state:
                                if hasattr(agent, "conversation"):
                                    agent.conversation = state.get("conversation", agent.conversation)
                                _print_success(f"⏪ Rolled back to checkpoint: {rest}")
                            else:
                                _print_warn(f"Checkpoint not found: {rest}")
                        except Exception as exc:
                            _print_error(f"Rollback failed: {exc}")

                # ── /checkpoints ───────────────────────────────────────────
                elif cmd == "/checkpoints":
                    if session_graph is None:
                        _print_warn("Session graph not available.")
                    else:
                        try:
                            checkpoints = session_graph.list_checkpoints()
                            if checkpoints:
                                _print_info(f"{'ID':<36}  {'Label':<20}  Saved At")
                                _print_info("-" * 72)
                                for cp in checkpoints:
                                    cid = cp.get("id", "?")
                                    clabel = cp.get("label", "")
                                    ctime = cp.get("saved_at", "")
                                    print(f"  {cid:<36}  {clabel:<20}  {ctime}")
                            else:
                                _print_warn("No checkpoints saved yet.")
                        except Exception as exc:
                            _print_error(f"Could not list checkpoints: {exc}")

                # ── /agent ─────────────────────────────────────────────────
                elif cmd == "/agent":
                    provider = getattr(agent, "provider", "unknown")
                    model = getattr(agent, "model", "unknown")
                    try:
                        model = agent.get_model()
                    except AttributeError:
                        pass
                    hist_len = len(getattr(agent, "conversation", []))
                    token_info = ""
                    try:
                        token_info = f"  Tokens: {agent.context_manager.token_count()}"
                    except AttributeError:
                        pass
                    _print_info(
                        f"\n🤖 Agent Status\n"
                        f"  Provider : {provider}\n"
                        f"  Model    : {model}\n"
                        f"  Mode     : {mode}\n"
                        f"  History  : {hist_len} message(s){token_info}\n"
                        f"  Scope    : {scope or '(none)'}\n"
                        f"  Pair mode: {'on' if pair_mode else 'off'}\n"
                    )

                # ── /research <topic> ──────────────────────────────────────
                elif cmd == "/research":
                    if not rest:
                        _print_error("Usage: /research <topic>")
                    else:
                        _print_info(f"🔬 Starting deep research on: {rest}")
                        research_prompt = (
                            f"Conduct a thorough, multi-step research on the following topic. "
                            f"Search broadly, synthesise findings, cite sources, and present a "
                            f"structured summary with key insights:\n\n{rest}"
                        )
                        try:
                            reply = agent.run(research_prompt)
                            _print_reply(f"\n🤖 {agent_name}:\n{reply}\n")
                            if session_graph is not None:
                                _auto_commit(session_graph, agent, user_input, reply)
                        except Exception as exc:
                            _print_error(f"Research error: {exc}")

                # ── /scope <path> ──────────────────────────────────────────
                elif cmd == "/scope":
                    if not rest:
                        _print_error("Usage: /scope <path>")
                    else:
                        expanded = os.path.expanduser(rest)
                        if os.path.isdir(expanded):
                            scope = expanded
                            _print_success(f"📁 Scope set to: {scope}")
                        else:
                            _print_error(f"Directory not found: {expanded}")

                # ── /git [cmd] ─────────────────────────────────────────────
                elif cmd == "/git":
                    git_cwd = scope or os.getcwd()
                    git_args = rest if rest else "--help"
                    full_cmd = f"git {git_args}"
                    _print_info(f"🔧 Running: {full_cmd}  (in {git_cwd})")
                    try:
                        result = subprocess.run(
                            full_cmd,
                            shell=True,
                            cwd=git_cwd,
                            capture_output=True,
                            text=True,
                        )
                        if result.stdout:
                            print(result.stdout)
                        if result.stderr:
                            _print_warn(result.stderr)
                    except Exception as exc:
                        _print_error(f"Git error: {exc}")

                # ── /clear ─────────────────────────────────────────────────
                elif cmd == "/clear":
                    if hasattr(agent, "conversation"):
                        agent.conversation = []
                    _print_success("🧹 Conversation history cleared.")

                # ── /reset ─────────────────────────────────────────────────
                elif cmd == "/reset":
                    if hasattr(agent, "conversation"):
                        agent.conversation = []
                    if session_graph is not None:
                        try:
                            session_graph.reset()
                        except Exception:
                            pass
                    mode = "normal"
                    pair_mode = False
                    _print_success("🔄 Full reset: history and session graph cleared.")

                # ── unknown slash command ──────────────────────────────────
                else:
                    _print_error(f"❓ Unknown command: {cmd}  (type /help for a list of commands)")

                continue  # back to prompt after slash command

            # ----------------------------------------------------------------
            # Normal message — send to agent
            # ----------------------------------------------------------------
            print()
            try:
                reply = agent.run(user_input)
                _print_reply(f"\n🤖 {agent_name}:\n{reply}\n")
                # Auto-commit to session graph
                if session_graph is not None:
                    _auto_commit(session_graph, agent, user_input, reply)
            except Exception as exc:
                _print_error(f"Agent error: {exc}")

        except KeyboardInterrupt:
            print()
            _print_warn("(Interrupted — type /exit to quit)")


def _auto_commit(session_graph: "SessionGraph", agent: "Agent", user_msg: str, reply: str) -> None:
    """Commit current conversation state to the session graph silently."""
    try:
        state = {"last_user": user_msg, "last_reply": reply}
        if hasattr(agent, "conversation"):
            state["conversation"] = list(agent.conversation)
        session_graph.commit(state)
    except Exception:
        pass  # Non-fatal — never crash the REPL for graph errors


def interactive_repl():
    """Interactive command loop."""
    setup_signal_handlers()
    cfg = load_config()
    agent_name = cfg.get("general", {}).get("agent_name", "GDR AI")
    user_name = cfg.get("general", {}).get("user_name", "GDR")

    print(f"\n⚡ {agent_name} initialized. Ready for your command, {user_name}.")
    print("Type 'exit' or press Ctrl+D to quit. Type 'doctor' to run diagnostics.\n")

    agent = Agent()

    while True:
        try:
            reset_stop_event()
            user_input = input(f"╭─[{user_name}@GDR-AI]\n╰─> ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit"):
                print("Goodbye!")
                break
            elif user_input.lower() == "doctor":
                run_doctor()
                continue
            elif user_input.lower() == "panic":
                print(trigger_panic())
                continue

            print()
            reply = agent.run(user_input)
            print(f"\n🤖 {agent_name}:\n{reply}\n")

        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break


def main():
    parser = argparse.ArgumentParser(description="GDR AI - Jarvis-style personal assistant on Kali Linux")
    parser.add_argument("prompt", nargs="*", help="Optional task prompt to run immediately")
    parser.add_argument("--voice", "-v", action="store_true", help="Launch hands-free voice mode")
    parser.add_argument("--gui", action="store_true", help="Launch web dashboard GUI")
    parser.add_argument("--call", "--desktop", "--app", dest="call", action="store_true", help="Launch standalone Aarushi Desktop Call Companion window")
    parser.add_argument("--cloud", action="store_true", help="Launch Cloudflare tunnel alongside GUI for remote access")
    parser.add_argument("--tunnel", action="store_true", help="Launch Cloudflare tunnel")
    parser.add_argument("--restart", "-r", action="store_true", help="Restart GUI daemon if port 8844 is already running (preserves all data)")
    parser.add_argument("--reset", action="store_true", help="Safely reset application data with explicit confirmation and automatic backup")
    parser.add_argument("--scope", choices=["conversations", "preferences", "memories", "all"], default="all", help="Scope of data to reset (default: all)")
    parser.add_argument("--confirm", type=str, default="", help="Confirmation string for scripted reset (must be 'RESET')")
    parser.add_argument("--resume", action="store_true", help="Resume interrupted task from checkpoint")
    parser.add_argument("command", nargs="?", choices=["doctor", "panic", "setup", "tasks", "tunnel", "approve", "fix", "repair", "mesh", "autostart", "companion", "timeline", "wellbeing", "reset", "restart", "call"], help="Subcommand")

    # If first argument matches subcommand
    if len(sys.argv) > 1 and sys.argv[1] in ("doctor", "panic", "setup", "tasks", "tunnel", "approve", "fix", "repair", "mesh", "autostart", "companion", "timeline", "wellbeing", "reset", "restart", "call"):
        cmd = sys.argv[1]
        if cmd == "call":
            from gdr.system.desktop_app import launch_desktop_call_app
            launch_desktop_call_app(port=8844, foreground=True)
            sys.exit(0)
        if cmd == "reset":
            from gdr.system.lifecycle import safe_reset_application_data
            scope = "all"
            if "--scope" in sys.argv:
                idx = sys.argv.index("--scope")
                if idx + 1 < len(sys.argv):
                    scope = sys.argv[idx + 1]
            elif len(sys.argv) > 2 and sys.argv[2] in ("conversations", "preferences", "memories", "all"):
                scope = sys.argv[2]
            confirm_val = ""
            if "--confirm" in sys.argv:
                idx = sys.argv.index("--confirm")
                if idx + 1 < len(sys.argv):
                    confirm_val = sys.argv[idx + 1]
            res = safe_reset_application_data(scope=scope, confirmation=confirm_val, interactive=sys.stdin.isatty())
            sys.exit(0 if res.get("success") else 1)

        elif cmd == "restart":
            from gdr.system.lifecycle import graceful_restart_gui
            graceful_restart_gui(port=8844)
            # Re-exec with GUI to start fresh instance with existing data
            sys.argv = [sys.argv[0], "--gui"]

        if cmd == "autostart":
            from gdr.system.autostart import (
                get_autostart_status,
                enable_autostart,
                disable_autostart,
                repair_autostart,
                prompt_autostart_configuration,
            )
            sub = sys.argv[2] if len(sys.argv) > 2 else "prompt"
            if sub == "enable":
                enable_autostart()
                print("✅ Automatic startup has been ENABLED.")
            elif sub == "disable":
                disable_autostart()
                print("⏸️  Automatic startup has been DISABLED.")
            elif sub == "repair":
                repair_autostart()
                print("🔧 Automatic startup configuration has been repaired.")
            elif sub == "status":
                print(json.dumps(get_autostart_status(), indent=2))
            else:
                prompt_autostart_configuration(interactive=True)
            sys.exit(0)

        elif cmd == "companion":
            from gdr.system.companion_service import get_companion_service
            svc = get_companion_service()
            sub = sys.argv[2] if len(sys.argv) > 2 else "status"
            if sub == "start":
                started = svc.start(foreground=False)
                print("✅ Aarushi companion service started in background." if started else "Companion service is already running.")
            elif sub == "stop":
                svc.stop()
                print("🛑 Aarushi companion service stopped.")
            elif sub == "restart":
                svc.stop()
                time.sleep(1.0)
                svc.start(foreground=False)
                print("🔄 Aarushi companion service restarted.")
            elif sub in ("run-fg", "foreground"):
                svc.run_loop()
            else:
                print(json.dumps(svc.get_status(), indent=2))
            sys.exit(0)

        elif cmd == "timeline":
            from gdr.system.timeline import get_timeline_tracker
            tl = get_timeline_tracker()
            sub = sys.argv[2] if len(sys.argv) > 2 else "summary"
            if sub == "stats":
                print(json.dumps(tl.get_daily_stats(), indent=2))
            elif sub == "events":
                print(json.dumps(tl.get_events(), indent=2))
            else:
                lines = tl.format_readable_timeline()
                print("\n=======================================================")
                print("📅 Aarushi Activity Timeline (Today)")
                print("=======================================================")
                for l in lines:
                    print(f"  • {l}")
                print("=======================================================\n")
            sys.exit(0)

        elif cmd == "wellbeing":
            from gdr.system.wellbeing import get_wellbeing_manager
            wb = get_wellbeing_manager()
            sub = sys.argv[2] if len(sys.argv) > 2 else "status"
            if sub == "snooze":
                mins = int(sys.argv[3]) if len(sys.argv) > 3 else 10
                print(wb.snooze(mins))
            elif sub in ("break", "take_break"):
                print(wb.record_break_taken(5))
            else:
                print(json.dumps(wb.get_status(), indent=2))
            sys.exit(0)

        if cmd in ("fix", "repair"):
            from gdr.repair import auto_repair
            auto_repair()
            sys.exit(0)
        elif cmd == "doctor":
            success = run_doctor()
            sys.exit(0 if success else 1)
        elif cmd == "panic":
            if "--clear" in sys.argv:
                clear_panic()
                print("✅ Panic mode cleared. Normal operations resumed.")
            else:
                print(trigger_panic())
            sys.exit(0)
        elif cmd == "setup":
            setup_wizard()
            sys.exit(0)
        elif cmd == "tunnel":
            from gdr.core.tunnel import start_tunnel, stop_tunnel, get_tunnel_status, generate_ascii_qr
            sub = sys.argv[2] if len(sys.argv) > 2 else "start"
            if sub == "stop":
                stop_tunnel()
                print("🛑 Cloudflare tunnel stopped.")
            elif sub == "status":
                st = get_tunnel_status()
                if st["active"] and st["url"]:
                    print(f"🟢 Cloudflare Tunnel is ACTIVE: {st['url']}")
                else:
                    print("⚪ Cloudflare Tunnel is OFFLINE.")
            else:
                print("🚀 Launching Cloudflare Quick Tunnel...")
                ok, url, msg = start_tunnel(port=8844)
                if ok:
                    print(f"\n✅ Cloudflare Tunnel is ACTIVE!")
                    print(f"🔗 Public URL: {url}")
                    print(f"📱 Mobile Teleprompter: {url}/stealth\n")
                    qr = generate_ascii_qr(url)
                    if qr:
                        print(qr)
                        print("\nScan QR code above with any phone camera to connect.\n")
                else:
                    print(f"❌ Failed to start tunnel: {msg}")
            sys.exit(0)
        elif cmd == "approve":
            from gdr.night_shift.queue import list_pending_approvals, resolve_approval
            sub = sys.argv[2] if len(sys.argv) > 2 else None
            items = list_pending_approvals()
            if not items:
                print("No pending approvals.")
                sys.exit(0)
            if sub in ("yes", "y", "allow"):
                target = items[0]
                resolve_approval(target["id"], approved=True)
                print(f"✅ Approved: {target['tool']} ({target['id']})")
            elif sub in ("no", "n", "deny"):
                target = items[0]
                resolve_approval(target["id"], approved=False)
                print(f"❌ Denied: {target['tool']} ({target['id']})")
            elif len(sys.argv) > 3 and sys.argv[3] in ("yes", "y", "no", "n"):
                appr_id = sub
                appr = sys.argv[3] in ("yes", "y")
                resolve_approval(appr_id, approved=appr)
                print(f"Resolved {appr_id} -> {'APPROVED' if appr else 'DENIED'}")
            else:
                print(f"📋 Pending Approvals ({len(items)}):")
                for i in items:
                    print(f"ID: {i['id']} | Action: {i['tool']} | Source: {i.get('source', 'local')} | Args: {i['args']}")
                print("\nTo approve: gdr approve <id> yes  (or: gdr approve yes)")
            sys.exit(0)
        elif cmd == "mesh":
            from gdr.mesh.coordinator import get_mesh_coordinator
            coord = get_mesh_coordinator()
            sub = sys.argv[2] if len(sys.argv) > 2 else "status"

            if sub in ("pair", "add"):
                code, pairing = coord.generate_pairing_code(
                    requester_name="New Node",
                    ttl_seconds=300
                )
                print("\n=======================================================")
                print("🔗 GDR-AI Device Mesh — Connect New Device")
                print("=======================================================")
                print(f"👉 Pairing Code: {code}")
                print(f"⏰ Expires In  : 5 minutes (single-use)")
                print("\nOn your second device (Android Termux, Windows, or Mac), run:")
                print(f"   gdr mesh connect <coordinator_url> {code}\n")
                try:
                    from gdr.core.tunnel import generate_ascii_qr
                    qr = generate_ascii_qr(f"gdr-mesh://pair?code={code}")
                    if qr:
                        print(qr)
                except Exception:
                    pass
                print("=======================================================\n")
            elif sub in ("connect", "join"):
                if len(sys.argv) < 5:
                    print("Usage: gdr mesh connect <coordinator_url> <pairing_code> [device_name]")
                    sys.exit(1)
                coord_url = sys.argv[3]
                p_code = sys.argv[4]
                d_name = sys.argv[5] if len(sys.argv) > 5 else "Remote Node"
                import urllib.request
                from gdr.mesh.platform.base import get_platform_adapter
                plat = get_platform_adapter().get_platform_name()
                req_data = json.dumps({
                    "code": p_code,
                    "device_name": d_name,
                    "platform": plat
                }).encode("utf-8")
                url = f"{coord_url.rstrip('/')}/api/mesh/pair/complete"
                try:
                    req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        res = json.loads(resp.read().decode("utf-8"))
                        if res.get("success"):
                            print(f"\n✅ Successfully paired with Mesh Coordinator!")
                            print(f"• Device ID   : {res.get('device_id')}")
                            print(f"• Device Name : {res.get('device_name')}")
                            client_cfg = {
                                "coordinator_url": coord_url,
                                "device_id": res.get("device_id"),
                                "device_token": res.get("device_token"),
                            }
                            cfg_path = Path.home() / ".config" / "gdr" / "mesh_client.json"
                            cfg_path.parent.mkdir(parents=True, exist_ok=True)
                            cfg_path.write_text(json.dumps(client_cfg, indent=2))
                            print("Starting mesh client agent...")
                            import asyncio
                            from gdr.mesh.agent import MeshAgent
                            agent = MeshAgent(coord_url, res.get("device_token"), res.get("device_id"))
                            asyncio.run(agent.run())
                        else:
                            print(f"❌ Pairing failed: {res.get('error')}")
                except Exception as e:
                    print(f"❌ Connection error: {e}")
            elif sub == "agent":
                cfg_path = Path.home() / ".config" / "gdr" / "mesh_client.json"
                if not cfg_path.exists():
                    print("❌ No paired mesh configuration found. Run 'gdr mesh connect <url> <code>' first.")
                    sys.exit(1)
                import asyncio
                client_cfg = json.loads(cfg_path.read_text())
                from gdr.mesh.agent import MeshAgent
                agent = MeshAgent(client_cfg["coordinator_url"], client_cfg["device_token"], client_cfg["device_id"])
                print(f"🚀 Launching GDR Mesh Agent connected to {client_cfg['coordinator_url']}...")
                asyncio.run(agent.run())
            else: # status / list
                devices = coord.list_devices()
                print("\n=======================================================")
                print("🌐 GDR-AI Multi-Device Mesh Status")
                print("=======================================================")
                if not devices:
                    print("No devices enrolled. Run 'gdr mesh pair' to add your phone or PC.")
                for d in devices:
                    st_icon = "🟢" if d["status"] == "online" else "⚪"
                    bat = d.get("battery", {})
                    bat_str = f" | Battery: {bat.get('percentage')}%" if bat.get("percentage") is not None else ""
                    print(f"{st_icon} {d['name']} [{d['id']}]")
                    print(f"   Platform: {d['platform'].capitalize()} | Status: {d['status'].upper()}{bat_str}")
                print("=======================================================\n")
            sys.exit(0)
        elif cmd == "tasks":
            # Handled by scheduler in Phase 2
            from gdr.scheduler.store import get_job_store
            store = get_job_store()
            sub = sys.argv[2] if len(sys.argv) > 2 else "list"
            if sub == "add":
                if len(sys.argv) < 4:
                    print("Usage: gdr tasks add \"<natural language schedule and description>\"")
                    sys.exit(1)
                text = " ".join(sys.argv[3:])
                from gdr.scheduler.natural import parse_natural_schedule
                parsed = parse_natural_schedule(text)
                if not parsed:
                    print(f"❌ Could not parse schedule from '{text}'. Try e.g. 'at 7am to wake up' or 'in 15m' or 'every weekday 9am summarize email'")
                    sys.exit(1)
                job_id = store.add_job(
                    description=parsed["description"],
                    prompt=parsed["prompt"],
                    schedule_type=parsed["schedule_type"],
                    schedule_expr=parsed["schedule_expr"],
                    next_run_at=parsed["next_run_at"],
                    is_reminder_only=parsed["is_reminder_only"]
                )
                print(f"✅ Scheduled task #{job_id}: '{parsed['description']}' at {parsed['next_run_at'].strftime('%Y-%m-%d %H:%M:%S')}")
            elif sub == "list":
                jobs = store.list_jobs()
                if not jobs:
                    print("No active scheduled tasks.")
                else:
                    print(f"{'ID':<6} | {'Next Run':<20} | {'Type':<8} | Description")
                    print("-" * 65)
                    for j in jobs:
                        print(f"{j['id']:<6} | {j['next_run_at'][:19]:<20} | {j['schedule_type']:<8} | {j['description']}")
            elif sub == "cancel" and len(sys.argv) > 3:
                deleted = store.delete_job(int(sys.argv[3]))
                if deleted:
                    print(f"✅ Cancelled task #{sys.argv[3]}.")
                else:
                    print(f"Task #{sys.argv[3]} not found.")
            elif sub == "snooze" and len(sys.argv) > 3:
                mins = int(sys.argv[4]) if len(sys.argv) > 4 else 10
                new_t = store.snooze_job(int(sys.argv[3]), minutes=mins)
                print(f"💤 Task #{sys.argv[3]} snoozed for {mins} minutes (next run: {new_t.strftime('%H:%M:%S')}).")
            sys.exit(0)

    args, unknown = parser.parse_known_args()

    if args.reset:
        from gdr.system.lifecycle import safe_reset_application_data
        res = safe_reset_application_data(scope=args.scope, confirmation=args.confirm, interactive=sys.stdin.isatty())
        sys.exit(0 if res.get("success") else 1)

    if args.restart and not args.gui:
        # User specified 'gdr --restart' without '--gui' -> restart web GUI daemon
        from gdr.system.lifecycle import graceful_restart_gui
        graceful_restart_gui(port=8844)
        args.gui = True

    if args.call or "--call" in sys.argv or "--desktop" in sys.argv or "--app" in sys.argv:
        from gdr.system.desktop_app import launch_desktop_call_app
        launch_desktop_call_app(port=8844, foreground=True)
        sys.exit(0)

    if args.voice:
        from gdr.voice.loop import run_voice_loop
        agent = Agent()
        run_voice_loop(agent_executor=agent.run)
        sys.exit(0)

    if args.gui:
        import socket
        import webbrowser
        import subprocess
        import time

        port = 8844
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.4)
        is_port_in_use = (sock.connect_ex(("127.0.0.1", port)) == 0)
        sock.close()

        want_cloud = bool(args.cloud or args.tunnel or "--cloud" in sys.argv or "--tunnel" in sys.argv)
        public_url = None

        if want_cloud:
            from gdr.core.tunnel import start_tunnel, generate_ascii_qr
            print("☁️ Initializing Cloudflare Quick Tunnel for remote access...")
            ok, public_url, msg = start_tunnel(port=port)
            if ok:
                print(f"✅ Cloudflare Public URL: {public_url}")
                print(f"📱 Remote Mobile Teleprompter: {public_url}/stealth")
                qr = generate_ascii_qr(public_url)
                if qr:
                    print(qr)
                    print("\n📱 Scan QR code above with your friend's phone to connect!\n")
            else:
                print(f"⚠️ Cloudflare tunnel note: {msg}\n")

        if is_port_in_use:
            if args.restart or "--restart" in sys.argv:
                from gdr.system.lifecycle import graceful_restart_gui
                graceful_restart_gui(port=port)
            else:
                print(f"🌐 GDR Web Dashboard is ALREADY running and active on http://127.0.0.1:{port}!")
                if public_url:
                    print(f"☁️ Public Shareable URL: {public_url}")
                print(f"🚀 Opened http://127.0.0.1:{port} in your browser.")
                print("💡 To restart the server in this terminal, run:")
                print("   gdr --gui --restart\n")
                try:
                    webbrowser.open(f"http://127.0.0.1:{port}")
                    if public_url:
                        webbrowser.open(public_url)
                except Exception:
                    pass
                sys.exit(0)

        import uvicorn
        from gdr.web.server import app
        from gdr.system.lifecycle import record_gui_pid, clear_gui_pid
        import atexit

        record_gui_pid()
        atexit.register(clear_gui_pid)

        def _get_lan_ip():
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except Exception:
                try:
                    return socket.gethostbyname(socket.gethostname())
                except Exception:
                    return "127.0.0.1"

        lan_ip = _get_lan_ip()
        print(f"🌐 Starting GDR Web Dashboard on http://127.0.0.1:{port}...")
        print(f"📱 Stealth Phone Prompter (100% Invisible to Google Meet): http://{lan_ip}:{port}/stealth")
        if public_url:
            print(f"☁️ Public Shareable Cloudflare URL: {public_url}")
        try:
            webbrowser.open(f"http://127.0.0.1:{port}")
            if public_url:
                webbrowser.open(public_url)
        except Exception:
            pass
        try:
            uvicorn.run(app, host="0.0.0.0", port=port)
        except (KeyboardInterrupt, SystemExit):
            print("\n👋 GDR Web Dashboard stopped cleanly.")
        sys.exit(0)

    if args.resume:
        cp = load_checkpoint()
        if not cp:
            print("No checkpoint found to resume.")
            sys.exit(1)
        print(f"Resuming saved task: '{cp.get('active_task')}' (saved {cp.get('saved_at')})")
        agent = Agent()
        agent.conversation = cp.get("conversation", [])
        reply = agent.run(cp.get("active_task", "Continue where you left off."))
        print(f"\n🤖 GDR AI:\n{reply}\n")
        sys.exit(0)

    if args.prompt:
        setup_signal_handlers()
        full_prompt = " ".join(args.prompt)
        agent = Agent()
        reply = agent.run(full_prompt)
        print(reply)
        sys.exit(0)

    # Default to interactive REPL
    interactive_repl()


if __name__ == "__main__":
    main()
