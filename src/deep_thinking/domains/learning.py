"""Learning domain plugin — study plans anchored to top universities and industry levels."""

from deep_thinking.domains.base import DomainPlugin, Expert, register_domain

LEARNING_DOMAIN = DomainPlugin(
    name="learning",
    display_name="学习计划",
    detection_keywords=[
        "学习", "学", "入门", "教程", "课程", "路线", "路径",
        "learn", "study", "tutorial", "roadmap", "curriculum",
        "从零开始", "系统学习", "掌握", "精通",
    ],
    authority_sources={
        "计算机基础": [
            "MIT 6.004 Computation Structures",
            "CMU 15-213 Introduction to Computer Systems (CSAPP)",
            "Stanford CS106B Programming Abstractions",
        ],
        "算法": [
            "MIT 6.006 Introduction to Algorithms",
            "Stanford CS161 Design and Analysis of Algorithms",
            "CLRS《Introduction to Algorithms》",
            "Sedgewick《Algorithms》",
        ],
        "系统设计": [
            "MIT 6.824 Distributed Systems",
            "CMU 15-440 Distributed Systems",
            "Martin Kleppmann《Designing Data-Intensive Applications》",
            "Google SRE Book",
        ],
        "机器学习": [
            "Stanford CS229 Machine Learning",
            "fast.ai Practical Deep Learning",
            "CMU 10-701 Introduction to Machine Learning",
            "Andrew Ng Coursera ML Specialization",
        ],
        "数学": [
            "MIT 18.06 Linear Algebra (Gilbert Strang)",
            "MIT 18.S096 Topics in Mathematics with Applications in Finance",
            "Stanford STATS 110 Probability",
        ],
        "编程语言": [
            "Official language documentation",
            "Language-specific style guides (Google, Airbnb)",
            "The language's most-starred GitHub learning repos",
        ],
    },
    anchor_templates=[
        "参考 {sources} 的课程大纲，为 {topic} 制定具体的学习路径，列出教材章节和实验项目",
        "基于 {source} 的教学体系，结合 Google L5 级别工程师的能力模型，分析 {topic} 的核心知识点",
        "对比 {sources} 的教学方法，找出 {topic} 最高效的学习顺序",
    ],
    verification_rules=[
        "Course must exist on university's official website or OCW",
        "Book must have ISBN and be findable on Amazon/Google Books",
        "Online resource must have a working URL",
        "Claimed difficulty level must match course prerequisites",
    ],
    council_experts=[
        Expert(
            name="学院派教授",
            perspective="理论基础与数学严谨性",
            anchor_source="MIT/CMU/Stanford 课程体系",
            style="严谨，强调基础",
        ),
        Expert(
            name="大厂资深工程师",
            perspective="工业界实战能力",
            anchor_source="Google/Meta/Amazon 工程实践",
            style="务实，强调产出",
        ),
        Expert(
            name="自学成才的独立开发者",
            perspective="最短路径和实用主义",
            anchor_source="开源社区、个人项目经验",
            style="激进，反对过度理论",
        ),
    ],
    multi_school_topics=["路线", "路径", "方法", "顺序", "先学什么"],
)

register_domain(LEARNING_DOMAIN)
