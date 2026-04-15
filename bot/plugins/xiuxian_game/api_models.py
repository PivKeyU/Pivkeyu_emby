from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class InitDataPayload(BaseModel):
    init_data: str


class BreakthroughPayload(InitDataPayload):
    use_pill: bool = False


class ConsumePillPayload(InitDataPayload):
    pill_id: int


class EquipArtifactPayload(InitDataPayload):
    artifact_id: int


class ArtifactBindingPayload(InitDataPayload):
    artifact_id: int


class ActivateTalismanPayload(InitDataPayload):
    talisman_id: int


class TalismanBindingPayload(InitDataPayload):
    talisman_id: int


class ActivateTechniquePayload(InitDataPayload):
    technique_id: int


class TitleEquipPayload(InitDataPayload):
    title_id: int | None = None


class TitleGroupSyncPayload(InitDataPayload):
    chat_id: int | None = None


class ExchangePayload(InitDataPayload):
    direction: str
    amount: int


class LeaderboardPayload(InitDataPayload):
    kind: str = "stone"
    page: int = 1


class PersonalShopPayload(InitDataPayload):
    shop_name: str
    item_kind: str
    item_ref_id: int
    quantity: int
    price_stone: int
    broadcast: bool = False


class PurchasePayload(InitDataPayload):
    item_id: int
    quantity: int = 1


class RetreatPayload(InitDataPayload):
    hours: int = 1


class SectJoinPayload(InitDataPayload):
    sect_id: int


class GiftPayload(InitDataPayload):
    target_tg: int
    amount: int


class TaskClaimPayload(InitDataPayload):
    task_id: int


class TaskCancelPayload(InitDataPayload):
    task_id: int


class CraftPayload(InitDataPayload):
    recipe_id: int


class ExploreStartPayload(InitDataPayload):
    scene_id: int
    minutes: int = 60


class ExploreClaimPayload(InitDataPayload):
    exploration_id: int


class ShopCancelPayload(InitDataPayload):
    item_id: int


class RedEnvelopePayload(InitDataPayload):
    cover_text: str = "福运临门"
    image_url: str = ""
    mode: str = "normal"
    amount_total: int
    count_total: int
    target_tg: int | None = None


class UserTaskPayload(InitDataPayload):
    title: str
    description: str = ""
    task_scope: str = "personal"
    task_type: str = "custom"
    question_text: str = ""
    answer_text: str = ""
    image_url: str = ""
    required_item_kind: str | None = None
    required_item_ref_id: int | None = None
    required_item_quantity: int = 0
    reward_stone: int = 0
    reward_item_kind: str | None = None
    reward_item_ref_id: int | None = None
    reward_item_quantity: int = 0
    max_claimants: int = 1
    active_in_group: bool = False
    group_chat_id: int | None = None


class AdminBootstrapPayload(BaseModel):
    token: str | None = None
    init_data: str | None = None


class RootQualityRulePayload(BaseModel):
    cultivation_rate: float
    breakthrough_bonus: int
    combat_factor: float


class DropWeightRulePayload(BaseModel):
    material_divine_sense_divisor: int
    high_quality_threshold: int
    high_quality_fortune_divisor: int
    high_quality_root_level_start: int


class ItemQualityValueRulePayload(BaseModel):
    artifact_multiplier: float
    pill_multiplier: float
    talisman_multiplier: float


