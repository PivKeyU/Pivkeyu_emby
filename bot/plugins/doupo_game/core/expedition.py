"""Data-driven multi-step expedition rules for the Doupo game."""

from __future__ import annotations

from typing import Any


EXPEDITION_REGIONS: list[dict[str, Any]] = [
    {
        "key": "magic_beast_mountains",
        "name": "魔兽山脉",
        "description": "林海中药材与低阶魔核丰富，适合初次游历。",
        "realm_stage_min": "斗之气",
        "recommended_power": 1200,
        "entry_gold": 0,
        "max_steps": 4,
        "event_keys": ["beast_tracks", "herb_valley", "hidden_cave", "lost_mercenary"],
        "completion_bonus": {
            "douqi": 70,
            "gold": 28,
            "items": {"monster_core_low": 1},
        },
    },
    {
        "key": "tagor_desert",
        "name": "塔戈尔沙漠",
        "description": "高温与蛇人巡逻并存，能寻到护火药材和异火踪迹。",
        "realm_stage_min": "斗者",
        "recommended_power": 13500,
        "entry_gold": 40,
        "max_steps": 5,
        "event_keys": ["desert_storm", "snake_patrol", "fire_vein", "desert_caravan"],
        "completion_bonus": {
            "douqi": 130,
            "gold": 55,
            "items": {"qinglian_fire_map": 1},
        },
    },
    {
        "key": "black_corner",
        "name": "黑角域",
        "description": "没有规矩的险地，回报丰厚，但每一步都可能遭到截杀。",
        "realm_stage_min": "大斗师",
        "recommended_power": 34000,
        "entry_gold": 100,
        "max_steps": 6,
        "event_keys": ["black_market", "road_ambush", "ancient_ruin", "fire_vein"],
        "completion_bonus": {
            "douqi": 220,
            "gold": 110,
            "items": {"monster_core_mid": 1, "mitel_auction_token": 1},
        },
    },
]


