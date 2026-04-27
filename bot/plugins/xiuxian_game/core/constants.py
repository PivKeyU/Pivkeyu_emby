"""修仙游戏常量 — 从 service.py 和 sql_xiuxian.py 提取，无外部依赖。"""

# 灵根常量
ROOT_SPECIAL_BONUS = {
    "天灵根": 15,
    "地灵根": 10,
}
ROOT_COMMON_QUALITY_ORDER = ["废灵根", "下品灵根", "中品灵根", "上品灵根", "极品灵根"]
ROOT_SPECIAL_QUALITIES = {"天灵根", "变异灵根"}
ROOT_TRANSFORM_PILL_TYPES = {"root_single", "root_double", "root_earth", "root_heaven", "root_variant"}

# 丹药批量使用类型 — clear_poison 故意排除，防止丹毒循环漏洞
PILL_BATCH_USE_TYPES = {
    "attack",
    "body_movement",
    "bone",
    "charisma",
    "comprehension",
    "cultivation",
    "defense",
    "divine_sense",
    "fortune",
    "karma",
    "qi_blood",
    "true_yuan",
    "willpower",
}
# clear_poison intentionally excluded from batch use to prevent
# infinite stat stacking via the dan_poison cycling exploit:
# 1. batch-use stat pills until dan_poison >= 100
# 2. batch-use clear_poison pills to reset dan_poison to 0
# 3. repeat — the only limit becomes inventory count

ROOT_COMBAT_BASELINE_QUALITY = "中品灵根"
ROOT_COMBAT_FACTOR_MIN = 0.97
ROOT_COMBAT_FACTOR_MAX = 1.06
ROOT_ELEMENT_FACTOR_WEIGHT = 0.35
ROOT_VARIANT_FACTOR_BONUS = 0.01

# 商店名称
PERSONAL_SHOP_NAME = "游仙小铺"
OFFICIAL_RECYCLE_NAME = "万宝归炉"
IMMORTAL_STONE_NAME = "仙界奇石"

# 物品类型
GAMBLING_SUPPORTED_ITEM_KINDS = {"artifact", "pill", "talisman", "material", "recipe", "technique"}
RECYCLABLE_ITEM_KINDS = {"artifact", "pill", "talisman", "material", "technique", "recipe"}

# 开局赠送
STARTER_TECHNIQUE_NAME = "长青诀"
STARTER_TITLE_NAME = "初入仙途"
STARTER_FOUNDATION_PILL_NAME = "筑基丹"

# 境界
FIRST_REALM_STAGE = "炼气"