class AdminSettingPayload(BaseModel):
    coin_exchange_rate: int | None = None
    exchange_fee_percent: int | None = None
    min_coin_exchange: int | None = None
    duel_bet_minutes: int | None = None
    duel_invite_timeout_seconds: int | None = None
    duel_winner_steal_percent: int | None = None
    artifact_plunder_chance: int | None = None
    message_auto_delete_seconds: int | None = None
    equipment_unbind_cost: int | None = None
    shop_broadcast_cost: int | None = None
    official_shop_name: str | None = None
    allow_user_task_publish: bool | None = None
    task_publish_cost: int | None = None
    user_task_daily_limit: int | None = None
    artifact_equip_limit: int | None = None
    allow_non_admin_image_upload: bool | None = None
    chat_cultivation_chance: int | None = None
    chat_cultivation_min_gain: int | None = None
    chat_cultivation_max_gain: int | None = None
    robbery_daily_limit: int | None = None
    robbery_max_steal: int | None = None
    high_quality_broadcast_level: int | None = None
    slave_tribute_percent: int | None = None
    slave_challenge_cooldown_hours: int | None = None
    sect_salary_min_stay_days: int | None = None
    sect_betrayal_cooldown_days: int | None = None
    sect_betrayal_stone_percent: int | None = None
    sect_betrayal_stone_min: int | None = None
    sect_betrayal_stone_max: int | None = None
    root_quality_value_rules: dict[str, RootQualityRulePayload] | None = None
    exploration_drop_weight_rules: DropWeightRulePayload | None = None
    item_quality_value_rules: dict[str, ItemQualityValueRulePayload] | None = None
    immortal_touch_infusion_layers: int | None = None


class ArtifactPayload(BaseModel):
    name: str
    rarity: str = "凡品"
    artifact_type: str = "battle"
    artifact_role: str = "battle"
    equip_slot: str = "weapon"
    artifact_set_id: int | None = None
    image_url: str = ""
    description: str = ""
    attack_bonus: int = 0
    defense_bonus: int = 0
    bone_bonus: int = 0
    comprehension_bonus: int = 0
    divine_sense_bonus: int = 0
    fortune_bonus: int = 0
    qi_blood_bonus: int = 0
    true_yuan_bonus: int = 0
    body_movement_bonus: int = 0
    duel_rate_bonus: int = 0
    cultivation_bonus: int = 0
    combat_config: dict[str, Any] = Field(default_factory=dict)
    min_realm_stage: str | None = None
    min_realm_layer: int = 1
    enabled: bool = True


class PillPayload(BaseModel):
    name: str
    rarity: str = "凡品"
    pill_type: str
    image_url: str = ""
    description: str = ""
    effect_value: int = 0
    poison_delta: int = 0
    attack_bonus: int = 0
    defense_bonus: int = 0
    bone_bonus: int = 0
    comprehension_bonus: int = 0
    divine_sense_bonus: int = 0
    fortune_bonus: int = 0
    qi_blood_bonus: int = 0
    true_yuan_bonus: int = 0
    body_movement_bonus: int = 0
    min_realm_stage: str | None = None
    min_realm_layer: int = 1
    enabled: bool = True


class TalismanPayload(BaseModel):
    name: str
    rarity: str = "凡品"
    image_url: str = ""
    description: str = ""
    attack_bonus: int = 0
    defense_bonus: int = 0
    bone_bonus: int = 0
    comprehension_bonus: int = 0
    divine_sense_bonus: int = 0
    fortune_bonus: int = 0
    qi_blood_bonus: int = 0
    true_yuan_bonus: int = 0
    body_movement_bonus: int = 0
    duel_rate_bonus: int = 0
    effect_uses: int = 1
    combat_config: dict[str, Any] = Field(default_factory=dict)
    min_realm_stage: str | None = None
    min_realm_layer: int = 1
    enabled: bool = True


class TechniquePayload(BaseModel):
    name: str
    rarity: str = "凡品"
    technique_type: str = "balanced"
    image_url: str = ""
    description: str = ""
    attack_bonus: int = 0
    defense_bonus: int = 0
    bone_bonus: int = 0
    comprehension_bonus: int = 0
    divine_sense_bonus: int = 0
    fortune_bonus: int = 0
    qi_blood_bonus: int = 0
    true_yuan_bonus: int = 0
    body_movement_bonus: int = 0
    duel_rate_bonus: int = 0
    cultivation_bonus: int = 0
    breakthrough_bonus: int = 0
    combat_config: dict[str, Any] = Field(default_factory=dict)
    min_realm_stage: str | None = None
    min_realm_layer: int = 1
    enabled: bool = True


