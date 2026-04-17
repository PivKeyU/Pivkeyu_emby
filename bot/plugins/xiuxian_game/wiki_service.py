from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from bot.plugins.xiuxian_game.achievement_service import ACHIEVEMENT_METRIC_LABELS
from bot.plugins.xiuxian_game.features.content_catalog import FARMABLE_MATERIAL_RULES
from bot.plugins.xiuxian_game.features.fishing import (
    FISHING_SPOTS,
    _build_fishing_candidates,
    _build_item_lookups,
    _spot_candidates,
)
from bot.plugins.xiuxian_game.features.growth import ensure_seed_data
from bot.sql_helper.sql_xiuxian import (
    ITEM_KIND_LABELS,
    get_quality_meta,
    get_xiuxian_settings,
    list_artifacts,
    list_achievements,
    list_encounter_templates,
    list_materials,
    list_pills,
    list_recipe_ingredients,
    list_recipes,
    list_scene_drops,
    list_scenes,
    list_shop_items,
    list_talismans,
    list_tasks,
    list_techniques,
    list_titles,
)

GUIDE_PATH = Path(__file__).with_name("PLAYER_GUIDE.md")
GUIDE_FALLBACK = """# 修仙玩家玩法手册

## 一、先做什么

- 先入道、设性别，再看灵根、境界、背包与称号。
- 每次上线先做固定收益，再决定斗法、探索、交易还是炼制。

## 二、日常节奏

- 优先吐纳、打工、领取俸禄与收取探索、灵田、任务奖励。
- 想搜索具体玩法、材料、装备或配方获取方式，直接用页面里的 Wiki 搜索。
"""

SOURCE_PREFIXES = (
    ("探索·", "探索"),
    ("垂钓·", "垂钓"),
    ("灵田·", "灵田"),
    ("炼制·", "炼制"),
    ("奇遇·", "奇遇"),
    ("仙界奇石", "奇石"),
    ("官方任务·", "任务"),
    ("宗门任务·", "任务"),
    ("成就·", "成就"),
    ("师徒·", "师徒"),
    ("入道·", "入道"),
    ("官方商店", "商店"),
)

