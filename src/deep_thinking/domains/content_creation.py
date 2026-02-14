"""Content creation domain plugin — 自媒体制作 anchoring."""

from deep_thinking.domains.base import DomainPlugin, Expert, register_domain

CONTENT_CREATION_DOMAIN = DomainPlugin(
    name="content-creation",
    display_name="自媒体制作",
    detection_keywords=[
        "自媒体", "公众号", "小红书", "抖音", "B站", "视频号",
        "content", "creator", "influencer", "youtube", "twitter",
        "涨粉", "流量", "爆款", "选题", "运营", "变现",
        "博主", "UP主", "短视频", "直播",
    ],
    authority_sources={
        "平台算法": [
            "各平台官方创作者中心文档",
            "抖音创作者学院",
            "小红书蒲公英平台规则",
            "YouTube Creator Academy",
            "B站创作学院",
        ],
        "数据分析": [
            "新榜 (newrank.cn) 数据报告",
            "蝉妈妈 (chanmama.com) 分析",
            "飞瓜数据",
            "Social Blade (YouTube/Twitter analytics)",
        ],
        "内容策略": [
            "头部创作者公开分享的方法论",
            "平台官方年度创作者报告",
            "内容营销经典：《Made to Stick》《Contagious》",
        ],
        "变现模式": [
            "平台官方商业化文档",
            "品牌合作定价参考 (星图/蒲公英)",
            "知识付费平台规则 (知识星球/小报童)",
        ],
    },
    anchor_templates=[
        "参考 {source} 的官方推荐算法文档，分析 {topic} 的最优内容策略",
        "基于 {sources} 的数据报告，结合头部创作者案例，评估 {topic}",
        "根据 {source} 的商业化规则，设计 {topic} 的变现路径",
    ],
    verification_rules=[
        "Platform rules must link to official creator documentation",
        "Follower/view counts can be verified via platform profiles",
        "Revenue claims must specify time period and platform",
        "Algorithm claims must cite official announcements, not rumors",
    ],
    council_experts=[
        Expert(
            name="内容策划专家",
            perspective="选题策划、内容质量、用户心理",
            anchor_source="爆款内容分析、用户调研数据",
            style="创意导向，强调差异化",
        ),
        Expert(
            name="平台算法研究者",
            perspective="推荐机制、流量分发、标签体系",
            anchor_source="平台官方文档、逆向分析",
            style="数据驱动，强调可测量",
        ),
        Expert(
            name="商业变现专家",
            perspective="商业模式、品牌合作、长期价值",
            anchor_source="MCN机构运营数据、品牌方预算",
            style="务实，关注ROI和可持续性",
        ),
    ],
    downstream_skills=[
        "twitter-content-creator",
        "wechat-article-writer",
        "social-content",
    ],
    multi_school_topics=["平台选择", "内容方向", "变现模式"],
)

register_domain(CONTENT_CREATION_DOMAIN)