class GrantPayload(BaseModel):
    tg: int
    item_kind: str
    item_ref_id: int
    quantity: int = 1


class TitlePayload(BaseModel):
    name: str
    description: str = ""
    color: str = ""
    image_url: str = ""
    attack_bonus: int = 0
    defense_bonus: int = 0
    bone_bonus: int = 0
    comprehension_bonus: int = 0
    divine_sense_bonus: int = 0
    fortune_bonus: int = 0
    qi_blood_bonus: int = 0
    true_yuan_bonus: int = 0
    body_movement_bonus: int = 0
    duel_rate_bonus: int = 0
    cultivation_bonus: int = 0
    breakthrough_bonus: int = 0
    enabled: bool = True


class TitleGrantPayload(BaseModel):
    tg: int
    title_id: int
    equip: bool = False


class AchievementPayload(BaseModel):
    achievement_key: str | None = None
    name: str
    description: str = ""
    metric_key: str
    target_value: int
    reward_config: dict[str, Any] = Field(default_factory=dict)
    notify_group: bool = True
    notify_private: bool = True
    enabled: bool = True
    sort_order: int = 0


class AchievementProgressPayload(BaseModel):
    tg: int
    increments: dict[str, int] = Field(default_factory=dict)
    source: str | None = None


class OfficialShopPayload(BaseModel):
    item_kind: str
    item_ref_id: int
    quantity: int
    price_stone: int
    shop_name: str | None = None


class OfficialShopPatchPayload(BaseModel):
    enabled: bool | None = None
    quantity: int | None = None
    price_stone: int | None = None


class SectRolePayload(BaseModel):
    role_key: str
    role_name: str
    attack_bonus: int = 0
    defense_bonus: int = 0
    duel_rate_bonus: int = 0
    cultivation_bonus: int = 0
    monthly_salary: int = 0
    can_publish_tasks: bool = False
    sort_order: int = 1


class SectPayload(BaseModel):
    name: str
    description: str = ""
    image_url: str = ""
    camp: str = "orthodox"
    min_realm_stage: str | None = None
    min_realm_layer: int = 1
    min_stone: int = 0
    min_bone: int = 0
    min_comprehension: int = 0
    min_divine_sense: int = 0
    min_fortune: int = 0
    min_willpower: int = 0
    min_charisma: int = 0
    min_karma: int = 0
    min_body_movement: int = 0
    min_combat_power: int = 0
    attack_bonus: int = 0
    defense_bonus: int = 0
    duel_rate_bonus: int = 0
    cultivation_bonus: int = 0
    fortune_bonus: int = 0
    body_movement_bonus: int = 0
    entry_hint: str = ""
    roles: list[SectRolePayload] = Field(default_factory=list)


class ArtifactSetPayload(BaseModel):
    name: str
    description: str = ""
    required_count: int = 2
    attack_bonus: int = 0
    defense_bonus: int = 0
    bone_bonus: int = 0
    comprehension_bonus: int = 0
    divine_sense_bonus: int = 0
    fortune_bonus: int = 0
    qi_blood_bonus: int = 0
    true_yuan_bonus: int = 0
    body_movement_bonus: int = 0
    duel_rate_bonus: int = 0
    cultivation_bonus: int = 0
    breakthrough_bonus: int = 0
    enabled: bool = True


class SectRoleAssignPayload(BaseModel):
    tg: int
    sect_id: int
    role_key: str


class MaterialPayload(BaseModel):
    name: str
    quality_level: int = 1
    image_url: str = ""
    description: str = ""
    enabled: bool = True


class RecipeIngredientPayload(BaseModel):
    material_id: int
    quantity: int = 1


class RecipePayload(BaseModel):
    name: str
    recipe_kind: str
    result_kind: str
    result_ref_id: int
    result_quantity: int = 1
    base_success_rate: int = 60
    broadcast_on_success: bool = False
    ingredients: list[RecipeIngredientPayload] = Field(default_factory=list)


