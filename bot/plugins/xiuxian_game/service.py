"""修仙核心数值与成长服务。

这里保留历史兼容出口。
后续新增或维护优先落到 `features/` 下的对应领域文件，再由这里兼容导出。
"""

from __future__ import annotations

import random
from datetime import timedelta
from math import ceil
from typing import Any

from pykeyboard import InlineButton, InlineKeyboard
from pyromod.helpers import ikb

from bot import api as api_config
from bot.func_helper.emby_currency import (
    convert_coin_to_stone,
    convert_stone_to_coin,
    get_emby_balance,
    get_exchange_settings,
)
from bot.sql_helper.sql_xiuxian import (
    ATTRIBUTE_LABELS,
    DEFAULT_SETTINGS,
    ELEMENT_CONTROLS,
    ELEMENT_GENERATES,
    FIVE_ELEMENTS,
    ITEM_KIND_LABELS,
    PILL_TYPE_LABELS,
    REALM_ORDER,
    ROOT_QUALITY_COLORS,
    ROOT_QUALITY_LEVELS,
    ROOT_VARIANT_ELEMENTS,
    admin_patch_profile,
    bind_user_artifact,
    bind_user_talisman,
    create_journal,
    create_artifact,
    create_duel_record,
    create_pill,
    create_shop_item,
    create_technique,
    create_talisman,
    get_artifact,
    get_current_title,
    get_emby_name_map,
    get_material,
    get_pill,
    get_profile,
    get_technique,
    get_talisman,
    get_xiuxian_settings,
    grant_artifact_to_user,
    grant_material_to_user,
    grant_pill_to_user,
    grant_recipe_to_user,
    grant_talisman_to_user,
    grant_technique_to_user,
    list_artifacts,
    list_artifact_sets,
    list_equipped_artifacts,
    list_materials,
    list_pills,
    list_profiles,
    list_recipes,
    list_shop_items,
    list_techniques,
    list_talismans,
    list_user_titles,
    list_user_artifacts,
    list_user_materials,
    list_user_pills,
    list_user_recipes,
    list_user_techniques,
    list_user_talismans,
    normalize_realm_stage,
    purchase_shop_item as sql_purchase_shop_item,
    plunder_random_artifact_to_user,
    realm_index,
    search_profiles,
    serialize_artifact,
    serialize_pill,
    serialize_profile,
    serialize_technique,
    serialize_talisman,
    set_current_technique,
    set_current_title,
    set_active_talisman,
    set_equipped_artifact,
    set_xiuxian_settings,
    sync_achievement_by_key,
    sync_official_shop_name,
    sync_artifact_by_name,
    sync_artifact_set_by_name,
    sync_encounter_template_by_name,
    sync_material_by_name,
    sync_pill_by_name,
    sync_talisman_by_name,
    sync_technique_by_name,
    sync_title_by_name,
    admin_set_user_artifact_inventory,
    admin_set_user_material_inventory,
    admin_set_user_pill_inventory,
    admin_set_user_talisman_inventory,
    revoke_recipe_from_user,
    revoke_technique_from_user,
    revoke_title_from_user,
    unbind_user_artifact,
    unbind_user_talisman,
    update_shop_item,
    upsert_profile,
    use_user_artifact_listing_stock,
    use_user_material_listing_stock,
    use_user_pill_listing_stock,
    use_user_talisman_listing_stock,
    consume_user_pill,
    consume_user_talisman,
    utcnow,
)
from bot.plugins.xiuxian_game.achievement_service import (
    build_user_achievement_overview,
    record_duel_metrics,
)
from bot.plugins.xiuxian_game.probability import (
    adjust_probability_rate,
    roll_probability_percent,
)
from bot.plugins.xiuxian_game.world_service import (
    get_sect_effects,
    sync_recipe_with_ingredients_by_name,
    sync_scene_with_drops_by_name,
    sync_sect_with_roles_by_name,
)
from bot.plugins.xiuxian_game.features.content_catalog import (
    DEFAULT_ENCOUNTER_TEMPLATES,
    EXTRA_ARTIFACTS,
    EXTRA_MATERIALS,
    EXTRA_PILLS,
    EXTRA_RECIPES,
    EXTRA_SCENES,
    EXTRA_TALISMANS,
)


ROOT_SPECIAL_BONUS = {
    "天灵根": 15,
    "地灵根": 10,
}
ROOT_COMMON_QUALITY_ORDER = ["废灵根", "下品灵根", "中品灵根", "上品灵根", "极品灵根"]
ROOT_SPECIAL_QUALITIES = {"天灵根", "变异灵根"}
ROOT_TRANSFORM_PILL_TYPES = {"root_single", "root_double", "root_earth", "root_heaven", "root_variant"}

PERSONAL_SHOP_NAME = "游仙小铺"

DEFAULT_ARTIFACTS = [
    {
        "name": "凡铁剑",
        "rarity": "凡品",
        "artifact_type": "battle",
        "description": "最基础的入门法宝，适合刚踏入仙途的道友防身。",
        "attack_bonus": 12,
        "defense_bonus": 6,
        "duel_rate_bonus": 2,
        "cultivation_bonus": 0,
        "combat_config": {
            "passives": [
                {
                    "name": "铁锋一击",
                    "kind": "extra_damage",
                    "chance": 18,
                    "flat_damage": 8,
                    "text": "凡铁剑劈出一线寒芒，逼得对手仓促后撤。",
                }
            ]
        },
        "image_url": "",
        "enabled": True,
    },
    {
        "name": "青罡剑",
        "rarity": "下品",
        "artifact_type": "battle",
        "description": "以寒铁与赤炎晶砂淬成，剑势凌厉，最适合初入筑基的剑修。",
        "attack_bonus": 18,
        "defense_bonus": 5,
        "body_movement_bonus": 4,
        "duel_rate_bonus": 4,
        "combat_config": {
            "opening_text": "青罡剑鸣，剑气先至。",
            "passives": [
                {
                    "name": "剑罡斩",
                    "kind": "extra_damage",
                    "chance": 26,
                    "flat_damage": 14,
                    "ratio_percent": 20,
                    "text": "青罡剑卷起一道剑罡，直取对手要害。",
                }
            ],
        },
        "min_realm_stage": "炼气",
        "min_realm_layer": 6,
        "image_url": "",
        "enabled": True,
    },
    {
        "name": "玄龟盾",
        "rarity": "下品",
        "artifact_type": "support",
        "description": "以玄龟甲片和地脉岩芯炼成，擅长化劲护体。",
        "attack_bonus": 4,
        "defense_bonus": 18,
        "qi_blood_bonus": 40,
        "duel_rate_bonus": 3,
        "combat_config": {
            "passives": [
                {
                    "name": "玄甲护身",
                    "kind": "shield",
                    "chance": 28,
                    "flat_shield": 22,
                    "ratio_percent": 24,
                    "duration": 1,
                    "text": "玄龟盾沉沉一震，垒起一层灵甲护住周身。",
                }
            ]
        },
        "min_realm_stage": "炼气",
        "min_realm_layer": 7,
        "image_url": "",
        "enabled": True,
    },
    {
        "name": "逐云履",
        "rarity": "中品",
        "artifact_type": "support",
        "description": "以云纹丝炼成的轻灵法履，步踏如风，专克笨重攻势。",
        "attack_bonus": 8,
        "defense_bonus": 8,
        "body_movement_bonus": 16,
        "duel_rate_bonus": 6,
        "combat_config": {
            "passives": [
                {
                    "name": "踏云错影",
                    "kind": "dodge",
                    "chance": 24,
                    "dodge_bonus": 16,
                    "duration": 1,
                    "text": "逐云履轻轻一点，身形已借雾气挪开半尺。",
                }
            ]
        },
        "min_realm_stage": "筑基",
        "min_realm_layer": 2,
        "image_url": "",
        "enabled": True,
    },
    {
        "name": "赤焰珠",
        "rarity": "中品",
        "artifact_type": "battle",
        "description": "珠内封着一缕离火，攻势不算厚重，但善于不断灼烧对手。",
        "attack_bonus": 16,
        "true_yuan_bonus": 50,
        "duel_rate_bonus": 5,
        "combat_config": {
            "passives": [
                {
                    "name": "离火灼心",
                    "kind": "burn",
                    "chance": 22,
                    "flat_damage": 10,
                    "duration": 2,
                    "text": "赤焰珠吐出离火细线，附在护体灵气上缓缓灼烧。",
                }
            ]
        },
        "min_realm_stage": "筑基",
        "min_realm_layer": 3,
        "image_url": "",
        "enabled": True,
    },
    {
        "name": "残修青罡古剑",
        "rarity": "上品",
        "artifact_type": "battle",
        "description": "自秘境残剑中修复而来，剑身尚有裂纹，却也藏着不俗杀意。",
        "attack_bonus": 28,
        "defense_bonus": 10,
        "body_movement_bonus": 6,
        "duel_rate_bonus": 8,
        "combat_config": {
            "opening_text": "古剑微震，似有旧日战魂苏醒。",
            "skills": [
                {
                    "name": "裂空古剑式",
                    "kind": "extra_damage",
                    "chance": 32,
                    "flat_damage": 22,
                    "ratio_percent": 28,
                    "cost_true_yuan": 20,
                    "text": "残修青罡古剑带着破空之声悍然斩下。",
                }
            ],
            "passives": [
                {
                    "name": "残锋噬血",
                    "kind": "bleed",
                    "chance": 18,
                    "flat_damage": 12,
                    "duration": 2,
                    "text": "旧伤被古剑撕开，鲜血顺着灵力痕迹一并溃散。",
                }
            ],
        },
        "min_realm_stage": "筑基",
        "min_realm_layer": 6,
        "image_url": "",
        "enabled": True,
    },
    {
        "name": "残修玄龟古盾",
        "rarity": "上品",
        "artifact_type": "support",
        "description": "由古盾残片重新归铸，盾势厚重，最适合久战磨敌。",
        "attack_bonus": 6,
        "defense_bonus": 28,
        "qi_blood_bonus": 80,
        "duel_rate_bonus": 4,
        "combat_config": {
            "skills": [
                {
                    "name": "镇岳灵壁",
                    "kind": "guard",
                    "chance": 34,
                    "defense_ratio_percent": 30,
                    "flat_shield": 28,
                    "cost_true_yuan": 16,
                    "duration": 1,
                    "text": "古盾轰然立起，如一座小山压住来势汹汹的劲力。",
                }
            ]
        },
        "min_realm_stage": "筑基",
        "min_realm_layer": 6,
        "image_url": "",
        "enabled": True,
    },
]

DEFAULT_PILLS = [
    {
        "name": "筑基丹",
        "pill_type": "foundation",
        "description": "筑基突破时使用，提高本次突破成功率。",
        "effect_value": 50,
        "poison_delta": 12,
        "image_url": "",
        "enabled": True,
    },
    {
        "name": "清心丹",
        "pill_type": "clear_poison",
        "description": "化解丹毒，服用后可降低 50 点丹毒。",
        "effect_value": 50,
        "poison_delta": 0,
        "image_url": "",
        "enabled": True,
    },
    {
        "name": "洗髓丹",
        "rarity": "下品",
        "pill_type": "bone",
        "description": "淬炼筋骨，永久提升 4 点根骨。",
        "effect_value": 4,
        "poison_delta": 6,
        "image_url": "",
        "min_realm_stage": "炼气",
        "min_realm_layer": 3,
        "enabled": True,
    },
    {
        "name": "悟道丹",
        "rarity": "下品",
        "pill_type": "comprehension",
        "description": "澄明灵台，永久提升 4 点悟性。",
        "effect_value": 4,
        "poison_delta": 8,
        "image_url": "",
        "min_realm_stage": "炼气",
        "min_realm_layer": 5,
        "enabled": True,
    },
    {
        "name": "凝神丹",
        "rarity": "下品",
        "pill_type": "divine_sense",
        "description": "凝练识海，永久提升 4 点神识。",
        "effect_value": 4,
        "poison_delta": 6,
        "image_url": "",
        "min_realm_stage": "炼气",
        "min_realm_layer": 4,
        "enabled": True,
    },
    {
        "name": "天运丹",
        "rarity": "中品",
        "pill_type": "fortune",
        "description": "温养命数，永久提升 3 点机缘。",
        "effect_value": 3,
        "poison_delta": 5,
        "image_url": "",
        "min_realm_stage": "筑基",
        "min_realm_layer": 1,
        "enabled": True,
    },
    {
        "name": "血魄丹",
        "rarity": "下品",
        "pill_type": "qi_blood",
        "description": "淬炼气血，永久提升 60 点气血。",
        "effect_value": 60,
        "poison_delta": 10,
        "image_url": "",
        "min_realm_stage": "炼气",
        "min_realm_layer": 6,
        "enabled": True,
    },
    {
        "name": "蕴元丹",
        "rarity": "下品",
        "pill_type": "true_yuan",
        "description": "温养丹田，永久提升 50 点真元。",
        "effect_value": 50,
        "poison_delta": 9,
        "image_url": "",
        "min_realm_stage": "炼气",
        "min_realm_layer": 6,
        "enabled": True,
    },
    {
        "name": "轻灵丹",
        "rarity": "下品",
        "pill_type": "body_movement",
        "description": "轻身活脉，永久提升 4 点身法。",
        "effect_value": 4,
        "poison_delta": 6,
        "image_url": "",
        "min_realm_stage": "炼气",
        "min_realm_layer": 4,
        "enabled": True,
    },
    {
        "name": "补天丹",
        "rarity": "极品",
        "pill_type": "root_refine",
        "description": "淬炼灵根，灵根品质提升 1 阶，最高提升至极品灵根。",
        "effect_value": 1,
        "poison_delta": 14,
        "image_url": "",
        "min_realm_stage": "筑基",
        "min_realm_layer": 5,
        "enabled": True,
    },
    {
        "name": "洗灵丹",
        "rarity": "极品",
        "pill_type": "root_remold",
        "description": "重塑灵根，重新洗炼灵根属性，结果至少为中品灵根。",
        "effect_value": 3,
        "poison_delta": 18,
        "image_url": "",
        "min_realm_stage": "筑基",
        "min_realm_layer": 9,
        "enabled": True,
    },
    {
        "name": "聚气丹",
        "rarity": "下品",
        "pill_type": "cultivation",
        "description": "快速凝聚灵气，适合炼气后期补足修为缺口。",
        "effect_value": 120,
        "poison_delta": 8,
        "min_realm_stage": "炼气",
        "min_realm_layer": 5,
        "enabled": True,
    },
    {
        "name": "回春丹",
        "rarity": "下品",
        "pill_type": "qi_blood",
        "description": "药力温和，可补气回血并稳住战后亏空。",
        "effect_value": 90,
        "poison_delta": 8,
        "min_realm_stage": "炼气",
        "min_realm_layer": 4,
        "enabled": True,
    },
    {
        "name": "凝元丹",
        "rarity": "下品",
        "pill_type": "true_yuan",
        "description": "温养丹田，适合需要多次催动功法的修士。",
        "effect_value": 80,
        "poison_delta": 8,
        "min_realm_stage": "炼气",
        "min_realm_layer": 5,
        "enabled": True,
    },
    {
        "name": "锐金丹",
        "rarity": "中品",
        "pill_type": "attack",
        "description": "短时间内淬出锋锐金气，永久略增攻伐之力。",
        "effect_value": 6,
        "poison_delta": 10,
        "min_realm_stage": "筑基",
        "min_realm_layer": 2,
        "enabled": True,
    },
    {
        "name": "护脉丹",
        "rarity": "中品",
        "pill_type": "defense",
        "description": "稳固经脉与护体真元，适合偏防御路线修士。",
        "effect_value": 6,
        "poison_delta": 9,
        "min_realm_stage": "筑基",
        "min_realm_layer": 2,
        "enabled": True,
    },
]

DEFAULT_TALISMANS = [
    {
        "name": "疾风符",
        "rarity": "凡品",
        "description": "在下一场斗法中提高先机与攻击，增强胜率。",
        "attack_bonus": 6,
        "duel_rate_bonus": 4,
        "body_movement_bonus": 6,
        "combat_config": {
            "passives": [
                {
                    "name": "疾风借位",
                    "kind": "dodge",
                    "chance": 20,
                    "dodge_bonus": 12,
                    "duration": 1,
                    "text": "符风一卷，身影轻轻一晃便错开了锋芒。",
                }
            ]
        },
        "image_url": "",
        "enabled": True,
    },
    {
        "name": "雷火符",
        "rarity": "下品",
        "description": "雷火并济，命中后容易留下灼伤与麻痹余威。",
        "attack_bonus": 10,
        "duel_rate_bonus": 5,
        "combat_config": {
            "skills": [
                {
                    "name": "雷火骤落",
                    "kind": "burn",
                    "chance": 34,
                    "flat_damage": 12,
                    "duration": 2,
                    "text": "雷火符炸开一团赤雷，火星顺着灵气扑上对手衣袍。",
                }
            ]
        },
        "min_realm_stage": "炼气",
        "min_realm_layer": 7,
        "image_url": "",
        "enabled": True,
    },
    {
        "name": "金钟符",
        "rarity": "下品",
        "description": "催起一层金钟灵罩，专克正面攻势。",
        "defense_bonus": 12,
        "duel_rate_bonus": 3,
        "combat_config": {
            "skills": [
                {
                    "name": "金钟护体",
                    "kind": "shield",
                    "chance": 40,
                    "flat_shield": 26,
                    "ratio_percent": 18,
                    "duration": 1,
                    "text": "金钟符金光一展，钟影将周身牢牢笼住。",
                }
            ]
        },
        "min_realm_stage": "炼气",
        "min_realm_layer": 7,
        "image_url": "",
        "enabled": True,
    },
    {
        "name": "轻身符",
        "rarity": "下品",
        "description": "以风脉符纹减轻身形，让对手更难锁定。",
        "body_movement_bonus": 12,
        "duel_rate_bonus": 4,
        "combat_config": {
            "skills": [
                {
                    "name": "轻烟借步",
                    "kind": "dodge",
                    "chance": 30,
                    "dodge_bonus": 20,
                    "duration": 1,
                    "text": "轻身符化作淡淡青烟，人已从残影中遁开。",
                }
            ]
        },
        "min_realm_stage": "炼气",
        "min_realm_layer": 5,
        "image_url": "",
        "enabled": True,
    },
    {
        "name": "破甲符",
        "rarity": "中品",
        "description": "专克护体法门，命中后能撕开几分防御。",
        "attack_bonus": 8,
        "duel_rate_bonus": 4,
        "combat_config": {
            "skills": [
                {
                    "name": "裂甲真纹",
                    "kind": "armor_break",
                    "chance": 28,
                    "defense_ratio_percent": 18,
                    "duration": 2,
                    "text": "破甲符贴身即碎，一串真纹顺着护体灵气钻入缝隙。",
                }
            ]
        },
        "min_realm_stage": "筑基",
        "min_realm_layer": 2,
        "image_url": "",
        "enabled": True,
    },
]

DEFAULT_TECHNIQUES = [
    {
        "name": "长青诀",
        "rarity": "凡品",
        "technique_type": "cultivation",
        "description": "循序吐纳、温养经脉的入门功法，适合刚踏入仙途的修士稳扎稳打。",
        "comprehension_bonus": 2,
        "true_yuan_bonus": 18,
        "cultivation_bonus": 8,
        "breakthrough_bonus": 4,
        "combat_config": {
            "passives": [
                {
                    "name": "长青回气",
                    "kind": "heal",
                    "chance": 18,
                    "flat_heal": 10,
                    "ratio_percent": 8,
                    "text": "长青诀运转片刻，经脉中回涌出一缕温润生机。",
                }
            ]
        },
        "min_realm_stage": "炼气",
        "min_realm_layer": 1,
        "enabled": True,
    },
    {
        "name": "金刚伏魔功",
        "rarity": "下品",
        "technique_type": "combat",
        "description": "以气血催动筋骨，重攻重势，适合偏战斗路线的修士。",
        "attack_bonus": 10,
        "defense_bonus": 6,
        "qi_blood_bonus": 36,
        "duel_rate_bonus": 5,
        "combat_config": {
            "skills": [
                {
                    "name": "伏魔重拳",
                    "kind": "extra_damage",
                    "chance": 26,
                    "flat_damage": 16,
                    "ratio_percent": 20,
                    "cost_true_yuan": 14,
                    "text": "金刚伏魔功鼓荡气血，一拳打得空气轰然作响。",
                }
            ]
        },
        "min_realm_stage": "筑基",
        "min_realm_layer": 1,
        "enabled": True,
    },
    {
        "name": "太虚凝神篇",
        "rarity": "下品",
        "technique_type": "balanced",
        "description": "偏重神识与悟性，可兼顾突破与斗法，是中前期泛用功法。",
        "comprehension_bonus": 4,
        "divine_sense_bonus": 5,
        "attack_bonus": 4,
        "defense_bonus": 4,
        "breakthrough_bonus": 6,
        "combat_config": {
            "skills": [
                {
                    "name": "凝神刺魄",
                    "kind": "extra_damage",
                    "chance": 24,
                    "flat_damage": 12,
                    "ratio_percent": 18,
                    "cost_true_yuan": 12,
                    "text": "太虚凝神篇化神识为细芒，猛然点向对手灵台。",
                }
            ]
        },
        "min_realm_stage": "筑基",
        "min_realm_layer": 3,
        "enabled": True,
    },
    {
        "name": "焚天离火诀",
        "rarity": "中品",
        "technique_type": "attack",
        "description": "将离火之气压入经脉，出手霸道，善于叠加灼伤。",
        "attack_bonus": 16,
        "true_yuan_bonus": 28,
        "duel_rate_bonus": 6,
        "combat_config": {
            "opening_text": "离火自掌心涌起，四周空气都被烤得扭曲。",
            "skills": [
                {
                    "name": "离火斩",
                    "kind": "burn",
                    "chance": 34,
                    "flat_damage": 14,
                    "ratio_percent": 20,
                    "duration": 2,
                    "cost_true_yuan": 18,
                    "text": "焚天离火诀催出一道火芒，紧贴护体罡气一路烧进去。",
                }
            ]
        },
        "min_realm_stage": "筑基",
        "min_realm_layer": 2,
        "enabled": True,
    },
    {
        "name": "游龙踏云步",
        "rarity": "中品",
        "technique_type": "movement",
        "description": "以身法见长，讲究腾挪借势，最擅把对手的重击引空。",
        "defense_bonus": 4,
        "body_movement_bonus": 18,
        "duel_rate_bonus": 7,
        "combat_config": {
            "skills": [
                {
                    "name": "云间错影",
                    "kind": "dodge",
                    "chance": 32,
                    "dodge_bonus": 22,
                    "duration": 1,
                    "cost_true_yuan": 12,
                    "text": "游龙踏云步连踏数步，残影在半空拖出一串水波般的弧线。",
                }
            ]
        },
        "min_realm_stage": "筑基",
        "min_realm_layer": 2,
        "enabled": True,
    },
    {
        "name": "玄龟镇岳经",
        "rarity": "中品",
        "technique_type": "defense",
        "description": "护体厚重如山，真元越稳，挨打时反而越显难缠。",
        "defense_bonus": 18,
        "qi_blood_bonus": 60,
        "duel_rate_bonus": 4,
        "combat_config": {
            "skills": [
                {
                    "name": "镇岳灵壁",
                    "kind": "guard",
                    "chance": 36,
                    "defense_ratio_percent": 26,
                    "flat_shield": 20,
                    "duration": 1,
                    "cost_true_yuan": 14,
                    "text": "玄龟镇岳经一沉，护体灵壁如山根般稳稳立住。",
                }
            ]
        },
        "min_realm_stage": "筑基",
        "min_realm_layer": 2,
        "enabled": True,
    },
    {
        "name": "太虚摄魂篇",
        "rarity": "中品",
        "technique_type": "divine",
        "description": "重神识与悟性，擅长看穿破绽，以小代价打出致命空隙。",
        "comprehension_bonus": 5,
        "divine_sense_bonus": 8,
        "attack_bonus": 6,
        "duel_rate_bonus": 5,
        "breakthrough_bonus": 4,
        "combat_config": {
            "skills": [
                {
                    "name": "摄魂灵刺",
                    "kind": "armor_break",
                    "chance": 30,
                    "defense_ratio_percent": 16,
                    "duration": 2,
                    "cost_true_yuan": 16,
                    "text": "太虚摄魂篇聚起一缕神识尖刺，直扎对方灵台与护体交界。",
                }
            ]
        },
        "min_realm_stage": "筑基",
        "min_realm_layer": 4,
        "enabled": True,
    },
]

DEFAULT_TITLES = [
    {"name": "红尘初行者", "description": "踏入仙途后的第一段旅程仍算平凡，却已不再是凡人。", "color": "#94a3b8", "fortune_bonus": 1},
    {"name": "斗法常客", "description": "常在斗法台露面，出手已不再生涩。", "color": "#ef4444", "attack_bonus": 2, "defense_bonus": 2, "duel_rate_bonus": 2},
    {"name": "秘境行者", "description": "熟悉山川遗府与古道残阵，遇事更懂趋吉避凶。", "color": "#0f766e", "divine_sense_bonus": 3, "fortune_bonus": 3},
    {"name": "百折不挠", "description": "屡败不乱，道心未折。", "color": "#2563eb", "qi_blood_bonus": 36, "defense_bonus": 4},
    {"name": "小有机缘", "description": "命数微盛，时常能从险地捡到别人错过的机缘。", "color": "#f59e0b", "fortune_bonus": 4, "true_yuan_bonus": 24},
    {"name": "炼器熟手", "description": "已经懂得分辨火候与材质，不再轻易炸炉。", "color": "#92400e", "comprehension_bonus": 4, "defense_bonus": 2},
    {"name": "丹心妙手", "description": "丹火温润，识药识性，对药力流转颇有心得。", "color": "#059669", "comprehension_bonus": 4, "true_yuan_bonus": 30},
    {"name": "夺宝老手", "description": "见财知势，动手之前总能先找准最值钱的那一件。", "color": "#7c3aed", "attack_bonus": 4, "fortune_bonus": 2, "duel_rate_bonus": 3},
]

DEFAULT_MATERIALS = [
    {"name": "寒铁矿", "quality_level": 1, "description": "常见矿料，适合炼制剑胚与基础法器。"},
    {"name": "灵木芯", "quality_level": 1, "description": "灵木深处凝出的芯材，可稳固器物中的灵纹。"},
    {"name": "云纹丝", "quality_level": 1, "description": "轻若无物的灵丝，常用于鞋履与轻甲。"},
    {"name": "归元草", "quality_level": 1, "description": "常用于温养气血与中和药性的低阶灵草。"},
    {"name": "赤炎晶砂", "quality_level": 2, "description": "带火性的细砂，适合攻伐类法器与符箓。"},
    {"name": "凝露花", "quality_level": 2, "description": "夜半凝露而生，适合炼制回春与凝元类丹药。"},
    {"name": "玄龟甲片", "quality_level": 2, "description": "来自妖龟遗骸的厚重甲片，护体效果极好。"},
    {"name": "雷击木", "quality_level": 2, "description": "遭天雷劈过的灵木，最适合承载雷火符纹。"},
    {"name": "青罡剑谱残页", "quality_level": 2, "description": "残缺的剑谱拓本，能补足青罡剑的炼制脉络。"},
    {"name": "回春丹谱残页", "quality_level": 2, "description": "记着几味关键药引顺序的丹谱残页。"},
    {"name": "雷火符谱残页", "quality_level": 2, "description": "隐约还看得清雷火二纹的落笔顺序。"},
    {"name": "金钟符谱残页", "quality_level": 2, "description": "记录了金钟护体符纹的几笔转折。"},
    {"name": "星辉砂", "quality_level": 3, "description": "夜间会微微发亮的细砂，常用于修复古器灵性。"},
    {"name": "地脉岩芯", "quality_level": 3, "description": "深埋地脉的凝实核心，能稳住法宝结构。"},
    {"name": "破损青罡剑胚", "quality_level": 3, "description": "从残剑崖捡回的残损剑胚，尚有修复价值。"},
    {"name": "破损玄龟盾片", "quality_level": 3, "description": "古盾脱落的一角残片，内里灵纹还未彻底断绝。"},
]

DEFAULT_RECIPES = [
    {"name": "青罡剑炼制图", "recipe_kind": "artifact", "result_kind": "artifact", "result_name": "青罡剑", "result_quantity": 1, "base_success_rate": 58, "broadcast_on_success": False, "ingredients": [{"material_name": "寒铁矿", "quantity": 3}, {"material_name": "赤炎晶砂", "quantity": 1}, {"material_name": "青罡剑谱残页", "quantity": 1}]},
    {"name": "玄龟盾炼制图", "recipe_kind": "artifact", "result_kind": "artifact", "result_name": "玄龟盾", "result_quantity": 1, "base_success_rate": 56, "broadcast_on_success": False, "ingredients": [{"material_name": "玄龟甲片", "quantity": 2}, {"material_name": "地脉岩芯", "quantity": 1}, {"material_name": "灵木芯", "quantity": 1}]},
    {"name": "逐云履炼制图", "recipe_kind": "artifact", "result_kind": "artifact", "result_name": "逐云履", "result_quantity": 1, "base_success_rate": 50, "broadcast_on_success": False, "ingredients": [{"material_name": "云纹丝", "quantity": 3}, {"material_name": "雷击木", "quantity": 1}, {"material_name": "星辉砂", "quantity": 1}]},
    {"name": "回春丹丹谱", "recipe_kind": "pill", "result_kind": "pill", "result_name": "回春丹", "result_quantity": 1, "base_success_rate": 66, "broadcast_on_success": False, "ingredients": [{"material_name": "归元草", "quantity": 2}, {"material_name": "凝露花", "quantity": 1}, {"material_name": "回春丹谱残页", "quantity": 1}]},
    {"name": "聚气丹丹谱", "recipe_kind": "pill", "result_kind": "pill", "result_name": "聚气丹", "result_quantity": 1, "base_success_rate": 72, "broadcast_on_success": False, "ingredients": [{"material_name": "归元草", "quantity": 2}, {"material_name": "灵木芯", "quantity": 1}]},
    {"name": "雷火符符谱", "recipe_kind": "talisman", "result_kind": "talisman", "result_name": "雷火符", "result_quantity": 2, "base_success_rate": 60, "broadcast_on_success": False, "ingredients": [{"material_name": "雷击木", "quantity": 2}, {"material_name": "赤炎晶砂", "quantity": 1}, {"material_name": "雷火符谱残页", "quantity": 1}]},
    {"name": "金钟符符谱", "recipe_kind": "talisman", "result_kind": "talisman", "result_name": "金钟符", "result_quantity": 2, "base_success_rate": 60, "broadcast_on_success": False, "ingredients": [{"material_name": "玄龟甲片", "quantity": 1}, {"material_name": "地脉岩芯", "quantity": 1}, {"material_name": "金钟符谱残页", "quantity": 1}]},
    {"name": "古剑残纹修复法", "recipe_kind": "artifact", "result_kind": "artifact", "result_name": "残修青罡古剑", "result_quantity": 1, "base_success_rate": 16, "broadcast_on_success": True, "ingredients": [{"material_name": "破损青罡剑胚", "quantity": 1}, {"material_name": "星辉砂", "quantity": 2}, {"material_name": "地脉岩芯", "quantity": 1}]},
    {"name": "古盾归铸法", "recipe_kind": "artifact", "result_kind": "artifact", "result_name": "残修玄龟古盾", "result_quantity": 1, "base_success_rate": 18, "broadcast_on_success": True, "ingredients": [{"material_name": "破损玄龟盾片", "quantity": 1}, {"material_name": "地脉岩芯", "quantity": 2}, {"material_name": "凝露花", "quantity": 1}]},
]