ENTRY_SOURCE_LABEL = "入道·初入仙途赠礼"
STARTER_ARTIFACT_NAME = "凡铁剑"
STARTER_TECHNIQUE_NAME = "长青诀"
STARTER_TITLE_NAME = "初入仙途"
MENTORSHIP_TITLE_SOURCES = {
    "传道授业": "师徒·带徒出师",
    "门下高徒": "师徒·完成出师",
}
BONUS_LABELS = (
    ("attack_bonus", "攻击"),
    ("defense_bonus", "防御"),
    ("bone_bonus", "根骨"),
    ("comprehension_bonus", "悟性"),
    ("divine_sense_bonus", "神识"),
    ("fortune_bonus", "机缘"),
    ("qi_blood_bonus", "气血"),
    ("true_yuan_bonus", "真元"),
    ("body_movement_bonus", "身法"),
    ("duel_rate_bonus", "斗法胜率"),
    ("cultivation_bonus", "修炼效率"),
    ("breakthrough_bonus", "突破加成"),
)
COMBAT_BONUS_FIELDS = (
    "attack_bonus",
    "defense_bonus",
    "qi_blood_bonus",
    "true_yuan_bonus",
    "body_movement_bonus",
    "duel_rate_bonus",
)
TUTORIAL_FILTER_RULES = (
    ("starter", ("开局", "新手前三天", "先做什么", "第一天", "第二天", "第三天", "每日上线", "常用指令", "首页 wiki", "修仙 wiki")),
    ("explore", ("探索", "秘境", "垂钓", "灵田", "奇遇")),
    ("crafting", ("炼制", "炼丹", "炼器", "制符", "残页", "配方", "丹修", "农修")),
    ("combat", ("战修", "斗法", "擂台", "抢劫", "偷窃", "炉鼎", "生死斗", "/duel", "/deathduel", "/leitai", "/rob")),
    ("task", ("任务", "悬赏", "委托", "/work")),
    ("social", ("师徒", "道侣", "红包", "赠礼", "双修", "问道", "传道", "出师", "/gift")),
    ("sect", ("宗门", "俸禄", "贡献", "入宗", "叛宗", "/salary")),
)
ACHIEVEMENT_ROUTE_HINTS = {
    "red_envelope_sent_count": "玩法链路：群内发红包 -> 累计发放次数 -> 领取成就奖励。",
    "red_envelope_sent_stone": "玩法链路：群内发红包 -> 累计发放灵石总量 -> 领取成就奖励。",
    "duel_initiated_count": "玩法链路：搜寻对手并发起斗法 -> 累计对战场次 -> 解锁成就奖励。",
    "duel_total_count": "玩法链路：持续参与斗法、擂台或生死斗 -> 累计场次 -> 解锁更高阶斗法成就。",
    "duel_win_count": "玩法链路：提升战力与法宝搭配 -> 赢下斗法 -> 解锁胜场成就。",
    "duel_loss_count": "玩法链路：参与高风险斗法也会累计败场 -> 达标后领取韧性类成就。",
    "rob_attempt_count": "玩法链路：发起抢劫或偷窃 -> 累计尝试次数 -> 解锁邪修路线成就。",
    "rob_success_count": "玩法链路：抢劫得手 -> 累计成功次数 -> 解锁夺宝成就。",
    "rob_fail_count": "玩法链路：抢劫失手也会累计 -> 达标后可拿到补偿型成就奖励。",
    "rob_stone_total": "玩法链路：靠抢劫获取灵石 -> 累计得手总额 -> 解锁高阶邪修成就。",
    "gift_sent_count": "玩法链路：赠礼给其他道友 -> 累计赠送次数 -> 解锁人情路线成就。",
    "gift_sent_stone": "玩法链路：赠送灵石或资助同道 -> 累计灵石总量 -> 解锁善缘成就。",
    "mentor_accept_count": "玩法链路：收徒成功 -> 建立师徒关系 -> 解锁传承成就。",
    "mentor_teach_count": "玩法链路：每日传道 -> 累计传道次数 -> 解锁师尊路线成就。",
    "disciple_consult_count": "玩法链路：每日向师尊问道 -> 累计问道次数 -> 解锁弟子路线成就。",
    "mentor_graduate_count": "玩法链路：培养弟子完成出师 -> 累计带徒出师次数 -> 解锁师门传承成就。",
    "disciple_graduate_count": "玩法链路：完成师徒出师流程 -> 累计出师次数 -> 解锁弟子成就与称号。",
    "craft_attempt_count": "玩法链路：获取配方与材料后开炉 -> 累计炼制尝试次数 -> 解锁炼制成就。",
    "craft_success_count": "玩法链路：稳定提高炼制成功次数 -> 解锁炼器炼丹路线成就。",
    "repair_success_count": "玩法链路：收集破损法宝与修复材料 -> 修复成功 -> 解锁修复成就。",
    "exploration_count": "玩法链路：持续秘境探索 -> 累计探索结算次数 -> 解锁秘境成就。",
    "exploration_danger_count": "玩法链路：在秘境中遭遇危险并活着归来 -> 累计险境次数 -> 解锁生还成就。",
    "exploration_recipe_drop_count": "玩法链路：秘境中刷残页或配方 -> 累计获得次数 -> 解锁残页成就。",
    "arena_open_count": "玩法链路：在群内开启擂台 -> 累计开台次数 -> 解锁擂主路线成就。",
    "arena_crowned_count": "玩法链路：登擂夺冠成为擂主 -> 累计夺冠次数 -> 解锁擂台成就。",
    "arena_defend_win_count": "玩法链路：守擂成功击退挑战者 -> 累计守擂次数 -> 解锁擂台防守成就。",
    "arena_final_win_count": "玩法链路：擂台结算时保持最终擂主 -> 累计终局夺魁次数 -> 解锁顶级擂主成就。",
}


def _unique_append(target: dict[Any, list[str]], key: Any, value: str) -> None:
    if not value:
        return
    rows = target[key]
    if value not in rows:
        rows.append(value)


def _clean_markdown_line(line: str) -> str:
    text = str(line or "").strip()
    if not text:
        return ""
    if text.startswith("- "):
        text = f"· {text[2:].strip()}"
    else:
        text = re.sub(r"^(\d+)\.\s+", "", text)
    return text.replace("`", "").strip()


def _extract_keywords(*values: str) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        raw = str(value or "")
        for token in re.findall(r"/[\w_]+|[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}", raw):
            normalized = token.strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            rows.append(token.strip())
    return rows


def _merge_filter_keys(*values: Any) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        items = value if isinstance(value, (list, tuple, set)) else [value]
        for item in items:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            rows.append(text)
    return rows


def _filters_from_source_labels(labels: list[str]) -> list[str]:
    filters: list[str] = []
    for label in labels:
        text = str(label or "").strip()
        if not text:
            continue
        if text.startswith(("探索·", "垂钓·", "灵田·", "奇遇·")):
            filters.append("explore")
        if text.startswith("炼制·"):
            filters.append("crafting")
        if text.startswith("官方任务·"):
            filters.append("task")
        if text.startswith("宗门任务·"):
            filters.extend(["task", "sect"])
        if text.startswith("师徒·"):
            filters.append("social")
        if text.startswith("入道·"):
            filters.append("starter")
    return _merge_filter_keys(filters)


def _filters_from_metric_key(metric_key: str) -> list[str]:
    key = str(metric_key or "").strip()
    if not key:
        return []
    if key.startswith(("duel_", "arena_", "rob_")):
        return ["combat"]
    if key.startswith(("craft_", "repair_")):
        return ["crafting"]
    if key.startswith("exploration_"):
        return ["explore"]
    if key.startswith(("mentor_", "disciple_", "gift_", "red_envelope_")):
        return ["social"]
    return []


