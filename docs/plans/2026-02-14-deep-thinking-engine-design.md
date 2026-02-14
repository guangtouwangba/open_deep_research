# Deep Thinking Engine — Design Document

> Date: 2026-02-14
> Status: Approved
> Base: extends `open_deep_research` repo

## Overview

A long-running thinking agent that transforms complex questions into structured, verified knowledge through a 5-phase pipeline (Anchor → Generate → Adversarial Critique → Verify → Synthesize). Based on [Anthropic's effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents).

Core principles:
- **Anchored questions** — ask based on authoritative sources, not open-ended
- **Adversarial review** — red-team critique before accepting any output
- **Verification trinity** — cross-reference, opposition search, fact-check
- **Expert council** — multi-persona debate for controversial topics
- **Cross-session persistence** — JSON state files bridge context windows

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Skill structure | Hybrid: general engine + domain plugins | Pipeline is universal, anchoring strategies differ by domain |
| State persistence | Global `~/.thinking-agent/` with configurable override | Most thinking tasks are personal, not project-bound |
| Pipeline autonomy | Smart checkpoints (after Phase C + D) | Phases A/B/E are straightforward; C/D need user input |
| Expert council | Auto-detect + manual trigger | Auto when confidence < 0.5 or conflicting findings |
| Domain plugins | 6 built-in | learning, research, investment, tech-eval, content-creation, game-dev |
| Integration with deepsearch | Extend, not fork | Reuse search/LLM infra, replace reflect/verify agents |

## File Structure

```
open_deep_research/
├── install.sh                               # Device init script
├── uninstall.sh                             # Cleanup script
├── src/
│   ├── deepsearch/                          # EXISTING: Untouched
│   │   ├── agents/
│   │   │   ├── planner.py
│   │   │   ├── researcher.py
│   │   │   ├── reflector.py
│   │   │   ├── verifier.py
│   │   │   └── writer.py
│   │   ├── search/
│   │   ├── workflow.py
│   │   ├── state.py
│   │   └── ...
│   └── deep_thinking/                       # NEW: Thinking engine
│       ├── __init__.py
│       ├── config.py                        # Config loading
│       ├── session.py                       # Session CRUD, state persistence
│       ├── state.py                         # ThinkingState, ThinkingTask, Phase enum
│       ├── workflow.py                      # LangGraph workflow with checkpoints
│       ├── cli.py                           # Click CLI: deepthink
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── anchor.py                    # AnchorAgent (wraps PlannerAgent)
│       │   ├── adversarial.py               # AdversarialAgent + Council mode
│       │   └── fact_checker.py              # FactCheckAgent (real web verification)
│       └── domains/
│           ├── __init__.py
│           ├── base.py                      # DomainPlugin interface
│           ├── learning.py
│           ├── research.py
│           ├── investment.py
│           ├── tech_eval.py
│           ├── content_creation.py
│           └── game_dev.py
├── skill/                                   # Claude Code skill
│   ├── SKILL.md
│   └── references/
│       ├── learning-anchors.md
│       ├── research-anchors.md
│       ├── investment-anchors.md
│       ├── tech-evaluation-anchors.md
│       ├── content-creation-anchors.md
│       └── game-dev-anchors.md
└── pyproject.toml                           # MODIFIED: add deep_thinking entry point
```

## Pipeline Design

```
用户输入目标
    │
    ▼
┌──────────────────────────┐
│  Session Init            │
│  - 检测/创建 session     │
│  - 读取 progress.json    │
│  - 识别域名 → 加载 anchor│
│  - 选择下一个 pending task│
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Phase A: 锚定 (自动)     │  ← 从 domain anchor 文件获取权威源
│  Phase B: 生成 (自动)     │  ← 基于权威源生成初版分析 (deepsearch.ResearcherAgent)
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Phase C: 对抗性评审      │  ★ CHECKPOINT 1
│  - 生成严厉批判          │
│  - 检测是否有根本分歧    │
│  - 若有 → 触发 Council   │
│  展示给用户，等待反馈     │
└──────────┬───────────────┘
           │ (用户确认/补充)
           ▼
┌──────────────────────────┐
│  Phase D: 验证三板斧      │  ★ CHECKPOINT 2
│  - 交叉验证 (3 sources)  │
│  - 搜索反对意见          │
│  - 事实核查 (WebSearch)  │
│  展示验证结果，标注 ⚠️    │
└──────────┬───────────────┘
           │ (用户确认/调整)
           ▼
┌──────────────────────────┐
│  Phase E: 综合 (自动)     │
│  - 整合批判 + 验证结果   │
│  - 计算置信度            │
│  - 写入 findings.md      │
│  - 更新 progress.json    │
│  - 选择下一个 task 或结束│
└──────────────────────────┘
```

### Session Init "Getting up to speed"

Every new context window:
1. Check `~/.thinking-agent/sessions/` for active sessions
2. User selects session (or creates new)
3. Read `thinking-progress.json` → understand current state
4. Read `findings.md` (tail) → see recent progress
5. Find first task where phase != "synthesized" → resume there
6. If resuming mid-phase (e.g., "critiqued") → pick up from Phase D
7. If new goal → execute **Goal Decomposition**: split into 5-15 thinking tasks

### Council Auto-Trigger Conditions

- Phase C critique reveals 2+ mutually contradictory authority viewpoints
- Task confidence < 0.5 after initial generation
- Domain config marks topic as inherently multi-school
- User manually requests

## Agent Design

### AnchorAgent (wraps deepsearch.PlannerAgent)

Enhances question generation with authority-source anchoring.

```python
# Current PlannerAgent output:
#   "What is quantitative trading?"
#
# AnchorAgent output:
#   "According to CMU 21-270 and Jim Simons' methodology,
#    what mathematical foundations are required for quantitative trading?"
```

How it works:
- Receives user goal + detected domain
- Loads domain config (e.g., `domains/learning.py`) which provides:
  - Authority sources per sub-topic
  - Anchoring templates ("According to {source}, what...")
  - Anti-patterns ("Don't ask open-ended 'what is X' questions")
- Calls `PlannerAgent.plan()` with enhanced system prompt
- Post-processes questions to ensure each references at least 1 authority source

### AdversarialAgent (replaces deepsearch.ReflectorAgent)

Aggressive red-team critique instead of mild gap analysis.

```python
# Current ReflectorAgent: "gaps": ["need more data on X"]
# AdversarialAgent: "weaknesses": [
#   "This plan is too theoretical — missing practical backtesting frameworks",
#   "Shreve's book is graduate-level math, unrealistic for a 6-month plan",
#   "No mention of transaction costs, which kills most quant strategies"
# ]
```

Three modes:
1. **Standard critique** — harsh expert review
2. **Council mode** (auto-triggered) — 2-3 expert personas debating
3. **User-augmented** — presents critique at checkpoint, user adds challenges

### FactCheckAgent (replaces deepsearch.VerifierAgent)

Real web-based verification instead of content-similarity comparison.

```python
# Current VerifierAgent: compare word overlap between findings
# FactCheckAgent:
# 1. Cross-reference: WebSearch "MIT 18.S096" → confirm course exists
# 2. Opposition: WebSearch "criticism of {claim}"
# 3. Fact-check: WebSearch for book ISBN, tool GitHub repo, etc.
```

Verification pipeline per claim:
1. Extract verifiable claims (book names, courses, tools, statistics)
2. WebSearch each claim → mark `confirmed` / `disputed` / `unverified`
3. Confirmed → record source in `sources.md`
4. Unverified → flag `⚠️`, present at Checkpoint 2

## State Files

### thinking-progress.json

```json
{
  "session_id": "2026-02-14-quantitative-trading",
  "goal": "系统学习量化交易",
  "domain": "learning",
  "created_at": "2026-02-14T10:00:00",
  "updated_at": "2026-02-14T15:30:00",
  "status": "in_progress",
  "tasks": [
    {
      "id": "t1",
      "topic": "数学基础：随机过程与布朗运动",
      "anchors": ["MIT 18.S096", "Shreve《Stochastic Calculus for Finance》"],
      "phase": "synthesized",
      "confidence": 0.85,
      "unverified_claims": [],
      "council_triggered": false,
      "completed_at": "2026-02-14T12:00:00"
    },
    {
      "id": "t2",
      "topic": "策略回测框架选型",
      "anchors": ["QuantConnect docs", "Zipline GitHub"],
      "phase": "critiqued",
      "confidence": 0.6,
      "unverified_claims": ["某Python库待确认"],
      "council_triggered": true,
      "completed_at": null
    }
  ]
}
```

Design choices:
- **JSON not Markdown** for status — model less likely to corrupt structured data
- **Phase enum**: `pending → anchored → generated → critiqued → verified → synthesized`
- **Never delete tasks** — only update phase/status
- Strongly guarded: "It is unacceptable to remove or edit task definitions"

### findings.md

Append-only, structured by task:

```markdown
# Findings: 系统学习量化交易

## t1: 数学基础 [SYNTHESIZED ✅ confidence: 0.85]

### 权威源
- MIT 18.S096 Topics in Mathematics with Applications in Finance
- Shreve《Stochastic Calculus for Finance II》Chapter 3-4

### 核心结论
(Phase B + E output)

### 红军批判
(Phase C output)

### 验证结果
- ✅ MIT 18.S096 confirmed: https://ocw.mit.edu/...
- ✅ Shreve book ISBN: 978-0387401010
- ⚠️ "Hull的书配合使用" — 未指定具体章节

### 专家委员会
(Council debate summary, if triggered)
```

### sources.md

Verified source registry, prevents re-verification:

```markdown
# Verified Sources

| Source | Type | Verified | URL |
|--------|------|----------|-----|
| MIT 18.S096 | Course | ✅ 2026-02-14 | https://ocw.mit.edu/... |
| Shreve Book | Book | ✅ 2026-02-14 | ISBN 978-0387401010 |
```

## Domain Plugins

### Plugin Interface

```python
class DomainPlugin:
    name: str                          # "learning", "investment", etc.
    detection_keywords: List[str]      # Auto-detect from user goal
    authority_sources: Dict[str, List[str]]  # sub-topic → sources
    anchor_templates: List[str]        # Prompt templates for anchoring
    verification_rules: List[str]      # Domain-specific fact-check rules
    council_experts: List[Expert]      # Pre-configured expert personas
    downstream_skills: List[str]       # Links to existing Claude Code skills
```

### Six Domains

| Domain | Authority Sources | Council Experts | Downstream Skills |
|--------|------------------|-----------------|-------------------|
| **learning** | MIT OCW, CMU courses, Google/Meta levels | 学院派教授 / 工业界工程师 / 自学独立开发者 | — |
| **research** | arXiv, Google Scholar, Nature, IEEE | 领域权威 / 方法论批评者 / 实践应用者 | — |
| **investment** | SEC, 巨潮资讯, Wind, Bloomberg | 价值投资派 / 量化派 / 宏观对冲派 | deep-investment-thinker, investment-advisor |
| **tech-eval** | Official docs, GitHub, ThoughtWorks Radar, CNCF | 架构师 / SRE / 开发者 | — |
| **content-creation** | 平台创作者文档, 新榜/蝉妈妈, 头部创作者 | 内容策划 / 算法专家 / 变现专家 | twitter-content-creator, wechat-article-writer |
| **game-dev** | GDC Vault, Unity/Unreal docs, postmortems | 游戏设计师 / 技术美术 / 独立开发者 | — |

## CLI Design

```bash
# New session
deepthink "系统学习量化交易，参考CMU和MIT课程体系"

# Specify domain
deepthink "Kafka vs RabbitMQ" --domain tech-eval

# Resume session
deepthink --resume 2026-02-14-quantitative-trading

# List sessions
deepthink --list

# Session status
deepthink --status 2026-02-14-quantitative-trading

# Full auto (skip checkpoints)
deepthink "..." --auto

# Depth control
deepthink "..." --depth comprehensive
```

### Checkpoint Interaction (non --auto)

```
$ deepthink "系统学习量化交易"

🎯 Goal decomposed into 8 tasks
📂 Session: ~/.thinking-agent/sessions/2026-02-14-quantitative-trading/

━━━ Task 1/8: 数学基础 ━━━
[Phase A] Anchoring to MIT 18.S096, Shreve... ✅
[Phase B] Generating initial analysis... ✅

★ CHECKPOINT: Adversarial Critique
┌──────────────────────────────────────────┐
│ 🔴 批判 1: 计划过于理论化               │
│ 🔴 批判 2: Shreve的书不现实             │
│ 🔴 批判 3: 未提及编程基础               │
│ ⚡ Council NOT triggered (confidence 0.7)│
└──────────────────────────────────────────┘
> Add your own challenges (Enter to skip): _

★ CHECKPOINT: Verification Results
┌──────────────────────────────────────────┐
│ ✅ MIT 18.S096 — confirmed               │
│ ✅ Shreve book — ISBN verified            │
│ ⚠️ "Python量化实战2024版" — NOT FOUND    │
└──────────────────────────────────────────┘
> Accept? [Y/n/edit]: _

[Phase E] Synthesizing... ✅ (confidence: 0.85)
━━━ Task 1 complete. Moving to Task 2... ━━━
```

## install.sh

```bash
#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$HOME/.claude/skills/thinking-engine"
STATE_DIR="$HOME/.thinking-agent"

echo "=== Deep Thinking Agent Installer ==="

# 1. Install Python package
echo "[1/4] Installing deep_thinking package..."
cd "$REPO_DIR"
uv sync

# 2. Symlink skill to Claude Code
echo "[2/4] Installing Claude Code skill..."
ln -sfn "$REPO_DIR/skill" "$SKILL_DIR"

# 3. Create global state directory
echo "[3/4] Creating state directory..."
mkdir -p "$STATE_DIR/sessions"

# 4. Init config
if [ ! -f "$STATE_DIR/config.json" ]; then
  echo "[4/4] Creating default config..."
  cat > "$STATE_DIR/config.json" << 'EOF'
{
  "default_depth": "balanced",
  "default_domain": "auto",
  "language": "zh",
  "checkpoints": true,
  "council_auto_trigger": true,
  "council_confidence_threshold": 0.5
}
EOF
else
  echo "[4/4] Config exists, skipping."
fi

echo ""
echo "✅ Installation complete!"
echo "   Skill: $SKILL_DIR"
echo "   State: $STATE_DIR"
echo "   CLI:   deepthink \"your topic\""
```

## Reuse vs Build

| Component | Source | Action |
|-----------|--------|--------|
| Search infrastructure | `deepsearch.search` | Reuse as-is |
| LLM integration | `deepsearch` (LangChain) | Reuse as-is |
| PlannerAgent | `deepsearch.agents.planner` | Wrap in AnchorAgent |
| ResearcherAgent | `deepsearch.agents.researcher` | Reuse in Phase B |
| WriterAgent | `deepsearch.agents.writer` | Reuse in Phase E |
| ReflectorAgent | `deepsearch.agents.reflector` | **Replace** with AdversarialAgent |
| VerifierAgent | `deepsearch.agents.verifier` | **Replace** with FactCheckAgent |
| LangGraph workflow | `deepsearch.workflow` | **New** workflow with checkpoints |
| CLI | `deepsearch.cli` | **New** CLI with Rich UI |
| State persistence | — | **Build** from scratch |
| Domain plugins | — | **Build** from scratch |
| Claude Code skill | — | **Build** from scratch |

## Implementation Phases

### Phase 1: Foundation
1. `src/deep_thinking/state.py` — ThinkingState, ThinkingTask, Phase enum
2. `src/deep_thinking/config.py` — Config loading
3. `src/deep_thinking/session.py` — Session CRUD, JSON persistence
4. `src/deep_thinking/domains/base.py` — DomainPlugin interface
5. `pyproject.toml` — Add package + CLI entry point

### Phase 2: Agents
6. `src/deep_thinking/agents/anchor.py` — AnchorAgent
7. `src/deep_thinking/agents/adversarial.py` — AdversarialAgent + Council
8. `src/deep_thinking/agents/fact_checker.py` — FactCheckAgent

### Phase 3: Workflow
9. `src/deep_thinking/workflow.py` — LangGraph workflow with checkpoints
10. `src/deep_thinking/cli.py` — CLI with Rich terminal UI

### Phase 4: Domains
11. `domains/learning.py`
12. `domains/research.py`
13. `domains/investment.py`
14. `domains/tech_eval.py`
15. `domains/content_creation.py`
16. `domains/game_dev.py`

### Phase 5: Skill & Install
17. `skill/SKILL.md` + 6 reference files
18. `install.sh` + `uninstall.sh`

### Phase 6: Test & Iterate
19. E2E test: `deepthink "系统学习量化交易"` full pipeline
20. Cross-session test: kill mid-task, resume, verify state integrity