DEFAULT_SCENES = [
    {
        "name": "黑风山谷",
        "description": "山风终年不散，适合初入仙途的修士历练与采集。",
        "max_minutes": 30,
        "min_combat_power": 0,
        "event_pool": [
            {"name": "山风异响", "description": "黑风卷石而来，你躲开乱石后在石缝里摸到几块灵石。", "event_type": "danger", "weight": 3, "stone_bonus_min": 8, "stone_bonus_max": 18, "stone_loss_min": 3, "stone_loss_max": 10},
            {"name": "旧修行囊", "description": "山道边有遗落多时的旧行囊，里头还剩下一页模糊图录。", "event_type": "recipe", "weight": 2, "bonus_reward_kind": "material", "bonus_reward_ref_id_name": "青罡剑谱残页", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 35},
            {"name": "灵风拂面", "description": "一阵带着药香的山风扫过，脚下多了几株被掩住的灵草。", "event_type": "fortune", "weight": 3},
        ],
        "drops": [
            {"reward_kind": "material", "reward_ref_id_name": "寒铁矿", "quantity_min": 1, "quantity_max": 3, "weight": 6, "stone_reward": 4, "event_text": "你在碎石间刨出几块寒铁矿。"},
            {"reward_kind": "material", "reward_ref_id_name": "灵木芯", "quantity_min": 1, "quantity_max": 2, "weight": 5, "stone_reward": 3, "event_text": "山谷古木中藏着尚未腐坏的灵木芯。"},
            {"reward_kind": "material", "reward_ref_id_name": "归元草", "quantity_min": 1, "quantity_max": 3, "weight": 6, "stone_reward": 3, "event_text": "山谷背阴处长着一片归元草。"},
        ],
    },
    {
        "name": "断剑崖",
        "description": "崖底堆满断剑残兵，剑修常来此寻觅旧器余辉。",
        "max_minutes": 45,
        "min_realm_stage": "炼气",
        "min_realm_layer": 5,
        "min_combat_power": 850,
        "event_pool": [
            {"name": "剑煞回潮", "description": "残剑煞气忽然倒卷，你虽被震退，却也在裂缝里捡到灵石碎袋。", "event_type": "danger", "weight": 3, "stone_bonus_min": 12, "stone_bonus_max": 28, "stone_loss_min": 6, "stone_loss_max": 16},
            {"name": "残碑拓影", "description": "你在半截石碑上拓出一页残谱。", "event_type": "recipe", "weight": 3, "bonus_reward_kind": "material", "bonus_reward_ref_id_name": "青罡剑谱残页", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 46},
            {"name": "旧器遗骸", "description": "乱石间压着一截带着余温的破损剑胚。", "event_type": "oddity", "weight": 2, "bonus_reward_kind": "material", "bonus_reward_ref_id_name": "破损青罡剑胚", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 18},
        ],
        "drops": [
            {"reward_kind": "material", "reward_ref_id_name": "寒铁矿", "quantity_min": 2, "quantity_max": 4, "weight": 5, "stone_reward": 6, "event_text": "残剑堆下埋着质地不错的寒铁矿。"},
            {"reward_kind": "material", "reward_ref_id_name": "赤炎晶砂", "quantity_min": 1, "quantity_max": 2, "weight": 4, "stone_reward": 8, "event_text": "剑痕摩擦地火，凝出了细碎的赤炎晶砂。"},
            {"reward_kind": "material", "reward_ref_id_name": "星辉砂", "quantity_min": 1, "quantity_max": 2, "weight": 2, "stone_reward": 12, "event_text": "夜色落入崖底，你拾到了闪烁的星辉砂。"},
        ],
    },
    {
        "name": "迷雾药园",
        "description": "雾气缭绕的废弃药园，药性温和却不失灵气。",
        "max_minutes": 40,
        "min_realm_stage": "炼气",
        "min_realm_layer": 3,
        "min_combat_power": 720,
        "event_pool": [
            {"name": "药灵惊走", "description": "药园深处有药灵窜过，追逐间踩断了几根枯藤，也抖落一些灵石。", "event_type": "danger", "weight": 2, "stone_bonus_min": 10, "stone_bonus_max": 22, "stone_loss_min": 2, "stone_loss_max": 8},
            {"name": "丹谱旧页", "description": "药架夹层里竟压着一张回春丹残页。", "event_type": "recipe", "weight": 3, "bonus_reward_kind": "material", "bonus_reward_ref_id_name": "回春丹谱残页", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 48},
            {"name": "露华未散", "description": "清晨雾气还未散尽，草叶上挂着可入丹的灵露。", "event_type": "fortune", "weight": 3},
        ],
        "drops": [
            {"reward_kind": "material", "reward_ref_id_name": "归元草", "quantity_min": 2, "quantity_max": 4, "weight": 6, "stone_reward": 5, "event_text": "你在药园边角采到几株完整的归元草。"},
            {"reward_kind": "material", "reward_ref_id_name": "凝露花", "quantity_min": 1, "quantity_max": 3, "weight": 5, "stone_reward": 8, "event_text": "花圃中央还活着几朵凝露花。"},
            {"reward_kind": "material", "reward_ref_id_name": "灵木芯", "quantity_min": 1, "quantity_max": 2, "weight": 3, "stone_reward": 5, "event_text": "旧药架中剥出了仍有药香的灵木芯。"},
        ],
    },
    {
        "name": "雷火符窟",
        "description": "窟内常有雷火共振，十分适合寻符材，但稍不留神就会被反噬。",
        "max_minutes": 50,
        "min_realm_stage": "筑基",
        "min_realm_layer": 1,
        "min_combat_power": 1500,
        "event_pool": [
            {"name": "符火反噬", "description": "残符忽然炸裂，火星烫穿袖口，好在地上散落了些灵石。", "event_type": "danger", "weight": 3, "stone_bonus_min": 14, "stone_bonus_max": 30, "stone_loss_min": 6, "stone_loss_max": 18},
            {"name": "符谱显痕", "description": "石壁上显出一段旧符纹，你赶紧拓下一页残纸。", "event_type": "recipe", "weight": 3, "bonus_reward_kind": "material", "bonus_reward_ref_id_name": "雷火符谱残页", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 42},
            {"name": "钟纹残迹", "description": "窟深处的石壁还有半面金钟纹路。", "event_type": "recipe", "weight": 2, "bonus_reward_kind": "material", "bonus_reward_ref_id_name": "金钟符谱残页", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 34},
        ],
        "drops": [
            {"reward_kind": "material", "reward_ref_id_name": "雷击木", "quantity_min": 1, "quantity_max": 3, "weight": 5, "stone_reward": 8, "event_text": "窟顶断木带着焦痕，是上好的雷击木。"},
            {"reward_kind": "material", "reward_ref_id_name": "赤炎晶砂", "quantity_min": 1, "quantity_max": 3, "weight": 5, "stone_reward": 7, "event_text": "石缝里凝着一层赤红晶砂。"},
            {"reward_kind": "material", "reward_ref_id_name": "星辉砂", "quantity_min": 1, "quantity_max": 1, "weight": 2, "stone_reward": 10, "event_text": "雷火碰撞后，窟底留下了一抹星辉砂。"},
        ],
    },
    {
        "name": "玄龟古潭",
        "description": "潭水极深，潭底不时浮出古盾残片与地脉灵气。",
        "max_minutes": 50,
        "min_realm_stage": "筑基",
        "min_realm_layer": 2,
        "min_combat_power": 1800,
        "event_pool": [
            {"name": "水压暗涌", "description": "古潭忽起暗流，你被逼得连退几步，腰间灵石也被卷走少许。", "event_type": "danger", "weight": 3, "stone_bonus_min": 16, "stone_bonus_max": 28, "stone_loss_min": 8, "stone_loss_max": 20},
            {"name": "古盾残片", "description": "潭底泥沙里埋着一块仍有灵纹的盾片。", "event_type": "oddity", "weight": 2, "bonus_reward_kind": "material", "bonus_reward_ref_id_name": "破损玄龟盾片", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 16},
            {"name": "地脉回响", "description": "潭底有地脉回响，石缝间的岩芯纹理越发清晰。", "event_type": "fortune", "weight": 3},
        ],
        "drops": [
            {"reward_kind": "material", "reward_ref_id_name": "玄龟甲片", "quantity_min": 1, "quantity_max": 3, "weight": 5, "stone_reward": 8, "event_text": "你自潭边剥下几块保存完好的玄龟甲片。"},
            {"reward_kind": "material", "reward_ref_id_name": "地脉岩芯", "quantity_min": 1, "quantity_max": 2, "weight": 3, "stone_reward": 12, "event_text": "潭底石缝里藏着沉重的地脉岩芯。"},
            {"reward_kind": "material", "reward_ref_id_name": "凝露花", "quantity_min": 1, "quantity_max": 2, "weight": 3, "stone_reward": 6, "event_text": "古潭边缘竟生着耐寒的凝露花。"},
        ],
    },
]

DEFAULT_ACHIEVEMENTS = [
    {"achievement_key": "envelope_novice", "name": "福泽初现", "description": "累计发放 1 次灵石红包。", "metric_key": "red_envelope_sent_count", "target_value": 1, "sort_order": 10, "reward_config": {"spiritual_stone": 20}},
    {"achievement_key": "envelope_generous", "name": "散财有道", "description": "累计通过红包发出 500 灵石。", "metric_key": "red_envelope_sent_stone", "target_value": 500, "sort_order": 11, "reward_config": {"cultivation": 80, "reward_title_names": ["红尘初行者"]}},
    {"achievement_key": "duel_rookie", "name": "试锋一战", "description": "累计发起 1 场斗法。", "metric_key": "duel_initiated_count", "target_value": 1, "sort_order": 20, "reward_config": {"spiritual_stone": 18}},
    {"achievement_key": "duel_veteran", "name": "斗法常客", "description": "累计发起 20 场斗法。", "metric_key": "duel_initiated_count", "target_value": 20, "sort_order": 21, "reward_config": {"cultivation": 160, "reward_title_names": ["斗法常客"]}},
    {"achievement_key": "duel_first_win", "name": "首战告捷", "description": "累计赢下 1 场斗法。", "metric_key": "duel_win_count", "target_value": 1, "sort_order": 22, "reward_config": {"spiritual_stone": 30}},
    {"achievement_key": "duel_ten_wins", "name": "胜势渐成", "description": "累计赢下 10 场斗法。", "metric_key": "duel_win_count", "target_value": 10, "sort_order": 23, "reward_config": {"cultivation": 180, "reward_title_names": ["小有机缘"]}},
    {"achievement_key": "duel_hardened", "name": "百折不挠", "description": "累计经历 10 场斗法失利。", "metric_key": "duel_loss_count", "target_value": 10, "sort_order": 24, "reward_config": {"spiritual_stone": 66, "reward_title_names": ["百折不挠"]}},
    {"achievement_key": "rob_novice", "name": "顺手牵机缘", "description": "累计尝试偷窃 1 次。", "metric_key": "rob_attempt_count", "target_value": 1, "sort_order": 30, "reward_config": {"spiritual_stone": 16}},
    {"achievement_key": "rob_success", "name": "夺宝老手", "description": "累计偷窃成功 10 次。", "metric_key": "rob_success_count", "target_value": 10, "sort_order": 31, "reward_config": {"cultivation": 180, "reward_title_names": ["夺宝老手"]}},
    {"achievement_key": "gift_kindness", "name": "同道相助", "description": "累计赠送 300 灵石。", "metric_key": "gift_sent_stone", "target_value": 300, "sort_order": 40, "reward_config": {"cultivation": 100}},
    {"achievement_key": "craft_first_success", "name": "炉火初明", "description": "累计成功炼制 1 次。", "metric_key": "craft_success_count", "target_value": 1, "sort_order": 50, "reward_config": {"spiritual_stone": 28}},
    {"achievement_key": "craft_ten_success", "name": "炼器熟手", "description": "累计成功炼制 10 次。", "metric_key": "craft_success_count", "target_value": 10, "sort_order": 51, "reward_config": {"cultivation": 180, "reward_title_names": ["炼器熟手"]}},
    {"achievement_key": "repair_master", "name": "残器归真", "description": "累计成功修复 1 件破损法宝。", "metric_key": "repair_success_count", "target_value": 1, "sort_order": 52, "reward_config": {"spiritual_stone": 120, "titles": []}},
    {"achievement_key": "explore_ten", "name": "秘境行者", "description": "累计完成 10 次秘境探索。", "metric_key": "exploration_count", "target_value": 10, "sort_order": 60, "reward_config": {"cultivation": 120, "reward_title_names": ["秘境行者"]}},
    {"achievement_key": "explore_recipe", "name": "残页搜罗者", "description": "累计获得 5 次配方残页。", "metric_key": "exploration_recipe_drop_count", "target_value": 5, "sort_order": 61, "reward_config": {"spiritual_stone": 88}},
]

SEED_QUALITY_LEVELS = {
    "凡品": 1,
    "下品": 2,
    "中品": 3,
    "上品": 4,
    "极品": 5,
    "仙品": 6,
    "先天至宝": 7,
}

SEED_MATERIAL_BLUEPRINTS = {
    "下品": [
        "青霜铁", "灵桑皮", "暖玉粉", "风鹤羽", "赤流砂",
        "寒水露", "厚土晶", "玄松脂", "离火絮", "断岳石",
    ],
    "中品": [
        "星河砂", "玄龟骨晶", "云母银丝", "赤霄铜髓", "灵雾草心",
        "霜华露珠", "金乌羽粉", "沧浪冰魄", "太乙木心", "断雷砂",
    ],
    "上品": [
        "太虚陨铁", "九曲灵丝", "地脉玉髓", "龙鳞铁片", "天游羽晶",
        "幻月晶核", "紫焰琉砂", "天游莲芯", "玄冰胆", "星陨木根",
    ],
    "极品": [
        "玄天乌金", "九霄凤羽", "太阴寒髓", "炽阳赤晶", "镇岳龙骨",
        "无垢净沙", "璇玑星砂", "幽冥墨玉", "太华灵液", "万象青金",
    ],
    "仙品": [
        "仙凰真羽", "苍穹雷髓", "九转金液", "造化玉露", "混元息壤",
        "玄冥冰魄", "太清星尘", "赤霄凤血", "长生灵藤心", "太初光砂",
    ],
    "先天至宝": [
        "先天混沌石", "太初紫气晶", "鸿蒙天髓", "造化青莲瓣", "周天星核",
        "玄黄母气", "大罗神铁", "无相天露", "太始龙骨", "元始真砂",
    ],
}

ARTIFACT_SET_BLUEPRINTS = [
    {
        "name": "青霄巡天套",
        "description": "轻灵迅捷的正道剑修套装，重攻伐与腾挪。",
        "required_count": 2,
        "attack_bonus": 10,
        "body_movement_bonus": 12,
        "duel_rate_bonus": 4,
        "items": [
            {
                "name": "青霄巡天剑",
                "rarity": "下品",
                "artifact_type": "battle",
                "artifact_role": "battle",
                "equip_slot": "weapon",
                "attack_bonus": 24,
                "body_movement_bonus": 6,
                "duel_rate_bonus": 4,
                "description": "剑锋轻颤如燕掠青云，专为快攻而生。",
                "combat_config": {"passives": [{"name": "青霄掠影", "kind": "extra_damage", "chance": 24, "flat_damage": 14, "ratio_percent": 18, "text": "青霄巡天剑借身法加速，一剑斜斩而下。"}]},
                "materials": [("青霜铁", 3), ("风鹤羽", 2), ("赤流砂", 1)],
                "success": 64,
            },
            {
                "name": "青霄巡天甲",
                "rarity": "下品",
                "artifact_type": "support",
                "artifact_role": "guardian",
                "equip_slot": "chest",
                "defense_bonus": 18,
                "qi_blood_bonus": 38,
                "body_movement_bonus": 4,
                "description": "以灵桑皮与暖玉粉熬炼而成，轻而不薄。",
                "combat_config": {"passives": [{"name": "巡天气罩", "kind": "shield", "chance": 20, "flat_shield": 18, "ratio_percent": 14, "text": "青霄巡天甲化出一层薄薄气罩，将余波卸去。"}]},
                "materials": [("灵桑皮", 3), ("暖玉粉", 1), ("厚土晶", 1)],
                "success": 62,
            },
            {
                "name": "青霄踏云靴",
                "rarity": "下品",
                "artifact_type": "support",
                "artifact_role": "movement",
                "equip_slot": "boots",
                "defense_bonus": 8,
                "body_movement_bonus": 18,
                "duel_rate_bonus": 3,
                "description": "落地无尘，最擅错步改位。",
                "combat_config": {"passives": [{"name": "踏云错位", "kind": "dodge", "chance": 24, "dodge_bonus": 18, "duration": 1, "text": "青霄踏云靴轻轻一点，人已错开半步。"}]},
                "materials": [("风鹤羽", 2), ("离火絮", 2), ("寒水露", 1)],
                "success": 63,
            },
        ],
    },
    {
        "name": "玄岳镇海套",
        "description": "以守为攻的厚重战套，适合护体与反打路线。",
        "required_count": 2,
        "defense_bonus": 14,
        "qi_blood_bonus": 66,
        "duel_rate_bonus": 3,
        "items": [
            {
                "name": "玄岳镇海枪",
                "rarity": "中品",
                "artifact_type": "battle",
                "artifact_role": "guardian",
                "equip_slot": "weapon",
                "attack_bonus": 30,
                "defense_bonus": 10,
                "description": "枪势沉稳如山岳压潮，破招时极具压迫。",
                "combat_config": {"passives": [{"name": "岳势横扫", "kind": "extra_damage", "chance": 28, "flat_damage": 20, "ratio_percent": 20, "text": "玄岳镇海枪横扫一轮，枪势压得对手难以喘息。"}]},
                "materials": [("星河砂", 2), ("玄龟骨晶", 2), ("断雷砂", 1)],
                "success": 58,
            },
            {
                "name": "玄岳护腿",
                "rarity": "中品",
                "artifact_type": "support",
                "artifact_role": "guardian",
                "equip_slot": "legs",
                "defense_bonus": 22,
                "qi_blood_bonus": 56,
                "body_movement_bonus": 4,
                "description": "腿部沉稳若磐石，硬撼重击而不乱。",
                "combat_config": {"passives": [{"name": "镇岳稳身", "kind": "guard", "chance": 26, "defense_ratio_percent": 20, "duration": 1, "text": "玄岳护腿灌入地脉之力，硬生生立稳脚步。"}]},
                "materials": [("玄龟骨晶", 2), ("太乙木心", 1), ("云母银丝", 2)],
                "success": 56,
            },
            {
                "name": "玄岳镇心佩",
                "rarity": "中品",
                "artifact_type": "support",
                "artifact_role": "support",
                "equip_slot": "necklace",
                "defense_bonus": 12,
                "true_yuan_bonus": 42,
                "cultivation_bonus": 8,
                "description": "佩玉厚润，能稳住真元与心神。",
                "combat_config": {"passives": [{"name": "镇海归元", "kind": "heal", "chance": 20, "flat_heal": 18, "ratio_percent": 12, "text": "玄岳镇心佩泛起清光，缓缓抚平受创经脉。"}]},
                "materials": [("霜华露珠", 2), ("沧浪冰魄", 1), ("云母银丝", 2)],
                "success": 57,
            },
        ],
    },
    {
        "name": "夜魇逐命套",
        "description": "邪道奇袭套装，强调爆发、闪避与蚕食真元。",
        "required_count": 2,
        "attack_bonus": 16,
        "duel_rate_bonus": 6,
        "body_movement_bonus": 10,
        "items": [
            {
                "name": "夜魇夺命刃",
                "rarity": "上品",
                "artifact_type": "battle",
                "artifact_role": "battle",
                "equip_slot": "weapon",
                "attack_bonus": 42,
                "fortune_bonus": 6,
                "duel_rate_bonus": 7,
                "description": "刀身细窄，最擅在死角递出夺命一击。",
                "combat_config": {"passives": [{"name": "夜魇追魂", "kind": "armor_break", "chance": 32, "defense_ratio_percent": 20, "duration": 2, "text": "夜魇夺命刃贴着护体缝隙一抹而过，灵罡顿时虚浮。"}]},
                "materials": [("太虚陨铁", 2), ("紫焰琉砂", 2), ("幻月晶核", 1)],
                "success": 52,
            },
            {
                "name": "夜魇潜影履",
                "rarity": "上品",
                "artifact_type": "support",
                "artifact_role": "movement",
                "equip_slot": "boots",
                "defense_bonus": 12,
                "body_movement_bonus": 28,
                "duel_rate_bonus": 6,
                "description": "步落无声，残影却能扰乱神识。",
                "combat_config": {"passives": [{"name": "潜影迷踪", "kind": "dodge", "chance": 30, "dodge_bonus": 24, "duration": 1, "text": "夜魇潜影履轻点地面，身形已隐入一缕暗影。"}]},
                "materials": [("九曲灵丝", 2), ("天游羽晶", 2), ("幻月晶核", 1)],
                "success": 53,
            },
            {
                "name": "夜魇摄魂链",
                "rarity": "上品",
                "artifact_type": "support",
                "artifact_role": "support",
                "equip_slot": "necklace",
                "attack_bonus": 16,
                "divine_sense_bonus": 18,
                "true_yuan_bonus": 36,
                "description": "细链如蛇，能牵动对手神魂起伏。",
                "combat_config": {"passives": [{"name": "摄魂乱念", "kind": "burn", "chance": 24, "flat_damage": 18, "ratio_percent": 14, "duration": 2, "text": "夜魇摄魂链忽然一紧，对手神魂如被细火炙烤。"}]},
                "materials": [("龙鳞铁片", 1), ("玄冰胆", 1), ("紫焰琉砂", 2)],
                "success": 50,
            },
        ],
    },
    {
        "name": "星河归元套",
        "description": "偏悟性与修炼的高阶法套，适合稳健积累。",
        "required_count": 3,
        "cultivation_bonus": 18,
        "comprehension_bonus": 12,
        "true_yuan_bonus": 88,
        "items": [
            {
                "name": "星河归元冠",
                "rarity": "极品",
                "artifact_type": "support",
                "artifact_role": "support",
                "equip_slot": "helmet",
                "comprehension_bonus": 18,
                "divine_sense_bonus": 18,
                "cultivation_bonus": 10,
                "description": "戴冠观星，神识更易沉入周天运转。",
                "combat_config": {"passives": [{"name": "星河静神", "kind": "heal", "chance": 22, "flat_heal": 24, "ratio_percent": 18, "text": "星河归元冠垂下细碎星芒，令心神与经脉同时平稳。"}]},
                "materials": [("玄天乌金", 1), ("璇玑星砂", 2), ("太华灵液", 1)],
                "success": 46,
            },
            {
                "name": "星河归元袍",
                "rarity": "极品",
                "artifact_type": "support",
                "artifact_role": "guardian",
                "equip_slot": "chest",
                "defense_bonus": 28,
                "qi_blood_bonus": 88,
                "cultivation_bonus": 8,
                "description": "法袍绣满周天星纹，守势圆融。",
                "combat_config": {"passives": [{"name": "周天回环", "kind": "shield", "chance": 24, "flat_shield": 30, "ratio_percent": 20, "text": "星河归元袍星纹齐亮，护体之力连成一圈。"}]},
                "materials": [("九霄凤羽", 1), ("太阴寒髓", 1), ("万象青金", 2)],
                "success": 45,
            },
            {
                "name": "星河归元环",
                "rarity": "极品",
                "artifact_type": "support",
                "artifact_role": "support",
                "equip_slot": "ring",
                "true_yuan_bonus": 96,
                "fortune_bonus": 10,
                "cultivation_bonus": 12,
                "description": "环内刻着归元纹，最适合久战回气。",
                "combat_config": {"passives": [{"name": "归元回潮", "kind": "heal", "chance": 18, "flat_heal": 26, "ratio_percent": 20, "text": "星河归元环轻震一声，真元回潮般涌回丹田。"}]},
                "materials": [("无垢净沙", 2), ("璇玑星砂", 2), ("幽冥墨玉", 1)],
                "success": 44,
            },
        ],
    },
    {
        "name": "紫宸天阙套",
        "description": "仙品天庭遗套，兼顾攻伐、护体与裂空机动。",
        "required_count": 3,
        "attack_bonus": 22,
        "defense_bonus": 18,
        "duel_rate_bonus": 8,
        "items": [
            {
                "name": "紫宸天刀",
                "rarity": "仙品",
                "artifact_type": "battle",
                "artifact_role": "battle",
                "equip_slot": "weapon",
                "attack_bonus": 58,
                "true_yuan_bonus": 66,
                "duel_rate_bonus": 8,
                "description": "刀势可撕开灵压，斩出一道短暂裂缝。",
                "combat_config": {"passives": [{"name": "裂空斩", "kind": "extra_damage", "chance": 34, "flat_damage": 30, "ratio_percent": 26, "text": "紫宸天刀凌空一斩，竟将灵气生生切开一道缝隙。"}]},
                "materials": [("仙凰真羽", 1), ("苍穹雷髓", 1), ("赤霄凤血", 1), ("太初光砂", 1)],
                "success": 36,
                "broadcast": True,
            },
            {
                "name": "紫宸战铠",
                "rarity": "仙品",
                "artifact_type": "support",
                "artifact_role": "guardian",
                "equip_slot": "chest",
                "defense_bonus": 42,
                "qi_blood_bonus": 132,
                "body_movement_bonus": 10,
                "description": "战铠内藏天阙旧阵，能缓冲重创。",
                "combat_config": {"passives": [{"name": "阙门护身", "kind": "shield", "chance": 28, "flat_shield": 42, "ratio_percent": 24, "text": "紫宸战铠外层阵纹迸亮，将巨力一层层削去。"}]},
                "materials": [("混元息壤", 1), ("玄冥冰魄", 1), ("九转金液", 1), ("长生灵藤心", 1)],
                "success": 35,
                "broadcast": True,
            },
            {
                "name": "紫宸飞履",
                "rarity": "仙品",
                "artifact_type": "support",
                "artifact_role": "movement",
                "equip_slot": "boots",
                "defense_bonus": 18,
                "body_movement_bonus": 36,
                "duel_rate_bonus": 8,
                "description": "一念踏空，落点可在数丈之外。",
                "combat_config": {"passives": [{"name": "飞履瞬空", "kind": "dodge", "chance": 32, "dodge_bonus": 32, "duration": 1, "text": "紫宸飞履一踏而空，身形似乎在原地消失了一瞬。"}]},
                "materials": [("造化玉露", 1), ("太清星尘", 1), ("仙凰真羽", 1), ("苍穹雷髓", 1)],
                "success": 38,
                "broadcast": True,
            },
        ],
    },
    {
        "name": "太初大道套",
        "description": "先天至宝级大道遗装，兼具大道护持与绝巅杀伐。",
        "required_count": 3,
        "attack_bonus": 30,
        "defense_bonus": 26,
        "breakthrough_bonus": 18,
        "items": [
            {
                "name": "太初道剑",
                "rarity": "先天至宝",
                "artifact_type": "battle",
                "artifact_role": "battle",
                "equip_slot": "weapon",
                "attack_bonus": 72,
                "comprehension_bonus": 24,
                "duel_rate_bonus": 10,
                "description": "剑出无声，却像天地本身在轻轻校正一切偏差。",
                "combat_config": {"passives": [{"name": "大道裁断", "kind": "armor_break", "chance": 36, "defense_ratio_percent": 28, "duration": 2, "text": "太初道剑轻轻一点，对手护体就像被天地法则直接削去一层。"}]},
                "materials": [("先天混沌石", 1), ("太初紫气晶", 1), ("大罗神铁", 1), ("元始真砂", 1)],
                "success": 24,
                "broadcast": True,
            },
            {
                "name": "太初道甲",
                "rarity": "先天至宝",
                "artifact_type": "support",
                "artifact_role": "guardian",
                "equip_slot": "chest",
                "defense_bonus": 58,
                "qi_blood_bonus": 188,
                "breakthrough_bonus": 10,
                "description": "道纹如水流淌，护体之时仿佛立于大道中央。",
                "combat_config": {"passives": [{"name": "大道垂护", "kind": "shield", "chance": 30, "flat_shield": 56, "ratio_percent": 28, "text": "太初道甲上的古老道纹同时亮起，护体光幕层层叠起。"}]},
                "materials": [("鸿蒙天髓", 1), ("造化青莲瓣", 1), ("玄黄母气", 1), ("太始龙骨", 1)],
                "success": 22,
                "broadcast": True,
            },
            {
                "name": "太初道环",
                "rarity": "先天至宝",
                "artifact_type": "support",
                "artifact_role": "support",
                "equip_slot": "ring",
                "true_yuan_bonus": 168,
                "fortune_bonus": 24,
                "cultivation_bonus": 18,
                "description": "一环在指，周天万象都像慢了半拍。",
                "combat_config": {"passives": [{"name": "一炁回环", "kind": "heal", "chance": 24, "flat_heal": 46, "ratio_percent": 28, "text": "太初道环轻轻一震，体内一炁周流不绝。"}]},
                "materials": [("周天星核", 1), ("无相天露", 1), ("先天混沌石", 1), ("鸿蒙天髓", 1)],
                "success": 23,
                "broadcast": True,
            },
        ],
    },
]

PILL_BLUEPRINTS = [
    {"name": "养元凝魄丹", "rarity": "下品", "pill_type": "cultivation", "effect_value": 160, "poison_delta": 2, "description": "适合炼气末期稳步冲关。", "materials": [("青霜铁", 1), ("寒水露", 2), ("暖玉粉", 1)], "success": 76},
    {"name": "踏云轻身丹", "rarity": "中品", "pill_type": "body_movement", "effect_value": 18, "poison_delta": 3, "description": "服后筋骨轻灵，腾挪更快。", "materials": [("云母银丝", 1), ("霜华露珠", 2), ("灵雾草心", 1)], "success": 68},
    {"name": "玄火锻骨丹", "rarity": "中品", "pill_type": "bone", "effect_value": 16, "poison_delta": 4, "description": "药性猛烈，适合淬骨强身。", "materials": [("赤霄铜髓", 2), ("金乌羽粉", 1), ("断雷砂", 1)], "success": 62},
    {"name": "天机明神丹", "rarity": "上品", "pill_type": "divine_sense", "effect_value": 22, "poison_delta": 4, "description": "可短时极大活跃神识。", "materials": [("幻月晶核", 1), ("玄冰胆", 1), ("天游莲芯", 1)], "success": 54},
    {"name": "九霄御气丹", "rarity": "极品", "pill_type": "true_yuan", "effect_value": 88, "poison_delta": 5, "description": "用于长时斗法前的真元储备。", "materials": [("九霄凤羽", 1), ("太华灵液", 1), ("璇玑星砂", 1)], "success": 46},
    {"name": "福缘问心丹", "rarity": "极品", "pill_type": "fortune", "effect_value": 12, "poison_delta": 5, "description": "药效玄妙，偏向增机缘。", "materials": [("无垢净沙", 1), ("幽冥墨玉", 1), ("太阴寒髓", 1)], "success": 45},
    {"name": "长生回命丹", "rarity": "仙品", "pill_type": "qi_blood", "effect_value": 168, "poison_delta": 6, "description": "可将气血与命火同时提起。", "materials": [("长生灵藤心", 1), ("造化玉露", 1), ("九转金液", 1)], "success": 38},
    {"name": "混元开天丹", "rarity": "先天至宝", "pill_type": "foundation", "effect_value": 22, "poison_delta": 8, "description": "对突破大境界有极高增幅。", "materials": [("太初紫气晶", 1), ("玄黄母气", 1), ("无相天露", 1)], "success": 24},
]

TALISMAN_BLUEPRINTS = [
    {"name": "御风符", "rarity": "下品", "attack_bonus": 8, "body_movement_bonus": 10, "duel_rate_bonus": 2, "description": "出手前贴上，脚下更轻。", "combat_config": {"skills": [{"name": "风行一瞬", "kind": "dodge", "chance": 30, "dodge_bonus": 16, "duration": 1, "text": "御风符一燃，身形轻得像被风托起。"}]}, "materials": [("风鹤羽", 2), ("寒水露", 1), ("离火絮", 1)], "success": 74},
    {"name": "护心符", "rarity": "中品", "defense_bonus": 14, "true_yuan_bonus": 18, "duel_rate_bonus": 2, "description": "稳住心脉与护体灵气。", "combat_config": {"skills": [{"name": "护心灵罩", "kind": "shield", "chance": 34, "flat_shield": 18, "ratio_percent": 16, "text": "护心符化作灵罩贴合胸口，挡下一轮冲击。"}]}, "materials": [("玄龟骨晶", 1), ("沧浪冰魄", 1), ("太乙木心", 1)], "success": 66},
    {"name": "镇岳符", "rarity": "上品", "defense_bonus": 20, "qi_blood_bonus": 32, "duel_rate_bonus": 3, "description": "专门对抗重击与冲撞。", "combat_config": {"skills": [{"name": "镇岳符壁", "kind": "guard", "chance": 30, "defense_ratio_percent": 22, "duration": 1, "text": "镇岳符化出岩壁似的厚重灵障，硬吃一击也不退。"}]}, "materials": [("地脉玉髓", 1), ("龙鳞铁片", 1), ("太虚陨铁", 1)], "success": 56},
    {"name": "摄魂符", "rarity": "极品", "attack_bonus": 22, "divine_sense_bonus": 22, "duel_rate_bonus": 4, "description": "一经引动，专攻神魂破绽。", "combat_config": {"skills": [{"name": "摄魂钉", "kind": "armor_break", "chance": 32, "defense_ratio_percent": 18, "duration": 2, "text": "摄魂符一亮，神识化作钉芒直接穿向灵台。"}]}, "materials": [("璇玑星砂", 1), ("幽冥墨玉", 1), ("玄天乌金", 1)], "success": 44},
    {"name": "裂空符", "rarity": "仙品", "attack_bonus": 28, "body_movement_bonus": 24, "duel_rate_bonus": 6, "description": "爆发时足以撕开短暂空隙。", "combat_config": {"skills": [{"name": "裂空步", "kind": "extra_damage", "chance": 34, "flat_damage": 26, "ratio_percent": 24, "text": "裂空符燃成一线黑痕，转瞬已经逼到身前。"}]}, "materials": [("苍穹雷髓", 1), ("太清星尘", 1), ("仙凰真羽", 1)], "success": 34},
    {"name": "化毒符", "rarity": "仙品", "defense_bonus": 18, "fortune_bonus": 10, "duel_rate_bonus": 4, "description": "可化去杂毒与一部分负面侵蚀。", "combat_config": {"skills": [{"name": "清晦灵洗", "kind": "heal", "chance": 24, "flat_heal": 30, "ratio_percent": 20, "text": "化毒符散出淡青灵光，将体内浊毒冲散大半。"}]}, "materials": [("造化玉露", 1), ("长生灵藤心", 1), ("玄冥冰魄", 1)], "success": 33},
    {"name": "太初神雷符", "rarity": "先天至宝", "attack_bonus": 36, "divine_sense_bonus": 24, "duel_rate_bonus": 8, "description": "先天神雷所成，出手便是绝杀起势。", "combat_config": {"skills": [{"name": "太初雷殛", "kind": "extra_damage", "chance": 36, "flat_damage": 36, "ratio_percent": 30, "text": "太初神雷符撕开长空，一道神雷直落而下。"}]}, "materials": [("太初紫气晶", 1), ("大罗神铁", 1), ("周天星核", 1)], "success": 22},
]