def _filters_from_tutorial_text(title: str, subtitle: str, body_lines: list[str]) -> list[str]:
    haystack = " ".join([str(title or ""), str(subtitle or ""), *[str(line or "") for line in body_lines]]).lower()
    filters: list[str] = []
    for filter_key, keywords in TUTORIAL_FILTER_RULES:
        if any(str(keyword).lower() in haystack for keyword in keywords):
            filters.append(filter_key)
    return _merge_filter_keys(filters)


def _has_combat_bonus(payload: dict[str, Any]) -> bool:
    return any(int(payload.get(field) or 0) != 0 for field in COMBAT_BONUS_FIELDS)


def _read_guide_text() -> str:
    try:
        content = GUIDE_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        content = ""
    return content or GUIDE_FALLBACK


def _format_bonus_summary(payload: dict[str, Any], limit: int = 5) -> str:
    parts: list[str] = []
    for field, label in BONUS_LABELS:
        value = int(payload.get(field) or 0)
        if value == 0:
            continue
        prefix = "+" if value > 0 else ""
        parts.append(f"{label}{prefix}{value}")
    if not parts:
        return "暂无直接属性加成"
    visible = parts[:limit]
    suffix = f" 等 {len(parts)} 项" if len(parts) > limit else ""
    return "、".join(visible) + suffix


def _format_reward_summary(
    reward: dict[str, Any],
    item_catalog: dict[str, dict[int, dict[str, Any]]],
    title_catalog: dict[int, dict[str, Any]],
) -> str:
    parts: list[str] = []
    stone = int(reward.get("spiritual_stone") or 0)
    cultivation = int(reward.get("cultivation") or 0)
    if stone > 0:
        parts.append(f"{stone} 灵石")
    if cultivation > 0:
        parts.append(f"{cultivation} 修为")
    for title_id in reward.get("titles") or []:
        title = title_catalog.get(int(title_id or 0)) or {}
        title_name = str(title.get("name") or "").strip()
        if title_name:
            parts.append(f"称号【{title_name}】")
    for item in reward.get("items") or []:
        kind = str((item or {}).get("kind") or "").strip()
        ref_id = int((item or {}).get("ref_id") or 0)
        quantity = max(int((item or {}).get("quantity") or 0), 0)
        if not kind or ref_id <= 0 or quantity <= 0:
            continue
        payload = (item_catalog.get(kind) or {}).get(ref_id) or {}
        item_name = str(payload.get("name") or f"{ITEM_KIND_LABELS.get(kind, kind)}#{ref_id}").strip()
        parts.append(f"{item_name} x{quantity}")
    message = str(reward.get("message") or "").strip()
    if message:
        parts.append(message)
    return "、".join(parts) if parts else "无额外奖励"


def _parse_guide_sections() -> list[dict[str, Any]]:
    text = _read_guide_text()
    current_h2 = ""
    current_title = ""
    current_lines: list[str] = []
    sections: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal current_title, current_lines
        if not current_title:
            return
        body_lines = [_clean_markdown_line(line) for line in current_lines]
        body_lines = [line for line in body_lines if line]
        if not body_lines:
            return
        section_id = f"tutorial-{len(sections) + 1}"
        preview = body_lines[:3]
        title = current_title.strip()
        tags = []
        if current_h2:
            tags.append(current_h2)
        tags.extend(_extract_keywords(title, " ".join(preview))[:4])
        sections.append(
            {
                "id": section_id,
                "kind": "tutorial",
                "group": "tutorial",
                "filter_keys": _merge_filter_keys("tutorial", _filters_from_tutorial_text(title, current_h2, body_lines)),
                "kind_label": "玩法教程",
                "title": title,
                "subtitle": current_h2 if current_h2 and current_h2 != title else "玩家玩法手册",
                "description": preview[0],
                "body_lines": body_lines,
                "tags": tags[:5],
                "keywords": _extract_keywords(title, current_h2, " ".join(body_lines)),
            }
        )

    for raw_line in text.splitlines():
        line = str(raw_line or "").rstrip()
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            flush()
            current_h2 = line[3:].strip()
            current_title = current_h2
            current_lines = []
            continue
        if line.startswith("### "):
            flush()
            heading = line[4:].strip()
            current_title = f"{current_h2} · {heading}" if current_h2 else heading
            current_lines = []
            continue
        if current_title:
            current_lines.append(line)
    flush()
    return sections


def _join_labels(labels: list[str], limit: int = 4) -> str:
    rows = [str(label or "").strip() for label in labels if str(label or "").strip()]
    if not rows:
        return "暂未标注"
    visible = rows[:limit]
    suffix = f" 等 {len(rows)} 处" if len(rows) > limit else ""
    return "、".join(visible) + suffix


def _source_type_tags(labels: list[str]) -> list[str]:
    tags: list[str] = []
    for label in labels:
        for prefix, source_type in SOURCE_PREFIXES:
            if str(label or "").startswith(prefix) and source_type not in tags:
                tags.append(source_type)
    return tags


