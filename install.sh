#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$HOME/.claude/skills/thinking-engine"
STATE_DIR="$HOME/.thinking-agent"

echo "=== Deep Thinking Agent Installer ==="
echo ""

# 1. Install Python package
echo "[1/4] Installing Python packages..."
cd "$REPO_DIR"
if command -v uv &> /dev/null; then
    uv sync
else
    pip install -e .
fi

# 2. Symlink skill to Claude Code
echo "[2/4] Installing Claude Code skill..."
mkdir -p "$HOME/.claude/skills"
ln -sfn "$REPO_DIR/skill" "$SKILL_DIR"
echo "      → $SKILL_DIR"

# 3. Create global state directory
echo "[3/4] Creating state directory..."
mkdir -p "$STATE_DIR/sessions"
echo "      → $STATE_DIR"

# 4. Init config if not exists
if [ ! -f "$STATE_DIR/config.json" ]; then
    echo "[4/4] Creating default config..."
    cat > "$STATE_DIR/config.json" << 'EOF'
{
  "default_depth": "balanced",
  "default_domain": "auto",
  "language": "zh",
  "checkpoints": true,
  "council_auto_trigger": true,
  "council_confidence_threshold": 0.5,
  "max_tasks": 15
}
EOF
else
    echo "[4/4] Config already exists, skipping."
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "   Skill:    $SKILL_DIR"
echo "   State:    $STATE_DIR"
echo "   CLI:      deepthink \"your topic\""
echo "   Shortcut: dt \"your topic\""
echo ""
echo "   Examples:"
echo "     deepthink \"系统学习量化交易，参考CMU和MIT课程体系\""
echo "     deepthink \"Kafka vs RabbitMQ 技术选型\" --domain tech-eval"
echo "     deepthink --list"
echo "     deepthink --resume SESSION_ID"
