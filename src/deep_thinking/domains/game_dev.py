"""Game development domain plugin — game design and production anchoring."""

from deep_thinking.domains.base import DomainPlugin, Expert, register_domain

GAME_DEV_DOMAIN = DomainPlugin(
    name="game-dev",
    display_name="游戏制作",
    detection_keywords=[
        "游戏", "game", "unity", "unreal", "godot",
        "关卡", "玩法", "美术", "像素", "3d", "2d",
        "独立游戏", "indie", "steam", "发行",
        "game design", "level design", "gameplay",
        "引擎", "engine", "shader", "渲染",
    ],
    authority_sources={
        "游戏设计": [
            "GDC Vault (Game Developers Conference talks)",
            "Jesse Schell《The Art of Game Design》",
            "Raph Koster《A Theory of Fun for Game Design》",
            "MDA Framework (Mechanics, Dynamics, Aesthetics)",
        ],
        "游戏引擎": [
            "Unity 官方文档与 Best Practices",
            "Unreal Engine 官方文档",
            "Godot 官方文档",
            "各引擎 GitHub issues 和 release notes",
        ],
        "技术美术": [
            "Real-Time Rendering (Akenine-Möller)",
            "GPU Gems series",
            "Shadertoy 社区",
            "GDC 技术美术 track",
        ],
        "独立游戏开发": [
            "Steam Spy / SteamDB 销量数据",
            "Gamasutra/Game Developer postmortems",
            "itch.io 社区数据",
            "成功独立游戏的 GDC postmortem",
        ],
        "项目管理": [
            "Extra Credits (游戏设计教育频道)",
            "Jason Schreier《Blood, Sweat, and Pixels》",
            "Agile/Scrum in game development (Noel Llopis)",
        ],
    },
    anchor_templates=[
        "参考 {source} 的最佳实践和 GDC postmortem 案例，分析 {topic}",
        "基于 {sources} 的官方文档和性能指南，评估 {topic} 的技术方案",
        "根据 {source} 的设计理论，结合成功游戏案例，设计 {topic}",
    ],
    verification_rules=[
        "Game must exist on Steam/App Store/itch.io",
        "Engine feature must be in official documentation or changelog",
        "GDC talk must be findable in GDC Vault",
        "Sales data must cite SteamSpy/SteamDB or official announcements",
    ],
    council_experts=[
        Expert(
            name="游戏设计师",
            perspective="核心玩法循环、趣味性、玩家心理",
            anchor_source="MDA Framework / 成功游戏案例分析",
            style="创意优先，强调fun factor",
        ),
        Expert(
            name="技术美术/程序",
            perspective="性能优化、渲染管线、跨平台兼容",
            anchor_source="引擎官方文档 / GPU Gems / Real-Time Rendering",
            style="技术导向，关注帧率和内存",
        ),
        Expert(
            name="独立开发者/制作人",
            perspective="范围控制、成本、发行策略、上线节奏",
            anchor_source="Gamasutra postmortems / Steam 发行数据",
            style="务实，强调scope和deadline",
        ),
    ],
    multi_school_topics=["引擎选择", "art style", "美术风格", "发行策略", "玩法类型"],
)

register_domain(GAME_DEV_DOMAIN)
