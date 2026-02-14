"""Research domain plugin — general academic/industry research anchoring."""

from deep_thinking.domains.base import DomainPlugin, Expert, register_domain

RESEARCH_DOMAIN = DomainPlugin(
    name="research",
    display_name="通用研究",
    detection_keywords=[
        "研究", "调研", "分析", "综述", "论文", "报告",
        "research", "survey", "analysis", "review", "investigate",
        "对比", "评估", "现状", "趋势",
    ],
    authority_sources={
        "学术研究": [
            "arXiv preprints",
            "Google Scholar top-cited papers",
            "Nature/Science review articles",
            "IEEE/ACM conference proceedings",
        ],
        "行业研究": [
            "Gartner Magic Quadrant",
            "McKinsey/BCG industry reports",
            "行业白皮书",
            "上市公司年报/招股书",
        ],
        "技术趋势": [
            "ThoughtWorks Technology Radar",
            "CNCF Landscape",
            "Stack Overflow Developer Survey",
            "GitHub Octoverse Report",
        ],
    },
    anchor_templates=[
        "基于 {sources} 近3年的研究成果，系统分析 {topic}",
        "参考 {source} 的方法论框架，评估 {topic} 的现状与趋势",
        "以 {sources} 为基准，对比分析 {topic} 的不同方案",
    ],
    verification_rules=[
        "Paper must have DOI or arXiv ID",
        "Statistics must link to original report/survey",
        "Industry report must identify publisher and date",
        "Claims about trends must cite data from last 2 years",
    ],
    council_experts=[
        Expert(
            name="领域权威学者",
            perspective="学术严谨性与理论深度",
            anchor_source="peer-reviewed publications",
            style="严谨，数据驱动",
        ),
        Expert(
            name="方法论批评者",
            perspective="研究方法与偏见识别",
            anchor_source="统计学与实验设计",
            style="怀疑，追问因果",
        ),
        Expert(
            name="实践应用者",
            perspective="研究成果的实际落地价值",
            anchor_source="产业实践案例",
            style="务实，关注ROI",
        ),
    ],
    multi_school_topics=["争议", "辩论", "对立", "分歧"],
)

register_domain(RESEARCH_DOMAIN)