class SceneEventPayload(BaseModel):
    name: str = ""
    description: str = ""
    event_type: str = "encounter"
    weight: int = 1
    stone_bonus_min: int = 0
    stone_bonus_max: int = 0
    stone_loss_min: int = 0
    stone_loss_max: int = 0
    bonus_reward_kind: str | None = None
    bonus_reward_ref_id: int | None = None
    bonus_quantity_min: int = 1
    bonus_quantity_max: int = 1
    bonus_chance: int = 0


class SceneDropPayload(BaseModel):
    reward_kind: str = "material"
    reward_ref_id: int | None = None
    quantity_min: int = 1
    quantity_max: int = 1
    weight: int = 1
    stone_reward: int = 0
    event_text: str = ""


class ScenePayload(BaseModel):
    name: str
    description: str = ""
    image_url: str = ""
    max_minutes: int = 60
    min_realm_stage: str | None = None
    min_realm_layer: int = 1
    min_combat_power: int = 0
    event_pool: list[SceneEventPayload] = Field(default_factory=list)
    drops: list[SceneDropPayload] = Field(default_factory=list)


class EncounterPayload(BaseModel):
    name: str
    description: str = ""
    image_url: str = ""
    button_text: str = "争抢机缘"
    success_text: str = ""
    broadcast_text: str = ""
    weight: int = 1
    active_seconds: int = 90
    min_realm_stage: str | None = None
    min_realm_layer: int = 1
    min_combat_power: int = 0
    reward_stone_min: int = 0
    reward_stone_max: int = 0
    reward_cultivation_min: int = 0
    reward_cultivation_max: int = 0
    reward_item_kind: str | None = None
    reward_item_ref_id: int | None = None
    reward_item_quantity_min: int = 1
    reward_item_quantity_max: int = 1
    reward_willpower: int = 0
    reward_charisma: int = 0
    reward_karma: int = 0
    enabled: bool = True


class EncounterDispatchPayload(BaseModel):
    template_id: int | None = None
    group_chat_id: int | None = None


class UploadPermissionPayload(BaseModel):
    tg: int


class AdminTaskPayload(BaseModel):
    title: str
    description: str = ""
    task_scope: str = "official"
    task_type: str = "custom"
    question_text: str = ""
    answer_text: str = ""
    image_url: str = ""
    required_item_kind: str | None = None
    required_item_ref_id: int | None = None
    required_item_quantity: int = 0
    reward_stone: int = 0
    reward_item_kind: str | None = None
    reward_item_ref_id: int | None = None
    reward_item_quantity: int = 0
    max_claimants: int = 1
    sect_id: int | None = None
    active_in_group: bool = False
    group_chat_id: int | None = None


class PlayerPatchPayload(BaseModel):
    spiritual_stone: int | None = None
    cultivation: int | None = None
    realm_stage: str | None = None
    realm_layer: int | None = None
    bone: int | None = None
    comprehension: int | None = None
    divine_sense: int | None = None
    fortune: int | None = None
    willpower: int | None = None
    charisma: int | None = None
    karma: int | None = None
    qi_blood: int | None = None
    true_yuan: int | None = None
    body_movement: int | None = None
    attack_power: int | None = None
    defense_power: int | None = None
    insight_bonus: int | None = None
    dan_poison: int | None = None
    sect_contribution: int | None = None
    root_type: str | None = None
    root_primary: str | None = None
    root_secondary: str | None = None
    root_relation: str | None = None
    root_bonus: int | None = None
    root_quality: str | None = None
    display_name: str | None = None
    username: str | None = None
    technique_capacity: int | None = None


class PlayerResourceGrantPayload(BaseModel):
    item_kind: str
    item_ref_id: int
    quantity: int = 1
    equip: bool = False


class PlayerInventoryPayload(BaseModel):
    item_kind: str
    item_ref_id: int
    quantity: int
    bound_quantity: int | None = None


class PlayerSelectionPayload(BaseModel):
    selection_kind: str
    item_ref_id: int | None = None


class PlayerRevokePayload(BaseModel):
    item_kind: str
    item_ref_id: int