def _source_route_summary(labels: list[str]) -> str:
    routes = _source_type_tags(labels)
    return "、".join(routes) if routes else "多玩法联动"


def _resolve_item_ref_id(
    item_catalog: dict[str, dict[int, dict[str, Any]]],
    kind: str,
    ref_id: int,
    item_name: str,
) -> int:
    catalog = item_catalog.get(kind) or {}
    if ref_id > 0 and ref_id in catalog:
        return ref_id
    name = str(item_name or "").strip()
    if not name:
        return 0
    for candidate_id, item in catalog.items():
        if str(item.get("name") or "").strip() == name:
            return int(candidate_id)
    return 0


def _build_source_catalog(
    item_catalog: dict[str, dict[int, dict[str, Any]]],
    title_catalog: dict[int, dict[str, Any]],
) -> dict[tuple[str, int], list[str]]:
    source_map: dict[tuple[str, int], list[str]] = defaultdict(list)

    for scene in list_scenes(enabled_only=True):
        scene_name = str(scene.get("name") or "").strip()
        if not scene_name:
            continue
        for event in scene.get("event_pool") or []:
            kind = str((event or {}).get("bonus_reward_kind") or "").strip()
            ref_id = int((event or {}).get("bonus_reward_ref_id") or 0)
            if kind and ref_id > 0:
                _unique_append(source_map, (kind, ref_id), f"探索·{scene_name}")
        for drop in list_scene_drops(int(scene.get("id") or 0)):
            kind = str(drop.get("reward_kind") or "").strip()
            ref_id = int(drop.get("reward_ref_id") or 0)
            if kind and ref_id > 0:
                _unique_append(source_map, (kind, ref_id), f"探索·{scene_name}")

    for encounter in list_encounter_templates(enabled_only=True):
        kind = str(encounter.get("reward_item_kind") or "").strip()
        ref_id = int(encounter.get("reward_item_ref_id") or 0)
        name = str(encounter.get("name") or "").strip()
        if kind and ref_id > 0 and name:
            _unique_append(source_map, (kind, ref_id), f"奇遇·{name}")

    for shop_item in list_shop_items(official_only=True):
        kind = str(shop_item.get("item_kind") or "").strip()
        ref_id = int(shop_item.get("item_ref_id") or 0)
        if kind and ref_id > 0:
            shop_name = str(shop_item.get("shop_name") or "").strip()
            label = f"官方商店·{shop_name}" if shop_name else "官方商店"
            _unique_append(source_map, (kind, ref_id), label)

    fishing_candidates = _build_fishing_candidates(_build_item_lookups(), owned_recipe_ids=set())
    for spot in FISHING_SPOTS.values():
        spot_name = str(spot.get("name") or "").strip()
        if not spot_name:
            continue
        for row in _spot_candidates(spot, fishing_candidates):
            kind = str(row.get("kind") or "").strip()
            ref_id = int(row.get("ref_id") or 0)
            if kind and ref_id > 0:
                _unique_append(source_map, (kind, ref_id), f"垂钓·{spot_name}")

    for recipe in list_recipes(enabled_only=True):
        result_kind = str(recipe.get("result_kind") or "").strip()
        result_ref_id = int(recipe.get("result_ref_id") or 0)
        recipe_name = str(recipe.get("name") or "").strip()
        if result_kind == "material" and result_ref_id > 0 and recipe_name:
            _unique_append(source_map, ("material", result_ref_id), f"炼制·{recipe_name}")

    for reward in get_xiuxian_settings().get("gambling_reward_pool") or []:
        if not bool(reward.get("enabled", True)):
            continue
        kind = str(reward.get("item_kind") or "").strip()
        ref_id = _resolve_item_ref_id(
            item_catalog,
            kind,
            int(reward.get("item_ref_id") or 0),
            str(reward.get("item_name") or "").strip(),
        )
        if kind and ref_id > 0:
            _unique_append(source_map, (kind, ref_id), "仙界奇石")

    for task in list_tasks(enabled_only=True):
        if int(task.get("owner_tg") or 0) > 0:
            continue
        task_scope = str(task.get("task_scope") or "").strip()
        if task_scope not in {"official", "sect"}:
            continue
        kind = str(task.get("reward_item_kind") or "").strip()
        ref_id = int(task.get("reward_item_ref_id") or 0)
        if not kind or ref_id <= 0:
            continue
        title = str(task.get("title") or "").strip() or "未命名任务"
        prefix = "官方任务" if task_scope == "official" else "宗门任务"
        _unique_append(source_map, (kind, ref_id), f"{prefix}·{title}")

    for achievement in list_achievements(enabled_only=True):
        reward = achievement.get("reward_config") or {}
        label = f"成就·{str(achievement.get('name') or '').strip() or '未命名成就'}"
        for title_id in reward.get("titles") or []:
            normalized_title_id = int(title_id or 0)
            if normalized_title_id > 0 and normalized_title_id in title_catalog:
                _unique_append(source_map, ("title", normalized_title_id), label)
        for reward_item in reward.get("items") or []:
            kind = str((reward_item or {}).get("kind") or "").strip()
            ref_id = int((reward_item or {}).get("ref_id") or 0)
            if kind and ref_id > 0:
                _unique_append(source_map, (kind, ref_id), label)

    for material in list_materials(enabled_only=True):
        material_id = int(material.get("id") or 0)
        material_name = str(material.get("name") or "").strip()
        if material_id <= 0 or not material_name:
            continue
        rules = FARMABLE_MATERIAL_RULES.get(material_name) or {}
        can_plant = bool(material.get("can_plant")) or bool(rules.get("can_plant"))
        if not can_plant:
            continue
        stage = str(material.get("unlock_realm_stage") or rules.get("unlock_realm_stage") or "炼气").strip()
        layer = max(int(material.get("unlock_realm_layer") or rules.get("unlock_realm_layer") or 1), 1)
        price = max(int(material.get("seed_price_stone") or rules.get("seed_price_stone") or 0), 0)
        price_text = f"·种子 {price} 灵石" if price > 0 else ""
        _unique_append(source_map, ("material", material_id), f"灵田·{stage}{layer}层可种{price_text}")

    for item_id, item in item_catalog.get("artifact", {}).items():
        if str(item.get("name") or "").strip() == STARTER_ARTIFACT_NAME:
            _unique_append(source_map, ("artifact", item_id), ENTRY_SOURCE_LABEL)
            break

    for item_id, item in item_catalog.get("technique", {}).items():
        if str(item.get("name") or "").strip() == STARTER_TECHNIQUE_NAME:
            _unique_append(source_map, ("technique", item_id), ENTRY_SOURCE_LABEL)
            break

    for title_id, title in title_catalog.items():
        title_name = str(title.get("name") or "").strip()
        if title_name == STARTER_TITLE_NAME:
            _unique_append(source_map, ("title", title_id), ENTRY_SOURCE_LABEL)
        mentorship_source = MENTORSHIP_TITLE_SOURCES.get(title_name)
        if mentorship_source:
            _unique_append(source_map, ("title", title_id), mentorship_source)

    return source_map