TECHNIQUE_BLUEPRINTS = [
    {"name": "青霄御风诀", "rarity": "下品", "technique_type": "movement", "description": "正道轻灵身法，讲究剑步合一。", "body_movement_bonus": 16, "duel_rate_bonus": 4, "combat_config": {"skills": [{"name": "御风借势", "kind": "dodge", "chance": 24, "dodge_bonus": 18, "duration": 1, "cost_true_yuan": 10, "text": "青霄御风诀顺势带起一阵清风，整个人贴着灵压边缘滑开。"}]}, "min_realm_stage": "炼气", "min_realm_layer": 7},
    {"name": "玄岳不动经", "rarity": "中品", "technique_type": "defense", "description": "以地脉沉息淬体，最适合硬接重手。", "defense_bonus": 18, "qi_blood_bonus": 52, "breakthrough_bonus": 4, "combat_config": {"skills": [{"name": "不动如岳", "kind": "guard", "chance": 28, "defense_ratio_percent": 24, "duration": 1, "cost_true_yuan": 14, "text": "玄岳不动经一沉，周身气机瞬间稳如山岳。"}]}, "min_realm_stage": "筑基", "min_realm_layer": 2},
    {"name": "夜魇夺魂录", "rarity": "上品", "technique_type": "attack", "description": "邪道追魂秘卷，强调神识压迫与破甲斩杀。", "attack_bonus": 20, "divine_sense_bonus": 14, "duel_rate_bonus": 6, "combat_config": {"skills": [{"name": "夺魂追斩", "kind": "armor_break", "chance": 30, "defense_ratio_percent": 18, "duration": 2, "cost_true_yuan": 18, "text": "夜魇夺魂录牵出一缕阴影，顺着护体缝隙猛然钻入。"}]}, "min_realm_stage": "结丹", "min_realm_layer": 1},
    {"name": "星河归元章", "rarity": "极品", "technique_type": "cultivation", "description": "以周天星河温养经脉，久修者真元最厚。", "comprehension_bonus": 12, "true_yuan_bonus": 68, "cultivation_bonus": 16, "breakthrough_bonus": 8, "combat_config": {"passives": [{"name": "归元长潮", "kind": "heal", "chance": 18, "flat_heal": 24, "ratio_percent": 18, "text": "星河归元章缓缓运转，真元与气血像潮水一样回涨。"}]}, "min_realm_stage": "元婴", "min_realm_layer": 2},
    {"name": "紫宸裂空经", "rarity": "仙品", "technique_type": "combat", "description": "天阙遗经，擅裂空突进与高压连斩。", "attack_bonus": 26, "body_movement_bonus": 22, "duel_rate_bonus": 8, "combat_config": {"skills": [{"name": "裂空天步", "kind": "extra_damage", "chance": 32, "flat_damage": 28, "ratio_percent": 26, "cost_true_yuan": 24, "text": "紫宸裂空经踏出一记短促破空步，下一瞬攻势已贴脸而来。"}]}, "min_realm_stage": "化神", "min_realm_layer": 2},
    {"name": "太初一炁经", "rarity": "先天至宝", "technique_type": "balanced", "description": "先天一炁归于本源，攻守修炼俱强。", "attack_bonus": 18, "defense_bonus": 18, "comprehension_bonus": 18, "true_yuan_bonus": 88, "cultivation_bonus": 20, "breakthrough_bonus": 12, "combat_config": {"passives": [{"name": "一炁周流", "kind": "heal", "chance": 24, "flat_heal": 34, "ratio_percent": 24, "text": "太初一炁经周流全身，一切损耗都被缓缓抚平。"}]}, "min_realm_stage": "须弥", "min_realm_layer": 1},
]

DEFAULT_ARTIFACT_SETS = [
    {key: value for key, value in blueprint.items() if key != "items"}
    for blueprint in ARTIFACT_SET_BLUEPRINTS
]

for quality_label, material_names in SEED_MATERIAL_BLUEPRINTS.items():
    DEFAULT_MATERIALS.extend(
        {
            "name": material_name,
            "quality_level": SEED_QUALITY_LEVELS[quality_label],
            "description": f"{quality_label}灵材【{material_name}】，多见于对应层级秘境，是炼器、炼丹、制符的常备核心素材。",
        }
        for material_name in material_names
    )

for blueprint in ARTIFACT_SET_BLUEPRINTS:
    for item in blueprint["items"]:
        DEFAULT_ARTIFACTS.append(
            {
                "name": item["name"],
                "rarity": item["rarity"],
                "artifact_type": item["artifact_type"],
                "artifact_role": item["artifact_role"],
                "equip_slot": item["equip_slot"],
                "artifact_set_name": blueprint["name"],
                "description": item["description"],
                "attack_bonus": item.get("attack_bonus", 0),
                "defense_bonus": item.get("defense_bonus", 0),
                "bone_bonus": item.get("bone_bonus", 0),
                "comprehension_bonus": item.get("comprehension_bonus", 0),
                "divine_sense_bonus": item.get("divine_sense_bonus", 0),
                "fortune_bonus": item.get("fortune_bonus", 0),
                "qi_blood_bonus": item.get("qi_blood_bonus", 0),
                "true_yuan_bonus": item.get("true_yuan_bonus", 0),
                "body_movement_bonus": item.get("body_movement_bonus", 0),
                "duel_rate_bonus": item.get("duel_rate_bonus", 0),
                "cultivation_bonus": item.get("cultivation_bonus", 0),
                "combat_config": item.get("combat_config", {}),
                "min_realm_stage": item.get("min_realm_stage"),
                "min_realm_layer": item.get("min_realm_layer", 1),
                "enabled": True,
            }
        )
        DEFAULT_RECIPES.append(
            {
                "name": f"{item['name']}炼制图",
                "recipe_kind": "artifact",
                "result_kind": "artifact",
                "result_name": item["name"],
                "result_quantity": 1,
                "base_success_rate": int(item.get("success", 60)),
                "broadcast_on_success": bool(item.get("broadcast", False)),
                "ingredients": [
                    {"material_name": material_name, "quantity": quantity}
                    for material_name, quantity in item.get("materials", [])
                ],
            }
        )

for pill in PILL_BLUEPRINTS:
    DEFAULT_PILLS.append(
        {
            "name": pill["name"],
            "rarity": pill["rarity"],
            "pill_type": pill["pill_type"],
            "description": pill["description"],
            "effect_value": pill["effect_value"],
            "poison_delta": pill["poison_delta"],
            "enabled": True,
        }
    )
    DEFAULT_RECIPES.append(
        {
            "name": f"{pill['name']}丹谱",
            "recipe_kind": "pill",
            "result_kind": "pill",
            "result_name": pill["name"],
            "result_quantity": 1,
            "base_success_rate": int(pill.get("success", 60)),
            "broadcast_on_success": False,
            "ingredients": [
                {"material_name": material_name, "quantity": quantity}
                for material_name, quantity in pill.get("materials", [])
            ],
        }
    )

for talisman in TALISMAN_BLUEPRINTS:
    DEFAULT_TALISMANS.append(
        {
            "name": talisman["name"],
            "rarity": talisman["rarity"],
            "description": talisman["description"],
            "attack_bonus": talisman.get("attack_bonus", 0),
            "defense_bonus": talisman.get("defense_bonus", 0),
            "bone_bonus": talisman.get("bone_bonus", 0),
            "comprehension_bonus": talisman.get("comprehension_bonus", 0),
            "divine_sense_bonus": talisman.get("divine_sense_bonus", 0),
            "fortune_bonus": talisman.get("fortune_bonus", 0),
            "qi_blood_bonus": talisman.get("qi_blood_bonus", 0),
            "true_yuan_bonus": talisman.get("true_yuan_bonus", 0),
            "body_movement_bonus": talisman.get("body_movement_bonus", 0),
            "duel_rate_bonus": talisman.get("duel_rate_bonus", 0),
            "effect_uses": talisman.get("effect_uses", 1),
            "combat_config": talisman.get("combat_config", {}),
            "enabled": True,
        }
    )
    DEFAULT_RECIPES.append(
        {
            "name": f"{talisman['name']}符谱",
            "recipe_kind": "talisman",
            "result_kind": "talisman",
            "result_name": talisman["name"],
            "result_quantity": 2,
            "base_success_rate": int(talisman.get("success", 60)),
            "broadcast_on_success": False,
            "ingredients": [
                {"material_name": material_name, "quantity": quantity}
                for material_name, quantity in talisman.get("materials", [])
            ],
        }
    )

DEFAULT_TECHNIQUES.extend(TECHNIQUE_BLUEPRINTS)
DEFAULT_TITLES.extend(
    [
        {"name": "剑宗真传", "description": "经剑宗长老首肯，已有真传气象。", "color": "#2563eb", "attack_bonus": 6, "body_movement_bonus": 4, "duel_rate_bonus": 3},
        {"name": "药王门生", "description": "对草木药性极熟，气机平和绵长。", "color": "#16a34a", "comprehension_bonus": 6, "true_yuan_bonus": 42, "cultivation_bonus": 4},
        {"name": "天机上客", "description": "常与天机阁论道，心神澄明。", "color": "#0f766e", "comprehension_bonus": 8, "divine_sense_bonus": 8},
        {"name": "魔宫行者", "description": "能在血煞中保持清醒，杀意更利。", "color": "#b91c1c", "attack_bonus": 8, "duel_rate_bonus": 4},
        {"name": "鬼府夜游", "description": "行走于阴影之间，出手总在死角。", "color": "#4c1d95", "body_movement_bonus": 8, "divine_sense_bonus": 4, "fortune_bonus": 4},
        {"name": "万毒不侵", "description": "毒息难侵，体内百脉更显稳固。", "color": "#15803d", "defense_bonus": 6, "qi_blood_bonus": 72, "fortune_bonus": 3},
    ]
)

DEFAULT_SECTS = [
    {
        "name": "太玄剑宗",
        "camp": "orthodox",
        "description": "以剑问道、以护苍生为宗旨，重视根骨、心性与实战。",
        "min_realm_stage": "筑基",
        "min_realm_layer": 2,
        "min_bone": 18,
        "min_comprehension": 16,
        "attack_bonus": 10,
        "body_movement_bonus": 8,
        "duel_rate_bonus": 4,
        "entry_hint": "只收剑心端正、敢于正面斗法之人。",
        "roles": [
            {"role_key": "leader", "role_name": "剑主", "attack_bonus": 16, "defense_bonus": 10, "duel_rate_bonus": 8, "cultivation_bonus": 6, "monthly_salary": 320, "can_publish_tasks": True, "sort_order": 1},
            {"role_key": "elder", "role_name": "镇峰长老", "attack_bonus": 12, "defense_bonus": 8, "duel_rate_bonus": 5, "cultivation_bonus": 4, "monthly_salary": 220, "can_publish_tasks": True, "sort_order": 2},
            {"role_key": "core", "role_name": "剑脉真传", "attack_bonus": 8, "defense_bonus": 6, "duel_rate_bonus": 4, "cultivation_bonus": 3, "monthly_salary": 150, "can_publish_tasks": False, "sort_order": 3},
            {"role_key": "inner_deacon", "role_name": "巡山执事", "attack_bonus": 6, "defense_bonus": 6, "duel_rate_bonus": 2, "cultivation_bonus": 2, "monthly_salary": 120, "can_publish_tasks": True, "sort_order": 4},
            {"role_key": "outer_deacon", "role_name": "护山执事", "attack_bonus": 4, "defense_bonus": 5, "duel_rate_bonus": 1, "cultivation_bonus": 2, "monthly_salary": 90, "can_publish_tasks": True, "sort_order": 5},
            {"role_key": "inner_disciple", "role_name": "内门剑修", "attack_bonus": 4, "defense_bonus": 3, "duel_rate_bonus": 1, "cultivation_bonus": 1, "monthly_salary": 56, "can_publish_tasks": False, "sort_order": 6},
            {"role_key": "outer_disciple", "role_name": "外门弟子", "attack_bonus": 2, "defense_bonus": 2, "duel_rate_bonus": 0, "cultivation_bonus": 1, "monthly_salary": 28, "can_publish_tasks": False, "sort_order": 7},
        ],
    },
    {
        "name": "药王谷",
        "camp": "orthodox",
        "description": "专研灵药、丹火与气血温养，讲究持久与稳健。",
        "min_realm_stage": "炼气",
        "min_realm_layer": 8,
        "min_comprehension": 20,
        "min_fortune": 16,
        "defense_bonus": 8,
        "cultivation_bonus": 10,
        "fortune_bonus": 8,
        "entry_hint": "不收浮躁好战之人，更看重悟性与药理天赋。",
        "roles": [
            {"role_key": "leader", "role_name": "谷主", "attack_bonus": 6, "defense_bonus": 14, "duel_rate_bonus": 2, "cultivation_bonus": 8, "monthly_salary": 300, "can_publish_tasks": True, "sort_order": 1},
            {"role_key": "elder", "role_name": "丹堂长老", "attack_bonus": 4, "defense_bonus": 10, "duel_rate_bonus": 2, "cultivation_bonus": 6, "monthly_salary": 220, "can_publish_tasks": True, "sort_order": 2},
            {"role_key": "core", "role_name": "药炉真传", "attack_bonus": 4, "defense_bonus": 8, "duel_rate_bonus": 1, "cultivation_bonus": 5, "monthly_salary": 160, "can_publish_tasks": False, "sort_order": 3},
            {"role_key": "inner_deacon", "role_name": "百草执事", "attack_bonus": 2, "defense_bonus": 6, "duel_rate_bonus": 1, "cultivation_bonus": 4, "monthly_salary": 120, "can_publish_tasks": True, "sort_order": 4},
            {"role_key": "outer_deacon", "role_name": "药圃执事", "attack_bonus": 1, "defense_bonus": 4, "duel_rate_bonus": 0, "cultivation_bonus": 3, "monthly_salary": 90, "can_publish_tasks": True, "sort_order": 5},
            {"role_key": "inner_disciple", "role_name": "内门药修", "attack_bonus": 1, "defense_bonus": 3, "duel_rate_bonus": 0, "cultivation_bonus": 2, "monthly_salary": 52, "can_publish_tasks": False, "sort_order": 6},
            {"role_key": "outer_disciple", "role_name": "试药弟子", "attack_bonus": 0, "defense_bonus": 2, "duel_rate_bonus": 0, "cultivation_bonus": 1, "monthly_salary": 24, "can_publish_tasks": False, "sort_order": 7},
        ],
    },
    {
        "name": "天机阁",
        "camp": "orthodox",
        "description": "洞察天机与神识妙用并重，擅长推演与布局。",
        "min_realm_stage": "结丹",
        "min_realm_layer": 1,
        "min_comprehension": 24,
        "min_divine_sense": 24,
        "defense_bonus": 4,
        "cultivation_bonus": 8,
        "fortune_bonus": 10,
        "entry_hint": "只有悟性与神识都足够出众者，才看得懂门前第一幅星图。",
        "roles": [
            {"role_key": "leader", "role_name": "阁主", "attack_bonus": 8, "defense_bonus": 8, "duel_rate_bonus": 6, "cultivation_bonus": 8, "monthly_salary": 360, "can_publish_tasks": True, "sort_order": 1},
            {"role_key": "elder", "role_name": "星盘长老", "attack_bonus": 6, "defense_bonus": 6, "duel_rate_bonus": 5, "cultivation_bonus": 6, "monthly_salary": 240, "can_publish_tasks": True, "sort_order": 2},
            {"role_key": "core", "role_name": "天机真传", "attack_bonus": 4, "defense_bonus": 4, "duel_rate_bonus": 4, "cultivation_bonus": 5, "monthly_salary": 170, "can_publish_tasks": False, "sort_order": 3},
            {"role_key": "inner_deacon", "role_name": "观星执事", "attack_bonus": 3, "defense_bonus": 3, "duel_rate_bonus": 2, "cultivation_bonus": 4, "monthly_salary": 120, "can_publish_tasks": True, "sort_order": 4},
            {"role_key": "outer_deacon", "role_name": "录图执事", "attack_bonus": 2, "defense_bonus": 2, "duel_rate_bonus": 1, "cultivation_bonus": 3, "monthly_salary": 90, "can_publish_tasks": True, "sort_order": 5},
            {"role_key": "inner_disciple", "role_name": "内门卜修", "attack_bonus": 1, "defense_bonus": 1, "duel_rate_bonus": 1, "cultivation_bonus": 2, "monthly_salary": 54, "can_publish_tasks": False, "sort_order": 6},
            {"role_key": "outer_disciple", "role_name": "引星弟子", "attack_bonus": 0, "defense_bonus": 1, "duel_rate_bonus": 0, "cultivation_bonus": 1, "monthly_salary": 26, "can_publish_tasks": False, "sort_order": 7},
        ],
    },
    {
        "name": "血煞魔宫",
        "camp": "heterodox",
        "description": "以杀养煞，重视血气、攻击与高压斗法。",
        "min_realm_stage": "筑基",
        "min_realm_layer": 4,
        "min_bone": 20,
        "min_fortune": 12,
        "attack_bonus": 14,
        "duel_rate_bonus": 6,
        "entry_hint": "不怕见血、不怕被围，方能踏入魔宫大门。",
        "roles": [
            {"role_key": "leader", "role_name": "宫主", "attack_bonus": 18, "defense_bonus": 8, "duel_rate_bonus": 10, "cultivation_bonus": 4, "monthly_salary": 340, "can_publish_tasks": True, "sort_order": 1},
            {"role_key": "elder", "role_name": "血煞长老", "attack_bonus": 14, "defense_bonus": 6, "duel_rate_bonus": 8, "cultivation_bonus": 3, "monthly_salary": 230, "can_publish_tasks": True, "sort_order": 2},
            {"role_key": "core", "role_name": "魔宫真种", "attack_bonus": 10, "defense_bonus": 4, "duel_rate_bonus": 6, "cultivation_bonus": 3, "monthly_salary": 160, "can_publish_tasks": False, "sort_order": 3},
            {"role_key": "inner_deacon", "role_name": "血卫执事", "attack_bonus": 8, "defense_bonus": 4, "duel_rate_bonus": 4, "cultivation_bonus": 2, "monthly_salary": 120, "can_publish_tasks": True, "sort_order": 4},
            {"role_key": "outer_deacon", "role_name": "煞堂执事", "attack_bonus": 6, "defense_bonus": 3, "duel_rate_bonus": 3, "cultivation_bonus": 1, "monthly_salary": 90, "can_publish_tasks": True, "sort_order": 5},
            {"role_key": "inner_disciple", "role_name": "内宫凶徒", "attack_bonus": 4, "defense_bonus": 2, "duel_rate_bonus": 2, "cultivation_bonus": 1, "monthly_salary": 56, "can_publish_tasks": False, "sort_order": 6},
            {"role_key": "outer_disciple", "role_name": "试煞者", "attack_bonus": 2, "defense_bonus": 1, "duel_rate_bonus": 1, "cultivation_bonus": 0, "monthly_salary": 28, "can_publish_tasks": False, "sort_order": 7},
        ],
    },
    {
        "name": "幽冥鬼府",
        "camp": "heterodox",
        "description": "行事诡谲，最擅影遁、摄魂与夜袭。",
        "min_realm_stage": "结丹",
        "min_realm_layer": 1,
        "min_divine_sense": 20,
        "min_fortune": 20,
        "body_movement_bonus": 12,
        "duel_rate_bonus": 6,
        "entry_hint": "看得见夜色中的第二层影子，才有资格敲响鬼府阴门。",
        "roles": [
            {"role_key": "leader", "role_name": "府君", "attack_bonus": 14, "defense_bonus": 8, "duel_rate_bonus": 10, "cultivation_bonus": 5, "monthly_salary": 330, "can_publish_tasks": True, "sort_order": 1},
            {"role_key": "elder", "role_name": "夜巡长老", "attack_bonus": 10, "defense_bonus": 6, "duel_rate_bonus": 8, "cultivation_bonus": 4, "monthly_salary": 220, "can_publish_tasks": True, "sort_order": 2},
            {"role_key": "core", "role_name": "摄魂真传", "attack_bonus": 8, "defense_bonus": 4, "duel_rate_bonus": 6, "cultivation_bonus": 4, "monthly_salary": 160, "can_publish_tasks": False, "sort_order": 3},
            {"role_key": "inner_deacon", "role_name": "引魂执事", "attack_bonus": 6, "defense_bonus": 3, "duel_rate_bonus": 4, "cultivation_bonus": 2, "monthly_salary": 118, "can_publish_tasks": True, "sort_order": 4},
            {"role_key": "outer_deacon", "role_name": "巡夜执事", "attack_bonus": 4, "defense_bonus": 2, "duel_rate_bonus": 3, "cultivation_bonus": 2, "monthly_salary": 88, "can_publish_tasks": True, "sort_order": 5},
            {"role_key": "inner_disciple", "role_name": "夜行弟子", "attack_bonus": 3, "defense_bonus": 2, "duel_rate_bonus": 2, "cultivation_bonus": 1, "monthly_salary": 52, "can_publish_tasks": False, "sort_order": 6},
            {"role_key": "outer_disciple", "role_name": "幽门杂徒", "attack_bonus": 1, "defense_bonus": 1, "duel_rate_bonus": 1, "cultivation_bonus": 0, "monthly_salary": 24, "can_publish_tasks": False, "sort_order": 7},
        ],
    },
    {
        "name": "万毒崖",
        "camp": "heterodox",
        "description": "百毒并修，重视耐毒、韧性与反制手段。",
        "min_realm_stage": "筑基",
        "min_realm_layer": 6,
        "min_comprehension": 18,
        "min_fortune": 18,
        "defense_bonus": 8,
        "fortune_bonus": 10,
        "entry_hint": "若连崖前第一缕毒雾都撑不过，就不必再往上走了。",
        "roles": [
            {"role_key": "leader", "role_name": "崖主", "attack_bonus": 8, "defense_bonus": 14, "duel_rate_bonus": 6, "cultivation_bonus": 5, "monthly_salary": 320, "can_publish_tasks": True, "sort_order": 1},
            {"role_key": "elder", "role_name": "毒师长老", "attack_bonus": 6, "defense_bonus": 10, "duel_rate_bonus": 5, "cultivation_bonus": 4, "monthly_salary": 220, "can_publish_tasks": True, "sort_order": 2},
            {"role_key": "core", "role_name": "百毒真传", "attack_bonus": 5, "defense_bonus": 8, "duel_rate_bonus": 4, "cultivation_bonus": 3, "monthly_salary": 150, "can_publish_tasks": False, "sort_order": 3},
            {"role_key": "inner_deacon", "role_name": "试毒执事", "attack_bonus": 3, "defense_bonus": 6, "duel_rate_bonus": 2, "cultivation_bonus": 2, "monthly_salary": 118, "can_publish_tasks": True, "sort_order": 4},
            {"role_key": "outer_deacon", "role_name": "药毒执事", "attack_bonus": 2, "defense_bonus": 4, "duel_rate_bonus": 1, "cultivation_bonus": 2, "monthly_salary": 88, "can_publish_tasks": True, "sort_order": 5},
            {"role_key": "inner_disciple", "role_name": "内门毒修", "attack_bonus": 2, "defense_bonus": 3, "duel_rate_bonus": 1, "cultivation_bonus": 1, "monthly_salary": 48, "can_publish_tasks": False, "sort_order": 6},
            {"role_key": "outer_disciple", "role_name": "试毒弟子", "attack_bonus": 1, "defense_bonus": 2, "duel_rate_bonus": 0, "cultivation_bonus": 1, "monthly_salary": 22, "can_publish_tasks": False, "sort_order": 7},
        ],
    },
]

DEFAULT_SCENES.extend(
    [
        {
            "name": "青木秘林",
            "description": "灵风流转的下品秘林，最适合打基础与寻觅轻灵材料。",
            "max_minutes": 36,
            "event_pool": [
                {"name": "旧剑匣遗痕", "description": "林间旧剑匣里压着一卷残旧炼图。", "event_type": "recipe", "weight": 3, "bonus_reward_kind": "recipe", "bonus_reward_ref_id_name": "青霄巡天剑炼制图", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 42},
                {"name": "风痕身法", "description": "古树年轮里藏着一段步法心得。", "event_type": "oddity", "weight": 2, "bonus_reward_kind": "technique", "bonus_reward_ref_id_name": "青霄御风诀", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 28},
                {"name": "枝影乱石", "description": "林中灵风卷石而起，险些打乱你的步伐。", "event_type": "danger", "weight": 3, "stone_bonus_min": 10, "stone_bonus_max": 24, "stone_loss_min": 4, "stone_loss_max": 10},
            ],
            "drops": [{"reward_kind": "material", "reward_ref_id_name": name, "quantity_min": 1, "quantity_max": 2, "weight": 4 + (10 - index), "stone_reward": 4, "event_text": f"你在青木秘林中采得一份【{name}】。"} for index, name in enumerate(SEED_MATERIAL_BLUEPRINTS["下品"], start=1)],
        },
        {
            "name": "玄潮古窟",
            "description": "中品矿窟深处有潮鸣回响，矿料与护身材料极多。",
            "max_minutes": 42,
            "event_pool": [
                {"name": "枪胚残图", "description": "矿壁夹层里卡着一张沉重枪图。", "event_type": "recipe", "weight": 3, "bonus_reward_kind": "recipe", "bonus_reward_ref_id_name": "玄岳镇海枪炼制图", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 38},
                {"name": "地息经文", "description": "地缝渗出的灵息里竟带着一段防御经文。", "event_type": "oddity", "weight": 2, "bonus_reward_kind": "technique", "bonus_reward_ref_id_name": "玄岳不动经", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 24},
                {"name": "暗潮回卷", "description": "暗潮裹着碎石回卷而来，你只来得及护住要害。", "event_type": "danger", "weight": 3, "stone_bonus_min": 14, "stone_bonus_max": 30, "stone_loss_min": 6, "stone_loss_max": 14},
            ],
            "drops": [{"reward_kind": "material", "reward_ref_id_name": name, "quantity_min": 1, "quantity_max": 2, "weight": 4 + (10 - index), "stone_reward": 6, "event_text": f"你在玄潮古窟中挖到一份【{name}】。"} for index, name in enumerate(SEED_MATERIAL_BLUEPRINTS["中品"], start=1)],
        },
        {
            "name": "魇月裂谷",
            "description": "上品裂谷常年被幻月照着，适合寻找暗袭与神魂材料。",
            "max_minutes": 48,
            "event_pool": [
                {"name": "夜刃图卷", "description": "裂谷深处漂着一页诡异刀图。", "event_type": "recipe", "weight": 3, "bonus_reward_kind": "recipe", "bonus_reward_ref_id_name": "夜魇夺命刃炼制图", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 34},
                {"name": "阴影秘页", "description": "你在断壁背面看到一段追魂秘法。", "event_type": "oddity", "weight": 2, "bonus_reward_kind": "technique", "bonus_reward_ref_id_name": "夜魇夺魂录", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 22},
                {"name": "魇月侵神", "description": "裂谷阴月忽明忽暗，让你的神识一阵刺痛。", "event_type": "danger", "weight": 3, "stone_bonus_min": 20, "stone_bonus_max": 40, "stone_loss_min": 10, "stone_loss_max": 20},
            ],
            "drops": [{"reward_kind": "material", "reward_ref_id_name": name, "quantity_min": 1, "quantity_max": 2, "weight": 4 + (10 - index), "stone_reward": 8, "event_text": f"你从魇月裂谷中截获一份【{name}】。"} for index, name in enumerate(SEED_MATERIAL_BLUEPRINTS["上品"], start=1)],
        },
        {
            "name": "星阙残庭",
            "description": "极品层级的残破仙庭，最容易捡到周天与归元类材料。",
            "max_minutes": 54,
            "event_pool": [
                {"name": "星袍织图", "description": "残庭石座上压着一页法袍织图。", "event_type": "recipe", "weight": 3, "bonus_reward_kind": "recipe", "bonus_reward_ref_id_name": "星河归元袍炼制图", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 30},
                {"name": "归元篇章", "description": "夜半星影错位间，竟显出一页归元经文。", "event_type": "oddity", "weight": 2, "bonus_reward_kind": "technique", "bonus_reward_ref_id_name": "星河归元章", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 20},
                {"name": "庭阵失衡", "description": "残庭阵纹突然逆卷，将你逼退数丈。", "event_type": "danger", "weight": 3, "stone_bonus_min": 26, "stone_bonus_max": 50, "stone_loss_min": 12, "stone_loss_max": 24},
            ],
            "drops": [{"reward_kind": "material", "reward_ref_id_name": name, "quantity_min": 1, "quantity_max": 2, "weight": 4 + (10 - index), "stone_reward": 10, "event_text": f"你在星阙残庭拾得一份【{name}】。"} for index, name in enumerate(SEED_MATERIAL_BLUEPRINTS["极品"], start=1)],
        },
        {
            "name": "紫宸天遗",
            "description": "仙品遗迹，常有裂空异象，出产天阙旧材。",
            "max_minutes": 58,
            "event_pool": [
                {"name": "天刀遗图", "description": "一截断碑后压着完整的仙刀炼图。", "event_type": "recipe", "weight": 3, "bonus_reward_kind": "recipe", "bonus_reward_ref_id_name": "紫宸天刀炼制图", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 26},
                {"name": "裂空真传", "description": "遗迹穹顶忽现一段天阙步法。", "event_type": "oddity", "weight": 2, "bonus_reward_kind": "technique", "bonus_reward_ref_id_name": "紫宸裂空经", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 18},
                {"name": "天阙坠雷", "description": "残破禁制坠下一缕神雷，震得经脉发麻。", "event_type": "danger", "weight": 3, "stone_bonus_min": 36, "stone_bonus_max": 66, "stone_loss_min": 18, "stone_loss_max": 32},
            ],
            "drops": [{"reward_kind": "material", "reward_ref_id_name": name, "quantity_min": 1, "quantity_max": 2, "weight": 4 + (10 - index), "stone_reward": 14, "event_text": f"你在紫宸天遗中截获一份【{name}】。"} for index, name in enumerate(SEED_MATERIAL_BLUEPRINTS["仙品"], start=1)],
        },
        {
            "name": "鸿蒙源海",
            "description": "先天至宝层级秘境，只在极少数机缘下才会开启。",
            "max_minutes": 60,
            "event_pool": [
                {"name": "大道剑图", "description": "源海之上浮起一卷大道剑图，转瞬又要散去。", "event_type": "recipe", "weight": 3, "bonus_reward_kind": "recipe", "bonus_reward_ref_id_name": "太初道剑炼制图", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 18},
                {"name": "一炁残章", "description": "海面涟漪化成一段古老经文，须在一息之间记住。", "event_type": "oddity", "weight": 2, "bonus_reward_kind": "technique", "bonus_reward_ref_id_name": "太初一炁经", "bonus_quantity_min": 1, "bonus_quantity_max": 1, "bonus_chance": 14},
                {"name": "源海逆浪", "description": "鸿蒙源海掀起一片逆浪，几乎将你的神识整个淹没。", "event_type": "danger", "weight": 3, "stone_bonus_min": 48, "stone_bonus_max": 88, "stone_loss_min": 24, "stone_loss_max": 40},
            ],
            "drops": [{"reward_kind": "material", "reward_ref_id_name": name, "quantity_min": 1, "quantity_max": 2, "weight": 4 + (10 - index), "stone_reward": 18, "event_text": f"你从鸿蒙源海中捞到一份【{name}】。"} for index, name in enumerate(SEED_MATERIAL_BLUEPRINTS["先天至宝"], start=1)],
        },
    ]
)

