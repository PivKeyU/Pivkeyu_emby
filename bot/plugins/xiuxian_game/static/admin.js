const tg = window.Telegram?.WebApp;
const tgBackButton = tg?.BackButton || null;
const DEFAULT_BACK_PATH = "/admin";

const REALM_OPTIONS = ["炼气", "筑基", "金丹", "元婴", "化神", "炼虚", "合体", "大乘", "渡劫", "人仙", "地仙", "天仙", "金仙", "大罗金仙", "仙君", "仙王", "仙尊", "仙帝"];
const QUALITY_OPTIONS = ["凡品", "下品", "中品", "上品", "极品", "仙品", "先天至宝"];
const PILL_TYPES = [
  { value: "foundation", label: "突破加成", effect: "突破助力值" },
  { value: "clear_poison", label: "解毒", effect: "减少丹毒值" },
  { value: "cultivation", label: "提升修为", effect: "增加修为值" },
  { value: "stone", label: "补给灵石", effect: "增加灵石值" },
  { value: "bone", label: "提升根骨", effect: "根骨增量" },
  { value: "comprehension", label: "提升悟性", effect: "悟性增量" },
  { value: "divine_sense", label: "提升神识", effect: "神识增量" },
  { value: "fortune", label: "提升机缘", effect: "机缘增量" },
  { value: "qi_blood", label: "提升气血", effect: "气血增量" },
  { value: "true_yuan", label: "提升真元", effect: "真元增量" },
  { value: "body_movement", label: "提升身法", effect: "身法增量" },
  { value: "attack", label: "提升攻击", effect: "攻击增量" },
  { value: "defense", label: "提升防御", effect: "防御增量" },
  { value: "root_refine", label: "淬炼灵根", effect: "淬灵阶数" },
  { value: "root_remold", label: "重塑灵根", effect: "保底品阶" },
  { value: "root_single", label: "洗成单灵根", effect: "保底品阶" },
  { value: "root_double", label: "洗成双灵根", effect: "保底品阶" },
  { value: "root_earth", label: "洗成地灵根", effect: "效果值未用" },
  { value: "root_heaven", label: "洗成天灵根", effect: "效果值未用" },
  { value: "root_variant", label: "洗成变异灵根", effect: "效果值未用" },
];
const SCENE_EVENT_TYPES = [
  ["encounter", "普通遭遇"],
  ["fortune", "机缘"],
  ["danger", "危险"],
  ["recipe", "配方残页"],
  ["oddity", "奇遇"],
];
const ROLE_PRESETS = [
  ["leader", "掌门"],
  ["elder", "长老"],
  ["core", "真传弟子"],
  ["inner_deacon", "内门执事"],
  ["outer_deacon", "外门执事"],
  ["inner_disciple", "内门弟子"],
  ["outer_disciple", "外门弟子"],
];
const PLAYER_SEARCH_PAGE_SIZE = 10;
const GRANT_USER_SEARCH_PAGE_SIZE = 8;
const GRANT_USER_SEARCH_DEBOUNCE_MS = 220;

const state = {
  token: localStorage.getItem("xiuxian_admin_token") || "",
  initData: tg?.initData || "",
  bundle: null,
  selectedPlayerTg: null,
  selectedPlayerDetail: null,
  playerSearch: {
    query: "",
    page: 1,
    pageSize: PLAYER_SEARCH_PAGE_SIZE,
    total: 0,
    items: [],
  },
  grantForm: {
    userOptions: [],
    userQuery: "",
    userSearchSeq: 0,
    userSearchTimer: null,
  },
};
const backState = {
  fallbackPath: DEFAULT_BACK_PATH,
  returnTo: "",
  referrerPath: ""
};
const TITLE_COLOR_DEFAULT = "#0f766e";
const TITLE_GRADIENT_DEFAULT_END = "#38bdf8";
const TITLE_SOLID_SWATCHES = [
  { label: "青玉", value: "#0f766e" },
  { label: "沧海", value: "#2563eb" },
  { label: "金霞", value: "#f59e0b" },
  { label: "赤霄", value: "#dc2626" },
  { label: "紫府", value: "#7c3aed" },
  { label: "桃华", value: "#ec4899" },
  { label: "霜银", value: "#94a3b8" },
  { label: "玄曜", value: "#111827" },
];
const TITLE_GRADIENT_PRESETS = [
  { label: "青霄流光", value: "linear-gradient(135deg, #0f766e 0%, #38bdf8 100%)" },
  { label: "赤金焰尾", value: "linear-gradient(135deg, #dc2626 0%, #f59e0b 100%)" },
  { label: "紫电星河", value: "linear-gradient(135deg, #7c3aed 0%, #2563eb 100%)" },
  { label: "琼华朝露", value: "linear-gradient(135deg, #14b8a6 0%, #e879f9 100%)" },
];
const TITLE_RAINBOW_PRESETS = [
  { label: "霓虹天幕", value: "linear-gradient(135deg, #fb7185 0%, #f59e0b 18%, #fde047 36%, #34d399 54%, #60a5fa 72%, #a78bfa 88%, #f472b6 100%)" },
  { label: "极光潮汐", value: "linear-gradient(135deg, #22d3ee 0%, #0ea5e9 18%, #6366f1 40%, #a855f7 64%, #ec4899 100%)" },
  { label: "琉璃焰轮", value: "linear-gradient(135deg, #f97316 0%, #ef4444 24%, #e879f9 52%, #8b5cf6 78%, #38bdf8 100%)" },
  { label: "仙虹织锦", value: "linear-gradient(135deg, #f43f5e 0%, #fb7185 15%, #facc15 35%, #4ade80 58%, #38bdf8 78%, #818cf8 100%)" },
];
let titleColorEditorMode = "solid";

const ADMIN_SECTION_LABELS = {
  settings: "\u57fa\u7840\u8bbe\u5b9a",
  "duel-settings": "\u6597\u6cd5\u8bbe\u5b9a",
  artifacts: "\u6cd5\u5b9d",
  talismans: "符箓",
  pills: "\u4e39\u836f",
  techniques: "\u529f\u6cd5",
  sects: "\u5b97\u95e8",
  materials: "\u6750\u6599",
  recipes: "\u914d\u65b9",
  scenes: "\u573a\u666f",
  encounters: "奇遇",
  tasks: "\u4efb\u52a1",
  auctions: "拍卖行",
  grant: "\u624b\u52a8\u53d1\u653e",
  "official shop": "\u5b98\u65b9\u5546\u5e97",
  players: "\u89d2\u8272\u7ba1\u7406",
};
const ADMIN_CORE_SECTION_KEYS = new Set(["settings", "duel-settings", "tasks", "grant", "official shop", "players"]);

const ITEM_AFFIX_FIELDS = [
  ["attack", "攻击"],
  ["defense", "防御"],
  ["bone", "根骨"],
  ["comprehension", "悟性"],
  ["divine-sense", "神识"],
  ["fortune", "机缘"],
  ["qi-blood", "气血"],
  ["true-yuan", "真元"],
  ["body-movement", "身法"],
];
const ROOT_QUALITY_RULES = [
  { key: "废灵根", label: "废灵根" },
  { key: "下品灵根", label: "下品灵根" },
  { key: "中品灵根", label: "中品灵根" },
  { key: "上品灵根", label: "上品灵根" },
  { key: "极品灵根", label: "极品灵根" },
  { key: "天灵根", label: "天灵根" },
  { key: "变异灵根", label: "变异灵根" },
];
const DEFAULT_ROOT_QUALITY_RULES = {
  废灵根: { cultivation_rate: 0.72, breakthrough_bonus: -8, combat_factor: 0.92 },
  下品灵根: { cultivation_rate: 0.88, breakthrough_bonus: -3, combat_factor: 0.97 },
  中品灵根: { cultivation_rate: 1.0, breakthrough_bonus: 0, combat_factor: 1.0 },
  上品灵根: { cultivation_rate: 1.12, breakthrough_bonus: 3, combat_factor: 1.05 },
  极品灵根: { cultivation_rate: 1.24, breakthrough_bonus: 6, combat_factor: 1.1 },
  天灵根: { cultivation_rate: 1.38, breakthrough_bonus: 12, combat_factor: 1.16 },
  变异灵根: { cultivation_rate: 1.3, breakthrough_bonus: 9, combat_factor: 1.14 },
};
const ITEM_QUALITY_RULES = [
  { key: "凡品", label: "凡品" },
  { key: "下品", label: "下品" },
  { key: "中品", label: "中品" },
  { key: "上品", label: "上品" },
  { key: "极品", label: "极品" },
  { key: "仙品", label: "仙品" },
  { key: "先天至宝", label: "先天至宝" },
];
const DEFAULT_ITEM_QUALITY_RULES = {
  凡品: { artifact_multiplier: 1.0, pill_multiplier: 1.0, talisman_multiplier: 1.0 },
  下品: { artifact_multiplier: 1.0, pill_multiplier: 1.0, talisman_multiplier: 1.0 },
  中品: { artifact_multiplier: 1.0, pill_multiplier: 1.0, talisman_multiplier: 1.0 },
  上品: { artifact_multiplier: 1.0, pill_multiplier: 1.0, talisman_multiplier: 1.0 },
  极品: { artifact_multiplier: 1.0, pill_multiplier: 1.0, talisman_multiplier: 1.0 },
  仙品: { artifact_multiplier: 1.0, pill_multiplier: 1.0, talisman_multiplier: 1.0 },
  先天至宝: { artifact_multiplier: 1.0, pill_multiplier: 1.0, talisman_multiplier: 1.0 },
};
const DROP_WEIGHT_RULE_FIELDS = [
  { key: "material_divine_sense_divisor", label: "材料掉落神识除数", tip: "神识越高，材料基础权重加成越明显；数值越小加成越快。" },
  { key: "high_quality_threshold", label: "高品质判定阈值", tip: "达到该品质及以上时，才会触发机缘和灵根的额外掉落加权。" },
  { key: "high_quality_fortune_divisor", label: "高品质机缘除数", tip: "机缘对高品质掉落的加成速度；数值越小，高机缘越容易出稀有掉落。" },
  { key: "high_quality_root_level_start", label: "高品质灵根起算等级", tip: "灵根等级高于该值后，额外权重开始生效。" },
];
const DEFAULT_DROP_WEIGHT_RULES = {
  material_divine_sense_divisor: 5,
  high_quality_threshold: 4,
  high_quality_fortune_divisor: 5,
  high_quality_root_level_start: 3,
};
const ACTIVITY_GROWTH_FIELDS = [
  { key: "practice", label: "吐纳修炼", tip: "每日吐纳结束后的微幅成长。" },
  { key: "commission", label: "灵石打工", tip: "完成打工或委托结算后的微幅成长。" },
  { key: "exploration", label: "秘境探索", tip: "领取探索奖励时的微幅成长。" },
  { key: "duel", label: "斗法胜出", tip: "普通斗法胜者的战后感悟成长。" },
];
const DEFAULT_ACTIVITY_GROWTH_RULES = {
  practice: { chance_percent: 18, gain_min: 1, gain_max: 2, attribute_count: 1 },
  commission: { chance_percent: 22, gain_min: 1, gain_max: 2, attribute_count: 1 },
  exploration: { chance_percent: 26, gain_min: 1, gain_max: 3, attribute_count: 1 },
  duel: { chance_percent: 20, gain_min: 1, gain_max: 2, attribute_count: 2 },
};
const GAMBLING_ITEM_KIND_OPTIONS = [
  { value: "material", label: "材料" },
  { value: "artifact", label: "法宝" },
  { value: "pill", label: "丹药" },
  { value: "talisman", label: "符箓" },
];
const DEFAULT_GAMBLING_QUALITY_RULES = {
  凡品: { weight_multiplier: 1.0 },
  下品: { weight_multiplier: 0.72 },
  中品: { weight_multiplier: 0.44 },
  上品: { weight_multiplier: 0.22 },
  极品: { weight_multiplier: 0.1 },
  仙品: { weight_multiplier: 0.04 },
  先天至宝: { weight_multiplier: 0.015 },
};
const DEFAULT_FISHING_QUALITY_RULES = {
  凡品: { weight_multiplier: 1.0 },
  下品: { weight_multiplier: 0.6 },
  中品: { weight_multiplier: 0.28 },
  上品: { weight_multiplier: 0.12 },
  极品: { weight_multiplier: 0.045 },
  仙品: { weight_multiplier: 0.012 },
  先天至宝: { weight_multiplier: 0.003 },
};
const PLAYER_STRING_FIELDS = new Set([
  "realm_stage",
  "root_type",
  "root_primary",
  "root_secondary",
  "root_relation",
  "root_quality",
]);
const EMBY_LEVEL_LABELS = {
  a: "白名单",
  b: "正常",
  c: "封禁",
  d: "未注册",
};

REALM_OPTIONS.splice(0, REALM_OPTIONS.length, "炼气", "筑基", "金丹", "元婴", "化神", "炼虚", "合体", "大乘", "渡劫", "人仙", "地仙", "天仙", "金仙", "大罗金仙", "仙君", "仙王", "仙尊", "仙帝");
QUALITY_OPTIONS.splice(0, QUALITY_OPTIONS.length, "凡品", "下品", "中品", "上品", "极品", "仙品", "先天至宝");
PILL_TYPES.splice(0, PILL_TYPES.length, ...[
  { value: "foundation", label: "突破加成", effect: "突破增幅" },
  { value: "clear_poison", label: "解毒", effect: "减少丹毒" },
  { value: "cultivation", label: "提升修为", effect: "增加修为" },
  { value: "stone", label: "补给灵石", effect: "增加灵石" },
  { value: "bone", label: "提升根骨", effect: "根骨增量" },
  { value: "comprehension", label: "提升悟性", effect: "提升悟性" },
  { value: "divine_sense", label: "提升神识", effect: "神识增量" },
  { value: "fortune", label: "提升机缘", effect: "机缘增量" },
  { value: "qi_blood", label: "提升气血", effect: "提升气血" },
  { value: "true_yuan", label: "提升真元", effect: "提升真元" },
  { value: "body_movement", label: "提升身法", effect: "提升身法" },
  { value: "attack", label: "提升攻击", effect: "提升攻击" },
  { value: "defense", label: "提升防御", effect: "提升防御" },
  { value: "root_refine", label: "淬炼灵根", effect: "淬灵阶数" },
  { value: "root_remold", label: "重塑灵根", effect: "保底品阶" },
  { value: "root_single", label: "洗成单灵根", effect: "保底品阶" },
  { value: "root_double", label: "洗成双灵根", effect: "保底品阶" },
  { value: "root_earth", label: "洗成地灵根", effect: "效果值未用" },
  { value: "root_heaven", label: "洗成天灵根", effect: "效果值未用" },
  { value: "root_variant", label: "洗成变异灵根", effect: "效果值未用" },
]);
ROLE_PRESETS.splice(0, ROLE_PRESETS.length, ...[
  ["leader", "掌门"],
  ["elder", "长老"],
  ["core", "真传弟子"],
  ["inner_deacon", "内门执事"],
  ["outer_deacon", "外门执事"],
  ["inner_disciple", "内门弟子"],
  ["outer_disciple", "外门弟子"],
]);
ITEM_AFFIX_FIELDS.splice(0, ITEM_AFFIX_FIELDS.length, ...[
  ["attack", "攻击"],
  ["defense", "防御"],
  ["bone", "根骨"],
  ["comprehension", "悟性"],
  ["divine-sense", "神识"],
  ["fortune", "机缘"],
  ["qi-blood", "气血"],
  ["true-yuan", "真元"],
  ["body-movement", "身法"],
]);

