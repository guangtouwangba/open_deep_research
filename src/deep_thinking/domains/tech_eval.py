"""Tech evaluation domain plugin — technology selection and architecture decisions."""

from deep_thinking.domains.base import DomainPlugin, Expert, register_domain

TECH_EVAL_DOMAIN = DomainPlugin(
    name="tech-eval",
    display_name="技术选型",
    detection_keywords=[
        "选型", "对比", "vs", "还是", "技术栈", "架构",
        "evaluate", "compare", "versus", "choose", "select",
        "迁移", "替代", "方案", "benchmark",
        "kafka", "redis", "mysql", "postgresql", "mongodb",
        "react", "vue", "kubernetes", "docker",
    ],
    authority_sources={
        "数据库": [
            "DB-Engines Ranking",
            "各数据库官方 Benchmark 文档",
            "Jepsen consistency analysis reports",
            "Use the Database Advisor (Percona/PlanetScale blogs)",
        ],
        "消息队列": [
            "Confluent (Kafka) 官方文档与 benchmark",
            "RabbitMQ 官方 Performance 文档",
            "Pulsar 官方对比文档",
            "LinkedIn/Uber 技术博客中的实战经验",
        ],
        "前端框架": [
            "State of JS Survey 年度报告",
            "各框架官方文档 (React/Vue/Svelte)",
            "Chrome Aurora team performance reports",
            "Vercel/Netlify 技术博客",
        ],
        "云原生": [
            "CNCF Landscape and Annual Survey",
            "ThoughtWorks Technology Radar",
            "Kubernetes 官方文档",
            "各云厂商最佳实践文档 (AWS Well-Architected, GCP)",
        ],
        "编程语言": [
            "Stack Overflow Developer Survey",
            "GitHub Octoverse Report",
            "各语言官方 benchmark (TechEmpower FrameworkBenchmarks)",
            "Computer Language Benchmarks Game",
        ],
    },
    anchor_templates=[
        "对比 {sources} 的官方 benchmark 数据，评估 {topic}",
        "参考 {source} 的最佳实践文档和生产环境使用报告，分析 {topic}",
        "基于 {sources} 的真实案例，从性能/成本/运维三个维度对比 {topic}",
    ],
    verification_rules=[
        "Benchmark must link to reproducible test methodology",
        "GitHub repo must exist and show recent activity",
        "Performance claims must specify hardware/config used",
        "Adoption claims must cite specific companies/projects using it",
    ],
    council_experts=[
        Expert(
            name="系统架构师",
            perspective="可维护性、团队能力匹配、长期演进",
            anchor_source="Martin Fowler/ThoughtWorks",
            style="谨慎，关注技术债",
        ),
        Expert(
            name="SRE工程师",
            perspective="运维成本、可观测性、故障恢复",
            anchor_source="Google SRE Book / 生产事故复盘",
            style="悲观，关注最坏情况",
        ),
        Expert(
            name="一线开发者",
            perspective="开发体验、学习曲线、生态完善度",
            anchor_source="Stack Overflow / GitHub issues / 社区活跃度",
            style="务实，关注日常效率",
        ),
    ],
    multi_school_topics=["vs", "还是", "选择", "哪个好", "compare"],
)

register_domain(TECH_EVAL_DOMAIN)
