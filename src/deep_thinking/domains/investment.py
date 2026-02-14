"""Investment domain plugin — bridges to existing investment skills."""

from deep_thinking.domains.base import DomainPlugin, Expert, register_domain

INVESTMENT_DOMAIN = DomainPlugin(
    name="investment",
    display_name="投资分析",
    detection_keywords=[
        "投资", "股票", "基金", "理财", "量化", "交易",
        "invest", "stock", "fund", "trading", "quant",
        "估值", "财报", "持仓", "仓位", "对冲", "套利",
        "黄金", "BTC", "ETH", "加密", "crypto",
    ],
    authority_sources={
        "价值投资": [
            "巴菲特致股东的信 (Berkshire Hathaway Annual Letters)",
            "Benjamin Graham《The Intelligent Investor》",
            "Howard Marks《The Most Important Thing》",
            "Seth Klarman《Margin of Safety》",
        ],
        "量化交易": [
            "CMU 21-270 Introduction to Mathematical Finance",
            "Shreve《Stochastic Calculus for Finance》",
            "Ernest Chan《Quantitative Trading》",
            "QuantConnect/Zipline 官方文档",
        ],
        "宏观分析": [
            "Ray Dalio《Principles for Navigating Big Debt Crises》",
            "IMF World Economic Outlook",
            "中国人民银行货币政策报告",
            "美联储 FOMC 会议纪要",
        ],
        "风险管理": [
            "Nassim Taleb《Antifragile》《Black Swan》",
            "Kelly Criterion 原始论文",
            "VaR and Expected Shortfall frameworks",
        ],
        "A股": [
            "巨潮资讯网 (cninfo.com.cn)",
            "上交所/深交所公告",
            "Wind/Choice 金融终端数据",
            "中国证监会政策文件",
        ],
    },
    anchor_templates=[
        "根据 {sources} 的分析框架，评估 {topic}",
        "基于 {source} 的方法论，结合最近3期财报数据，分析 {topic}",
        "参考 {sources} 的投资理念，从多空两面分析 {topic}",
    ],
    verification_rules=[
        "Financial data must match official filings (SEC/巨潮)",
        "Book/paper must exist and be correctly attributed",
        "Historical performance claims must cite specific time periods",
        "Regulatory references must link to official government sources",
    ],
    council_experts=[
        Expert(
            name="价值投资者",
            perspective="长期价值、安全边际、护城河",
            anchor_source="巴菲特/格雷厄姆/芒格",
            style="保守，强调安全边际",
        ),
        Expert(
            name="量化分析师",
            perspective="数学模型、统计套利、因子分析",
            anchor_source="西蒙斯/AQR/Two Sigma",
            style="数据驱动，不信故事",
        ),
        Expert(
            name="风险控制专家",
            perspective="尾部风险、反脆弱、仓位管理",
            anchor_source="塔勒布/Bridgewater风控体系",
            style="悲观，永远先看风险",
        ),
    ],
    downstream_skills=[
        "deep-investment-thinker",
        "investment-advisor",
        "investment-analyst-brain",
        "investment-asset-allocation",
    ],
    multi_school_topics=["该不该买", "抄底", "选股", "策略", "配置"],
)

register_domain(INVESTMENT_DOMAIN)