function $(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function normalizeHexColor(value) {
  const raw = String(value || "").trim();
  if (/^#[0-9a-f]{3}$/i.test(raw)) {
    const [, r, g, b] = raw;
    return `#${r}${r}${g}${g}${b}${b}`.toLowerCase();
  }
  if (/^#[0-9a-f]{6}$/i.test(raw)) return raw.toLowerCase();
  if (/^#[0-9a-f]{8}$/i.test(raw)) return `#${raw.slice(1, 7)}`.toLowerCase();
  return "";
}

function hexWithAlpha(value, alpha) {
  const hex = normalizeHexColor(value);
  return hex ? `${hex}${alpha}` : "";
}

function isGradientDecorColor(value) {
  return /gradient\s*\(/i.test(String(value || ""));
}

function normalizeDecorColor(value, fallback = "") {
  const raw = String(value || "").trim();
  if (!raw) return fallback;
  if (raw.length > 255) return fallback;
  if (!/^[#(),.%/+\-\sa-zA-Z0-9]+$/.test(raw)) return fallback;
  const lower = raw.toLowerCase();
  if (lower.includes("url(") || lower.includes("expression(") || lower.includes("javascript:") || lower.includes("var(")) {
    return fallback;
  }
  if (/^#[0-9a-f]{3,8}$/i.test(raw)) return raw;
  if (/^(rgb|rgba|hsl|hsla)\([#0-9a-z.,%/+\-\s]+\)$/i.test(raw)) return raw;
  if (/^(linear|radial|conic)-gradient\([#0-9a-z.,%/+\-\s]+\)$/i.test(raw)) return raw;
  return fallback;
}

function buildDecorBadgeStyle(color, fallback = "#9ca3af") {
  const safeColor = normalizeDecorColor(color, fallback) || fallback;
  if (isGradientDecorColor(safeColor)) {
    return `background:${safeColor};color:#fff;box-shadow:inset 0 0 0 1px rgba(255,255,255,.28);`;
  }
  const hex = normalizeHexColor(safeColor);
  if (hex) {
    return `background:${hexWithAlpha(hex, "22")};color:${hex};box-shadow:inset 0 0 0 1px ${hexWithAlpha(hex, "33")};`;
  }
  return `background:rgba(148,163,184,.14);color:${safeColor};box-shadow:inset 0 0 0 1px rgba(148,163,184,.24);`;
}

function buildDecorTextStyle(color) {
  const safeColor = normalizeDecorColor(color, "");
  if (!safeColor) return "";
  if (isGradientDecorColor(safeColor)) {
    return `display:inline-block;background:${safeColor};background-size:100% 100%;background-clip:text;-webkit-background-clip:text;color:transparent;-webkit-text-fill-color:transparent;`;
  }
  return `color:${safeColor};`;
}

function titleColoredNameHtml(label, color) {
  const safeLabel = escapeHtml(label || "未命名称号");
  const style = escapeHtml(buildDecorTextStyle(color));
  return `<span class="title-colored-name"${style ? ` style="${style}"` : ""}>${safeLabel}</span>`;
}

function titleColorBadgeHtml(label, color, className = "badge badge--normal") {
  const safeLabel = escapeHtml(label || "称号预览");
  const style = escapeHtml(buildDecorBadgeStyle(color));
  return `<span class="${className}" style="${style}">${safeLabel}</span>`;
}

function summarizeDecorColor(color) {
  const safeColor = normalizeDecorColor(color, "");
  if (!safeColor) return "默认";
  if (isGradientDecorColor(safeColor)) return "渐变 / 炫彩";
  return safeColor;
}

function toColorPickerHex(value, fallback = TITLE_COLOR_DEFAULT) {
  return normalizeHexColor(value) || fallback;
}

function clampGradientAngle(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 135;
  return Math.min(360, Math.max(0, Math.round(numeric)));
}

function buildLinearGradient(start, end, angle) {
  return `linear-gradient(${clampGradientAngle(angle)}deg, ${toColorPickerHex(start, TITLE_COLOR_DEFAULT)} 0%, ${toColorPickerHex(end, TITLE_GRADIENT_DEFAULT_END)} 100%)`;
}

function inferTitleColorMode(value) {
  const safeColor = normalizeDecorColor(value, "");
  if (!isGradientDecorColor(safeColor)) return "solid";
  if (TITLE_RAINBOW_PRESETS.some((item) => item.value === safeColor)) return "rainbow";
  return "gradient";
}

function extractGradientMeta(value) {
  const safeColor = normalizeDecorColor(value, "");
  const matches = safeColor.match(/#[0-9a-f]{3,8}/ig) || [];
  const angleMatch = safeColor.match(/(-?\d+(?:\.\d+)?)deg/i);
  return {
    start: toColorPickerHex(matches[0], TITLE_COLOR_DEFAULT),
    end: toColorPickerHex(matches[matches.length - 1], TITLE_GRADIENT_DEFAULT_END),
    angle: clampGradientAngle(angleMatch?.[1] || 135),
  };
}

function parseJsonInput(raw, fallback = {}) {
  const text = String(raw ?? "").trim();
  if (!text) return fallback;
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error(`JSON 解析失败: ${error.message}`);
  }
}

function parseIntegerListInput(raw) {
  return String(raw ?? "")
    .split(/[\s,，、;；|/]+/)
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item) && item > 0)
    .map((item) => Math.trunc(item));
}

function formatIntegerListInput(values) {
  return Array.isArray(values) ? values.map((item) => Number(item)).filter((item) => Number.isFinite(item) && item > 0).join(",") : "";
}

function parseShanghaiDate(value) {
  if (!value) return null;
  const normalized = typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(value)
    ? `${value}+00:00`
    : value;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatShanghaiDate(value) {
  const date = parseShanghaiDate(value);
  if (!date) return "未设置";
  return date.toLocaleString("zh-CN", { timeZone: "Asia/Shanghai", hour12: false });
}

function currentRelativePath() {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

function toSameOriginPath(path, fallback = "") {
  if (!path) return fallback;
  try {
    const url = new URL(path, window.location.origin);
    if (url.origin !== window.location.origin) {
      return fallback;
    }
    return `${url.pathname}${url.search}${url.hash}` || fallback;
  } catch {
    return fallback;
  }
}

function handleBackNavigation() {
  const currentPath = currentRelativePath();
  if (backState.returnTo && backState.returnTo !== currentPath) {
    window.location.href = backState.returnTo;
    return;
  }

  if (backState.referrerPath && backState.referrerPath !== currentPath) {
    if (window.history.length > 1) {
      window.history.back();
      return;
    }
    window.location.href = backState.referrerPath;
    return;
  }

  window.location.href = backState.fallbackPath;
}

function setupBackNavigation(defaultPath = DEFAULT_BACK_PATH) {
  backState.fallbackPath = toSameOriginPath(defaultPath, DEFAULT_BACK_PATH) || DEFAULT_BACK_PATH;
  backState.returnTo = toSameOriginPath(new URLSearchParams(window.location.search).get("return_to"), "");
  backState.referrerPath = toSameOriginPath(document.referrer, "");

  const currentPath = currentRelativePath();
  const hasPrevious = (backState.returnTo && backState.returnTo !== currentPath)
    || (backState.referrerPath && backState.referrerPath !== currentPath);
  const backButton = document.getElementById("page-back-button");
  if (backButton) {
    backButton.textContent = hasPrevious ? "返回上一级" : "返回管理台";
    backButton.addEventListener("click", handleBackNavigation);
  }

  if (tgBackButton) {
    tgBackButton.offClick?.(handleBackNavigation);
    tgBackButton.onClick(handleBackNavigation);
    tgBackButton.show();
  }
}

function adminStatus(text, tone = "info") {
  const node = $("admin-status");
  if (!node) return;
  node.textContent = text;
  node.dataset.tone = tone;
}

function adminSectionCards() {
  return [...document.querySelectorAll(".fold-card")];
}

function adminSectionMeta(card, index = 0) {
  const eyebrowNode = card.querySelector(".eyebrow");
  const eyebrow = (eyebrowNode?.textContent || "").trim();
  const key = (eyebrowNode?.dataset.sectionKey || "").trim();
  const title = (card.querySelector("h2")?.textContent || "").trim();
  card.id ||= `admin-section-${key.replace(/\s+/g, "-") || index + 1}`;
  return {
    card,
    key,
    eyebrow,
    title,
    label: ADMIN_SECTION_LABELS[key] || title || eyebrow || `Section ${index + 1}`,
  };
}

function adminSectionCount(key) {
  const bundle = state.bundle || {};
  if (key === "artifacts") return bundle.artifacts?.length || 0;
  if (key === "talismans") return bundle.talismans?.length || 0;
  if (key === "pills") return bundle.pills?.length || 0;
  if (key === "techniques") return bundle.techniques?.length || 0;
  if (key === "sects") return bundle.sects?.length || 0;
  if (key === "materials") return bundle.materials?.length || 0;
  if (key === "recipes") return bundle.recipes?.length || 0;
  if (key === "scenes") return bundle.scenes?.length || 0;
  if (key === "encounters") return bundle.encounters?.length || 0;
  if (key === "tasks") return bundle.tasks?.length || 0;
  if (key === "auctions") return bundle.auctions?.length || 0;
  if (key === "official shop") return bundle.official_shop?.length || 0;
  if (key === "grant") return bundle.upload_permissions?.length || 0;
  return null;
}

function ensureAdminNavigator() {
  if (document.querySelector("#admin-control-deck")) return;
  const shell = document.querySelector(".admin-shell");
  const hero = document.querySelector(".hero-card");
  if (!shell || !hero) return;
  const deck = document.createElement("section");
  deck.id = "admin-control-deck";
  deck.className = "card control-deck";
  deck.innerHTML = `
    <div class="control-head">
      <div>
        <p class="eyebrow">\u5feb\u6377\u5bfc\u822a</p>
        <h2>\u5feb\u901f\u5b9a\u4f4d\u8981\u4fee\u6539\u7684\u7248\u5757</h2>
        <p class="muted">\u652f\u6301\u641c\u7d22\u3001\u5e38\u7528\u7b5b\u9009\u3001\u4e00\u952e\u5c55\u5f00\u6216\u76f4\u8fbe\u533a\u5757\u3002</p>
      </div>
      <div class="control-actions">
        <button type="button" class="secondary" data-admin-core>\u53ea\u770b\u5e38\u7528</button>
        <button type="button" class="secondary" data-admin-open-all>\u5168\u90e8\u5c55\u5f00</button>
        <button type="button" class="secondary" data-admin-close-all>\u5168\u90e8\u6536\u8d77</button>
        <button type="button" class="secondary" data-admin-clear-filter>\u6e05\u7a7a\u7b5b\u9009</button>
      </div>
    </div>
    <label class="control-search">
      <span>\u641c\u7d22\u533a\u5757</span>
      <input id="admin-section-search" type="search" placeholder="\u4f8b\u5982\uff1a\u4efb\u52a1\u3001\u5546\u5e97\u3001\u6cd5\u5b9d\u3001\u6750\u6599">
    </label>
    <div id="admin-section-pills" class="control-pills"></div>
    <p id="admin-section-empty" class="muted control-empty hidden">\u6ca1\u6709\u627e\u5230\u5339\u914d\u7684\u7ba1\u7406\u533a\u5757\u3002</p>
  `;
  hero.insertAdjacentElement("afterend", deck);

  deck.querySelector("[data-admin-open-all]")?.addEventListener("click", () => toggleAdminSections(true));
  deck.querySelector("[data-admin-close-all]")?.addEventListener("click", () => toggleAdminSections(false));
  deck.querySelector("[data-admin-clear-filter]")?.addEventListener("click", () => {
    const input = $("admin-section-search");
    if (input) input.value = "";
    applyAdminSectionFilter("");
  });
  deck.querySelector("[data-admin-core]")?.addEventListener("click", () => {
    const input = $("admin-section-search");
    if (input) input.value = "";
    applyAdminSectionFilter("", ADMIN_CORE_SECTION_KEYS);
  });
  $("admin-section-search")?.addEventListener("input", (event) => {
    applyAdminSectionFilter(event.currentTarget?.value || "");
  });
}

function renderAdminNavigator() {
  ensureAdminNavigator();
  const pills = $("admin-section-pills");
  if (!pills) return;
  const rows = adminSectionCards().map((card, index) => adminSectionMeta(card, index));
  pills.innerHTML = rows.map((section) => {
    const count = adminSectionCount(section.key);
    return `
      <button type="button" class="nav-pill" data-admin-section="${escapeHtml(section.key)}">
        <span>${escapeHtml(section.label)}</span>
        ${count === null ? "" : `<span class="nav-pill-count">${escapeHtml(count)}</span>`}
      </button>
    `;
  }).join("");
  pills.querySelectorAll("[data-admin-section]").forEach((button) => {
    button.addEventListener("click", () => focusAdminSection(button.dataset.adminSection));
  });
  applyAdminSectionFilter($("admin-section-search")?.value || "");
}

function applyAdminSectionFilter(rawQuery = "", allowedKeys = null) {
  const query = String(rawQuery || "").trim().toLowerCase();
  const allowSet = allowedKeys instanceof Set ? allowedKeys : null;
  let visibleCount = 0;
  adminSectionCards().forEach((card, index) => {
    const section = adminSectionMeta(card, index);
    const haystack = `${section.eyebrow} ${section.title} ${section.label} ${section.key}`.toLowerCase();
    const matchedQuery = !query || haystack.includes(query);
    const matchedAllow = !allowSet || allowSet.has(section.key);
    const visible = matchedQuery && matchedAllow;
    card.classList.toggle("is-hidden-filter", !visible);
    if (visible) visibleCount += 1;
  });
  document.querySelectorAll("[data-admin-section]").forEach((button) => {
    const hiddenByFilter = allowSet ? !allowSet.has(button.dataset.adminSection || "") : false;
    button.classList.toggle("is-dimmed", hiddenByFilter);
  });
  $("admin-section-empty")?.classList.toggle("hidden", visibleCount > 0);
}

function toggleAdminSections(open) {
  adminSectionCards().forEach((card) => {
    if (!card.classList.contains("is-hidden-filter")) {
      card.open = open;
    }
  });
}

function focusAdminSection(key) {
  const rows = adminSectionCards().map((card, index) => adminSectionMeta(card, index));
  const target = rows.find((section) => section.key === key);
  if (!target) return;
  rows.forEach((section) => {
    if (!section.card.classList.contains("is-hidden-filter")) {
      section.card.open = section.key === key;
    }
  });
  document.querySelectorAll("[data-admin-section]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.adminSection === key);
  });
  target.card.scrollIntoView({ behavior: "smooth", block: "start" });
  pulseTarget(target.card);
}

function pulseTarget(node) {
  if (!node) return;
  node.classList.remove("jump-highlight");
  void node.offsetWidth;
  node.classList.add("jump-highlight");
  window.setTimeout(() => {
    node.classList.remove("jump-highlight");
  }, 1500);
}

function syncSelectedPlayerUI(text = null) {
  const pill = $("selected-player-pill");
  const button = $("jump-player-editor");
  const hasSelection = Boolean(state.selectedPlayerTg);
  if (pill) {
    pill.textContent = text || (hasSelection ? `正在编辑 TG ${state.selectedPlayerTg}` : "未选中角色");
  }
  if (button) {
    button.disabled = !hasSelection;
    button.textContent = hasSelection ? "回到角色编辑" : "跳到角色编辑";
  }
}

function highlightSelectedPlayerResult() {
  document.querySelectorAll("#player-search-results [data-tg]").forEach((el) => {
    el.classList.toggle("is-selected", Number(el.dataset.tg) === Number(state.selectedPlayerTg || 0));
  });
}

function revealPlayerEditor(smooth = true) {
  const panel = $("player-edit-panel");
  if (!panel) return;
  const playerCard = adminSectionCards()
    .map((card, index) => adminSectionMeta(card, index))
    .find((section) => section.key === "players");
  if (playerCard?.card?.classList.contains("is-hidden-filter")) {
    const input = $("admin-section-search");
    if (input) input.value = "";
    applyAdminSectionFilter("");
  }
  focusAdminSection("players");
  panel.classList.remove("hidden");
  window.requestAnimationFrame(() => {
    panel.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" });
    pulseTarget(panel);
  });
}

function touch(tone = "success") {
  if (!tg?.HapticFeedback) return;
  if (tone === "error") return tg.HapticFeedback.notificationOccurred("error");
  if (tone === "warning") return tg.HapticFeedback.notificationOccurred("warning");
  tg.HapticFeedback.notificationOccurred("success");
}

const TG_POPUP_TITLE_LIMIT = 64;
const TG_POPUP_MESSAGE_LIMIT = 256;
const TG_POPUP_FALLBACK_MESSAGE = {
  success: "操作已完成。",
  warning: "操作已完成，请留意页面提示。",
  error: "操作失败，请稍后再试。",
};

function safeTelegramPopupText(value, limit, fallback = "") {
  const text = String(value ?? "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
  const normalized = text || fallback;
  if (!normalized) return "";
  if (normalized.length <= limit) return normalized;
  return `${normalized.slice(0, Math.max(limit - 1, 1)).trimEnd()}…`;
}

async function popup(title, message, tone = "success") {
  touch(tone);
  if (tg?.showPopup) {
    try {
      await tg.showPopup({
        title: safeTelegramPopupText(title, TG_POPUP_TITLE_LIMIT, "提示"),
        message: safeTelegramPopupText(
          message,
          TG_POPUP_MESSAGE_LIMIT,
          TG_POPUP_FALLBACK_MESSAGE[tone] || TG_POPUP_FALLBACK_MESSAGE.success,
        ),
        buttons: [{ type: "close", text: "知道了" }],
      });
      return;
    } catch (error) {
      console.warn("Telegram popup failed, fallback to alert", error);
    }
  }
  window.alert(`${title}\n\n${message}`);
}

function adminHeaders(withJson = true) {
  const headers = {};
  if (withJson) headers["Content-Type"] = "application/json";
  if (state.token) headers["x-admin-token"] = state.token;
  if (state.initData) headers["x-telegram-init-data"] = state.initData;
  return headers;
}

async function readPayload(response) {
  const raw = await response.text();
  if (!raw) return { code: response.ok ? 200 : response.status, data: null };
  try {
    return JSON.parse(raw);
  } catch {
    throw new Error(raw.trim() || "内部服务异常");
  }
}

async function request(method, path, body = null) {
  const options = { method, headers: adminHeaders(body !== null) };
  if (body !== null) options.body = JSON.stringify(body);
  const response = await fetch(path, options);
  const payload = await readPayload(response);
  if (!response.ok || payload.code !== 200) {
    throw new Error(payload.detail || payload.message || "请求失败");
  }
  return payload.data;
}

async function uploadImage(file, folder) {
  if (!file) throw new Error("请先选择图片文件");
  const formData = new FormData();
  formData.append("folder", folder);
  formData.append("file", file);
  const response = await fetch("/plugins/xiuxian/admin-api/upload-image", {
    method: "POST",
    headers: adminHeaders(false),
    body: formData,
  });
  const payload = await readPayload(response);
  if (!response.ok || payload.code !== 200) {
    throw new Error(payload.detail || payload.message || "上传失败");
  }
  return payload.data;
}

function normalizeAdminUrlValue(value) {
  const raw = String(value ?? "").trim();
  if (!raw) return "";
  if (/^[a-z][a-z0-9+.-]*:/i.test(raw)) return raw;
  if (raw.startsWith("//")) return `${window.location.protocol}${raw}`;
  if (raw.startsWith("/") || raw.startsWith("./") || raw.startsWith("../")) {
    try {
      return new URL(raw, window.location.origin).href;
    } catch {
      return raw;
    }
  }
  return raw;
}

function setAdminInputValue(target, value) {
  const node = typeof target === "string" ? $(target) : target;
  if (!node) return "";
  const nextValue = node.matches?.('input[type="url"]')
    ? normalizeAdminUrlValue(value)
    : String(value ?? "");
  node.value = nextValue;
  return nextValue;
}

function setOptions(node, rows, current = "", placeholder = "请选择") {
  if (!node) return;
  node.innerHTML = "";
  if (placeholder !== null) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = placeholder;
    node.appendChild(opt);
  }
  for (const row of rows) {
    const opt = document.createElement("option");
    opt.value = row.value;
    opt.textContent = row.label;
    if (String(current) === String(row.value)) opt.selected = true;
    node.appendChild(opt);
  }
}

function qualityRows() {
  return QUALITY_OPTIONS.map((label) => ({ value: label, label }));
}

function realmRows() {
  return [{ value: "", label: "无限制" }, ...REALM_OPTIONS.map((label) => ({ value: label, label }))];
}

function itemRows(kind, query = "") {
  const bundle = state.bundle || {};
  const key = kind === "artifact"
    ? "artifacts"
    : kind === "pill"
      ? "pills"
      : kind === "talisman"
        ? "talismans"
        : kind === "material"
          ? "materials"
          : kind === "recipe"
            ? "recipes"
            : kind === "technique"
              ? "techniques"
              : "";
  const rows = bundle[key] || [];
  const keyword = String(query || "").trim().toLowerCase();
  return rows.map((item) => {
    const data = item.material || item;
    return { value: data.id, label: `${data.id} · ${data.name}` };
  }).filter((row) => {
    if (!keyword) return true;
    return String(row.value).includes(keyword) || row.label.toLowerCase().includes(keyword);
  });
}

function sectRows() {
  return (state.bundle?.sects || []).map((row) => ({ value: row.id, label: `${row.id} · ${row.name}` }));
}

function materialRows() {
  return (state.bundle?.materials || []).map((row) => ({ value: row.id, label: `${row.id} · ${row.name}` }));
}

function grantUserRows(items = []) {
  return items.map((item) => {
    const extras = [`TG ${item.tg}`];
    if (item.username) extras.push(`@${item.username}`);
    if (item.emby_account?.name) extras.push(item.emby_account.name);
    if (item.emby_account?.embyid) extras.push(`Emby ${item.emby_account.embyid}`);
    return {
      value: item.tg,
      label: `${playerDisplayName(item, item.tg)} · ${extras.join(" · ")}`,
    };
  });
}

function findGrantUserByTg(tg) {
  return (state.grantForm?.userOptions || []).find((item) => Number(item.tg) === Number(tg)) || null;
}

function syncGrantItemSearchTip(rows = null) {
  const tip = $("grant-item-search-tip");
  if (!tip) return;
  const keyword = String($("grant-item-search")?.value || "").trim();
  const matches = Array.isArray(rows) ? rows : itemRows($("grant-kind")?.value || "artifact", keyword);
  if (!keyword) {
    tip.textContent = `当前共 ${matches.length} 件可发放物品。`;
    return;
  }
  tip.textContent = matches.length ? `已筛出 ${matches.length} 件匹配物品。` : "没有匹配的物品。";
}

function syncGrantItemOptions() {
  const rows = itemRows($("grant-kind")?.value || "artifact", $("grant-item-search")?.value || "");
  setOptions($("grant-ref-id"), rows, $("grant-ref-id")?.value);
  syncGrantItemSearchTip(rows);
}

function syncPlayerBatchResourceForm() {
  const kindNode = $("player-batch-kind");
  const refNode = $("player-batch-ref-id");
  const quantityNode = $("player-batch-quantity");
  const equipNode = $("player-batch-equip");
  if (!kindNode || !refNode) return;
  const kind = kindNode.value || "artifact";
  const rows = itemRows(kind);
  setOptions(refNode, rows, refNode.value);
  const supportsQuantity = ["artifact", "pill", "talisman", "material"].includes(kind);
  const supportsEquip = ["title", "technique"].includes(kind);
  if (quantityNode) {
    quantityNode.disabled = !supportsQuantity;
    if (!supportsQuantity) quantityNode.value = "1";
  }
  if (equipNode) {
    equipNode.disabled = !supportsEquip;
    if (!supportsEquip) equipNode.checked = false;
  }
}

function renderPlayerBatchResourceSummary(result = null) {
  const root = $("player-batch-resource-summary");
  if (!root) return;
  if (!result) {
    root.innerHTML = `<article class="stack-item"><strong>尚未执行批量操作</strong><p>支持全体发放或扣除。扣除时，未持有该物品的玩家会自动跳过，不会报错中断。</p></article>`;
    return;
  }
  const failedRows = Array.isArray(result.failed_rows) ? result.failed_rows : [];
  const skippedTgs = Array.isArray(result.skipped_tgs) ? result.skipped_tgs : [];
  const actionLabel = result.operation === "deduct" ? "扣除" : "发放";
  root.innerHTML = `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>最近一次批量${escapeHtml(actionLabel)}</strong>
        <span class="badge">${escapeHtml(result.item_kind || "item")} : ${escapeHtml(result.item_ref_id || 0)}</span>
      </div>
      <p>数量 ${escapeHtml(result.quantity || 1)}，已处理 ${escapeHtml(result.processed_count || 0)} 名玩家。</p>
      <p>成功 ${escapeHtml(result.success_count || 0)} 人，跳过 ${escapeHtml(result.skipped_count || 0)} 人，失败 ${escapeHtml(result.failed_count || 0)} 人。</p>
      ${skippedTgs.length ? `<p>已跳过 TG：${escapeHtml(skippedTgs.join("、"))}</p>` : `<p class="muted">本次没有跳过玩家。</p>`}
      ${failedRows.length ? `<p>失败样本：${escapeHtml(failedRows.map((row) => `TG ${row.tg}(${row.reason})`).join("；"))}</p>` : `<p class="muted">本次没有失败样本。</p>`}
    </article>
  `;
}

function syncGrantUserSearchTip() {
  const tip = $("grant-user-search-tip");
  if (!tip) return;
  const query = String($("grant-user-search")?.value || "").trim();
  const targetTg = Number($("grant-tg")?.value || 0);
  if (targetTg > 0) {
    const matched = findGrantUserByTg(targetTg);
    tip.textContent = matched
      ? `当前目标：${playerDisplayName(matched, targetTg)}（TG ${targetTg}）。`
      : `当前目标 TG ${targetTg}。`;
    return;
  }
  if (!query) {
    tip.textContent = "支持按 TG 昵称、@username、Emby 账号名或 TG ID 搜索，也可直接手填 TG ID。";
    return;
  }
  tip.textContent = (state.grantForm?.userOptions || []).length
    ? "从“匹配用户”中选择目标后，会自动写入 TG ID。"
    : "未找到匹配用户，可继续修改关键词或直接手填 TG ID。";
}

function syncGrantUserMatches() {
  const rows = grantUserRows(state.grantForm?.userOptions || []);
  const placeholder = state.grantForm?.userQuery
    ? (rows.length ? "请选择匹配用户" : "未找到匹配用户")
    : "先输入关键词搜索";
  setOptions($("grant-user-match"), rows, $("grant-tg")?.value || $("grant-user-match")?.value, placeholder);
  syncGrantUserSearchTip();
}

async function fetchGrantUserMatches(query, seq = state.grantForm.userSearchSeq) {
  const keyword = String(query || "").trim();
  state.grantForm.userQuery = keyword;
  if (!keyword) {
    state.grantForm.userOptions = [];
    syncGrantUserMatches();
    return;
  }
  try {
    const data = await request("GET", `/plugins/xiuxian/admin-api/players?q=${encodeURIComponent(keyword)}&page=1&page_size=${GRANT_USER_SEARCH_PAGE_SIZE}`);
    if (seq !== state.grantForm.userSearchSeq) return;
    state.grantForm.userOptions = Array.isArray(data?.items) ? data.items : [];
    syncGrantUserMatches();
    const numericTg = /^\d+$/.test(keyword) ? Number(keyword) : 0;
    if (numericTg > 0 && findGrantUserByTg(numericTg)) {
      $("grant-user-match").value = String(numericTg);
      $("grant-tg").value = String(numericTg);
      syncGrantUserSearchTip();
    }
  } catch (error) {
    if (seq !== state.grantForm.userSearchSeq) return;
    state.grantForm.userOptions = [];
    syncGrantUserMatches();
    const tip = $("grant-user-search-tip");
    if (tip) tip.textContent = "用户搜索失败，可直接手填 TG ID。";
    console.warn("grant user search failed", error);
  }
}

function queueGrantUserSearch() {
  const keyword = String($("grant-user-search")?.value || "").trim();
  state.grantForm.userQuery = keyword;
  state.grantForm.userSearchSeq = Number(state.grantForm.userSearchSeq || 0) + 1;
  const seq = state.grantForm.userSearchSeq;
  if (state.grantForm.userSearchTimer) {
    window.clearTimeout(state.grantForm.userSearchTimer);
    state.grantForm.userSearchTimer = null;
  }
  if (/^\d+$/.test(keyword) && Number(keyword) > 0 && $("grant-tg")) {
    $("grant-tg").value = keyword;
  }
  if (!keyword) {
    state.grantForm.userOptions = [];
    syncGrantUserMatches();
    return;
  }
  if (!/^\d+$/.test(keyword) && keyword.length < 2) {
    state.grantForm.userOptions = [];
    syncGrantUserMatches();
    return;
  }
  syncGrantUserSearchTip();
  state.grantForm.userSearchTimer = window.setTimeout(() => {
    fetchGrantUserMatches(keyword, seq);
  }, GRANT_USER_SEARCH_DEBOUNCE_MS);
}

function syncGrantTargetTg() {
  const tg = Number($("grant-tg")?.value || 0);
  const matchNode = $("grant-user-match");
  if (matchNode) {
    const hasMatch = [...matchNode.options].some((opt) => Number(opt.value || 0) === tg);
    matchNode.value = hasMatch && tg > 0 ? String(tg) : "";
  }
  syncGrantUserSearchTip();
}

function applyGrantTargetPlayer(profile = {}) {
  const tg = Number(profile?.tg || 0);
  if (!tg) return;
  if ($("grant-tg")) $("grant-tg").value = String(tg);
  if ($("grant-user-search")) $("grant-user-search").value = playerDisplayName(profile, tg);
  state.grantForm.userOptions = [profile];
  state.grantForm.userQuery = playerDisplayName(profile, tg);
  syncGrantUserMatches();
}

function ensureAffixFields(prefix, includeMerit = false, includeCultivation = false) {
  const form = $(`${prefix}-form`);
  if (!form || form.dataset.affixReady === "1") return;
  const anchor = form.querySelector(".form-actions");
  if (!anchor) return;
  for (const [key, label] of ITEM_AFFIX_FIELDS) {
    if ($(`${prefix}-${key}`)) continue;
    const node = document.createElement("label");
    node.innerHTML = `${label}词条<input id="${prefix}-${key}" type="number" value="0">`;
    form.insertBefore(node, anchor);
  }
  if (includeCultivation && !$(`${prefix}-cultivation`)) {
    const node = document.createElement("label");
    node.innerHTML = `修炼词条<input id="${prefix}-cultivation" type="number" value="0">`;
    form.insertBefore(node, anchor);
  }
  form.dataset.affixReady = "1";
}

function affixPayload(prefix) {
  return {
    attack_bonus: Number($(`${prefix}-attack`)?.value || 0),
    defense_bonus: Number($(`${prefix}-defense`)?.value || 0),
    bone_bonus: Number($(`${prefix}-bone`)?.value || 0),
    comprehension_bonus: Number($(`${prefix}-comprehension`)?.value || 0),
    divine_sense_bonus: Number($(`${prefix}-divine-sense`)?.value || 0),
    fortune_bonus: Number($(`${prefix}-fortune`)?.value || 0),
    qi_blood_bonus: Number($(`${prefix}-qi-blood`)?.value || 0),
    true_yuan_bonus: Number($(`${prefix}-true-yuan`)?.value || 0),
    body_movement_bonus: Number($(`${prefix}-body-movement`)?.value || 0),
  };
}

function affixSummary(item) {
  const rows = [];
  if (Number(item.attack_bonus || 0)) rows.push(`攻击 ${item.attack_bonus}`);
  if (Number(item.defense_bonus || 0)) rows.push(`防御 ${item.defense_bonus}`);
  if (Number(item.bone_bonus || 0)) rows.push(`根骨 ${item.bone_bonus}`);
  if (Number(item.comprehension_bonus || 0)) rows.push(`悟性 ${item.comprehension_bonus}`);
  if (Number(item.divine_sense_bonus || 0)) rows.push(`神识 ${item.divine_sense_bonus}`);
  if (Number(item.fortune_bonus || 0)) rows.push(`机缘 ${item.fortune_bonus}`);
  if (Number(item.qi_blood_bonus || 0)) rows.push(`气血 ${item.qi_blood_bonus}`);
  if (Number(item.true_yuan_bonus || 0)) rows.push(`真元 ${item.true_yuan_bonus}`);
  if (Number(item.body_movement_bonus || 0)) rows.push(`身法 ${item.body_movement_bonus}`);
  if (Number(item.cultivation_bonus || 0)) rows.push(`修炼 ${item.cultivation_bonus}`);
  if (Number(item.duel_rate_bonus || 0)) rows.push(`斗法 ${item.duel_rate_bonus}%`);
  if (Number(item.breakthrough_bonus || 0)) rows.push(`突破 ${item.breakthrough_bonus}`);
  return rows.join(" · ") || "暂无额外词条";
}

function hydrateAdminForms() {
  setOptions($("artifact-type"), [
    { value: "battle", label: "战斗法宝" },
    { value: "support", label: "辅助法宝" },
  ], $("artifact-type")?.value || "battle", null);
  setOptions(
    $("artifact-set-id"),
    [{ value: "", label: "无套装" }, ...((state.bundle?.artifact_sets || []).map((item) => ({ value: item.id, label: `${item.id} · ${item.name}` })))],
    $("artifact-set-id")?.value || "",
    null,
  );
  setOptions($("pill-type"), PILL_TYPES.map((item) => ({ value: item.value, label: item.label })), $("pill-type")?.value || "foundation", null);
  ensureAffixFields("artifact", true, true);
  ensureAffixFields("pill");
  ensureAffixFields("talisman");
  ensureAffixFields("technique", false, true);
}

function artifactSubmitButton() {
  return document.querySelector("#artifact-form button[type='submit']");
}

function collectArtifactPayload() {
  return {
    name: $("artifact-name")?.value.trim() || "",
    rarity: $("artifact-rarity")?.value || "凡品",
    artifact_type: $("artifact-type")?.value || "battle",
    artifact_role: $("artifact-role")?.value || "battle",
    equip_slot: $("artifact-slot")?.value || "weapon",
    artifact_set_id: Number($("artifact-set-id")?.value || 0) || null,
    unique_item: Boolean($("artifact-unique")?.checked),
    image_url: $("artifact-image")?.value.trim() || "",
    description: $("artifact-description")?.value.trim() || "",
    ...affixPayload("artifact"),
    duel_rate_bonus: Number($("artifact-duel")?.value || 0),
    cultivation_bonus: Number($("artifact-cultivation")?.value || 0),
    combat_config: parseJsonInput($("artifact-combat-config")?.value || "{}", {}),
    min_realm_stage: $("artifact-stage")?.value || null,
    min_realm_layer: Number($("artifact-layer")?.value || 1),
    enabled: Boolean($("artifact-enabled")?.checked),
  };
}

function resetArtifactForm() {
  setAdminInputValue("artifact-id", "");
  setAdminInputValue("artifact-name", "");
  setAdminInputValue("artifact-image", "");
  setAdminInputValue("artifact-description", "");
  setAdminInputValue("artifact-attack", 0);
  setAdminInputValue("artifact-defense", 0);
  setAdminInputValue("artifact-bone", 0);
  setAdminInputValue("artifact-comprehension", 0);
  setAdminInputValue("artifact-divine-sense", 0);
  setAdminInputValue("artifact-fortune", 0);
  setAdminInputValue("artifact-qi-blood", 0);
  setAdminInputValue("artifact-true-yuan", 0);
  setAdminInputValue("artifact-body-movement", 0);
  setAdminInputValue("artifact-duel", 0);
  setAdminInputValue("artifact-cultivation", 0);
  setAdminInputValue("artifact-combat-config", "");
  setAdminInputValue("artifact-layer", 1);
  if ($("artifact-rarity")) $("artifact-rarity").value = "凡品";
  if ($("artifact-type")) $("artifact-type").value = "battle";
  if ($("artifact-role")) $("artifact-role").value = "battle";
  if ($("artifact-slot")) $("artifact-slot").value = "weapon";
  if ($("artifact-stage")) $("artifact-stage").value = "";
  if ($("artifact-set-id")) $("artifact-set-id").value = "";
  if ($("artifact-unique")) $("artifact-unique").checked = false;
  if ($("artifact-enabled")) $("artifact-enabled").checked = true;
  const submit = artifactSubmitButton();
  if (submit) submit.textContent = "新增法宝";
}

function loadArtifactForm(item = {}) {
  setAdminInputValue("artifact-id", item.id || "");
  setAdminInputValue("artifact-name", item.name || "");
  setAdminInputValue("artifact-image", item.image_url || "");
  setAdminInputValue("artifact-description", item.description || "");
  setAdminInputValue("artifact-attack", item.attack_bonus || 0);
  setAdminInputValue("artifact-defense", item.defense_bonus || 0);
  setAdminInputValue("artifact-bone", item.bone_bonus || 0);
  setAdminInputValue("artifact-comprehension", item.comprehension_bonus || 0);
  setAdminInputValue("artifact-divine-sense", item.divine_sense_bonus || 0);
  setAdminInputValue("artifact-fortune", item.fortune_bonus || 0);
  setAdminInputValue("artifact-qi-blood", item.qi_blood_bonus || 0);
  setAdminInputValue("artifact-true-yuan", item.true_yuan_bonus || 0);
  setAdminInputValue("artifact-body-movement", item.body_movement_bonus || 0);
  setAdminInputValue("artifact-duel", item.duel_rate_bonus || 0);
  setAdminInputValue("artifact-cultivation", item.cultivation_bonus || 0);
  setAdminInputValue(
    "artifact-combat-config",
    item.combat_config && Object.keys(item.combat_config || {}).length ? JSON.stringify(item.combat_config, null, 2) : "",
  );
  setAdminInputValue("artifact-layer", item.min_realm_layer || 1);
  if ($("artifact-rarity")) $("artifact-rarity").value = item.rarity || "凡品";
  if ($("artifact-type")) $("artifact-type").value = item.artifact_type || "battle";
  if ($("artifact-role")) $("artifact-role").value = item.artifact_role || "battle";
  if ($("artifact-slot")) $("artifact-slot").value = item.equip_slot || "weapon";
  if ($("artifact-stage")) $("artifact-stage").value = item.min_realm_stage || "";
  if ($("artifact-set-id")) $("artifact-set-id").value = item.artifact_set_id || "";
  if ($("artifact-unique")) $("artifact-unique").checked = Boolean(item.unique_item);
  if ($("artifact-enabled")) $("artifact-enabled").checked = item.enabled !== false;
  const submit = artifactSubmitButton();
  if (submit) submit.textContent = "保存法宝";
}

function bindUploadButtons() {
  document.querySelectorAll("[data-upload-file]").forEach((button) => {
    button.onclick = async () => {
      const file = $(button.dataset.uploadFile)?.files?.[0];
      const target = $(button.dataset.uploadTarget);
      try {
        const payload = await uploadImage(file, button.dataset.uploadFolder || "admin");
        setAdminInputValue(target, payload.url || payload.relative_url || "");
        await popup("上传成功", "图片地址已经自动写回表单。");
      } catch (error) {
        await popup("上传失败", String(error.message || error), "error");
      }
    };
  });
}

function updatePillEffectLabel() {
  const type = $("pill-type")?.value || "foundation";
  const row = PILL_TYPES.find((item) => item.value === type);
  const label = $("pill-effect")?.closest("label");
  if (label && row) {
    label.childNodes[0].textContent = row.effect;
  }
}

function createBuilderRow(html) {
  const wrapper = document.createElement("div");
  wrapper.className = "builder-row";
  wrapper.innerHTML = `${html}<button type="button" class="ghost" data-remove-row>删除</button>`;
  wrapper.querySelector("[data-remove-row]").onclick = () => wrapper.remove();
  return wrapper;
}

function addSectRoleRow(data = {}) {
  const rows = $("sect-role-rows");
  if (!rows) return;
  const wrapper = createBuilderRow(`
    <label>职位
      <select data-role-key>${ROLE_PRESETS.map(([value, label]) => `<option value="${value}" ${String(data.role_key || value) === value ? "selected" : ""}>${label}</option>`).join("")}</select>
    </label>
    <label>称呼<input data-role-name type="text" value="${escapeHtml(data.role_name || "")}" placeholder="职位名称"></label>
    <label>攻击<input data-role-attack type="number" value="${escapeHtml(data.attack_bonus || 0)}"></label>
    <label>防御<input data-role-defense type="number" value="${escapeHtml(data.defense_bonus || 0)}"></label>
    <label>斗法%<input data-role-duel type="number" value="${escapeHtml(data.duel_rate_bonus || 0)}"></label>
    <label>修炼<input data-role-cultivation type="number" value="${escapeHtml(data.cultivation_bonus || 0)}"></label>
    <label>月俸<input data-role-salary type="number" value="${escapeHtml(data.monthly_salary || 0)}"></label>
    <label class="inline-check"><input data-role-publish type="checkbox" ${data.can_publish_tasks ? "checked" : ""}>可发宗门任务</label>
  `);
  const select = wrapper.querySelector("[data-role-key]");
  const name = wrapper.querySelector("[data-role-name]");
  const syncRoleName = () => {
    if (!name.dataset.touched) {
      name.value = ROLE_PRESETS.find(([value]) => value === select.value)?.[1] || name.value;
    }
  };
  name.addEventListener("input", () => { name.dataset.touched = "1"; });
  select.addEventListener("change", syncRoleName);
  syncRoleName();
  rows.appendChild(wrapper);
}

function addRecipeIngredientRow(data = {}) {
  const rows = $("recipe-ingredient-rows");
  if (!rows) return;
  const options = materialRows().map((row) => `<option value="${row.value}" ${String(data.material_id || "") === String(row.value) ? "selected" : ""}>${escapeHtml(row.label)}</option>`).join("");
  rows.appendChild(createBuilderRow(`
    <label>材料
      <select data-ingredient-id>${options}</select>
    </label>
    <label>数量
      <input data-ingredient-quantity type="number" min="1" value="${escapeHtml(data.quantity || 1)}">
    </label>
  `));
}

function addSceneEventRow(data = {}) {
  const rows = $("scene-event-rows");
  if (!rows) return;
  const typeOptions = SCENE_EVENT_TYPES.map(([value, label]) => `<option value="${value}" ${(data.event_type || "encounter") === value ? "selected" : ""}>${escapeHtml(label)}</option>`).join("");
  const wrapper = createBuilderRow(`
    <label>事件名称
      <input data-scene-event-name type="text" value="${escapeHtml(data.name || "")}" placeholder="例如：残碑拓影">
    </label>
    <label>事件类型
      <select data-scene-event-type>${typeOptions}</select>
    </label>
    <label>权重
      <input data-scene-event-weight type="number" min="1" value="${escapeHtml(data.weight || 1)}">
    </label>
    <label>灵石奖励最小值
      <input data-scene-stone-bonus-min type="number" min="0" value="${escapeHtml(data.stone_bonus_min || 0)}">
    </label>
    <label>灵石奖励最大值
      <input data-scene-stone-bonus-max type="number" min="0" value="${escapeHtml(data.stone_bonus_max || 0)}">
    </label>
    <label>灵石损失最小值
      <input data-scene-stone-loss-min type="number" min="0" value="${escapeHtml(data.stone_loss_min || 0)}">
    </label>
    <label>灵石损失最大值
      <input data-scene-stone-loss-max type="number" min="0" value="${escapeHtml(data.stone_loss_max || 0)}">
    </label>
    <label>额外奖励类型
      <select data-scene-bonus-kind>
        <option value="" ${(data.bonus_reward_kind || "") === "" ? "selected" : ""}>无</option>
        <option value="material" ${(data.bonus_reward_kind || "") === "material" ? "selected" : ""}>材料</option>
        <option value="artifact" ${(data.bonus_reward_kind || "") === "artifact" ? "selected" : ""}>法宝</option>
        <option value="pill" ${(data.bonus_reward_kind || "") === "pill" ? "selected" : ""}>丹药</option>
        <option value="talisman" ${(data.bonus_reward_kind || "") === "talisman" ? "selected" : ""}>符箓</option>
      </select>
    </label>
    <label>额外奖励
      <select data-scene-bonus-ref></select>
    </label>
    <label>额外奖励最小数量
      <input data-scene-bonus-min type="number" min="1" value="${escapeHtml(data.bonus_quantity_min || 1)}">
    </label>
    <label>额外奖励最大数量
      <input data-scene-bonus-max type="number" min="1" value="${escapeHtml(data.bonus_quantity_max || 1)}">
    </label>
    <label>额外奖励触发率（%）
      <input data-scene-bonus-chance type="number" min="0" max="100" value="${escapeHtml(data.bonus_chance || 0)}">
    </label>
    <label class="wide-field">事件描述
      <textarea data-scene-event-description rows="2" placeholder="例如：石壁上浮现旧日符纹，你急忙拓下一页残纸。">${escapeHtml(data.description || "")}</textarea>
    </label>
  `);
  const kindNode = wrapper.querySelector("[data-scene-bonus-kind]");
  const refNode = wrapper.querySelector("[data-scene-bonus-ref]");
  const sync = () => setOptions(refNode, itemRows(kindNode.value || "material"), data.bonus_reward_ref_id, "无");
  kindNode.addEventListener("change", sync);
  sync();
  rows.appendChild(wrapper);
}

function addSceneDropRow(data = {}) {
  const rows = $("scene-drop-rows");
  if (!rows) return;
  const rewardKind = data.reward_kind || "material";
  const wrapper = createBuilderRow(`
    <label>掉落类型
      <select data-drop-kind>
        <option value="material" ${rewardKind === "material" ? "selected" : ""}>材料</option>
        <option value="artifact" ${rewardKind === "artifact" ? "selected" : ""}>法宝</option>
        <option value="pill" ${rewardKind === "pill" ? "selected" : ""}>丹药</option>
        <option value="talisman" ${rewardKind === "talisman" ? "selected" : ""}>符箓</option>
      </select>
    </label>
    <label>对应物品
      <select data-drop-ref></select>
    </label>
    <label>最小数量<input data-drop-min type="number" min="1" value="${escapeHtml(data.quantity_min || 1)}"></label>
    <label>最大数量<input data-drop-max type="number" min="1" value="${escapeHtml(data.quantity_max || 1)}"></label>
    <label>权重<input data-drop-weight type="number" min="1" value="${escapeHtml(data.weight || 1)}"></label>
    <label>额外灵石<input data-drop-stone type="number" min="0" value="${escapeHtml(data.stone_reward || 0)}"></label>
    <label class="wide-field">触发文本<input data-drop-event type="text" value="${escapeHtml(data.event_text || "")}" placeholder="例如：你在废墟深处捡到一块玄铁"></label>
  `);
  const kindNode = wrapper.querySelector("[data-drop-kind]");
  const refNode = wrapper.querySelector("[data-drop-ref]");
  const sync = () => setOptions(refNode, itemRows(kindNode.value), data.reward_ref_id, "无");
  kindNode.addEventListener("change", sync);
  sync();
  rows.appendChild(wrapper);
}

function addGamblingPoolRow(data = {}) {
  const rows = $("setting-gambling-pool-rows");
  if (!rows) return;
  const itemKind = String(data.item_kind || "material");
  const gamblingWeight = data.gambling_weight ?? data.base_weight ?? 1;
  const fishingWeight = data.fishing_weight ?? data.base_weight ?? 1;
  const gamblingEnabled = data.gambling_enabled ?? data.enabled ?? true;
  const fishingEnabled = data.fishing_enabled ?? data.enabled ?? true;
  const wrapper = createBuilderRow(`
    <div class="builder-grid builder-grid--wide">
      <label>奖励类型
        <select data-gambling-kind>
          ${GAMBLING_ITEM_KIND_OPTIONS.map((item) => `<option value="${item.value}" ${itemKind === item.value ? "selected" : ""}>${escapeHtml(item.label)}</option>`).join("")}
        </select>
      </label>
      <label>物品搜索
        <input data-gambling-search type="search" value="${escapeHtml(data.item_name || "")}" placeholder="输入名称或 ID 过滤物品">
      </label>
      <label>奖励物品
        <select data-gambling-ref></select>
      </label>
      <label>最小数量
        <input data-gambling-min type="number" min="1" value="${escapeHtml(data.quantity_min || 1)}">
      </label>
      <label>最大数量
        <input data-gambling-max type="number" min="1" value="${escapeHtml(data.quantity_max || data.quantity_min || 1)}">
      </label>
      <label>奇石权重
        <input data-gambling-weight type="number" min="0" step="0.01" value="${escapeHtml(gamblingWeight)}">
      </label>
      <label>钓鱼权重
        <input data-fishing-weight type="number" min="0" step="0.01" value="${escapeHtml(fishingWeight)}">
      </label>
      <label class="inline-check">
        <input data-gambling-enabled type="checkbox" ${gamblingEnabled === false ? "" : "checked"}>
        进入奇石奖池
      </label>
      <label class="inline-check">
        <input data-fishing-enabled type="checkbox" ${fishingEnabled === false ? "" : "checked"}>
        进入钓鱼奖池
      </label>
    </div>
    <div class="builder-chip-line">
      <span class="builder-chip">共享同一物品池</span>
      <span class="builder-chip">奇石 / 钓鱼独立权重</span>
      <span class="builder-chip">保存后即时生效</span>
    </div>
  `);
  const kindNode = wrapper.querySelector("[data-gambling-kind]");
  const searchNode = wrapper.querySelector("[data-gambling-search]");
  const refNode = wrapper.querySelector("[data-gambling-ref]");
  const sync = (selected = null) => {
    const rowsForKind = itemRows(kindNode.value || "material", searchNode?.value || "");
    setOptions(refNode, rowsForKind, selected ?? data.item_ref_id ?? "", "请选择物品");
    refNode.disabled = !rowsForKind.length;
  };
  kindNode.addEventListener("change", () => sync(""));
  searchNode?.addEventListener("input", () => sync(refNode?.value || ""));
  sync(data.item_ref_id ? String(data.item_ref_id) : "");
  rows.appendChild(wrapper);
}

function ensureSettingRuleRows() {
  const rootRows = $("setting-root-quality-rows");
  if (rootRows && rootRows.dataset.ready !== "1") {
    rootRows.innerHTML = "";
    ROOT_QUALITY_RULES.forEach(({ key, label }) => {
      const row = document.createElement("div");
      row.className = "builder-row";
      row.innerHTML = `
        <label>品质
          <input type="text" value="${escapeHtml(label)}" disabled>
        </label>
        <label>修炼倍率
          <input data-root-quality="${escapeHtml(key)}" data-root-rule="cultivation_rate" type="number" min="0.1" step="0.01" value="${escapeHtml(DEFAULT_ROOT_QUALITY_RULES[key].cultivation_rate)}">
        </label>
        <label>突破加成
          <input data-root-quality="${escapeHtml(key)}" data-root-rule="breakthrough_bonus" type="number" step="1" value="${escapeHtml(DEFAULT_ROOT_QUALITY_RULES[key].breakthrough_bonus)}">
        </label>
        <label>战力倍率
          <input data-root-quality="${escapeHtml(key)}" data-root-rule="combat_factor" type="number" min="0.1" step="0.01" value="${escapeHtml(DEFAULT_ROOT_QUALITY_RULES[key].combat_factor)}">
        </label>
      `;
      rootRows.appendChild(row);
    });
    rootRows.dataset.ready = "1";
  }

  const itemRows = $("setting-item-quality-rows");
  if (itemRows && itemRows.dataset.ready !== "1") {
    itemRows.innerHTML = "";
    ITEM_QUALITY_RULES.forEach(({ key, label }) => {
      const row = document.createElement("div");
      row.className = "builder-row";
      row.innerHTML = `
        <label>品质
          <input type="text" value="${escapeHtml(label)}" disabled>
        </label>
        <label>法宝倍率
          <input data-item-quality="${escapeHtml(key)}" data-item-rule="artifact_multiplier" type="number" min="0" step="0.01" value="${escapeHtml(DEFAULT_ITEM_QUALITY_RULES[key].artifact_multiplier)}">
        </label>
        <label>丹药倍率
          <input data-item-quality="${escapeHtml(key)}" data-item-rule="pill_multiplier" type="number" min="0" step="0.01" value="${escapeHtml(DEFAULT_ITEM_QUALITY_RULES[key].pill_multiplier)}">
        </label>
        <label>符箓倍率
          <input data-item-quality="${escapeHtml(key)}" data-item-rule="talisman_multiplier" type="number" min="0" step="0.01" value="${escapeHtml(DEFAULT_ITEM_QUALITY_RULES[key].talisman_multiplier)}">
        </label>
      `;
      itemRows.appendChild(row);
    });
    itemRows.dataset.ready = "1";
  }

  const dropRows = $("setting-drop-weight-rows");
  if (dropRows && dropRows.dataset.ready !== "1") {
    dropRows.innerHTML = "";
    DROP_WEIGHT_RULE_FIELDS.forEach(({ key, label, tip }) => {
      const row = document.createElement("div");
      row.className = "builder-row";
      row.innerHTML = `
        <label class="wide-field">${label}
          <input data-drop-weight-rule="${escapeHtml(key)}" type="number" min="0" step="1" value="${escapeHtml(DEFAULT_DROP_WEIGHT_RULES[key])}">
        </label>
        <p class="muted">${escapeHtml(tip)}</p>
      `;
      dropRows.appendChild(row);
    });
    dropRows.dataset.ready = "1";
  }

  const activityRows = $("setting-activity-growth-rows");
  if (activityRows && activityRows.dataset.ready !== "1") {
    activityRows.innerHTML = "";
    ACTIVITY_GROWTH_FIELDS.forEach(({ key, label, tip }) => {
      const rule = DEFAULT_ACTIVITY_GROWTH_RULES[key];
      const row = document.createElement("div");
      row.className = "builder-row";
      row.innerHTML = `
        <label>玩法
          <input type="text" value="${escapeHtml(label)}" disabled>
        </label>
        <label>触发率（%）
          <input data-activity-growth="${escapeHtml(key)}" data-activity-rule="chance_percent" type="number" min="0" max="95" value="${escapeHtml(rule.chance_percent)}">
        </label>
        <label>单项最小值
          <input data-activity-growth="${escapeHtml(key)}" data-activity-rule="gain_min" type="number" min="1" value="${escapeHtml(rule.gain_min)}">
        </label>
        <label>单项最大值
          <input data-activity-growth="${escapeHtml(key)}" data-activity-rule="gain_max" type="number" min="1" value="${escapeHtml(rule.gain_max)}">
        </label>
        <label>抽取属性数
          <input data-activity-growth="${escapeHtml(key)}" data-activity-rule="attribute_count" type="number" min="1" max="3" value="${escapeHtml(rule.attribute_count)}">
        </label>
        <p class="muted wide-field">${escapeHtml(tip)}</p>
      `;
      activityRows.appendChild(row);
    });
    activityRows.dataset.ready = "1";
  }

  const gamblingQualityRows = $("setting-gambling-quality-rows");
  if (gamblingQualityRows && gamblingQualityRows.dataset.ready !== "1") {
    gamblingQualityRows.innerHTML = "";
    ITEM_QUALITY_RULES.forEach(({ key, label }) => {
      const row = document.createElement("div");
      row.className = "builder-row";
      row.innerHTML = `
        <label>品阶
          <input type="text" value="${escapeHtml(label)}" disabled>
        </label>
        <label>权重倍率
          <input data-gambling-quality="${escapeHtml(key)}" data-gambling-rule="weight_multiplier" type="number" min="0" step="0.001" value="${escapeHtml(DEFAULT_GAMBLING_QUALITY_RULES[key].weight_multiplier)}">
        </label>
        <p class="muted">该倍率会先作用于对应品阶的基础权重，随后再叠加机缘对高品阶的额外增幅。</p>
      `;
      gamblingQualityRows.appendChild(row);
    });
    gamblingQualityRows.dataset.ready = "1";
  }

  const fishingQualityRows = $("setting-fishing-quality-rows");
  if (fishingQualityRows && fishingQualityRows.dataset.ready !== "1") {
    fishingQualityRows.innerHTML = "";
    ITEM_QUALITY_RULES.forEach(({ key, label }) => {
      const row = document.createElement("div");
      row.className = "builder-row";
      row.innerHTML = `
        <label>品阶
          <input type="text" value="${escapeHtml(label)}" disabled>
        </label>
        <label>权重倍率
          <input data-fishing-quality="${escapeHtml(key)}" data-fishing-rule="weight_multiplier" type="number" min="0" step="0.001" value="${escapeHtml(DEFAULT_FISHING_QUALITY_RULES[key].weight_multiplier)}">
        </label>
        <p class="muted">该倍率只作用于垂钓，不影响仙界奇石的抽取权重。</p>
      `;
      fishingQualityRows.appendChild(row);
    });
    fishingQualityRows.dataset.ready = "1";
  }
}

function collectRootQualityRules() {
  ensureSettingRuleRows();
  return ROOT_QUALITY_RULES.reduce((result, { key }) => {
    result[key] = {
      cultivation_rate: Number(document.querySelector(`[data-root-quality="${key}"][data-root-rule="cultivation_rate"]`)?.value || DEFAULT_ROOT_QUALITY_RULES[key].cultivation_rate),
      breakthrough_bonus: Number(document.querySelector(`[data-root-quality="${key}"][data-root-rule="breakthrough_bonus"]`)?.value || DEFAULT_ROOT_QUALITY_RULES[key].breakthrough_bonus),
      combat_factor: Number(document.querySelector(`[data-root-quality="${key}"][data-root-rule="combat_factor"]`)?.value || DEFAULT_ROOT_QUALITY_RULES[key].combat_factor),
    };
    return result;
  }, {});
}

function collectItemQualityRules() {
  ensureSettingRuleRows();
  return ITEM_QUALITY_RULES.reduce((result, { key }) => {
    result[key] = {
      artifact_multiplier: Number(document.querySelector(`[data-item-quality="${key}"][data-item-rule="artifact_multiplier"]`)?.value || DEFAULT_ITEM_QUALITY_RULES[key].artifact_multiplier),
      pill_multiplier: Number(document.querySelector(`[data-item-quality="${key}"][data-item-rule="pill_multiplier"]`)?.value || DEFAULT_ITEM_QUALITY_RULES[key].pill_multiplier),
      talisman_multiplier: Number(document.querySelector(`[data-item-quality="${key}"][data-item-rule="talisman_multiplier"]`)?.value || DEFAULT_ITEM_QUALITY_RULES[key].talisman_multiplier),
    };
    return result;
  }, {});
}

function collectDropWeightRules() {
  ensureSettingRuleRows();
  return DROP_WEIGHT_RULE_FIELDS.reduce((result, { key }) => {
    result[key] = Number(document.querySelector(`[data-drop-weight-rule="${key}"]`)?.value || DEFAULT_DROP_WEIGHT_RULES[key]);
    return result;
  }, {});
}

function collectActivityGrowthRules() {
  ensureSettingRuleRows();
  return ACTIVITY_GROWTH_FIELDS.reduce((result, { key }) => {
    const fallback = DEFAULT_ACTIVITY_GROWTH_RULES[key];
    result[key] = {
      chance_percent: Number(document.querySelector(`[data-activity-growth="${key}"][data-activity-rule="chance_percent"]`)?.value || fallback.chance_percent),
      gain_min: Number(document.querySelector(`[data-activity-growth="${key}"][data-activity-rule="gain_min"]`)?.value || fallback.gain_min),
      gain_max: Number(document.querySelector(`[data-activity-growth="${key}"][data-activity-rule="gain_max"]`)?.value || fallback.gain_max),
      attribute_count: Number(document.querySelector(`[data-activity-growth="${key}"][data-activity-rule="attribute_count"]`)?.value || fallback.attribute_count),
    };
    return result;
  }, {});
}

function collectGamblingQualityRules() {
  ensureSettingRuleRows();
  return ITEM_QUALITY_RULES.reduce((result, { key }) => {
    result[key] = {
      weight_multiplier: Number(document.querySelector(`[data-gambling-quality="${key}"][data-gambling-rule="weight_multiplier"]`)?.value || DEFAULT_GAMBLING_QUALITY_RULES[key].weight_multiplier),
    };
    return result;
  }, {});
}

function collectFishingQualityRules() {
  ensureSettingRuleRows();
  return ITEM_QUALITY_RULES.reduce((result, { key }) => {
    result[key] = {
      weight_multiplier: Number(document.querySelector(`[data-fishing-quality="${key}"][data-fishing-rule="weight_multiplier"]`)?.value || DEFAULT_FISHING_QUALITY_RULES[key].weight_multiplier),
    };
    return result;
  }, {});
}

function collectGamblingRewardPool() {
  return [...document.querySelectorAll("#setting-gambling-pool-rows .builder-row")]
    .map((row) => {
      const quantityMin = Math.max(Number(row.querySelector("[data-gambling-min]")?.value || 1), 1);
      const quantityMax = Math.max(Number(row.querySelector("[data-gambling-max]")?.value || 1), quantityMin);
      const gamblingWeight = Number(row.querySelector("[data-gambling-weight]")?.value || 0);
      const fishingWeight = Number(row.querySelector("[data-fishing-weight]")?.value || 0);
      return {
        item_kind: row.querySelector("[data-gambling-kind]")?.value || "material",
        item_ref_id: Number(row.querySelector("[data-gambling-ref]")?.value || 0) || null,
        quantity_min: quantityMin,
        quantity_max: quantityMax,
        base_weight: gamblingWeight,
        gambling_weight: gamblingWeight,
        fishing_weight: fishingWeight,
        enabled: Boolean(row.querySelector("[data-gambling-enabled]")?.checked),
        gambling_enabled: Boolean(row.querySelector("[data-gambling-enabled]")?.checked),
        fishing_enabled: Boolean(row.querySelector("[data-fishing-enabled]")?.checked),
      };
    })
    .filter((row) => row.item_ref_id && row.gambling_weight >= 0 && row.fishing_weight >= 0);
}

function applyRootQualityRules(settings = {}) {
  ensureSettingRuleRows();
  const rules = settings.root_quality_value_rules || DEFAULT_ROOT_QUALITY_RULES;
  ROOT_QUALITY_RULES.forEach(({ key }) => {
    const current = rules[key] || DEFAULT_ROOT_QUALITY_RULES[key];
    const cultivationNode = document.querySelector(`[data-root-quality="${key}"][data-root-rule="cultivation_rate"]`);
    const breakthroughNode = document.querySelector(`[data-root-quality="${key}"][data-root-rule="breakthrough_bonus"]`);
    const combatNode = document.querySelector(`[data-root-quality="${key}"][data-root-rule="combat_factor"]`);
    if (cultivationNode) cultivationNode.value = current.cultivation_rate ?? DEFAULT_ROOT_QUALITY_RULES[key].cultivation_rate;
    if (breakthroughNode) breakthroughNode.value = current.breakthrough_bonus ?? DEFAULT_ROOT_QUALITY_RULES[key].breakthrough_bonus;
    if (combatNode) combatNode.value = current.combat_factor ?? DEFAULT_ROOT_QUALITY_RULES[key].combat_factor;
  });
}

function applyItemQualityRules(settings = {}) {
  ensureSettingRuleRows();
  const rules = settings.item_quality_value_rules || DEFAULT_ITEM_QUALITY_RULES;
  ITEM_QUALITY_RULES.forEach(({ key }) => {
    const current = rules[key] || DEFAULT_ITEM_QUALITY_RULES[key];
    const artifactNode = document.querySelector(`[data-item-quality="${key}"][data-item-rule="artifact_multiplier"]`);
    const pillNode = document.querySelector(`[data-item-quality="${key}"][data-item-rule="pill_multiplier"]`);
    const talismanNode = document.querySelector(`[data-item-quality="${key}"][data-item-rule="talisman_multiplier"]`);
    if (artifactNode) artifactNode.value = current.artifact_multiplier ?? DEFAULT_ITEM_QUALITY_RULES[key].artifact_multiplier;
    if (pillNode) pillNode.value = current.pill_multiplier ?? DEFAULT_ITEM_QUALITY_RULES[key].pill_multiplier;
    if (talismanNode) talismanNode.value = current.talisman_multiplier ?? DEFAULT_ITEM_QUALITY_RULES[key].talisman_multiplier;
  });
}

function applyDropWeightRules(settings = {}) {
  ensureSettingRuleRows();
  const rules = settings.exploration_drop_weight_rules || DEFAULT_DROP_WEIGHT_RULES;
  DROP_WEIGHT_RULE_FIELDS.forEach(({ key }) => {
    const node = document.querySelector(`[data-drop-weight-rule="${key}"]`);
    if (node) node.value = rules[key] ?? DEFAULT_DROP_WEIGHT_RULES[key];
  });
}

function applyActivityGrowthRules(settings = {}) {
  ensureSettingRuleRows();
  const rules = settings.activity_stat_growth_rules || DEFAULT_ACTIVITY_GROWTH_RULES;
  ACTIVITY_GROWTH_FIELDS.forEach(({ key }) => {
    const current = rules[key] || DEFAULT_ACTIVITY_GROWTH_RULES[key];
    const chanceNode = document.querySelector(`[data-activity-growth="${key}"][data-activity-rule="chance_percent"]`);
    const minNode = document.querySelector(`[data-activity-growth="${key}"][data-activity-rule="gain_min"]`);
    const maxNode = document.querySelector(`[data-activity-growth="${key}"][data-activity-rule="gain_max"]`);
    const countNode = document.querySelector(`[data-activity-growth="${key}"][data-activity-rule="attribute_count"]`);
    if (chanceNode) chanceNode.value = current.chance_percent ?? DEFAULT_ACTIVITY_GROWTH_RULES[key].chance_percent;
    if (minNode) minNode.value = current.gain_min ?? DEFAULT_ACTIVITY_GROWTH_RULES[key].gain_min;
    if (maxNode) maxNode.value = current.gain_max ?? DEFAULT_ACTIVITY_GROWTH_RULES[key].gain_max;
    if (countNode) countNode.value = current.attribute_count ?? DEFAULT_ACTIVITY_GROWTH_RULES[key].attribute_count;
  });
}

function applyGamblingQualityRules(settings = {}) {
  ensureSettingRuleRows();
  const rules = settings.gambling_quality_weight_rules || DEFAULT_GAMBLING_QUALITY_RULES;
  ITEM_QUALITY_RULES.forEach(({ key }) => {
    const current = rules[key] || DEFAULT_GAMBLING_QUALITY_RULES[key];
    const node = document.querySelector(`[data-gambling-quality="${key}"][data-gambling-rule="weight_multiplier"]`);
    if (node) node.value = current.weight_multiplier ?? DEFAULT_GAMBLING_QUALITY_RULES[key].weight_multiplier;
  });
}

function applyFishingQualityRules(settings = {}) {
  ensureSettingRuleRows();
  const rules = settings.fishing_quality_weight_rules || DEFAULT_FISHING_QUALITY_RULES;
  ITEM_QUALITY_RULES.forEach(({ key }) => {
    const current = rules[key] || DEFAULT_FISHING_QUALITY_RULES[key];
    const node = document.querySelector(`[data-fishing-quality="${key}"][data-fishing-rule="weight_multiplier"]`);
    if (node) node.value = current.weight_multiplier ?? DEFAULT_FISHING_QUALITY_RULES[key].weight_multiplier;
  });
}

function applyGamblingRewardPool(settings = {}) {
  const root = $("setting-gambling-pool-rows");
  if (!root) return;
  root.innerHTML = "";
  const rows = Array.isArray(settings.gambling_reward_pool) ? settings.gambling_reward_pool : [];
  if (!rows.length) {
    addGamblingPoolRow();
    return;
  }
  rows.forEach((row) => addGamblingPoolRow(row));
}

function applyArenaStageRules(settings = {}) {
  const root = $("setting-arena-stage-rows");
  if (!root) return;
  const ruleMap = new Map(
    (Array.isArray(settings.arena_stage_rules) ? settings.arena_stage_rules : [])
      .map((row) => [String(row?.realm_stage || "").trim(), row || {}])
  );
  root.innerHTML = REALM_OPTIONS.map((stage, index) => {
    const fallbackDuration = index < 2 ? 60 : index < 5 ? 90 : index < 9 ? 120 : 180;
    const current = ruleMap.get(stage) || {};
    return `
      <div class="builder-row">
        <div class="builder-inline-label">
          <strong>${escapeHtml(stage)}</strong>
          <span class="summary-tip">同境界同一时间仅保留一座擂台</span>
        </div>
        <label>
          持续分钟
          <input type="number" min="10" max="10080" data-arena-stage="${escapeHtml(stage)}" data-arena-rule="duration_minutes" value="${escapeHtml(current.duration_minutes ?? fallbackDuration)}">
        </label>
        <label>
          落幕修为奖励
          <input type="number" min="0" max="1000000000000" data-arena-stage="${escapeHtml(stage)}" data-arena-rule="reward_cultivation" value="${escapeHtml(current.reward_cultivation ?? 0)}">
        </label>
      </div>
    `;
  }).join("");
}

function collectArenaStageRules() {
  return REALM_OPTIONS.map((stage, index) => {
    const fallbackDuration = index < 2 ? 60 : index < 5 ? 90 : index < 9 ? 120 : 180;
    const durationNode = document.querySelector(`[data-arena-stage="${stage}"][data-arena-rule="duration_minutes"]`);
    const rewardNode = document.querySelector(`[data-arena-stage="${stage}"][data-arena-rule="reward_cultivation"]`);
    return {
      realm_stage: stage,
      duration_minutes: Number(durationNode?.value || fallbackDuration),
      reward_cultivation: Number(rewardNode?.value || 0),
    };
  });
}

function collectSectRoles() {
  return [...document.querySelectorAll("#sect-role-rows .builder-row")].map((row, index) => ({
    role_key: row.querySelector("[data-role-key]").value,
    role_name: row.querySelector("[data-role-name]").value.trim(),
    attack_bonus: Number(row.querySelector("[data-role-attack]").value || 0),
    defense_bonus: Number(row.querySelector("[data-role-defense]").value || 0),
    duel_rate_bonus: Number(row.querySelector("[data-role-duel]").value || 0),
    cultivation_bonus: Number(row.querySelector("[data-role-cultivation]").value || 0),
    monthly_salary: Number(row.querySelector("[data-role-salary]").value || 0),
    can_publish_tasks: row.querySelector("[data-role-publish]").checked,
    sort_order: index + 1,
  }));
}

function collectRecipeIngredients() {
  return [...document.querySelectorAll("#recipe-ingredient-rows .builder-row")].map((row) => ({
    material_id: Number(row.querySelector("[data-ingredient-id]").value || 0),
    quantity: Number(row.querySelector("[data-ingredient-quantity]").value || 1),
  })).filter((row) => row.material_id > 0);
}

function collectSceneEvents() {
  return [...document.querySelectorAll("#scene-event-rows .builder-row")]
    .map((row) => ({
      name: row.querySelector("[data-scene-event-name]")?.value.trim() || "",
      description: row.querySelector("[data-scene-event-description]")?.value.trim() || "",
      event_type: row.querySelector("[data-scene-event-type]")?.value || "encounter",
      weight: Number(row.querySelector("[data-scene-event-weight]")?.value || 1),
      stone_bonus_min: Number(row.querySelector("[data-scene-stone-bonus-min]")?.value || 0),
      stone_bonus_max: Number(row.querySelector("[data-scene-stone-bonus-max]")?.value || 0),
      stone_loss_min: Number(row.querySelector("[data-scene-stone-loss-min]")?.value || 0),
      stone_loss_max: Number(row.querySelector("[data-scene-stone-loss-max]")?.value || 0),
      bonus_reward_kind: row.querySelector("[data-scene-bonus-kind]")?.value || null,
      bonus_reward_ref_id: Number(row.querySelector("[data-scene-bonus-ref]")?.value || 0) || null,
      bonus_quantity_min: Number(row.querySelector("[data-scene-bonus-min]")?.value || 1),
      bonus_quantity_max: Number(row.querySelector("[data-scene-bonus-max]")?.value || 1),
      bonus_chance: Number(row.querySelector("[data-scene-bonus-chance]")?.value || 0),
    }))
    .filter((row) => row.name || row.description);
}

function collectSceneDrops() {
  return [...document.querySelectorAll("#scene-drop-rows .builder-row")].map((row) => ({
    reward_kind: row.querySelector("[data-drop-kind]").value,
    reward_ref_id: Number(row.querySelector("[data-drop-ref]").value || 0) || null,
    quantity_min: Number(row.querySelector("[data-drop-min]").value || 1),
    quantity_max: Number(row.querySelector("[data-drop-max]").value || 1),
    weight: Number(row.querySelector("[data-drop-weight]").value || 1),
    stone_reward: Number(row.querySelector("[data-drop-stone]").value || 0),
    event_text: row.querySelector("[data-drop-event]").value.trim(),
  }));
}

function renderTagList(id, rows, formatter) {
  const root = $(id);
  if (!root) return;
  root.innerHTML = rows.length ? rows.map(formatter).join("") : `<span class="tag">暂无</span>`;
}

function renderStack(id, html) {
  const root = $(id);
  if (root) root.innerHTML = html;
}

function deleteButton(entity, id) {
  return `<button type="button" class="ghost" data-delete="${entity}" data-id="${id}">删除</button>`;
}

function editButton(entity, id) {
  return `<button type="button" class="ghost" data-edit="${entity}" data-id="${id}">编辑</button>`;
}

function encounterDispatchButton(id) {
  return `<button type="button" class="secondary" data-encounter-dispatch="${id}">投放到群</button>`;
}

function combatConfigSummary(config = {}) {
  const skills = Array.isArray(config.skills) ? config.skills : [];
  const passives = Array.isArray(config.passives) ? config.passives : [];
  const parts = [];
  if (config.opening_text) parts.push(`起手: ${config.opening_text}`);
  if (skills.length) parts.push(`主动 ${skills.map((item) => item.name || item.kind).filter(Boolean).join("、")}`);
  if (passives.length) parts.push(`被动 ${passives.map((item) => item.name || item.kind).filter(Boolean).join("、")}`);
  return parts.join(" · ") || "无战斗特效";
}

function renderWorld() {
  const bundle = state.bundle;
  if (!bundle) return;

  renderTagList("upload-permission-list", bundle.upload_permissions || [], (row) => `<span class="tag">TG ${escapeHtml(row.tg)}</span>`);
  renderErrorLogs(bundle.error_logs || []);

  renderStack("artifact-list", (bundle.artifacts || []).map((item) => `
    <article class="stack-item"><div class="stack-item-head"><strong>${escapeHtml(item.name)}</strong><span class="badge badge--normal">${escapeHtml(item.artifact_type_label || item.artifact_type)}</span></div>
    <p>品质 ${escapeHtml(item.rarity)} · 攻击 ${escapeHtml(item.attack_bonus)} · 防御 ${escapeHtml(item.defense_bonus)} · 斗法 ${escapeHtml(item.duel_rate_bonus)}% · 修炼 ${escapeHtml(item.cultivation_bonus)}</p>
    <p>${escapeHtml(combatConfigSummary(item.combat_config || {}))}</p>
    <p>境界限制：${escapeHtml(item.min_realm_stage || "无限制")} ${escapeHtml(item.min_realm_layer || 1)} 层</p>
    <div class="inline-action-buttons">${deleteButton("artifact", item.id)}</div></article>`).join("") || `<article class="stack-item"><strong>暂无法宝</strong></article>`);

  renderStack("talisman-list", (bundle.talismans || []).map((item) => `
    <article class="stack-item"><div class="stack-item-head"><strong>${escapeHtml(item.name)}</strong><span class="badge badge--normal">${escapeHtml(item.rarity)}</span></div>
    <p>攻击 ${escapeHtml(item.attack_bonus)} · 防御 ${escapeHtml(item.defense_bonus)} · 斗法 ${escapeHtml(item.duel_rate_bonus)}%</p><p>${escapeHtml(combatConfigSummary(item.combat_config || {}))}</p>
    <div class="inline-action-buttons">${deleteButton("talisman", item.id)}</div></article>`).join("") || `<article class="stack-item"><strong>暂无符箓</strong></article>`);

  renderStack("pill-list", (bundle.pills || []).map((item) => `
    <article class="stack-item"><div class="stack-item-head"><strong>${escapeHtml(item.name)}</strong><span class="badge badge--normal">${escapeHtml(item.pill_type_label || item.pill_type)}</span></div>
    <p>${escapeHtml(item.effect_value_label || "效果值")} ${escapeHtml(item.effect_value)} · 丹毒 ${escapeHtml(item.poison_delta)}</p>
    <div class="inline-action-buttons">${deleteButton("pill", item.id)}</div></article>`).join("") || `<article class="stack-item"><strong>暂无丹药</strong></article>`);

  renderStack("material-list", (bundle.materials || []).map((item) => `
    <article class="stack-item"><div class="stack-item-head"><strong>${escapeHtml(item.name)}</strong><span class="badge badge--normal">${escapeHtml(item.quality_label || item.quality_level)}</span></div>
    <p>${escapeHtml(item.description || "暂无描述")}</p><div class="inline-action-buttons">${deleteButton("material", item.id)}</div></article>`).join("") || `<article class="stack-item"><strong>暂无材料</strong></article>`);

  renderStack("recipe-list", (bundle.recipes || []).map((item) => `
    <article class="stack-item"><div class="stack-item-head"><strong>${escapeHtml(item.name)}</strong><span class="badge badge--normal">${escapeHtml(item.recipe_kind_label || item.recipe_kind)}</span></div>
    <p>产出：${escapeHtml(item.result_item?.name || item.result_kind_label || item.result_kind)} × ${escapeHtml(item.result_quantity)} · 成功率 ${escapeHtml(item.base_success_rate)}%</p>
    <p>材料：${escapeHtml((item.ingredients || []).map((row) => `${row.material?.name || row.material_id}×${row.quantity}`).join("、") || "未配置")}</p>
    <div class="inline-action-buttons">${deleteButton("recipe", item.id)}</div></article>`).join("") || `<article class="stack-item"><strong>暂无配方</strong></article>`);

  renderStack("scene-list", (bundle.scenes || []).map((item) => `
    <article class="stack-item"><div class="stack-item-head"><strong>${escapeHtml(item.name)}</strong><span class="badge badge--normal">最多 ${escapeHtml(item.max_minutes)} 分钟</span></div>
    <p>${escapeHtml(item.description || "暂无描述")}</p><p>门槛：${escapeHtml(item.min_realm_stage ? `${item.min_realm_stage}${item.min_realm_layer || 1}层` : "无限制")} · 战力 ${escapeHtml(item.min_combat_power || 0)}</p><p>掉落 ${escapeHtml((item.drops || []).length)} 项 · 事件 ${escapeHtml((item.event_pool || []).length)} 条</p><p>${escapeHtml((item.event_pool || []).map((event) => `${event.name || "未命名事件"}(${event.event_type || "encounter"})`).slice(0, 3).join("、") || "暂无事件详情")}</p>
    <div class="inline-action-buttons">${deleteButton("scene", item.id)}</div></article>`).join("") || `<article class="stack-item"><strong>暂无场景</strong></article>`);

  renderStack("encounter-list", (bundle.encounters || []).map((item) => `
    <article class="stack-item"><div class="stack-item-head"><strong>${escapeHtml(item.name)}</strong><span class="badge badge--normal">${escapeHtml(item.weight || 1)} 权重</span></div>
    <p>${escapeHtml(item.description || "暂无描述")}</p>
    <p>门槛：${escapeHtml(item.min_realm_stage ? `${item.min_realm_stage}${item.min_realm_layer || 1}层` : "无限制")} · 战力 ${escapeHtml(item.min_combat_power || 0)} · 持续 ${escapeHtml(item.active_seconds || 90)} 秒</p>
    <p>奖励：灵石 ${escapeHtml(item.reward_stone_min || 0)}-${escapeHtml(item.reward_stone_max || 0)} · 修为 ${escapeHtml(item.reward_cultivation_min || 0)}-${escapeHtml(item.reward_cultivation_max || 0)}${item.reward_item_kind ? ` · 物品 ${escapeHtml(item.reward_item_kind)} × ${escapeHtml(item.reward_item_quantity_min || 1)}-${escapeHtml(item.reward_item_quantity_max || 1)}` : ""}</p>
    <div class="inline-action-buttons">${encounterDispatchButton(item.id)}${deleteButton("encounter", item.id)}</div></article>`).join("") || `<article class="stack-item"><strong>暂无奇遇</strong></article>`);

  renderStack("sect-list", (bundle.sects || []).map((item) => `
    <article class="stack-item"><div class="stack-item-head"><strong>${escapeHtml(item.name)}</strong><span class="badge badge--normal">${escapeHtml((item.roles || []).length)} 个职位</span></div>
    <p>${escapeHtml(item.description || "暂无宗门简介")}</p><p>门槛：${escapeHtml(item.min_realm_stage || "无限制")} ${escapeHtml(item.min_realm_layer || 1)} 层 · 战力 ${escapeHtml(item.min_combat_power || 0)} · 灵石 ${escapeHtml(item.min_stone)}</p><p>考察期：${escapeHtml(item.salary_min_stay_days || 30)} 天</p>
    <div class="inline-action-buttons">${deleteButton("sect", item.id)}</div></article>`).join("") || `<article class="stack-item"><strong>暂无宗门</strong></article>`);

  renderStack("task-list", (bundle.tasks || []).map((item) => `
    <article class="stack-item"><div class="stack-item-head"><strong>${escapeHtml(item.title)}</strong><span class="badge badge--normal">${escapeHtml(item.task_scope_label || item.task_scope)}</span></div>
    <p>${escapeHtml(item.task_type_label || item.task_type)} · 领取 ${escapeHtml(item.claimants_count || 0)}/${escapeHtml(item.max_claimants || 1)} · 状态 ${escapeHtml(item.status)}</p>
    <div class="inline-action-buttons">${deleteButton("task", item.id)}</div></article>`).join("") || `<article class="stack-item"><strong>暂无任务</strong></article>`);

  renderStack("official-shop-list", (bundle.official_shop || []).map((item) => `
    <article class="stack-item">
      <div class="stack-item-head"><strong>${escapeHtml(item.item_name)}</strong><span class="badge badge--normal">${escapeHtml(item.price_stone)} 灵石</span></div>
      <p>${escapeHtml(item.shop_name)} · 库存 ${escapeHtml(item.quantity)} · ${item.enabled ? "上架中" : "已下架"}</p>
      <div class="inline-action-buttons">
        <button type="button" class="ghost" data-shop-toggle="${item.id}" data-next-enabled="${item.enabled ? "false" : "true"}">${item.enabled ? "下架" : "上架"}</button>
      </div>
    </article>`).join("") || `<article class="stack-item"><strong>暂无官方商品</strong></article>`);

  renderStack("auction-list", (bundle.auctions || []).map((item) => `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(item.item_name)} × ${escapeHtml(item.quantity)}</strong>
        <span class="badge badge--normal">${escapeHtml(item.status_label || item.status || "未知状态")}</span>
      </div>
      <p>${escapeHtml(item.item_kind_label || item.item_kind)} · 卖家 ${escapeHtml(item.owner_display_name || `TG ${item.owner_tg || 0}`)}</p>
      <p>起拍 ${escapeHtml(item.opening_price_stone)} · 当前 ${escapeHtml(item.current_display_price_stone)} · 加价 ${escapeHtml(item.bid_increment_stone)} · 一口价 ${escapeHtml(item.buyout_price_stone > 0 ? item.buyout_price_stone : "未设置")}</p>
      <p>手续费 ${escapeHtml(item.fee_percent || 0)}% · 出价 ${escapeHtml(item.bid_count || 0)} 次 · 结束 ${escapeHtml(formatShanghaiDate(item.end_at))}</p>
      <p>群消息：${escapeHtml(item.group_chat_id || "-")} / ${escapeHtml(item.group_message_id || "-")}</p>
    </article>`).join("") || `<article class="stack-item"><strong>暂无拍卖记录</strong></article>`);
}

function syncSelects() {
  setOptions($("artifact-rarity"), qualityRows(), $("artifact-rarity")?.value);
  setOptions($("technique-rarity"), qualityRows(), $("technique-rarity")?.value);
  setOptions($("talisman-rarity"), qualityRows(), $("talisman-rarity")?.value);
  setOptions($("material-quality"), qualityRows(), $("material-quality")?.value);
  ["artifact-stage", "talisman-stage", "pill-stage", "sect-stage", "technique-stage", "scene-stage", "encounter-stage"].forEach((id) => setOptions($(id), realmRows(), $(id)?.value, "无限制"));
  setOptions($("sect-assign-id"), sectRows(), $("sect-assign-id")?.value);
  setOptions($("admin-task-sect-id"), [{ value: "", label: "无" }, ...sectRows()], $("admin-task-sect-id")?.value);
  setOptions($("recipe-result-id"), itemRows($("recipe-result-kind")?.value || "pill"), $("recipe-result-id")?.value);
  syncGrantItemOptions();
  setOptions($("official-ref-id"), itemRows($("official-kind")?.value || "artifact"), $("official-ref-id")?.value);
  setOptions($("encounter-item-id"), [{ value: "", label: "无" }, ...itemRows($("encounter-item-kind")?.value || "")], $("encounter-item-id")?.value);
  setOptions($("admin-task-item-id"), [{ value: "", label: "无" }, ...itemRows($("admin-task-item-kind")?.value || "")], $("admin-task-item-id")?.value);
  setOptions($("admin-task-required-id"), [{ value: "", label: "无" }, ...itemRows($("admin-task-required-kind")?.value || "")], $("admin-task-required-id")?.value);
  const roles = (($("sect-assign-id")?.value && state.bundle?.sects) ? (state.bundle.sects.find((item) => String(item.id) === String($("sect-assign-id").value))?.roles || []) : []);
  setOptions($("sect-assign-role"), roles.map((item) => ({ value: item.role_key, label: item.role_name })), $("sect-assign-role")?.value);
  document.querySelectorAll("#scene-drop-rows .builder-row").forEach((row) => {
    const kind = row.querySelector("[data-drop-kind]")?.value || "material";
    setOptions(row.querySelector("[data-drop-ref]"), itemRows(kind), row.querySelector("[data-drop-ref]")?.value, "无");
  });
  document.querySelectorAll("#scene-event-rows .builder-row").forEach((row) => {
    const kind = row.querySelector("[data-scene-bonus-kind]")?.value || "";
    setOptions(row.querySelector("[data-scene-bonus-ref]"), itemRows(kind || "material"), row.querySelector("[data-scene-bonus-ref]")?.value, "无");
  });
  document.querySelectorAll("#setting-gambling-pool-rows .builder-row").forEach((row) => {
    const kind = row.querySelector("[data-gambling-kind]")?.value || "material";
    const keyword = row.querySelector("[data-gambling-search]")?.value || "";
    setOptions(row.querySelector("[data-gambling-ref]"), itemRows(kind, keyword), row.querySelector("[data-gambling-ref]")?.value, "请选择物品");
  });
  syncGrantUserMatches();
}

function applySettings(settings = {}) {
  ensureSettingRuleRows();
  $("setting-exchange-enabled").checked = settings.coin_stone_exchange_enabled ?? true;
  $("setting-rate").value = settings.coin_exchange_rate ?? 100;
  $("setting-fee").value = settings.exchange_fee_percent ?? 1;
  $("setting-min").value = settings.min_coin_exchange ?? 1;
  updateExchangeSettingNote();
  $("setting-duel-bet-enabled").checked = settings.duel_bet_enabled ?? true;
  $("setting-duel-seconds").value = settings.duel_bet_seconds ?? 120;
  $("setting-duel-bet-min").value = settings.duel_bet_min_amount ?? 10;
  $("setting-duel-bet-max").value = settings.duel_bet_max_amount ?? 100;
  $("setting-duel-bet-options").value = formatIntegerListInput(settings.duel_bet_amount_options ?? [10, 50, 100]);
  $("setting-duel-invite-timeout").value = settings.duel_invite_timeout_seconds ?? 90;
  $("setting-arena-open-fee").value = settings.arena_open_fee_stone ?? 0;
  $("setting-arena-challenge-fee").value = settings.arena_challenge_fee_stone ?? 0;
  $("setting-duel-steal").value = settings.duel_winner_steal_percent ?? 25;
  $("setting-artifact-plunder").value = settings.artifact_plunder_chance ?? 20;
  $("setting-message-auto-delete").value = settings.message_auto_delete_seconds ?? 180;
  $("setting-unbind-cost").value = settings.equipment_unbind_cost ?? 100;
  $("setting-broadcast").value = settings.shop_broadcast_cost ?? 20;
  $("setting-shop-notice-group").value = settings.shop_notice_group_id ?? 0;
  $("setting-shop-name").value = settings.official_shop_name ?? "官方商店";
  $("setting-auction-fee").value = settings.auction_fee_percent ?? 5;
  $("setting-auction-duration").value = settings.auction_duration_minutes ?? 60;
  $("setting-auction-notice-group").value = settings.auction_notice_group_id ?? 0;
  $("setting-arena-notice-group").value = settings.arena_notice_group_id ?? 0;
  $("setting-event-summary-interval").value = settings.event_summary_interval_minutes ?? 10;
  $("setting-task-publish-cost").value = settings.task_publish_cost ?? 20;
  $("setting-user-task-daily-limit").value = settings.user_task_daily_limit ?? 3;
  $("setting-allow-user-task-publish").checked = settings.allow_user_task_publish ?? true;
  $("setting-gambling-exchange-cost").value = settings.gambling_exchange_cost_stone ?? 120;
  $("setting-gambling-exchange-max").value = settings.gambling_exchange_max_count ?? 20;
  $("setting-gambling-open-max").value = settings.gambling_open_max_count ?? 100;
  $("setting-gambling-broadcast-quality").value = settings.gambling_broadcast_quality_level ?? 5;
  $("setting-gambling-fortune-divisor").value = settings.gambling_fortune_divisor ?? 6;
  $("setting-gambling-fortune-bonus").value = settings.gambling_fortune_bonus_per_quality_percent ?? 8;
  if ($("official-shop-name")) $("official-shop-name").value = settings.official_shop_name ?? "官方商店";
  $("setting-artifact-limit").value = settings.artifact_equip_limit ?? 3;
  $("setting-user-upload").checked = Boolean(settings.allow_non_admin_image_upload);
  $("setting-chat-chance").value = settings.chat_cultivation_chance ?? 6;
  $("setting-chat-min").value = settings.chat_cultivation_min_gain ?? 1;
  $("setting-chat-max").value = settings.chat_cultivation_max_gain ?? 2;
  $("setting-robbery-limit").value = settings.robbery_daily_limit ?? 3;
  $("setting-robbery-max").value = settings.robbery_max_steal ?? 180;
  $("setting-seclusion-efficiency").value = settings.seclusion_cultivation_efficiency_percent ?? 60;
  $("setting-quality-broadcast").value = settings.high_quality_broadcast_level ?? 4;
  $("setting-slave-tribute").value = settings.slave_tribute_percent ?? 20;
  $("setting-furnace-harvest").value = settings.furnace_harvest_cultivation_percent ?? 10;
  $("setting-slave-cooldown").value = settings.slave_challenge_cooldown_hours ?? 24;
  $("setting-rebirth-cooldown-enabled").checked = settings.rebirth_cooldown_enabled ?? false;
  $("setting-rebirth-cooldown-base").value = settings.rebirth_cooldown_base_hours ?? 12;
  $("setting-rebirth-cooldown-increment").value = settings.rebirth_cooldown_increment_hours ?? 6;
  $("setting-sect-salary-stay").value = settings.sect_salary_min_stay_days ?? 30;
  if ($("sect-salary-stay-days") && !$("sect-id")?.value) $("sect-salary-stay-days").value = settings.sect_salary_min_stay_days ?? 30;
  $("setting-sect-betrayal-cooldown").value = settings.sect_betrayal_cooldown_days ?? 7;
  $("setting-sect-betrayal-percent").value = settings.sect_betrayal_stone_percent ?? 10;
  $("setting-sect-betrayal-min").value = settings.sect_betrayal_stone_min ?? 20;
  $("setting-sect-betrayal-max").value = settings.sect_betrayal_stone_max ?? 300;
  $("setting-error-log-retention").value = settings.error_log_retention_count ?? 500;
  applyRootQualityRules(settings);
  applyItemQualityRules(settings);
  applyDropWeightRules(settings);
  applyActivityGrowthRules(settings);
  applyGamblingQualityRules(settings);
  applyFishingQualityRules(settings);
  applyGamblingRewardPool(settings);
  applyArenaStageRules(settings);
}

function updateExchangeSettingNote() {
  const rate = Math.max(Number($("setting-rate")?.value || 100), 1);
  const min = Math.max(Number($("setting-min")?.value || 1), 1);
  const effective = Math.max(rate, min);
  const node = $("setting-exchange-rate-note");
  if (!node) return;
  node.textContent = `当前比例示例：${rate} 灵石 = 1 片刻碎片；实际最低门槛 = max(${rate}, ${min}) = ${effective} 灵石。`;
}

function renderErrorLogs(rows = []) {
  renderStack("error-log-list", (rows || []).map((item) => {
    const who = item.display_name || (item.username ? `@${item.username}` : "") || (item.tg ? `TG ${item.tg}` : "未知用户");
    const detail = String(item.detail || "").trim();
    const preview = detail ? (detail.length > 800 ? `${detail.slice(0, 800)}\n...` : detail) : "无详细堆栈";
    return `
      <article class="stack-item">
        <div class="stack-item-head"><strong>${escapeHtml(item.operation || "未知操作")}</strong><span class="badge badge--normal">${escapeHtml(item.level || "ERROR")}</span></div>
        <p>${escapeHtml(who)} · ${escapeHtml(item.method || "POST")} ${escapeHtml(item.path || "")} · 状态 ${escapeHtml(item.status_code || "-")}</p>
        <p>${escapeHtml(item.message || "未知错误")}</p>
        <pre class="compact-copy">${escapeHtml(preview)}</pre>
        <p class="muted compact-copy">${escapeHtml(item.created_at || "")}</p>
      </article>`;
  }).join("") || `<article class="stack-item"><strong>暂无错误日志</strong></article>`);
}

async function bootstrapAdmin(forceToken = false) {
  const playerQuery = String($("player-search-q")?.value || state.playerSearch?.query || "");
  const playerPage = Math.max(Number(state.playerSearch?.page || 1), 1);
  const playerPageSize = Math.max(Number(state.playerSearch?.pageSize || PLAYER_SEARCH_PAGE_SIZE), 1);
  const payload = {
    player_query: playerQuery,
    player_page: playerPage,
    player_page_size: playerPageSize,
  };
  if (!forceToken && state.initData) payload.init_data = state.initData;
  else if (state.token) payload.token = state.token;
  else {
    $("token-panel")?.setAttribute("open", "open");
    adminStatus("等待主人凭证。", "warning");
    return;
  }
  const data = await request("POST", "/plugins/xiuxian/admin-api/bootstrap", payload);
  if (Array.isArray(data.pill_type_options) && data.pill_type_options.length) {
    // 后台下拉选项以后端定义为准，镜像更新后管理页可立即看到最新类型与文案。
    PILL_TYPES.splice(0, PILL_TYPES.length, ...data.pill_type_options.map((item) => ({
      value: String(item.value || ""),
      label: String(item.label || item.value || ""),
      effect: String(item.effect || "主效果"),
    })));
  }
  state.bundle = data;
  applySettings(data.settings || {});
  syncSelects();
  syncPlayerBatchResourceForm();
  renderPlayerBatchResourceSummary();
  renderWorld();
  const applied = applyPlayerSearchResult(data.player_search || {}, {
    query: playerQuery,
    requestedPage: playerPage,
    pageSize: playerPageSize,
  });
  if (applied.needsRefetch) {
    await searchPlayers({
      query: playerQuery,
      page: applied.refetchPage,
      pageSize: playerPageSize,
    });
  }
  renderAdminNavigator();
  adminStatus(`修仙后台已就绪，当前管理数据加载完成。`, "success");
}

function applyAdminSettingsUpdate(settings = {}) {
  if (!state.bundle) state.bundle = {};
  state.bundle.settings = settings;
  applySettings(settings);
  syncSelects();
  renderAdminNavigator();
}

function applyUploadPermissionUpdate(payload = {}) {
  const tg = Number(payload.tg || 0);
  if (!tg) return;
  if (!state.bundle) state.bundle = {};
  const rows = Array.isArray(state.bundle.upload_permissions) ? state.bundle.upload_permissions.slice() : [];
  const index = rows.findIndex((row) => Number(row?.tg || 0) === tg);
  if (payload.granted && !payload.builtin && index === -1) {
    rows.push({ tg });
  }
  if (payload.removed && index >= 0) {
    rows.splice(index, 1);
  }
  rows.sort((left, right) => Number(left?.tg || 0) - Number(right?.tg || 0));
  state.bundle.upload_permissions = rows;
  renderTagList("upload-permission-list", rows, (row) => `<span class="tag">TG ${escapeHtml(row.tg)}</span>`);
  renderAdminNavigator();
}

async function submitAndRefresh(handler, successTitle, successMessage, { refresh = "bootstrap", afterSuccess = null } = {}) {
  const result = await handler();
  if (typeof afterSuccess === "function") {
    afterSuccess(result);
  }
  const refreshPromise = refresh === "bootstrap" ? bootstrapAdmin() : Promise.resolve();
  const popupPromise = popup(successTitle, successMessage);
  await refreshPromise;
  await popupPromise;
  return result;
}

function bindEvents() {
  initTitleColorEditor();
  $("pill-type")?.addEventListener("change", updatePillEffectLabel);
  $("recipe-result-kind")?.addEventListener("change", syncSelects);
  $("grant-kind")?.addEventListener("change", syncSelects);
  $("grant-item-search")?.addEventListener("input", syncGrantItemOptions);
  $("grant-user-search")?.addEventListener("input", queueGrantUserSearch);
  $("grant-user-match")?.addEventListener("change", () => {
    const tg = Number($("grant-user-match")?.value || 0);
    if (tg > 0 && $("grant-tg")) $("grant-tg").value = String(tg);
    syncGrantUserSearchTip();
  });
  $("grant-tg")?.addEventListener("input", syncGrantTargetTg);
  $("official-kind")?.addEventListener("change", syncSelects);
  $("encounter-item-kind")?.addEventListener("change", syncSelects);
  $("admin-task-item-kind")?.addEventListener("change", syncSelects);
  $("admin-task-required-kind")?.addEventListener("change", syncSelects);
  $("admin-task-type")?.addEventListener("change", syncAdminTaskFormState);
  $("sect-assign-id")?.addEventListener("change", syncSelects);
  $("sect-role-add")?.addEventListener("click", () => addSectRoleRow());
  $("recipe-ingredient-add")?.addEventListener("click", () => addRecipeIngredientRow());
  $("scene-event-add")?.addEventListener("click", () => addSceneEventRow());
  $("scene-drop-add")?.addEventListener("click", () => addSceneDropRow());
  $("setting-gambling-pool-add")?.addEventListener("click", () => addGamblingPoolRow());

  $("token-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    state.token = $("admin-token").value.trim();
    localStorage.setItem("xiuxian_admin_token", state.token);
    await bootstrapAdmin(true);
  });

  $("settings-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/settings", {
      coin_stone_exchange_enabled: $("setting-exchange-enabled").checked,
      coin_exchange_rate: Number($("setting-rate").value || 100),
      exchange_fee_percent: Number($("setting-fee").value || 1),
      min_coin_exchange: Number($("setting-min").value || 1),
      message_auto_delete_seconds: Number($("setting-message-auto-delete").value || 0),
      shop_broadcast_cost: Number($("setting-broadcast").value || 20),
      shop_notice_group_id: Number($("setting-shop-notice-group").value || 0),
      official_shop_name: $("setting-shop-name").value.trim(),
      auction_fee_percent: Number($("setting-auction-fee").value || 0),
      auction_duration_minutes: Number($("setting-auction-duration").value || 60),
      auction_notice_group_id: Number($("setting-auction-notice-group").value || 0),
      arena_notice_group_id: Number($("setting-arena-notice-group").value || 0),
      event_summary_interval_minutes: Number($("setting-event-summary-interval").value || 0),
      task_publish_cost: Number($("setting-task-publish-cost").value || 0),
      user_task_daily_limit: Number($("setting-user-task-daily-limit").value || 0),
      allow_user_task_publish: $("setting-allow-user-task-publish").checked,
      allow_non_admin_image_upload: $("setting-user-upload").checked,
      chat_cultivation_chance: Number($("setting-chat-chance").value || 6),
      chat_cultivation_min_gain: Number($("setting-chat-min").value || 1),
      chat_cultivation_max_gain: Number($("setting-chat-max").value || 2),
      robbery_daily_limit: Number($("setting-robbery-limit").value || 3),
      robbery_max_steal: Number($("setting-robbery-max").value || 180),
      seclusion_cultivation_efficiency_percent: Number($("setting-seclusion-efficiency").value || 60),
      gambling_exchange_cost_stone: Number($("setting-gambling-exchange-cost").value || 120),
      gambling_exchange_max_count: Number($("setting-gambling-exchange-max").value || 20),
      gambling_open_max_count: Number($("setting-gambling-open-max").value || 100),
      gambling_broadcast_quality_level: Number($("setting-gambling-broadcast-quality").value || 5),
      gambling_fortune_divisor: Number($("setting-gambling-fortune-divisor").value || 6),
      gambling_fortune_bonus_per_quality_percent: Number($("setting-gambling-fortune-bonus").value || 8),
      root_quality_value_rules: collectRootQualityRules(),
      item_quality_value_rules: collectItemQualityRules(),
      exploration_drop_weight_rules: collectDropWeightRules(),
      activity_stat_growth_rules: collectActivityGrowthRules(),
      gambling_quality_weight_rules: collectGamblingQualityRules(),
      fishing_quality_weight_rules: collectFishingQualityRules(),
      gambling_reward_pool: collectGamblingRewardPool(),
    }), "保存成功", "基础规则已更新。", {
      refresh: "none",
      afterSuccess: (settings) => {
        applyAdminSettingsUpdate(settings || {});
        adminStatus("基础规则已更新。", "success");
      },
    });
  });

  $("setting-shop-name")?.addEventListener("input", (event) => {
    if ($("official-shop-name")) {
      $("official-shop-name").value = event.currentTarget?.value?.trim?.() || "";
    }
  });
  $("setting-rate")?.addEventListener("input", updateExchangeSettingNote);
  $("setting-min")?.addEventListener("input", updateExchangeSettingNote);

  $("duel-settings-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/settings", {
      duel_bet_enabled: $("setting-duel-bet-enabled").checked,
      duel_bet_seconds: Number($("setting-duel-seconds").value || 120),
      duel_bet_min_amount: Number($("setting-duel-bet-min").value || 10),
      duel_bet_max_amount: Number($("setting-duel-bet-max").value || 100),
      duel_bet_amount_options: parseIntegerListInput($("setting-duel-bet-options").value),
      duel_invite_timeout_seconds: Number($("setting-duel-invite-timeout").value || 90),
      arena_open_fee_stone: Number($("setting-arena-open-fee").value || 0),
      arena_challenge_fee_stone: Number($("setting-arena-challenge-fee").value || 0),
      duel_winner_steal_percent: Number($("setting-duel-steal").value || 25),
      artifact_plunder_chance: Number($("setting-artifact-plunder").value || 20),
      equipment_unbind_cost: Number($("setting-unbind-cost").value || 0),
      artifact_equip_limit: Number($("setting-artifact-limit").value || 3),
      high_quality_broadcast_level: Number($("setting-quality-broadcast").value || 4),
      slave_tribute_percent: Number($("setting-slave-tribute").value || 20),
      furnace_harvest_cultivation_percent: Number($("setting-furnace-harvest").value || 10),
      slave_challenge_cooldown_hours: Number($("setting-slave-cooldown").value || 24),
      rebirth_cooldown_enabled: $("setting-rebirth-cooldown-enabled").checked,
      rebirth_cooldown_base_hours: Number($("setting-rebirth-cooldown-base").value || 0),
      rebirth_cooldown_increment_hours: Number($("setting-rebirth-cooldown-increment").value || 0),
      sect_salary_min_stay_days: Number($("setting-sect-salary-stay").value || 30),
      sect_betrayal_cooldown_days: Number($("setting-sect-betrayal-cooldown").value || 7),
      sect_betrayal_stone_percent: Number($("setting-sect-betrayal-percent").value || 10),
      sect_betrayal_stone_min: Number($("setting-sect-betrayal-min").value || 20),
      sect_betrayal_stone_max: Number($("setting-sect-betrayal-max").value || 300),
      arena_stage_rules: collectArenaStageRules(),
    }), "保存成功", "斗法与装备规则已更新。", {
      refresh: "none",
      afterSuccess: (settings) => {
        applyAdminSettingsUpdate(settings || {});
        adminStatus("斗法与装备规则已更新。", "success");
      },
    });
  });

  $("error-log-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await request("POST", "/plugins/xiuxian/admin-api/settings", {
      error_log_retention_count: Number($("setting-error-log-retention").value || 500),
    });
    const logs = await request("POST", "/plugins/xiuxian/admin-api/error-logs", {
      limit: Number($("error-log-limit").value || 100),
      tg: Number($("error-log-tg").value || 0) || null,
      level: $("error-log-level").value || null,
      keyword: $("error-log-keyword").value.trim() || null,
    });
    state.bundle.error_logs = logs;
    renderErrorLogs(logs);
    adminStatus("错误日志设置已保存，日志列表已刷新。", "success");
  });

  $("error-log-refresh")?.addEventListener("click", async () => {
    const logs = await request("POST", "/plugins/xiuxian/admin-api/error-logs", {
      limit: Number($("error-log-limit").value || 100),
      tg: Number($("error-log-tg").value || 0) || null,
      level: $("error-log-level").value || null,
      keyword: $("error-log-keyword").value.trim() || null,
    });
    state.bundle.error_logs = logs;
    renderErrorLogs(logs);
    adminStatus("错误日志已刷新。", "success");
  });

  $("artifact-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/artifact", {
      name: $("artifact-name").value.trim(),
      rarity: $("artifact-rarity").value,
      artifact_type: $("artifact-type").value,
      image_url: $("artifact-image").value.trim(),
      description: $("artifact-description").value.trim(),
      attack_bonus: Number($("artifact-attack").value || 0),
      defense_bonus: Number($("artifact-defense").value || 0),
      duel_rate_bonus: Number($("artifact-duel").value || 0),
      cultivation_bonus: Number($("artifact-cultivation").value || 0),
      min_realm_stage: $("artifact-stage").value || null,
      min_realm_layer: Number($("artifact-layer").value || 1),
    }), "创建成功", "法宝已加入修仙体系。");
    form?.reset?.();
    syncSelects();
  });

  $("talisman-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/talisman", {
      name: $("talisman-name").value.trim(), rarity: $("talisman-rarity").value, image_url: $("talisman-image").value.trim(),
      description: $("talisman-description").value.trim(), attack_bonus: Number($("talisman-attack").value || 0),
      defense_bonus: Number($("talisman-defense").value || 0), duel_rate_bonus: Number($("talisman-duel").value || 0),
      effect_uses: Number($("talisman-effect-uses")?.value || 1),
      min_realm_stage: $("talisman-stage").value || null, min_realm_layer: Number($("talisman-layer").value || 1),
    }), "创建成功", "符箓已加入修仙体系。");
    form?.reset?.();
    syncSelects();
  });

  $("pill-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/pill", {
      name: $("pill-name").value.trim(), pill_type: $("pill-type").value, image_url: $("pill-image").value.trim(),
      description: $("pill-description").value.trim(), effect_value: Number($("pill-effect").value || 0),
      poison_delta: Number($("pill-poison").value || 0), min_realm_stage: $("pill-stage").value || null,
      min_realm_layer: Number($("pill-layer").value || 1),
    }), "创建成功", "丹药已加入修仙体系。");
    form?.reset?.();
    updatePillEffectLabel();
    syncSelects();
  });

  $("sect-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/sect", {
      name: $("sect-name").value.trim(), description: $("sect-description").value.trim(), image_url: $("sect-image").value.trim(),
      min_realm_stage: $("sect-stage").value || null, min_realm_layer: Number($("sect-layer").value || 1),
      min_stone: Number($("sect-stone").value || 0), roles: collectSectRoles(),
    }), "创建成功", "宗门已建立。");
    form?.reset?.();
    $("sect-role-rows").innerHTML = "";
    ROLE_PRESETS.forEach(([role_key, role_name]) => addSectRoleRow({ role_key, role_name }));
  });

  $("sect-assign-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/sect/role", {
      tg: Number($("sect-assign-tg").value || 0), sect_id: Number($("sect-assign-id").value || 0), role_key: $("sect-assign-role").value,
    }), "任命成功", "宗门职位已更新。");
  });

  $("material-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/material", {
      name: $("material-name").value.trim(), quality_level: QUALITY_OPTIONS.indexOf($("material-quality").value) + 1,
      image_url: $("material-image").value.trim(), description: $("material-description").value.trim(),
    }), "创建成功", "材料已加入资源库。");
    form?.reset?.();
  });

  $("recipe-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/recipe", {
      name: $("recipe-name").value.trim(), recipe_kind: $("recipe-kind").value, result_kind: $("recipe-result-kind").value,
      result_ref_id: Number($("recipe-result-id").value || 0), result_quantity: Number($("recipe-result-quantity").value || 1),
      base_success_rate: Number($("recipe-success").value || 60),
      broadcast_on_success: $("recipe-broadcast").checked, ingredients: collectRecipeIngredients(),
    }), "创建成功", "配方已保存。");
    form?.reset?.();
    $("recipe-ingredient-rows").innerHTML = "";
    addRecipeIngredientRow();
  });

  $("scene-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/scene", {
      name: $("scene-name").value.trim(), description: $("scene-description").value.trim(), image_url: $("scene-image").value.trim(),
      max_minutes: Number($("scene-max-minutes").value || 60),
      min_realm_stage: $("scene-stage").value || null,
      min_realm_layer: Number($("scene-layer").value || 1),
      min_combat_power: Number($("scene-power").value || 0),
      event_pool: collectSceneEvents(),
      drops: collectSceneDrops(),
    }), "创建成功", "探索场景已保存。");
    form?.reset?.();
    $("scene-event-rows").innerHTML = "";
    $("scene-drop-rows").innerHTML = "";
    addSceneEventRow();
    addSceneDropRow();
  });

  $("encounter-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/encounter", {
      name: $("encounter-name").value.trim(),
      description: $("encounter-description").value.trim(),
      image_url: $("encounter-image").value.trim(),
      button_text: $("encounter-button-text").value.trim() || "争抢机缘",
      success_text: $("encounter-success-text").value.trim(),
      broadcast_text: $("encounter-broadcast-text").value.trim(),
      weight: Number($("encounter-weight").value || 1),
      active_seconds: Number($("encounter-active-seconds").value || 90),
      min_realm_stage: $("encounter-stage").value || null,
      min_realm_layer: Number($("encounter-layer").value || 1),
      min_combat_power: Number($("encounter-power").value || 0),
      reward_stone_min: Number($("encounter-stone-min").value || 0),
      reward_stone_max: Number($("encounter-stone-max").value || 0),
      reward_cultivation_min: Number($("encounter-cultivation-min").value || 0),
      reward_cultivation_max: Number($("encounter-cultivation-max").value || 0),
      reward_item_kind: $("encounter-item-kind").value || null,
      reward_item_ref_id: Number($("encounter-item-id").value || 0) || null,
      reward_item_quantity_min: Number($("encounter-item-quantity-min").value || 1),
      reward_item_quantity_max: Number($("encounter-item-quantity-max").value || 1),
      enabled: $("encounter-enabled").checked,
    }), "创建成功", "群内奇遇已保存。");
    form?.reset?.();
    syncSelects();
  });

  $("grant-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const tg = Number($("grant-tg").value || 0);
    const itemRefId = Number($("grant-ref-id").value || 0);
    if (!tg) {
      await popup("发放失败", "请先搜索并选择目标用户，或直接填写 TG ID。", "error");
      return;
    }
    if (!itemRefId) {
      await popup("发放失败", "请先选择要发放的物品。", "error");
      return;
    }
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/grant", {
      tg, item_kind: $("grant-kind").value,
      item_ref_id: itemRefId, quantity: Number($("grant-quantity").value || 1),
    }), "发放成功", "物品已发放到指定玩家。");
  });

  $("official-shop-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/shop/official", {
      item_kind: $("official-kind").value, item_ref_id: Number($("official-ref-id").value || 0),
      quantity: Number($("official-quantity").value || 1), price_stone: Number($("official-price").value || 0),
    }), "上架成功", "官方商店已更新。");
  });

  $("artifact-reset-btn")?.addEventListener("click", () => {
    resetArtifactForm();
  });

  document.body.addEventListener("click", async (event) => {
    const del = event.target.closest("[data-delete]");
    if (del) {
      const entity = del.dataset.delete;
      const id = Number(del.dataset.id || 0);
      try {
        await submitAndRefresh(() => request("DELETE", `/plugins/xiuxian/admin-api/${entity}/${id}`), "删除成功", "目标条目已删除。");
      } catch (error) {
        await popup("删除失败", String(error.message || error), "error");
      }
      return;
    }
    const edit = event.target.closest("[data-edit]");
    if (edit) {
      const entity = edit.dataset.edit;
      const id = Number(edit.dataset.id || 0);
      if (entity === "artifact") {
        const item = (state.bundle?.artifacts || []).find((row) => Number(row.id || 0) === id);
        if (!item) {
          await popup("编辑失败", "未找到目标法宝。", "error");
          return;
        }
        loadArtifactForm(item);
        $("artifact-form")?.scrollIntoView?.({ behavior: "smooth", block: "start" });
      }
      return;
    }
    const dispatch = event.target.closest("[data-encounter-dispatch]");
    if (dispatch) {
      try {
        await submitAndRefresh(
          () => request("POST", "/plugins/xiuxian/admin-api/encounter/dispatch", {
            template_id: Number(dispatch.dataset.encounterDispatch || 0),
          }),
          "投放成功",
          "奇遇已经推送到群里。",
        );
      } catch (error) {
        await popup("投放失败", String(error.message || error), "error");
      }
      return;
    }
    const toggle = event.target.closest("[data-shop-toggle]");
    if (toggle) {
      try {
        await submitAndRefresh(() => request("PATCH", `/plugins/xiuxian/admin-api/shop/${Number(toggle.dataset.shopToggle)}`, {
          enabled: toggle.dataset.nextEnabled === "true",
        }), "修改成功", "官方商品状态已更新。");
      } catch (error) {
        await popup("修改失败", String(error.message || error), "error");
      }
    }
  });

  bindUploadButtons();
  updatePillEffectLabel();
}

