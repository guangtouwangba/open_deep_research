#!/bin/bash
set -e

SKILL_DIR="$HOME/.claude/skills/thinking-engine"
STATE_DIR="$HOME/.thinking-agent"

echo "=== Deep Thinking Agent Uninstaller ==="
echo ""

# 1. Remove skill symlink
if [ -L "$SKILL_DIR" ] || [ -d "$SKILL_DIR" ]; then
    echo "[1/2] Removing Claude Code skill..."
    rm -rf "$SKILL_DIR"
    echo "      Removed: $SKILL_DIR"
else
    echo "[1/2] Skill not found, skipping."
fi

# 2. Ask about state directory
if [ -d "$STATE_DIR" ]; then
    echo "[2/2] State directory found: $STATE_DIR"
    read -p "      Delete all thinking sessions? (y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        rm -rf "$STATE_DIR"
        echo "      Removed: $STATE_DIR"
    else
        echo "      Keeping state directory."
    fi
else
    echo "[2/2] No state directory found."
fi

echo ""
echo "✅ Uninstall complete."
echo "   Note: Python package still installed. Run 'pip uninstall deepsearch' to remove."
