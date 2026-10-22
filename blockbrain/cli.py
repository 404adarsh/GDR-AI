"""Command Line Interface for blockbrain AI.
Provides CLI modes: interactive REPL, one-shot prompt, --voice, --gui, --resume, doctor, panic, and setup.
"""

import argparse
import os
import sys
from typing import List, Optional

from blockbrain.config import load_config, save_config
from blockbrain.core.agent import Agent
from blockbrain.core.events import setup_signal_handlers, reset_stop_event, load_checkpoint
from blockbrain.doctor import run_doctor
from blockbrain.safety.panic import trigger_panic, clear_panic, is_panicked
from blockbrain.safety.secrets import set_keyring_secret, get_secret


def setup_wizard():
    """First-run setup wizard collecting API keys, phone number, and timezone."""
    print("\n" + "=" * 55)
    print("🧙 blockbrain AI First-Run Setup Wizard")
    print("=" * 55)

    cfg = load_config()

    # Timezone
    import time
    sys_tz = time.tzname[0] if time.tzname else "Asia/Kolkata"
    tz = input(f"Timezone [{cfg['general'].get('timezone', sys_tz)}]: ").strip()
    if tz:
        cfg['general']['timezone'] = tz

    # User Name
    user_name = input(f"Your Name [{cfg['general'].get('user_name', 'blockbrain')}]: ").strip()
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
    print("\n🎉 Setup complete! Configuration saved to ~/.config/blockbrain/config.toml.\n")


def interactive_repl():
    """Interactive command loop."""
    setup_signal_handlers()
    cfg = load_config()
    agent_name = cfg.get("general", {}).get("agent_name", "blockbrain AI")
    user_name = cfg.get("general", {}).get("user_name", "blockbrain")

    print(f"\n⚡ {agent_name} initialized. Ready for your command, {user_name}.")
    print("Type 'exit' or press Ctrl+D to quit. Type 'doctor' to run diagnostics.\n")

    agent = Agent()

    while True:
        try:
            reset_stop_event()
            user_input = input(f"╭─[{user_name}@blockbrain-AI]\n╰─> ").strip()
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
    parser = argparse.ArgumentParser(description="blockbrain AI - Jarvis-style personal assistant on Kali Linux")
    parser.add_argument("prompt", nargs="*", help="Optional task prompt to run immediately")
    parser.add_argument("--voice", "-v", action="store_true", help="Launch hands-free voice mode")
    parser.add_argument("--gui", action="store_true", help="Launch web dashboard GUI")
    parser.add_argument("--cloud", action="store_true", help="Launch Cloudflare tunnel alongside GUI for remote access")
    parser.add_argument("--tunnel", action="store_true", help="Launch Cloudflare tunnel")
    parser.add_argument("--restart", "-r", action="store_true", help="Restart GUI daemon if port 8844 is already running")
    parser.add_argument("--resume", action="store_true", help="Resume interrupted task from checkpoint")
    parser.add_argument("command", nargs="?", choices=["doctor", "panic", "setup", "tasks", "tunnel", "approve"], help="Subcommand")

    # If first argument matches subcommand
    if len(sys.argv) > 1 and sys.argv[1] in ("doctor", "panic", "setup", "tasks", "tunnel", "approve"):
        cmd = sys.argv[1]
        if cmd == "doctor":
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
        elif cmd == "tasks":
            # Handled by scheduler in Phase 2
            from blockbrain.scheduler.store import get_job_store
            store = get_job_store()
            sub = sys.argv[2] if len(sys.argv) > 2 else "list"
            if sub == "add":
                if len(sys.argv) < 4:
                    print("Usage: blockbrain tasks add \"<natural language schedule and description>\"")
                    sys.exit(1)
                text = " ".join(sys.argv[3:])
                from blockbrain.scheduler.natural import parse_natural_schedule
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

    if args.voice:
        from blockbrain.voice.loop import run_voice_loop
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
                print(f"🔄 Restarting blockbrain Web Dashboard on port {port}...")
                try:
                    subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True)
                    time.sleep(1.0)
                except Exception as e:
                    print(f"⚠️ Warning stopping existing process: {e}")
            else:
<<<<<<< HEAD:gdr/cli.py
                print(f"🌐 GDR Web Dashboard is ALREADY running and active on http://127.0.0.1:{port}!")
                if public_url:
                    print(f"☁️ Public Shareable URL: {public_url}")
                print(f"🚀 Opened http://127.0.0.1:{port} in your browser.")
=======
                print(f"🌐 blockbrain Web Dashboard is ALREADY running and active on http://127.0.0.1:{port}!")
                print("🚀 Opened http://127.0.0.1:8844 in your browser.")
>>>>>>> be45bc369589618a8c67114725bf6b54a0777a1f:blockbrain/cli.py
                print("💡 To restart the server in this terminal, run:")
                print("   blockbrain --gui --restart\n")
                try:
                    webbrowser.open(f"http://127.0.0.1:{port}")
                    if public_url:
                        webbrowser.open(public_url)
                except Exception:
                    pass
                sys.exit(0)

        import uvicorn
        from blockbrain.web.server import app

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
        print(f"🌐 Starting blockbrain Web Dashboard on http://127.0.0.1:{port}...")
        print(f"📱 Stealth Phone Prompter (100% Invisible to Google Meet): http://{lan_ip}:{port}/stealth")
        if public_url:
            print(f"☁️ Public Shareable Cloudflare URL: {public_url}")
        try:
            webbrowser.open(f"http://127.0.0.1:{port}")
            if public_url:
                webbrowser.open(public_url)
        except Exception:
            pass
        uvicorn.run(app, host="0.0.0.0", port=port)
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
        print(f"\n🤖 blockbrain AI:\n{reply}\n")
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