const _baseSyncSelects = syncSelects;
const _baseRenderWorld = renderWorld;

syncSelects = function syncSelectsEnhanced() {
  _baseSyncSelects();
  hydrateAdminForms();
  setOptions($("artifact-rarity"), qualityRows(), $("artifact-rarity")?.value);
  setOptions($("technique-rarity"), qualityRows(), $("technique-rarity")?.value);
  setOptions($("pill-rarity"), qualityRows(), $("pill-rarity")?.value);
  setOptions($("talisman-rarity"), qualityRows(), $("talisman-rarity")?.value);
  setOptions($("artifact-type"), [
    { value: "battle", label: "战斗法宝" },
    { value: "support", label: "辅助法宝" },
  ], $("artifact-type")?.value || "battle", null);
  setOptions($("pill-type"), PILL_TYPES.map((item) => ({ value: item.value, label: item.label })), $("pill-type")?.value || "foundation", null);
  syncAdminTaskFormState();
};

function syncAdminTaskFormState() {
  const taskType = $("admin-task-type")?.value || "custom";
  const isQuiz = taskType === "quiz";
  const title = $("admin-task-title");
  const description = $("admin-task-description");
  const pushGroup = $("admin-task-push-group");
  const maxClaimants = $("admin-task-max-claimants");
  const question = $("admin-task-question");
  const answer = $("admin-task-answer");
  if (pushGroup) {
    if (isQuiz) pushGroup.checked = true;
    pushGroup.disabled = isQuiz;
  }
  if (maxClaimants) {
    if (isQuiz) maxClaimants.value = "1";
    maxClaimants.disabled = isQuiz;
  }
  if (title) title.required = true;
  if (description) description.required = !isQuiz;
  if (question) question.required = isQuiz;
  if (answer) answer.required = isQuiz;
}