DEFAULT_MATERIALS.extend(EXTRA_MATERIALS)
DEFAULT_ARTIFACTS.extend(EXTRA_ARTIFACTS)
DEFAULT_PILLS.extend(
    {
        "name": pill["name"],
        "rarity": pill["rarity"],
        "pill_type": pill["pill_type"],
        "description": pill["description"],
        "effect_value": pill["effect_value"],
        "poison_delta": pill["poison_delta"],
        "enabled": True,
    }
    for pill in EXTRA_PILLS
)
DEFAULT_TALISMANS.extend(
    {
        "name": talisman["name"],
        "rarity": talisman["rarity"],
        "description": talisman["description"],
        "attack_bonus": talisman.get("attack_bonus", 0),
        "defense_bonus": talisman.get("defense_bonus", 0),
        "bone_bonus": talisman.get("bone_bonus", 0),
        "comprehension_bonus": talisman.get("comprehension_bonus", 0),
        "divine_sense_bonus": talisman.get("divine_sense_bonus", 0),
        "fortune_bonus": talisman.get("fortune_bonus", 0),
        "qi_blood_bonus": talisman.get("qi_blood_bonus", 0),
        "true_yuan_bonus": talisman.get("true_yuan_bonus", 0),
        "body_movement_bonus": talisman.get("body_movement_bonus", 0),
        "duel_rate_bonus": talisman.get("duel_rate_bonus", 0),
        "effect_uses": talisman.get("effect_uses", 1),
        "combat_config": talisman.get("combat_config", {}),
        "enabled": True,
    }
    for talisman in EXTRA_TALISMANS
)
DEFAULT_RECIPES.extend(EXTRA_RECIPES)
DEFAULT_SCENES.extend(EXTRA_SCENES)

BREAKTHROUGH_BASE_RATE = {
    "炼气": 45,
    "筑基": 38,
    "结丹": 32,
    "元婴": 26,
    "化神": 21,
    "须弥": 17,
    "芥子": 13,
    "混元一体": 0,
}
ROOT_QUALITY_ROLLS = [
    ("天灵根", 1),
    ("变异灵根", 1),
    ("极品灵根", 10),
    ("上品灵根", 20),
    ("中品灵根", 32),
    ("下品灵根", 28),
    ("废灵根", 8),
]
ITEM_STAT_FIELDS = (
    "attack_bonus",
    "defense_bonus",
    "bone_bonus",
    "comprehension_bonus",
    "divine_sense_bonus",
    "fortune_bonus",
    "qi_blood_bonus",
    "true_yuan_bonus",
    "body_movement_bonus",
    "duel_rate_bonus",
    "cultivation_bonus",
)


def _coerce_float(value: Any, default: float, minimum: float | None = None) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = float(default)
    if minimum is not None:
        result = max(result, minimum)
    return round(result, 4)


def _coerce_int(value: Any, default: int, minimum: int | None = None) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = int(default)
    if minimum is not None:
        result = max(result, minimum)
    return result


