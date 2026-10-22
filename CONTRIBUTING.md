# Contributing to GDR AI

Thank you for your interest in contributing to **GDR AI**! We welcome community contributions to improve performance, add tool integrations, enhance security, and make desktop AI automation more reliable.

---

## 🛠️ Development Setup

### 1. Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- Git
- `ffmpeg` and `portaudio19-dev` (for local audio and voice processing)
- Virtual environment tool (`python3 -m venv`)

### 2. Fork and Clone
```bash
git clone https://github.com/404adarsh/GDR-AI.git
cd GDR-AI
```

### 3. Create a Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

Or run the interactive installer:
```bash
./install.sh
```

---

## 🧪 Running the Test Suite

Before submitting any changes, ensure all tests pass cleanly:

```bash
# Run the full test suite
pytest tests/ -v

# Run targeted fast tests
pytest tests/test_bots_rag_sarvam_and_vad.py -v
```

---

## 🔒 Security & Secrets Guidelines

We maintain strict security hygiene:
1. **Never commit secrets:** API keys, bot tokens, `.env` files, `.secrets.env`, private keys (`id_rsa`, `*.pem`), or database files must **NEVER** be committed.
2. **Secret Masking:** Any endpoint or UI component handling secrets must only return masked strings (e.g. `sk_...4a2b`) or boolean flags (`has_key: True`), never plaintext values.
3. **Hardware & User Independence:** Do not hardcode specific machine user paths (such as `/home/username`). Use relative paths, `Path.home()`, or standard XDG base directory specifications.
4. **Idempotency & Process Locks:** Any bot worker or event listener should utilize `BotProcessLock` and `EventDeduplicator` to guarantee duplicate instances or repeated requests do not conflict.

---

## 🚀 Pull Request Workflow

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Commit your changes with clear, descriptive commit messages:
   ```bash
   git commit -m "feat(voice): add adaptive speech endpointing threshold"
   ```
3. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
4. Open a Pull Request against `main`. Ensure all CI checks pass.

---

## 📜 Code of Conduct & Licensing

By contributing to GDR AI, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