function uploadPermissionTarget() {
  return Number($("upload-permission-tg")?.value || 0);
}

async function submitUploadPermission(grant) {
  const tg = uploadPermissionTarget();
  if (!tg) {
    throw new Error("请先输入用户 TG ID");
  }
  const endpoint = grant
    ? "/plugins/xiuxian/admin-api/upload-permission/grant"
    : "/plugins/xiuxian/admin-api/upload-permission/revoke";
  const payload = await request("POST", endpoint, { tg });
  applyUploadPermissionUpdate(payload);
  if (grant) {
    const message = payload.builtin
      ? `TG ${tg} 是主人，默认已允许上传图片。`
      : `已为 TG ${tg} 开启图片上传权限。`;
    adminStatus(message, "success");
    await popup("授权成功", message);
    return;
  }
  const message = payload.removed
    ? `已移除 TG ${tg} 的图片上传权限。`
    : `TG ${tg} 当前没有额外授权记录。`;
  adminStatus(message, payload.removed ? "success" : "warning");
  await popup(payload.removed ? "移除成功" : "无需移除", message, payload.removed ? "success" : "warning");
}

function bindAttributeAwareSubmitters() {
  $("artifact-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    const artifactId = Number($("artifact-id")?.value || 0);
    const payload = collectArtifactPayload();
    try {
      await submitAndRefresh(
        () => request(
          artifactId > 0 ? "PATCH" : "POST",
          artifactId > 0 ? `/plugins/xiuxian/admin-api/artifact/${artifactId}` : "/plugins/xiuxian/admin-api/artifact",
          payload,
        ),
        artifactId > 0 ? "保存成功" : "创建成功",
        artifactId > 0 ? "法宝配置已更新。" : "法宝已经录入修仙体系。",
      );
      resetArtifactForm();
      syncSelects();
    } catch (error) {
      await popup("提交失败", String(error.message || error), "error");
    }
  }, true);

  $("talisman-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    const form = event.currentTarget;
    try {
      await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/talisman", {
        name: $("talisman-name").value.trim(),
        rarity: $("talisman-rarity")?.value || "凡品",
        image_url: $("talisman-image")?.value.trim() || "",
        description: $("talisman-description")?.value.trim() || "",
        ...affixPayload("talisman"),
        duel_rate_bonus: Number($("talisman-duel")?.value || 0),
        effect_uses: Number($("talisman-effect-uses")?.value || 1),
        combat_config: parseJsonInput($("talisman-combat-config")?.value || "{}", {}),
        min_realm_stage: $("talisman-stage")?.value || null,
        min_realm_layer: Number($("talisman-layer")?.value || 1),
      }), "创建成功", "符箓已经录入修仙体系。");
      form?.reset?.();
      syncSelects();
    } catch (error) {
      await popup("提交失败", String(error.message || error), "error");
    }
  }, true);

  $("pill-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    const form = event.currentTarget;
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/pill", {
      name: $("pill-name").value.trim(),
      rarity: $("pill-rarity")?.value || "凡品",
      pill_type: $("pill-type")?.value || "foundation",
      image_url: $("pill-image")?.value.trim() || "",
      description: $("pill-description")?.value.trim() || "",
      effect_value: Number($("pill-effect")?.value || 0),
      poison_delta: Number($("pill-poison")?.value || 0),
      ...affixPayload("pill"),
      min_realm_stage: $("pill-stage")?.value || null,
      min_realm_layer: Number($("pill-layer")?.value || 1),
    }), "创建成功", "丹药已经录入修仙体系。");
    form?.reset?.();
    syncSelects();
    updatePillEffectLabel();
  }, true);

  $("technique-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    const form = event.currentTarget;
    try {
      await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/technique", {
        name: $("technique-name").value.trim(),
        rarity: $("technique-rarity")?.value || "凡品",
        technique_type: $("technique-type")?.value || "balanced",
        image_url: $("technique-image")?.value.trim() || "",
        description: $("technique-description")?.value.trim() || "",
        ...affixPayload("technique"),
        duel_rate_bonus: Number($("technique-duel")?.value || 0),
        cultivation_bonus: Number($("technique-cultivation")?.value || 0),
        breakthrough_bonus: Number($("technique-breakthrough")?.value || 0),
        combat_config: parseJsonInput($("technique-combat-config")?.value || "{}", {}),
        min_realm_stage: $("technique-stage")?.value || null,
        min_realm_layer: Number($("technique-layer")?.value || 1),
      }), "创建成功", "功法已经录入修仙体系。");
      form?.reset?.();
      syncSelects();
    } catch (error) {
      await popup("提交失败", String(error.message || error), "error");
    }
  }, true);