def _normalize_root_quality_value_rules(raw: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    # 后台可以覆盖灵根档位数值，但必须把缺失字段补齐成完整配置，前端展示和战斗结算才稳定。
    defaults = DEFAULT_SETTINGS["root_quality_value_rules"]
    rules = {}
    raw = raw if isinstance(raw, dict) else {}
    for name, level in ROOT_QUALITY_LEVELS.items():
        default_rule = defaults.get(name, {})
        source = raw.get(name) if isinstance(raw.get(name), dict) else {}
        rules[name] = {
            "level": level,
            "cultivation_rate": _coerce_float(source.get("cultivation_rate"), default_rule.get("cultivation_rate", 1.0), 0.1),
            "breakthrough_bonus": _coerce_int(source.get("breakthrough_bonus"), default_rule.get("breakthrough_bonus", 0)),
            "combat_factor": _coerce_float(source.get("combat_factor"), default_rule.get("combat_factor", 1.0), 0.1),
            "color": ROOT_QUALITY_COLORS[name],
        }
    return rules


def _normalize_item_quality_value_rules(raw: dict[str, Any] | None) -> dict[str, dict[str, float]]:
    # 物品品质倍率同样按“默认值 + 管理员覆盖”归一化，避免升级后旧配置缺字段。
    defaults = DEFAULT_SETTINGS["item_quality_value_rules"]
    rules = {}
    raw = raw if isinstance(raw, dict) else {}
    for name, default_rule in defaults.items():
        source = raw.get(name) if isinstance(raw.get(name), dict) else {}
        rules[name] = {
            "artifact_multiplier": _coerce_float(source.get("artifact_multiplier"), default_rule.get("artifact_multiplier", 1.0), 0.0),
            "pill_multiplier": _coerce_float(source.get("pill_multiplier"), default_rule.get("pill_multiplier", 1.0), 0.0),
            "talisman_multiplier": _coerce_float(source.get("talisman_multiplier"), default_rule.get("talisman_multiplier", 1.0), 0.0),
        }
    return rules


def _item_quality_multiplier(item: dict[str, Any] | None, item_kind: str) -> float:
    field_map = {
        "artifact": "artifact_multiplier",
        "pill": "pill_multiplier",
        "talisman": "talisman_multiplier",
    }
    rules = _normalize_item_quality_value_rules(
        get_xiuxian_settings().get("item_quality_value_rules", DEFAULT_SETTINGS["item_quality_value_rules"])
    )
    rarity = str((item or {}).get("rarity") or "凡品").strip() or "凡品"
    fallback = rules.get("凡品", DEFAULT_SETTINGS["item_quality_value_rules"]["凡品"])
    current = rules.get(rarity, fallback)
    value = current.get(field_map[item_kind], 1.0)
    return float(1.0 if value is None else value)


def _root_quality_payload(name: str | None) -> dict[str, Any]:
    rules = _normalize_root_quality_value_rules(
        get_xiuxian_settings().get("root_quality_value_rules", DEFAULT_SETTINGS["root_quality_value_rules"])
    )
    return rules.get(name or "中品灵根", rules["中品灵根"])


def _normalized_root_quality(profile: dict[str, Any] | None) -> str:
    profile = profile or {}

    raw_quality = str(profile.get("root_quality") or "").strip()
    if raw_quality in ROOT_QUALITY_LEVELS:
        return raw_quality
    if raw_quality == "地灵根":
        return "极品灵根"

    try:
        quality_level = int(profile.get("root_quality_level") or 0)
    except (TypeError, ValueError):
        quality_level = 0
    if quality_level > 0:
        for name, level in ROOT_QUALITY_LEVELS.items():
            if level == quality_level:
                return name

    root_type = str(profile.get("root_type") or "").strip()
    relation = str(profile.get("root_relation") or "").strip()
    try:
        root_bonus = int(profile.get("root_bonus") or 0)
    except (TypeError, ValueError):
        root_bonus = 0

    if root_type == "天灵根" or root_bonus >= ROOT_SPECIAL_BONUS["天灵根"]:
        return "天灵根"
    if root_type == "变异灵根":
        return "变异灵根"
    if root_type == "地灵根" or root_bonus >= ROOT_SPECIAL_BONUS["地灵根"]:
        return "极品灵根"
    if root_type == "双灵根":
        if relation == "相克" or root_bonus < 0:
            return "中品灵根"
        return "上品灵根"
    if root_type == "单灵根":
        return "中品灵根"
    return "中品灵根"


def _roll_root_quality() -> str:
    roll = random.randint(1, 100)
    cursor = 0
    for name, weight in ROOT_QUALITY_ROLLS:
        cursor += weight
        if roll <= cursor:
            return name
    return "中品灵根"


def _profile_root_elements(profile: dict[str, Any]) -> list[str]:
    elements = []
    primary = str(profile.get("root_primary") or "").strip()
    secondary = str(profile.get("root_secondary") or "").strip()
    if primary:
        elements.append(primary)
    if secondary and secondary != primary:
        elements.append(secondary)
    return elements


def _sum_item_stats(*effect_sets: dict[str, Any] | None) -> dict[str, float]:
    totals = {key: 0.0 for key in ITEM_STAT_FIELDS}
    for effects in effect_sets:
        for key in totals:
            totals[key] += float((effects or {}).get(key, 0) or 0)
    return totals


def _build_opening_stats(root_payload: dict[str, Any]) -> dict[str, int]:
    quality = _root_quality_payload(root_payload.get("root_quality"))
    quality_level = int(quality["level"])
    special_bonus = 4 if root_payload.get("root_type") == "天灵根" else 3 if root_payload.get("root_type") == "变异灵根" else 0
    bone = random.randint(10, 18) + quality_level + special_bonus
    comprehension = random.randint(10, 18) + quality_level + (2 if root_payload.get("root_type") in {"天灵根", "变异灵根"} else 0)
    divine_sense = random.randint(9, 17) + quality_level + (2 if root_payload.get("root_primary") in {"水", "雷", "风"} else 0)
    fortune = random.randint(8, 16) + quality_level + (2 if root_payload.get("root_quality") in {"极品灵根", "天灵根", "变异灵根"} else 0)
    willpower = random.randint(8, 15) + quality_level + (2 if root_payload.get("root_type") in {"地灵根", "天灵根"} else 0)
    charisma = random.randint(8, 15) + quality_level + (2 if root_payload.get("root_primary") in {"木", "水", "风"} else 0)
    karma = random.randint(8, 15) + quality_level + (2 if root_payload.get("root_quality") in {"上品灵根", "极品灵根", "天灵根", "变异灵根"} else 0)
    body_movement = random.randint(8, 15) + quality_level + (2 if root_payload.get("root_primary") in {"风", "火", "雷"} else 0)
    attack_power = random.randint(10, 18) + quality_level * 2 + (3 if root_payload.get("root_primary") in {"火", "金", "雷"} else 0)
    defense_power = random.randint(10, 18) + quality_level * 2 + (3 if root_payload.get("root_primary") in {"土", "金", "水"} else 0)
    qi_blood = 160 + bone * 12 + defense_power * 4 + quality_level * 20
    true_yuan = 140 + comprehension * 9 + divine_sense * 6 + quality_level * 18
    return {
        "bone": bone,
        "comprehension": comprehension,
        "divine_sense": divine_sense,
        "fortune": fortune,
        "willpower": willpower,
        "charisma": charisma,
        "karma": karma,
        "qi_blood": qi_blood,
        "true_yuan": true_yuan,
        "body_movement": body_movement,
        "attack_power": attack_power,
        "defense_power": defense_power,
    }


def _realm_progress_score(stage: str | None, layer: int | None) -> int:
    return max(realm_index(stage), 0) * 9 + max(int(layer or 1), 1) - 1


def _profile_growth_floor(profile: dict[str, Any]) -> dict[str, int]:
    quality = _root_quality_payload(_normalized_root_quality(profile))
    quality_level = int(quality["level"])
    quality_name = _normalized_root_quality(profile)
    root_type = str(profile.get("root_type") or "").strip()
    primary = str(profile.get("root_primary") or "").strip()
    progress = _realm_progress_score(profile.get("realm_stage"), profile.get("realm_layer"))
    special_bonus = 2 if root_type == "天灵根" else 1 if root_type == "变异灵根" else 0
    bone = 10 + quality_level + progress // 3 + (2 if primary in {"土", "金"} else 0) + special_bonus
    comprehension = 10 + quality_level + progress // 3 + (2 if primary in {"木", "水"} else 0) + special_bonus
    divine_sense = 9 + quality_level + progress // 4 + (2 if primary in {"雷", "风", "水"} else 0) + special_bonus
    fortune = 8 + quality_level + progress // 5 + (2 if root_type in {"地灵根", "天灵根", "变异灵根"} else 0)
    willpower = 8 + quality_level + progress // 4 + (2 if root_type in {"地灵根", "天灵根"} else 0)
    charisma = 8 + quality_level + progress // 5 + (2 if primary in {"木", "水", "风"} else 0)
    karma = 8 + quality_level + progress // 4 + (2 if quality_name in {"上品灵根", "极品灵根", "天灵根", "变异灵根"} else 0)
    attack_power = 10 + quality_level * 2 + progress // 2 + (3 if primary in {"火", "金", "雷"} else 0)
    defense_power = 10 + quality_level * 2 + progress // 2 + (3 if primary in {"土", "金", "水"} else 0)
    body_movement = 8 + quality_level + progress // 3 + (2 if primary in {"风", "火", "雷"} else 0)
    qi_blood = 160 + bone * 12 + defense_power * 4 + quality_level * 20 + progress * 18
    true_yuan = 140 + comprehension * 9 + divine_sense * 6 + quality_level * 18 + progress * 16
    return {
        "bone": bone,
        "comprehension": comprehension,
        "divine_sense": divine_sense,
        "fortune": fortune,
        "willpower": willpower,
        "charisma": charisma,
        "karma": karma,
        "qi_blood": qi_blood,
        "true_yuan": true_yuan,
        "body_movement": body_movement,
        "attack_power": attack_power,
        "defense_power": defense_power,
    }


def _apply_profile_growth_floor(tg: int, explicit_fields: set[str] | None = None) -> dict[str, Any]:
    profile = serialize_profile(get_profile(tg, create=False))
    if profile is None or not profile.get("consented"):
        raise ValueError("玩家不存在")
    explicit = set(explicit_fields or set())
    patch = {}
    for key, minimum in _profile_growth_floor(profile).items():
        if key in explicit:
            continue
        current = int(profile.get(key) or 0)
        if current < minimum:
            patch[key] = minimum
    if not patch:
        return profile
    updated = upsert_profile(tg, **patch)
    return serialize_profile(updated)


def _effective_stats(
    profile: dict[str, Any],
    artifact_effects: dict[str, Any] | None = None,
    talisman_effects: dict[str, Any] | None = None,
    sect_effects: dict[str, Any] | None = None,
    technique_effects: dict[str, Any] | None = None,
    title_effects: dict[str, Any] | None = None,
) -> dict[str, float]:
    totals = _sum_item_stats(artifact_effects, talisman_effects, sect_effects, technique_effects, title_effects)
    stats = {
        "bone": float(profile.get("bone", 0) or 0) + totals["bone_bonus"],
        "comprehension": float(profile.get("comprehension", 0) or 0) + totals["comprehension_bonus"],
        "divine_sense": float(profile.get("divine_sense", 0) or 0) + totals["divine_sense_bonus"],
        "fortune": float(profile.get("fortune", 0) or 0) + totals["fortune_bonus"],
        "willpower": float(profile.get("willpower", 0) or 0),
        "charisma": float(profile.get("charisma", 0) or 0),
        "karma": float(profile.get("karma", 0) or 0),
        "qi_blood": float(profile.get("qi_blood", 0) or 0) + totals["qi_blood_bonus"],
        "true_yuan": float(profile.get("true_yuan", 0) or 0) + totals["true_yuan_bonus"],
        "body_movement": float(profile.get("body_movement", 0) or 0) + totals["body_movement_bonus"],
        "attack_power": float(profile.get("attack_power", 0) or 0) + totals["attack_bonus"],
        "defense_power": float(profile.get("defense_power", 0) or 0) + totals["defense_bonus"],
        "duel_rate_bonus": totals["duel_rate_bonus"],
        "cultivation_bonus": totals["cultivation_bonus"],
    }
    stats["qi_blood"] = max(stats["qi_blood"], 1.0)
    stats["true_yuan"] = max(stats["true_yuan"], 1.0)
    return stats


def resolve_technique_effects(
    profile: dict[str, Any],
    technique: dict[str, Any] | None,
    opponent_profile: dict[str, Any] | None = None,
) -> dict[str, float]:
    if technique is None:
        return {
            "attack_bonus": 0.0,
            "defense_bonus": 0.0,
            "bone_bonus": 0.0,
            "comprehension_bonus": 0.0,
            "divine_sense_bonus": 0.0,
            "fortune_bonus": 0.0,
            "qi_blood_bonus": 0.0,
            "true_yuan_bonus": 0.0,
            "body_movement_bonus": 0.0,
            "duel_rate_bonus": 0.0,
            "cultivation_bonus": 0.0,
            "breakthrough_bonus": 0.0,
        }
    return {
        "attack_bonus": float(technique.get("attack_bonus", 0) or 0),
        "defense_bonus": float(technique.get("defense_bonus", 0) or 0),
        "bone_bonus": float(technique.get("bone_bonus", 0) or 0),
        "comprehension_bonus": float(technique.get("comprehension_bonus", 0) or 0),
        "divine_sense_bonus": float(technique.get("divine_sense_bonus", 0) or 0),
        "fortune_bonus": float(technique.get("fortune_bonus", 0) or 0),
        "qi_blood_bonus": float(technique.get("qi_blood_bonus", 0) or 0),
        "true_yuan_bonus": float(technique.get("true_yuan_bonus", 0) or 0),
        "body_movement_bonus": float(technique.get("body_movement_bonus", 0) or 0),
        "duel_rate_bonus": float(technique.get("duel_rate_bonus", 0) or 0),
        "cultivation_bonus": float(technique.get("cultivation_bonus", 0) or 0),
        "breakthrough_bonus": float(technique.get("breakthrough_bonus", 0) or 0),
    }


def resolve_title_effects(
    profile: dict[str, Any],
    title: dict[str, Any] | None,
    opponent_profile: dict[str, Any] | None = None,
) -> dict[str, float]:
    if title is None:
        return {
            "attack_bonus": 0.0,
            "defense_bonus": 0.0,
            "bone_bonus": 0.0,
            "comprehension_bonus": 0.0,
            "divine_sense_bonus": 0.0,
            "fortune_bonus": 0.0,
            "qi_blood_bonus": 0.0,
            "true_yuan_bonus": 0.0,
            "body_movement_bonus": 0.0,
            "duel_rate_bonus": 0.0,
            "cultivation_bonus": 0.0,
            "breakthrough_bonus": 0.0,
        }
    return {
        "attack_bonus": float(title.get("attack_bonus", 0) or 0),
        "defense_bonus": float(title.get("defense_bonus", 0) or 0),
        "bone_bonus": float(title.get("bone_bonus", 0) or 0),
        "comprehension_bonus": float(title.get("comprehension_bonus", 0) or 0),
        "divine_sense_bonus": float(title.get("divine_sense_bonus", 0) or 0),
        "fortune_bonus": float(title.get("fortune_bonus", 0) or 0),
        "qi_blood_bonus": float(title.get("qi_blood_bonus", 0) or 0),
        "true_yuan_bonus": float(title.get("true_yuan_bonus", 0) or 0),
        "body_movement_bonus": float(title.get("body_movement_bonus", 0) or 0),
        "duel_rate_bonus": float(title.get("duel_rate_bonus", 0) or 0),
        "cultivation_bonus": float(title.get("cultivation_bonus", 0) or 0),
        "breakthrough_bonus": float(title.get("breakthrough_bonus", 0) or 0),
    }


def _root_element_duel_modifier(attacker: dict[str, Any], defender: dict[str, Any]) -> float:
    attacker_elements = _profile_root_elements(attacker)
    defender_elements = _profile_root_elements(defender)
    modifier = 0.0
    for own in attacker_elements:
        for rival in defender_elements:
            if ELEMENT_CONTROLS.get(own) == rival:
                modifier += 0.025
            if ELEMENT_CONTROLS.get(rival) == own:
                modifier -= 0.025
            if ELEMENT_GENERATES.get(own) == rival:
                modifier += 0.01
            if ELEMENT_GENERATES.get(rival) == own:
                modifier -= 0.01
    return max(min(modifier, 0.08), -0.08)

def resolve_artifact_effects(
    profile: dict[str, Any],
    artifact: dict[str, Any] | None,
    opponent_profile: dict[str, Any] | None = None,
) -> dict[str, float]:
    if artifact is None:
        return {
            "attack_bonus": 0.0,
            "defense_bonus": 0.0,
            "bone_bonus": 0.0,
            "comprehension_bonus": 0.0,
            "divine_sense_bonus": 0.0,
            "fortune_bonus": 0.0,
            "qi_blood_bonus": 0.0,
            "true_yuan_bonus": 0.0,
            "body_movement_bonus": 0.0,
            "duel_rate_bonus": 0.0,
            "cultivation_bonus": 0.0,
        }
    multiplier = _item_quality_multiplier(artifact, "artifact")
    return {
        "attack_bonus": float(artifact.get("attack_bonus", 0) or 0) * multiplier,
        "defense_bonus": float(artifact.get("defense_bonus", 0) or 0) * multiplier,
        "bone_bonus": float(artifact.get("bone_bonus", 0) or 0) * multiplier,
        "comprehension_bonus": float(artifact.get("comprehension_bonus", 0) or 0) * multiplier,
        "divine_sense_bonus": float(artifact.get("divine_sense_bonus", 0) or 0) * multiplier,
        "fortune_bonus": float(artifact.get("fortune_bonus", 0) or 0) * multiplier,
        "qi_blood_bonus": float(artifact.get("qi_blood_bonus", 0) or 0) * multiplier,
        "true_yuan_bonus": float(artifact.get("true_yuan_bonus", 0) or 0) * multiplier,
        "body_movement_bonus": float(artifact.get("body_movement_bonus", 0) or 0) * multiplier,
        "duel_rate_bonus": float(artifact.get("duel_rate_bonus", 0) or 0) * multiplier,
        "cultivation_bonus": float(artifact.get("cultivation_bonus", 0) or 0) * multiplier,
    }


def resolve_talisman_effects(
    profile: dict[str, Any],
    talisman: dict[str, Any] | None,
    opponent_profile: dict[str, Any] | None = None,
) -> dict[str, float]:
    if talisman is None:
        return {
            "attack_bonus": 0.0,
            "defense_bonus": 0.0,
            "bone_bonus": 0.0,
            "comprehension_bonus": 0.0,
            "divine_sense_bonus": 0.0,
            "fortune_bonus": 0.0,
            "qi_blood_bonus": 0.0,
            "true_yuan_bonus": 0.0,
            "body_movement_bonus": 0.0,
            "duel_rate_bonus": 0.0,
        }
    multiplier = _item_quality_multiplier(talisman, "talisman")
    return {
        "attack_bonus": float(talisman.get("attack_bonus", 0) or 0) * multiplier,
        "defense_bonus": float(talisman.get("defense_bonus", 0) or 0) * multiplier,
        "bone_bonus": float(talisman.get("bone_bonus", 0) or 0) * multiplier,
        "comprehension_bonus": float(talisman.get("comprehension_bonus", 0) or 0) * multiplier,
        "divine_sense_bonus": float(talisman.get("divine_sense_bonus", 0) or 0) * multiplier,
        "fortune_bonus": float(talisman.get("fortune_bonus", 0) or 0) * multiplier,
        "qi_blood_bonus": float(talisman.get("qi_blood_bonus", 0) or 0) * multiplier,
        "true_yuan_bonus": float(talisman.get("true_yuan_bonus", 0) or 0) * multiplier,
        "body_movement_bonus": float(talisman.get("body_movement_bonus", 0) or 0) * multiplier,
        "duel_rate_bonus": float(talisman.get("duel_rate_bonus", 0) or 0) * multiplier,
    }


def resolve_pill_effects(
    profile: dict[str, Any],
    pill: dict[str, Any] | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, float]:
    if pill is None:
        return {
            "effect_value": 0.0,
            "poison_delta": 0.0,
            "success_rate_bonus": 0.0,
            "clear_poison": 0.0,
            "cultivation_gain": 0.0,
            "stone_gain": 0.0,
            "insight_gain": 0.0,
            "attack_bonus": 0.0,
            "defense_bonus": 0.0,
            "bone_bonus": 0.0,
            "comprehension_bonus": 0.0,
            "divine_sense_bonus": 0.0,
            "fortune_bonus": 0.0,
            "willpower_bonus": 0.0,
            "charisma_bonus": 0.0,
            "karma_bonus": 0.0,
            "qi_blood_bonus": 0.0,
            "true_yuan_bonus": 0.0,
            "body_movement_bonus": 0.0,
            "root_quality_gain": 0.0,
            "root_quality_floor": 0.0,
        }
    pill_type = pill.get("pill_type")
    multiplier = _item_quality_multiplier(pill, "pill")
    base_effect_value = max(float(pill.get("effect_value", 0) or 0) * multiplier, 0.0)
    payload = {
        "effect_value": base_effect_value,
        "poison_delta": float(pill.get("poison_delta", 0) or 0),
        "success_rate_bonus": 0.0,
        "clear_poison": base_effect_value if pill_type == "clear_poison" else 0.0,
        "cultivation_gain": base_effect_value if pill_type == "cultivation" else 0.0,
        "stone_gain": base_effect_value if pill_type == "stone" else 0.0,
        "insight_gain": 0.0,
        "attack_bonus": float(pill.get("attack_bonus", 0) or 0) * multiplier,
        "defense_bonus": float(pill.get("defense_bonus", 0) or 0) * multiplier,
        "bone_bonus": float(pill.get("bone_bonus", 0) or 0) * multiplier,
        "comprehension_bonus": float(pill.get("comprehension_bonus", 0) or 0) * multiplier,
        "divine_sense_bonus": float(pill.get("divine_sense_bonus", 0) or 0) * multiplier,
        "fortune_bonus": float(pill.get("fortune_bonus", 0) or 0) * multiplier,
        "willpower_bonus": 0.0,
        "charisma_bonus": 0.0,
        "karma_bonus": 0.0,
        "qi_blood_bonus": float(pill.get("qi_blood_bonus", 0) or 0) * multiplier,
        "true_yuan_bonus": float(pill.get("true_yuan_bonus", 0) or 0) * multiplier,
        "body_movement_bonus": float(pill.get("body_movement_bonus", 0) or 0) * multiplier,
        "root_quality_gain": 0.0,
        "root_quality_floor": 0.0,
    }
    if pill_type == "foundation":
        payload["success_rate_bonus"] = base_effect_value
    elif pill_type == "bone":
        payload["bone_bonus"] += base_effect_value
    elif pill_type == "comprehension":
        payload["comprehension_bonus"] += base_effect_value
    elif pill_type == "divine_sense":
        payload["divine_sense_bonus"] += base_effect_value
    elif pill_type == "fortune":
        payload["fortune_bonus"] += base_effect_value
    elif pill_type == "willpower":
        payload["willpower_bonus"] += base_effect_value
    elif pill_type == "charisma":
        payload["charisma_bonus"] += base_effect_value
    elif pill_type == "karma":
        payload["karma_bonus"] += base_effect_value
    elif pill_type == "qi_blood":
        payload["qi_blood_bonus"] += base_effect_value
    elif pill_type == "true_yuan":
        payload["true_yuan_bonus"] += base_effect_value
    elif pill_type == "body_movement":
        payload["body_movement_bonus"] += base_effect_value
    elif pill_type == "attack":
        payload["attack_bonus"] += base_effect_value
    elif pill_type == "defense":
        payload["defense_bonus"] += base_effect_value
    elif pill_type == "root_refine":
        payload["root_quality_gain"] = max(base_effect_value, 0.0)
    elif pill_type == "root_remold":
        payload["root_quality_floor"] = max(base_effect_value, 0.0)
    return payload


def _pill_usage_reason(profile_data: dict[str, Any], pill: dict[str, Any]) -> str:
    if not realm_requirement_met(profile_data, pill.get("min_realm_stage"), pill.get("min_realm_layer")):
        return f"需要达到 {format_realm_requirement(pill.get('min_realm_stage'), pill.get('min_realm_layer'))} 才能服用这枚丹药。"
    pill_type = str(pill.get("pill_type") or "").strip()
    if pill_type == "foundation":
        return "筑基丹只能在突破时配合使用。"
    if pill_type == "root_refine":
        effects = resolve_pill_effects(profile_data, pill)
        steps = max(int(round(float(effects.get("root_quality_gain", 0) or 0))), 0)
        current_quality = _normalized_root_quality(profile_data)
        if current_quality in ROOT_SPECIAL_QUALITIES:
            return "当前已是特殊灵根，无法再用此丹淬炼。"
        if steps <= 0:
            return "这枚淬灵丹没有可生效的品阶。"
        if _refined_root_payload(profile_data, steps) is None:
            return "当前灵根品质已达可淬炼上限。"
    if pill_type in ROOT_TRANSFORM_PILL_TYPES:
        if _transformed_root_payload(profile_data, pill_type, pill.get("effect_value")) is None:
            return "这枚丹药当前无法改变你的灵根。"
    return ""


def _pill_effect_summary(before_profile: dict[str, Any], after_profile: dict[str, Any]) -> str:
    parts: list[str] = []
    before_root = format_root(before_profile)
    after_root = format_root(after_profile)
    before_stage = normalize_realm_stage(before_profile.get("realm_stage") or "炼气")
    after_stage = normalize_realm_stage(after_profile.get("realm_stage") or "炼气")
    before_layer = max(int(before_profile.get("realm_layer") or 1), 1)
    after_layer = max(int(after_profile.get("realm_layer") or 1), 1)

    def cultivation_progress_total(profile: dict[str, Any]) -> int:
        stage = normalize_realm_stage(profile.get("realm_stage") or "炼气")
        layer = max(int(profile.get("realm_layer") or 1), 1)
        cultivation = max(int(profile.get("cultivation") or 0), 0)
        total = cultivation
        for current_layer in range(1, layer):
            total += cultivation_threshold(stage, current_layer)
        return total

    if before_root != after_root:
        parts.append(f"灵根：{before_root} -> {after_root}")
    if before_stage != after_stage or before_layer != after_layer:
        parts.append(f"境界：{before_stage}{before_layer}层 -> {after_stage}{after_layer}层")
    cultivation_delta = (
        cultivation_progress_total(after_profile) - cultivation_progress_total(before_profile)
        if before_stage == after_stage
        else int(after_profile.get("cultivation") or 0) - int(before_profile.get("cultivation") or 0)
    )
    if cultivation_delta:
        parts.append(f"修为 {'+' if cultivation_delta > 0 else ''}{cultivation_delta}")
    for key in (
        "spiritual_stone",
        "bone",
        "comprehension",
        "divine_sense",
        "fortune",
        "willpower",
        "charisma",
        "karma",
        "qi_blood",
        "true_yuan",
        "body_movement",
        "attack_power",
        "defense_power",
        "dan_poison",
    ):
        delta = int(after_profile.get(key) or 0) - int(before_profile.get(key) or 0)
        if not delta:
            continue
        label = {
            "cultivation": "修为",
            "spiritual_stone": "灵石",
            "attack_power": "攻击",
            "defense_power": "防御",
            "dan_poison": "丹毒",
        }.get(key, ATTRIBUTE_LABELS.get(f"{key}_bonus", key))
        parts.append(f"{label} {'+' if delta > 0 else ''}{delta}")
    return "；".join(parts) if parts else "药力已经化开。"


def _profile_base_name(profile: dict[str, Any]) -> str:
    return (
        str(profile.get("display_label") or "").strip()
        or str(profile.get("display_name") or "").strip()
        or (f"@{profile['username']}" if str(profile.get("username") or "").strip() else f"TG {profile.get('tg', 0)}")
    )


def _profile_title_name(profile: dict[str, Any], title: dict[str, Any] | None = None) -> str:
    if title and str(title.get("name") or "").strip():
        return str(title.get("name") or "").strip()
    return str(profile.get("current_title_name") or "").strip()


def _profile_name_with_title(profile: dict[str, Any], title: dict[str, Any] | None = None) -> str:
    base_name = _profile_base_name(profile)
    title_name = _profile_title_name(profile, title)
    if not title_name:
        return base_name
    return f"「{title_name}」{base_name}"


def _artifact_effect_template() -> dict[str, float]:
    return {
        "attack_bonus": 0.0,
        "defense_bonus": 0.0,
        "bone_bonus": 0.0,
        "comprehension_bonus": 0.0,
        "divine_sense_bonus": 0.0,
        "fortune_bonus": 0.0,
        "qi_blood_bonus": 0.0,
        "true_yuan_bonus": 0.0,
        "body_movement_bonus": 0.0,
        "duel_rate_bonus": 0.0,
        "cultivation_bonus": 0.0,
        "breakthrough_bonus": 0.0,
    }


def _artifact_set_index() -> dict[int, dict[str, Any]]:
    return {
        int(item["id"]): dict(item)
        for item in list_artifact_sets(enabled_only=True)
        if int(item.get("id") or 0) > 0
    }


def _decorate_artifact_with_set(artifact: dict[str, Any], artifact_set_map: dict[int, dict[str, Any]] | None = None) -> dict[str, Any]:
    if artifact_set_map is None:
        artifact_set_map = _artifact_set_index()
    set_id = int(artifact.get("artifact_set_id") or 0)
    artifact_set = dict(artifact_set_map.get(set_id) or {})
    artifact["artifact_set"] = artifact_set or None
    artifact["artifact_set_name"] = artifact_set.get("name")
    return artifact


def _artifact_set_effects(artifact_set: dict[str, Any] | None) -> dict[str, float]:
    if artifact_set is None:
        return _artifact_effect_template()
    return {
        "attack_bonus": float(artifact_set.get("attack_bonus", 0) or 0),
        "defense_bonus": float(artifact_set.get("defense_bonus", 0) or 0),
        "bone_bonus": float(artifact_set.get("bone_bonus", 0) or 0),
        "comprehension_bonus": float(artifact_set.get("comprehension_bonus", 0) or 0),
        "divine_sense_bonus": float(artifact_set.get("divine_sense_bonus", 0) or 0),
        "fortune_bonus": float(artifact_set.get("fortune_bonus", 0) or 0),
        "qi_blood_bonus": float(artifact_set.get("qi_blood_bonus", 0) or 0),
        "true_yuan_bonus": float(artifact_set.get("true_yuan_bonus", 0) or 0),
        "body_movement_bonus": float(artifact_set.get("body_movement_bonus", 0) or 0),
        "duel_rate_bonus": float(artifact_set.get("duel_rate_bonus", 0) or 0),
        "cultivation_bonus": float(artifact_set.get("cultivation_bonus", 0) or 0),
        "breakthrough_bonus": float(artifact_set.get("breakthrough_bonus", 0) or 0),
    }


def _resolve_active_artifact_sets(equipped_artifacts: list[dict[str, Any]] | None) -> dict[str, Any]:
    artifact_set_map = _artifact_set_index()
    grouped: dict[int, list[dict[str, Any]]] = {}
    for artifact in equipped_artifacts or []:
        set_id = int(artifact.get("artifact_set_id") or 0)
        if set_id <= 0 or set_id not in artifact_set_map:
            continue
        grouped.setdefault(set_id, []).append(artifact)

    totals = _artifact_effect_template()
    sets: list[dict[str, Any]] = []
    for set_id, artifacts in grouped.items():
        artifact_set = dict(artifact_set_map[set_id])
        equipped_count = len(artifacts)
        required_count = max(int(artifact_set.get("required_count") or 2), 1)
        active = equipped_count >= required_count
        resolved_effects = _artifact_set_effects(artifact_set) if active else _artifact_effect_template()
        if active:
            for key in totals:
                totals[key] += float(resolved_effects.get(key, 0) or 0)
        artifact_set["equipped_count"] = equipped_count
        artifact_set["active"] = active
        artifact_set["artifact_names"] = [str(item.get("name") or "") for item in artifacts if str(item.get("name") or "").strip()]
        artifact_set["resolved_effects"] = resolved_effects
        sets.append(artifact_set)

    sets.sort(key=lambda item: (-int(item.get("active") or 0), -int(item.get("equipped_count") or 0), int(item.get("id") or 0)))
    return {"sets": sets, "totals": totals}


def collect_equipped_artifacts(tg: int) -> list[dict[str, Any]]:
    artifact_set_map = _artifact_set_index()
    return [_decorate_artifact_with_set(row["artifact"], artifact_set_map) for row in list_equipped_artifacts(tg)]


def merge_artifact_effects(
    profile: dict[str, Any],
    equipped_artifacts: list[dict[str, Any]] | None,
    opponent_profile: dict[str, Any] | None = None,
) -> dict[str, float]:
    totals = _artifact_effect_template()
    for artifact in equipped_artifacts or []:
        effects = resolve_artifact_effects(profile, artifact, opponent_profile)
        for key in totals:
            totals[key] += float(effects.get(key, 0) or 0)
    active_set_bundle = _resolve_active_artifact_sets(equipped_artifacts)
    for key in totals:
        totals[key] += float((active_set_bundle.get("totals") or {}).get(key, 0) or 0)
    return totals


def build_user_artifact_rows(
    profile_data: dict[str, Any],
    tg: int,
    retreating: bool,
    equip_limit: int,
    equipped_ids: set[int],
    equipped_slot_names: set[str] | None = None,
) -> list[dict[str, Any]]:
    artifact_set_map = _artifact_set_index()
    occupied_slots = {slot for slot in (equipped_slot_names or set()) if slot}
    rows = []
    for row in list_user_artifacts(tg):
        total_quantity = max(int(row.get("quantity") or 0), 0)
        bound_quantity = max(min(int(row.get("bound_quantity") or 0), total_quantity), 0)
        item = _decorate_artifact_with_set(row["artifact"], artifact_set_map)
        item["resolved_effects"] = resolve_artifact_effects(profile_data, item)
        item["equipped"] = int(item["id"]) in equipped_ids
        equipped_quantity = 1 if item["equipped"] else 0
        row["bound_quantity"] = bound_quantity
        row["unbound_quantity"] = max(total_quantity - bound_quantity, 0)
        row["consumable_quantity"] = max(total_quantity - bound_quantity - equipped_quantity, 0)
        row["tradeable_quantity"] = row["consumable_quantity"]
        usable = realm_requirement_met(profile_data, item.get("min_realm_stage"), item.get("min_realm_layer"))
        if usable:
            reason = ""
        else:
            reason = f"需要达到 {format_realm_requirement(item.get('min_realm_stage'), item.get('min_realm_layer'))}"
        target_slot = str(item.get("equip_slot") or "").strip()
        slot_replaceable = bool(target_slot and target_slot in occupied_slots)
        if not item["equipped"] and len(equipped_ids) >= equip_limit and not slot_replaceable:
            usable = False
            reason = f"当前最多只能装备 {equip_limit} 件法宝"
        if retreating:
            usable = False
            reason = "闭关期间无法切换法宝"
        item["usable"] = usable or item["equipped"]
        item["unusable_reason"] = "" if item["equipped"] else reason
        item["action_label"] = "卸下法宝" if item["equipped"] else f"装备到{item.get('equip_slot_label') or '槽位'}"
        item["bound"] = bound_quantity > 0
        item["bound_quantity"] = bound_quantity
        rows.append(row)
    return rows


def _build_user_technique_rows(profile_data: dict[str, Any], tg: int) -> list[dict[str, Any]]:
    current_id = int(profile_data.get("current_technique_id") or 0)
    rows = []
    for row in list_user_techniques(tg, enabled_only=True):
        technique = dict(row.get("technique") or {})
        if not technique:
            continue
        technique["resolved_effects"] = resolve_technique_effects(profile_data, technique)
        technique["active"] = int(technique.get("id") or 0) == current_id
        technique["source"] = row.get("source")
        technique["obtained_note"] = row.get("obtained_note")
        usable = realm_requirement_met(profile_data, technique.get("min_realm_stage"), technique.get("min_realm_layer"))
        reason = "" if usable else f"需要达到 {format_realm_requirement(technique.get('min_realm_stage'), technique.get('min_realm_layer'))}"
        technique["usable"] = usable or technique["active"]
        technique["unusable_reason"] = "" if technique["active"] else reason
        technique["action_label"] = "当前功法" if technique["active"] else "切换功法"
        rows.append(technique)
    return rows


def _current_technique_payload(profile_data: dict[str, Any]) -> dict[str, Any] | None:
    technique_id = int(profile_data.get("current_technique_id") or 0)
    if not technique_id:
        return None
    technique = serialize_technique(get_technique(technique_id))
    if not technique or not technique.get("enabled"):
        return None
    technique["resolved_effects"] = resolve_technique_effects(profile_data, technique)
    technique["active"] = True
    return technique


SEED_DATA_VERSION = "2026-04-14-default-content-v2"
SEED_DATA_READY = False


def _resolve_seed_result_ref_id(
    kind: str,
    name: str,
    *,
    artifact_map: dict[str, dict[str, Any]],
    pill_map: dict[str, dict[str, Any]],
    talisman_map: dict[str, dict[str, Any]],
    material_map: dict[str, dict[str, Any]],
    technique_map: dict[str, dict[str, Any]] | None = None,
    recipe_map: dict[str, dict[str, Any]] | None = None,
) -> int:
    lookup = {
        "artifact": artifact_map,
        "pill": pill_map,
        "talisman": talisman_map,
        "material": material_map,
        "technique": technique_map or {},
        "recipe": recipe_map or {},
    }.get(kind)
    if lookup is None or name not in lookup:
        raise ValueError(f"未找到默认种子引用：{kind}::{name}")
    return int(lookup[name]["id"])


def ensure_seed_data(force: bool = False) -> None:
    global SEED_DATA_READY
    if SEED_DATA_READY and not force:
        return

    title_map: dict[str, dict[str, Any]] = {}
    for payload in DEFAULT_TITLES:
        title = sync_title_by_name(**payload, enabled=True)
        title_map[title["name"]] = title

    artifact_set_map: dict[str, dict[str, Any]] = {}
    for payload in DEFAULT_ARTIFACT_SETS:
        artifact_set = sync_artifact_set_by_name(**payload, enabled=True)
        artifact_set_map[artifact_set["name"]] = artifact_set

    for payload in DEFAULT_ARTIFACTS:
        artifact_payload = dict(payload)
        artifact_set_name = str(artifact_payload.pop("artifact_set_name", "") or "").strip()
        if artifact_set_name:
            artifact_payload["artifact_set_id"] = int(artifact_set_map[artifact_set_name]["id"])
        sync_artifact_by_name(**artifact_payload)
    artifact_map = {item["name"]: item for item in list_artifacts()}

    for payload in DEFAULT_PILLS:
        sync_pill_by_name(**payload)
    pill_map = {item["name"]: item for item in list_pills()}

    for payload in DEFAULT_TALISMANS:
        sync_talisman_by_name(**payload)
    talisman_map = {item["name"]: item for item in list_talismans()}

    for payload in DEFAULT_TECHNIQUES:
        sync_technique_by_name(**payload)
    technique_map = {item["name"]: item for item in list_techniques()}

    for payload in DEFAULT_MATERIALS:
        sync_material_by_name(**payload, enabled=True)
    material_map = {item["name"]: item for item in list_materials()}
    settings = get_xiuxian_settings()
    sync_official_shop_name(
        str(settings.get("official_shop_name", DEFAULT_SETTINGS["official_shop_name"]) or DEFAULT_SETTINGS["official_shop_name"])
    )

    for recipe in DEFAULT_RECIPES:
        result_ref_id = _resolve_seed_result_ref_id(
            str(recipe["result_kind"]),
            str(recipe["result_name"]),
            artifact_map=artifact_map,
            pill_map=pill_map,
            talisman_map=talisman_map,
            material_map=material_map,
            technique_map=technique_map,
        )
        sync_recipe_with_ingredients_by_name(
            name=str(recipe["name"]),
            recipe_kind=str(recipe["recipe_kind"]),
            result_kind=str(recipe["result_kind"]),
            result_ref_id=result_ref_id,
            result_quantity=int(recipe["result_quantity"]),
            base_success_rate=int(recipe["base_success_rate"]),
            broadcast_on_success=bool(recipe.get("broadcast_on_success")),
            ingredients=[
                {
                    "material_id": _resolve_seed_result_ref_id(
                        "material",
                        str(item["material_name"]),
                        artifact_map=artifact_map,
                        pill_map=pill_map,
                        talisman_map=talisman_map,
                        material_map=material_map,
                        technique_map=technique_map,
                    ),
                    "quantity": int(item["quantity"]),
                }
                for item in recipe.get("ingredients") or []
            ],
        )
    recipe_map = {item["name"]: item for item in list_recipes()}

    for payload in DEFAULT_SECTS:
        sync_sect_with_roles_by_name(**payload)

    for scene in DEFAULT_SCENES:
        resolved_events = []
        for event in scene.get("event_pool") or []:
            payload = dict(event)
            if payload.get("bonus_reward_ref_id_name"):
                payload["bonus_reward_ref_id"] = _resolve_seed_result_ref_id(
                    str(payload.get("bonus_reward_kind") or "material"),
                    str(payload.get("bonus_reward_ref_id_name")),
                    artifact_map=artifact_map,
                    pill_map=pill_map,
                    talisman_map=talisman_map,
                    material_map=material_map,
                    technique_map=technique_map,
                    recipe_map=recipe_map,
                )
            payload.pop("bonus_reward_ref_id_name", None)
            resolved_events.append(payload)
        resolved_drops = []
        for drop in scene.get("drops") or []:
            payload = dict(drop)
            if payload.get("reward_ref_id_name"):
                payload["reward_ref_id"] = _resolve_seed_result_ref_id(
                    str(payload.get("reward_kind") or "material"),
                    str(payload.get("reward_ref_id_name")),
                    artifact_map=artifact_map,
                    pill_map=pill_map,
                    talisman_map=talisman_map,
                    material_map=material_map,
                    technique_map=technique_map,
                    recipe_map=recipe_map,
                )
            payload.pop("reward_ref_id_name", None)
            resolved_drops.append(payload)
        sync_scene_with_drops_by_name(
            name=str(scene["name"]),
            description=str(scene.get("description") or ""),
            image_url=str(scene.get("image_url") or ""),
            max_minutes=int(scene.get("max_minutes") or 60),
            min_realm_stage=scene.get("min_realm_stage"),
            min_realm_layer=int(scene.get("min_realm_layer") or 1),
            min_combat_power=int(scene.get("min_combat_power") or 0),
            event_pool=resolved_events,
            drops=resolved_drops,
        )

    for encounter in DEFAULT_ENCOUNTER_TEMPLATES:
        encounter_payload = dict(encounter)
        reward_item_name = str(encounter_payload.pop("reward_item_ref_name", "") or "").strip()
        if reward_item_name:
            encounter_payload["reward_item_ref_id"] = _resolve_seed_result_ref_id(
                str(encounter_payload.get("reward_item_kind") or "material"),
                reward_item_name,
                artifact_map=artifact_map,
                pill_map=pill_map,
                talisman_map=talisman_map,
                material_map=material_map,
                technique_map=technique_map,
                recipe_map=recipe_map,
            )
        sync_encounter_template_by_name(**encounter_payload)

    for payload in DEFAULT_ACHIEVEMENTS:
        achievement_payload = dict(payload)
        reward_config = dict(achievement_payload.get("reward_config") or {})
        reward_title_names = [str(name) for name in reward_config.pop("reward_title_names", []) if str(name).strip()]
        reward_config["titles"] = [
            int(title_map[name]["id"])
            for name in reward_title_names
            if name in title_map
        ]
        achievement_payload["reward_config"] = reward_config
        sync_achievement_by_key(**achievement_payload)

    SEED_DATA_READY = True


def china_now():
    return utcnow() + timedelta(hours=8)


def is_same_china_day(left, right) -> bool:
    if left is None or right is None:
        return False
    return (left + timedelta(hours=8)).date() == (right + timedelta(hours=8)).date()


def realm_requirement_met(profile: dict[str, Any], min_stage: str | None, min_layer: int | None) -> bool:
    if not min_stage:
        return True

    current_stage = realm_index(profile.get("realm_stage"))
    required_stage = realm_index(min_stage)
    current_layer = int(profile.get("realm_layer") or 0)
    required_layer = int(min_layer or 1)
    if current_stage != required_stage:
        return current_stage > required_stage
    return current_layer >= required_layer


def format_realm_requirement(min_stage: str | None, min_layer: int | None) -> str:
    if not min_stage:
        return "无限制"
    return f"{min_stage}{int(min_layer or 1)}层"


def apply_cultivation_gain(stage: str, layer: int, cultivation: int, gain: int) -> tuple[int, int, list[int], int]:
    current_layer = max(int(layer or 1), 1)
    current_cultivation = max(int(cultivation or 0), 0) + max(int(gain or 0), 0)
    upgraded_layers: list[int] = []
    threshold = cultivation_threshold(stage, current_layer)

    while current_layer < 9 and current_cultivation >= threshold:
        current_cultivation -= threshold
        current_layer += 1
        upgraded_layers.append(current_layer)
        threshold = cultivation_threshold(stage, current_layer)

    if current_layer >= 9:
        current_cultivation = min(current_cultivation, threshold)

    remaining = max(threshold - current_cultivation, 0)
    return current_layer, current_cultivation, upgraded_layers, remaining


def _compute_immortal_touch_gain(stage: str, layer: int, cultivation: int, infusion_layers: int) -> int:
    simulated_layer = max(int(layer or 1), 1)
    simulated_cultivation = max(int(cultivation or 0), 0)
    remaining_layers = max(int(infusion_layers or 1), 1)
    total_gain = 0

    while remaining_layers > 0:
        threshold = cultivation_threshold(stage, simulated_layer)
        current = min(simulated_cultivation, threshold)
        total_gain += max(threshold - current, 0)
        if simulated_layer >= 9:
            break
        simulated_layer += 1
        simulated_cultivation = 0
        remaining_layers -= 1

    return total_gain


def immortal_touch_infuse_cultivation(actor_tg: int, target_tg: int) -> dict[str, Any]:
    if actor_tg == target_tg:
        raise ValueError("请回复其他道友后再施展仙人抚顶。")

    target = get_profile(target_tg, create=False)
    if target is None or not target.consented:
        raise ValueError("被回复的道友还没有踏入仙途。")

    ensure_not_in_retreat(target_tg)
    settings = get_xiuxian_settings()
    configured_layers = _coerce_int(
        settings.get("immortal_touch_infusion_layers"),
        DEFAULT_SETTINGS["immortal_touch_infusion_layers"],
        1,
    )
    stage = normalize_realm_stage(target.realm_stage or "炼气")
    current_layer = int(target.realm_layer or 1)
    current_cultivation = int(target.cultivation or 0)
    gain = _compute_immortal_touch_gain(stage, current_layer, current_cultivation, configured_layers)
    if gain <= 0:
        raise ValueError("对方当前修为已圆满，暂时无法继续灌注。")

    next_layer, next_cultivation, upgraded_layers, remaining = apply_cultivation_gain(
        stage,
        current_layer,
        current_cultivation,
        gain,
    )
    updated = upsert_profile(
        target_tg,
        cultivation=next_cultivation,
        realm_layer=next_layer,
    )
    threshold = cultivation_threshold(stage, next_layer)
    create_journal(actor_tg, "immortal_touch", "仙人抚顶", f"为 TG {target_tg} 灌注了 {gain} 点修为")
    create_journal(target_tg, "immortal_touch", "获仙人抚顶", f"获得 TG {actor_tg} 灌注的 {gain} 点修为")
    return {
        "gain": gain,
        "configured_layers": configured_layers,
        "upgraded_layers": upgraded_layers,
        "remaining": remaining,
        "breakthrough_ready": bool(next_layer >= 9 and next_cultivation >= threshold),
        "threshold": threshold,
        "profile": serialize_profile(updated),
    }


def build_progress(stage: str, layer: int, cultivation: int) -> dict[str, int | bool]:
    threshold = cultivation_threshold(stage, layer)
    current = min(max(int(cultivation or 0), 0), threshold)
    if layer < 9:
        return {
            "threshold": threshold,
            "current": current,
            "remaining": max(threshold - current, 0),
            "breakthrough_ready": False,
        }
    return {
        "threshold": threshold,
        "current": min(current, threshold),
        "remaining": max(threshold - min(current, threshold), 0),
        "breakthrough_ready": min(current, threshold) >= threshold,
    }


def _compute_retreat_plan(profile) -> dict[str, int]:
    profile_data = serialize_profile(profile)
    artifact_effects = merge_artifact_effects(profile_data, collect_equipped_artifacts(profile.tg))
    sect_effects = get_sect_effects(profile_data)
    technique_effects = resolve_technique_effects(profile_data, _current_technique_payload(profile_data))
    title_effects = resolve_title_effects(profile_data, get_current_title(profile.tg))
    artifact_bonus = (
        int(artifact_effects.get("cultivation_bonus", 0))
        + int(sect_effects.get("cultivation_bonus", 0))
        + int(technique_effects.get("cultivation_bonus", 0))
        + int(title_effects.get("cultivation_bonus", 0))
        + int(profile_data.get("insight_bonus", 0) or 0)
    )
    poison_penalty = min(int(profile.dan_poison or 0) // 4, 25)
    gain_per_hour = max(90 + realm_index(profile.realm_stage) * 18 + int(profile.realm_layer or 1) * 10 + artifact_bonus * 2 - poison_penalty, 40)
    cost_per_hour = max(ceil(gain_per_hour / 12), 6)
    return {
        "gain_per_minute": max(gain_per_hour // 60, 1),
        "cost_per_minute": max(cost_per_hour // 60, 1),
    }


def _is_retreating(profile) -> bool:
    return bool(profile and profile.retreat_started_at and profile.retreat_end_at and int(profile.retreat_minutes_total or 0) > int(profile.retreat_minutes_resolved or 0))


def _settle_retreat_progress(tg: int) -> dict[str, Any] | None:
    profile = get_profile(tg, create=False)
    if profile is None or not _is_retreating(profile):
        return None

    now = utcnow()
    end_at = profile.retreat_end_at or now
    started_at = profile.retreat_started_at or now
    total_minutes = max(int(profile.retreat_minutes_total or 0), 0)
    resolved_minutes = max(int(profile.retreat_minutes_resolved or 0), 0)
    elapsed_minutes = int(max(min(now, end_at) - started_at, timedelta()).total_seconds() // 60)
    target_minutes = min(max(elapsed_minutes, 0), total_minutes)
    delta_minutes = max(target_minutes - resolved_minutes, 0)

    if delta_minutes <= 0:
        if now >= end_at and resolved_minutes >= total_minutes:
            upsert_profile(
                tg,
                retreat_started_at=None,
                retreat_end_at=None,
                retreat_gain_per_minute=0,
                retreat_cost_per_minute=0,
                retreat_minutes_total=0,
                retreat_minutes_resolved=0,
            )
        return None

    gain_per_minute = max(int(profile.retreat_gain_per_minute or 0), 0)
    cost_per_minute = max(int(profile.retreat_cost_per_minute or 0), 0)
    affordable_minutes = delta_minutes
    insufficient_stone = False
    if cost_per_minute > 0:
        # 灵石不足时只结算当前能支付的分钟数，避免把剩余闭关进度直接跳过。
        affordable_minutes = min(delta_minutes, max(int(profile.spiritual_stone or 0), 0) // cost_per_minute)
        insufficient_stone = affordable_minutes < delta_minutes

    if affordable_minutes <= 0:
        if insufficient_stone or now >= end_at:
            updated = upsert_profile(
                tg,
                retreat_started_at=None,
                retreat_end_at=None,
                retreat_gain_per_minute=0,
                retreat_cost_per_minute=0,
                retreat_minutes_total=0,
                retreat_minutes_resolved=0,
            )
            return {
                "gain": 0,
                "cost": 0,
                "upgraded_layers": [],
                "remaining": 0,
                "finished": True,
                "insufficient_stone": True,
                "profile": serialize_profile(updated),
            }
        return None

    gain = affordable_minutes * gain_per_minute
    cost = affordable_minutes * cost_per_minute
    layer, cultivation, upgraded_layers, remaining = apply_cultivation_gain(
        profile.realm_stage or "炼气",
        int(profile.realm_layer or 1),
        int(profile.cultivation or 0),
        gain,
    )

    settled_minutes = min(resolved_minutes + affordable_minutes, total_minutes)
    finished = insufficient_stone or settled_minutes >= total_minutes or now >= end_at
    updated = upsert_profile(
        tg,
        cultivation=cultivation,
        realm_layer=layer,
        spiritual_stone=max(int(profile.spiritual_stone or 0) - cost, 0),
        retreat_minutes_resolved=0 if finished else settled_minutes,
        retreat_started_at=None if finished else profile.retreat_started_at,
        retreat_end_at=None if finished else profile.retreat_end_at,
        retreat_gain_per_minute=0 if finished else int(profile.retreat_gain_per_minute or 0),
        retreat_cost_per_minute=0 if finished else int(profile.retreat_cost_per_minute or 0),
        retreat_minutes_total=0 if finished else total_minutes,
    )

    return {
        "gain": gain,
        "cost": cost,
        "upgraded_layers": upgraded_layers,
        "remaining": remaining,
        "finished": finished,
        "insufficient_stone": insufficient_stone,
        "profile": serialize_profile(updated),
    }


def ensure_not_in_retreat(tg: int) -> None:
    profile = get_profile(tg, create=False)
    if profile is not None and _is_retreating(profile):
        raise ValueError("你正在闭关中，当前不能执行这个操作。")


def build_plugin_url(path: str) -> str | None:
    public_url = (api_config.public_url or "").rstrip("/")
    if not public_url:
        return None
    return f"{public_url}{path}"


def xiuxian_entry_button() -> InlineKeyboard:
    return ikb([[("初入仙途", "xiuxian:entry")]])


def xiuxian_confirm_keyboard() -> InlineKeyboard:
    app_url = build_plugin_url("/plugins/xiuxian/app")
    rows = [[("确认入道", "xiuxian:confirm"), ("返回", "back_start")]]
    if app_url:
        rows.append([("打开修仙面板", app_url, "url")])
    return ikb(rows)


def xiuxian_profile_keyboard() -> InlineKeyboard:
    app_url = build_plugin_url("/plugins/xiuxian/app")
    rows = [[("吐纳修炼", "xiuxian:train"), ("尝试突破", "xiuxian:break")]]
    if app_url:
        rows.append([("打开修仙面板", app_url, "url")])
    rows.append([("返回主页", "back_start")])
    return ikb(rows)


def leaderboard_keyboard(kind: str, page: int, total_pages: int) -> InlineKeyboard:
    keyboard = InlineKeyboard()
    keyboard.row(
        InlineButton("灵石榜", "xiuxian:rank:stone:1"),
        InlineButton("境界榜", "xiuxian:rank:realm:1"),
        InlineButton("法宝榜", "xiuxian:rank:artifact:1"),
    )
    pager = []
    if page > 1:
        pager.append(InlineButton("上一页", f"xiuxian:rank:{kind}:{page - 1}"))
    pager.append(InlineButton(f"{page}/{max(total_pages, 1)}", "xiuxian:noop"))
    if page < total_pages:
        pager.append(InlineButton("下一页", f"xiuxian:rank:{kind}:{page + 1}"))
    keyboard.row(*pager)
    return keyboard


def duel_keyboard(challenger_tg: int, defender_tg: int, stake: int, bet_minutes: int) -> InlineKeyboard:
    return ikb(
        [[
            ("接受斗法", f"xiuxian:duel:accept:{challenger_tg}:{defender_tg}:{stake}:{bet_minutes}"),
            ("拒绝斗法", f"xiuxian:duel:reject:{challenger_tg}:{defender_tg}:{stake}:{bet_minutes}"),
        ]]
    )


def cultivation_threshold(stage: str, layer: int) -> int:
    return 80 + realm_index(stage) * 30 + max(layer, 1) * 18


def next_realm_stage(stage: str) -> str | None:
    idx = realm_index(stage)
    if idx >= len(REALM_ORDER) - 1:
        return None
    return REALM_ORDER[idx + 1]


def determine_relation(primary: str, secondary: str) -> tuple[str, int]:
    if ELEMENT_GENERATES.get(primary) == secondary or ELEMENT_GENERATES.get(secondary) == primary:
        return "相生", 5
    if ELEMENT_CONTROLS.get(primary) == secondary or ELEMENT_CONTROLS.get(secondary) == primary:
        return "相克", -5
    return "平衡", 0


def ensure_xiuxian_profile(tg: int) -> dict[str, Any]:
    profile = get_profile(tg, create=True)
    return serialize_profile(profile)


def _legacy_serialize_full_profile(tg: int) -> dict[str, Any]:
    ensure_seed_data()
    profile = get_profile(tg, create=True)
    if profile and profile.consented:
        _settle_retreat_progress(tg)
        profile = get_profile(tg, create=False)

    profile_data = serialize_profile(profile)
    if profile_data is None:
        raise ValueError("未找到修仙档案。")

    progress = build_progress(
        profile_data["realm_stage"],
        int(profile_data["realm_layer"] or 1),
        int(profile_data["cultivation"] or 0),
    )
    retreating = _is_retreating(profile)
    xiuxian_settings = get_xiuxian_settings()
    equip_limit = max(int(xiuxian_settings.get("artifact_equip_limit", DEFAULT_SETTINGS["artifact_equip_limit"]) or 0), 1)
    equipped_rows = list_equipped_artifacts(tg)
    artifact_set_map = _artifact_set_index()
    equipped = []
    equipped_ids: set[int] = set()
    equipped_slot_names: set[str] = set()
    for row in equipped_rows:
        item = _decorate_artifact_with_set(row["artifact"], artifact_set_map)
        item["resolved_effects"] = resolve_artifact_effects(profile_data, item)
        item["equipped"] = True
        item["slot"] = row["slot"]
        equipped.append(item)
        equipped_ids.add(int(item["id"]))
        if str(item.get("equip_slot") or "").strip():
            equipped_slot_names.add(str(item.get("equip_slot") or "").strip())
    active_talisman = serialize_talisman(get_talisman(profile.active_talisman_id)) if profile and profile.active_talisman_id else None
    if active_talisman:
        active_talisman["resolved_effects"] = resolve_talisman_effects(profile_data, active_talisman)
    current_technique = _current_technique_payload(profile_data)
    current_title = get_current_title(tg)
    if current_title:
        current_title["resolved_effects"] = resolve_title_effects(profile_data, current_title)
    profile_data["current_title_name"] = (current_title or {}).get("name")
    profile_data["display_name_with_title"] = _profile_name_with_title(profile_data, current_title)

    artifact_set_bundle = _resolve_active_artifact_sets(equipped)
    artifacts = build_user_artifact_rows(profile_data, tg, retreating, equip_limit, equipped_ids, equipped_slot_names)
    techniques = _build_user_technique_rows(profile_data, tg)
    pills = []
    for row in list_user_pills(tg):
        item = row["pill"]
        item["resolved_effects"] = resolve_pill_effects(profile_data, item)
        reason = _pill_usage_reason(profile_data, item)
        usable = not reason
        row["pill"]["usable"] = usable and not retreating
        row["pill"]["unusable_reason"] = "闭关期间无法使用丹药" if usable and retreating else reason
        pills.append(row)

    talismans = []
    for row in list_user_talismans(tg):
        total_quantity = max(int(row.get("quantity") or 0), 0)
        bound_quantity = max(min(int(row.get("bound_quantity") or 0), total_quantity), 0)
        item = row["talisman"]
        item["resolved_effects"] = resolve_talisman_effects(profile_data, item)
        usable = realm_requirement_met(profile_data, item.get("min_realm_stage"), item.get("min_realm_layer"))
        reason = "" if usable else f"需要达到 {format_realm_requirement(item.get('min_realm_stage'), item.get('min_realm_layer'))}"
        if profile_data.get("active_talisman_id") and profile_data.get("active_talisman_id") != item["id"]:
            usable = False
            reason = "你已经预装了一张待生效的符箓"
        row["bound_quantity"] = bound_quantity
        row["unbound_quantity"] = max(total_quantity - bound_quantity, 0)
        row["consumable_quantity"] = row["unbound_quantity"]
        row["tradeable_quantity"] = row["unbound_quantity"]
        item["usable"] = usable and not retreating
        item["active"] = profile_data.get("active_talisman_id") == item["id"]
        item["unusable_reason"] = "闭关期间无法启用符箓" if usable and not item["active"] and retreating else reason
        item["bound"] = bound_quantity > 0
        item["bound_quantity"] = bound_quantity
        talismans.append(row)

    titles = []
    current_title_id = int(profile_data.get("current_title_id") or 0)
    for row in list_user_titles(tg):
        title = row.get("title") or {}
        title["resolved_effects"] = resolve_title_effects(profile_data, title)
        title["equipped"] = int(title.get("id") or 0) == current_title_id
        title["action_label"] = "卸下称号" if title["equipped"] else "佩戴称号"
        row["title"] = title
        titles.append(row)

    achievement_overview = build_user_achievement_overview(tg)

    all_personal_shop = list_shop_items(official_only=False)
    personal_shop = [item for item in all_personal_shop if item["owner_tg"] == tg]
    community_shop = [item for item in all_personal_shop if item["owner_tg"] not in {None, tg}]
    settings = {
        **get_exchange_settings(),
        "artifact_equip_limit": equip_limit,
        "equipment_unbind_cost": int(xiuxian_settings.get("equipment_unbind_cost", DEFAULT_SETTINGS["equipment_unbind_cost"]) or 0),
        "artifact_plunder_chance": int(
            xiuxian_settings.get("artifact_plunder_chance", DEFAULT_SETTINGS["artifact_plunder_chance"]) or 0
        ),
        "duel_winner_steal_percent": int(
            xiuxian_settings.get("duel_winner_steal_percent", DEFAULT_SETTINGS["duel_winner_steal_percent"]) or 0
        ),
        "official_shop_name": str(xiuxian_settings.get("official_shop_name", DEFAULT_SETTINGS["official_shop_name"]) or DEFAULT_SETTINGS["official_shop_name"]),
        "allow_user_task_publish": bool(xiuxian_settings.get("allow_user_task_publish", DEFAULT_SETTINGS["allow_user_task_publish"])),
        "task_publish_cost": max(int(xiuxian_settings.get("task_publish_cost", DEFAULT_SETTINGS["task_publish_cost"]) or 0), 0),
    }

    capabilities = {
        "can_train": profile_data["consented"] and not retreating and not is_same_china_day(profile.last_train_at, utcnow()),
        "train_reason": "" if not retreating and not is_same_china_day(profile.last_train_at, utcnow()) else ("闭关期间无法吐纳修炼" if retreating else "今日已经完成过吐纳修炼了"),
        "can_breakthrough": profile_data["consented"] and not retreating and int(profile_data["realm_layer"] or 0) >= 9 and bool(progress["breakthrough_ready"]),
        "breakthrough_reason": "" if not retreating and int(profile_data["realm_layer"] or 0) >= 9 and progress["breakthrough_ready"] else ("闭关期间无法突破" if retreating else "只有达到当前境界九层且满修为后才能突破"),
        "can_retreat": profile_data["consented"] and not retreating,
        "retreat_reason": "" if not retreating else "你正在闭关中",
        "is_in_retreat": retreating,
        "artifact_equip_limit": equip_limit,
        "equipped_artifact_count": len(equipped),
    }

    return {
        "profile": profile_data,
        "progress": progress,
        "capabilities": capabilities,
        "emby_balance": get_emby_balance(tg),
        "equipped_artifact": equipped[0] if equipped else None,
        "equipped_artifacts": equipped,
        "active_talisman": active_talisman,
        "current_technique": current_technique,
        "current_title": current_title,
        "active_artifact_sets": artifact_set_bundle["sets"],
        "artifacts": artifacts,
        "pills": pills,
        "talismans": talismans,
        "techniques": techniques,
        "technique_owned_count": len(techniques),
        "technique_total_count": len(list_techniques(enabled_only=True)),
        "titles": titles,
        "achievements": achievement_overview.get("achievements") or [],
        "achievement_metric_progress": achievement_overview.get("metric_progress") or {},
        "achievement_unlocked_count": int(achievement_overview.get("unlocked_count") or 0),
        "achievement_total_count": int(achievement_overview.get("total_count") or 0),
        "settings": settings,
        "official_shop": list_shop_items(official_only=True),
        "community_shop": community_shop,
        "personal_shop": personal_shop,
    }


def _find_pill_in_inventory(tg: int, pill_type: str) -> dict[str, Any] | None:
    for row in list_user_pills(tg):
        pill = row["pill"]
        if pill["pill_type"] == pill_type and row["quantity"] > 0:
            return row
    return None


def equip_artifact_for_user(tg: int, artifact_id: int) -> dict[str, Any]:
    ensure_not_in_retreat(tg)
    profile = serialize_profile(get_profile(tg, create=False))
    if profile is None:
        raise ValueError("你还没有踏入仙途。")

    owned = {row["artifact"]["id"] for row in list_user_artifacts(tg)}
    if artifact_id not in owned:
        raise ValueError("你的背包里没有这件法宝。")
    artifact = get_artifact(artifact_id)
    if artifact is None:
        raise ValueError("未找到目标法宝。")
    if not realm_requirement_met(profile, artifact.min_realm_stage, artifact.min_realm_layer):
        raise ValueError(f"需要达到 {format_realm_requirement(artifact.min_realm_stage, artifact.min_realm_layer)} 才能装备这件法宝。")

    equip_limit = max(int(get_xiuxian_settings().get("artifact_equip_limit", DEFAULT_SETTINGS["artifact_equip_limit"]) or 0), 1)
    result = set_equipped_artifact(tg, artifact_id, equip_limit)
    if result is None:
        raise ValueError("法宝装备状态更新失败。")
    return {
        "action": result["action"],
        "artifact_name": artifact.name,
        "profile": serialize_full_profile(tg),
    }


def bind_artifact_for_user(tg: int, artifact_id: int) -> dict[str, Any]:
    profile_obj = get_profile(tg, create=False)
    if profile_obj is None or not profile_obj.consented:
        raise ValueError("你还没有踏入仙途。")
    artifact = get_artifact(artifact_id)
    if artifact is None:
        raise ValueError("未找到目标法宝。")
    result = bind_user_artifact(tg, artifact_id, 1)
    return {
        "artifact": serialize_artifact(artifact),
        "bound_quantity": int(result.get("bound_quantity") or 0),
        "profile": serialize_full_profile(tg),
    }


def unbind_artifact_for_user(tg: int, artifact_id: int) -> dict[str, Any]:
    profile_obj = get_profile(tg, create=False)
    if profile_obj is None or not profile_obj.consented:
        raise ValueError("你还没有踏入仙途。")
    artifact = get_artifact(artifact_id)
    if artifact is None:
        raise ValueError("未找到目标法宝。")
    cost = max(int(get_xiuxian_settings().get("equipment_unbind_cost", DEFAULT_SETTINGS["equipment_unbind_cost"]) or 0), 0)
    result = unbind_user_artifact(tg, artifact_id, cost, 1)
    return {
        "artifact": serialize_artifact(artifact),
        "bound_quantity": int(result.get("bound_quantity") or 0),
        "cost": int(result.get("cost") or 0),
        "profile": serialize_full_profile(tg),
    }


def activate_talisman_for_user(tg: int, talisman_id: int) -> dict[str, Any]:
    ensure_not_in_retreat(tg)
    profile_obj = get_profile(tg, create=False)
    if profile_obj is None or not profile_obj.consented:
        raise ValueError("你还没有踏入仙途。")
    if profile_obj.active_talisman_id:
        raise ValueError("你已经准备了一张符箓，需先消耗后才能再启用。")

    owned = {row["talisman"]["id"] for row in list_user_talismans(tg)}
    if talisman_id not in owned:
        raise ValueError("你的背包里没有这张符箓。")

    talisman = get_talisman(talisman_id)
    if talisman is None or not talisman.enabled:
        raise ValueError("未找到可用的符箓。")
    if not realm_requirement_met(serialize_profile(profile_obj), talisman.min_realm_stage, talisman.min_realm_layer):
        raise ValueError(f"需要达到 {format_realm_requirement(talisman.min_realm_stage, talisman.min_realm_layer)} 才能启用这张符箓。")
    if not consume_user_talisman(tg, talisman_id, 1):
        raise ValueError("你的背包里没有足够的符箓。")

    set_active_talisman(tg, talisman_id)
    return {
        "talisman": serialize_talisman(talisman),
        "profile": serialize_full_profile(tg),
    }


def bind_talisman_for_user(tg: int, talisman_id: int) -> dict[str, Any]:
    profile_obj = get_profile(tg, create=False)
    if profile_obj is None or not profile_obj.consented:
        raise ValueError("你还没有踏入仙途。")
    talisman = get_talisman(talisman_id)
    if talisman is None or not talisman.enabled:
        raise ValueError("未找到可用的符箓。")
    result = bind_user_talisman(tg, talisman_id, 1)
    return {
        "talisman": serialize_talisman(talisman),
        "bound_quantity": int(result.get("bound_quantity") or 0),
        "profile": serialize_full_profile(tg),
    }


def unbind_talisman_for_user(tg: int, talisman_id: int) -> dict[str, Any]:
    profile_obj = get_profile(tg, create=False)
    if profile_obj is None or not profile_obj.consented:
        raise ValueError("你还没有踏入仙途。")
    talisman = get_talisman(talisman_id)
    if talisman is None or not talisman.enabled:
        raise ValueError("未找到可用的符箓。")
    cost = max(int(get_xiuxian_settings().get("equipment_unbind_cost", DEFAULT_SETTINGS["equipment_unbind_cost"]) or 0), 0)
    result = unbind_user_talisman(tg, talisman_id, cost, 1)
    return {
        "talisman": serialize_talisman(talisman),
        "bound_quantity": int(result.get("bound_quantity") or 0),
        "cost": int(result.get("cost") or 0),
        "profile": serialize_full_profile(tg),
    }


def activate_technique_for_user(tg: int, technique_id: int) -> dict[str, Any]:
    ensure_seed_data()
    profile_obj = get_profile(tg, create=False)
    if profile_obj is None or not profile_obj.consented:
        raise ValueError("你还没有踏入仙途。")
    owned_ids = {
        int((row.get("technique") or {}).get("id") or 0)
        for row in list_user_techniques(tg, enabled_only=True)
    }
    if int(technique_id) not in owned_ids:
        raise ValueError("你尚未获得这门功法，需要先通过探索或机缘参悟。")
    technique = get_technique(technique_id)
    if technique is None or not technique.enabled:
        raise ValueError("未找到可用的功法。")
    profile_data = serialize_profile(profile_obj)
    if not realm_requirement_met(profile_data, technique.min_realm_stage, technique.min_realm_layer):
        raise ValueError(f"需要达到 {format_realm_requirement(technique.min_realm_stage, technique.min_realm_layer)} 才能参悟这门功法。")
    set_current_technique(tg, technique_id)
    return {
        "technique": serialize_technique(technique),
        "profile": serialize_full_profile(tg),
    }


def set_current_title_for_user(tg: int, title_id: int | None) -> dict[str, Any]:
    profile_obj = get_profile(tg, create=False)
    if profile_obj is None or not profile_obj.consented:
        raise ValueError("你还没有踏入仙途。")
    title = set_current_title(tg, title_id)
    return {
        "title": title,
        "profile": serialize_full_profile(tg),
    }


def start_retreat_for_user(tg: int, hours: int) -> dict[str, Any]:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("你还没有踏入仙途。")
    if _is_retreating(profile):
        raise ValueError("你已经在闭关中。")

    retreat_hours = max(min(int(hours or 0), 4), 1)
    plan = _compute_retreat_plan(profile)
    total_minutes = retreat_hours * 60
    total_cost = plan["cost_per_minute"] * total_minutes
    if int(profile.spiritual_stone or 0) < total_cost:
        raise ValueError(f"灵石不足，闭关 {retreat_hours} 小时预计需要 {total_cost} 灵石。")

    now = utcnow()
    updated = upsert_profile(
        tg,
        retreat_started_at=now,
        retreat_end_at=now + timedelta(hours=retreat_hours),
        retreat_gain_per_minute=plan["gain_per_minute"],
        retreat_cost_per_minute=plan["cost_per_minute"],
        retreat_minutes_total=total_minutes,
        retreat_minutes_resolved=0,
    )
    return {
        "hours": retreat_hours,
        "estimated_gain": plan["gain_per_minute"] * total_minutes,
        "estimated_cost": total_cost,
        "profile": serialize_full_profile(updated.tg),
    }


def finish_retreat_for_user(tg: int) -> dict[str, Any]:
    result = _settle_retreat_progress(tg)
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("你还没有踏入仙途。")
    if result is None and not _is_retreating(profile):
        raise ValueError("你当前并未处于闭关状态。")

    upsert_profile(
        tg,
        retreat_started_at=None,
        retreat_end_at=None,
        retreat_gain_per_minute=0,
        retreat_cost_per_minute=0,
        retreat_minutes_total=0,
        retreat_minutes_resolved=0,
    )
    return {
        "settled": result or {"gain": 0, "cost": 0, "upgraded_layers": [], "finished": True},
        "profile": serialize_full_profile(tg),
    }


def create_personal_shop_listing(
    *,
    tg: int,
    shop_name: str,
    item_kind: str,
    item_ref_id: int,
    quantity: int,
    price_stone: int,
    broadcast: bool,
) -> dict[str, Any]:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("你还没有踏入仙途。")
    if _is_retreating(profile):
        raise ValueError("闭关期间无法上架个人商店。")

    item_name = ""
    if item_kind == "artifact":
        artifact = get_artifact(item_ref_id)
        if artifact is None:
            raise ValueError("未找到目标法宝。")
        if not use_user_artifact_listing_stock(tg, item_ref_id, quantity):
            raise ValueError("可交易的法宝数量不足，已绑定或已装备的法宝无法上架。")
        item_name = artifact.name
    elif item_kind == "pill":
        pill = get_pill(item_ref_id)
        if pill is None:
            raise ValueError("未找到目标丹药。")
        if not use_user_pill_listing_stock(tg, item_ref_id, quantity):
            raise ValueError("背包里的丹药数量不足。")
        item_name = pill.name
    elif item_kind == "material":
        material = get_material(item_ref_id)
        if material is None:
            raise ValueError("未找到目标材料。")
        if not use_user_material_listing_stock(tg, item_ref_id, quantity):
            raise ValueError("背包里的材料数量不足。")
        item_name = material.name
    elif item_kind == "talisman":
        talisman = get_talisman(item_ref_id)
        if talisman is None:
            raise ValueError("未找到目标符箓。")
        if not use_user_talisman_listing_stock(tg, item_ref_id, quantity):
            raise ValueError("可交易的符箓数量不足，已绑定的符箓无法上架。")
        item_name = talisman.name
    else:
        raise ValueError("不支持的上架物品类型。")

    settings = get_xiuxian_settings()
    broadcast_cost = int(settings.get("shop_broadcast_cost", DEFAULT_SETTINGS["shop_broadcast_cost"]) or 0)
    charisma_discount = min(max(int(profile.charisma or 0) - 10, 0) // 4, broadcast_cost)
    final_broadcast_cost = max(broadcast_cost - charisma_discount, 0)
    if broadcast and int(profile.spiritual_stone or 0) < final_broadcast_cost:
        raise ValueError("灵石不足，无法支付全群播报费用。")

    resolved_shop_name = str(shop_name or profile.shop_name or PERSONAL_SHOP_NAME).strip() or PERSONAL_SHOP_NAME

    listing = create_shop_item(
        owner_tg=tg,
        shop_name=resolved_shop_name,
        item_kind=item_kind,
        item_ref_id=item_ref_id,
        item_name=item_name,
        quantity=quantity,
        price_stone=price_stone,
        is_official=False,
    )

    updated = upsert_profile(
        tg,
        shop_name=resolved_shop_name,
        shop_broadcast=bool(broadcast),
        spiritual_stone=int(profile.spiritual_stone or 0) - (final_broadcast_cost if broadcast else 0),
    )

    return {
        "listing": listing,
        "broadcast_cost": final_broadcast_cost if broadcast else 0,
        "broadcast_discount": charisma_discount if broadcast else 0,
        "profile": serialize_profile(updated),
    }


def create_official_shop_listing(
    *,
    item_kind: str,
    item_ref_id: int,
    quantity: int,
    price_stone: int,
    shop_name: str | None = None,
) -> dict[str, Any]:
    settings = get_xiuxian_settings()
    official_name = str(settings.get("official_shop_name", DEFAULT_SETTINGS["official_shop_name"]) or DEFAULT_SETTINGS["official_shop_name"]).strip() or DEFAULT_SETTINGS["official_shop_name"]
    if item_kind == "artifact":
        artifact = get_artifact(item_ref_id)
        if artifact is None:
            raise ValueError("未找到目标法宝。")
        item_name = artifact.name
    elif item_kind == "pill":
        pill = get_pill(item_ref_id)
        if pill is None:
            raise ValueError("未找到目标丹药。")
        item_name = pill.name
    elif item_kind == "talisman":
        talisman = get_talisman(item_ref_id)
        if talisman is None:
            raise ValueError("未找到目标符箓。")
        item_name = talisman.name
    elif item_kind == "material":
        material = get_material(item_ref_id)
        if material is None:
            raise ValueError("未找到目标材料。")
        item_name = material.name
    else:
        raise ValueError("不支持的官方商店物品类型。")

    return create_shop_item(
        owner_tg=None,
        shop_name=official_name,
        item_kind=item_kind,
        item_ref_id=item_ref_id,
        item_name=item_name,
        quantity=quantity,
        price_stone=price_stone,
        is_official=True,
    )


def patch_shop_listing(item_id: int, **fields) -> dict[str, Any] | None:
    return update_shop_item(item_id, **fields)


def update_xiuxian_settings(payload: dict[str, Any]) -> dict[str, Any]:
    patch = dict(payload)
    if "shop_broadcast_cost" in patch and patch["shop_broadcast_cost"] is not None:
        patch["shop_broadcast_cost"] = min(
            _coerce_int(
                patch["shop_broadcast_cost"],
                DEFAULT_SETTINGS["shop_broadcast_cost"],
                0,
            ),
            1000000,
        )
    if "official_shop_name" in patch and patch["official_shop_name"] is not None:
        patch["official_shop_name"] = str(patch["official_shop_name"]).strip() or DEFAULT_SETTINGS["official_shop_name"]
    if "allow_user_task_publish" in patch:
        patch["allow_user_task_publish"] = bool(patch["allow_user_task_publish"])
    if "task_publish_cost" in patch and patch["task_publish_cost"] is not None:
        patch["task_publish_cost"] = min(
            _coerce_int(
                patch["task_publish_cost"],
                DEFAULT_SETTINGS["task_publish_cost"],
                0,
            ),
            1000000,
        )
    if "equipment_unbind_cost" in patch and patch["equipment_unbind_cost"] is not None:
        patch["equipment_unbind_cost"] = min(
            _coerce_int(
                patch["equipment_unbind_cost"],
                DEFAULT_SETTINGS["equipment_unbind_cost"],
                0,
            ),
            1000000,
        )
    if "artifact_plunder_chance" in patch and patch["artifact_plunder_chance"] is not None:
        patch["artifact_plunder_chance"] = min(
            _coerce_int(
                patch["artifact_plunder_chance"],
                DEFAULT_SETTINGS["artifact_plunder_chance"],
                0,
            ),
            100,
        )
    if "duel_winner_steal_percent" in patch and patch["duel_winner_steal_percent"] is not None:
        patch["duel_winner_steal_percent"] = min(
            _coerce_int(
                patch["duel_winner_steal_percent"],
                DEFAULT_SETTINGS["duel_winner_steal_percent"],
                0,
            ),
            100,
        )
    if "message_auto_delete_seconds" in patch and patch["message_auto_delete_seconds"] is not None:
        patch["message_auto_delete_seconds"] = min(
            _coerce_int(
                patch["message_auto_delete_seconds"],
                DEFAULT_SETTINGS["message_auto_delete_seconds"],
                0,
            ),
            86400,
        )
    if "root_quality_value_rules" in patch:
        patch["root_quality_value_rules"] = _normalize_root_quality_value_rules(patch["root_quality_value_rules"])
    if "item_quality_value_rules" in patch:
        patch["item_quality_value_rules"] = _normalize_item_quality_value_rules(patch["item_quality_value_rules"])
    if "exploration_drop_weight_rules" in patch:
        defaults = DEFAULT_SETTINGS["exploration_drop_weight_rules"]
        raw = patch["exploration_drop_weight_rules"] if isinstance(patch["exploration_drop_weight_rules"], dict) else {}
        patch["exploration_drop_weight_rules"] = {
            "material_divine_sense_divisor": _coerce_int(raw.get("material_divine_sense_divisor"), defaults["material_divine_sense_divisor"], 1),
            "high_quality_threshold": min(
                _coerce_int(raw.get("high_quality_threshold"), defaults["high_quality_threshold"], 1),
                max(ROOT_QUALITY_LEVELS.values()),
            ),
            "high_quality_fortune_divisor": _coerce_int(raw.get("high_quality_fortune_divisor"), defaults["high_quality_fortune_divisor"], 1),
            "high_quality_root_level_start": _coerce_int(raw.get("high_quality_root_level_start"), defaults["high_quality_root_level_start"], 0),
        }
    if "high_quality_broadcast_level" in patch and patch["high_quality_broadcast_level"] is not None:
        patch["high_quality_broadcast_level"] = min(
            _coerce_int(patch["high_quality_broadcast_level"], DEFAULT_SETTINGS["high_quality_broadcast_level"], 1),
            max(ROOT_QUALITY_LEVELS.values()),
        )
    if "immortal_touch_infusion_layers" in patch and patch["immortal_touch_infusion_layers"] is not None:
        patch["immortal_touch_infusion_layers"] = min(
            _coerce_int(
                patch["immortal_touch_infusion_layers"],
                DEFAULT_SETTINGS["immortal_touch_infusion_layers"],
                1,
            ),
            9,
        )
    settings = set_xiuxian_settings(patch)
    if "official_shop_name" in patch:
        sync_official_shop_name(settings["official_shop_name"])
    return settings


def grant_item_to_user(tg: int, item_kind: str, item_ref_id: int, quantity: int) -> dict[str, Any]:
    if item_kind == "artifact":
        return grant_artifact_to_user(tg, item_ref_id, quantity)
    if item_kind == "material":
        return grant_material_to_user(tg, item_ref_id, quantity)
    if item_kind == "pill":
        return grant_pill_to_user(tg, item_ref_id, quantity)
    if item_kind == "talisman":
        return grant_talisman_to_user(tg, item_ref_id, quantity)
    if item_kind == "recipe":
        return grant_recipe_to_user(tg, item_ref_id, source="admin", obtained_note="后台发放")
    if item_kind == "technique":
        return grant_technique_to_user(
            tg,
            item_ref_id,
            source="admin",
            obtained_note="后台发放",
            auto_equip_if_empty=True,
        )
    raise ValueError("不支持的发放物品类型。")


def purchase_shop_item(tg: int, item_id: int, quantity: int = 1) -> dict[str, Any]:
    ensure_not_in_retreat(tg)
    return sql_purchase_shop_item(tg, item_id, quantity)


def compute_artifact_score(
    profile: dict[str, Any],
    equipped_artifacts: list[dict[str, Any]] | None,
    opponent_profile: dict[str, Any] | None = None,
) -> int:
    if not equipped_artifacts:
        return 0
    effects = merge_artifact_effects(profile, equipped_artifacts, opponent_profile)
    return (
        int(round(effects.get("attack_bonus", 0)))
        + int(round(effects.get("defense_bonus", 0)))
        + int(round(effects.get("bone_bonus", 0)))
        + int(round(effects.get("comprehension_bonus", 0)))
        + int(round(effects.get("divine_sense_bonus", 0)))
        + int(round(effects.get("fortune_bonus", 0)))
        + int(round(effects.get("body_movement_bonus", 0)))
        + int(round(effects.get("qi_blood_bonus", 0) / 10))
        + int(round(effects.get("true_yuan_bonus", 0) / 10))
        + int(round(effects.get("duel_rate_bonus", 0))) * 10
        + int(round(effects.get("cultivation_bonus", 0))) * 2
    )


def compute_talisman_score(
    profile: dict[str, Any],
    active_talisman: dict[str, Any] | None,
    opponent_profile: dict[str, Any] | None = None,
) -> int:
    if active_talisman is None:
        return 0
    effects = resolve_talisman_effects(profile, active_talisman, opponent_profile)
    return (
        int(round(effects.get("attack_bonus", 0)))
        + int(round(effects.get("defense_bonus", 0)))
        + int(round(effects.get("bone_bonus", 0)))
        + int(round(effects.get("comprehension_bonus", 0)))
        + int(round(effects.get("divine_sense_bonus", 0)))
        + int(round(effects.get("fortune_bonus", 0)))
        + int(round(effects.get("body_movement_bonus", 0)))
        + int(round(effects.get("qi_blood_bonus", 0) / 10))
        + int(round(effects.get("true_yuan_bonus", 0) / 10))
        + int(round(effects.get("duel_rate_bonus", 0))) * 10
    )


def build_leaderboard(kind: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    profiles = [serialize_profile(row) for row in list_profiles()]
    tgs = [int(item["tg"]) for item in profiles]
    emby_name_map = get_emby_name_map(tgs)

    rows = []
    for item in profiles:
        equipped_artifacts = collect_equipped_artifacts(int(item["tg"]))
        base = {
            "tg": item["tg"],
            "name": emby_name_map.get(item["tg"], f"TG {item['tg']}"),
            "realm_stage": item["realm_stage"],
            "realm_layer": item["realm_layer"],
            "cultivation": int(item["cultivation"] or 0),
            "spiritual_stone": item["spiritual_stone"],
            "artifact_name": ", ".join(artifact["name"] for artifact in equipped_artifacts[:3]) if equipped_artifacts else None,
            "artifact_score": compute_artifact_score(item, equipped_artifacts),
            "realm_stage_rank": realm_index(item["realm_stage"]),
        }
        if kind == "stone":
            base["score"] = int(item["spiritual_stone"] or 0)
        elif kind == "realm":
            base["score"] = base["realm_stage_rank"]
        else:
            base["score"] = base["artifact_score"]
        rows.append(base)

    if kind == "realm":
        rows.sort(
            key=lambda row: (
                -int(row["realm_stage_rank"]),
                -int(row["realm_layer"] or 0),
                -int(row["cultivation"] or 0),
                -int(row["spiritual_stone"] or 0),
                int(row["tg"]),
            )
        )
    else:
        rows.sort(key=lambda row: (-int(row["score"] or 0), int(row["tg"])))
    rows = rows[:100]
    total = len(rows)
    total_pages = max((total + page_size - 1) // page_size, 1)
    current_page = min(max(int(page), 1), total_pages)
    start = (current_page - 1) * page_size
    items = rows[start:start + page_size]

    for index, item in enumerate(items, start=start + 1):
        item["rank"] = index

    return {
        "kind": kind,
        "page": current_page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "items": items,
    }


def format_leaderboard_text(result: dict[str, Any]) -> str:
    title_map = {
        "stone": "灵石排行榜",
        "realm": "境界排行榜",
        "artifact": "法宝排行榜",
    }
    lines = [f"**{title_map.get(result['kind'], '排行榜')}**", f"第 {result['page']} 页 / 共 {result['total_pages']} 页", ""]
    if not result["items"]:
        lines.append("当前没有可显示的数据。")
        return "\n".join(lines)

    for item in result["items"]:
        if result["kind"] == "stone":
            desc = f"{item['spiritual_stone']} 灵石"
        elif result["kind"] == "realm":
            desc = f"{item['realm_stage']}{item['realm_layer']}层"
        else:
            desc = item["artifact_name"] or "暂无装备法宝"
        lines.append(f"{item['rank']}. {item['name']} | {desc}")
    return "\n".join(lines)


def create_foundation_pill_for_user_if_missing(tg: int) -> None:
    pill_row = _find_pill_in_inventory(tg, "foundation")
    if pill_row is not None:
        return

    for pill in list_pills(enabled_only=True):
        if pill["pill_type"] == "foundation":
            grant_pill_to_user(tg, pill["id"], 1)
            return


def admin_seed_demo_assets(tg: int) -> dict[str, Any]:
    ensure_seed_data()
    first_artifact = next((item for item in list_artifacts(enabled_only=True)), None)
    foundation_pill = next((item for item in list_pills(enabled_only=True) if item["pill_type"] == "foundation"), None)
    clear_pill = next((item for item in list_pills(enabled_only=True) if item["pill_type"] == "clear_poison"), None)
    first_talisman = next((item for item in list_talismans(enabled_only=True)), None)

    if first_artifact:
        grant_artifact_to_user(tg, first_artifact["id"], 1)
    if foundation_pill:
        grant_pill_to_user(tg, foundation_pill["id"], 1)
    if clear_pill:
        grant_pill_to_user(tg, clear_pill["id"], 1)
    if first_talisman:
        grant_talisman_to_user(tg, first_talisman["id"], 1)

    return serialize_full_profile(tg)


def maybe_gain_cultivation_from_chat(tg: int) -> dict[str, Any] | None:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented or _is_retreating(profile):
        return None

    settings = get_xiuxian_settings()
    base_chance = max(min(int(settings.get("chat_cultivation_chance", DEFAULT_SETTINGS["chat_cultivation_chance"]) or 0), 100), 0)
    if base_chance <= 0:
        return None
    chance_roll = roll_probability_percent(
        base_chance,
        actor_fortune=int(profile.fortune or 0),
        actor_weight=0.35,
        minimum=0,
        maximum=100,
    )
    if not chance_roll["success"]:
        return None

    min_gain = max(int(settings.get("chat_cultivation_min_gain", DEFAULT_SETTINGS["chat_cultivation_min_gain"]) or 1), 1)
    max_gain = max(int(settings.get("chat_cultivation_max_gain", DEFAULT_SETTINGS["chat_cultivation_max_gain"]) or min_gain), min_gain)
    gain = random.randint(min_gain, max_gain)
    layer, cultivation, upgraded_layers, remaining = apply_cultivation_gain(
        profile.realm_stage or "炼气",
        int(profile.realm_layer or 1),
        int(profile.cultivation or 0),
        gain,
    )
    updated = upsert_profile(
        tg,
        cultivation=cultivation,
        realm_layer=layer,
    )
    _apply_profile_growth_floor(tg)
    return {
        "gain": gain,
        "upgraded_layers": upgraded_layers,
        "remaining": remaining,
        "profile": serialize_profile(get_profile(updated.tg, create=False)),
    }


def broadcast_shop_copy(seller_name: str, shop_name: str, item_name: str, price_stone: int) -> str:
    return (
        f"📣 **坊市播报**\n"
        f"🧑‍🌾 {seller_name} 刚刚在 **{shop_name}** 上架了 **{item_name}**\n"
        f"💰 售价：{price_stone} 灵石\n"
        "🛍️ 感兴趣的道友可以前往修仙面板查看。"
    )


def convert_emby_coin_to_stone(tg: int, amount: int) -> dict[str, Any]:
    ensure_not_in_retreat(tg)
    return convert_coin_to_stone(tg, amount)


def convert_stone_to_emby_coin(tg: int, amount: int) -> dict[str, Any]:
    ensure_not_in_retreat(tg)
    return convert_stone_to_coin(tg, amount)


def list_public_shop_items() -> dict[str, Any]:
    settings = get_xiuxian_settings()
    return {
        "official_shop_name": settings.get("official_shop_name", DEFAULT_SETTINGS["official_shop_name"]),
        "official_items": list_shop_items(official_only=True),
    }


def search_xiuxian_players(
    query: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    return search_profiles(query=query, page=page, page_size=page_size)


def admin_patch_player(tg: int, **fields) -> dict[str, Any] | None:
    patch = dict(fields)
    root_fields = {"root_type", "root_primary", "root_secondary", "root_relation", "root_bonus", "root_quality"}
    if root_fields.intersection(patch):
        profile = serialize_profile(get_profile(tg, create=False))
        if profile is None or not profile.get("consented"):
            return None

        merged = {**profile, **patch}
        for key in ("root_type", "root_primary", "root_secondary", "root_relation", "root_quality"):
            if key in merged:
                merged[key] = str(merged.get(key) or "").strip() or None

        root_type = merged.get("root_type")
        if root_type != "双灵根":
            patch["root_secondary"] = None
            merged["root_secondary"] = None
        if root_type in {"单灵根", "地灵根"}:
            patch["root_relation"] = "平稳中正"
            merged["root_relation"] = "平稳中正"
        elif root_type == "天灵根":
            patch["root_relation"] = "天道垂青"
            merged["root_relation"] = "天道垂青"
        elif root_type == "变异灵根":
            patch["root_relation"] = "异灵独秀"
            merged["root_relation"] = "异灵独秀"

        has_root = any(merged.get(key) for key in ("root_type", "root_primary", "root_secondary", "root_quality"))
        if has_root:
            quality_name = _normalized_root_quality(merged)
            quality = _root_quality_payload(quality_name)
            patch["root_quality"] = quality_name
            patch["root_quality_level"] = int(quality["level"])
            patch["root_quality_color"] = quality["color"]
        else:
            patch["root_quality"] = None
            patch["root_quality_level"] = 1
            patch["root_quality_color"] = None
    result = admin_patch_profile(tg, **patch)
    if result is None:
        return None
    return _apply_profile_growth_floor(tg, explicit_fields=set(patch.keys()))


def build_admin_player_detail(tg: int) -> dict[str, Any] | None:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        return None
    bundle = serialize_full_profile(tg)
    bundle["materials"] = list_user_materials(tg)
    bundle["recipes"] = list_user_recipes(tg, enabled_only=False)
    return bundle


def admin_grant_player_resource(
    tg: int,
    item_kind: str,
    item_ref_id: int,
    quantity: int = 1,
    equip: bool = False,
) -> dict[str, Any]:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("玩家不存在")
    normalized_kind = str(item_kind or "").strip()
    if normalized_kind == "title":
        grant_title_to_user(
            tg,
            int(item_ref_id),
            source="admin",
            obtained_note="后台发放",
            equip=equip,
            auto_equip_if_empty=equip,
        )
    elif normalized_kind == "technique":
        grant_technique_to_user(
            tg,
            int(item_ref_id),
            source="admin",
            obtained_note="后台发放",
            auto_equip_if_empty=equip,
        )
        if equip:
            set_current_technique(tg, int(item_ref_id))
    else:
        grant_item_to_user(tg, normalized_kind, int(item_ref_id), max(int(quantity or 1), 1))
    return build_admin_player_detail(tg) or {}


def admin_set_player_inventory(
    tg: int,
    item_kind: str,
    item_ref_id: int,
    quantity: int,
    bound_quantity: int | None = None,
) -> dict[str, Any]:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("玩家不存在")
    normalized_kind = str(item_kind or "").strip()
    if normalized_kind == "artifact":
        admin_set_user_artifact_inventory(tg, int(item_ref_id), int(quantity), bound_quantity)
    elif normalized_kind == "pill":
        admin_set_user_pill_inventory(tg, int(item_ref_id), int(quantity))
    elif normalized_kind == "talisman":
        admin_set_user_talisman_inventory(tg, int(item_ref_id), int(quantity), bound_quantity)
    elif normalized_kind == "material":
        admin_set_user_material_inventory(tg, int(item_ref_id), int(quantity))
    else:
        raise ValueError("不支持的背包类型")
    return build_admin_player_detail(tg) or {}


def admin_revoke_player_resource(tg: int, item_kind: str, item_ref_id: int) -> dict[str, Any]:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("玩家不存在")
    normalized_kind = str(item_kind or "").strip()
    removed = False
    if normalized_kind == "title":
        removed = revoke_title_from_user(tg, int(item_ref_id))
    elif normalized_kind == "technique":
        removed = revoke_technique_from_user(tg, int(item_ref_id))
    elif normalized_kind == "recipe":
        removed = revoke_recipe_from_user(tg, int(item_ref_id))
    else:
        raise ValueError("不支持的移除类型")
    if not removed:
        raise ValueError("玩家未持有该条目")
    return build_admin_player_detail(tg) or {}


def admin_set_player_selection(tg: int, selection_kind: str, item_ref_id: int | None = None) -> dict[str, Any]:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("玩家不存在")
    normalized_kind = str(selection_kind or "").strip()
    target_id = None if item_ref_id in {None, 0} else int(item_ref_id)
    if normalized_kind == "title":
        set_current_title(tg, target_id)
    elif normalized_kind == "technique":
        if target_id is not None and target_id not in {int(item.get("id") or 0) for item in list_user_techniques(tg, enabled_only=False)}:
            raise ValueError("玩家未持有该功法")
        set_current_technique(tg, target_id)
    elif normalized_kind == "talisman":
        if target_id is not None and target_id not in {
            int((row.get("talisman") or {}).get("id") or 0)
            for row in list_user_talismans(tg)
        }:
            raise ValueError("玩家未持有该符箓")
        set_active_talisman(tg, target_id)
    elif normalized_kind == "artifact":
        if target_id is None:
            raise ValueError("法宝选择不能为空")
        if target_id not in {
            int((row.get("artifact") or {}).get("id") or 0)
            for row in list_user_artifacts(tg)
        }:
            raise ValueError("玩家背包里没有这件法宝")
        equip_limit = max(int(get_xiuxian_settings().get("artifact_equip_limit", DEFAULT_SETTINGS["artifact_equip_limit"]) or 0), 1)
        set_equipped_artifact(tg, target_id, equip_limit)
    else:
        raise ValueError("不支持的当前配置类型")
    return build_admin_player_detail(tg) or {}


def _battle_bundle(bundle_or_profile: dict[str, Any], opponent_profile: dict[str, Any] | None = None, apply_random: bool = False) -> dict[str, Any]:
    if "profile" in bundle_or_profile:
        bundle = bundle_or_profile
        profile = dict(bundle["profile"])
        artifacts = bundle.get("equipped_artifacts") or []
        talisman = bundle.get("active_talisman")
        technique = bundle.get("current_technique")
    else:
        profile = dict(bundle_or_profile)
        artifacts = collect_equipped_artifacts(int(profile["tg"]))
        active_talisman_id = profile.get("active_talisman_id")
        talisman = serialize_talisman(get_talisman(int(active_talisman_id))) if active_talisman_id else None
        current_technique_id = profile.get("current_technique_id")
        technique = serialize_technique(get_technique(int(current_technique_id))) if current_technique_id else None
    title = None
    if "profile" in bundle_or_profile:
        title = bundle.get("current_title")
    elif profile.get("current_title_id"):
        title = get_current_title(int(profile["tg"]))

    quality_name = _normalized_root_quality(profile)
    quality = _root_quality_payload(quality_name)
    sect_effects = get_sect_effects(profile)
    artifact_effects = merge_artifact_effects(profile, artifacts, opponent_profile)
    talisman_effects = resolve_talisman_effects(profile, talisman, opponent_profile) if talisman else None
    technique_effects = resolve_technique_effects(profile, technique, opponent_profile) if technique else None
    title_effects = resolve_title_effects(profile, title, opponent_profile) if title else None
    stats = _effective_stats(profile, artifact_effects, talisman_effects, sect_effects, technique_effects, title_effects)

    stage_index = realm_index(profile.get("realm_stage"))
    layer = int(profile.get("realm_layer") or 0)
    realm_base = 180 + stage_index * 220 + max(layer, 1) * 34
    attribute_factor = (
        1
        + stats["bone"] / 240
        + stats["comprehension"] / 260
        + stats["divine_sense"] / 280
        + stats["fortune"] / 320
        + stats["willpower"] / 340
        + stats["charisma"] / 420
        + stats["karma"] / 360
    )
    offense_factor = 1 + stats["attack_power"] / 200
    defense_factor = 1 + stats["defense_power"] / 220
    vitality_factor = 1 + stats["qi_blood"] / 2200
    mana_factor = 1 + stats["true_yuan"] / 2400
    movement_factor = 1 + stats["body_movement"] / 240
    artifact_factor = 1 + (
        artifact_effects.get("attack_bonus", 0)
        + artifact_effects.get("defense_bonus", 0)
        + artifact_effects.get("bone_bonus", 0)
        + artifact_effects.get("comprehension_bonus", 0)
        + artifact_effects.get("divine_sense_bonus", 0)
        + artifact_effects.get("fortune_bonus", 0)
        + artifact_effects.get("qi_blood_bonus", 0) / 8
        + artifact_effects.get("true_yuan_bonus", 0) / 8
        + artifact_effects.get("body_movement_bonus", 0)
    ) / 260
    talisman_factor = 1.0
    if talisman_effects:
        talisman_factor += (
            talisman_effects.get("attack_bonus", 0)
            + talisman_effects.get("defense_bonus", 0)
            + talisman_effects.get("bone_bonus", 0)
            + talisman_effects.get("comprehension_bonus", 0)
            + talisman_effects.get("divine_sense_bonus", 0)
            + talisman_effects.get("fortune_bonus", 0)
            + talisman_effects.get("qi_blood_bonus", 0) / 8
            + talisman_effects.get("true_yuan_bonus", 0) / 8
            + talisman_effects.get("body_movement_bonus", 0)
        ) / 320

    root_factor = float(quality["combat_factor"])
    if opponent_profile:
        root_factor += _root_element_duel_modifier(profile, opponent_profile)
    if profile.get("root_type") == "变异灵根":
        root_factor += 0.03
    duel_rate_factor = 1 + (stats["duel_rate_bonus"] / 100)
    random_factor = random.uniform(0.95, 1.10) if apply_random else 1.0
    power = (
        realm_base
        * attribute_factor
        * offense_factor
        * defense_factor
        * vitality_factor
        * mana_factor
        * movement_factor
        * max(root_factor, 0.75)
        * max(artifact_factor, 0.8)
        * max(talisman_factor, 0.85)
        * max(duel_rate_factor, 0.7)
        * random_factor
    )
    return {
        "profile": profile,
        "quality": quality_name,
        "quality_payload": quality,
        "stats": stats,
        "artifact_effects": artifact_effects,
        "talisman_effects": talisman_effects or {},
        "sect_effects": sect_effects,
        "technique_effects": technique_effects or {},
        "title_effects": title_effects or {},
        "power": float(power),
    }


def serialize_full_profile(tg: int) -> dict[str, Any]:
    bundle = _legacy_serialize_full_profile(tg)
    profile = bundle.get("profile") or {}
    has_root = bool(str(profile.get("root_type") or "").strip() or str(profile.get("root_quality") or "").strip())
    if has_root:
        quality_name = _normalized_root_quality(profile)
        quality = _root_quality_payload(quality_name)
        profile["root_quality"] = quality_name
        profile["root_quality_level"] = profile.get("root_quality_level") or quality["level"]
        profile["root_quality_color"] = profile.get("root_quality_color") or quality["color"]
    else:
        profile["root_quality"] = None
        profile["root_quality_level"] = None
        profile["root_quality_color"] = None
    profile["root_text"] = format_root(profile)
    battle = _battle_bundle(bundle)
    bundle["effective_stats"] = {
        key: int(round(value)) if isinstance(value, (int, float)) else value
        for key, value in battle["stats"].items()
    }
    bundle["combat_power"] = int(round(battle["power"]))
    return bundle


def generate_root_payload() -> dict[str, Any]:
    quality_name = _roll_root_quality()
    quality = _root_quality_payload(quality_name)
    if quality_name == "天灵根":
        primary = random.choice(FIVE_ELEMENTS)
        return {
            "root_type": "天灵根",
            "root_primary": primary,
            "root_secondary": None,
            "root_relation": "天道垂青",
            "root_bonus": 12,
            "root_quality": quality_name,
            "root_quality_level": quality["level"],
            "root_quality_color": quality["color"],
        }
    if quality_name == "变异灵根":
        primary = random.choice(ROOT_VARIANT_ELEMENTS)
        return {
            "root_type": "变异灵根",
            "root_primary": primary,
            "root_secondary": None,
            "root_relation": "异灵独秀",
            "root_bonus": 10,
            "root_quality": quality_name,
            "root_quality_level": quality["level"],
            "root_quality_color": quality["color"],
        }
    if random.randint(1, 100) <= 10:
        primary, secondary = random.sample(FIVE_ELEMENTS, 2)
        relation, bonus = determine_relation(primary, secondary)
        return {
            "root_type": "双灵根",
            "root_primary": primary,
            "root_secondary": secondary,
            "root_relation": relation,
            "root_bonus": bonus,
            "root_quality": quality_name,
            "root_quality_level": quality["level"],
            "root_quality_color": quality["color"],
        }
    primary = random.choice(FIVE_ELEMENTS)
    return {
        "root_type": "单灵根",
        "root_primary": primary,
        "root_secondary": None,
        "root_relation": "平稳中正",
        "root_bonus": 0,
        "root_quality": quality_name,
        "root_quality_level": quality["level"],
        "root_quality_color": quality["color"],
    }


def _refined_root_payload(profile: dict[str, Any], steps: int) -> dict[str, Any] | None:
    quality_name = _normalized_root_quality(profile)
    if quality_name in ROOT_SPECIAL_QUALITIES:
        return None
    current_quality = quality_name if quality_name in ROOT_COMMON_QUALITY_ORDER else "中品灵根"
    current_index = ROOT_COMMON_QUALITY_ORDER.index(current_quality)
    target_index = min(current_index + max(int(steps or 0), 0), len(ROOT_COMMON_QUALITY_ORDER) - 1)
    if target_index <= current_index:
        return None
    target_quality = ROOT_COMMON_QUALITY_ORDER[target_index]
    quality = _root_quality_payload(target_quality)
    return {
        "root_type": profile.get("root_type"),
        "root_primary": profile.get("root_primary"),
        "root_secondary": profile.get("root_secondary"),
        "root_relation": profile.get("root_relation"),
        "root_bonus": int(profile.get("root_bonus") or 0),
        "root_quality": target_quality,
        "root_quality_level": int(quality["level"]),
        "root_quality_color": quality["color"],
    }


def _generate_root_payload_with_floor(floor_level: int) -> dict[str, Any]:
    minimum = max(min(int(floor_level or 0), ROOT_QUALITY_LEVELS["极品灵根"]), 0)
    best = generate_root_payload()
    best_level = int(best.get("root_quality_level") or 0)
    if minimum <= 0 or best_level >= minimum:
        return best
    for _ in range(31):
        candidate = generate_root_payload()
        candidate_level = int(candidate.get("root_quality_level") or 0)
        if candidate_level >= minimum:
            return candidate
        if candidate_level > best_level:
            best = candidate
            best_level = candidate_level
    return best


def _common_root_quality_name(level: int) -> str:
    clamped_level = max(1, min(int(level or 1), ROOT_QUALITY_LEVELS["极品灵根"]))
    return ROOT_COMMON_QUALITY_ORDER[clamped_level - 1]


def _current_common_root_level(profile: dict[str, Any]) -> int:
    current_quality = _normalized_root_quality(profile)
    if current_quality in ROOT_SPECIAL_QUALITIES:
        return ROOT_QUALITY_LEVELS["极品灵根"]
    return max(1, min(ROOT_QUALITY_LEVELS.get(current_quality, 1), ROOT_QUALITY_LEVELS["极品灵根"]))


def _build_single_root_payload(profile: dict[str, Any], floor_level: int) -> dict[str, Any]:
    quality_level = max(
        _current_common_root_level(profile),
        max(min(int(floor_level or 0), ROOT_QUALITY_LEVELS["极品灵根"]), 0),
        ROOT_QUALITY_LEVELS["中品灵根"],
    )
    quality_name = _common_root_quality_name(quality_level)
    quality = _root_quality_payload(quality_name)
    return {
        "root_type": "单灵根",
        "root_primary": random.choice(FIVE_ELEMENTS),
        "root_secondary": None,
        "root_relation": "平稳中正",
        "root_bonus": 0,
        "root_quality": quality_name,
        "root_quality_level": int(quality["level"]),
        "root_quality_color": quality["color"],
    }


def _build_double_root_payload(profile: dict[str, Any], floor_level: int) -> dict[str, Any]:
    primary, secondary = random.sample(FIVE_ELEMENTS, 2)
    relation, bonus = determine_relation(primary, secondary)
    baseline = ROOT_QUALITY_LEVELS["中品灵根"] if relation == "相克" else ROOT_QUALITY_LEVELS["上品灵根"]
    quality_level = max(
        _current_common_root_level(profile),
        max(min(int(floor_level or 0), ROOT_QUALITY_LEVELS["极品灵根"]), 0),
        baseline,
    )
    quality_name = _common_root_quality_name(quality_level)
    quality = _root_quality_payload(quality_name)
    return {
        "root_type": "双灵根",
        "root_primary": primary,
        "root_secondary": secondary,
        "root_relation": relation,
        "root_bonus": bonus,
        "root_quality": quality_name,
        "root_quality_level": int(quality["level"]),
        "root_quality_color": quality["color"],
    }


def _build_earth_root_payload() -> dict[str, Any]:
    quality = _root_quality_payload("极品灵根")
    return {
        "root_type": "地灵根",
        "root_primary": random.choice(FIVE_ELEMENTS),
        "root_secondary": None,
        "root_relation": "平稳中正",
        "root_bonus": ROOT_SPECIAL_BONUS["地灵根"],
        "root_quality": "极品灵根",
        "root_quality_level": int(quality["level"]),
        "root_quality_color": quality["color"],
    }


def _build_heaven_root_payload() -> dict[str, Any]:
    primary = random.choice(FIVE_ELEMENTS)
    quality = _root_quality_payload("天灵根")
    return {
        "root_type": "天灵根",
        "root_primary": primary,
        "root_secondary": None,
        "root_relation": "天道垂青",
        "root_bonus": 12,
        "root_quality": "天灵根",
        "root_quality_level": int(quality["level"]),
        "root_quality_color": quality["color"],
    }


def _build_variant_root_payload() -> dict[str, Any]:
    primary = random.choice(ROOT_VARIANT_ELEMENTS)
    quality = _root_quality_payload("变异灵根")
    return {
        "root_type": "变异灵根",
        "root_primary": primary,
        "root_secondary": None,
        "root_relation": "异灵独秀",
        "root_bonus": 10,
        "root_quality": "变异灵根",
        "root_quality_level": int(quality["level"]),
        "root_quality_color": quality["color"],
    }


def _transformed_root_payload(profile: dict[str, Any], pill_type: str, effect_value: float | int | None = None) -> dict[str, Any] | None:
    floor_level = max(int(round(float(effect_value or 0))), 0)
    if pill_type == "root_single":
        return _build_single_root_payload(profile, floor_level)
    if pill_type == "root_double":
        return _build_double_root_payload(profile, floor_level)
    if pill_type == "root_earth":
        return _build_earth_root_payload()
    if pill_type == "root_heaven":
        return _build_heaven_root_payload()
    if pill_type == "root_variant":
        return _build_variant_root_payload()
    return None


def format_root(payload: dict[str, Any]) -> str:
    root_type = str(payload.get("root_type") or "").strip()
    if not root_type:
        return "尚未踏入仙途"

    quality = _normalized_root_quality(payload)
    primary = str(payload.get("root_primary") or "")
    secondary = str(payload.get("root_secondary") or "")
    relation = str(payload.get("root_relation") or "")
    if root_type in {"天灵根", "变异灵根"}:
        return f"{quality} · {primary}"
    if root_type == "双灵根":
        return f"{quality} · {primary}/{secondary} · {relation}"
    return f"{quality} · {primary}"


def init_path_for_user(tg: int) -> dict[str, Any]:
    ensure_seed_data()
    profile = get_profile(tg, create=True)
    if profile and profile.consented:
        return serialize_full_profile(tg)

    root_payload = generate_root_payload()
    stats = _build_opening_stats(root_payload)
    updated = upsert_profile(
        tg,
        consented=True,
        root_type=root_payload["root_type"],
        root_primary=root_payload["root_primary"],
        root_secondary=root_payload["root_secondary"],
        root_relation=root_payload["root_relation"],
        root_bonus=root_payload["root_bonus"],
        root_quality=root_payload["root_quality"],
        root_quality_level=root_payload["root_quality_level"],
        root_quality_color=root_payload["root_quality_color"],
        realm_stage="炼气",
        realm_layer=1,
        cultivation=0,
        spiritual_stone=50,
        dan_poison=0,
        shop_name="",
        shop_broadcast=False,
        **stats,
    )
    return serialize_full_profile(updated.tg)


def practice_for_user(tg: int) -> dict[str, Any]:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("你还没有踏入仙途。")
    if _is_retreating(profile):
        raise ValueError("闭关期间无法吐纳修炼。")
    if is_same_china_day(profile.last_train_at, utcnow()):
        raise ValueError("今日已经完成过吐纳修炼了。")

    profile_data = serialize_profile(profile)
    artifact_effects = merge_artifact_effects(profile_data, collect_equipped_artifacts(tg))
    active_talisman = serialize_talisman(get_talisman(profile.active_talisman_id)) if profile.active_talisman_id else None
    talisman_effects = resolve_talisman_effects(profile_data, active_talisman) if active_talisman else None
    current_technique = _current_technique_payload(profile_data)
    technique_effects = resolve_technique_effects(profile_data, current_technique) if current_technique else None
    current_title = get_current_title(tg)
    title_effects = resolve_title_effects(profile_data, current_title) if current_title else None
    stats = _effective_stats(profile_data, artifact_effects, talisman_effects, get_sect_effects(profile_data), technique_effects, title_effects)
    quality = _root_quality_payload(_normalized_root_quality(profile_data))
    poison_penalty = max(float(profile.dan_poison or 0) - stats["bone"] * 0.45, 0.0) / 110
    base_gain = random.randint(18, 36)
    gain = int(round((base_gain + stats["bone"] * 0.55 + stats["comprehension"] * 0.75 + stats["cultivation_bonus"]) * quality["cultivation_rate"] * max(0.55, 1 - poison_penalty)))
    gain = max(gain, 5)
    stone_gain = random.randint(2, 8) + int(stats["fortune"] // 18)
    stage = normalize_realm_stage(profile.realm_stage or "炼气")
    layer, cultivation, upgraded_layers, remaining = apply_cultivation_gain(stage, int(profile.realm_layer or 1), int(profile.cultivation or 0), gain)
    updated = upsert_profile(
        tg,
        cultivation=cultivation,
        spiritual_stone=int(profile.spiritual_stone or 0) + stone_gain,
        realm_layer=layer,
        last_train_at=utcnow(),
    )
    _apply_profile_growth_floor(tg)
    return {
        "gain": gain,
        "stone_gain": stone_gain,
        "upgraded_layers": upgraded_layers,
        "remaining": remaining,
        "profile": serialize_full_profile(updated.tg),
    }


def breakthrough_for_user(tg: int, use_pill: bool = False) -> dict[str, Any]:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("你还没有踏入仙途。")
    if _is_retreating(profile):
        raise ValueError("闭关期间无法突破。")
    if int(profile.realm_layer or 0) < 9:
        raise ValueError("只有达到当前大境界九层后才能尝试突破。")

    stage = normalize_realm_stage(profile.realm_stage or "炼气")
    required_cultivation = cultivation_threshold(stage, 9)
    if int(profile.cultivation or 0) < required_cultivation:
        raise ValueError(f"当前修为尚未圆满，还差 {required_cultivation - int(profile.cultivation or 0)} 点修为。")
    next_stage = next_realm_stage(stage)
    if next_stage is None:
        raise ValueError("你已经走到当前修炼体系的尽头。")

    profile_data = serialize_profile(profile)
    artifact_effects = merge_artifact_effects(profile_data, collect_equipped_artifacts(tg))
    active_talisman = serialize_talisman(get_talisman(profile.active_talisman_id)) if profile.active_talisman_id else None
    talisman_effects = resolve_talisman_effects(profile_data, active_talisman) if active_talisman else None
    current_technique = _current_technique_payload(profile_data)
    technique_effects = resolve_technique_effects(profile_data, current_technique) if current_technique else None
    current_title = get_current_title(tg)
    title_effects = resolve_title_effects(profile_data, current_title) if current_title else None
    stats = _effective_stats(profile_data, artifact_effects, talisman_effects, get_sect_effects(profile_data), technique_effects, title_effects)
    quality = _root_quality_payload(_normalized_root_quality(profile_data))
    success_rate = BREAKTHROUGH_BASE_RATE.get(stage, 12)
    success_rate += int(round((stats["bone"] - 12) * 0.45))
    success_rate += int(round((stats["comprehension"] - 12) * 0.6))
    success_rate += int(quality["breakthrough_bonus"])
    success_rate += int(round((artifact_effects or {}).get("breakthrough_bonus", 0)))
    success_rate += int(round((technique_effects or {}).get("breakthrough_bonus", 0)))
    success_rate += int(round((title_effects or {}).get("breakthrough_bonus", 0)))
    success_rate += int(round((stats["willpower"] - 10) * 0.35))
    success_rate += int(round((stats["karma"] - 10) * 0.2))
    success_rate -= int(max(float(profile.dan_poison or 0) - stats["bone"] * 0.3, 0) // 8)
    if _normalized_root_quality(profile_data) == "天灵根":
        success_rate += 4

    pill_bonus = 0
    used_pill_name = None
    if stage == "炼气" and use_pill:
        pill_row = _find_pill_in_inventory(tg, "foundation")
        if pill_row is None:
            raise ValueError("你没有可用的筑基丹。")
        used_pill_name = pill_row["pill"]["name"]
        pill_effects = resolve_pill_effects(profile_data, pill_row["pill"], {"pill_uses": int(profile.breakthrough_pill_uses or 0), "base_success_rate": success_rate})
        base_bonus = max(50 - int(profile.breakthrough_pill_uses or 0) * 5, 30)
        pill_bonus = max(int(round(pill_effects.get("success_rate_bonus", 0))), base_bonus)
        success_rate += pill_bonus

    success_rate = max(min(success_rate, 95), 1)
    success_roll = roll_probability_percent(
        success_rate,
        actor_fortune=stats["fortune"],
        actor_weight=0.45,
        minimum=1,
        maximum=95,
    )
    success_rate = success_roll["chance"]
    roll = success_roll["roll"]
    success = bool(success_roll["success"])
    if use_pill and used_pill_name:
        pill_row = _find_pill_in_inventory(tg, "foundation")
        if pill_row is None or not consume_user_pill(tg, pill_row["pill"]["id"], 1):
            raise ValueError("筑基丹消耗失败，请稍后再试。")

    if success:
        updated = upsert_profile(
            tg,
            realm_stage=next_stage,
            realm_layer=1,
            cultivation=0,
            breakthrough_pill_uses=int(profile.breakthrough_pill_uses or 0) + (1 if use_pill else 0),
            qi_blood=int(profile.qi_blood or 0) + 25 + int(stats["bone"] // 2),
            true_yuan=int(profile.true_yuan or 0) + 20 + int(stats["comprehension"] // 2),
            attack_power=int(profile.attack_power or 0) + 3,
            defense_power=int(profile.defense_power or 0) + 3,
            willpower=int(profile.willpower or 0) + 1,
            karma=int(profile.karma or 0) + (1 if success_rate >= 60 else 0),
        )
        _apply_profile_growth_floor(tg)
    else:
        updated = upsert_profile(
            tg,
            cultivation=max(int(profile.cultivation or 0) - required_cultivation // 2, 0),
            breakthrough_pill_uses=int(profile.breakthrough_pill_uses or 0) + (1 if use_pill else 0),
            willpower=int(profile.willpower or 0) + 1,
        )
    return {
        "success": success,
        "roll": roll,
        "success_rate": success_rate,
        "pill_bonus": pill_bonus,
        "used_pill": used_pill_name,
        "profile": serialize_full_profile(updated.tg),
    }


def consume_pill_for_user(tg: int, pill_id: int) -> dict[str, Any]:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("你还没有踏入仙途。")
    if _is_retreating(profile):
        raise ValueError("闭关期间无法服用丹药。")
    pill = get_pill(pill_id)
    if pill is None or not pill.enabled:
        raise ValueError("未找到可用的丹药。")
    profile_data = serialize_profile(profile)
    pill_data = serialize_pill(pill)
    usage_reason = _pill_usage_reason(profile_data, pill_data)
    if usage_reason:
        raise ValueError(usage_reason)
    if not consume_user_pill(tg, pill_id, 1):
        raise ValueError("你的背包里没有这枚丹药。")

    effects = resolve_pill_effects(profile_data, pill_data)
    bone_resistance = min((float(profile.bone or 0) / 200), 0.45)
    dan_poison = min(int(profile.dan_poison or 0) + int(round(float(effects.get("poison_delta", 0) or 0) * (1 - bone_resistance))), 100)
    cultivation = int(profile.cultivation or 0)
    spiritual_stone = int(profile.spiritual_stone or 0)
    bone = int(profile.bone or 0) + int(round(effects.get("bone_bonus", 0)))
    comprehension = int(profile.comprehension or 0) + int(round(effects.get("comprehension_bonus", 0)))
    divine_sense = int(profile.divine_sense or 0) + int(round(effects.get("divine_sense_bonus", 0)))
    fortune = int(profile.fortune or 0) + int(round(effects.get("fortune_bonus", 0)))
    willpower = int(profile.willpower or 0) + int(round(effects.get("willpower_bonus", 0)))
    charisma = int(profile.charisma or 0) + int(round(effects.get("charisma_bonus", 0)))
    karma = int(profile.karma or 0) + int(round(effects.get("karma_bonus", 0)))
    qi_blood = int(profile.qi_blood or 0) + int(round(effects.get("qi_blood_bonus", 0)))
    true_yuan = int(profile.true_yuan or 0) + int(round(effects.get("true_yuan_bonus", 0)))
    body_movement = int(profile.body_movement or 0) + int(round(effects.get("body_movement_bonus", 0)))
    attack_power = int(profile.attack_power or 0) + int(round(effects.get("attack_bonus", 0)))
    defense_power = int(profile.defense_power or 0) + int(round(effects.get("defense_bonus", 0)))
    root_patch: dict[str, Any] | None = None

    if pill.pill_type == "clear_poison":
        dan_poison = max(dan_poison - int(round(effects.get("clear_poison", effects.get("effect_value", 50)))), 0)
    elif pill.pill_type == "cultivation":
        cultivation += int(round(effects.get("cultivation_gain", effects.get("effect_value", 0))))
    elif pill.pill_type == "stone":
        spiritual_stone += int(round(effects.get("stone_gain", effects.get("effect_value", 0))))
    elif pill.pill_type == "root_refine":
        steps = max(int(round(float(effects.get("root_quality_gain", 0) or 0))), 0)
        root_patch = _refined_root_payload(profile_data, steps)
    elif pill.pill_type == "root_remold":
        floor_level = max(int(round(float(effects.get("root_quality_floor", 0) or 0))), 0)
        root_patch = _generate_root_payload_with_floor(floor_level)
    elif pill.pill_type in ROOT_TRANSFORM_PILL_TYPES:
        root_patch = _transformed_root_payload(profile_data, pill.pill_type, effects.get("effect_value", pill_data.get("effect_value", 0)))

    layer, cultivation, _, _ = apply_cultivation_gain(normalize_realm_stage(profile.realm_stage or "炼气"), int(profile.realm_layer or 1), cultivation, 0)
    updated = upsert_profile(
        tg,
        dan_poison=dan_poison,
        cultivation=cultivation,
        spiritual_stone=spiritual_stone,
        bone=bone,
        comprehension=comprehension,
        divine_sense=divine_sense,
        fortune=fortune,
        willpower=willpower,
        charisma=charisma,
        karma=karma,
        qi_blood=qi_blood,
        true_yuan=true_yuan,
        body_movement=body_movement,
        attack_power=attack_power,
        defense_power=defense_power,
        realm_layer=layer,
        **(root_patch or {}),
    )
    bundle = serialize_full_profile(updated.tg)
    return {
        "pill": {**pill_data, "resolved_effects": effects},
        "profile": bundle,
        "summary": _pill_effect_summary(profile_data, bundle["profile"]),
    }


def _duel_display_name(profile: dict[str, Any]) -> str:
    return _profile_name_with_title(profile)


def _duel_item_names(items: list[dict[str, Any]] | None, fallback: str) -> str:
    rows = [str(item.get("name") or "").strip() for item in (items or []) if str(item.get("name") or "").strip()]
    return "、".join(rows[:3]) if rows else fallback


def _duel_source_token(source_type: str, payload: dict[str, Any]) -> str:
    source_id = int(payload.get("id") or 0)
    source_name = str(payload.get("name") or source_type).strip()
    return f"{source_type}:{source_id}:{source_name}"


def _build_duel_source_uses(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    talisman = bundle.get("active_talisman") or {}
    if not talisman:
        return {}
    limit = max(int(talisman.get("effect_uses") or 1), 1)
    token = _duel_source_token("符箓", talisman)
    return {
        token: {
            "source_type": "符箓",
            "source_name": str(talisman.get("name") or "符箓"),
            "limit": limit,
            "remaining": limit,
        }
    }


def _duel_combat_entries(bundle: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    rows = {"skills": [], "passives": [], "openings": []}
    sources: list[tuple[str, dict[str, Any]]] = []
    if bundle.get("current_technique"):
        sources.append(("功法", bundle["current_technique"]))
    if bundle.get("active_talisman"):
        sources.append(("符箓", bundle["active_talisman"]))
    for artifact in bundle.get("equipped_artifacts") or []:
        sources.append(("法宝", artifact))
    for source_type, payload in sources:
        config = payload.get("combat_config") or {}
        if not isinstance(config, dict):
            continue
        source_token = _duel_source_token(source_type, payload)
        opening_text = str(config.get("opening_text") or "").strip()
        if opening_text:
            rows["openings"].append(f"{payload.get('name') or source_type}：{opening_text}")
        for key in ("skills", "passives"):
            for item in config.get(key) or []:
                if not isinstance(item, dict) or not str(item.get("kind") or "").strip():
                    continue
                rows[key].append(
                    {
                        **item,
                        "source_type": source_type,
                        "source_name": str(payload.get("name") or source_type),
                        "source_token": source_token,
                        "display_name": str(item.get("name") or item.get("kind") or source_type),
                    }
                )
    return rows


def _create_duel_actor(bundle: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    profile = bundle["profile"]
    stats = state["stats"]
    return {
        "tg": int(profile["tg"]),
        "name": _duel_display_name(profile),
        "profile": profile,
        "stats": stats,
        "power": float(state["power"]),
        "max_hp": max(int(round(stats["qi_blood"])), 1),
        "hp": max(int(round(stats["qi_blood"])), 1),
        "max_mp": max(int(round(stats["true_yuan"])), 1),
        "mp": max(int(round(stats["true_yuan"])), 1),
        "active_talisman": bundle.get("active_talisman") or None,
        "combat_entries": _duel_combat_entries(bundle),
        "source_uses": _build_duel_source_uses(bundle),
        "effects": {
            "burn": [],
            "bleed": [],
            "shield": [],
            "guard": [],
            "dodge": [],
            "armor_break": [],
        },
    }


def _append_duel_log(logs: list[dict[str, Any]], round_no: int, text: str, kind: str = "action") -> None:
    logs.append({"round": round_no, "kind": kind, "text": text})


def _active_effect_value(actor: dict[str, Any], effect_kind: str, value_key: str) -> float:
    total = 0.0
    for item in actor["effects"].get(effect_kind, []):
        total += float(item.get(value_key) or 0)
    return total


def _duel_entry_remaining_uses(actor: dict[str, Any], entry: dict[str, Any]) -> int | None:
    token = str(entry.get("source_token") or "").strip()
    if not token:
        return None
    usage = actor.get("source_uses", {}).get(token)
    if not usage:
        return None
    return max(int(usage.get("remaining") or 0), 0)


def _consume_duel_entry_use(
    actor: dict[str, Any],
    entry: dict[str, Any],
    round_no: int,
    logs: list[dict[str, Any]],
) -> bool:
    token = str(entry.get("source_token") or "").strip()
    if not token:
        return True
    usage = actor.get("source_uses", {}).get(token)
    if not usage:
        return True
    remaining = max(int(usage.get("remaining") or 0), 0)
    if remaining <= 0:
        return False
    usage["remaining"] = remaining - 1
    if usage["remaining"] <= 0:
        _append_duel_log(
            logs,
            round_no,
            f"{actor['name']} 所祭出的{usage.get('source_name') or '符箓'}灵意已尽，本场无法再继续显化。",
            "state",
        )
    return True


def _consume_shield(actor: dict[str, Any], damage: int) -> int:
    remaining = max(int(damage), 0)
    absorbed = 0
    updated = []
    for effect in actor["effects"]["shield"]:
        pool = max(int(effect.get("pool") or 0), 0)
        if remaining > 0 and pool > 0:
            current_absorb = min(pool, remaining)
            pool -= current_absorb
            remaining -= current_absorb
            absorbed += current_absorb
        if pool > 0:
            effect["pool"] = pool
            updated.append(effect)
    actor["effects"]["shield"] = updated
    return absorbed


def _tick_duel_dot(actor: dict[str, Any], effect_kind: str, round_no: int, logs: list[dict[str, Any]]) -> None:
    survivors = []
    for effect in actor["effects"].get(effect_kind, []):
        damage = max(int(effect.get("damage") or 0), 1)
        actor["hp"] = max(actor["hp"] - damage, 0)
        if effect_kind == "burn":
            _append_duel_log(logs, round_no, f"{actor['name']} 被{effect.get('name') or '灼烧'}反复炙烤，气血 -{damage}。", "dot")
        else:
            _append_duel_log(logs, round_no, f"{actor['name']} 伤口被{effect.get('name') or '流血'}牵动，气血 -{damage}。", "dot")
        effect["remaining"] = max(int(effect.get("remaining") or 1) - 1, 0)
        if effect["remaining"] > 0:
            survivors.append(effect)
    actor["effects"][effect_kind] = survivors


def _decay_duel_effects(actor: dict[str, Any]) -> None:
    for effect_kind in ("guard", "dodge", "armor_break", "shield"):
        next_rows = []
        for effect in actor["effects"].get(effect_kind, []):
            effect["remaining"] = max(int(effect.get("remaining") or 1) - 1, 0)
            if effect_kind == "shield":
                if effect["remaining"] > 0 and int(effect.get("pool") or 0) > 0:
                    next_rows.append(effect)
            elif effect["remaining"] > 0:
                next_rows.append(effect)
        actor["effects"][effect_kind] = next_rows


def _apply_duel_effect(
    source: dict[str, Any],
    target: dict[str, Any],
    effect: dict[str, Any],
    round_no: int,
    logs: list[dict[str, Any]],
) -> None:
    kind = str(effect.get("kind") or "").strip()
    name = effect.get("display_name") or effect.get("name") or kind
    duration = max(int(effect.get("duration") or 1), 1)
    flat_damage = max(int(effect.get("flat_damage") or 0), 0)
    flat_heal = max(int(effect.get("flat_heal") or 0), 0)
    ratio_percent = int(effect.get("ratio_percent") or 0)
    text = str(effect.get("text") or "").strip()
    if kind == "burn":
        damage = max(flat_damage + int(source["stats"]["attack_power"] * max(ratio_percent, 0) / 100), 6)
        target["effects"]["burn"].append({"name": name, "damage": damage, "remaining": duration})
        _append_duel_log(logs, round_no, text or f"{source['name']} 让 {target['name']} 身上残留离火，后续将持续受创。")
    elif kind == "bleed":
        damage = max(flat_damage + int(source["stats"]["attack_power"] * max(ratio_percent, 0) / 100), 5)
        target["effects"]["bleed"].append({"name": name, "damage": damage, "remaining": duration})
        _append_duel_log(logs, round_no, text or f"{target['name']} 被撕开伤口，气血开始一点点外泄。")
    elif kind == "shield":
        pool = max(flat_damage + flat_heal + max(int(effect.get("flat_shield") or 0), 0) + int(source["stats"]["defense_power"] * max(ratio_percent, 0) / 100), 1)
        source["effects"]["shield"].append({"name": name, "pool": pool, "remaining": duration})
        _append_duel_log(logs, round_no, text or f"{source['name']} 身前升起一层护体灵罩，可抵消 {pool} 点伤害。")
    elif kind == "guard":
        ratio = max(float(effect.get("defense_ratio_percent") or ratio_percent or 0) / 100.0, 0.0)
        source["effects"]["guard"].append({"name": name, "ratio": ratio, "remaining": duration})
        _append_duel_log(logs, round_no, text or f"{source['name']} 沉气护体，接下来承伤将被削弱。")
    elif kind == "dodge":
        bonus = max(int(effect.get("dodge_bonus") or 0), 0)
        source["effects"]["dodge"].append({"name": name, "bonus": bonus, "remaining": duration})
        _append_duel_log(logs, round_no, text or f"{source['name']} 身法一提，短时间内更难被锁定。")
    elif kind == "armor_break":
        ratio = max(float(effect.get("defense_ratio_percent") or ratio_percent or 0) / 100.0, 0.0)
        target["effects"]["armor_break"].append({"name": name, "ratio": ratio, "remaining": duration})
        _append_duel_log(logs, round_no, text or f"{target['name']} 的护体灵气被撕开一角，防御出现破绽。")
    elif kind == "heal":
        heal_value = max(flat_heal + int(source["stats"]["true_yuan"] * max(ratio_percent, 0) / 100), 1)
        source["hp"] = min(source["max_hp"], source["hp"] + heal_value)
        _append_duel_log(logs, round_no, text or f"{source['name']} 调匀气息，气血回升 {heal_value}。")


def _choose_duel_skill(actor: dict[str, Any], round_no: int, logs: list[dict[str, Any]]) -> dict[str, Any] | None:
    skills = list(actor["combat_entries"].get("skills") or [])
    random.shuffle(skills)
    for skill in skills:
        cost_true_yuan = max(int(skill.get("cost_true_yuan") or 0), 0)
        if actor["mp"] < cost_true_yuan:
            continue
        remaining_uses = _duel_entry_remaining_uses(actor, skill)
        if remaining_uses is not None and remaining_uses <= 0:
            continue
        chance = max(min(int(skill.get("chance") or 0), 100), 0)
        if chance <= 0:
            continue
        if not roll_probability_percent(chance)["success"]:
            continue
        if not _consume_duel_entry_use(actor, skill, round_no, logs):
            continue
        actor["mp"] = max(actor["mp"] - cost_true_yuan, 0)
        return skill
    return None


def _execute_duel_turn(
    attacker: dict[str, Any],
    defender: dict[str, Any],
    round_no: int,
    logs: list[dict[str, Any]],
) -> None:
    if attacker["hp"] <= 0 or defender["hp"] <= 0:
        return
    skill = _choose_duel_skill(attacker, round_no, logs)
    move_name = skill.get("display_name") if skill else "寻常一击"
    hit_bonus = int(skill.get("hit_bonus") or 0) if skill else 0
    dodge_bonus = _active_effect_value(defender, "dodge", "bonus")
    dodge_chance = max(min(int(8 + (defender["stats"]["body_movement"] - attacker["stats"]["body_movement"]) * 0.45 + dodge_bonus - hit_bonus), 40), 5)
    if roll_probability_percent(dodge_chance)["success"]:
        _append_duel_log(
            logs,
            round_no,
            f"{attacker['name']} 施展 {move_name}，却被 {defender['name']} 凭身法错开，攻势落空。",
            "dodge",
        )
        return

    defense_break_ratio = min(_active_effect_value(defender, "armor_break", "ratio"), 0.45)
    effective_defense = max(defender["stats"]["defense_power"] * (1 - defense_break_ratio), 1)
    base_damage = attacker["stats"]["attack_power"] * random.uniform(0.88, 1.18)
    if skill:
        base_damage += attacker["stats"]["attack_power"] * max(int(skill.get("ratio_percent") or 0), 0) / 100
        base_damage += max(int(skill.get("flat_damage") or 0), 0)
    else:
        base_damage += attacker["stats"]["attack_power"] * 0.18
    crit_chance = max(min(int(9 + (attacker["stats"]["divine_sense"] - defender["stats"]["divine_sense"]) * 0.35 + attacker["stats"]["fortune"] * 0.18), 32), 6)
    critical = roll_probability_percent(crit_chance)["success"]
    if critical:
        base_damage *= 1.45
    damage = max(int(round(base_damage - effective_defense * 0.38)), 1)
    guard_ratio = min(_active_effect_value(defender, "guard", "ratio"), 0.6)
    damage = max(int(round(damage * (1 - guard_ratio))), 1)
    absorbed = _consume_shield(defender, damage)
    damage_after_shield = max(damage - absorbed, 0)
    defender["hp"] = max(defender["hp"] - damage_after_shield, 0)
    crit_text = " 会心一击。" if critical else ""
    shield_text = f" 其中 {absorbed} 点被护盾挡下。" if absorbed else ""
    skill_text = ""
    if skill and skill.get("text"):
        skill_text = f"{skill.get('text')} "
    _append_duel_log(
        logs,
        round_no,
        f"{skill_text}{attacker['name']} 以 {move_name} 命中 {defender['name']}，造成 {damage_after_shield} 点伤害。{shield_text}{crit_text}".strip(),
    )
    if skill:
        _apply_duel_effect(attacker, defender, skill, round_no, logs)
    for passive in attacker["combat_entries"].get("passives") or []:
        remaining_uses = _duel_entry_remaining_uses(attacker, passive)
        if remaining_uses is not None and remaining_uses <= 0:
            continue
        chance = max(min(int(passive.get("chance") or 0), 100), 0)
        if chance <= 0 or not roll_probability_percent(chance)["success"]:
            continue
        if not _consume_duel_entry_use(attacker, passive, round_no, logs):
            continue
        _apply_duel_effect(attacker, defender, passive, round_no, logs)
    if damage_after_shield <= 0 and absorbed > 0:
        _append_duel_log(logs, round_no, f"{defender['name']} 的护体灵光完全吃下了这波冲击。", "shield")


def _simulate_duel_battle(
    challenger_bundle: dict[str, Any],
    defender_bundle: dict[str, Any],
    challenger_state: dict[str, Any],
    defender_state: dict[str, Any],
) -> dict[str, Any]:
    challenger_actor = _create_duel_actor(challenger_bundle, challenger_state)
    defender_actor = _create_duel_actor(defender_bundle, defender_state)
    logs: list[dict[str, Any]] = []
    for actor in (challenger_actor, defender_actor):
        talisman = actor.get("active_talisman") or {}
        if talisman:
            effect_uses = max(int(talisman.get("effect_uses") or 1), 1)
            _append_duel_log(
                logs,
                0,
                f"{actor['name']} 先行祭起符箓【{talisman.get('name') or '无名符箓'}】，本场最多显化 {effect_uses} 次。",
                "opening",
            )
    for opening in challenger_actor["combat_entries"]["openings"]:
        _append_duel_log(logs, 0, f"{challenger_actor['name']} 起手运转，{opening}", "opening")
    for opening in defender_actor["combat_entries"]["openings"]:
        _append_duel_log(logs, 0, f"{defender_actor['name']} 也不示弱，{opening}", "opening")

    max_rounds = 8
    round_count = 0
    for round_no in range(1, max_rounds + 1):
        round_count = round_no
        _append_duel_log(logs, round_no, f"第 {round_no} 回合，双方气机再度碰撞。", "round")
        for actor in (challenger_actor, defender_actor):
            _tick_duel_dot(actor, "burn", round_no, logs)
            _tick_duel_dot(actor, "bleed", round_no, logs)
        if challenger_actor["hp"] <= 0 or defender_actor["hp"] <= 0:
            break
        challenger_speed = challenger_actor["stats"]["body_movement"] + random.uniform(0, 12)
        defender_speed = defender_actor["stats"]["body_movement"] + random.uniform(0, 12)
        order = (
            [(challenger_actor, defender_actor), (defender_actor, challenger_actor)]
            if challenger_speed >= defender_speed
            else [(defender_actor, challenger_actor), (challenger_actor, defender_actor)]
        )
        for attacker, defender in order:
            _execute_duel_turn(attacker, defender, round_no, logs)
            if defender["hp"] <= 0:
                _append_duel_log(logs, round_no, f"{defender['name']} 气机溃散，已难再战。", "finish")
                break
        _decay_duel_effects(challenger_actor)
        _decay_duel_effects(defender_actor)
        if challenger_actor["hp"] <= 0 or defender_actor["hp"] <= 0:
            break

    if challenger_actor["hp"] == defender_actor["hp"]:
        challenger_score = challenger_actor["hp"] / challenger_actor["max_hp"] * 100 + challenger_actor["power"] / 30
        defender_score = defender_actor["hp"] / defender_actor["max_hp"] * 100 + defender_actor["power"] / 30
        challenger_win = challenger_score >= defender_score
    else:
        challenger_win = challenger_actor["hp"] > defender_actor["hp"]
    winner = challenger_actor if challenger_win else defender_actor
    loser = defender_actor if challenger_win else challenger_actor
    summary = (
        f"{winner['name']} 以剩余气血 {winner['hp']}/{winner['max_hp']} "
        f"压过 {loser['name']} 的 {loser['hp']}/{loser['max_hp']}，斗法告一段落。"
    )
    return {
        "challenger_actor": challenger_actor,
        "defender_actor": defender_actor,
        "winner_tg": winner["tg"],
        "loser_tg": loser["tg"],
        "summary": summary,
        "round_count": round_count,
        "battle_log": logs,
    }


def _build_duel_snapshot(
    bundle: dict[str, Any],
    state: dict[str, Any],
    opponent_profile: dict[str, Any],
    win_rate: float,
) -> dict[str, Any]:
    profile = bundle["profile"]
    technique = bundle.get("current_technique") or {}
    talisman = bundle.get("active_talisman") or {}
    root_modifier = _root_element_duel_modifier(profile, opponent_profile)
    variant_bonus = 0.03 if profile.get("root_type") == "变异灵根" else 0.0
    stats = {
        key: int(round(value))
        for key, value in state["stats"].items()
        if key in {
            "bone",
            "comprehension",
            "divine_sense",
            "fortune",
            "qi_blood",
            "true_yuan",
            "body_movement",
            "attack_power",
            "defense_power",
            "duel_rate_bonus",
        }
    }
    return {
        "name": _duel_display_name(profile),
        "realm_text": f"{profile['realm_stage']}{profile['realm_layer']}层",
        "power": round(state["power"], 2),
        "win_rate": round(win_rate * 100, 1),
        "root_text": format_root(profile),
        "root_quality": state["quality"],
        "root_modifier_percent": round(root_modifier * 100, 1),
        "root_factor": round(float(state["quality_payload"]["combat_factor"]) + root_modifier + variant_bonus, 3),
        "technique_name": technique.get("name") or "未修功法",
        "artifact_names": _duel_item_names(bundle.get("equipped_artifacts"), "未装备法宝"),
        "talisman_name": talisman.get("name") or "未备符箓",
        "stats": stats,
    }


def _format_duel_side_block(snapshot: dict[str, Any], label: str) -> list[str]:
    stats = snapshot["stats"]
    return [
        f"{label}：{snapshot['name']}",
        f"境界：{snapshot['realm_text']} ｜ 战力：{snapshot['power']:.1f} ｜ 预测胜率：{snapshot['win_rate']:.1f}%",
        f"灵根：{snapshot['root_text']} ｜ 五行修正 {snapshot['root_modifier_percent']:+.1f}% ｜ 灵根战斗系数 {snapshot['root_factor']:.3f}",
        f"功法：{snapshot['technique_name']}",
        f"法宝：{snapshot['artifact_names']} ｜ 符箓：{snapshot['talisman_name']}",
        (
            "核心数值："
            f"攻 {stats['attack_power']} 防 {stats['defense_power']} "
            f"气血 {stats['qi_blood']} 真元 {stats['true_yuan']} "
            f"身法 {stats['body_movement']} 斗法 {stats['duel_rate_bonus']:+d}%"
        ),
        (
            "资质数值："
            f"根骨 {stats['bone']} 悟性 {stats['comprehension']} "
            f"神识 {stats['divine_sense']} 机缘 {stats['fortune']}"
        ),
    ]


def format_duel_matchup_text(
    duel: dict[str, Any],
    stake: int = 0,
    title: str = "⚔️ **斗法邀请**",
    plunder_percent: int | None = None,
) -> str:
    settings = get_xiuxian_settings()
    if plunder_percent is None:
        plunder_percent = max(
            min(
                int(
                    settings.get(
                        "duel_winner_steal_percent",
                        DEFAULT_SETTINGS["duel_winner_steal_percent"],
                    )
                    or 0
                ),
                100,
            ),
            0,
        )
    artifact_plunder_chance = max(
        min(int(settings.get("artifact_plunder_chance", DEFAULT_SETTINGS["artifact_plunder_chance"]) or 0), 100),
        0,
    )
    lines = [
        title,
        *_format_duel_side_block(duel["challenger_snapshot"], "挑战者"),
        "",
        *_format_duel_side_block(duel["defender_snapshot"], "应战者"),
        "",
        f"综合预测：挑战者 {duel['challenger_rate'] * 100:.1f}% / 应战者 {duel['defender_rate'] * 100:.1f}%",
    ]
    if stake:
        lines.append(f"赌注：每人 {stake} 灵石")
    lines.append(f"胜者掠夺：败者当前灵石的 {plunder_percent}%")
    lines.append(f"法宝掠夺：基础 {artifact_plunder_chance}% 夺取 1 件未绑定法宝，受双方机缘影响")
    return "\n".join(lines)


def compute_duel_odds(challenger_tg: int, defender_tg: int) -> dict[str, Any]:
    challenger = serialize_full_profile(challenger_tg)
    defender = serialize_full_profile(defender_tg)
    challenger_profile = challenger["profile"]
    defender_profile = defender["profile"]
    if not challenger_profile["consented"] or not defender_profile["consented"]:
        raise ValueError("斗法双方都必须已经踏入仙途。")

    challenger_state = _battle_bundle(challenger, defender_profile)
    defender_state = _battle_bundle(defender, challenger_profile)
    total_power = max(challenger_state["power"] + defender_state["power"], 1)
    rate = challenger_state["power"] / total_power
    stage_diff = realm_index(challenger_profile["realm_stage"]) - realm_index(defender_profile["realm_stage"])
    if abs(stage_diff) >= 2:
        rate = adjust_probability_rate(
            rate,
            actor_fortune=challenger_state["stats"]["fortune"],
            opponent_fortune=defender_state["stats"]["fortune"],
            actor_weight=0.18,
            opponent_weight=0.18,
            minimum=0.001,
            maximum=0.999,
        )
    else:
        rate = adjust_probability_rate(
            rate,
            actor_fortune=challenger_state["stats"]["fortune"],
            opponent_fortune=defender_state["stats"]["fortune"],
            actor_weight=0.18,
            opponent_weight=0.18,
            minimum=0.03,
            maximum=0.97,
        )
    defender_rate = max(min(1 - rate, 0.999), 0.001)
    challenger_snapshot = _build_duel_snapshot(challenger, challenger_state, defender_profile, rate)
    defender_snapshot = _build_duel_snapshot(defender, defender_state, challenger_profile, defender_rate)
    return {
        "challenger": challenger,
        "defender": defender,
        "challenger_snapshot": challenger_snapshot,
        "defender_snapshot": defender_snapshot,
        "challenger_rate": round(rate, 4),
        "defender_rate": round(defender_rate, 4),
        "challenger_power": round(challenger_state["power"], 2),
        "defender_power": round(defender_state["power"], 2),
        "weights": {
            "stage_diff": stage_diff,
            "root_modifier": round(_root_element_duel_modifier(challenger_profile, defender_profile), 4),
            "challenger_quality": challenger_state["quality"],
            "defender_quality": defender_state["quality"],
            "challenger_attack": round(challenger_state["stats"]["attack_power"]),
            "challenger_defense": round(challenger_state["stats"]["defense_power"]),
            "challenger_qi_blood": round(challenger_state["stats"]["qi_blood"]),
            "challenger_true_yuan": round(challenger_state["stats"]["true_yuan"]),
            "challenger_body_movement": round(challenger_state["stats"]["body_movement"]),
            "defender_attack": round(defender_state["stats"]["attack_power"]),
            "defender_defense": round(defender_state["stats"]["defense_power"]),
            "defender_qi_blood": round(defender_state["stats"]["qi_blood"]),
            "defender_true_yuan": round(defender_state["stats"]["true_yuan"]),
            "defender_body_movement": round(defender_state["stats"]["body_movement"]),
        },
    }


def assert_duel_stake_affordable(
    challenger_profile: dict[str, Any],
    defender_profile: dict[str, Any],
    stake_amount: int,
) -> None:
    stake = max(int(stake_amount or 0), 0)
    if stake <= 0:
        return
    shortages = []
    for profile in (challenger_profile, defender_profile):
        current_stone = int(profile.get("spiritual_stone") or 0)
        if current_stone >= stake:
            continue
        shortages.append(f"{_duel_display_name(profile)} 当前仅有 {current_stone} 灵石")
    if shortages:
        raise ValueError(f"赌注 {stake} 灵石无法成立：" + "；".join(shortages) + "。")


def _clear_duel_active_talismans(*tgs: int) -> None:
    cleared: set[int] = set()
    for tg in tgs:
        if tg in cleared:
            continue
        set_active_talisman(int(tg), None)
        cleared.add(int(tg))


def resolve_duel(challenger_tg: int, defender_tg: int, stake: int = 0) -> dict[str, Any]:
    duel = compute_duel_odds(challenger_tg, defender_tg)
    challenger_profile = duel["challenger"]["profile"]
    defender_profile = duel["defender"]["profile"]
    stake_amount = max(int(stake), 0)
    settings = get_xiuxian_settings()
    plunder_percent = max(
        min(int(settings.get("duel_winner_steal_percent", DEFAULT_SETTINGS["duel_winner_steal_percent"]) or 0), 100),
        0,
    )
    artifact_plunder_base_chance = max(
        min(int(settings.get("artifact_plunder_chance", DEFAULT_SETTINGS["artifact_plunder_chance"]) or 0), 100),
        0,
    )
    assert_duel_stake_affordable(challenger_profile, defender_profile, stake_amount)

    challenger_state = _battle_bundle(duel["challenger"], defender_profile, apply_random=True)
    defender_state = _battle_bundle(duel["defender"], challenger_profile, apply_random=True)
    dynamic_rate = float(duel["challenger_rate"])
    simulated_battle = _simulate_duel_battle(duel["challenger"], duel["defender"], challenger_state, defender_state)
    winner_tg = int(simulated_battle["winner_tg"])
    loser_tg = int(simulated_battle["loser_tg"])
    challenger_win = winner_tg == challenger_tg
    winner_state = challenger_state if challenger_win else defender_state
    loser_state = defender_state if challenger_win else challenger_state
    challenger_profile_obj = get_profile(challenger_tg, create=False)
    defender_profile_obj = get_profile(defender_tg, create=False)
    winner_profile = get_profile(winner_tg, create=False)
    loser_profile = get_profile(loser_tg, create=False)
    if challenger_profile_obj is None or defender_profile_obj is None or winner_profile is None or loser_profile is None:
        raise ValueError("斗法双方的修仙资料缺失。")

    challenger_stone = int(challenger_profile_obj.spiritual_stone or 0)
    defender_stone = int(defender_profile_obj.spiritual_stone or 0)
    challenger_after_stake = max(challenger_stone - stake_amount, 0)
    defender_after_stake = max(defender_stone - stake_amount, 0)
    winner_after_stake = challenger_after_stake if winner_tg == challenger_tg else defender_after_stake
    loser_after_stake = defender_after_stake if winner_tg == challenger_tg else challenger_after_stake
    plunder_amount = loser_after_stake * plunder_percent // 100 if plunder_percent > 0 else 0

    upsert_profile(
        winner_tg,
        spiritual_stone=winner_after_stake + stake_amount * 2 + plunder_amount,
    )
    upsert_profile(
        loser_tg,
        spiritual_stone=max(loser_after_stake - plunder_amount, 0),
    )

    artifact_plunder_roll = roll_probability_percent(
        artifact_plunder_base_chance,
        actor_fortune=winner_state["stats"]["fortune"],
        opponent_fortune=loser_state["stats"]["fortune"],
        actor_weight=0.45,
        opponent_weight=0.35,
        minimum=0,
        maximum=95,
    )
    artifact_plunder = None
    if artifact_plunder_roll["success"]:
        artifact_plunder = plunder_random_artifact_to_user(winner_tg, loser_tg)
        if artifact_plunder and artifact_plunder.get("artifact"):
            artifact_name = artifact_plunder["artifact"].get("name", "未知法宝")
            create_journal(winner_tg, "duel", "斗法夺宝", f"斗法取胜后夺得法宝【{artifact_name}】")
            create_journal(loser_tg, "duel", "斗法失宝", f"斗法落败后被夺走法宝【{artifact_name}】")

    create_duel_record(
        challenger_tg=challenger_tg,
        defender_tg=defender_tg,
        winner_tg=winner_tg,
        loser_tg=loser_tg,
        challenger_rate=int(round(dynamic_rate * 1000)),
        defender_rate=int(round((1 - dynamic_rate) * 1000)),
        summary=str(simulated_battle["summary"]),
        battle_log=simulated_battle["battle_log"],
    )
    _clear_duel_active_talismans(challenger_tg, defender_tg)
    achievement_unlocks = record_duel_metrics(challenger_tg, defender_tg, winner_tg, loser_tg)
    return {
        "challenger": serialize_full_profile(challenger_tg),
        "defender": serialize_full_profile(defender_tg),
        "winner_tg": winner_tg,
        "loser_tg": loser_tg,
        "challenger_rate": dynamic_rate,
        "defender_rate": 1 - dynamic_rate,
        "roll": None,
        "winner_power": round(max(challenger_state["power"], defender_state["power"]), 2),
        "loser_power": round(min(challenger_state["power"], defender_state["power"]), 2),
        "stake": stake_amount,
        "pot": stake_amount * 2,
        "plunder_percent": plunder_percent,
        "plunder_amount": plunder_amount,
        "artifact_plunder": {
            **artifact_plunder_roll,
            "artifact": None if artifact_plunder is None else artifact_plunder.get("artifact"),
            "was_equipped": bool(artifact_plunder and artifact_plunder.get("was_equipped")),
        },
        "summary": str(simulated_battle["summary"]),
        "battle_log": simulated_battle["battle_log"],
        "round_count": int(simulated_battle["round_count"]),
        "achievement_unlocks": achievement_unlocks,
    }


def generate_shop_name(first_name: str) -> str:
    return PERSONAL_SHOP_NAME


def format_duel_settlement_text(
    result: dict[str, Any],
    bet_settlement: dict[str, Any] | None = None,
    page: int = 1,
    page_size: int = 10,
) -> str:
    challenger = result["challenger"]["profile"]
    defender = result["defender"]["profile"]
    winner_profile = challenger if int(result["winner_tg"]) == int(challenger["tg"]) else defender
    loser_profile = defender if int(result["loser_tg"]) == int(defender["tg"]) else challenger
    winner_name = _duel_display_name(winner_profile)
    loser_name = _duel_display_name(loser_profile)
    lines = [
        "⚖️ **斗法已结算**",
        f"胜者：{winner_name}",
        f"败者：{loser_name}",
        f"{result['summary']}",
    ]

    battle_log = list(result.get("battle_log") or [])
    if battle_log:
        lines.extend(
            [
                "",
                f"斗法过程：共 {int(result.get('round_count') or 0)} 回合，详细战报已实时播报完毕。",
            ]
        )

    stake = int(result.get("stake") or 0)
    if stake > 0:
        lines.extend(
            [
                "",
                "赌斗盈亏：",
                f"{winner_name} 赢得 {stake} 灵石",
                f"{loser_name} 输掉 {stake} 灵石",
            ]
        )

    plunder_percent = int(result.get("plunder_percent") or 0)
    if plunder_percent > 0:
        lines.extend(
            [
                "",
                "胜者掠夺：",
                f"{winner_name} 额外掠夺 {int(result.get('plunder_amount') or 0)} 灵石",
                f"掠夺比例：{plunder_percent}%",
            ]
        )

    artifact_plunder = result.get("artifact_plunder") or {}
    artifact_payload = artifact_plunder.get("artifact") or {}
    if artifact_payload:
        lines.extend(
            [
                "",
                "法宝掠夺：",
                f"{winner_name} 夺取了 {loser_name} 的 {artifact_payload.get('name', '未知法宝')}",
                f"触发概率：{artifact_plunder.get('chance', 0)}%",
            ]
        )

    rows = list((bet_settlement or {}).get("entries") or [])
    page_size = max(int(page_size or 10), 1)
    total_pages = max(ceil(len(rows) / page_size), 1)
    current_page = min(max(int(page or 1), 1), total_pages)
    start = (current_page - 1) * page_size
    page_rows = rows[start : start + page_size]
    side_label = {
        "challenger": "挑战者",
        "defender": "应战者",
    }
    lines.append("")
    lines.append("押注结算：")
    if not rows:
        lines.append("暂无道友参与押注。")
    else:
        header = "按净收益从高到低："
        if total_pages > 1:
            header += f" 第 {current_page}/{total_pages} 页"
        lines.append(header)
        for index, row in enumerate(page_rows, start=start + 1):
            if row.get("result") == "win":
                lines.append(
                    f"{index}. {row['name']} 押中{side_label.get(row.get('side'), '胜方')}，"
                    f"下注 {row['bet_amount']}，净赚 {row['net_profit']}，返还 {row['amount']} 灵石"
                )
            else:
                lines.append(
                    f"{index}. {row['name']} 押错{side_label.get(row.get('side'), '败方')}，"
                    f"下注 {row['bet_amount']}，净亏 {abs(int(row.get('net_profit') or 0))} 灵石"
                )

    lines.extend(
        [
            "",
            "祝词：",
            "愿胜者道心愈坚、再攀一层；愿败者锋芒不折、来日再战。",
            "也愿诸位观战押注的道友财运常在、仙途长青，机缘与紫气同来。",
        ]
    )
    return "\n".join(lines)


def generate_duel_preview_text(duel: dict[str, Any], stake: int = 0) -> str:
    return format_duel_matchup_text(duel, stake=stake)


from bot.plugins.xiuxian_game.features.pills import (  # noqa: E402
    consume_pill_for_user as consume_pill_for_user,
    pill_effect_summary as _pill_effect_summary,
    pill_usage_reason as _pill_usage_reason,
    resolve_pill_effects as resolve_pill_effects,
)
from bot.plugins.xiuxian_game.features.retreat import (  # noqa: E402
    ensure_not_in_retreat as ensure_not_in_retreat,
    finish_retreat_for_user as finish_retreat_for_user,
    is_retreating as _is_retreating,
    settle_retreat_progress as _settle_retreat_progress,
    start_retreat_for_user as start_retreat_for_user,
)