EXPEDITION_EVENTS: dict[str, dict[str, Any]] = {
    "beast_tracks": {
        "title": "密林兽踪",
        "story": "潮湿泥地上留着新鲜爪印，前方灌木间传来低沉兽吼。",
        "choices": [
            {
                "key": "detour",
                "label": "绕路采集",
                "description": "避开正面冲突，沿林缘搜集药材。",
                "risk": "稳妥",
                "base_chance": 100,
                "success": {"damage": [0, 3], "douqi": [8, 16], "gold": [2, 7], "danger": -1, "drops": {"ice_spirit_flame_grass": 45}},
            },
            {
                "key": "hunt",
                "label": "设伏猎杀",
                "description": "判断行进路线后设伏，正面争夺魔核。",
                "risk": "均衡",
                "base_chance": 74,
                "success": {"damage": [4, 10], "douqi": [25, 48], "gold": [8, 18], "danger": 1, "drops": {"monster_core_low": 78}},
                "failure": {"damage": [17, 28], "douqi": [4, 10], "gold": [0, 3], "danger": 2},
            },
            {
                "key": "track_nest",
                "label": "追入巢穴",
                "description": "追踪到巢穴深处，赌一次稀有收获。",
                "risk": "凶险",
                "base_chance": 56,
                "success": {"damage": [8, 15], "douqi": [40, 72], "gold": [14, 28], "danger": 2, "drops": {"monster_core_low": 100, "monster_core_mid": 24}},
                "failure": {"damage": [24, 38], "douqi": [5, 14], "gold": [0, 4], "danger": 3},
            },
        ],
    },
    "herb_valley": {
        "title": "幽谷药香",
        "story": "山风送来浓郁药香，谷底灵草成片，岩壁上却盘踞着守药魔兽。",
        "choices": [
            {"key": "edge", "label": "谷口采药", "description": "只取外围成熟药草。", "risk": "稳妥", "base_chance": 100, "success": {"damage": [0, 2], "douqi": [6, 13], "gold": [1, 5], "danger": -1, "drops": {"ice_spirit_flame_grass": 80, "snake_shed_grass": 38}}},
            {"key": "lure", "label": "引兽离谷", "description": "制造声响引开魔兽，再进入谷底。", "risk": "均衡", "base_chance": 70, "success": {"damage": [3, 8], "douqi": [18, 35], "gold": [5, 12], "danger": 1, "drops": {"blood_lotus_essence": 70, "seven_leaf_lotus": 18}}, "failure": {"damage": [14, 24], "douqi": [3, 8], "danger": 2}},
            {"key": "challenge", "label": "强夺灵药", "description": "击败守药魔兽，搜尽谷底。", "risk": "凶险", "base_chance": 54, "success": {"damage": [8, 14], "douqi": [35, 62], "gold": [10, 20], "danger": 2, "drops": {"blood_lotus_essence": 100, "seven_leaf_lotus": 42}}, "failure": {"damage": [23, 36], "douqi": [4, 10], "danger": 3}},
        ],
    },
    "hidden_cave": {
        "title": "前人洞府",
        "story": "藤蔓后露出半扇石门，门内斗气流转，禁制尚未完全消散。",
        "choices": [
            {"key": "meditate", "label": "门外感悟", "description": "不触碰禁制，只借残余斗气修炼。", "risk": "稳妥", "base_chance": 100, "success": {"damage": [0, 2], "douqi": [20, 34], "gold": [0, 3], "danger": -1}},
            {"key": "probe", "label": "破解禁制", "description": "寻找禁制薄弱处进入外室。", "risk": "均衡", "base_chance": 68, "success": {"damage": [3, 9], "douqi": [26, 48], "gold": [12, 24], "danger": 1, "drops": {"black_iron_ore": 65, "flame_method_fragment": 12}}, "failure": {"damage": [16, 27], "douqi": [5, 10], "danger": 2}},
            {"key": "break", "label": "强破石门", "description": "以斗技撼动整座禁制。", "risk": "凶险", "base_chance": 50, "success": {"damage": [9, 16], "douqi": [45, 78], "gold": [20, 38], "danger": 2, "drops": {"flame_method_fragment": 40, "baji_beng_scroll": 10}}, "failure": {"damage": [27, 42], "douqi": [4, 12], "danger": 3}},
        ],
    },
    "lost_mercenary": {
        "title": "负伤佣兵",
        "story": "一名佣兵靠在树下喘息，包裹散落在远处，附近似乎还有追兵。",
        "choices": [
            {"key": "guide", "label": "指明归路", "description": "提供方向后继续上路。", "risk": "稳妥", "base_chance": 100, "success": {"damage": [0, 1], "douqi": [8, 15], "gold": [5, 10], "danger": -1}},
            {"key": "escort", "label": "护送离山", "description": "护送佣兵穿过魔兽活动区。", "risk": "均衡", "base_chance": 76, "success": {"damage": [3, 8], "douqi": [18, 32], "gold": [16, 28], "danger": 0, "drops": {"healing_powder": 35}}, "failure": {"damage": [12, 22], "douqi": [3, 8], "danger": 2}},
            {"key": "recover_pack", "label": "夺回包裹", "description": "循着痕迹追击劫匪。", "risk": "凶险", "base_chance": 58, "success": {"damage": [7, 14], "douqi": [32, 58], "gold": [25, 44], "danger": 2, "drops": {"monster_core_low": 55}}, "failure": {"damage": [22, 34], "douqi": [4, 10], "danger": 3}},
        ],
    },
    "desert_storm": {
        "title": "黑沙暴",
        "story": "天际卷起黑色沙墙，火属性能量在风暴中心躁动不休。",
        "choices": [
            {"key": "shelter", "label": "寻找背风处", "description": "保存体力，等待风暴减弱。", "risk": "稳妥", "base_chance": 100, "success": {"damage": [2, 6], "douqi": [10, 18], "gold": [0, 4], "danger": -2}},
            {"key": "cross", "label": "斗气护体", "description": "以斗气护住经脉，穿越沙墙。", "risk": "均衡", "base_chance": 70, "success": {"damage": [6, 12], "douqi": [30, 52], "gold": [8, 16], "danger": 1, "drops": {"snake_shed_grass": 62}}, "failure": {"damage": [20, 32], "douqi": [6, 12], "danger": 2}},
            {"key": "center", "label": "追逐火流", "description": "深入风暴中心吸收火属性能量。", "risk": "凶险", "base_chance": 52, "success": {"damage": [10, 18], "douqi": [48, 82], "gold": [12, 24], "danger": 3, "drops": {"earth_core_fire_mushroom": 70, "qinglian_fire_map": 18}}, "failure": {"damage": [28, 44], "douqi": [5, 13], "danger": 4}},
        ],
    },
    "snake_patrol": {
        "title": "蛇人巡队",
        "story": "蛇人巡逻队封锁了绿洲入口，沙丘后还能看见一条隐蔽小径。",
        "choices": [
            {"key": "wait", "label": "隐匿等待", "description": "收敛气息，等巡队离开。", "risk": "稳妥", "base_chance": 100, "success": {"damage": [1, 4], "douqi": [9, 16], "gold": [2, 6], "danger": -1}},
            {"key": "trail", "label": "潜行小径", "description": "借沙丘遮蔽绕过封锁。", "risk": "均衡", "base_chance": 72, "success": {"damage": [4, 9], "douqi": [24, 43], "gold": [10, 20], "danger": 1, "drops": {"snake_shed_grass": 75, "blood_lotus_essence": 35}}, "failure": {"damage": [17, 28], "douqi": [4, 9], "danger": 3}},
            {"key": "breakthrough", "label": "正面突围", "description": "击溃巡队，夺取补给。", "risk": "凶险", "base_chance": 55, "success": {"damage": [9, 16], "douqi": [42, 70], "gold": [18, 34], "danger": 3, "drops": {"snake_reputation_token": 45, "scale_guard_armor": 8}}, "failure": {"damage": [26, 40], "douqi": [5, 12], "danger": 4}},
        ],
    },
    "fire_vein": {
        "title": "地火裂隙",
        "story": "岩层裂开一道赤红缝隙，精纯火劲不断涌出，深处隐约有异火气息。",
        "choices": [
            {"key": "observe", "label": "记录火脉", "description": "观察流向并记录安全路线。", "risk": "稳妥", "base_chance": 100, "success": {"damage": [1, 5], "douqi": [14, 24], "gold": [2, 7], "danger": -1, "drops": {"earth_core_fire_mushroom": 35}}},
            {"key": "temper", "label": "引火淬体", "description": "引导地火淬炼经脉。", "risk": "均衡", "base_chance": 67, "success": {"damage": [7, 13], "douqi": [36, 64], "gold": [7, 14], "danger": 2, "drops": {"earth_core_fire_mushroom": 72}}, "failure": {"damage": [22, 35], "douqi": [8, 16], "danger": 3}},
            {"key": "descend", "label": "深入裂隙", "description": "向异火气息最浓处深入。", "risk": "凶险", "base_chance": 48, "success": {"damage": [12, 20], "douqi": [58, 96], "gold": [15, 30], "danger": 4, "drops": {"qinglian_fire_map": 52, "fallen_heart_flame_trace": 14}}, "failure": {"damage": [32, 48], "douqi": [7, 18], "danger": 5}},
        ],
    },
    "desert_caravan": {
        "title": "沙漠商队",
        "story": "一支商队被流沙困住，领队愿意用货物换取援手。",
        "choices": [
            {"key": "directions", "label": "告知水源", "description": "交换地图情报，各自赶路。", "risk": "稳妥", "base_chance": 100, "success": {"damage": [0, 2], "douqi": [7, 14], "gold": [8, 14], "danger": -1}},
            {"key": "rescue", "label": "协助脱困", "description": "以斗气托起陷入流沙的货车。", "risk": "均衡", "base_chance": 78, "success": {"damage": [3, 8], "douqi": [20, 36], "gold": [20, 34], "danger": 0, "drops": {"fire_guard_pill": 32}}, "failure": {"damage": [12, 22], "douqi": [4, 9], "danger": 2}},
            {"key": "escort", "label": "护送穿沙", "description": "一路护送到下一处据点。", "risk": "凶险", "base_chance": 60, "success": {"damage": [7, 14], "douqi": [34, 60], "gold": [34, 56], "danger": 2, "drops": {"mitel_auction_token": 38}}, "failure": {"damage": [21, 34], "douqi": [5, 11], "danger": 3}},
        ],
    },
    "black_market": {
        "title": "黑市暗局",
        "story": "摊主压低声音兜售来路不明的纳戒，几道目光同时盯上了你。",
        "choices": [
            {"key": "leave", "label": "识破离场", "description": "不碰赃物，记下黑市布局。", "risk": "稳妥", "base_chance": 100, "success": {"damage": [0, 3], "douqi": [12, 22], "gold": [5, 12], "danger": -1}},
            {"key": "bargain", "label": "压价交易", "description": "利用对方急于出手的心理周旋。", "risk": "均衡", "base_chance": 66, "success": {"damage": [2, 7], "douqi": [28, 48], "gold": [28, 50], "danger": 2, "drops": {"monster_core_mid": 36}}, "failure": {"damage": [18, 30], "douqi": [4, 10], "danger": 3}},
            {"key": "take_ring", "label": "夺戒反杀", "description": "顺势掀桌，解决埋伏者。", "risk": "凶险", "base_chance": 48, "success": {"damage": [11, 19], "douqi": [55, 90], "gold": [48, 82], "danger": 4, "drops": {"low_grade_storage_ring": 30, "monster_core_high": 18}}, "failure": {"damage": [34, 50], "douqi": [6, 15], "danger": 5}},
        ],
    },
    "road_ambush": {
        "title": "峡谷截杀",
        "story": "峡谷两端同时落下巨石，数名蒙面斗者从岩壁跃下。",
        "choices": [
            {"key": "smoke", "label": "烟尘脱身", "description": "击碎岩壁制造烟尘，保存实力。", "risk": "稳妥", "base_chance": 100, "success": {"damage": [3, 8], "douqi": [14, 26], "gold": [4, 10], "danger": -1}},
            {"key": "leader", "label": "擒贼先擒王", "description": "越过围攻直取领头者。", "risk": "均衡", "base_chance": 64, "success": {"damage": [8, 15], "douqi": [40, 68], "gold": [35, 60], "danger": 2, "drops": {"black_iron_sword": 24}}, "failure": {"damage": [25, 38], "douqi": [6, 13], "danger": 4}},
            {"key": "counter", "label": "全数反杀", "description": "封住退路，以战养战。", "risk": "凶险", "base_chance": 46, "success": {"damage": [14, 23], "douqi": [62, 102], "gold": [60, 96], "danger": 5, "drops": {"monster_core_mid": 68, "flame_guard_bracer": 15}}, "failure": {"damage": [38, 56], "douqi": [8, 18], "danger": 6}},
        ],
    },
    "ancient_ruin": {
        "title": "远古残殿",
        "story": "破败石殿沉在峡谷尽头，墙上残留着高阶斗技运转痕迹。",
        "choices": [
            {"key": "rubbing", "label": "临摹石壁", "description": "只记录可辨认的斗气路线。", "risk": "稳妥", "base_chance": 100, "success": {"damage": [1, 4], "douqi": [24, 40], "gold": [3, 9], "danger": -1}},
            {"key": "outer_hall", "label": "搜寻外殿", "description": "避开主阵，搜索坍塌偏殿。", "risk": "均衡", "base_chance": 62, "success": {"damage": [7, 14], "douqi": [45, 76], "gold": [30, 54], "danger": 2, "drops": {"flame_method_fragment": 55, "thunder_steps_scroll": 16}}, "failure": {"damage": [25, 39], "douqi": [7, 15], "danger": 4}},
            {"key": "main_hall", "label": "闯入主殿", "description": "硬抗残阵，争夺核心传承。", "risk": "凶险", "base_chance": 43, "success": {"damage": [15, 25], "douqi": [75, 120], "gold": [55, 90], "danger": 5, "drops": {"flame_divide_scroll": 34, "thunder_steps_scroll": 30}}, "failure": {"damage": [42, 62], "douqi": [9, 20], "danger": 6}},
        ],
    },
}


def expedition_region(region_key: str) -> dict[str, Any] | None:
    return next((dict(region) for region in EXPEDITION_REGIONS if region["key"] == str(region_key)), None)