$("task-admin-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  event.stopImmediatePropagation();
  const form = event.currentTarget;
  try {
    const result = await request("POST", "/plugins/xiuxian/admin-api/task", {
      title: $("admin-task-title").value.trim(),
      description: $("admin-task-description").value.trim(),
      task_scope: $("admin-task-scope").value,
      task_type: $("admin-task-type").value,
      question_text: $("admin-task-question").value.trim(),
      answer_text: $("admin-task-answer").value.trim(),
      image_url: $("admin-task-image").value.trim(),
      required_item_kind: $("admin-task-required-kind").value || null,
      required_item_ref_id: Number($("admin-task-required-id").value || 0) || null,
      required_item_quantity: Number($("admin-task-required-quantity").value || 0),
      reward_stone: Number($("admin-task-stone").value || 0),
      reward_item_kind: $("admin-task-item-kind").value || null,
      reward_item_ref_id: Number($("admin-task-item-id").value || 0) || null,
      reward_item_quantity: Number($("admin-task-item-quantity").value || 0),
      max_claimants: Number($("admin-task-max-claimants").value || 1),
      sect_id: Number($("admin-task-sect-id").value || 0) || null,
      active_in_group: $("admin-task-push-group").checked,
    });
    await bootstrapAdmin();
    const pushWarning = result?.push_warning;
    const message = pushWarning
      ? `任务《${result.title || "未命名任务"}》已创建，但群内推送失败。\n${pushWarning}`
      : "任务已经创建并按配置推送。";
    adminStatus(message, pushWarning ? "warning" : "success");
    await popup(pushWarning ? "创建已完成，但推送失败" : "发布成功", message, pushWarning ? "warning" : "success");
    form?.reset?.();
    syncSelects();
  } catch (error) {
    const message = String(error?.message || error || "任务发布失败");
    adminStatus(message, "error");
    await popup("发布失败", message, "error");
  }
}, true);

  $("upload-permission-grant")?.addEventListener("click", async () => {
    try {
      await submitUploadPermission(true);
    } catch (error) {
      const message = String(error.message || error);
      adminStatus(message, "error");
      await popup("上传失败", message, "error");
    }
  });

  $("upload-permission-revoke")?.addEventListener("click", async () => {
    try {
      await submitUploadPermission(false);
    } catch (error) {
      const message = String(error.message || error);
      adminStatus(message, "error");
      await popup("上传失败", message, "error");
    }
  });
}

