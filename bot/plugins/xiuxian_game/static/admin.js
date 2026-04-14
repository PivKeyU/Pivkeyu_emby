const tg = window.Telegram?.WebApp;
const tgBackButton = tg?.BackButton || null;
const DEFAULT_BACK_PATH = "/admin";

const REALM_OPTIONS = ["凡人", "炼气", "筑基", "结丹", "元婴", "化神", "须弥", "芥子", "混元一体"];
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
  },
};
const backState = {
  fallbackPath: DEFAULT_BACK_PATH,
  returnTo: "",
  referrerPath: ""
};

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

REALM_OPTIONS.splice(0, REALM_OPTIONS.length, "凡人", "炼气", "筑基", "结丹", "元婴", "化神", "须弥", "芥子", "混元一体");
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

function parseJsonInput(raw, fallback = {}) {
  const text = String(raw ?? "").trim();
  if (!text) return fallback;
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error(`JSON 解析失败: ${error.message}`);
  }
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

async function popup(title, message, tone = "success") {
  touch(tone);
  if (tg?.showPopup) {
    await tg.showPopup({ title, message, buttons: [{ type: "close", text: "知道了" }] });
    return;
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

function itemRows(kind) {
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
  return rows.map((item) => {
    const data = item.material || item;
    return { value: data.id, label: `${data.id} · ${data.name}` };
  });
}

function sectRows() {
  return (state.bundle?.sects || []).map((row) => ({ value: row.id, label: `${row.id} · ${row.name}` }));
}

function materialRows() {
  return (state.bundle?.materials || []).map((row) => ({ value: row.id, label: `${row.id} · ${row.name}` }));
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
  setOptions($("pill-type"), PILL_TYPES.map((item) => ({ value: item.value, label: item.label })), $("pill-type")?.value || "foundation", null);
  ensureAffixFields("artifact", true, true);
  ensureAffixFields("pill");
  ensureAffixFields("talisman");
  ensureAffixFields("technique", false, true);
}

function bindUploadButtons() {
  document.querySelectorAll("[data-upload-file]").forEach((button) => {
    button.onclick = async () => {
      const file = $(button.dataset.uploadFile)?.files?.[0];
      const target = $(button.dataset.uploadTarget);
      try {
        const payload = await uploadImage(file, button.dataset.uploadFolder || "admin");
        if (target) target.value = payload.url || payload.relative_url;
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
    <p>奖励：灵石 ${escapeHtml(item.reward_stone_min || 0)}-${escapeHtml(item.reward_stone_max || 0)} · 修为 ${escapeHtml(item.reward_cultivation_min || 0)}-${escapeHtml(item.reward_cultivation_max || 0)} · 心志 ${escapeHtml(item.reward_willpower || 0)} · 魅力 ${escapeHtml(item.reward_charisma || 0)} · 因果 ${escapeHtml(item.reward_karma || 0)}</p>
    <div class="inline-action-buttons">${encounterDispatchButton(item.id)}${deleteButton("encounter", item.id)}</div></article>`).join("") || `<article class="stack-item"><strong>暂无奇遇</strong></article>`);

  renderStack("sect-list", (bundle.sects || []).map((item) => `
    <article class="stack-item"><div class="stack-item-head"><strong>${escapeHtml(item.name)}</strong><span class="badge badge--normal">${escapeHtml((item.roles || []).length)} 个职位</span></div>
    <p>${escapeHtml(item.description || "暂无宗门简介")}</p><p>门槛：${escapeHtml(item.min_realm_stage || "无限制")} ${escapeHtml(item.min_realm_layer || 1)} 层 · 灵石 ${escapeHtml(item.min_stone)}</p>
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
  setOptions($("grant-ref-id"), itemRows($("grant-kind")?.value || "artifact"), $("grant-ref-id")?.value);
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
}

function applySettings(settings = {}) {
  ensureSettingRuleRows();
  $("setting-rate").value = settings.coin_exchange_rate ?? 100;
  $("setting-fee").value = settings.exchange_fee_percent ?? 1;
  $("setting-min").value = settings.min_coin_exchange ?? 1;
  $("setting-duel-minutes").value = settings.duel_bet_minutes ?? 2;
  $("setting-duel-steal").value = settings.duel_winner_steal_percent ?? 25;
  $("setting-artifact-plunder").value = settings.artifact_plunder_chance ?? 20;
  $("setting-message-auto-delete").value = settings.message_auto_delete_seconds ?? 180;
  $("setting-unbind-cost").value = settings.equipment_unbind_cost ?? 100;
  $("setting-broadcast").value = settings.shop_broadcast_cost ?? 20;
  $("setting-shop-name").value = settings.official_shop_name ?? "官方商店";
  $("setting-task-publish-cost").value = settings.task_publish_cost ?? 20;
  $("setting-allow-user-task-publish").checked = settings.allow_user_task_publish ?? true;
  if ($("official-shop-name")) $("official-shop-name").value = settings.official_shop_name ?? "官方商店";
  $("setting-artifact-limit").value = settings.artifact_equip_limit ?? 3;
  $("setting-user-upload").checked = Boolean(settings.allow_non_admin_image_upload);
  $("setting-chat-chance").value = settings.chat_cultivation_chance ?? 8;
  $("setting-chat-min").value = settings.chat_cultivation_min_gain ?? 1;
  $("setting-chat-max").value = settings.chat_cultivation_max_gain ?? 3;
  $("setting-robbery-limit").value = settings.robbery_daily_limit ?? 3;
  $("setting-robbery-max").value = settings.robbery_max_steal ?? 180;
  $("setting-quality-broadcast").value = settings.high_quality_broadcast_level ?? 4;
  $("setting-slave-tribute").value = settings.slave_tribute_percent ?? 20;
  $("setting-slave-cooldown").value = settings.slave_challenge_cooldown_hours ?? 24;
  applyRootQualityRules(settings);
  applyItemQualityRules(settings);
  applyDropWeightRules(settings);
}

async function bootstrapAdmin(forceToken = false) {
  const payload = {};
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
  renderWorld();
  await searchPlayers({
    query: $("player-search-q")?.value || "",
    page: state.playerSearch?.page || 1,
  });
  renderAdminNavigator();
  adminStatus(`修仙后台已就绪，当前管理数据加载完成。`, "success");
}

async function submitAndRefresh(handler, successTitle, successMessage) {
  await handler();
  await bootstrapAdmin();
  await popup(successTitle, successMessage);
}

function bindEvents() {
  $("pill-type")?.addEventListener("change", updatePillEffectLabel);
  $("recipe-result-kind")?.addEventListener("change", syncSelects);
  $("grant-kind")?.addEventListener("change", syncSelects);
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

  $("token-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    state.token = $("admin-token").value.trim();
    localStorage.setItem("xiuxian_admin_token", state.token);
    await bootstrapAdmin(true);
  });

  $("settings-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/settings", {
      coin_exchange_rate: Number($("setting-rate").value || 100),
      exchange_fee_percent: Number($("setting-fee").value || 1),
      min_coin_exchange: Number($("setting-min").value || 1),
      message_auto_delete_seconds: Number($("setting-message-auto-delete").value || 0),
      shop_broadcast_cost: Number($("setting-broadcast").value || 20),
      official_shop_name: $("setting-shop-name").value.trim(),
      task_publish_cost: Number($("setting-task-publish-cost").value || 0),
      allow_user_task_publish: $("setting-allow-user-task-publish").checked,
      allow_non_admin_image_upload: $("setting-user-upload").checked,
      chat_cultivation_chance: Number($("setting-chat-chance").value || 8),
      chat_cultivation_min_gain: Number($("setting-chat-min").value || 1),
      chat_cultivation_max_gain: Number($("setting-chat-max").value || 3),
      robbery_daily_limit: Number($("setting-robbery-limit").value || 3),
      robbery_max_steal: Number($("setting-robbery-max").value || 180),
      root_quality_value_rules: collectRootQualityRules(),
      item_quality_value_rules: collectItemQualityRules(),
      exploration_drop_weight_rules: collectDropWeightRules(),
    }), "保存成功", "基础规则已更新。");
  });

  $("setting-shop-name")?.addEventListener("input", (event) => {
    if ($("official-shop-name")) {
      $("official-shop-name").value = event.currentTarget?.value?.trim?.() || "";
    }
  });

  $("duel-settings-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/settings", {
      duel_bet_minutes: Number($("setting-duel-minutes").value || 2),
      duel_winner_steal_percent: Number($("setting-duel-steal").value || 25),
      artifact_plunder_chance: Number($("setting-artifact-plunder").value || 20),
      equipment_unbind_cost: Number($("setting-unbind-cost").value || 0),
      artifact_equip_limit: Number($("setting-artifact-limit").value || 3),
      high_quality_broadcast_level: Number($("setting-quality-broadcast").value || 4),
      slave_tribute_percent: Number($("setting-slave-tribute").value || 20),
      slave_challenge_cooldown_hours: Number($("setting-slave-cooldown").value || 24),
    }), "保存成功", "斗法与装备规则已更新。");
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
      reward_willpower: Number($("encounter-willpower").value || 0),
      reward_charisma: Number($("encounter-charisma").value || 0),
      reward_karma: Number($("encounter-karma").value || 0),
      enabled: $("encounter-enabled").checked,
    }), "创建成功", "群内奇遇已保存。");
    form?.reset?.();
    syncSelects();
  });

  $("task-admin-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/task", {
      title: $("admin-task-title").value.trim(), description: $("admin-task-description").value.trim(), task_scope: $("admin-task-scope").value,
      task_type: $("admin-task-type").value, question_text: $("admin-task-question").value.trim(), answer_text: $("admin-task-answer").value.trim(),
      image_url: $("admin-task-image").value.trim(), reward_stone: Number($("admin-task-stone").value || 0),
      reward_item_kind: $("admin-task-item-kind").value || null, reward_item_ref_id: Number($("admin-task-item-id").value || 0) || null,
      reward_item_quantity: Number($("admin-task-item-quantity").value || 0), max_claimants: Number($("admin-task-max-claimants").value || 1),
      sect_id: Number($("admin-task-sect-id").value || 0) || null, active_in_group: $("admin-task-push-group").checked,
    }), "发布成功", "任务已经创建并按配置推送。");
    form?.reset?.();
  });

  $("grant-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/grant", {
      tg: Number($("grant-tg").value || 0), item_kind: $("grant-kind").value,
      item_ref_id: Number($("grant-ref-id").value || 0), quantity: Number($("grant-quantity").value || 1),
    }), "发放成功", "物品已发放到指定玩家。");
  });

  $("official-shop-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/shop/official", {
      item_kind: $("official-kind").value, item_ref_id: Number($("official-ref-id").value || 0),
      quantity: Number($("official-quantity").value || 1), price_stone: Number($("official-price").value || 0),
    }), "上架成功", "官方商店已更新。");
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
  await bootstrapAdmin();
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
    const form = event.currentTarget;
    try {
      await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/artifact", {
        name: $("artifact-name").value.trim(),
        rarity: $("artifact-rarity")?.value || "凡品",
        artifact_type: $("artifact-type")?.value || "battle",
        image_url: $("artifact-image")?.value.trim() || "",
        description: $("artifact-description")?.value.trim() || "",
        ...affixPayload("artifact"),
        duel_rate_bonus: Number($("artifact-duel")?.value || 0),
        cultivation_bonus: Number($("artifact-cultivation")?.value || 0),
        combat_config: parseJsonInput($("artifact-combat-config")?.value || "{}", {}),
        min_realm_stage: $("artifact-stage")?.value || null,
        min_realm_layer: Number($("artifact-layer")?.value || 1),
      }), "创建成功", "法宝已经录入修仙体系。");
      form?.reset?.();
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
  const safeColor = typeof color === "string" && color ? color : "#9ca3af";
  const style = safeColor.includes("gradient")
    ? `background:${safeColor};color:#fff;box-shadow:inset 0 0 0 1px rgba(255,255,255,.28);`
    : `background:${safeColor}22;color:${safeColor};box-shadow:inset 0 0 0 1px ${safeColor}33;`;
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
      <p>${qualityBadgeHtml(item.rarity || "凡品", item.quality_color)} · ${escapeHtml(affixSummary(item))}</p>
      <p>${escapeHtml(combatConfigSummary(item.combat_config || {}))}</p>
      <p>境界限制：${escapeHtml(item.min_realm_stage || "无限制")} ${escapeHtml(item.min_realm_layer || 1)} 层</p>
      <div class="inline-action-buttons">${deleteButton("artifact", item.id)}</div>
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
          <strong>${escapeHtml(item.name || "未命名称号")}</strong>
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
  const total = Number(data?.total || 0);
  const totalPages = Math.max(Math.ceil(total / Math.max(Number(data?.page_size || pageSize), 1)), 1);
  if (total > 0 && requestedPage > totalPages) {
    return searchPlayers({ query, page: totalPages, pageSize });
  }
  state.playerSearch = {
    query,
    page: Math.max(Number(data?.page || requestedPage), 1),
    pageSize: Math.max(Number(data?.page_size || pageSize), 1),
    total,
  };
  const items = data?.items || [];
  renderPlayerSearchSummary(items);
  renderPlayerSearchPagination();
  if (!container) return;
  if (!items.length) {
    container.innerHTML = `<article class="stack-item"><strong>未找到角色</strong></article>`;
    return;
  }
  container.innerHTML = items.map((p) => `
    <article class="stack-item is-clickable${Number(state.selectedPlayerTg || 0) === Number(p.tg) ? " is-selected" : ""}" data-tg="${p.tg}">
      <div class="stack-item-head">
        <strong>${escapeHtml(p.display_label || p.display_name || (p.username ? "@" + p.username : "TG " + p.tg))}</strong>
        <span class="badge">${escapeHtml(p.realm_stage || "凡人")} ${p.realm_layer || 0}层</span>
      </div>
      <p>灵石 ${p.spiritual_stone || 0} · 修为 ${p.cultivation || 0} · 片刻碎片 ${p.emby_account?.iv ?? 0}</p>
      <p>${escapeHtml(p.emby_account?.name || "未绑定 Emby")} · ${escapeHtml(p.emby_account?.embyid || "无 Emby ID")}</p>
    </article>
  `).join("");
  bindPlayerSearchResultClicks(container);
  highlightSelectedPlayerResult();
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
    await searchPlayers({
      query: $("player-search-q")?.value || "",
      page: state.playerSearch?.page || 1,
    });
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
document.getElementById("player-inventory-form")?.addEventListener("submit", submitPlayerInventoryEdit);
document.getElementById("player-owned-form")?.addEventListener("submit", submitPlayerOwnedGrant);
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
  renderAchievementMetricOptions();
};

function renderTitleAdminList() {
  renderStack("title-list", (state.bundle?.titles || []).map((item) => `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        <span class="badge badge--normal">${item.enabled ? "启用中" : "已停用"}</span>
      </div>
      <p>${escapeHtml(item.description || "暂无称号描述")}</p>
      <p>${escapeHtml(adminTitleEffectSummary(item))}</p>
      <p>颜色 ${escapeHtml(item.color || "默认")} · ID ${escapeHtml(item.id)}</p>
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
  await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/title", {
    name: $("title-name").value.trim(),
    description: $("title-description").value.trim(),
    color: $("title-color").value.trim(),
    image_url: $("title-image").value.trim(),
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
  }), "创建成功", "称号已加入修仙系统。");
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
ensureSettingRuleRows();
bindEvents();
bindAttributeAwareSubmitters();
hydrateAdminForms();
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
