const tg = window.Telegram?.WebApp;
const tgBackButton = tg?.BackButton || null;
const DEFAULT_BACK_PATH = "/admin";

const REALM_OPTIONS = ["凡人", "炼气", "筑基", "结丹", "元婴", "化神", "须弥", "芥子", "混元一体"];
const QUALITY_OPTIONS = ["凡品", "黄品", "玄品", "地品", "天品", "仙品"];
const PILL_TYPES = [
  { value: "foundation", label: "突破加成", effect: "突破助力值" },
  { value: "clear_poison", label: "解毒", effect: "减少丹毒值" },
  { value: "cultivation", label: "提升修为", effect: "增加修为值" },
  { value: "stone", label: "补给灵石", effect: "增加灵石值" },
  { value: "insight", label: "提高悟性", effect: "提高修炼速度" },
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

const state = {
  token: localStorage.getItem("xiuxian_admin_token") || "",
  initData: tg?.initData || "",
  bundle: null,
};
const backState = {
  fallbackPath: DEFAULT_BACK_PATH,
  returnTo: "",
  referrerPath: ""
};

const ADMIN_SECTION_LABELS = {
  settings: "\u57fa\u7840\u8bbe\u5b9a",
  artifacts: "\u6cd5\u5b9d",
  talismans: "\u7b26\u7bab",
  pills: "\u4e39\u836f",
  techniques: "\u529f\u6cd5",
  sects: "\u5b97\u95e8",
  materials: "\u6750\u6599",
  recipes: "\u914d\u65b9",
  scenes: "\u573a\u666f",
  tasks: "\u4efb\u52a1",
  grant: "\u624b\u52a8\u53d1\u653e",
  "official shop": "\u5b98\u65b9\u5546\u5e97",
  players: "\u89d2\u8272\u7ba1\u7406",
};
const ADMIN_CORE_SECTION_KEYS = new Set(["settings", "tasks", "grant", "official shop", "players"]);

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

REALM_OPTIONS.splice(0, REALM_OPTIONS.length, "凡人", "炼气", "筑基", "结丹", "元婴", "化神", "须弥", "芥子", "混元一体");
QUALITY_OPTIONS.splice(0, QUALITY_OPTIONS.length, "凡品", "下品", "中品", "上品", "极品", "仙品", "先天至宝");
PILL_TYPES.splice(0, PILL_TYPES.length, ...[
  { value: "foundation", label: "突破加成", effect: "突破增幅" },
  { value: "clear_poison", label: "解毒", effect: "减少丹毒" },
  { value: "cultivation", label: "提升修为", effect: "增加修为" },
  { value: "stone", label: "补给灵石", effect: "增加灵石" },
  { value: "comprehension", label: "提升悟性", effect: "提升悟性" },
  { value: "qi_blood", label: "提升气血", effect: "提升气血" },
  { value: "true_yuan", label: "提升真元", effect: "提升真元" },
  { value: "body_movement", label: "提升身法", effect: "提升身法" },
  { value: "attack", label: "提升攻击", effect: "提升攻击" },
  { value: "defense", label: "提升防御", effect: "提升防御" },
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
  const key = kind === "artifact" ? "artifacts" : kind === "pill" ? "pills" : kind === "talisman" ? "talismans" : kind === "material" ? "materials" : "";
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
        if (target) target.value = payload.relative_url || payload.url;
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

function updateArtifactMeritState() {}

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

function addSceneEventRow(value = "") {
  const rows = $("scene-event-rows");
  if (!rows) return;
  rows.appendChild(createBuilderRow(`
    <label class="wide-field">事件描述
      <input data-scene-event type="text" value="${escapeHtml(value)}" placeholder="例如：山风呼啸，灵气暗涌">
    </label>
  `));
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
  return [...document.querySelectorAll("#scene-event-rows [data-scene-event]")]
    .map((node) => node.value.trim())
    .filter(Boolean);
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

function renderWorld() {
  const bundle = state.bundle;
  if (!bundle) return;

  renderTagList("upload-permission-list", bundle.upload_permissions || [], (row) => `<span class="tag">TG ${escapeHtml(row.tg)}</span>`);

  renderStack("artifact-list", (bundle.artifacts || []).map((item) => `
    <article class="stack-item"><div class="stack-item-head"><strong>${escapeHtml(item.name)}</strong><span class="badge badge--normal">${escapeHtml(item.artifact_type_label || item.artifact_type)}</span></div>
    <p>品质 ${escapeHtml(item.rarity)} · 攻击 ${escapeHtml(item.attack_bonus)} · 防御 ${escapeHtml(item.defense_bonus)} · 斗法 ${escapeHtml(item.duel_rate_bonus)}% · 修炼 ${escapeHtml(item.cultivation_bonus)}</p>
    <p>境界限制：${escapeHtml(item.min_realm_stage || "无限制")} ${escapeHtml(item.min_realm_layer || 1)} 层</p>
    <div class="inline-action-buttons">${deleteButton("artifact", item.id)}</div></article>`).join("") || `<article class="stack-item"><strong>暂无法宝</strong></article>`);

  renderStack("talisman-list", (bundle.talismans || []).map((item) => `
    <article class="stack-item"><div class="stack-item-head"><strong>${escapeHtml(item.name)}</strong><span class="badge badge--normal">${escapeHtml(item.rarity)}</span></div>
    <p>攻击 ${escapeHtml(item.attack_bonus)} · 防御 ${escapeHtml(item.defense_bonus)} · 斗法 ${escapeHtml(item.duel_rate_bonus)}%</p>
    <div class="inline-action-buttons">${deleteButton("talisman", item.id)}</div></article>`).join("") || `<article class="stack-item"><strong>暂无符箓</strong></article>`);

  renderStack("pill-list", (bundle.pills || []).map((item) => `
    <article class="stack-item"><div class="stack-item-head"><strong>${escapeHtml(item.name)}</strong><span class="badge badge--normal">${escapeHtml(item.pill_type_label || item.pill_type)}</span></div>
    <p>效果值 ${escapeHtml(item.effect_value)} · 丹毒 ${escapeHtml(item.poison_delta)}</p>
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
    <p>${escapeHtml(item.description || "暂无描述")}</p><p>掉落 ${escapeHtml((item.drops || []).length)} 项 · 事件 ${escapeHtml((item.event_pool || []).length)} 条</p>
    <div class="inline-action-buttons">${deleteButton("scene", item.id)}</div></article>`).join("") || `<article class="stack-item"><strong>暂无场景</strong></article>`);

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
  ["artifact-stage", "talisman-stage", "pill-stage", "sect-stage", "technique-stage"].forEach((id) => setOptions($(id), realmRows(), $(id)?.value, "无限制"));
  setOptions($("sect-assign-id"), sectRows(), $("sect-assign-id")?.value);
  setOptions($("admin-task-sect-id"), [{ value: "", label: "无" }, ...sectRows()], $("admin-task-sect-id")?.value);
  setOptions($("recipe-result-id"), itemRows($("recipe-result-kind")?.value || "pill"), $("recipe-result-id")?.value);
  setOptions($("grant-ref-id"), itemRows($("grant-kind")?.value || "artifact"), $("grant-ref-id")?.value);
  setOptions($("official-ref-id"), itemRows($("official-kind")?.value || "artifact"), $("official-ref-id")?.value);
  setOptions($("admin-task-item-id"), [{ value: "", label: "无" }, ...itemRows($("admin-task-item-kind")?.value || "")], $("admin-task-item-id")?.value);
  setOptions($("admin-task-required-id"), [{ value: "", label: "无" }, ...itemRows($("admin-task-required-kind")?.value || "")], $("admin-task-required-id")?.value);
  const roles = (($("sect-assign-id")?.value && state.bundle?.sects) ? (state.bundle.sects.find((item) => String(item.id) === String($("sect-assign-id").value))?.roles || []) : []);
  setOptions($("sect-assign-role"), roles.map((item) => ({ value: item.role_key, label: item.role_name })), $("sect-assign-role")?.value);
  document.querySelectorAll("#scene-drop-rows .builder-row").forEach((row) => {
    const kind = row.querySelector("[data-drop-kind]")?.value || "material";
    setOptions(row.querySelector("[data-drop-ref]"), itemRows(kind), row.querySelector("[data-drop-ref]")?.value, "无");
  });
}

function applySettings(settings = {}) {
  ensureSettingRuleRows();
  $("setting-rate").value = settings.coin_exchange_rate ?? 100;
  $("setting-fee").value = settings.exchange_fee_percent ?? 1;
  $("setting-min").value = settings.min_coin_exchange ?? 1;
  $("setting-duel-minutes").value = settings.duel_bet_minutes ?? 2;
  $("setting-broadcast").value = settings.shop_broadcast_cost ?? 20;
  $("setting-shop-name").value = settings.official_shop_name ?? "风月阁";
  $("setting-artifact-limit").value = settings.artifact_equip_limit ?? 3;
  $("setting-user-upload").checked = Boolean(settings.allow_non_admin_image_upload);
  $("setting-chat-chance").value = settings.chat_cultivation_chance ?? 8;
  $("setting-chat-min").value = settings.chat_cultivation_min_gain ?? 1;
  $("setting-chat-max").value = settings.chat_cultivation_max_gain ?? 3;
  $("setting-robbery-limit").value = settings.robbery_daily_limit ?? 3;
  $("setting-robbery-max").value = settings.robbery_max_steal ?? 180;
  $("setting-red-stone").value = settings.red_packet_merit_min_stone ?? 100;
  $("setting-red-count").value = settings.red_packet_merit_min_count ?? 3;
  $("setting-red-merit").value = settings.red_packet_merit_reward ?? 2;
  $("setting-quality-broadcast").value = settings.high_quality_broadcast_level ?? 4;
  const immortalTouchNode = $("setting-immortal-touch-layers");
  if (immortalTouchNode) immortalTouchNode.value = settings.immortal_touch_infusion_layers ?? 1;
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
  state.bundle = data;
  applySettings(data.settings || {});
  syncSelects();
  renderWorld();
  await searchPlayers($("player-search-q")?.value || "");
  renderAdminNavigator();
  adminStatus(`修仙后台已就绪，当前管理数据加载完成。`, "success");
}

async function submitAndRefresh(handler, successTitle, successMessage) {
  await handler();
  await bootstrapAdmin();
  await popup(successTitle, successMessage);
}

function bindEvents() {
  $("artifact-type")?.addEventListener("change", updateArtifactMeritState);
  $("pill-type")?.addEventListener("change", updatePillEffectLabel);
  $("recipe-result-kind")?.addEventListener("change", syncSelects);
  $("grant-kind")?.addEventListener("change", syncSelects);
  $("official-kind")?.addEventListener("change", syncSelects);
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
      duel_bet_minutes: Number($("setting-duel-minutes").value || 2),
      shop_broadcast_cost: Number($("setting-broadcast").value || 20),
      official_shop_name: $("setting-shop-name").value.trim(),
      artifact_equip_limit: Number($("setting-artifact-limit").value || 3),
      allow_non_admin_image_upload: $("setting-user-upload").checked,
      chat_cultivation_chance: Number($("setting-chat-chance").value || 8),
      chat_cultivation_min_gain: Number($("setting-chat-min").value || 1),
      chat_cultivation_max_gain: Number($("setting-chat-max").value || 3),
      robbery_daily_limit: Number($("setting-robbery-limit").value || 3),
      robbery_max_steal: Number($("setting-robbery-max").value || 180),
      red_packet_merit_min_stone: Number($("setting-red-stone").value || 100),
      red_packet_merit_min_count: Number($("setting-red-count").value || 3),
      red_packet_merit_reward: Number($("setting-red-merit").value || 2),
      high_quality_broadcast_level: Number($("setting-quality-broadcast").value || 4),
      immortal_touch_infusion_layers: Number($("setting-immortal-touch-layers")?.value || 1),
      root_quality_value_rules: collectRootQualityRules(),
      item_quality_value_rules: collectItemQualityRules(),
      exploration_drop_weight_rules: collectDropWeightRules(),
    }), "保存成功", "基础规则已更新。");
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
    updateArtifactMeritState();
    syncSelects();
  });

  $("talisman-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/talisman", {
      name: $("talisman-name").value.trim(), rarity: $("talisman-rarity").value, image_url: $("talisman-image").value.trim(),
      description: $("talisman-description").value.trim(), attack_bonus: Number($("talisman-attack").value || 0),
      defense_bonus: Number($("talisman-defense").value || 0), duel_rate_bonus: Number($("talisman-duel").value || 0),
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
      max_minutes: Number($("scene-max-minutes").value || 60), event_pool: collectSceneEvents(), drops: collectSceneDrops(),
    }), "创建成功", "探索场景已保存。");
    form?.reset?.();
    $("scene-event-rows").innerHTML = "";
    $("scene-drop-rows").innerHTML = "";
    addSceneEventRow();
    addSceneDropRow();
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
      quantity: Number($("official-quantity").value || 1), price_stone: Number($("official-price").value || 0), shop_name: $("official-shop-name").value.trim() || null,
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
  updateArtifactMeritState();
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
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/artifact", {
      name: $("artifact-name").value.trim(),
      rarity: $("artifact-rarity")?.value || "凡品",
      artifact_type: $("artifact-type")?.value || "battle",
      image_url: $("artifact-image")?.value.trim() || "",
      description: $("artifact-description")?.value.trim() || "",
      ...affixPayload("artifact"),
      duel_rate_bonus: Number($("artifact-duel")?.value || 0),
      cultivation_bonus: Number($("artifact-cultivation")?.value || 0),
      min_realm_stage: $("artifact-stage")?.value || null,
      min_realm_layer: Number($("artifact-layer")?.value || 1),
    }), "创建成功", "法宝已经录入修仙体系。");
    form?.reset?.();
    syncSelects();
    updateArtifactMeritState();
  }, true);

  $("talisman-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    const form = event.currentTarget;
    await submitAndRefresh(() => request("POST", "/plugins/xiuxian/admin-api/talisman", {
      name: $("talisman-name").value.trim(),
      rarity: $("talisman-rarity")?.value || "凡品",
      image_url: $("talisman-image")?.value.trim() || "",
      description: $("talisman-description")?.value.trim() || "",
      ...affixPayload("talisman"),
      duel_rate_bonus: Number($("talisman-duel")?.value || 0),
      min_realm_stage: $("talisman-stage")?.value || null,
      min_realm_layer: Number($("talisman-layer")?.value || 1),
    }), "创建成功", "符箓已经录入修仙体系。");
    form?.reset?.();
    syncSelects();
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
      min_realm_stage: $("technique-stage")?.value || null,
      min_realm_layer: Number($("technique-layer")?.value || 1),
    }), "创建成功", "功法已经录入修仙体系。");
    form?.reset?.();
    syncSelects();
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
      await popup("Upload Error", message, "error");
    }
  });

  $("upload-permission-revoke")?.addEventListener("click", async () => {
    try {
      await submitUploadPermission(false);
    } catch (error) {
      const message = String(error.message || error);
      adminStatus(message, "error");
      await popup("Upload Error", message, "error");
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
      <div class="inline-action-buttons">${deleteButton("talisman", item.id)}</div>
    </article>`).join("") || `<article class="stack-item"><strong>暂无符箓</strong></article>`);

  renderStack("pill-list", (bundle.pills || []).map((item) => `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        ${qualityBadgeHtml(item.rarity || "凡品", item.quality_color)}
      </div>
      <p>${escapeHtml(item.pill_type_label || item.pill_type)} · 主效果 ${escapeHtml(item.effect_value)} · 丹毒 ${escapeHtml(item.poison_delta)}</p>
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
  "bone", "comprehension", "divine_sense", "fortune",
  "qi_blood", "true_yuan", "body_movement", "attack_power", "defense_power",
  "dan_poison", "sect_contribution",
];

async function searchPlayers(q = "") {
  const data = await request("GET", `/plugins/xiuxian/admin-api/players?q=${encodeURIComponent(q)}&page=1&page_size=30`);
  const container = $("player-search-results");
  if (!data || !data.items || data.items.length === 0) {
    container.innerHTML = `<article class="stack-item"><strong>未找到角色</strong></article>`;
    return;
  }
  container.innerHTML = data.items.map((p) => `
    <article class="stack-item" style="cursor:pointer" data-tg="${p.tg}">
      <div class="stack-item-head">
        <strong>${escapeHtml(p.display_label || p.display_name || (p.username ? "@" + p.username : "TG " + p.tg))}</strong>
        <span class="badge">${escapeHtml(p.realm_stage || "凡人")} ${p.realm_layer || 0}层</span>
      </div>
      <p>灵石 ${p.spiritual_stone || 0} · 修为 ${p.cultivation || 0}</p>
    </article>
  `).join("");
  container.querySelectorAll("[data-tg]").forEach((el) => {
    el.addEventListener("click", () => {
      openPlayerEdit(Number(el.dataset.tg)).catch((error) => popup("加载失败", String(error.message || error), "error"));
    });
  });
}

async function openPlayerEdit(tg) {
  const data = await request("GET", `/plugins/xiuxian/admin-api/players/${tg}`);
  const profile = data?.profile || data || {};
  $("player-edit-panel").style.display = "";
  $("player-edit-tg").value = tg;
  document.getElementById("player-edit-title").textContent = `编辑: ${profile?.display_label || profile?.display_name || (profile?.username ? "@" + profile.username : "TG " + tg)}`;
  PLAYER_EDIT_FIELDS.forEach((key) => {
    const el = $("pe-" + key);
    if (el) el.value = profile?.[key] ?? "";
  });
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
    payload[key] = key === "realm_stage" ? raw : Number(raw);
  });
  try {
    await request("PATCH", `/plugins/xiuxian/admin-api/players/${tg}`, payload);
    await popup("操作成功", "角色属性已保存", "success");
    $("player-edit-panel").style.display = "none";
    await searchPlayers($("player-search-q")?.value || "");
  } catch (err) {
    await popup("保存失败", String(err.message || err), "error");
  }
}

document.getElementById("player-search-form")?.addEventListener("submit", (e) => {
  e.preventDefault();
  searchPlayers($("player-search-q")?.value || "");
});
document.getElementById("player-edit-form")?.addEventListener("submit", submitPlayerEdit);
document.getElementById("player-edit-cancel")?.addEventListener("click", () => {
  $("player-edit-panel").style.display = "none";
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