function qualityBadgeHtml(label, color, className = "badge badge--normal") {
  const safeLabel = escapeHtml(label || "凡品");
  const style = buildDecorBadgeStyle(color, "#9ca3af");
  return `<span class="${className}" style="${style}">${safeLabel}</span>`;
}

renderWorld = function renderWorldEnhanced() {
  _baseRenderWorld();
  const bundle = state.bundle;
  if (!bundle) return;

  renderStack("artifact-list", (bundle.artifacts || []).map((item) => `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        <span class="badge badge--normal">${escapeHtml(item.artifact_type_label || item.artifact_type)}</span>
      </div>
      <p>${qualityBadgeHtml(item.rarity || "凡品", item.quality_color)} · ${escapeHtml(affixSummary(item))}${item.unique_item ? " · 唯一法宝" : ""}</p>
      <p>${escapeHtml(combatConfigSummary(item.combat_config || {}))}</p>
      <p>境界限制：${escapeHtml(item.min_realm_stage || "无限制")} ${escapeHtml(item.min_realm_layer || 1)} 层</p>
      <div class="inline-action-buttons">${editButton("artifact", item.id)}${deleteButton("artifact", item.id)}</div>
    </article>`).join("") || `<article class="stack-item"><strong>暂无法宝</strong></article>`);

  renderStack("talisman-list", (bundle.talismans || []).map((item) => `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        ${qualityBadgeHtml(item.rarity || "凡品", item.quality_color)}
      </div>
      <p>${escapeHtml(affixSummary(item))}</p>
      <p>斗法内最多显化 ${escapeHtml(item.effect_uses || 1)} 次</p>
      <p>${escapeHtml(combatConfigSummary(item.combat_config || {}))}</p>
      <div class="inline-action-buttons">${deleteButton("talisman", item.id)}</div>
    </article>`).join("") || `<article class="stack-item"><strong>暂无符箓</strong></article>`);

  renderStack("pill-list", (bundle.pills || []).map((item) => `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        ${qualityBadgeHtml(item.rarity || "凡品", item.quality_color)}
      </div>
      <p>${escapeHtml(item.pill_type_label || item.pill_type)} · ${escapeHtml(item.effect_value_label || "主效果")} ${escapeHtml(item.effect_value)} · 丹毒 ${escapeHtml(item.poison_delta)}</p>
      <p>${escapeHtml(affixSummary(item))}</p>
      <div class="inline-action-buttons">${deleteButton("pill", item.id)}</div>
    </article>`).join("") || `<article class="stack-item"><strong>暂无丹药</strong></article>`);

  renderStack("material-list", (bundle.materials || []).map((item) => `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        ${qualityBadgeHtml(item.quality_label || item.quality_level, item.quality_color)}
      </div>
      <p>${escapeHtml(item.quality_feature || item.quality_description || item.description || "暂无描述")}</p>
      <div class="inline-action-buttons">${deleteButton("material", item.id)}</div>
    </article>`).join("") || `<article class="stack-item"><strong>暂无材料</strong></article>`);

  renderStack("technique-list", (bundle.techniques || []).map((item) => `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        ${qualityBadgeHtml(item.rarity || "凡品", item.quality_color)}
      </div>
      <p>${escapeHtml(item.technique_type_label || item.technique_type)} · ${escapeHtml(affixSummary(item))}</p>
      <p>${escapeHtml(combatConfigSummary(item.combat_config || {}))}</p>
      <p>境界限制：${escapeHtml(item.min_realm_stage || "无限制")} ${escapeHtml(item.min_realm_layer || 1)} 层</p>
      <div class="inline-action-buttons">${deleteButton("technique", item.id)}</div>
    </article>`).join("") || `<article class="stack-item"><strong>暂无功法</strong></article>`);

  renderStack("task-list", (bundle.tasks || []).map((item) => {
    const requiredItemName = item.required_item?.name || item.required_item_kind_label || item.required_item_kind || "无";
    const requiredText = item.required_item_kind && Number(item.required_item_quantity || 0)
      ? `需提交：${requiredItemName} × ${item.required_item_quantity}`
      : "无需提交物品";
    return `
      <article class="stack-item">
        <div class="stack-item-head"><strong>${escapeHtml(item.title)}</strong><span class="badge badge--normal">${escapeHtml(item.task_scope_label || item.task_scope)}</span></div>
        <p>${escapeHtml(item.task_type_label || item.task_type)} · 领取 ${escapeHtml(item.claimants_count || 0)}/${escapeHtml(item.max_claimants || 1)} · 状态 ${escapeHtml(item.status)}</p>
        <p>${escapeHtml(requiredText)}</p>
        <div class="inline-action-buttons">${deleteButton("task", item.id)}</div>
      </article>`;
  }).join("") || `<article class="stack-item"><strong>暂无任务</strong></article>`);
};