def _build_item_catalog() -> dict[str, dict[int, dict[str, Any]]]:
    return {
        "material": {int(item["id"]): item for item in list_materials(enabled_only=True) if int(item.get("id") or 0) > 0},
        "artifact": {int(item["id"]): item for item in list_artifacts(enabled_only=True) if int(item.get("id") or 0) > 0},
        "pill": {int(item["id"]): item for item in list_pills(enabled_only=True) if int(item.get("id") or 0) > 0},
        "talisman": {int(item["id"]): item for item in list_talismans(enabled_only=True) if int(item.get("id") or 0) > 0},
        "technique": {int(item["id"]): item for item in list_techniques(enabled_only=True) if int(item.get("id") or 0) > 0},
    }


def _build_title_catalog() -> dict[int, dict[str, Any]]:
    return {
        int(item["id"]): item
        for item in list_titles(enabled_only=True)
        if int(item.get("id") or 0) > 0
    }


def _build_recipe_entries(
    source_map: dict[tuple[str, int], list[str]],
    material_use_map: dict[int, list[str]],
    crafted_by_map: dict[tuple[str, int], list[str]],
    item_catalog: dict[str, dict[int, dict[str, Any]]],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for recipe in list_recipes(enabled_only=True):
        recipe_id = int(recipe.get("id") or 0)
        if recipe_id <= 0:
            continue
        result_kind = str(recipe.get("result_kind") or "").strip()
        result_ref_id = int(recipe.get("result_ref_id") or 0)
        result_item = (item_catalog.get(result_kind) or {}).get(result_ref_id) or {}
        result_name = str(result_item.get("name") or recipe.get("name") or "").strip()
        quality = get_quality_meta(result_item.get("rarity") or result_item.get("quality_level") or 1)
        ingredient_lines: list[str] = []
        fragment_lines: list[str] = []
        ingredient_names: list[str] = []
        ingredient_source_labels: list[str] = []
        for ingredient in list_recipe_ingredients(recipe_id):
            material = ingredient.get("material") or {}
            material_id = int(material.get("id") or ingredient.get("material_id") or 0)
            material_name = str(material.get("name") or "").strip()
            quantity = max(int(ingredient.get("quantity") or 1), 1)
            ingredient_names.append(material_name)
            sources = source_map.get(("material", material_id), [])
            ingredient_source_labels.extend(sources)
            ingredient_lines.append(f"{material_name} x{quantity}（{_join_labels(sources, limit=3)}）")
            _unique_append(material_use_map, material_id, str(recipe.get("name") or "").strip())
            if "残页" in material_name:
                fragment_lines.append(f"{material_name} x{quantity}（{_join_labels(sources, limit=3)}）")
        recipe_sources = source_map.get(("recipe", recipe_id), [])
        body_lines = [
            f"产物：{ITEM_KIND_LABELS.get(result_kind, result_kind)}【{result_name}】",
            f"基础成功率：{max(int(recipe.get('base_success_rate') or 0), 0)}%",
        ]
        if recipe_sources:
            body_lines.append(f"配方获取：{_join_labels(recipe_sources)}")
        elif fragment_lines:
            body_lines.append(f"残页参悟：{'；'.join(fragment_lines[:3])}")
        if ingredient_lines:
            body_lines.append(f"炼制材料：{'；'.join(ingredient_lines[:4])}")
        route_labels = recipe_sources or ingredient_source_labels
        filter_keys = _merge_filter_keys(
            "recipe",
            "crafting",
            _filters_from_source_labels(recipe_sources),
            _filters_from_source_labels(ingredient_source_labels),
        )
        if fragment_lines:
            body_lines.append(f"玩法链路：先从{_source_route_summary(route_labels)}收集残页与主材，再到炼制页参悟并开炉。")
        else:
            body_lines.append(f"玩法链路：先拿到配方，再通过{_source_route_summary(route_labels)}补齐材料后炼制成品。")
        entries.append(
            {
                "id": f"recipe-{recipe_id}",
                "kind": "recipe",
                "group": "recipe",
                "filter_keys": filter_keys,
                "kind_label": "配方",
                "title": str(recipe.get("name") or "").strip(),
                "subtitle": f"{recipe.get('recipe_kind_label') or '炼制配方'} · 产物：{result_name}",
                "description": str(recipe.get("description") or result_item.get("description") or "").strip() or f"可炼制 {result_name}",
                "body_lines": body_lines,
                "tags": [
                    ITEM_KIND_LABELS.get(result_kind, result_kind),
                    str(quality.get("label") or ""),
                    f"{max(int(recipe.get('base_success_rate') or 0), 0)}%",
                    *_source_type_tags(recipe_sources),
                ][:5],
                "keywords": _extract_keywords(
                    str(recipe.get("name") or ""),
                    str(recipe.get("recipe_kind_label") or ""),
                    str(recipe.get("description") or ""),
                    result_name,
                    result_kind,
                    " ".join(ingredient_names),
                    " ".join(recipe_sources),
                ),
            }
        )
        _unique_append(crafted_by_map, (result_kind, result_ref_id), str(recipe.get("name") or "").strip())
    return entries


def _build_material_entries(
    source_map: dict[tuple[str, int], list[str]],
    material_use_map: dict[int, list[str]],
    item_catalog: dict[str, dict[int, dict[str, Any]]],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for material in item_catalog.get("material", {}).values():
        material_id = int(material.get("id") or 0)
        name = str(material.get("name") or "").strip()
        if material_id <= 0 or not name:
            continue
        rules = FARMABLE_MATERIAL_RULES.get(name) or {}
        can_plant = bool(material.get("can_plant")) or bool(rules.get("can_plant"))
        quality = get_quality_meta(material.get("quality_level") or 1)
        sources = source_map.get(("material", material_id), [])
        used_by = material_use_map.get(material_id, [])
        body_lines = []
        if sources:
            body_lines.append(f"主要来源：{_join_labels(sources)}")
        else:
            body_lines.append("主要来源：暂未标注，可留意探索、垂钓、奇遇、奇石与后台补充。")
        if used_by:
            body_lines.append(f"常见用途：{_join_labels(used_by, limit=5)}")
        if can_plant:
            stage = str(material.get("unlock_realm_stage") or rules.get("unlock_realm_stage") or "炼气").strip()
            layer = max(int(material.get("unlock_realm_layer") or rules.get("unlock_realm_layer") or 1), 1)
            body_lines.append(f"灵田种植：{stage}{layer}层后可播种。")
        if can_plant and sources:
            body_lines.append(f"玩法链路：先通过{_source_route_summary(sources)}拿到首批材料或种子，再转灵田稳定产出。")
        elif sources:
            body_lines.append(f"玩法链路：优先走{_source_route_summary(sources)}获取，再按常见用途推进后续炼制或突破。")
        filter_keys = _merge_filter_keys(
            "material",
            _filters_from_source_labels(sources),
            "crafting" if used_by else "",
        )
        entries.append(
            {
                "id": f"material-{material_id}",
                "kind": "material",
                "group": "material",
                "filter_keys": filter_keys,
                "kind_label": "材料",
                "title": name,
                "subtitle": f"材料 · {quality.get('label') or '凡品'}",
                "description": str(material.get("description") or "").strip() or "炼器、炼丹与制符常用材料。",
                "body_lines": body_lines,
                "tags": [
                    str(quality.get("label") or ""),
                    *(_source_type_tags(sources)[:3]),
                    "可种植" if can_plant else "",
                ],
                "keywords": _extract_keywords(name, str(material.get("description") or ""), " ".join(sources), " ".join(used_by)),
            }
        )
    return entries


def _build_item_entries(
    source_map: dict[tuple[str, int], list[str]],
    crafted_by_map: dict[tuple[str, int], list[str]],
    item_catalog: dict[str, dict[int, dict[str, Any]]],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for kind in ("artifact", "pill", "talisman", "technique"):
        for item in item_catalog.get(kind, {}).values():
            item_id = int(item.get("id") or 0)
            name = str(item.get("name") or "").strip()
            if item_id <= 0 or not name:
                continue
            quality = get_quality_meta(item.get("rarity_level") or item.get("rarity") or item.get("quality_level") or 1)
            direct_sources = source_map.get((kind, item_id), [])
            crafted_by = crafted_by_map.get((kind, item_id), [])
            body_lines = []
            if kind != "technique" and crafted_by:
                body_lines.append(f"炼制方式：{_join_labels(crafted_by, limit=4)}")
            if direct_sources:
                source_label = "主要来源" if kind == "technique" else "直接获取"
                body_lines.append(f"{source_label}：{_join_labels(direct_sources, limit=4)}")
            if kind == "technique":
                technique_type = str(item.get("technique_type_label") or item.get("technique_type") or "功法").strip()
                realm_stage = str(item.get("min_realm_stage") or "").strip()
                realm_layer = max(int(item.get("min_realm_layer") or 0), 0)
                if realm_stage:
                    layer_text = f"{realm_layer}层" if realm_layer > 0 else ""
                    body_lines.append(f"修习门槛：{realm_stage}{layer_text}")
                body_lines.append(f"主要加成：{_format_bonus_summary(item)}")
            if not body_lines:
                fallback = "获取方式：暂未标注，可先搜索同名配方或查看相关玩法教程。"
                if kind == "technique":
                    fallback = "获取方式：暂未标注，可留意探索、奇遇、入道赠礼与后台补充。"
                body_lines.append(fallback)
            if kind != "technique" and direct_sources and crafted_by:
                body_lines.append(f"玩法链路：可直接走{_source_route_summary(direct_sources)}获取，也可先搜同名配方走炼制路线。")
            elif direct_sources:
                body_lines.append(f"玩法链路：优先走{_source_route_summary(direct_sources)}获取。")
            elif kind != "technique" and crafted_by:
                body_lines.append("玩法链路：先搜索同名配方，补齐材料后再炼制。")
            elif kind == "technique":
                body_lines.append(f"玩法链路：优先走{_source_route_summary(direct_sources)}掌握功法，再按门槛切换修习。")
            subtitle_parts = [ITEM_KIND_LABELS.get(kind, kind), str(quality.get("label") or "凡品")]
            if kind == "technique":
                subtitle_parts.append(str(item.get("technique_type_label") or item.get("technique_type") or "功法"))
            filter_keys = _merge_filter_keys(
                kind,
                _filters_from_source_labels(direct_sources),
                "crafting" if kind in {"pill", "talisman"} or crafted_by else "",
                "combat" if kind in {"artifact", "talisman"} or _has_combat_bonus(item) else "",
            )
            entries.append(
                {
                    "id": f"{kind}-{item_id}",
                    "kind": kind,
                    "group": kind,
                    "filter_keys": filter_keys,
                    "kind_label": ITEM_KIND_LABELS.get(kind, kind),
                    "title": name,
                    "subtitle": " · ".join(part for part in subtitle_parts if part),
                    "description": str(item.get("description") or "").strip() or "可在修仙世界中获取与使用。",
                    "body_lines": body_lines,
                    "tags": [
                        ITEM_KIND_LABELS.get(kind, kind),
                        str(quality.get("label") or ""),
                        *(_source_type_tags(direct_sources)[:3]),
                    ],
                    "keywords": _extract_keywords(name, str(item.get("description") or ""), " ".join(crafted_by), " ".join(direct_sources)),
                }
            )
    return entries


def _build_title_entries(
    source_map: dict[tuple[str, int], list[str]],
    title_catalog: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for title in title_catalog.values():
        title_id = int(title.get("id") or 0)
        name = str(title.get("name") or "").strip()
        if title_id <= 0 or not name:
            continue
        sources = source_map.get(("title", title_id), [])
        body_lines = [
            f"主要来源：{_join_labels(sources, limit=4)}" if sources else "主要来源：暂未标注，可留意成就、师徒、入道赠礼与后台补充。",
            f"称号效果：{_format_bonus_summary(title)}",
        ]
        if sources:
            body_lines.append(f"玩法链路：围绕{_source_route_summary(sources)}推进，对应达标后即可领取称号。")
        filter_keys = _merge_filter_keys(
            "title",
            _filters_from_source_labels(sources),
            "combat" if _has_combat_bonus(title) else "",
        )
        entries.append(
            {
                "id": f"title-{title_id}",
                "kind": "title",
                "group": "title",
                "filter_keys": filter_keys,
                "kind_label": "称号",
                "title": name,
                "subtitle": "称号",
                "description": str(title.get("description") or "").strip() or "佩戴后可提供额外加成。",
                "body_lines": body_lines,
                "tags": ["称号", *_source_type_tags(sources)[:3]],
                "keywords": _extract_keywords(name, str(title.get("description") or ""), " ".join(sources)),
            }
        )
    return entries


def _build_achievement_entries(
    item_catalog: dict[str, dict[int, dict[str, Any]]],
    title_catalog: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for achievement in list_achievements(enabled_only=True):
        achievement_id = int(achievement.get("id") or 0)
        if achievement_id <= 0:
            continue
        reward = achievement.get("reward_config") or {}
        reward_titles = [
            str((title_catalog.get(int(title_id or 0)) or {}).get("name") or "").strip()
            for title_id in reward.get("titles") or []
            if int(title_id or 0) > 0
        ]
        reward_titles = [title for title in reward_titles if title]
        reward_items = []
        for reward_item in reward.get("items") or []:
            kind = str((reward_item or {}).get("kind") or "").strip()
            ref_id = int((reward_item or {}).get("ref_id") or 0)
            quantity = max(int((reward_item or {}).get("quantity") or 0), 0)
            if not kind or ref_id <= 0 or quantity <= 0:
                continue
            payload = (item_catalog.get(kind) or {}).get(ref_id) or {}
            reward_items.append(str(payload.get("name") or f"{ITEM_KIND_LABELS.get(kind, kind)}#{ref_id}").strip())
        metric_key = str(achievement.get("metric_key") or "").strip()
        metric_label = ACHIEVEMENT_METRIC_LABELS.get(metric_key, metric_key or "未标注")
        route_hint = ACHIEVEMENT_ROUTE_HINTS.get(metric_key, "玩法链路：推进对应玩法并累计次数、胜场或收益后，即可解锁该成就。")
        filter_keys = _merge_filter_keys("achievement", _filters_from_metric_key(metric_key))
        entries.append(
            {
                "id": f"achievement-{achievement_id}",
                "kind": "achievement",
                "group": "achievement",
                "filter_keys": filter_keys,
                "kind_label": "成就",
                "title": str(achievement.get("name") or "").strip() or f"成就#{achievement_id}",
                "subtitle": f"成就 · {metric_label} · 目标 {max(int(achievement.get('target_value') or 0), 1)}",
                "description": str(achievement.get("description") or "").strip() or "达成指定玩法目标后可领取奖励。",
                "body_lines": [
                    f"统计项目：{metric_label}" + (f"（{metric_key}）" if metric_key and metric_label != metric_key else ""),
                    f"达成目标：{max(int(achievement.get('target_value') or 0), 1)}",
                    f"奖励内容：{_format_reward_summary(reward, item_catalog, title_catalog)}",
                    route_hint,
                ],
                "tags": [
                    "成就",
                    metric_label,
                    *(reward_titles[:2]),
                ],
                "keywords": _extract_keywords(
                    str(achievement.get("name") or ""),
                    str(achievement.get("achievement_key") or ""),
                    str(achievement.get("description") or ""),
                    metric_key,
                    metric_label,
                    " ".join(reward_titles),
                    " ".join(reward_items),
                    route_hint,
                ),
            }
        )
    return entries


def build_wiki_bundle() -> dict[str, Any]:
    ensure_seed_data()
    tutorials = _parse_guide_sections()
    item_catalog = _build_item_catalog()
    title_catalog = _build_title_catalog()
    source_map = _build_source_catalog(item_catalog, title_catalog)
    material_use_map: dict[int, list[str]] = defaultdict(list)
    crafted_by_map: dict[tuple[str, int], list[str]] = defaultdict(list)
    recipe_entries = _build_recipe_entries(source_map, material_use_map, crafted_by_map, item_catalog)
    material_entries = _build_material_entries(source_map, material_use_map, item_catalog)
    item_entries = _build_item_entries(source_map, crafted_by_map, item_catalog)
    title_entries = _build_title_entries(source_map, title_catalog)
    achievement_entries = _build_achievement_entries(item_catalog, title_catalog)
    artifact_count = sum(1 for entry in item_entries if str(entry.get("group") or "") == "artifact")
    pill_count = sum(1 for entry in item_entries if str(entry.get("group") or "") == "pill")
    talisman_count = sum(1 for entry in item_entries if str(entry.get("group") or "") == "talisman")
    technique_count = sum(1 for entry in item_entries if str(entry.get("group") or "") == "technique")
    search_index = tutorials + material_entries + item_entries + title_entries + recipe_entries + achievement_entries
    featured_tutorials = tutorials[:8]
    return {
        "featured_tutorials": featured_tutorials,
        "search_index": search_index,
        "counts": {
            "tutorial": len(tutorials),
            "material": len(material_entries),
            "artifact": artifact_count,
            "pill": pill_count,
            "talisman": talisman_count,
            "technique": technique_count,
            "title": len(title_entries),
            "recipe": len(recipe_entries),
            "achievement": len(achievement_entries),
        },
        "search_examples": ["闭关", "宗门", "补天丹", "天道精华", "玄龟盾炼制图", "长青诀", "初入仙途", "承道出山"],
    }
