---
name: thinking-engine
description: >
  深度思考引擎——将任何复杂问题转化为结构化、经过验证的知识。通过5阶段管线
  （锚定权威源→生成→对抗性评审→验证三板斧→综合修正）进行深度分析，支持跨session
  持续迭代。当用户说"深度思考"、"帮我系统分析"、"制定学习计划"、"技术选型分析"、
  "深度研究"、"think deeply"、"我要系统学习"、"对比分析"、"帮我深入分析"、
  "帮我想清楚"时触发。也可通过 deepthink 或 dt 命令调用。支持6个领域：学习计划、
  通用研究、投资分析、技术选型、自媒体制作、游戏制作。
---

# Deep Thinking Engine

## Overview

A long-running thinking agent that transforms complex questions into structured, verified
knowledge through a 5-phase pipeline. Based on Anthropic's harness patterns for long-running agents.

**Core principle:** Don't ask open-ended questions — anchor to authoritative sources.
Don't trust first drafts — adversarial critique + fact-check before accepting.

## Quick Start

```bash
# Via CLI
deepthink "系统学习量化交易，参考CMU和MIT课程体系"
deepthink "Kafka vs RabbitMQ" --domain tech-eval
deepthink --resume SESSION_ID
deepthink --list
```

## 5-Phase Pipeline

```
Phase A: 锚定 (auto)     → Anchor questions to authoritative sources
Phase B: 生成 (auto)     → Generate analysis based on anchored sources
Phase C: 对抗性评审      → ★ CHECKPOINT 1: Red-team critique + optional council
Phase D: 验证三板斧      → ★ CHECKPOINT 2: Cross-reference, opposition, fact-check
Phase E: 综合 (auto)     → Synthesize with critique + verification feedback
```

## Domains

6 built-in domains, auto-detected or manually specified:

| Domain | Flag | Use When |
|--------|------|----------|
| learning | `--domain learning` | Study plans, skill development |
| research | `--domain research` | Academic/industry research |
| investment | `--domain investment` | Investment analysis, quantitative trading |
| tech-eval | `--domain tech-eval` | Technology comparison, architecture decisions |
| content-creation | `--domain content-creation` | 自媒体, content strategy |
| game-dev | `--domain game-dev` | Game design, engine selection |

Domain details: see `references/` directory for anchor sources per domain.

## State Files

Sessions persist at `~/.thinking-agent/sessions/{session-id}/`:

- **thinking-progress.json** — Task list with phase status, confidence, verified claims (JSON)
- **findings.md** — Accumulated verified knowledge (append-only Markdown)
- **sources.md** — Verified source registry (prevents re-verification)
- **report.md** — Final comprehensive report (generated on completion)

## Integration with Existing Skills

The thinking engine bridges to specialized skills:

- **investment domain** → `deep-investment-thinker`, `investment-advisor`, `investment-asset-allocation`
- **content-creation domain** → `twitter-content-creator`, `wechat-article-writer`

## Key Features

### Anchored Questions
Every question references specific authoritative sources to constrain AI's search space:
- ❌ "帮我生成一个学习计算机科学的计划"
- ✅ "参考 MIT 6.004 和 CMU 15-213 的课程大纲，结合 Google L5 工程师能力模型，制定6个月学习路径"

### Adversarial Critique
Red-team critique that attacks weak thinking, not mild gap analysis.

### Expert Council
Auto-triggered when confidence < 0.5 or conflicting findings detected.
Simulates domain experts debating from different schools of thought.

### Verification Trinity
1. Cross-reference: 3 independent sources per key claim
2. Opposition search: What do critics say?
3. Fact-check: Books, courses, tools verified via web search

## References

Domain-specific anchor sources and verification strategies:

- [learning-anchors.md](references/learning-anchors.md) — University courses, engineering levels
- [research-anchors.md](references/research-anchors.md) — Academic papers, industry reports
- [investment-anchors.md](references/investment-anchors.md) — Financial frameworks, bridges to investment skills
- [tech-evaluation-anchors.md](references/tech-evaluation-anchors.md) — Benchmarks, official docs
- [content-creation-anchors.md](references/content-creation-anchors.md) — Platform algorithms, creator strategies
- [game-dev-anchors.md](references/game-dev-anchors.md) — GDC talks, engine docs, postmortems