/* ---------- Player Management ---------- */
const PLAYER_EDIT_FIELDS = [
  "spiritual_stone", "cultivation", "realm_stage", "realm_layer",
  "root_type", "root_primary", "root_secondary", "root_relation", "root_bonus", "root_quality",
  "bone", "comprehension", "divine_sense", "fortune", "willpower", "charisma", "karma",
  "qi_blood", "true_yuan", "body_movement", "attack_power", "defense_power",
  "dan_poison", "sect_contribution", "technique_capacity",
];

function playerDisplayName(profile = {}, fallbackTg = null) {
  const tg = Number(profile?.tg || fallbackTg || 0);
  return profile?.display_label || profile?.display_name || (profile?.username ? `@${profile.username}` : `TG ${tg || "未知"}`);
}

function techniqueRows() {
  return (state.bundle?.techniques || []).map((item) => ({ value: item.id, label: `${item.id} · ${item.name}` }));
}

function recipeRows() {
  return (state.bundle?.recipes || []).map((item) => ({ value: item.id, label: `${item.id} · ${item.name}` }));
}

function selectedPlayerAdminPath(path = "") {
  const tg = Number(state.selectedPlayerTg || $("player-edit-tg")?.value || 0);
  if (!tg) {
    throw new Error("请先选择角色");
  }
  return `/plugins/xiuxian/admin-api/players/${tg}${path}`;
}

function playerOwnedMeta(source, note) {
  const rows = [source, note].map((item) => String(item || "").trim()).filter(Boolean);
  return rows.length ? rows.join(" · ") : "后台未记录来源";
}

function playerFillInventoryButton(kind, itemId, quantity, boundQuantity = null) {
  const boundAttr = boundQuantity == null ? "" : ` data-player-fill-inventory-bound="${escapeHtml(boundQuantity)}"`;
  return `<button type="button" class="ghost" data-player-fill-inventory-kind="${escapeHtml(kind)}" data-player-fill-inventory-id="${escapeHtml(itemId)}" data-player-fill-inventory-quantity="${escapeHtml(quantity)}"${boundAttr}>载入库存表单</button>`;
}

function playerSelectionButton(label, selectionKind, itemRefId = null) {
  const refAttr = itemRefId == null ? "" : ` data-player-select-item-ref-id="${escapeHtml(itemRefId)}"`;
  return `<button type="button" class="ghost" data-player-select-kind="${escapeHtml(selectionKind)}"${refAttr}>${escapeHtml(label)}</button>`;
}

function playerRevokeButton(kind, itemRefId) {
  return `<button type="button" class="ghost" data-player-revoke-kind="${escapeHtml(kind)}" data-player-revoke-item-ref-id="${escapeHtml(itemRefId)}">移除</button>`;
}

function syncPlayerResourceForms() {
  const inventoryKindNode = $("player-inventory-kind");
  const inventoryRefNode = $("player-inventory-ref-id");
  const boundWrap = $("player-inventory-bound-wrap");
  const boundNode = $("player-inventory-bound");
  const inventoryKind = inventoryKindNode?.value || "artifact";
  const supportsBound = inventoryKind === "artifact" || inventoryKind === "talisman";
  if (boundWrap) boundWrap.style.display = supportsBound ? "" : "none";
  if (!supportsBound && boundNode) boundNode.value = "";
  setOptions(inventoryRefNode, itemRows(inventoryKind), inventoryRefNode?.value);

  const ownedKindNode = $("player-owned-kind");
  const ownedRefNode = $("player-owned-ref-id");
  const equipNode = $("player-owned-equip");
  const equipLabel = equipNode?.closest("label");
  const ownedKind = ownedKindNode?.value || "title";
  const ownedRows = ownedKind === "title" ? titleRows() : ownedKind === "technique" ? techniqueRows() : recipeRows();
  setOptions(ownedRefNode, ownedRows, ownedRefNode?.value);
  const canEquip = ownedKind !== "recipe";
  if (equipLabel) equipLabel.style.display = canEquip ? "" : "none";
  if (equipNode) {
    if (!canEquip) equipNode.checked = false;
    equipNode.disabled = !canEquip;
  }
}

function renderPlayerAccount(account) {
  const container = $("player-account-info");
  const panel = $("player-account-panel");
  if (!container || !panel) return;
  panel.style.display = "";
  if (!account) {
    container.innerHTML = `<p>当前角色未绑定 Emby 账户。</p>`;
    return;
  }
  container.innerHTML = `
    <p>账号名：${escapeHtml(account.name || "未设置")}</p>
    <p>Emby ID：${escapeHtml(account.embyid || "未设置")}</p>
    <p>等级：${escapeHtml(EMBY_LEVEL_LABELS[account.lv] || account.lv || "未设置")} · 片刻碎片：${escapeHtml(account.iv ?? 0)}</p>
    <p>到期时间：${escapeHtml(formatShanghaiDate(account.ex))}</p>
  `;
}

function playerSearchTotalPages() {
  const total = Number(state.playerSearch?.total || 0);
  const pageSize = Number(state.playerSearch?.pageSize || PLAYER_SEARCH_PAGE_SIZE);
  return Math.max(Math.ceil(total / pageSize), 1);
}

function renderPlayerSearchSummary(items = []) {
  const node = $("player-search-summary");
  if (!node) return;
  const total = Number(state.playerSearch?.total || 0);
  const page = Number(state.playerSearch?.page || 1);
  const pageSize = Number(state.playerSearch?.pageSize || PLAYER_SEARCH_PAGE_SIZE);
  const totalPages = playerSearchTotalPages();
  if (total <= 0) {
    node.textContent = "当前没有符合条件的角色。";
    return;
  }
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(start + items.length - 1, total);
  node.textContent = `共 ${total} 位角色，当前第 ${page}/${totalPages} 页，显示 ${start}-${end}。`;
}

function renderPlayerSearchPagination() {
  const pagination = $("player-search-pagination");
  const prevButton = $("player-page-prev");
  const nextButton = $("player-page-next");
  const jumpInput = $("player-page-jump-input");
  if (!pagination || !prevButton || !nextButton || !jumpInput) return;
  const total = Number(state.playerSearch?.total || 0);
  const page = Number(state.playerSearch?.page || 1);
  const totalPages = playerSearchTotalPages();
  const hasItems = total > 0;
  pagination.classList.toggle("hidden", !hasItems);
  prevButton.disabled = !hasItems || page <= 1;
  nextButton.disabled = !hasItems || page >= totalPages;
  jumpInput.min = "1";
  jumpInput.max = String(totalPages);
  jumpInput.placeholder = hasItems ? `输入 1-${totalPages}` : "暂无页码";
}

function bindPlayerSearchResultClicks(container) {
  container.querySelectorAll("[data-tg]").forEach((el) => {
    el.addEventListener("click", () => {
      openPlayerEdit(Number(el.dataset.tg)).catch((error) => popup("加载失败", String(error.message || error), "error"));
    });
  });
}

function renderPlayerSearchResults(items = state.playerSearch?.items || []) {
  const container = $("player-search-results");
  if (!container) return;
  if (!items.length) {
    container.innerHTML = `<article class="stack-item"><strong>未找到角色</strong></article>`;
    return;
  }
  container.innerHTML = items.map((p) => `
    <article class="stack-item is-clickable${Number(state.selectedPlayerTg || 0) === Number(p.tg) ? " is-selected" : ""}" data-tg="${p.tg}">
      <div class="stack-item-head">
        <strong>${escapeHtml(p.display_label || p.display_name || (p.username ? "@" + p.username : "TG " + p.tg))}</strong>
        <span class="badge">${escapeHtml(p.realm_stage || "炼气")} ${p.realm_layer || 0}层</span>
      </div>
      <p>灵石 ${p.spiritual_stone || 0} · 修为 ${p.cultivation || 0} · 片刻碎片 ${p.emby_account?.iv ?? 0}</p>
      <p>${escapeHtml(p.emby_account?.name || "未绑定 Emby")} · ${escapeHtml(p.emby_account?.embyid || "无 Emby ID")}</p>
    </article>
  `).join("");
  bindPlayerSearchResultClicks(container);
  highlightSelectedPlayerResult();
}

function applyPlayerSearchResult(data, { query = "", requestedPage = 1, pageSize = PLAYER_SEARCH_PAGE_SIZE } = {}) {
  const total = Math.max(Number(data?.total || 0), 0);
  const safePageSize = Math.max(Number(data?.page_size || pageSize), 1);
  const totalPages = Math.max(Math.ceil(total / safePageSize), 1);
  if (total > 0 && requestedPage > totalPages) {
    return { needsRefetch: true, refetchPage: totalPages };
  }
  const items = Array.isArray(data?.items) ? data.items : [];
  state.playerSearch = {
    query,
    page: Math.max(Number(data?.page || requestedPage), 1),
    pageSize: safePageSize,
    total,
    items,
  };
  renderPlayerSearchSummary(items);
  renderPlayerSearchPagination();
  renderPlayerSearchResults(items);
  return { needsRefetch: false, items };
}

function syncPlayerSearchItemFromDetail(detail = {}) {
  const profile = detail?.profile || detail;
  const tg = Number(profile?.tg || 0);
  if (!tg) return;
  const items = Array.isArray(state.playerSearch?.items) ? state.playerSearch.items.slice() : [];
  const index = items.findIndex((item) => Number(item?.tg || 0) === tg);
  if (index < 0) return;
  items[index] = {
    ...items[index],
    ...profile,
    emby_account: detail?.emby_account || profile?.emby_account || items[index]?.emby_account || null,
  };
  state.playerSearch = {
    ...(state.playerSearch || {}),
    items,
  };
  renderPlayerSearchSummary(items);
  renderPlayerSearchResults(items);
}

function renderPlayerInventory(detail = {}) {
  const root = $("player-inventory-list");
  if (!root) return;
  const artifactRows = Array.isArray(detail.artifacts) ? detail.artifacts : [];
  const pillRows = Array.isArray(detail.pills) ? detail.pills : [];
  const talismanRows = Array.isArray(detail.talismans) ? detail.talismans : [];
  const materialRowsList = Array.isArray(detail.materials) ? detail.materials : [];
  const parts = [];

  const artifactCards = artifactRows.map((row) => {
    const item = row.artifact || {};
    const actions = [
      playerFillInventoryButton("artifact", item.id, row.quantity || 0, row.bound_quantity ?? 0),
      playerSelectionButton(item.equipped ? "卸下法宝" : (item.action_label || "切换法宝"), "artifact", item.id),
    ];
    return `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(item.name || "未命名法宝")}</strong>
          ${qualityBadgeHtml(item.rarity || "凡品", item.quality_color)}
        </div>
        <p>${escapeHtml(item.equip_slot_label || item.equip_slot || "未知槽位")} · ${escapeHtml(item.artifact_role_label || item.artifact_role || "未分类")}</p>
        <p>总数 ${escapeHtml(row.quantity || 0)} · 绑定 ${escapeHtml(row.bound_quantity || 0)} · 可流通 ${escapeHtml(row.consumable_quantity || 0)} · ${item.equipped ? "已装备" : "未装备"}</p>
        <p>${escapeHtml(affixSummary(item))}</p>
        <div class="inline-action-buttons player-inline-actions">${actions.join("")}</div>
      </article>
    `;
  });
  parts.push(`
    <section class="stack-list">
      <article class="stack-item">
        <strong>法宝背包</strong>
        <p>${artifactRows.length ? `共 ${artifactRows.length} 类法宝` : "当前没有法宝库存"}</p>
      </article>
      ${artifactCards.join("") || `<article class="stack-item"><strong>暂无法宝</strong></article>`}
    </section>
  `);

  const pillCards = pillRows.map((row) => {
    const item = row.pill || {};
    return `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(item.name || "未命名丹药")}</strong>
          ${qualityBadgeHtml(item.rarity || "凡品", item.quality_color)}
        </div>
        <p>${escapeHtml(item.pill_type_label || item.pill_type || "丹药")} · 数量 ${escapeHtml(row.quantity || 0)}</p>
        <p>${escapeHtml(item.effect_value_label || "效果")} ${escapeHtml(item.effect_value || 0)} · 丹毒 ${escapeHtml(item.poison_delta || 0)}</p>
        <div class="inline-action-buttons player-inline-actions">${playerFillInventoryButton("pill", item.id, row.quantity || 0)}</div>
      </article>
    `;
  });
  parts.push(`
    <section class="stack-list">
      <article class="stack-item">
        <strong>丹药背包</strong>
        <p>${pillRows.length ? `共 ${pillRows.length} 类丹药` : "当前没有丹药库存"}</p>
      </article>
      ${pillCards.join("") || `<article class="stack-item"><strong>暂无丹药</strong></article>`}
    </section>
  `);

  const talismanCards = talismanRows.map((row) => {
    const item = row.talisman || {};
    const actions = [
      playerFillInventoryButton("talisman", item.id, row.quantity || 0, row.bound_quantity ?? 0),
      playerSelectionButton(item.active ? "清除待生效符箓" : "设为待生效符箓", "talisman", item.active ? null : item.id),
    ];
    return `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(item.name || "未命名符箓")}</strong>
          ${qualityBadgeHtml(item.rarity || "凡品", item.quality_color)}
        </div>
        <p>总数 ${escapeHtml(row.quantity || 0)} · 绑定 ${escapeHtml(row.bound_quantity || 0)} · 可流通 ${escapeHtml(row.consumable_quantity || 0)} · ${item.active ? "当前待生效" : "未预装"}</p>
        <p>${escapeHtml(affixSummary(item))}</p>
        <div class="inline-action-buttons player-inline-actions">${actions.join("")}</div>
      </article>
    `;
  });
  parts.push(`
    <section class="stack-list">
      <article class="stack-item">
        <strong>符箓背包</strong>
        <p>${talismanRows.length ? `共 ${talismanRows.length} 类符箓` : "当前没有符箓库存"}</p>
      </article>
      ${talismanCards.join("") || `<article class="stack-item"><strong>暂无符箓</strong></article>`}
    </section>
  `);

  const materialCards = materialRowsList.map((row) => {
    const item = row.material || {};
    return `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(item.name || "未命名材料")}</strong>
          ${qualityBadgeHtml(item.quality_label || item.quality_level || "凡品", item.quality_color)}
        </div>
        <p>数量 ${escapeHtml(row.quantity || 0)}</p>
        <p>${escapeHtml(item.description || item.quality_feature || "暂无描述")}</p>
        <div class="inline-action-buttons player-inline-actions">${playerFillInventoryButton("material", item.id, row.quantity || 0)}</div>
      </article>
    `;
  });
  parts.push(`
    <section class="stack-list">
      <article class="stack-item">
        <strong>材料背包</strong>
        <p>${materialRowsList.length ? `共 ${materialRowsList.length} 类材料` : "当前没有材料库存"}</p>
      </article>
      ${materialCards.join("") || `<article class="stack-item"><strong>暂无材料</strong></article>`}
    </section>
  `);

  root.innerHTML = parts.join("");
}

function renderPlayerTitles(detail = {}) {
  const root = $("player-title-list");
  if (!root) return;
  const rows = Array.isArray(detail.titles) ? detail.titles : [];
  root.innerHTML = rows.map((row) => {
    const item = row.title || {};
    const actions = [
      playerSelectionButton(item.equipped ? "卸下称号" : (item.action_label || "佩戴称号"), "title", item.equipped ? null : item.id),
      playerRevokeButton("title", item.id),
    ];
    return `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${titleColoredNameHtml(item.name || "未命名称号", item.color)}</strong>
          <span class="badge badge--normal">${item.equipped ? "已佩戴" : "未佩戴"}</span>
        </div>
        <p>${escapeHtml(item.description || "暂无称号描述")}</p>
        <p>${escapeHtml(adminTitleEffectSummary(item))}</p>
        <p>${escapeHtml(playerOwnedMeta(row.source, row.obtained_note))}</p>
        <div class="inline-action-buttons player-inline-actions">${actions.join("")}</div>
      </article>
    `;
  }).join("") || `<article class="stack-item"><strong>暂无称号</strong></article>`;
}

function renderPlayerTechniques(detail = {}) {
  const root = $("player-technique-list");
  if (!root) return;
  const rows = Array.isArray(detail.techniques) ? detail.techniques : [];
  root.innerHTML = rows.map((item) => {
    const actions = [
      playerSelectionButton(item.active ? "清空当前功法" : (item.action_label || "设为当前功法"), "technique", item.active ? null : item.id),
      playerRevokeButton("technique", item.id),
    ];
    return `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(item.name || "未命名功法")}</strong>
          ${qualityBadgeHtml(item.rarity || "凡品", item.quality_color)}
        </div>
        <p>${escapeHtml(item.technique_type_label || item.technique_type || "功法")} · ${item.active ? "当前参悟中" : "未设为当前"}</p>
        <p>${escapeHtml(affixSummary(item))}</p>
        <p>${escapeHtml(playerOwnedMeta(item.source, item.obtained_note))}</p>
        <div class="inline-action-buttons player-inline-actions">${actions.join("")}</div>
      </article>
    `;
  }).join("") || `<article class="stack-item"><strong>暂无功法</strong></article>`;
}

function renderPlayerRecipes(detail = {}) {
  const root = $("player-recipe-list");
  if (!root) return;
  const rows = Array.isArray(detail.recipes) ? detail.recipes : [];
  root.innerHTML = rows.map((row) => {
    const item = row.recipe || {};
    return `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(item.name || "未命名配方")}</strong>
          <span class="badge badge--normal">${escapeHtml(item.recipe_kind_label || item.recipe_kind || "配方")}</span>
        </div>
        <p>产出 ${escapeHtml(item.result_item?.name || item.result_kind_label || item.result_kind || "未知产物")} × ${escapeHtml(item.result_quantity || 1)} · 成功率 ${escapeHtml(item.base_success_rate || 0)}%</p>
        <p>${escapeHtml(playerOwnedMeta(row.source, row.obtained_note))}</p>
        <div class="inline-action-buttons player-inline-actions">${playerRevokeButton("recipe", item.id)}</div>
      </article>
    `;
  }).join("") || `<article class="stack-item"><strong>暂无配方</strong></article>`;
}

function applyPlayerDetail(data, { reveal = true, smooth = true } = {}) {
  const detail = data?.profile ? data : { profile: data || {} };
  const profile = detail.profile || {};
  const tg = Number(profile.tg || state.selectedPlayerTg || $("player-edit-tg")?.value || 0);
  if (!tg) return;
  state.selectedPlayerTg = tg;
  state.selectedPlayerDetail = detail;
  syncSelectedPlayerUI(playerDisplayName(profile, tg));
  applyGrantTargetPlayer(profile);
  $("player-edit-tg").value = String(tg);
  const titleNode = $("player-edit-title");
  if (titleNode) titleNode.textContent = `编辑: ${playerDisplayName(profile, tg)}`;
  renderPlayerAccount(detail.emby_account || profile.emby_account || null);
  PLAYER_EDIT_FIELDS.forEach((key) => {
    const el = $("pe-" + key);
    if (el) el.value = profile?.[key] ?? "";
  });
  renderPlayerInventory(detail);
  renderPlayerTitles(detail);
  renderPlayerTechniques(detail);
  renderPlayerRecipes(detail);
  syncPlayerSearchItemFromDetail(detail);
  syncPlayerResourceForms();
  highlightSelectedPlayerResult();
  if (reveal) revealPlayerEditor(smooth);
}

async function refreshSelectedPlayerDetail(options = {}) {
  const detail = await request("GET", selectedPlayerAdminPath(""));
  applyPlayerDetail(detail, options);
  return detail;
}

async function searchPlayers(options = {}) {
  const query = String(options.query ?? state.playerSearch?.query ?? "");
  const requestedPage = Math.max(Number(options.page ?? state.playerSearch?.page ?? 1), 1);
  const pageSize = Number(options.pageSize ?? state.playerSearch?.pageSize ?? PLAYER_SEARCH_PAGE_SIZE);
  const container = $("player-search-results");
  if (container) {
    container.innerHTML = `<article class="stack-item"><strong>正在加载角色...</strong></article>`;
  }
  const data = await request("GET", `/plugins/xiuxian/admin-api/players?q=${encodeURIComponent(query)}&page=${requestedPage}&page_size=${pageSize}`);
  const applied = applyPlayerSearchResult(data, { query, requestedPage, pageSize });
  if (applied.needsRefetch) {
    return searchPlayers({ query, page: applied.refetchPage, pageSize });
  }
  return applied.items || [];
}

async function openPlayerEdit(tg) {
  const data = await request("GET", `/plugins/xiuxian/admin-api/players/${tg}`);
  applyPlayerDetail(data);
}

async function submitPlayerEdit(e) {
  e.preventDefault();
  const tg = $("player-edit-tg").value;
  if (!tg) return;
  const payload = {};
  PLAYER_EDIT_FIELDS.forEach((key) => {
    const el = $("pe-" + key);
    if (!el) return;
    const raw = el.value;
    if (raw === "" || raw == null) return;
    payload[key] = PLAYER_STRING_FIELDS.has(key) ? raw : Number(raw);
  });
  try {
    const detail = await request("PATCH", `/plugins/xiuxian/admin-api/players/${tg}`, payload);
    applyPlayerDetail(detail, { reveal: false, smooth: false });
    await popup("操作成功", "角色属性已保存", "success");
    highlightSelectedPlayerResult();
    revealPlayerEditor(false);
  } catch (err) {
    await popup("保存失败", String(err.message || err), "error");
  }
}

async function submitPlayerInventoryEdit(event) {
  event.preventDefault();
  try {
    const itemRefId = Number($("player-inventory-ref-id")?.value || 0);
    if (!itemRefId) {
      throw new Error("请选择要调整的背包物品");
    }
    const detail = await request("POST", selectedPlayerAdminPath("/resource/inventory"), {
      item_kind: $("player-inventory-kind")?.value || "artifact",
      item_ref_id: itemRefId,
      quantity: Number($("player-inventory-quantity")?.value || 0),
      bound_quantity: $("player-inventory-bound")?.value === "" ? null : Number($("player-inventory-bound")?.value || 0),
    });
    applyPlayerDetail(detail, { reveal: false, smooth: false });
    await popup("背包已更新", "玩家背包库存已经保存。", "success");
  } catch (error) {
    await popup("保存失败", String(error.message || error), "error");
  }
}

