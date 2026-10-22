#!/usr/bin/env bash
# ==============================================================================
# GDR-AI (Autonomous Personal Assistant) - Clean Open Source Git Publisher
# Removes existing Git history & origin, initializes a fresh clean repository,
# and pushes to your new GitHub repository with ZERO leaks.
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================================="
echo "🛡️  GDR-AI - Clean Open Source Git Publisher"
echo "=================================================================="
echo "This script prepares your repository for public open-source release:"
echo "  1. Ensures all private keys, logs, and history files are excluded."
echo "  2. Resets git tracking history to eliminate legacy commit leaks."
echo "  3. Prompts for your new GitHub repository URL."
echo "  4. Pushes clean, ready-to-run code to the new repository."
echo "=================================================================="
echo ""

# Verify .gitignore exists
if [ ! -f ".gitignore" ]; then
    echo "❌ Error: .gitignore not found. Cannot proceed without leak protection."
    exit 1
fi

# Ask for the new repository URL
read -rp "🔗 Enter your new GitHub repository URL (press Enter for default: https://github.com/404adarsh/GDR-AI.git): " REPO_URL
REPO_URL="$(echo "$REPO_URL" | xargs)"
if [ -z "$REPO_URL" ]; then
    REPO_URL="https://github.com/404adarsh/GDR-AI.git"
fi

echo ""
echo "Target remote: $REPO_URL"
read -rp "⚠️  Are you sure you want to initialize a fresh clean repo and push to this URL? (y/N): " CONFIRM
CONFIRM="$(echo "$CONFIRM" | tr '[:upper:]' '[:lower:]')"

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "yes" ]; then
    echo "❌ Operation cancelled by user."
    exit 0
fi

echo ""
echo "🧹 Removing legacy .git history to guarantee clean commit history..."
rm -rf .git

echo "✨ Initializing fresh Git repository (main branch)..."
git init -b main

echo "📦 Staging verified source code (Protected by .gitignore)..."
git add .

# Double check that sensitive files are not staged
STAGED_LEAKS="$(git diff --cached --name-only | grep -E "(\.secrets\.env|\.env$|gdr_history\.csv|gdr_history\.jsonl|requests\.db|\.backup)" || true)"
if [ -n "$STAGED_LEAKS" ]; then
    echo "❌ CRITICAL SAFETY STOP: The following private files were staged:"
    echo "$STAGED_LEAKS"
    echo "Aborting push to prevent data leak."
    exit 1
fi

echo "📝 Creating initial open-source commit..."
git commit -m "feat: initial open source release of GDR-AI (Autonomous Personal Assistant)"

echo "🔗 Connecting to new remote: $REPO_URL ..."
git remote add origin "$REPO_URL"

echo "🚀 Pushing to $REPO_URL (main branch)..."
git push -u origin main --force

echo ""
echo "=================================================================="
echo "🎉 SUCCESS! Your clean, leak-free repository is published at:"
echo "   $REPO_URL"
echo "=================================================================="

