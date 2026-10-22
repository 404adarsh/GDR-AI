#!/usr/bin/env bash
# ==============================================================================
# GDR-AI Smart Git Pusher (Linux & macOS)
# Asks for a commit message, validates leak protection, commits and pushes.
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================================="
echo "🚀 GDR-AI Smart Git Pusher"
echo "=================================================================="

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "⚠️ Git repository not found. Initializing..."
    git init -b main
    git remote add origin https://github.com/404adarsh/GDR-AI.git 2>/dev/null || true
fi

# Ask for commit message
echo ""
read -rp "📝 Enter commit message: " COMMIT_MSG
COMMIT_MSG="$(echo "$COMMIT_MSG" | xargs)"

if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="chore: update GDR-AI ($(date +'%Y-%m-%d %H:%M:%S'))"
fi

echo ""
echo "📦 Staging changes..."
git add .

# Security Check: Verify private files are NOT staged
STAGED_LEAKS="$(git diff --cached --name-only | grep -E "(\.secrets\.env|\.env$|gdr_history\.csv|gdr_history\.jsonl|requests\.db|\.backup)" || true)"
if [ -n "$STAGED_LEAKS" ]; then
    echo "❌ CRITICAL SAFETY STOP: The following private files were staged:"
    echo "$STAGED_LEAKS"
    echo "Aborting push to prevent sensitive credential leaks."
    exit 1
fi

# Check if there are changes to commit
if git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "ℹ️  No new changes to commit in working tree."
else
    echo "📝 Creating commit: $COMMIT_MSG"
    git commit -m "$COMMIT_MSG"
fi

echo ""
echo "🚀 Pushing to origin main..."

# Try standard push first
if git push origin main 2>/dev/null; then
    echo ""
    echo "=================================================================="
    echo "🎉 Successfully pushed to https://github.com/404adarsh/GDR-AI"
    echo "=================================================================="
    exit 0
fi

# If standard push failed (e.g. requires authentication or 403), prompt for token
echo "⚠️ Direct push requires GitHub authentication credentials."
echo ""
read -rp "👤 Enter GitHub Username [404adarsh]: " GH_USER
GH_USER="${GH_USER:-404adarsh}"

read -rsp "🔑 Enter GitHub Personal Access Token (PAT): " GH_TOKEN
echo ""

if [ -z "$GH_TOKEN" ]; then
    echo "❌ No token entered. Push aborted."
    exit 1
fi

echo "🚀 Authenticating and pushing..."
git push "https://${GH_USER}:${GH_TOKEN}@github.com/404adarsh/GDR-AI.git" main

echo ""
echo "=================================================================="
echo "🎉 Successfully pushed to https://github.com/404adarsh/GDR-AI!"
echo "=================================================================="