async function submitPlayerOwnedGrant(event) {
  event.preventDefault();
  try {
    const itemRefId = Number($("player-owned-ref-id")?.value || 0);
    if (!itemRefId) {
      throw new Error("请选择要授予的条目");
    }
    const detail = await request("POST", selectedPlayerAdminPath("/resource/grant"), {
      item_kind: $("player-owned-kind")?.value || "title",
      item_ref_id: itemRefId,
      quantity: 1,
      equip: Boolean($("player-owned-equip")?.checked),
    });
    applyPlayerDetail(detail, { reveal: false, smooth: false });
    await popup("授予成功", "条目已经写入该角色。", "success");
  } catch (error) {
    await popup("授予失败", String(error.message || error), "error");
  }
}

async function submitPlayerBatchResource(event) {
  event.preventDefault();
  try {
    const itemRefId = Number($("player-batch-ref-id")?.value || 0);
    if (!itemRefId) {
      throw new Error("请选择要批量操作的条目");
    }
    const payload = {
      operation: $("player-batch-operation")?.value || "grant",
      item_kind: $("player-batch-kind")?.value || "artifact",
      item_ref_id: itemRefId,
      quantity: Number($("player-batch-quantity")?.value || 1),
      equip: Boolean($("player-batch-equip")?.checked),
      announce_in_group: Boolean($("player-batch-announce")?.checked),
    };
    const result = await request("POST", "/plugins/xiuxian/admin-api/players/resource/batch", payload);
    renderPlayerBatchResourceSummary(result);
    const actionLabel = payload.operation === "deduct" ? "扣除" : "发放";
    await popup(
      `批量${actionLabel}完成`,
      `成功 ${result.success_count || 0} 人，跳过 ${result.skipped_count || 0} 人，失败 ${result.failed_count || 0} 人。`,
      "success",
    );
  } catch (error) {
    await popup("批量操作失败", String(error.message || error), "error");
  }
}

async function handlePlayerResourceAction(event) {
  const fillButton = event.target.closest("[data-player-fill-inventory-kind]");
  if (fillButton) {
    $("player-inventory-kind").value = fillButton.dataset.playerFillInventoryKind || "artifact";
    syncPlayerResourceForms();
    $("player-inventory-ref-id").value = fillButton.dataset.playerFillInventoryId || "";
    $("player-inventory-quantity").value = fillButton.dataset.playerFillInventoryQuantity || "0";
    $("player-inventory-bound").value = fillButton.dataset.playerFillInventoryBound ?? "";
    $("player-inventory-quantity")?.focus?.();
    return;
  }

  const selectionButton = event.target.closest("[data-player-select-kind]");
  if (selectionButton) {
    try {
      const rawRefId = selectionButton.dataset.playerSelectItemRefId;
      const detail = await request("POST", selectedPlayerAdminPath("/resource/select"), {
        selection_kind: selectionButton.dataset.playerSelectKind,
        item_ref_id: rawRefId == null || rawRefId === "" ? null : Number(rawRefId),
      });
      applyPlayerDetail(detail, { reveal: false, smooth: false });
      await popup("配置已更新", "玩家当前佩戴/启用状态已经保存。", "success");
    } catch (error) {
      await popup("操作失败", String(error.message || error), "error");
    }
    return;
  }

  const revokeButton = event.target.closest("[data-player-revoke-kind]");
  if (revokeButton) {
    try {
      const detail = await request("POST", selectedPlayerAdminPath("/resource/revoke"), {
        item_kind: revokeButton.dataset.playerRevokeKind,
        item_ref_id: Number(revokeButton.dataset.playerRevokeItemRefId || 0),
      });
      applyPlayerDetail(detail, { reveal: false, smooth: false });
      await popup("移除成功", "玩家持有内容已经回收。", "success");
    } catch (error) {
      await popup("移除失败", String(error.message || error), "error");
    }
  }
}

document.getElementById("player-search-form")?.addEventListener("submit", (e) => {
  e.preventDefault();
  searchPlayers({
    query: $("player-search-q")?.value || "",
    page: 1,
  });
});
document.getElementById("player-page-prev")?.addEventListener("click", () => {
  searchPlayers({
    query: $("player-search-q")?.value || "",
    page: Math.max((state.playerSearch?.page || 1) - 1, 1),
  });
});
document.getElementById("player-page-next")?.addEventListener("click", () => {
  searchPlayers({
    query: $("player-search-q")?.value || "",
    page: Math.min((state.playerSearch?.page || 1) + 1, playerSearchTotalPages()),
  });
});
document.getElementById("player-page-jump-form")?.addEventListener("submit", (e) => {
  e.preventDefault();
  const jumpInput = $("player-page-jump-input");
  const totalPages = playerSearchTotalPages();
  const targetPage = Math.min(Math.max(Number(jumpInput?.value || 1), 1), totalPages);
  if (jumpInput) jumpInput.value = "";
  searchPlayers({
    query: $("player-search-q")?.value || "",
    page: targetPage,
  });
});
document.getElementById("player-edit-form")?.addEventListener("submit", submitPlayerEdit);
document.getElementById("player-batch-resource-form")?.addEventListener("submit", submitPlayerBatchResource);
document.getElementById("player-inventory-form")?.addEventListener("submit", submitPlayerInventoryEdit);
document.getElementById("player-owned-form")?.addEventListener("submit", submitPlayerOwnedGrant);
document.getElementById("player-batch-kind")?.addEventListener("change", syncPlayerBatchResourceForm);
document.getElementById("player-inventory-kind")?.addEventListener("change", syncPlayerResourceForms);
document.getElementById("player-owned-kind")?.addEventListener("change", syncPlayerResourceForms);
document.getElementById("player-edit-panel")?.addEventListener("click", (event) => {
  handlePlayerResourceAction(event);
});
document.getElementById("player-edit-cancel")?.addEventListener("click", () => {
  state.selectedPlayerTg = null;
  state.selectedPlayerDetail = null;
  $("player-edit-tg").value = "";
  $("player-edit-panel").classList.add("hidden");
  syncSelectedPlayerUI();
  highlightSelectedPlayerResult();
});
document.getElementById("jump-player-editor")?.addEventListener("click", () => {
  if (!state.selectedPlayerTg) return;
  revealPlayerEditor();
});

function renderSystemOpSummary(title, lines = [], tone = "info") {
  const root = $("system-op-summary");
  if (!root) return;
  const detail = (lines || []).filter(Boolean).map((line) => `<p>${escapeHtml(line)}</p>`).join("");
  root.innerHTML = `
    <strong>${escapeHtml(title || "最近一次系统操作")}</strong>
    ${detail || `<p class="muted">暂无附加信息。</p>`}
  `;
  root.dataset.tone = tone;
}

async function withAdminButtonBusy(button, pendingText, handler) {
  if (!button) return handler();
  const previous = button.textContent;
  button.disabled = true;
  button.textContent = pendingText;
  try {
    return await handler();
  } finally {
    button.disabled = false;
    button.textContent = previous;
  }
}

document.getElementById("system-reset-player-data")?.addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    const result = await withAdminButtonBusy(button, "清档中...", () =>
      request("POST", "/plugins/xiuxian/admin-api/system/reset-player-data")
    );
    state.selectedPlayerTg = null;
    state.selectedPlayerDetail = null;
    $("player-edit-tg").value = "";
    $("player-edit-panel")?.classList.add("hidden");
    syncSelectedPlayerUI();
    await bootstrapAdmin();
    const lines = Object.entries(result || {}).map(([key, value]) => `${key}: ${value}`);
    const profileCount = Number(result?.profiles || 0);
    renderSystemOpSummary("玩家修仙数据已清空", lines, "warning");
    adminStatus("所有玩家修仙数据已清空。", "warning");
    await popup("清档完成", profileCount > 0 ? `已清空 ${profileCount} 个玩家档案，详细统计已写入页面。` : "所有玩家修仙数据已清空，详细统计已写入页面。", "warning");
  } catch (error) {
    const message = String(error.message || error);
    renderSystemOpSummary("玩家数据清档失败", [message], "error");
    adminStatus(message, "error");
    await popup("清档失败", message, "error");
  }
});

ADMIN_SECTION_LABELS.titles = "称号";
ADMIN_SECTION_LABELS.achievements = "成就";

function adminTitleEffectSummary(item = {}) {
  const rows = [];
  if (Number(item.attack_bonus || 0)) rows.push(`攻击 ${item.attack_bonus}`);
  if (Number(item.defense_bonus || 0)) rows.push(`防御 ${item.defense_bonus}`);
  if (Number(item.bone_bonus || 0)) rows.push(`根骨 ${item.bone_bonus}`);
  if (Number(item.comprehension_bonus || 0)) rows.push(`悟性 ${item.comprehension_bonus}`);
  if (Number(item.divine_sense_bonus || 0)) rows.push(`神识 ${item.divine_sense_bonus}`);
  if (Number(item.fortune_bonus || 0)) rows.push(`机缘 ${item.fortune_bonus}`);
  if (Number(item.qi_blood_bonus || 0)) rows.push(`气血 ${item.qi_blood_bonus}`);
  if (Number(item.true_yuan_bonus || 0)) rows.push(`真元 ${item.true_yuan_bonus}`);
  if (Number(item.body_movement_bonus || 0)) rows.push(`身法 ${item.body_movement_bonus}`);
  if (Number(item.duel_rate_bonus || 0)) rows.push(`斗法 ${item.duel_rate_bonus}%`);
  if (Number(item.cultivation_bonus || 0)) rows.push(`修炼 ${item.cultivation_bonus}`);
  if (Number(item.breakthrough_bonus || 0)) rows.push(`突破 ${item.breakthrough_bonus}`);
  return rows.join(" · ") || "暂无额外效果";
}

function adminRewardSummary(config = {}) {
  const rows = [];
  if (Number(config.spiritual_stone || 0)) rows.push(`灵石 ${config.spiritual_stone}`);
  if (Number(config.cultivation || 0)) rows.push(`修为 ${config.cultivation}`);
  if (Array.isArray(config.titles) && config.titles.length) rows.push(`称号 ${config.titles.join(", ")}`);
  if (Array.isArray(config.items) && config.items.length) {
    rows.push(config.items.map((item) => `${item.kind || "item"}#${item.ref_id || item.item_ref_id} x${item.quantity || 0}`).join("、"));
  }
  if (config.message) rows.push(String(config.message));
  return rows.join(" · ") || "无额外奖励";
}

function renderTitleColorSwatches(targetId, presets, wide = false) {
  const root = $(targetId);
  if (!root) return;
  root.innerHTML = presets.map((item) => {
    const previewStyle = escapeHtml(`background:${normalizeDecorColor(item.value, TITLE_COLOR_DEFAULT)};`);
    const value = escapeHtml(item.value);
    if (wide) {
      return `
        <button type="button" class="title-color-swatch title-color-swatch--wide" data-title-color-value="${value}" title="${escapeHtml(item.label)}">
          <span class="title-color-swatch-bar" style="${previewStyle}"></span>
          <span class="title-color-swatch-title">${escapeHtml(item.label)}</span>
        </button>
      `;
    }
    return `
      <button type="button" class="title-color-swatch" data-title-color-value="${value}" title="${escapeHtml(item.label)}">
        <span class="title-color-swatch-chip" style="${previewStyle}"></span>
      </button>
    `;
  }).join("");
}

function updateTitleColorPresetState(value) {
  const safeColor = normalizeDecorColor(value, "");
  document.querySelectorAll("[data-title-color-value]").forEach((button) => {
    button.classList.toggle("is-active", safeColor && button.dataset.titleColorValue === safeColor);
  });
}

function syncTitleColorControls(value) {
  const safeColor = normalizeDecorColor(value, "");
  const solidColor = !isGradientDecorColor(safeColor) ? safeColor : extractGradientMeta(safeColor).start;
  if ($("title-solid-color")) {
    $("title-solid-color").value = toColorPickerHex(solidColor, TITLE_COLOR_DEFAULT);
  }
  const gradient = extractGradientMeta(safeColor);
  if ($("title-gradient-start")) $("title-gradient-start").value = gradient.start;
  if ($("title-gradient-end")) $("title-gradient-end").value = gradient.end;
  if ($("title-gradient-angle")) $("title-gradient-angle").value = String(gradient.angle);
  if ($("title-gradient-angle-value")) $("title-gradient-angle-value").textContent = `${gradient.angle}°`;
}

function updateTitleColorPreview() {
  const rawValue = $("title-color")?.value?.trim() || "";
  const safeColor = normalizeDecorColor(rawValue, "");
  const previewName = $("title-color-preview-name");
  const previewBadge = $("title-color-preview-badge");
  const previewCode = $("title-color-preview-code");
  const titleName = $("title-name")?.value?.trim() || "斗战真君";
  if (previewName) {
    previewName.innerHTML = titleColoredNameHtml(titleName, safeColor);
  }
  if (previewBadge) {
    previewBadge.setAttribute("style", buildDecorBadgeStyle(safeColor || "#9ca3af"));
    previewBadge.textContent = safeColor ? (isGradientDecorColor(safeColor) ? "渐变预览" : "纯色预览") : "默认配色";
  }
  if (previewCode) {
    previewCode.textContent = rawValue
      ? (safeColor ? `当前值：${rawValue}` : `当前值：${rawValue}（当前写法无法预览，将按默认配色显示）`)
      : "当前值：默认";
  }
}

function setTitleColorMode(mode) {
  titleColorEditorMode = ["solid", "gradient", "rainbow"].includes(mode) ? mode : "solid";
  document.querySelectorAll("[data-title-color-mode]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.titleColorMode === titleColorEditorMode);
  });
  document.querySelectorAll("[data-title-color-panel]").forEach((panel) => {
    panel.classList.toggle("is-hidden", panel.dataset.titleColorPanel !== titleColorEditorMode);
  });
}

function refreshTitleColorEditor(mode = "") {
  const input = $("title-color");
  if (!input) return;
  const rawValue = input.value.trim();
  syncTitleColorControls(rawValue);
  setTitleColorMode(mode || inferTitleColorMode(rawValue));
  updateTitleColorPresetState(rawValue);
  updateTitleColorPreview();
}

function applyTitleColorValue(value, mode = "") {
  if ($("title-color")) {
    $("title-color").value = String(value || "").trim();
  }
  refreshTitleColorEditor(mode);
}

function applyGradientBuilderValue() {
  applyTitleColorValue(
    buildLinearGradient(
      $("title-gradient-start")?.value || TITLE_COLOR_DEFAULT,
      $("title-gradient-end")?.value || TITLE_GRADIENT_DEFAULT_END,
      $("title-gradient-angle")?.value || 135,
    ),
    "gradient",
  );
}

function initTitleColorEditor() {
  const root = $("title-color-editor");
  const input = $("title-color");
  if (!root || !input || input.dataset.paletteReady === "1") return;
  input.dataset.paletteReady = "1";
  renderTitleColorSwatches("title-solid-swatches", TITLE_SOLID_SWATCHES);
  renderTitleColorSwatches("title-gradient-presets", TITLE_GRADIENT_PRESETS, true);
  renderTitleColorSwatches("title-rainbow-presets", TITLE_RAINBOW_PRESETS, true);

  root.addEventListener("click", (event) => {
    const modeButton = event.target.closest("[data-title-color-mode]");
    if (modeButton) {
      const nextMode = modeButton.dataset.titleColorMode || "solid";
      if (nextMode === inferTitleColorMode($("title-color")?.value || "")) {
        setTitleColorMode(nextMode);
        return;
      }
      if (nextMode === "solid") {
        applyTitleColorValue($("title-solid-color")?.value || TITLE_COLOR_DEFAULT, "solid");
      } else if (nextMode === "gradient") {
        applyGradientBuilderValue();
      } else {
        applyTitleColorValue(TITLE_RAINBOW_PRESETS[0]?.value || "", "rainbow");
      }
      return;
    }

    const presetButton = event.target.closest("[data-title-color-value]");
    if (presetButton) {
      const value = presetButton.dataset.titleColorValue || "";
      applyTitleColorValue(value, inferTitleColorMode(value));
      return;
    }

    if (event.target.id === "title-color-clear") {
      applyTitleColorValue("", "solid");
    }
  });

  input.addEventListener("input", () => refreshTitleColorEditor());
  $("title-name")?.addEventListener("input", () => updateTitleColorPreview());
  $("title-solid-color")?.addEventListener("input", () => applyTitleColorValue($("title-solid-color").value, "solid"));
  $("title-gradient-start")?.addEventListener("input", applyGradientBuilderValue);
  $("title-gradient-end")?.addEventListener("input", applyGradientBuilderValue);
  $("title-gradient-angle")?.addEventListener("input", () => {
    if ($("title-gradient-angle-value")) {
      $("title-gradient-angle-value").textContent = `${clampGradientAngle($("title-gradient-angle").value)}°`;
    }
    applyGradientBuilderValue();
  });

  refreshTitleColorEditor();
  window.refreshTitleColorEditor = refreshTitleColorEditor;
}

function renderAchievementMetricOptions() {
  const root = $("achievement-metric-options");
  if (!root) return;
  const rows = state.bundle?.achievement_metric_presets || [];
  root.innerHTML = rows.map((item) => `<option value="${escapeHtml(item.key)}">${escapeHtml(item.label || item.key)}</option>`).join("");
}

function titleRows() {
  return (state.bundle?.titles || []).map((item) => ({ value: item.id, label: `${item.id} · ${item.name}` }));
}

const baseSyncSelectsWithTitles = syncSelects;
syncSelects = function syncSelectsWithAchievementTitle() {
  baseSyncSelectsWithTitles();
  setOptions($("title-grant-id"), titleRows(), $("title-grant-id")?.value);
  syncPlayerResourceForms();
  syncPlayerBatchResourceForm();
  renderAchievementMetricOptions();
};

function renderTitleAdminList() {
  renderStack("title-list", (state.bundle?.titles || []).map((item) => `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${titleColoredNameHtml(item.name, item.color)}</strong>
        <span class="badge badge--normal">${item.enabled ? "启用中" : "已停用"}</span>
      </div>
      <p>${escapeHtml(item.description || "暂无称号描述")}</p>
      <p>${escapeHtml(adminTitleEffectSummary(item))}</p>
      <p class="quality-line">${titleColorBadgeHtml(item.color ? "称号预览" : "默认配色", item.color || "")}<span class="field-note">颜色 ${escapeHtml(summarizeDecorColor(item.color))} · ID ${escapeHtml(item.id)}</span></p>
      <div class="inline-action-buttons">${deleteButton("title", item.id)}</div>
    </article>
  `).join("") || `<article class="stack-item"><strong>暂无称号</strong></article>`);
}

function renderAchievementAdminList() {
  renderStack("achievement-list", (state.bundle?.achievements || []).map((item) => `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        <span class="badge badge--normal">${item.enabled ? "启用中" : "已停用"}</span>
      </div>
      <p>Key ${escapeHtml(item.achievement_key || "auto")} · 统计项 ${escapeHtml(item.metric_key)} · 目标 ${escapeHtml(item.target_value)}</p>
      <p>${escapeHtml(item.description || "暂无成就描述")}</p>
      <p>奖励：${escapeHtml(adminRewardSummary(item.reward_config || {}))}</p>
      <p>通知：群 ${item.notify_group ? "开" : "关"} / 私 ${item.notify_private ? "开" : "关"}</p>
      <div class="inline-action-buttons">${deleteButton("achievement", item.id)}</div>
    </article>
  `).join("") || `<article class="stack-item"><strong>暂无成就</strong></article>`);
}

const baseRenderWorldWithAchievementTitle = renderWorld;
renderWorld = function renderWorldWithAchievementTitle() {
  baseRenderWorldWithAchievementTitle();
  renderTitleAdminList();
  renderAchievementAdminList();
};

function parseRewardConfigInput() {
  const raw = $("achievement-reward-config")?.value?.trim() || "";
  if (!raw) return {};
  return JSON.parse(raw);
}

document.getElementById("title-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = $("title-name")?.value.trim() || "";
  const imageUrl = setAdminInputValue("title-image", $("title-image")?.value || "");
  if (!name) {
    await popup("提交失败", "请先填写称号名称。", "error");
    return;
  }
  try {
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/title", {
      name,
      description: $("title-description").value.trim(),
      color: $("title-color").value.trim(),
      image_url: imageUrl,
      attack_bonus: Number($("title-attack").value || 0),
      defense_bonus: Number($("title-defense").value || 0),
      bone_bonus: Number($("title-bone").value || 0),
      comprehension_bonus: Number($("title-comprehension").value || 0),
      divine_sense_bonus: Number($("title-divine-sense").value || 0),
      fortune_bonus: Number($("title-fortune").value || 0),
      qi_blood_bonus: Number($("title-qi-blood").value || 0),
      true_yuan_bonus: Number($("title-true-yuan").value || 0),
      body_movement_bonus: Number($("title-body-movement").value || 0),
      duel_rate_bonus: Number($("title-duel").value || 0),
      cultivation_bonus: Number($("title-cultivation").value || 0),
      breakthrough_bonus: Number($("title-breakthrough").value || 0),
      enabled: $("title-enabled").checked,
    }), "保存成功", "称号已写入修仙系统。");
  } catch (error) {
    await popup("提交失败", String(error.message || error), "error");
  }
});

document.getElementById("title-grant-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/title/grant", {
    tg: Number($("title-grant-tg").value || 0),
    title_id: Number($("title-grant-id").value || 0),
    equip: $("title-grant-equip").checked,
  }), "发放成功", "称号已经发放给目标用户。");
});

document.getElementById("achievement-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  let rewardConfig = {};
  try {
    rewardConfig = parseRewardConfigInput();
  } catch (error) {
    await popup("奖励配置错误", "奖励 JSON 不是合法格式。", "error");
    return;
  }
  await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/achievement", {
    achievement_key: $("achievement-key").value.trim() || null,
    name: $("achievement-name").value.trim(),
    description: $("achievement-description").value.trim(),
    metric_key: $("achievement-metric-key").value.trim(),
    target_value: Number($("achievement-target").value || 1),
    reward_config: rewardConfig,
    notify_group: $("achievement-notify-group").checked,
    notify_private: $("achievement-notify-private").checked,
    enabled: $("achievement-enabled").checked,
    sort_order: Number($("achievement-sort").value || 0),
  }), "创建成功", "成就规则已经保存。");
});

document.getElementById("achievement-progress-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const metricKey = $("achievement-progress-key").value.trim();
  const amount = Number($("achievement-progress-amount").value || 0);
  const result = await request("POST", "/plugins/xiuxian/admin-api/achievement/progress", {
    tg: Number($("achievement-progress-tg").value || 0),
    increments: metricKey ? { [metricKey]: amount } : {},
    source: $("achievement-progress-source").value.trim() || null,
  });
  await bootstrapAdmin();
  const unlocked = result?.unlocks || [];
  await popup(
    "补录完成",
    unlocked.length
      ? `进度已补录，并触发 ${unlocked.length} 个成就：${unlocked.map((item) => item.achievement?.name || "未命名成就").join("、")}`
      : "进度已补录，当前没有新成就达成。",
  );
});

ROLE_PRESETS.forEach(([role_key, role_name]) => addSectRoleRow({ role_key, role_name }));
addRecipeIngredientRow();
addSceneEventRow();
addSceneDropRow();
addGamblingPoolRow();
ensureSettingRuleRows();
bindEvents();
bindAttributeAwareSubmitters();
hydrateAdminForms();
if ($("title-form")) {
  $("title-form").noValidate = true;
}
window.setAdminInputValue = setAdminInputValue;
window.normalizeAdminUrlValue = normalizeAdminUrlValue;
renderAdminNavigator();
syncSelectedPlayerUI();
tg?.ready?.();
tg?.expand?.();
tg?.setHeaderColor?.("#f8f9fa");
tg?.setBackgroundColor?.("#f8f9fa");
setupBackNavigation();
window.addEventListener("beforeunload", () => {
  tgBackButton?.offClick?.(handleBackNavigation);
});
bootstrapAdmin().catch(async (error) => {
  adminStatus(String(error.message || error), "error");
  await popup("初始化失败", String(error.message || error), "error");
});
