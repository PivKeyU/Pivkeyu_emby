const tg = window.Telegram?.WebApp;

const state = {
  initData: tg?.initData || "",
  profileBundle: null,
  wikiBundle: null,
  deferredBundleLoading: false,
  deferredBundleLoaded: false,
  wikiFilter: "all",
  wikiSearchQuery: "",
  leaderboard: { kind: "stone", page: 1, totalPages: 1 },
  shopNameEditing: false,
  giftTarget: null,
  giftSearchQuery: "",
  giftSearchResults: [],
  giftSearchTimer: null,
  mentorshipTarget: null,
  mentorshipSearchQuery: "",
  mentorshipSearchResults: [],
  mentorshipSearchTimer: null,
  marriageTarget: null,
  marriageSearchQuery: "",
  marriageSearchResults: [],
  marriageSearchTimer: null,
};

const REALM_ORDER = ["炼气", "筑基", "金丹", "元婴", "化神", "炼虚", "合体", "大乘", "渡劫", "人仙", "地仙", "天仙", "金仙", "大罗金仙", "仙君", "仙王", "仙尊", "仙帝"];

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

function grantedItemName(payload) {
  if (!payload || typeof payload !== "object") return "";
  return payload.artifact?.name
    || payload.pill?.name
    || payload.talisman?.name
    || payload.material?.name
    || payload.item_name
    || "";
}

function setStatus(text, tone = "info") {
  document.querySelector("#status-text").textContent = text;
  const chip = document.querySelector("#feedback-chip");
  chip.textContent = text;
  chip.className = `feedback-chip ${tone === "error" ? "error" : tone === "success" ? "success" : tone === "warning" ? "warning" : ""}`;
  chip.classList.remove("hidden");
}

function touchFeedback(tone = "success") {
  if (!tg?.HapticFeedback) return;
  if (tone === "error") {
    tg.HapticFeedback.notificationOccurred("error");
    return;
  }
  if (tone === "warning") {
    tg.HapticFeedback.notificationOccurred("warning");
    return;
  }
  tg.HapticFeedback.notificationOccurred("success");
}

function normalizeErrorLegacy(error, fallback) {
  const message = String(error?.message || fallback || "操作失败，请稍后再试").trim();
  if (!message || /^[?？.\s]+$/.test(message)) {
    return fallback || "操作失败，请稍后再试";
  }
  return message;
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

async function popupLegacy(title, message, tone = "success") {
  touchFeedback(tone);
  if (tg?.showPopup) {
    try {
      await tg.showPopup({
        title: safeTelegramPopupText(title, TG_POPUP_TITLE_LIMIT, "提示"),
        message: safeTelegramPopupText(
          message,
          TG_POPUP_MESSAGE_LIMIT,
          TG_POPUP_FALLBACK_MESSAGE[tone] || TG_POPUP_FALLBACK_MESSAGE.success,
        ),
        buttons: [{ type: "close", text: "知道了" }]
      });
      return;
    } catch (error) {
      console.warn("Telegram popup failed, fallback to alert", error);
    }
  }
  window.alert(`${title}\n\n${message}`);
}

async function postJsonLegacy(path, body = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ init_data: state.initData, ...body })
  });
  const payload = await response.json();
  if (!response.ok || payload.code !== 200) {
    throw new Error(payload.detail || payload.message || "请求失败");
  }
  return payload.data;
}

async function uploadImageLegacy(path, file, folder) {
  if (!file) {
    throw new Error("请先选择一张图片");
  }
  const formData = new FormData();
  formData.append("init_data", state.initData);
  formData.append("folder", folder);
  formData.append("file", file);
  const response = await fetch(path, {
    method: "POST",
    body: formData
  });
  const payload = await response.json();
  if (!response.ok || payload.code !== 200) {
    throw new Error(payload.detail || payload.message || "上传失败");
  }
  return payload.data;
}

function defaultMessage(fallback = "操作失败，请稍后再试") {
  return fallback || "操作失败，请稍后再试";
}

function normalizeError(error, fallback) {
  const message = String(error?.message || fallback || defaultMessage()).trim();
  if (!message || /^[??\s]+$/.test(message)) {
    return defaultMessage(fallback);
  }
  if (message.startsWith("Unexpected token") || message === "Internal Server Error") {
    return defaultMessage(fallback);
  }
  return message;
}

async function popup(title, message, tone = "success") {
  touchFeedback(tone);
  if (tg?.showPopup) {
    try {
      await tg.showPopup({
        title: safeTelegramPopupText(title, TG_POPUP_TITLE_LIMIT, "提示"),
        message: safeTelegramPopupText(
          message,
          TG_POPUP_MESSAGE_LIMIT,
          TG_POPUP_FALLBACK_MESSAGE[tone] || TG_POPUP_FALLBACK_MESSAGE.success,
        ),
        buttons: [{ type: "close", text: "知道了" }]
      });
      return;
    } catch (error) {
      console.warn("Telegram popup failed, fallback to alert", error);
    }
  }
  window.alert(`${title}\n\n${message}`);
}

async function readResponsePayload(response) {
  const raw = await response.text();
  if (!raw) {
    return { code: response.ok ? 200 : response.status, data: null };
  }
  try {
    return JSON.parse(raw);
  } catch {
    throw new Error(raw.trim() || "Internal Server Error");
  }
}

async function postJson(path, body = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ init_data: state.initData, ...body })
  });
  const payload = await readResponsePayload(response);
  if (!response.ok || payload.code !== 200) {
    throw new Error(payload.detail || payload.message || "请求失败");
  }
  return payload.data;
}

async function uploadImage(path, file, folder) {
  if (!file) {
    throw new Error("请先选择一张图片");
  }
  const formData = new FormData();
  formData.append("init_data", state.initData);
  formData.append("folder", folder);
  formData.append("file", file);
  const response = await fetch(path, {
    method: "POST",
    body: formData
  });
  const payload = await readResponsePayload(response);
  if (!response.ok || payload.code !== 200) {
    throw new Error(payload.detail || payload.message || "上传失败");
  }
  return payload.data;
}

async function runButtonAction(button, pendingText, handler) {
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

function setDisabled(button, disabled, reason = "") {
  if (!button) return;
  button.disabled = Boolean(disabled);
  button.title = disabled ? reason : "";
}

function applyBreakthroughActionState(bundle, fallbackReason = "当前无法尝试突破") {
  const canBreakthrough = Boolean(bundle?.capabilities?.can_breakthrough);
  const requiredPillName = String(bundle?.capabilities?.required_breakthrough_pill_name || "").trim();
  const requiredSceneName = String(bundle?.capabilities?.required_breakthrough_scene_name || "").trim();
  const breakButton = document.querySelector("#break-btn");
  const breakPillButton = document.querySelector("#break-pill-btn");
  if (breakPillButton) {
    breakPillButton.textContent = requiredPillName ? `服用${requiredPillName}突破` : "服用破境丹突破";
  }
  if (breakButton) {
    if (requiredPillName) {
      const reason = requiredSceneName
        ? `当前版本突破必须服用【${requiredPillName}】；丹方与材料可在【${requiredSceneName}】获取。`
        : `当前版本突破必须服用【${requiredPillName}】。`;
      setDisabled(breakButton, true, reason);
    } else {
      setDisabled(breakButton, !canBreakthrough, fallbackReason);
    }
  }
  setDisabled(
    breakPillButton,
    !canBreakthrough,
    !canBreakthrough ? (bundle?.capabilities?.breakthrough_reason || fallbackReason) : "",
  );
}

function parseShanghaiDate(value) {
  if (!value) return null;
  const normalized = typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(value)
    ? `${value}+00:00`
    : value;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDate(value) {
  if (!value) return "未开始";
  const date = parseShanghaiDate(value);
  return date ? date.toLocaleString("zh-CN", { timeZone: "Asia/Shanghai", hour12: false }) : "未知";
}

function normalizeWikiSearchQuery(value) {
  return String(value || "").trim().toLowerCase();
}

function wikiSearchTokens(value) {
  const query = normalizeWikiSearchQuery(value);
  if (!query) return [];
  return query.split(/\s+/).filter(Boolean);
}

function wikiHaystack(entry) {
  return [
    entry?.title,
    entry?.subtitle,
    entry?.description,
    ...(Array.isArray(entry?.tags) ? entry.tags : []),
    ...(Array.isArray(entry?.keywords) ? entry.keywords : []),
    ...(Array.isArray(entry?.body_lines) ? entry.body_lines : []),
  ].join(" ").toLowerCase();
}

function wikiEntryScore(entry, query) {
  const normalizedQuery = normalizeWikiSearchQuery(query);
  if (!normalizedQuery) return 0;
  const tokens = wikiSearchTokens(normalizedQuery);
  const haystack = wikiHaystack(entry);
  if (!tokens.every((token) => haystack.includes(token))) return -1;
  const title = String(entry?.title || "").toLowerCase();
  const subtitle = String(entry?.subtitle || "").toLowerCase();
  const keywords = Array.isArray(entry?.keywords) ? entry.keywords.join(" ").toLowerCase() : "";
  const body = Array.isArray(entry?.body_lines) ? entry.body_lines.join(" ").toLowerCase() : "";
  let score = 0;
  if (title === normalizedQuery) score += 120;
  if (title.includes(normalizedQuery)) score += 80;
  if (subtitle.includes(normalizedQuery)) score += 32;
  if (keywords.includes(normalizedQuery)) score += 24;
  if (body.includes(normalizedQuery)) score += 12;
  score += Math.max(12 - title.length, 0);
  return score;
}

function wikiFilterMatches(entry, filter) {
  if (!filter || filter === "all") return true;
  const keys = Array.isArray(entry?.filter_keys) ? entry.filter_keys.map((item) => String(item || "")) : [String(entry?.group || "")];
  return keys.includes(String(filter || ""));
}

const WIKI_FILTER_LABELS = {
  tutorial: "玩法",
  starter: "入门",
  explore: "探索",
  crafting: "炼制",
  combat: "战斗",
  task: "任务",
  social: "社交",
  sect: "宗门",
  material: "材料",
  artifact: "法宝",
  pill: "丹药",
  talisman: "符箓",
  technique: "功法",
  title: "称号",
  recipe: "配方",
  achievement: "成就",
};

function normalizeWikiDisplayText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function wikiCardTitle(entry) {
  const title = normalizeWikiDisplayText(entry?.title);
  const subtitle = normalizeWikiDisplayText(entry?.subtitle);
  if (!title) return "";
  if (String(entry?.group || "") === "tutorial" && subtitle && title.startsWith(`${subtitle} · `)) {
    return title.slice(subtitle.length + 3).trim();
  }
  return title;
}

function wikiCardSubtitle(entry) {
  const title = normalizeWikiDisplayText(entry?.title);
  const subtitle = normalizeWikiDisplayText(entry?.subtitle);
  if (!subtitle || title === subtitle) return "";
  return subtitle;
}

function wikiCardTags(entry) {
  if (String(entry?.group || "") === "tutorial") {
    const filterKeys = Array.isArray(entry?.filter_keys) ? entry.filter_keys : [];
    return filterKeys
      .filter((key) => key && key !== "tutorial")
      .map((key) => WIKI_FILTER_LABELS[String(key)] || "")
      .filter(Boolean)
      .slice(0, 3);
  }
  return (Array.isArray(entry?.tags) ? entry.tags : []).filter(Boolean).slice(0, 4);
}

function wikiCardLines(entry) {
  const lines = Array.isArray(entry?.body_lines) ? entry.body_lines : [];
  const seen = new Set();
  const skipValues = [
    entry?.title,
    entry?.subtitle,
    entry?.description,
  ].map((value) => normalizeWikiDisplayText(value).toLowerCase()).filter(Boolean);
  skipValues.forEach((value) => seen.add(value));
  const visible = [];
  for (const line of lines) {
    const text = normalizeWikiDisplayText(line);
    if (!text) continue;
    const normalized = text.toLowerCase();
    if (seen.has(normalized)) continue;
    seen.add(normalized);
    visible.push(text);
  }
  return visible.slice(0, String(entry?.group || "") === "tutorial" ? 1 : 2);
}

function wikiPopupLines(entry) {
  const rows = [];
  const subtitle = wikiCardSubtitle(entry);
  if (subtitle) rows.push(subtitle);
  for (const value of [entry?.description, ...(Array.isArray(entry?.body_lines) ? entry.body_lines : [])]) {
    const text = normalizeWikiDisplayText(value);
    if (!text) continue;
    const normalized = text.toLowerCase();
    if (rows.some((item) => normalizeWikiDisplayText(item).toLowerCase() === normalized)) continue;
    rows.push(text);
  }
  return rows;
}

function renderWikiCards(root, entries, { emptyTitle, emptyText } = {}) {
  if (!root) return;
  if (!Array.isArray(entries) || !entries.length) {
    root.innerHTML = `<article class="stack-item"><strong>${escapeHtml(emptyTitle || "暂无内容")}</strong><p>${escapeHtml(emptyText || "请稍后再试。")}</p></article>`;
    return;
  }
  root.innerHTML = entries.map((entry) => {
    const tags = wikiCardTags(entry);
    const lines = wikiCardLines(entry);
    const title = wikiCardTitle(entry);
    const subtitle = wikiCardSubtitle(entry);
    const description = normalizeWikiDisplayText(entry?.description);
    return `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(title || entry?.title || "未命名词条")}</strong>
          <button type="button" class="ghost" data-wiki-entry="${escapeHtml(entry?.id || "")}">查看全文</button>
        </div>
        <div class="wiki-meta-line">
          <span>${escapeHtml(entry?.kind_label || "词条")}</span>
          ${subtitle ? `<span>${escapeHtml(subtitle)}</span>` : ""}
        </div>
        ${description ? `<p>${escapeHtml(description)}</p>` : ""}
        ${tags.length ? `<div class="item-tags">${tags.map((tag) => `<span class="badge badge--normal">${escapeHtml(tag)}</span>`).join("")}</div>` : ""}
        ${lines.length ? `<div class="wiki-body-lines">${lines.map((line) => `<p class="section-copy">${escapeHtml(line)}</p>`).join("")}</div>` : ""}
      </article>
    `;
  }).join("");
}

function currentWikiEntries() {
  const bundle = state.wikiBundle;
  const filter = state.wikiFilter || "all";
  const query = state.wikiSearchQuery || "";
  const rows = Array.isArray(bundle?.search_index) ? bundle.search_index.slice() : [];
  const filtered = rows.filter((entry) => wikiFilterMatches(entry, filter));
  if (!query) {
    const defaults = filter === "all"
      ? filtered.filter((entry) => entry.group !== "tutorial")
      : filtered;
    return defaults.slice(0, 12);
  }
  return filtered
    .map((entry) => ({ entry, score: wikiEntryScore(entry, query) }))
    .filter((row) => row.score >= 0)
    .sort((left, right) => right.score - left.score || String(left.entry?.title || "").localeCompare(String(right.entry?.title || ""), "zh-CN"))
    .slice(0, 20)
    .map((row) => row.entry);
}

function renderWikiArea() {
  const countsNode = document.querySelector("#wiki-counts");
  const hintNode = document.querySelector("#wiki-search-hint");
  const featuredRoot = document.querySelector("#wiki-featured-list");
  const resultRoot = document.querySelector("#wiki-result-list");
  const filterButtons = Array.from(document.querySelectorAll("[data-wiki-filter]"));
  const bundle = state.wikiBundle;

  filterButtons.forEach((button) => {
    button.classList.toggle("is-active", (button.dataset.wikiFilter || "all") === (state.wikiFilter || "all"));
  });

  if (!bundle) {
    if (countsNode) countsNode.textContent = "正在整理词条...";
    if (hintNode) hintNode.textContent = "可搜索玩法教程、材料来源、法宝、丹药、符箓、功法、称号、成就与配方获取方式，也可按入门、探索、炼制、战斗、任务、社交、宗门筛选。";
    renderWikiCards(featuredRoot, [], { emptyTitle: "Wiki 加载中", emptyText: "正在整理新手手册与掉落词条，请稍候。" });
    renderWikiCards(resultRoot, [], { emptyTitle: "等待检索", emptyText: "输入关键词后，可快速定位玩法和物品来源。" });
    return;
  }

  const counts = bundle.counts || {};
  const examples = Array.isArray(bundle.search_examples) ? bundle.search_examples.filter(Boolean) : [];
  if (countsNode) {
    countsNode.textContent = `教程 ${Number(counts.tutorial || 0)} · 材料 ${Number(counts.material || 0)} · 法宝 ${Number(counts.artifact || 0)} · 丹药 ${Number(counts.pill || 0)} · 符箓 ${Number(counts.talisman || 0)} · 功法 ${Number(counts.technique || 0)} · 称号 ${Number(counts.title || 0)} · 配方 ${Number(counts.recipe || 0)} · 成就 ${Number(counts.achievement || 0)}`;
  }
  if (hintNode) {
    hintNode.textContent = examples.length
      ? `试试这些关键词：${examples.join("、")}`
      : "可搜索玩法教程、材料来源、法宝、丹药、符箓、功法、称号、成就与配方获取方式，也可按入门、探索、炼制、战斗、任务、社交、宗门筛选。";
  }

  renderWikiCards(featuredRoot, bundle.featured_tutorials || [], {
    emptyTitle: "暂无推荐教程",
    emptyText: "主人还没有补充玩法手册。",
  });

  const query = state.wikiSearchQuery || "";
  const entries = currentWikiEntries();
  renderWikiCards(resultRoot, entries, {
    emptyTitle: query ? "没有找到对应词条" : "暂无检索词条",
    emptyText: query
      ? "可换个关键词，或先搜玩法名、材料名、法宝名、丹药名、符箿名、功法名、成就名、配方名。"
      : "输入关键词后，可查看对应的玩法与来源说明。",
  });
}

async function openWikiEntry(entryId) {
  const rows = Array.isArray(state.wikiBundle?.search_index) ? state.wikiBundle.search_index : [];
  const entry = rows.find((item) => String(item?.id || "") === String(entryId || ""));
  if (!entry) return;
  const lines = wikiPopupLines(entry);
  await popup(wikiCardTitle(entry) || entry.title || "修仙 Wiki", lines.join("\n\n"), "success");
}

async function refreshWikiBundle() {
  const bundle = await postJson("/plugins/xiuxian/api/wiki");
  state.wikiBundle = bundle;
  renderWikiArea();
  return bundle;
}

function formatRemainingDuration(totalSeconds) {
  const safeSeconds = Math.max(Number(totalSeconds || 0), 0);
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const seconds = Math.floor(safeSeconds % 60);
  if (hours > 0) return `${hours} 小时 ${minutes} 分`;
  if (minutes > 0) return `${minutes} 分 ${seconds} 秒`;
  return `${seconds} 秒`;
}

function officialShopName(bundle = state.profileBundle) {
  const raw = bundle?.settings?.official_shop_name;
  return String(raw || "").trim() || "官方商店";
}

function officialRecycleName(bundle = state.profileBundle) {
  const raw = bundle?.official_recycle?.shop_name;
  return String(raw || "").trim() || "官方回收";
}

function currentDuelLockReason(bundle = state.profileBundle) {
  const reason = bundle?.capabilities?.duel_lock_reason;
  return String(reason || "").trim();
}

function currentSocialInteractionLockReason(bundle = state.profileBundle) {
  const reason = bundle?.capabilities?.social_interaction_lock_reason;
  return String(reason || "").trim();
}

function currentSocialMode(bundle = state.profileBundle) {
  return String(bundle?.profile?.social_mode || "worldly").trim() || "worldly";
}

function attributeGrowthText(changes = [], prefix = "小幅成长") {
  const rows = (changes || [])
    .map((item) => {
      const label = String(item?.label || item?.key || "属性").trim();
      const value = Number(item?.value || 0);
      return value > 0 ? `${label}+${value}` : "";
    })
    .filter(Boolean);
  return rows.length ? `${prefix}：${rows.join("、")}` : "";
}

function setSelectOptions(select, options = [], selectedValue = "") {
  if (!select) return;
  const normalizedSelected = String(selectedValue ?? "");
  select.innerHTML = options.map((item) => `
    <option value="${escapeHtml(item.value)}" ${String(item.value) === normalizedSelected ? "selected" : ""}>${escapeHtml(item.label)}</option>
  `).join("");
}

function currentGiftTarget() {
  return state.giftTarget && Number(state.giftTarget.tg || 0) > 0 ? state.giftTarget : null;
}

function renderGiftTargetSelection() {
  const root = document.querySelector("#gift-target-selected");
  const hidden = document.querySelector("#gift-target");
  const target = currentGiftTarget();
  if (!root || !hidden) return;
  hidden.value = target ? String(target.tg) : "";
  if (!target) {
    root.innerHTML = "";
    return;
  }
  const hint = target.username ? `@${target.username}` : `TG ${target.tg}`;
  root.innerHTML = `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>已选目标：${escapeHtml(target.display_label || hint)}</strong>
        <button type="button" class="ghost" data-clear-gift-target>重新选择</button>
      </div>
      <p>当前仅展示公开昵称与用户名：${escapeHtml(hint)}。</p>
    </article>
  `;
}

function renderGiftSearchResults(items = state.giftSearchResults) {
  const root = document.querySelector("#gift-player-search-results");
  if (!root) return;
  const keyword = String(state.giftSearchQuery || "").trim();
  if (!keyword) {
    root.innerHTML = "";
    return;
  }
  if (!(items || []).length) {
    root.innerHTML = `<article class="stack-item"><strong>未找到匹配道友</strong><p>试试输入 @用户名、TG ID 或昵称。</p></article>`;
    return;
  }
  root.innerHTML = (items || []).map((item) => `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(item.display_label || `TG ${item.tg}`)}</strong>
        <button
          type="button"
          class="ghost"
          data-gift-target-tg="${escapeHtml(item.tg)}"
          data-gift-target-label="${escapeHtml(item.display_label || `TG ${item.tg}`)}"
          data-gift-target-username="${escapeHtml(item.username || "")}"
        >选择</button>
      </div>
      <p>${escapeHtml(item.username ? `@${item.username}` : `TG ${item.tg}`)}</p>
    </article>
  `).join("");
}

function setGiftTarget(target) {
  const tgValue = Number(target?.tg || 0);
  state.giftTarget = tgValue > 0
    ? {
      tg: tgValue,
      display_label: String(target?.display_label || target?.label || `TG ${tgValue}`).trim(),
      username: String(target?.username || "").trim().replace(/^@/, ""),
    }
    : null;
  renderGiftTargetSelection();
  syncGiftPanelState(state.profileBundle);
}

function currentMentorshipTarget() {
  return state.mentorshipTarget && Number(state.mentorshipTarget.tg || 0) > 0 ? state.mentorshipTarget : null;
}

function renderMentorshipTargetSelection() {
  const root = document.querySelector("#mentorship-target-selected");
  const target = currentMentorshipTarget();
  if (!root) return;
  if (!target) {
    root.innerHTML = "";
    return;
  }
  const hint = target.username ? `@${target.username}` : `TG ${target.tg}`;
  root.innerHTML = `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>已选目标：${escapeHtml(target.display_label || hint)}</strong>
        <button type="button" class="ghost" data-clear-mentorship-target>重新选择</button>
      </div>
      <p>当前仅展示公开昵称与用户名：${escapeHtml(hint)}。</p>
    </article>
  `;
}

function renderMentorshipSearchResults(items = state.mentorshipSearchResults) {
  const root = document.querySelector("#mentorship-player-search-results");
  if (!root) return;
  const keyword = String(state.mentorshipSearchQuery || "").trim();
  if (!keyword) {
    root.innerHTML = "";
    return;
  }
  if (!(items || []).length) {
    root.innerHTML = `<article class="stack-item"><strong>未找到匹配道友</strong><p>试试输入 @用户名、TG ID 或昵称。</p></article>`;
    return;
  }
  root.innerHTML = (items || []).map((item) => `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(item.display_label || `TG ${item.tg}`)}</strong>
        <button
          type="button"
          class="ghost"
          data-mentorship-target-tg="${escapeHtml(item.tg)}"
          data-mentorship-target-label="${escapeHtml(item.display_label || `TG ${item.tg}`)}"
          data-mentorship-target-username="${escapeHtml(item.username || "")}"
        >选择</button>
      </div>
      <p>${escapeHtml(item.username ? `@${item.username}` : `TG ${item.tg}`)}</p>
    </article>
  `).join("");
}

function setMentorshipTarget(target) {
  const tgValue = Number(target?.tg || 0);
  state.mentorshipTarget = tgValue > 0
    ? {
      tg: tgValue,
      display_label: String(target?.display_label || target?.label || `TG ${tgValue}`).trim(),
      username: String(target?.username || "").trim().replace(/^@/, ""),
    }
    : null;
  renderMentorshipTargetSelection();
  syncMentorshipRequestComposer(state.profileBundle);
}

async function searchMentorshipPlayers(query, page = 1) {
  const keyword = String(query || "").trim();
  state.mentorshipSearchQuery = keyword;
  if (!keyword) {
    state.mentorshipSearchResults = [];
    renderMentorshipSearchResults([]);
    return { items: [], page: 1, page_size: 0, total: 0 };
  }
  const requestKeyword = keyword;
  const payload = await postJson("/plugins/xiuxian/api/player/search", {
    query: keyword,
    page,
    page_size: 8,
  });
  if (state.mentorshipSearchQuery !== requestKeyword) {
    return payload;
  }
  state.mentorshipSearchResults = payload.items || [];
  renderMentorshipSearchResults(state.mentorshipSearchResults);
  return payload;
}

function mentorshipRequestRoleLabel(role) {
  return String(role || "").trim() === "mentor" ? "收徒邀请" : "拜师申请";
}

function syncMentorshipRequestComposer(bundle = state.profileBundle) {
  renderMentorshipTargetSelection();
  renderMentorshipSearchResults();
  const mentorship = bundle?.mentorship || {};
  const target = currentMentorshipTarget();
  const role = document.querySelector("#mentorship-request-role")?.value || "disciple";
  const socialLockReason = currentSocialInteractionLockReason(bundle);
  let roleLockReason = "";
  if (role === "mentor" && !mentorship.can_take_disciple) {
    roleLockReason = mentorship.request_hint || "当前不可继续收徒。";
  }
  if (role === "disciple" && !mentorship.can_seek_mentor) {
    roleLockReason = mentorship.request_hint || "当前不可再拜师。";
  }
  const inputLockReason = socialLockReason || "";
  const submitLockReason = socialLockReason || roleLockReason || (target ? "" : "先选择目标道友。");
  ["#mentorship-player-query", "#mentorship-player-search", "#mentorship-request-role", "#mentorship-request-message"]
    .forEach((selector) => setDisabled(document.querySelector(selector), Boolean(inputLockReason), inputLockReason));
  setDisabled(document.querySelector("#mentorship-request-form button[type='submit']"), Boolean(submitLockReason), submitLockReason);
  const hint = document.querySelector("#mentorship-request-hint");
  if (hint) {
    const roleText = mentorshipRequestRoleLabel(role);
    hint.textContent = socialLockReason
      ? socialLockReason
      : roleLockReason
        ? roleLockReason
        : target
          ? `${mentorship.request_hint || "可继续结识同道。"} 当前准备发送：${roleText} -> ${target.display_label || `TG ${target.tg}`}。`
          : (mentorship.request_hint || "完成搜索并选中目标后，才可递上拜帖。");
  }
}

function currentMarriageTarget() {
  return state.marriageTarget && Number(state.marriageTarget.tg || 0) > 0 ? state.marriageTarget : null;
}

function renderMarriageTargetSelection() {
  const root = document.querySelector("#marriage-target-selected");
  const target = currentMarriageTarget();
  if (!root) return;
  if (!target) {
    root.innerHTML = "";
    return;
  }
  const hint = target.username ? `@${target.username}` : `TG ${target.tg}`;
  root.innerHTML = `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>已选目标：${escapeHtml(target.display_label || hint)}</strong>
        <button type="button" class="ghost" data-clear-marriage-target>重新选择</button>
      </div>
      <p>当前仅展示公开昵称与用户名：${escapeHtml(hint)}。</p>
    </article>
  `;
}

function renderMarriageSearchResults(items = state.marriageSearchResults) {
  const root = document.querySelector("#marriage-player-search-results");
  if (!root) return;
  const keyword = String(state.marriageSearchQuery || "").trim();
  if (!keyword) {
    root.innerHTML = "";
    return;
  }
  if (!(items || []).length) {
    root.innerHTML = `<article class="stack-item"><strong>未找到匹配道友</strong><p>试试输入 @用户名、TG ID 或昵称。</p></article>`;
    return;
  }
  root.innerHTML = (items || []).map((item) => `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(item.display_label || `TG ${item.tg}`)}</strong>
        <button
          type="button"
          class="ghost"
          data-marriage-target-tg="${escapeHtml(item.tg)}"
          data-marriage-target-label="${escapeHtml(item.display_label || `TG ${item.tg}`)}"
          data-marriage-target-username="${escapeHtml(item.username || "")}"
        >选择</button>
      </div>
      <p>${escapeHtml(item.username ? `@${item.username}` : `TG ${item.tg}`)}</p>
    </article>
  `).join("");
}

function setMarriageTarget(target) {
  const tgValue = Number(target?.tg || 0);
  state.marriageTarget = tgValue > 0
    ? {
      tg: tgValue,
      display_label: String(target?.display_label || target?.label || `TG ${tgValue}`).trim(),
      username: String(target?.username || "").trim().replace(/^@/, ""),
    }
    : null;
  renderMarriageTargetSelection();
  syncMarriageRequestComposer(state.profileBundle);
}

async function searchMarriagePlayers(query, page = 1) {
  const keyword = String(query || "").trim();
  state.marriageSearchQuery = keyword;
  if (!keyword) {
    state.marriageSearchResults = [];
    renderMarriageSearchResults([]);
    return { items: [], page: 1, page_size: 0, total: 0 };
  }
  const requestKeyword = keyword;
  const payload = await postJson("/plugins/xiuxian/api/player/search", {
    query: keyword,
    page,
    page_size: 8,
  });
  if (state.marriageSearchQuery !== requestKeyword) {
    return payload;
  }
  state.marriageSearchResults = payload.items || [];
  renderMarriageSearchResults(state.marriageSearchResults);
  return payload;
}

function syncGenderComposer(bundle = state.profileBundle) {
  const marriage = bundle?.marriage || {};
  const select = document.querySelector("#gender-select");
  const submit = document.querySelector("#gender-set-form button[type='submit']");
  const hint = document.querySelector("#gender-set-hint");
  const lockReason = marriage.can_set_gender ? "" : (marriage.gender_change_reason || "");
  if (select) {
    select.value = String(marriage.gender || bundle?.profile?.gender || "male");
  }
  setDisabled(select, Boolean(lockReason), lockReason);
  setDisabled(submit, Boolean(lockReason), lockReason);
  if (hint) {
    hint.textContent = lockReason
      ? lockReason
      : marriage.gender_set
        ? `当前已设置为${marriage.gender_label || "已设置"}。未结为道侣前可重新调整。`
        : "未设置性别前，其他修仙玩法会被锁定。";
  }
}

function syncMarriageRequestComposer(bundle = state.profileBundle) {
  renderMarriageTargetSelection();
  renderMarriageSearchResults();
  const marriage = bundle?.marriage || {};
  const target = currentMarriageTarget();
  const socialLockReason = currentSocialInteractionLockReason(bundle);
  const inputLockReason = socialLockReason || (!marriage.can_request_marriage ? (marriage.request_hint || "当前不可发起姻缘请求。") : "");
  const submitLockReason = inputLockReason || (target ? "" : "先选择目标道友。");
  ["#marriage-player-query", "#marriage-player-search", "#marriage-request-message"]
    .forEach((selector) => setDisabled(document.querySelector(selector), Boolean(inputLockReason), inputLockReason));
  setDisabled(document.querySelector("#marriage-request-form button[type='submit']"), Boolean(submitLockReason), submitLockReason);
  const hint = document.querySelector("#marriage-request-hint");
  if (hint) {
    hint.textContent = submitLockReason
      ? submitLockReason
      : `${marriage.request_hint || "可递上结缘信物。"} 当前准备发送给 ${target?.display_label || `TG ${target?.tg || 0}`}。`;
  }
}

function inventoryGiftRows(kind, bundle = state.profileBundle) {
  const profileBundle = bundle || {};
  if (kind === "artifact") {
    return (profileBundle.artifacts || [])
      .map((row) => {
        const quantity = Number(row.unbound_quantity ?? Math.max(Number(row.quantity || 0) - Number(row.bound_quantity || 0), 0));
        return {
          value: Number(row.artifact?.id || 0),
          label: `${row.artifact?.name || "未命名法宝"} · 可赠 ${quantity}`,
          quantity,
        };
      })
      .filter((item) => item.value > 0 && item.quantity > 0);
  }
  if (kind === "talisman") {
    return (profileBundle.talismans || [])
      .map((row) => {
        const quantity = Number(row.unbound_quantity ?? Math.max(Number(row.quantity || 0) - Number(row.bound_quantity || 0), 0));
        return {
          value: Number(row.talisman?.id || 0),
          label: `${row.talisman?.name || "未命名符箓"} · 可赠 ${quantity}`,
          quantity,
        };
      })
      .filter((item) => item.value > 0 && item.quantity > 0);
  }
  if (kind === "pill") {
    return (profileBundle.pills || [])
      .map((row) => ({
        value: Number(row.pill?.id || 0),
        label: `${row.pill?.name || "未命名丹药"} · 持有 ${Number(row.quantity || 0)}`,
        quantity: Number(row.quantity || 0),
      }))
      .filter((item) => item.value > 0 && item.quantity > 0);
  }
  return (profileBundle.materials || [])
    .map((row) => ({
      value: Number(row.material?.id || 0),
      label: `${row.material?.name || "未命名材料"} · 持有 ${Number(row.quantity || 0)}`,
      quantity: Number(row.quantity || 0),
    }))
    .filter((item) => item.value > 0 && item.quantity > 0);
}

function renderItemGiftInventorySelect(bundle = state.profileBundle) {
  const kind = document.querySelector("#item-gift-kind")?.value || "artifact";
  const select = document.querySelector("#item-gift-ref");
  const quantityInput = document.querySelector("#item-gift-quantity");
  const hint = document.querySelector("#item-gift-hint");
  const previousValue = select?.value || "";
  const rows = inventoryGiftRows(kind, bundle);
  if (!select) return;
  if (!rows.length) {
    setSelectOptions(select, [{ value: "", label: "当前类型暂无可赠送物品" }], "");
    if (quantityInput) quantityInput.value = "1";
    if (hint && !currentGiftTarget()) {
      hint.textContent = "先搜索并选中一位道友，再赠送背包物品。";
    } else if (hint) {
      hint.textContent = "当前类型没有可赠送的未绑定物品，切换类型后再试。";
    }
    return;
  }
  const selectedRow = rows.find((item) => String(item.value) === String(previousValue)) || rows[0];
  setSelectOptions(select, rows, String(selectedRow.value));
  if (quantityInput) {
    const maxQuantity = Math.max(Number(selectedRow.quantity || 1), 1);
    quantityInput.max = String(maxQuantity);
    quantityInput.value = String(Math.min(Number(quantityInput.value || 1), maxQuantity));
  }
  if (hint) {
    const target = currentGiftTarget();
    hint.textContent = target
      ? `当前赠送目标：${target.display_label || (target.username ? `@${target.username}` : `TG ${target.tg}`)}。不会展示对方面板信息。`
      : "先搜索并选中一位道友，再赠送背包物品。";
  }
}

function syncGiftPanelState(bundle = state.profileBundle) {
  renderGiftTargetSelection();
  renderGiftSearchResults();
  renderItemGiftInventorySelect(bundle);
  const duelLockReason = currentDuelLockReason(bundle);
  const socialLockReason = currentSocialInteractionLockReason(bundle);
  const target = currentGiftTarget();
  const interactionLockReason = duelLockReason || socialLockReason;
  const giftBlockedReason = interactionLockReason || (target ? "" : "先选择赠送对象。");
  ["#gift-player-query", "#gift-player-search", "#item-gift-kind", "#item-gift-ref", "#item-gift-quantity"]
    .forEach((selector) => setDisabled(document.querySelector(selector), Boolean(interactionLockReason), interactionLockReason));
  setDisabled(document.querySelector("#gift-form button[type='submit']"), Boolean(giftBlockedReason), giftBlockedReason);
  setDisabled(document.querySelector("#item-gift-form button[type='submit']"), Boolean(giftBlockedReason), giftBlockedReason);
}

async function searchGiftPlayers(query, page = 1) {
  const keyword = String(query || "").trim();
  state.giftSearchQuery = keyword;
  if (!keyword) {
    state.giftSearchResults = [];
    renderGiftSearchResults([]);
    return { items: [], page: 1, page_size: 0, total: 0 };
  }
  const requestKeyword = keyword;
  const payload = await postJson("/plugins/xiuxian/api/player/search", {
    query: keyword,
    page,
    page_size: 8,
  });
  if (state.giftSearchQuery !== requestKeyword) {
    return payload;
  }
  state.giftSearchResults = payload.items || [];
  renderGiftSearchResults(state.giftSearchResults);
  return payload;
}

function profileRootText(profile) {
  if (!profile.root_type) return "尚未踏入仙途";
  if (profile.root_type === "双灵根") {
    return `${profile.root_type} · ${profile.root_primary}/${profile.root_secondary} · ${profile.root_relation}`;
  }
  return `${profile.root_type} · ${profile.root_primary || "无属性"} · ${profile.root_relation || "待定"}`;
}

function renderBottomNav(items = []) {
  const nav = document.querySelector("#bottom-nav");
  if (!nav) return;
  const currentPath = window.location.pathname;
  nav.innerHTML = "";
  nav.classList.toggle("hidden", !(items || []).length);
  for (const item of items || []) {
    const link = document.createElement("a");
    link.href = item.path;
    link.textContent = `${item.icon || ""} ${item.label}`.trim();
    if (item.path === currentPath) {
      link.classList.add("is-active");
    }
    nav.appendChild(link);
  }
}

function visibleFoldCards() {
  return [...document.querySelectorAll(".fold-card")].filter((card) => !card.classList.contains("hidden"));
}

function foldCardLabel(card) {
  return card?.querySelector(".fold-summary h2")?.textContent?.trim() || "未命名模块";
}

function jumpToFoldCard(cardId) {
  const card = document.getElementById(cardId);
  if (!card || card.classList.contains("hidden")) return;
  card.open = true;
  card.scrollIntoView({ behavior: "smooth", block: "start" });
  syncFoldToolbar();
}

function syncFoldToolbar() {
  const toolbar = document.querySelector("#fold-toolbar");
  if (!toolbar) return;

  const cards = visibleFoldCards();
  toolbar.classList.toggle("hidden", cards.length < 2);

  const count = document.querySelector("#fold-count");
  if (count) {
    count.textContent = `当前显示 ${cards.length} 个模块`;
  }

  const openAllButton = document.querySelector("[data-fold-open-all]");
  const closeAllButton = document.querySelector("[data-fold-close-all]");
  if (openAllButton) {
    openAllButton.disabled = !cards.some((card) => !card.open);
  }
  if (closeAllButton) {
    closeAllButton.disabled = !cards.some((card) => card.open);
  }

  const shortcuts = document.querySelector("#fold-shortcuts");
  if (shortcuts) {
    shortcuts.innerHTML = "";
    for (const card of cards) {
      if (!card.id) continue;
      const wrapper = document.createElement("div");
      wrapper.className = "shortcut-wrapper";
      
      const button = document.createElement("button");
      button.type = "button";
      button.className = `ghost fold-shortcut${card.open ? " is-active" : ""}`;
      button.textContent = foldCardLabel(card);
      button.dataset.foldTarget = card.id;
      
      const upBtn = document.createElement("button");
      upBtn.className = "sort-btn up";
      upBtn.innerHTML = "↑";
      upBtn.onclick = (e) => { e.stopPropagation(); moveShortcut(wrapper, -1); };
      
      const downBtn = document.createElement("button");
      downBtn.className = "sort-btn down";
      downBtn.innerHTML = "↓";
      downBtn.onclick = (e) => { e.stopPropagation(); moveShortcut(wrapper, 1); };

      wrapper.appendChild(upBtn);
      wrapper.appendChild(button);
      wrapper.appendChild(downBtn);
      shortcuts.appendChild(wrapper);
    }
  }
}

function toggleFoldCards(open) {
  visibleFoldCards().forEach((card) => {
    card.open = open;
  });
  syncFoldToolbar();
}

function setupFoldToolbar() {
  document.querySelector("[data-fold-open-all]")?.addEventListener("click", () => toggleFoldCards(true));
  document.querySelector("[data-fold-close-all]")?.addEventListener("click", () => toggleFoldCards(false));
  const shortcuts = document.querySelector("#fold-shortcuts");
  if (shortcuts) {
    shortcuts.addEventListener("click", (event) => {
      const button = event.target.closest("[data-fold-target]");
      if (!button) return;
      jumpToFoldCard(button.dataset.foldTarget);
    });

    // Touch/click sorting replaced dragging
    window.moveShortcut = (wrapper, direction) => {
      const parent = wrapper.parentNode;
      const index = Array.from(parent.children).indexOf(wrapper);
      if (direction === -1 && index > 0) {
        parent.insertBefore(wrapper, parent.children[index - 1]);
      } else if (direction === 1 && index < parent.children.length - 1) {
        parent.insertBefore(wrapper, parent.children[index + 2]);
      }
      syncBoardGridFromShortcuts();
    };

    function syncBoardGridFromShortcuts() {
      const boardGrid = document.querySelector(".board-grid");
      if (boardGrid) {
        const newOrderIds = Array.from(shortcuts.querySelectorAll(".fold-shortcut"))
          .map(btn => btn.dataset.foldTarget)
          .filter(Boolean);
          
        const cardMap = new Map();
        Array.from(boardGrid.querySelectorAll(".fold-card")).forEach(c => cardMap.set(c.id, c));
        
        newOrderIds.forEach(id => {
          if (cardMap.has(id)) {
            boardGrid.appendChild(cardMap.get(id));
            cardMap.delete(id);
          }
        });
        cardMap.forEach(c => boardGrid.appendChild(c));
        
        localStorage.setItem("xiuxian_layout_order", JSON.stringify(
          Array.from(boardGrid.querySelectorAll(".fold-card")).map(c => c.id).filter(Boolean)
        ));
      }
    }
  }

  document.querySelectorAll(".fold-card").forEach((card) => {
    card.addEventListener("toggle", syncFoldToolbar);
  });
  syncFoldToolbar();
}

function ensureSectionState(selector, visible, openWhenVisible = false) {
  const section = document.querySelector(selector);
  if (!section) return;
  section.classList.toggle("hidden", !visible);
  if (!visible) {
    section.open = false;
  } else if (openWhenVisible) {
    section.open = true;
  }
  syncFoldToolbar();
}

function inventoryRowsByKind(kind, bundle = state.profileBundle) {
  const source = bundle || {};
  if (kind === "artifact") return source.artifacts || [];
  if (kind === "pill") return source.pills || [];
  if (kind === "talisman") return source.talismans || [];
  if (kind === "material") return source.materials || [];
  return [];
}

function tradeableInventoryRows(kind, bundle = state.profileBundle) {
  return inventoryRowsByKind(kind, bundle).filter((row) => Number(row.tradeable_quantity ?? row.quantity ?? 0) > 0);
}

function populateTradeableInventorySelect(select, kind, emptyText) {
  if (!select) return;
  const previousValue = select.value;
  const rows = tradeableInventoryRows(kind);
  select.innerHTML = "";
  if (!rows.length) {
    select.innerHTML = `<option value="">${emptyText}</option>`;
    return;
  }

  rows.forEach((row) => {
    const item = row[kind];
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = `${item.name} · 可交易 ${row.tradeable_quantity ?? row.quantity}`;
    select.appendChild(option);
  });

  if ([...select.options].some((option) => String(option.value) === String(previousValue))) {
    select.value = previousValue;
  }
}

function renderInventorySelect() {
  const select = document.querySelector("#shop-item-ref");
  const kind = document.querySelector("#shop-item-kind")?.value || "artifact";
  populateTradeableInventorySelect(select, kind, "暂无可上架物品");
}

function renderAuctionInventorySelect() {
  const select = document.querySelector("#auction-item-ref");
  const kind = document.querySelector("#auction-item-kind")?.value || "artifact";
  populateTradeableInventorySelect(select, kind, "暂无可拍卖物品");
}

function officialRecycleItems(bundle = state.profileBundle) {
  return Array.isArray(bundle?.official_recycle?.items) ? bundle.official_recycle.items : [];
}

function findOfficialRecycleQuote(kind, itemRefId, bundle = state.profileBundle) {
  return officialRecycleItems(bundle).find(
    (row) => String(row.item_kind || "") === String(kind || "") && String(row.item_ref_id || "") === String(itemRefId || "")
  ) || null;
}

function populateOfficialRecycleInventorySelect() {
  const select = document.querySelector("#official-recycle-item-ref");
  if (!select) return;
  const previousValue = select.value;
  const kind = document.querySelector("#official-recycle-kind")?.value || "artifact";
  const rows = officialRecycleItems().filter((row) => String(row.item_kind || "") === String(kind) && Number(row.available_quantity || 0) > 0);
  select.innerHTML = "";
  if (!rows.length) {
    select.innerHTML = `<option value="">暂无可回收物品</option>`;
    return;
  }
  rows.forEach((row) => {
    const option = document.createElement("option");
    option.value = row.item_ref_id;
    option.textContent = `${row.item_name} · 可回收 ${row.available_quantity} · ${row.unit_price_stone} 灵石/件`;
    select.appendChild(option);
  });
  if ([...select.options].some((option) => String(option.value) === String(previousValue))) {
    select.value = previousValue;
  }
}

function updateOfficialRecycleQuotePreview(bundle = state.profileBundle) {
  const preview = document.querySelector("#official-recycle-preview");
  const quantityInput = document.querySelector("#official-recycle-quantity");
  const hint = document.querySelector("#official-recycle-hint");
  const kind = document.querySelector("#official-recycle-kind")?.value || "artifact";
  const itemRefId = Number(document.querySelector("#official-recycle-item-ref")?.value || 0);
  const quote = findOfficialRecycleQuote(kind, itemRefId, bundle);
  if (!preview || !quantityInput) return;
  if (!quote) {
    quantityInput.max = "1";
    if (Number(quantityInput.value || 0) < 1) quantityInput.value = "1";
    preview.value = officialRecycleItems(bundle).length ? "请选择可回收物品" : "暂无可回收物品";
    if (hint) {
      hint.textContent = String(bundle?.official_recycle?.description || "官方会按物品品阶与属性保守估价回收。");
    }
    return;
  }
  const availableQuantity = Math.max(Number(quote.available_quantity || 0), 0);
  let quantity = Math.max(Number(quantityInput.value || 1), 1);
  if (availableQuantity > 0) {
    quantity = Math.min(quantity, availableQuantity);
  }
  quantityInput.max = String(Math.max(availableQuantity, 1));
  quantityInput.value = String(quantity);
  const totalPrice = Math.max(Number(quote.unit_price_stone || 0), 0) * quantity;
  preview.value = `单价 ${quote.unit_price_stone || 0} 灵石，当前可回收 ${availableQuantity} 件，本次到账 ${totalPrice} 灵石`;
  if (hint) {
    hint.textContent = String(quote.quote_note || bundle?.official_recycle?.description || "官方会按物品品阶与属性保守估价回收。");
  }
}

function taskRequirementRows(kind) {
  const bundle = state.profileBundle || {};
  if (kind === "artifact") {
    return (bundle.artifacts || [])
      .filter((row) => Number(row.consumable_quantity ?? row.quantity ?? 0) > 0)
      .map((row) => ({ value: row.artifact.id, label: `${row.artifact.name} · 可提交 ${row.consumable_quantity ?? row.quantity}` }));
  }
  if (kind === "pill") {
    return (bundle.pills || [])
      .filter((row) => Number(row.quantity || 0) > 0)
      .map((row) => ({ value: row.pill.id, label: `${row.pill.name} · 库存 ${row.quantity}` }));
  }
  if (kind === "talisman") {
    return (bundle.talismans || [])
      .filter((row) => Number(row.consumable_quantity ?? row.quantity ?? 0) > 0)
      .map((row) => ({ value: row.talisman.id, label: `${row.talisman.name} · 可提交 ${row.consumable_quantity ?? row.quantity}` }));
  }
  if (kind === "material") {
    return (bundle.materials || [])
      .filter((row) => Number(row.quantity || 0) > 0)
      .map((row) => ({ value: row.material.id, label: `${row.material.name} · 库存 ${row.quantity}` }));
  }
  return [];
}

function renderTaskRequirementSelect() {
  const kind = document.querySelector("#task-required-kind")?.value || "";
  const select = document.querySelector("#task-required-ref");
  if (!select) return;
  const previousValue = select.value;
  const rows = taskRequirementRows(kind);
  select.innerHTML = "";
  select.disabled = !kind;
  if (!rows.length) {
    select.innerHTML = `<option value="">${kind ? "暂无可提交物品" : "无"}</option>`;
    select.value = "";
    return;
  }
  rows.forEach((row) => {
    const option = document.createElement("option");
    option.value = row.value;
    option.textContent = row.label;
    select.appendChild(option);
  });
  select.disabled = false;
  if (rows.some((row) => String(row.value) === String(previousValue))) {
    select.value = previousValue;
  }
}

function applyShopNameState(shopName) {
  const input = document.querySelector("#shop-name");
  const button = document.querySelector("#shop-name-toggle");
  if (!input) return;
  input.value = shopName || "游仙小铺";
  input.readOnly = !state.shopNameEditing;
  if (button) {
    button.textContent = state.shopNameEditing ? "锁定铺名" : "修改铺名";
  }
}

function artifactTypeLabel(type) {
  return type === "support" ? "辅助法宝" : "战斗法宝";
}

function fallbackReason(reason, fallback) {
  const message = String(reason || "").trim();
  return !message || /^[?？.\s]+$/.test(message) ? fallback : message;
}

function meaningfulTextLength(value) {
  return String(value ?? "").replace(/\s+/g, "").length;
}

function taskPublishBlockReason(bundle = state.profileBundle) {
  const settings = bundle?.settings || {};
  const publishAllowed = settings.allow_user_task_publish ?? true;
  const publishCost = Number(settings.task_publish_cost || 0);
  const dailyLimit = Number(settings.user_task_daily_limit || 0);
  const publishedToday = Number(settings.user_task_published_today || 0);
  const currentStone = Number(bundle?.profile?.spiritual_stone || 0);
  const duelLockReason = currentDuelLockReason(bundle);

  if (!publishAllowed) {
    return "当前未开放玩家发布任务。";
  }
  if (duelLockReason) {
    return duelLockReason;
  }
  if (dailyLimit > 0 && publishedToday >= dailyLimit) {
    return `今日已发布 ${publishedToday}/${dailyLimit} 次悬赏，已达到上限。`;
  }
  if (currentStone < publishCost) {
    return `发布任务需要 ${publishCost} 灵石，当前灵石不足。`;
  }
  return "";
}

function applyInteractiveBlockState(button, blocked, reason = "") {
  if (!button) return;
  const message = blocked ? String(reason || "").trim() : "";
  button.classList.toggle("is-blocked", Boolean(message));
  button.title = message;
  button.setAttribute("aria-disabled", message ? "true" : "false");
  if (message) {
    button.dataset.blockedReason = message;
  } else {
    delete button.dataset.blockedReason;
  }
}

function renderProfile(bundle) {
  state.profileBundle = bundle;
  const profile = bundle.profile;

  if (!profile.consented) {
    ensureSectionState("#enter-card", true, true);
    [
      "#profile-card",
      "#action-card",
      "#exchange-card",
      "#inventory-card",
      "#technique-card",
      "#official-shop-card",
      "#market-card",
      "#auction-card",
      "#leaderboard-card",
      "#sect-card",
      "#task-card",
      "#craft-card",
      "#explore-card",
      "#red-envelope-card",
      "#journal-card",
      "#gift-card"
    ].forEach((selector) => ensureSectionState(selector, false));
    setStatus("你还没有踏入仙途，确认后会立即抽取灵根并创建修仙档案。", "warning");
    return;
  }

  ensureSectionState("#enter-card", false);
  ensureSectionState("#profile-card", true, true);
  ensureSectionState("#action-card", true, true);
  ensureSectionState("#exchange-card", true);
  ensureSectionState("#inventory-card", true);
  ensureSectionState("#technique-card", true);
  ensureSectionState("#official-shop-card", true);
  ensureSectionState("#market-card", true);
  ensureSectionState("#auction-card", true);
  ensureSectionState("#leaderboard-card", true);
  ensureSectionState("#sect-card", true);
  ensureSectionState("#task-card", true);
  ensureSectionState("#craft-card", true);
  ensureSectionState("#explore-card", true);
  ensureSectionState("#red-envelope-card", true);
  ensureSectionState("#journal-card", true);
  ensureSectionState("#gift-card", true);

  const progress = bundle.progress || {};
  const retreating = bundle.capabilities?.is_in_retreat;
  const equippedArtifacts = bundle.equipped_artifacts || [];
  const artifactNames = equippedArtifacts.length ? equippedArtifacts.map((item) => item.name).join("、") : "暂无";
  const equipLimit = bundle.settings?.artifact_equip_limit || bundle.capabilities?.artifact_equip_limit || 1;
  const talismanName = bundle.active_talisman?.name || "暂无";
  const retreatStatus = retreating ? `闭关中，预计结束 ${formatDate(profile.retreat_end_at)}` : "未在闭关";

  document.querySelector("#realm-badge").textContent = `${profile.realm_stage}${profile.realm_layer}层`;
  document.querySelector("#root-text").textContent = `灵根：${profileRootText(profile)} · 斗法修正 ${profile.root_bonus >= 0 ? "+" : ""}${profile.root_bonus}%`;
  document.querySelector("#profile-grid").innerHTML = `
    <article class="profile-item"><span>境界</span><strong>${escapeHtml(profile.realm_stage)}${escapeHtml(profile.realm_layer)}层</strong></article>
    <article class="profile-item"><span>当前修为</span><strong>${escapeHtml(progress.current ?? profile.cultivation)} / ${escapeHtml(progress.threshold ?? 0)}</strong></article>
    <article class="profile-item"><span>距离下层</span><strong>${escapeHtml(progress.remaining ?? 0)}</strong></article>
    <article class="profile-item"><span>灵石</span><strong>${escapeHtml(profile.spiritual_stone)}</strong></article>
    <article class="profile-item"><span>片刻碎片</span><strong>${escapeHtml(bundle.emby_balance)}</strong></article>
    <article class="profile-item"><span>丹毒</span><strong>${escapeHtml(profile.dan_poison)}/100</strong></article>
    <article class="profile-item"><span>已装备法宝</span><strong>${escapeHtml(artifactNames)}</strong></article>
    <article class="profile-item"><span>装备数量</span><strong>${escapeHtml(equippedArtifacts.length)} / ${escapeHtml(equipLimit)}</strong></article>
    <article class="profile-item"><span>待生效符箓</span><strong>${escapeHtml(talismanName)}</strong></article>
    <article class="profile-item"><span>闭关状态</span><strong>${escapeHtml(retreatStatus)}</strong></article>
  `;

  const hints = [];
  if (retreating) {
    hints.push("闭关中，无法使用其他修仙功能");
  } else {
    if (!bundle.capabilities?.can_train) hints.push("今日吐纳次数已用完");
    if (!bundle.capabilities?.can_breakthrough) hints.push("当前尚未达到可突破条件");
  }
  document.querySelector("#action-hint").textContent = hints.join(" · ") || "当前状态良好，可以继续修炼、突破或闭关。";

  const exchangeEnabled = bundle.settings?.coin_stone_exchange_enabled ?? true;
  document.querySelector("#exchange-hint").textContent =
    exchangeEnabled
      ? `当前比例：1 片刻碎片 = ${bundle.settings.rate} 灵石，手续费 ${bundle.settings.fee_percent}%，灵石兑换碎片最低 ${bundle.settings.min_coin_exchange} 灵石。`
      : "灵石互兑功能当前已关闭，可联系管理员在后台重新开启。";

  setDisabled(document.querySelector("#train-btn"), !bundle.capabilities?.can_train, "当前无法吐纳修炼");
  applyBreakthroughActionState(bundle, "当前无法尝试突破");
  setDisabled(document.querySelector("#retreat-start-btn"), !bundle.capabilities?.can_retreat, "当前无法开始闭关");
  setDisabled(document.querySelector("#retreat-finish-btn"), !retreating, "当前没有进行中的闭关");

  renderArtifactList(bundle.artifacts, retreating, equipLimit, equippedArtifacts.length);
  renderTalismanList(bundle.talismans, retreating);
  renderPillList(bundle.pills, retreating);
  renderOfficialShop(bundle.official_shop, retreating);
  renderPersonalShop(bundle.personal_shop);
  renderCommunityShop(bundle.community_shop, retreating);
  renderInventorySelect();

  const shopDisabledReason = retreating ? "闭关期间无法经营店铺" : "";
  ["#shop-item-kind", "#shop-item-ref", "#shop-quantity", "#shop-price", "#shop-name", "#shop-broadcast"]
    .forEach((selector) => setDisabled(document.querySelector(selector), retreating, shopDisabledReason));
  setDisabled(document.querySelector("#personal-shop-form button[type='submit']"), retreating, shopDisabledReason);
}

function renderProfile(bundle) {
  state.profileBundle = bundle;
  const profile = bundle.profile || {};
  const consented = Boolean(profile.consented);

  ensureSectionState("#enter-card", !consented, true);
  [
    "#profile-card",
    "#action-card",
    "#exchange-card",
    "#inventory-card",
    "#technique-card",
    "#official-shop-card",
    "#official-recycle-card",
    "#market-card",
    "#auction-card",
    "#leaderboard-card",
    "#sect-card",
    "#task-card",
    "#craft-card",
    "#explore-card",
    "#red-envelope-card",
    "#journal-card",
    "#gift-card",
  ].forEach((selector) => ensureSectionState(selector, consented));

  if (!consented) {
    setStatus("你还没有踏入仙途，确认后就会抽取灵根并建立修仙档案。", "warning");
    return;
  }

  const progress = bundle.progress || {};
  const settings = bundle.settings || {};
  const retreating = Boolean(bundle.capabilities?.is_in_retreat);
  const equippedArtifacts = bundle.equipped_artifacts || [];
  const equipLimit = settings.artifact_equip_limit || bundle.capabilities?.artifact_equip_limit || 1;
  const artifactNames = equippedArtifacts.length ? equippedArtifacts.map((item) => item.name).join("、") : "暂无";
  const talismanName = bundle.active_talisman?.name || "暂无";
  const retreatStatus = retreating ? `闭关中，预计结束 ${formatDate(profile.retreat_end_at)}` : "未在闭关";
  const profileGrid = document.querySelector("#profile-grid");
  const rootText = document.querySelector("#root-text");
  const realmBadge = document.querySelector("#realm-badge");

  if (realmBadge) {
    realmBadge.textContent = `${profile.realm_stage || "炼气"}${profile.realm_layer || 0}层`;
  }
  if (rootText) {
    rootText.textContent = `灵根：${profileRootText(profile)} · 斗法修正 ${profile.root_bonus >= 0 ? "+" : ""}${profile.root_bonus || 0}%`;
  }
  if (profileGrid) {
    profileGrid.innerHTML = `
      <article class="profile-item"><span>境界</span><strong>${escapeHtml(profile.realm_stage || "炼气")}${escapeHtml(profile.realm_layer || 0)}层</strong></article>
      <article class="profile-item"><span>当前修为</span><strong>${escapeHtml(progress.current ?? profile.cultivation ?? 0)} / ${escapeHtml(progress.threshold ?? 0)}</strong></article>
      <article class="profile-item"><span>距离下一层</span><strong>${escapeHtml(progress.remaining ?? 0)}</strong></article>
      <article class="profile-item"><span>灵石</span><strong>${escapeHtml(profile.spiritual_stone ?? 0)}</strong></article>
      <article class="profile-item"><span>片刻碎片</span><strong>${escapeHtml(bundle.emby_balance ?? 0)}</strong></article>
      <article class="profile-item"><span>丹毒</span><strong>${escapeHtml(profile.dan_poison ?? 0)} / 100</strong></article>
      <article class="profile-item"><span>法宝</span><strong>${escapeHtml(artifactNames)}</strong></article>
      <article class="profile-item"><span>装备数量</span><strong>${escapeHtml(equippedArtifacts.length)} / ${escapeHtml(equipLimit)}</strong></article>
      <article class="profile-item"><span>待生效符箓</span><strong>${escapeHtml(talismanName)}</strong></article>
      <article class="profile-item"><span>闭关状态</span><strong>${escapeHtml(retreatStatus)}</strong></article>
      <article class="profile-item"><span>宗门贡献</span><strong>${escapeHtml(profile.sect_contribution ?? 0)}</strong></article>
      <article class="profile-item"><span>魅力</span><strong>${escapeHtml(bundle.effective_stats?.charisma ?? profile.charisma ?? 0)}</strong></article>
      <article class="profile-item"><span>机缘</span><strong>${escapeHtml(bundle.effective_stats?.fortune ?? profile.fortune ?? 0)}</strong></article>
    `;
  }

  const hints = [];
  if (retreating) {
    hints.push("闭关期间无法使用大部分修仙功能。");
  } else {
    if (!bundle.capabilities?.can_train) hints.push("今日吐纳次数已经用完。");
    if (!bundle.capabilities?.can_breakthrough) hints.push("达到当前大境界九层满修为后才可突破。");
  }
  const actionHint = document.querySelector("#action-hint");
  if (actionHint) {
    actionHint.textContent = hints.join(" ") || "状态平稳，可以继续吐纳、突破、经营坊市或探索。";
  }

  const rate = settings.rate ?? settings.coin_exchange_rate ?? 100;
  const fee = settings.fee_percent ?? settings.exchange_fee_percent ?? 1;
  const minExchange = settings.min_coin_exchange ?? 1;
  const exchangeEnabled = settings.coin_stone_exchange_enabled ?? true;
  const exchangeHint = document.querySelector("#exchange-hint");
  if (exchangeHint) {
    exchangeHint.textContent = exchangeEnabled
      ? `当前比例：1 片刻碎片 = ${rate} 灵石，手续费 ${fee}%，灵石兑换碎片最低消耗 ${minExchange} 灵石，不足 ${rate} 灵石一份的零头会保留。`
      : "灵石互兑功能当前已关闭，可联系管理员在后台重新开启。";
  }
  const officialShopTitle = document.querySelector("#official-shop-title");
  if (officialShopTitle) {
    officialShopTitle.textContent = officialShopName(bundle);
  }

  setDisabled(document.querySelector("#train-btn"), !bundle.capabilities?.can_train, "当前无法吐纳修炼");
  applyBreakthroughActionState(bundle, "当前无法尝试突破");
  setDisabled(document.querySelector("#retreat-start-btn"), !bundle.capabilities?.can_retreat, "当前无法开始闭关");
  setDisabled(document.querySelector("#retreat-finish-btn"), !retreating, "当前没有进行中的闭关");
  const exchangeDisabledReason = !exchangeEnabled
    ? "灵石互兑功能当前已关闭。"
    : (retreating ? "闭关期间无法兑换灵石和片刻碎片。" : "");
  ["#coin-to-stone-amount", "#stone-to-coin-amount"]
    .forEach((selector) => setDisabled(document.querySelector(selector), retreating || !exchangeEnabled, exchangeDisabledReason));
  setDisabled(document.querySelector("#coin-to-stone-form button[type='submit']"), retreating || !exchangeEnabled, exchangeDisabledReason);
  setDisabled(document.querySelector("#stone-to-coin-form button[type='submit']"), retreating || !exchangeEnabled, exchangeDisabledReason);

  const shopDisabledReason = retreating ? "闭关期间无法经营店铺。" : "";
  ["#shop-item-kind", "#shop-item-ref", "#shop-quantity", "#shop-price", "#shop-name", "#shop-broadcast"]
    .forEach((selector) => setDisabled(document.querySelector(selector), retreating, shopDisabledReason));
  setDisabled(document.querySelector("#personal-shop-form button[type='submit']"), retreating, shopDisabledReason);

  renderArtifactList(bundle.artifacts || [], retreating, equipLimit, equippedArtifacts.length);
  renderTalismanList(bundle.talismans || [], retreating);
  renderPillList(bundle.pills || [], retreating);
  renderOfficialShop(bundle.official_shop || [], retreating);
  renderPersonalShop(bundle.personal_shop || []);
  renderCommunityShop(bundle.community_shop || [], retreating);
  renderInventorySelect();
  renderJournalArea(bundle);
}

function renderArtifactList(items, retreating, equipLimit, equippedCount) {
  const root = document.querySelector("#artifact-list");
  root.innerHTML = "";
  if (!items.length) {
    root.innerHTML = `<article class="stack-item"><strong>暂无法宝</strong><p>管理后台发放或在${escapeHtml(officialShopName())}购买后会出现在这里。</p></article>`;
    return;
  }

  for (const row of items) {
    const item = row.artifact;
    const effects = item.resolved_effects || {};
    const disabled = !item.usable || retreating;
    const fallback = retreating
      ? "闭关期间无法切换法宝"
      : item.equipped
        ? "当前法宝已装备"
        : equippedCount >= equipLimit
          ? `当前最多只能装备 ${equipLimit} 件法宝`
          : "当前条件不满足，暂时无法装备";
    const reason = retreating || !item.equipped ? fallbackReason(item.unusable_reason, fallback) : "";

    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        <span class="badge badge--normal">x${escapeHtml(row.quantity)}</span>
      </div>
      <p>${escapeHtml(item.description || "暂无描述")}</p>
      <div class="item-tags">
        <span class="tag ${item.artifact_type === "support" ? "support" : ""}">${escapeHtml(item.artifact_type_label || artifactTypeLabel(item.artifact_type))}</span>
        ${item.unique_item ? `<span class="tag">唯一</span>` : ""}
        <span class="tag">攻击 ${escapeHtml(effects.attack_bonus ?? item.attack_bonus)}</span>
        <span class="tag">防御 ${escapeHtml(effects.defense_bonus ?? item.defense_bonus)}</span>
        <span class="tag">斗法 +${escapeHtml(effects.duel_rate_bonus ?? item.duel_rate_bonus)}%</span>
        <span class="tag">修炼 +${escapeHtml(effects.cultivation_bonus ?? item.cultivation_bonus)}</span>
      </div>
      <p>境界要求：${escapeHtml(item.min_realm_stage ? `${item.min_realm_stage}${item.min_realm_layer}层` : "无限制")}</p>
      ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : ""}
      <button type="button" data-equip-id="${item.id}" ${disabled ? "disabled" : ""}>${escapeHtml(item.action_label || (item.equipped ? "卸下法宝" : "装备法宝"))}</button>
    `;
    root.appendChild(card);
  }
}

function renderPillList(items, retreating) {
  const root = document.querySelector("#pill-list");
  root.innerHTML = "";
  if (!items.length) {
    root.innerHTML = `<article class="stack-item"><strong>暂无丹药</strong><p>${escapeHtml(officialShopName())}购买或主人发放后会出现在这里。</p></article>`;
    return;
  }

  for (const row of items) {
    const item = row.pill;
    const effects = item.resolved_effects || {};
    const disabled = !item.usable || retreating;
    const reason = item.usable ? "" : fallbackReason(item.unusable_reason, retreating ? "闭关期间无法服用丹药" : "当前条件不满足，暂时无法服用");

    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        <span class="badge badge--pending">x${escapeHtml(row.quantity)}</span>
      </div>
      <p>${escapeHtml(item.description || "暂无描述")}</p>
      <div class="item-tags">
        <span class="tag">${escapeHtml(item.pill_type_label)}</span>
        <span class="tag">${escapeHtml(item.effect_value_label || "效果值")} ${escapeHtml(effects.effect_value ?? item.effect_value)}</span>
        <span class="tag">丹毒 +${escapeHtml(effects.poison_delta ?? item.poison_delta)}</span>
      </div>
      <p>境界要求：${escapeHtml(item.min_realm_stage ? `${item.min_realm_stage}${item.min_realm_layer}层` : "无限制")}</p>
      ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : ""}
      <button type="button" data-pill-id="${item.id}" ${disabled ? "disabled" : ""}>服用丹药</button>
    `;
    root.appendChild(card);
  }
}

function renderTalismanList(items, retreating) {
  const root = document.querySelector("#talisman-list");
  root.innerHTML = "";
  if (!items.length) {
    root.innerHTML = `<article class="stack-item"><strong>暂无符箓</strong><p>符箓会在下一场斗法中生效，后台发放或商店购买后会出现在这里。</p></article>`;
    return;
  }

  for (const row of items) {
    const item = row.talisman;
    const effects = item.resolved_effects || {};
    const disabled = item.active || !item.usable || retreating;
    const reason = item.active
      ? "当前已有待生效符箓"
      : fallbackReason(item.unusable_reason, retreating ? "闭关期间无法启用符箓" : "当前条件不满足，暂时无法启用");

    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        <span class="badge badge--vip">x${escapeHtml(row.quantity)}</span>
      </div>
      <p>${escapeHtml(item.description || "暂无描述")}</p>
      <div class="item-tags">
        <span class="tag">${escapeHtml(item.rarity)}</span>
        <span class="tag">攻击 ${escapeHtml(effects.attack_bonus ?? item.attack_bonus)}</span>
        <span class="tag">斗法 +${escapeHtml(effects.duel_rate_bonus ?? item.duel_rate_bonus)}%</span>
      </div>
      <p>境界要求：${escapeHtml(item.min_realm_stage ? `${item.min_realm_stage}${item.min_realm_layer}层` : "无限制")}</p>
      ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : ""}
      <button type="button" data-talisman-id="${item.id}" ${disabled ? "disabled" : ""}>${item.active ? "已待生效" : "激活到下一场斗法"}</button>
    `;
    root.appendChild(card);
  }
}

function renderOfficialShop(items, retreating) {
  const root = document.querySelector("#official-shop-list");
  root.innerHTML = "";
  if (!items.length) {
    root.innerHTML = `<article class="stack-item"><strong>${escapeHtml(officialShopName())}暂无商品</strong><p>等主人上架后，这里会自动显示。</p></article>`;
    return;
  }

  const duelLockReason = currentDuelLockReason();
  const blockedReason = retreating ? "闭关期间无法交易。" : duelLockReason;
  for (const item of items) {
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.item_name)}</strong>
        <span class="badge badge--vip">${escapeHtml(item.price_stone)} 灵石</span>
      </div>
      <p>${escapeHtml(item.item_kind_label)} · 库存 ${escapeHtml(item.quantity)} · ${escapeHtml(item.shop_name)}</p>
      ${blockedReason ? `<p class="reason-text">${escapeHtml(blockedReason)}</p>` : ""}
      <button type="button" data-buy-id="${item.id}" ${(retreating || duelLockReason) ? "disabled" : ""}>购买 1 件</button>
    `;
    root.appendChild(card);
  }
}

function renderOfficialRecyclePanel(bundle, retreating) {
  const root = document.querySelector("#official-recycle-list");
  const preview = document.querySelector("#official-recycle-preview");
  const hint = document.querySelector("#official-recycle-hint");
  if (!root) return;
  const quotes = officialRecycleItems(bundle);
  root.innerHTML = "";
  const duelLockReason = currentDuelLockReason(bundle);
  const blockedReason = retreating ? "闭关期间无法回收。" : duelLockReason;
  if (!quotes.length) {
    root.innerHTML = `<article class="stack-item"><strong>${escapeHtml(officialRecycleName(bundle))}暂无可回收物品</strong><p>未绑定且可交易的法宝、符箓，以及背包内丹药材料会显示在这里。</p></article>`;
    if (preview) preview.value = "暂无可回收物品";
    if (hint) {
      hint.textContent = String(bundle?.official_recycle?.description || "官方会按物品品阶与属性保守估价回收。");
    }
    populateOfficialRecycleInventorySelect();
    updateOfficialRecycleQuotePreview(bundle);
    return;
  }

  for (const quote of quotes) {
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(quote.item_name)}</strong>
        <span class="badge badge--normal">${escapeHtml(quote.unit_price_stone)} 灵石/件</span>
      </div>
      <div class="item-tags">
        ${qualityBadgeHtml(quote.quality_label || "凡品", quote.quality_color, "tag")}
        <span class="tag">${escapeHtml(quote.item_kind_label || quote.item_kind)}</span>
        <span class="tag">可回收 ${escapeHtml(quote.available_quantity || 0)}</span>
      </div>
      <p>当前整包回收最多到账 ${escapeHtml(quote.max_total_price_stone || 0)} 灵石。</p>
      <p class="muted">${escapeHtml(quote.quote_note || "")}</p>
      ${blockedReason ? `<p class="reason-text">${escapeHtml(blockedReason)}</p>` : ""}
    `;
    root.appendChild(card);
  }

  populateOfficialRecycleInventorySelect();
  updateOfficialRecycleQuotePreview(bundle);
}

function renderPersonalShop(items) {
  const root = document.querySelector("#personal-shop-list");
  root.innerHTML = "";
  if (!items.length) {
    root.innerHTML = `<article class="stack-item"><strong>你的店铺暂时空空如也</strong><p>可以从背包里选择法宝、符箓、丹药或材料上架。</p></article>`;
    return;
  }

  for (const item of items) {
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.item_name)}</strong>
        <span class="badge badge--normal">${escapeHtml(item.price_stone)} 灵石</span>
      </div>
      <p>${escapeHtml(item.item_kind_label)} · 库存 ${escapeHtml(item.quantity)} · ${escapeHtml(item.shop_name)}</p>
    `;
    root.appendChild(card);
  }
}

function renderCommunityShop(items, retreating) {
  const root = document.querySelector("#community-shop-list");
  root.innerHTML = "";
  if (!items.length) {
    root.innerHTML = `<article class="stack-item"><strong>群修市集暂无商品</strong><p>等有道友上架后，这里会热闹起来。</p></article>`;
    return;
  }

  const duelLockReason = currentDuelLockReason();
  const blockedReason = retreating ? "闭关期间无法交易。" : duelLockReason;
  for (const item of items) {
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.item_name)}</strong>
        <span class="badge badge--normal">${escapeHtml(item.price_stone)} 灵石</span>
      </div>
      <p>${escapeHtml(item.item_kind_label)} · 库存 ${escapeHtml(item.quantity)} · ${escapeHtml(item.shop_name)}</p>
      ${blockedReason ? `<p class="reason-text">${escapeHtml(blockedReason)}</p>` : ""}
      <button type="button" data-buy-id="${item.id}" ${(retreating || duelLockReason) ? "disabled" : ""}>购买 1 件</button>
    `;
    root.appendChild(card);
  }
}

function auctionStatusText(item) {
  return String(item?.status_label || item?.status || "未知状态");
}

function auctionBuyoutText(item) {
  const price = Number(item?.buyout_price_stone || 0);
  return price > 0 ? `${price} 灵石` : "未设置";
}

function auctionLeaderText(item) {
  return String(item?.highest_bidder_display_name || "").trim()
    || (item?.highest_bidder_tg ? `TG ${item.highest_bidder_tg}` : "暂无");
}

function renderPersonalAuctions(items = []) {
  const root = document.querySelector("#personal-auction-list");
  if (!root) return;
  root.innerHTML = "";
  if (!items.length) {
    root.innerHTML = `<article class="stack-item"><strong>你还没有发起拍卖</strong><p>从背包中挑选可交易物品后，可以直接推送到群里开拍。</p></article>`;
    return;
  }

  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "stack-item";
    let extraText = `当前价 ${item.current_display_price_stone} 灵石 · 下次出价 ${item.next_bid_price_stone} 灵石`;
    if (item.status === "sold") {
      extraText = `成交 ${item.final_price_stone} 灵石 · 入账 ${item.seller_income_stone} 灵石 · 手续费 ${item.fee_amount_stone} 灵石`;
    } else if (item.status === "expired") {
      extraText = "无人出价，拍品已经退回背包。";
    } else if (item.status === "cancelled") {
      extraText = "拍卖已取消，拍品与竞价灵石均已退回。";
    }
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.item_name)} × ${escapeHtml(item.quantity)}</strong>
        <span class="badge badge--normal">${escapeHtml(auctionStatusText(item))}</span>
      </div>
      <p>${escapeHtml(item.item_kind_label || item.item_kind)} · 结束 ${escapeHtml(formatDate(item.end_at))}</p>
      <p>加价 ${escapeHtml(item.bid_increment_stone)} 灵石 · 一口价 ${escapeHtml(auctionBuyoutText(item))}</p>
      <p>领先者：${escapeHtml(auctionLeaderText(item))} · 出价 ${escapeHtml(item.bid_count || 0)} 次</p>
      <p>${escapeHtml(extraText)}</p>
      ${item.group_message_id ? `<p class="section-copy">群消息已推送${item.status === "active" ? "并置顶" : ""}，竞拍请在群里点击按钮完成。</p>` : ""}
    `;
    root.appendChild(card);
  });
}

function renderCommunityAuctions(items = []) {
  const root = document.querySelector("#community-auction-list");
  if (!root) return;
  root.innerHTML = "";
  if (!items.length) {
    root.innerHTML = `<article class="stack-item"><strong>群内暂时没有进行中的拍卖</strong><p>等其他道友开拍后，这里会显示当前竞拍情况。</p></article>`;
    return;
  }

  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.item_name)} × ${escapeHtml(item.quantity)}</strong>
        <span class="badge badge--vip">${escapeHtml(item.current_display_price_stone)} 灵石</span>
      </div>
      <p>${escapeHtml(item.item_kind_label || item.item_kind)} · 卖家 ${escapeHtml(item.owner_display_name || `TG ${item.owner_tg || 0}`)}</p>
      <p>下次出价 ${escapeHtml(item.next_bid_price_stone)} 灵石 · 每次加价 ${escapeHtml(item.bid_increment_stone)} 灵石</p>
      <p>一口价 ${escapeHtml(auctionBuyoutText(item))} · 结束 ${escapeHtml(formatDate(item.end_at))}</p>
      <p>当前领先：${escapeHtml(auctionLeaderText(item))} · 出价 ${escapeHtml(item.bid_count || 0)} 次</p>
      <p class="section-copy">请前往群里的置顶拍卖消息点击按钮竞拍，群消息会随出价自动刷新。</p>
    `;
    root.appendChild(card);
  });
}

function taskRewardText(task) {
  const parts = [];
  if (task.reward_stone) parts.push(`${task.reward_stone} 灵石`);
  if (task.reward_item_kind && task.reward_item_quantity) {
    parts.push(`${task.reward_item_quantity} ${task.reward_item_kind_label || task.reward_item_kind}`);
  }
  return parts.join(" · ") || "无奖励";
}

function renderSectArea(bundle) {
  const currentRoot = document.querySelector("#sect-current");
  const listRoot = document.querySelector("#sect-list");
  const salaryButton = document.querySelector("#sect-salary-btn");
  if (!currentRoot || !listRoot || !salaryButton) return;

  const current = bundle.current_sect;
  currentRoot.innerHTML = "";
  if (current) {
    const role = current.current_role?.role_name || "门下弟子";
    currentRoot.innerHTML = `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(current.name)}</strong>
          <span class="badge badge--normal">${escapeHtml(role)}</span>
        </div>
        <p>${escapeHtml(current.description || "暂无宗门简介")}</p>
      </article>
    `;
    salaryButton.disabled = false;
  } else {
    currentRoot.innerHTML = `<article class="stack-item"><strong>暂未加入宗门</strong><p>可在下方选择满足条件的宗门加入。</p></article>`;
    salaryButton.disabled = true;
  }

  listRoot.innerHTML = "";
  const sects = [...(bundle.sects || [])].sort((left, right) => {
    if (Boolean(left.joinable) !== Boolean(right.joinable)) return left.joinable ? -1 : 1;
    const realmCompare = compareRealmRequirement(left.min_realm_stage, left.min_realm_layer, right.min_realm_stage, right.min_realm_layer);
    if (realmCompare !== 0) return realmCompare;
    return String(left.name || "").localeCompare(String(right.name || ""), "zh-Hans-CN");
  });
  if (!sects.length) {
    listRoot.innerHTML = `<article class="stack-item"><strong>暂无可加入宗门</strong></article>`;
    return;
  }
  for (const sect of sects) {
    const card = document.createElement("article");
    card.className = "stack-item";
    const disabled = current?.id === sect.id || !sect.joinable;
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(sect.name)}</strong>
        <span class="badge badge--normal">${escapeHtml((sect.roles || []).length)} 个职位</span>
      </div>
      <p>${escapeHtml(sect.description || "暂无简介")}</p>
      <p>条件：${escapeHtml(sect.min_realm_stage || "无")} ${escapeHtml(sect.min_realm_layer || 1)} 层 / 灵石 ${escapeHtml(sect.min_stone || 0)}</p>
      <button type="button" data-sect-id="${sect.id}" ${disabled ? "disabled" : ""}>${current?.id === sect.id ? "已加入" : "加入宗门"}</button>
      ${disabled && sect.join_reason ? `<p class="muted compact-copy">${escapeHtml(sect.join_reason)}</p>` : ""}
    `;
    listRoot.appendChild(card);
  }
}

function renderTaskArea(bundle) {
  const root = document.querySelector("#task-list");
  if (!root) return;
  root.innerHTML = "";
  const settings = bundle.settings || {};
  const publishCost = Number(settings.task_publish_cost || 0);
  const dailyLimit = Number(settings.user_task_daily_limit || 0);
  const publishedToday = Number(settings.user_task_published_today || 0);
  const publishNote = document.querySelector("#task-compose-note");
  const publishButton = document.querySelector("#task-form button[type='submit']");
  const uploadAllowed = Boolean(bundle.capabilities?.can_upload_images);
  const uploadReason = fallbackReason(bundle.capabilities?.upload_image_reason, "当前无法上传图片");
  const uploadButton = document.querySelector("#task-image-upload");
  const uploadInput = document.querySelector("#task-image-file");
  const uploadHelp = document.querySelector("#task-upload-help");
  setDisabled(uploadButton, !uploadAllowed, uploadReason);
  setDisabled(uploadInput, !uploadAllowed, uploadReason);
  if (uploadHelp) {
    uploadHelp.textContent = uploadAllowed
      ? "如需带图答题，可先上传图片再发布任务。"
      : uploadReason;
  }
  const publishReason = taskPublishBlockReason(bundle);
  applyInteractiveBlockState(publishButton, Boolean(publishReason), publishReason);
  if (publishNote) {
    const limitText = dailyLimit > 0 ? `今日已发布 ${publishedToday}/${dailyLimit} 次。` : "今日发布次数不限。";
    publishNote.textContent = publishReason || (publishCost > 0
      ? `当前发布一次任务需要消耗 ${publishCost} 灵石，且必须设置奖励。${limitText}`
      : `发布前请补充清晰信息，且必须设置奖励。${limitText}`);
  }
  renderTaskRequirementSelect();
  const tasks = bundle.tasks || [];
  if (!tasks.length) {
    root.innerHTML = `<article class="stack-item"><strong>暂无任务</strong><p>主人、宗门或玩家发布悬赏后会出现在这里。</p></article>`;
    return;
  }
  for (const task of tasks) {
    const claimStatus = task.claim?.status || "";
    const alreadyCompleted = Boolean(task.winner_tg) || claimStatus === "completed";
    const alreadyAccepted = Boolean(task.claimed) && !alreadyCompleted;
    const requiresItem = Boolean(task.required_item_kind && Number(task.required_item_quantity || 0) > 0);
    const disabled = alreadyAccepted || alreadyCompleted || task.task_type === "quiz";
    const requiredItemName = task.required_item?.name || task.required_item_kind_label || task.required_item_kind || "物品";
    const actionLabel = alreadyCompleted
      ? "已完成"
      : alreadyAccepted
        ? "已接取"
        : task.task_type === "quiz"
          ? "请到群内作答"
          : requiresItem
            ? "提交物品并完成"
            : "接取任务";
    const canCancel = Boolean(task.can_cancel);
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(task.title)}</strong>
        <span class="badge badge--normal">${escapeHtml(task.task_scope_label || task.task_scope)}</span>
      </div>
      <p>${escapeHtml(task.description || "暂无描述")}</p>
      <p>类型：${escapeHtml(task.task_type_label || task.task_type)} · 奖励：${escapeHtml(taskRewardText(task))}</p>
      ${requiresItem ? `<p>提交需求：${escapeHtml(requiredItemName)} × ${escapeHtml(task.required_item_quantity)}</p>` : ""}
      ${task.question_text ? `<p>题目：${escapeHtml(task.question_text)}</p>` : ""}
      <div class="inline-actions">
        <button type="button" data-task-id="${task.id}" data-task-action="claim" ${disabled ? "disabled" : ""}>${actionLabel}</button>
        ${canCancel ? `<button type="button" class="ghost" data-task-id="${task.id}" data-task-action="cancel">撤销任务</button>` : ""}
      </div>
    `;
    root.appendChild(card);
  }
}

function renderTechniqueArea(bundle) {
  const currentRoot = document.querySelector("#technique-current");
  const listRoot = document.querySelector("#technique-list");
  if (!currentRoot || !listRoot) return;

  const current = bundle.current_technique;
  currentRoot.innerHTML = current
    ? `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(current.name)}</strong>
          <span class="badge badge--normal">${escapeHtml(current.technique_type_label || current.technique_type || "功法")}</span>
        </div>
        <p>${escapeHtml(current.description || "暂无描述")}</p>
        <div class="item-tags">
          ${qualityBadgeHtml(current.rarity || "凡品", current.quality_color, "tag")}
          ${itemAffixTags(current, current.resolved_effects || {})}
        </div>
      </article>
    `
    : `<article class="stack-item"><strong>当前未参悟功法</strong><p>可从下方功法目录中切换一门适合你的修行路线。</p></article>`;

  const techniques = bundle.techniques || [];
  listRoot.innerHTML = "";
  if (!techniques.length) {
    listRoot.innerHTML = `<article class="stack-item"><strong>暂无可用功法</strong></article>`;
    return;
  }
  techniques.forEach((item) => {
    const effects = item.resolved_effects || {};
    const disabled = item.active || !item.usable;
    const reason = item.active ? "" : fallbackReason(item.unusable_reason, "当前无法切换到这门功法");
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        <span class="badge badge--normal">${escapeHtml(item.technique_type_label || item.technique_type || "功法")}</span>
      </div>
      <p>${escapeHtml(item.description || "暂无描述")}</p>
      <div class="item-tags">
        ${qualityBadgeHtml(item.rarity || "凡品", item.quality_color, "tag")}
        ${itemAffixTags(item, effects)}
      </div>
      <p>境界要求：${escapeHtml(item.min_realm_stage ? `${item.min_realm_stage}${item.min_realm_layer}层` : "无限制")}</p>
      ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : ""}
      <button type="button" data-technique-id="${item.id}" ${disabled ? "disabled" : ""}>${escapeHtml(item.action_label || (item.active ? "当前功法" : "切换功法"))}</button>
    `;
    listRoot.appendChild(card);
  });
}

function renderCraftArea(bundle) {
  const materialRoot = document.querySelector("#material-list");
  const recipeRoot = document.querySelector("#recipe-list");
  if (!materialRoot || !recipeRoot) return;

  const materials = bundle.materials || [];
  materialRoot.innerHTML = materials.length
    ? materials.map((row) => `<article class="stack-item"><strong>${escapeHtml(row.material.name)}</strong><p>品质 ${escapeHtml(row.material.quality_label || row.material.quality_level)} · 数量 ${escapeHtml(row.quantity)}</p><p class="muted">${escapeHtml(row.material.quality_feature || "")}</p></article>`).join("")
    : `<article class="stack-item"><strong>暂无炼制材料</strong><p>可通过探索、任务或主人发放获得。</p></article>`;

  const recipes = bundle.recipes || [];
  recipeRoot.innerHTML = "";
  if (!recipes.length) {
    recipeRoot.innerHTML = `<article class="stack-item"><strong>暂无配方</strong></article>`;
    return;
  }
  for (const recipe of recipes) {
    const ingredients = (recipe.ingredients || []).map((item) => `${item.material?.name || "材料"}×${item.quantity}`).join("，");
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(recipe.name)}</strong>
        <span class="badge badge--normal">${escapeHtml(recipe.recipe_kind_label || recipe.recipe_kind)}</span>
      </div>
      <p>产出：${escapeHtml(recipe.result_item?.name || "成品")} × ${escapeHtml(recipe.result_quantity)}</p>
      <p>材料：${escapeHtml(ingredients || "未配置")}</p>
      <p>基础成功率：${escapeHtml(recipe.base_success_rate)}%</p>
      <button type="button" data-recipe-id="${recipe.id}">开始炼制</button>
    `;
    recipeRoot.appendChild(card);
  }
}

function compareRealmRequirement(leftStage, leftLayer, rightStage, rightLayer) {
  const leftIndex = REALM_ORDER.indexOf(leftStage || "");
  const rightIndex = REALM_ORDER.indexOf(rightStage || "");
  if (leftIndex !== rightIndex) return leftIndex - rightIndex;
  return Number(leftLayer || 1) - Number(rightLayer || 1);
}

function cleanSceneCopy(text) {
  return String(text || "")
    .replace(/\s+/g, " ")
    .replace(/[，、]{2,}/g, "，")
    .replace(/[。！？]{2,}/g, "。")
    .trim()
    .replace(/^[，。！？；、,.!?;]+|[，。！？；、,.!?;]+$/g, "");
}

function sceneRiskBadgeClass(level) {
  if (level === "stable" || level === "light") return "badge--normal";
  if (level === "medium") return "badge--pending";
  return "badge--danger";
}

function sceneDisplayMeta(scene, currentStage, currentLayer, currentPower) {
  const state = scene.requirement_state || {};
  const minStage = scene.min_realm_stage || "";
  const minLayer = Number(scene.min_realm_layer || 1);
  const minPower = Number(scene.min_combat_power || 0);
  const currentStageIndex = REALM_ORDER.indexOf(currentStage || "");
  const minStageIndex = REALM_ORDER.indexOf(minStage || "");
  const realmQualified = !minStage || minStageIndex < 0 || currentStageIndex > minStageIndex || (currentStageIndex === minStageIndex && currentLayer >= minLayer);
  const powerQualified = minPower <= 0 || currentPower >= minPower;
  const warnings = [];
  if (Array.isArray(state.risk_reasons) && state.risk_reasons.length) {
    warnings.push(...state.risk_reasons.map((item) => cleanSceneCopy(item)).filter(Boolean));
  } else {
    if (minPower > 0 && !powerQualified) warnings.push("当前战力偏低，翻车概率会明显提高");
    if (minStage && !realmQualified) warnings.push("当前境界不足，翻车概率会明显提高");
  }
  if (state.item_loss_warning) warnings.push(cleanSceneCopy(state.item_loss_warning));
  const riskLevel = String(state.risk_level || (realmQualified && powerQualified ? "stable" : "high"));
  const riskLabel = String(state.risk_label || (realmQualified && powerQualified ? "稳妥" : "高危"));
  const riskPercent = Number(state.risk_percent ?? state.death_chance ?? 0);
  const itemLossRisk = Number(state.item_loss_risk || 0);
  return {
    minStage,
    minLayer,
    minPower,
    realmQualified,
    powerQualified,
    qualified: realmQualified && powerQualified,
    warnings,
    riskLevel,
    riskLabel,
    riskPercent,
    itemLossRisk,
    requirementSummary: cleanSceneCopy(state.requirement_summary),
    safeNote: cleanSceneCopy(state.safe_note),
  };
}

function buildSceneSearchText(scene = {}) {
  return [
    scene.name,
    scene.description,
    (scene.drops || []).map((drop) => drop.reward_name || drop.reward_ref_id_name || drop.reward_kind_label || drop.reward_kind),
    (scene.event_pool || []).map((event) => [event.name, event.description, event.bonus_reward_name, event.bonus_reward_kind_label || event.bonus_reward_kind]),
  ];
}

function renderExploreArea(bundle) {
  const sceneRoot = document.querySelector("#scene-list");
  const activeRoot = document.querySelector("#exploration-active");
  if (!sceneRoot || !activeRoot) return;
  const currentStage = bundle.profile?.realm_stage || "炼气";
  const currentLayer = Number(bundle.profile?.realm_layer || 1);
  const currentPower = Number(bundle.combat_power || 0);
  const sceneQuery = inventorySearchValue("#scene-search");

  const active = bundle.active_exploration;
  activeRoot.innerHTML = "";
  if (active && !active.claimed) {
    const endAt = parseShanghaiDate(active.end_at);
    const canClaim = endAt ? endAt.getTime() <= Date.now() : false;
    activeRoot.innerHTML = `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>探索进行中</strong>
          <span class="badge badge--normal">${escapeHtml(active.reward_kind_label || active.reward_kind || "奖励")}</span>
        </div>
        <p>${escapeHtml(cleanSceneCopy(active.event_text) || "未知遭遇")}</p>
        <p>结束时间：${escapeHtml(formatDate(active.end_at))}</p>
        <button type="button" data-explore-claim="${active.id}" ${canClaim ? "" : "disabled"}>${canClaim ? "领取奖励" : "尚未结束"}</button>
      </article>
    `;
  } else {
    activeRoot.innerHTML = `<article class="stack-item"><strong>当前没有待领取探索</strong></article>`;
  }

  const buildDurationOptions = (maxMinutesRaw) => {
    const maxMinutes = Math.max(Number(maxMinutesRaw) || 1, 1);
    const candidates = maxMinutes <= 10
      ? [maxMinutes]
      : maxMinutes <= 20
        ? [10, maxMinutes]
        : maxMinutes <= 30
          ? [10, 20, maxMinutes]
          : [10, 20, 30, Math.min(45, maxMinutes), maxMinutes];
    return [...new Set(candidates.filter((value) => value > 0 && value <= maxMinutes))]
      .sort((left, right) => left - right)
      .map((value) => `<option value="${value}">${value} 分钟</option>`)
      .join("");
  };

  sceneRoot.innerHTML = "";
  const sourceScenes = bundle.scenes || [];
  const scenes = sourceScenes
    .filter((scene) => textQueryMatches(sceneQuery, buildSceneSearchText(scene)))
    .map((scene) => ({ scene, meta: sceneDisplayMeta(scene, currentStage, currentLayer, currentPower) }))
    .sort((left, right) => {
      if (left.meta.qualified !== right.meta.qualified) return left.meta.qualified ? -1 : 1;
      if (left.meta.powerQualified !== right.meta.powerQualified) return left.meta.powerQualified ? -1 : 1;
      if (left.meta.minPower !== right.meta.minPower) return left.meta.minPower - right.meta.minPower;
      const realmCompare = compareRealmRequirement(left.meta.minStage, left.meta.minLayer, right.meta.minStage, right.meta.minLayer);
      if (realmCompare !== 0) return realmCompare;
      return String(left.scene.name || "").localeCompare(String(right.scene.name || ""), "zh-Hans-CN");
    });
  if (!scenes.length) {
    sceneRoot.innerHTML = sourceScenes.length
      ? `<article class="stack-item"><strong>未找到匹配秘境</strong><p>可按秘境名、掉落、功法或材料关键词继续搜索。</p></article>`
      : `<article class="stack-item"><strong>暂无探索场景</strong></article>`;
    return;
  }
  for (const { scene, meta } of scenes) {
    const explorationCount = Number(scene.user_exploration_count || 0);
    const rewardCards = (scene.drops || []).slice(0, 6).map((drop) => `
      <article class="scene-drop-item">
        <strong>${escapeHtml(drop.reward_name || drop.reward_ref_id_name || drop.reward_kind_label || "未知掉落")}</strong>
        <p>${escapeHtml(cleanSceneCopy(drop.event_text) || `${drop.quantity_min || 1}~${drop.quantity_max || 1} 件掉落`)}</p>
      </article>
    `).join("");
    const warningText = meta.warnings.join(" · ");
    const safeText = meta.safeNote || "当前实力已基本覆盖此处风险，可优先刷取所需材料与功法。";
    const riskText = meta.itemLossRisk > 0
      ? `风险评级 ${meta.riskLabel}（综合 ${meta.riskPercent}% / 掉宝 ${meta.itemLossRisk}%）`
      : `风险评级 ${meta.riskLabel}（综合 ${meta.riskPercent}%）`;
    const card = document.createElement("article");
    card.className = `stack-item scene-card ${meta.qualified ? "is-qualified" : "is-risky"}`;
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(scene.name)}</strong>
        <span class="badge ${sceneRiskBadgeClass(meta.riskLevel)}">${escapeHtml(meta.riskLabel)}</span>
      </div>
      <p>${escapeHtml(cleanSceneCopy(scene.description) || "暂无场景描述")}</p>
      <div class="info-grid">
        <article class="info-chip">
          <span>战力门槛</span>
          <strong>${escapeHtml(meta.minPower > 0 ? `${meta.minPower}（当前 ${currentPower}）` : `无限制（当前 ${currentPower}）`)}</strong>
        </article>
        <article class="info-chip">
          <span>境界门槛</span>
          <strong>${escapeHtml(meta.minStage ? `${meta.minStage}${meta.minLayer}层` : "无限制")}</strong>
        </article>
        <article class="info-chip">
          <span>历练记录</span>
          <strong>已探索 ${escapeHtml(explorationCount)} 次</strong>
        </article>
        <article class="info-chip">
          <span>风险评估</span>
          <strong>${escapeHtml(riskText)}</strong>
        </article>
      </div>
      ${meta.requirementSummary ? `<p class="muted">${escapeHtml(`进入要求：${meta.requirementSummary}`)}</p>` : ""}
      ${warningText ? `<p class="reason-text">${escapeHtml(warningText)}</p>` : `<p>${escapeHtml(safeText)}</p>`}
      <div class="scene-drop-list">${rewardCards || `<article class="scene-drop-item"><strong>掉落待补充</strong><p>当前秘境尚未配置可展示的奖励。</p></article>`}</div>
      <label>探索时长
        <select data-scene-minutes="${scene.id}">
          ${buildDurationOptions(scene.max_minutes)}
        </select>
      </label>
      <button type="button" data-scene-id="${scene.id}">${meta.riskLevel === "high" || meta.riskLevel === "extreme" ? "冒险进入" : "开始探索"}</button>
    `;
    sceneRoot.appendChild(card);
  }
}

function renderLeaderboard(result) {
  state.leaderboard = {
    kind: result.kind,
    page: result.page,
    totalPages: result.total_pages
  };

  document.querySelectorAll(".rank-tab").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.kind === result.kind);
  });

  const list = document.querySelector("#leaderboard-list");
  list.innerHTML = "";
  if (!result.items.length) {
    list.innerHTML = `<article class="stack-item"><strong>暂无排行榜数据</strong><p>等更多道友入道后，这里会热闹起来。</p></article>`;
    return;
  }

  for (const item of result.items) {
    const desc = result.kind === "stone"
      ? `${item.spiritual_stone} 灵石`
      : result.kind === "realm"
        ? `${item.realm_stage}${item.realm_layer}层`
        : (item.artifact_name || "暂无法宝");

    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${item.rank}. ${escapeHtml(item.name)}</strong>
        <span class="badge badge--normal">${escapeHtml(desc)}</span>
      </div>
      <p>TG ${escapeHtml(item.tg)}</p>
    `;
    list.appendChild(card);
  }

  document.querySelector("#rank-page").textContent = `第 ${result.page} 页 / 共 ${result.total_pages} 页`;
  document.querySelector("#rank-prev").disabled = result.page <= 1;
  document.querySelector("#rank-next").disabled = result.page >= result.total_pages;
}

function renderArtifactList(items, retreating, equipLimit, equippedCount) {
  const root = document.querySelector("#artifact-list");
  root.innerHTML = "";
  if (!items.length) {
    root.innerHTML = `<article class="stack-item"><strong>暂无法宝</strong><p>去${escapeHtml(officialShopName())}挑几件趁手的宝贝，再来装配吧。</p></article>`;
    return;
  }

  for (const row of items) {
    const item = row.artifact;
    const effects = item.resolved_effects || {};
    const limitReached = !item.equipped && equippedCount >= equipLimit;
    const disabled = retreating || (!item.equipped && (!item.usable || limitReached));
    let reason = "";
    if (disabled) {
      if (retreating) {
        reason = "闭关期间不能切换法宝。";
      } else if (limitReached) {
        reason = `当前最多只能装备 ${equipLimit} 件法宝。`;
      } else {
        reason = item.unusable_reason || "当前条件不满足，暂时无法装备。";
      }
    }

    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        <span class="badge badge--normal">x${escapeHtml(row.quantity)}</span>
      </div>
      <p>${escapeHtml(item.description || "暂无描述")}</p>
      <div class="item-tags">
        <span class="tag ${item.artifact_type === "support" ? "support" : ""}">${escapeHtml(item.artifact_type_label || artifactTypeLabel(item.artifact_type))}</span>
        <span class="tag">攻击 ${escapeHtml(effects.attack_bonus ?? item.attack_bonus)}</span>
        <span class="tag">防御 ${escapeHtml(effects.defense_bonus ?? item.defense_bonus)}</span>
        <span class="tag">斗法 +${escapeHtml(effects.duel_rate_bonus ?? item.duel_rate_bonus)}%</span>
        <span class="tag">修炼 +${escapeHtml(effects.cultivation_bonus ?? item.cultivation_bonus)}</span>
      </div>
      <p>境界要求：${escapeHtml(item.min_realm_stage ? `${item.min_realm_stage}${item.min_realm_layer}层` : "无限制")}</p>
      ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : ""}
      <button type="button" data-equip-id="${item.id}" ${disabled ? "disabled" : ""}>${escapeHtml(item.action_label || (item.equipped ? "卸下法宝" : "装备法宝"))}</button>
    `;
    root.appendChild(card);
  }
}

function renderPersonalShop(items) {
  const root = document.querySelector("#personal-shop-list");
  root.innerHTML = "";
  if (!items.length) {
    root.innerHTML = `<article class="stack-item"><strong>游仙小铺暂时空空如也</strong><p>从背包里挑一件物品上架后，这里就会热闹起来。</p></article>`;
    return;
  }

  const duelLockReason = currentDuelLockReason();
  for (const item of items) {
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.item_name)}</strong>
        <span class="badge badge--normal">${escapeHtml(item.price_stone)} 灵石</span>
      </div>
      <p>${escapeHtml(item.item_kind_label)} · 库存 ${escapeHtml(item.quantity)} · 游仙小铺</p>
      <div class="inline-action-buttons">
        <button type="button" data-cancel-id="${item.id}" class="ghost" ${duelLockReason ? "disabled" : ""}>取消上架</button>
      </div>
    `;
    root.appendChild(card);
  }
}

function renderSectArea(bundle) {
  const currentRoot = document.querySelector("#sect-current");
  const listRoot = document.querySelector("#sect-list");
  const salaryButton = document.querySelector("#sect-salary-btn");
  const leaveButton = document.querySelector("#sect-leave-btn");
  if (!currentRoot || !listRoot || !salaryButton || !leaveButton) return;

  const current = bundle.current_sect;
  currentRoot.innerHTML = "";
  if (current) {
    const role = current.current_role?.role_name || "门下弟子";
    const contribution = bundle.profile?.sect_contribution ?? 0;
    currentRoot.innerHTML = `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(current.name)}</strong>
          <span class="badge badge--normal">${escapeHtml(role)}</span>
        </div>
        <p>${escapeHtml(current.description || "暂无宗门简介")}</p>
        <div class="item-tags">
          <span class="tag">成员 ${escapeHtml((current.roster || []).length)}</span>
          <span class="tag">贡献 ${escapeHtml(contribution)}</span>
          <span class="tag">月俸 ${escapeHtml(current.current_role?.monthly_salary ?? 0)} 灵石</span>
        </div>
      </article>
    `;
    salaryButton.disabled = false;
    leaveButton.disabled = false;
  } else {
    currentRoot.innerHTML = `<article class="stack-item"><strong>暂未加入宗门</strong><p>满足条件后，就可以在下方挑选心仪宗门了。</p></article>`;
    salaryButton.disabled = true;
    leaveButton.disabled = true;
  }

  listRoot.innerHTML = "";
  const sects = bundle.sects || [];
  if (!sects.length) {
    listRoot.innerHTML = `<article class="stack-item"><strong>暂无可加入宗门</strong></article>`;
    return;
  }

  for (const sect of sects) {
    const disabled = current?.id === sect.id || !sect.joinable;
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(sect.name)}</strong>
        <span class="badge badge--normal">${escapeHtml((sect.roles || []).length)} 个职位</span>
      </div>
      <p>${escapeHtml(sect.description || "暂无简介")}</p>
      <div class="item-tags">
        <span class="tag">境界 ${escapeHtml(sect.min_realm_stage || "无")}${escapeHtml(sect.min_realm_layer || 1)}层</span>
        <span class="tag">灵石 ${escapeHtml(sect.min_stone || 0)}</span>
      </div>
      ${disabled && sect.join_reason ? `<p class="reason-text">${escapeHtml(sect.join_reason)}</p>` : ""}
      <button type="button" data-sect-id="${sect.id}" ${disabled ? "disabled" : ""}>${current?.id === sect.id ? "已加入" : "加入宗门"}</button>
    `;
    listRoot.appendChild(card);
  }
}

function renderRedEnvelopeClaims(claims = []) {
  const root = document.querySelector("#red-envelope-claim-list");
  if (!root) return;
  if (!claims.length) {
    root.innerHTML = `<article class="stack-item"><strong>最近没有新的领取记录</strong><p>发红包或领取红包后，记录会更新在这里。</p></article>`;
    return;
  }
  root.innerHTML = claims.slice(-8).reverse().map((row) => `
    <article class="stack-item">
      <strong>${escapeHtml(row.name || `TG ${row.tg}`)}</strong>
      <p>领取了 ${escapeHtml(row.amount)} 灵石 · ${escapeHtml(formatDate(row.created_at))}</p>
    </article>
  `).join("");
}

function renderJournalArea(bundle) {
  const root = document.querySelector("#journal-list");
  if (!root) return;
  const rows = (bundle.journal || []).filter((row) => row.title !== "主人修改");
  if (!rows.length) {
    root.innerHTML = `<article class="stack-item"><strong>最近 24 小时还没有新记录</strong><p>修炼、交易、任务、红包和宗门往来都会记在这里。</p></article>`;
    return;
  }
  root.innerHTML = rows.map((row) => `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(row.title)}</strong>
        <span class="badge badge--normal">${escapeHtml(formatDate(row.created_at))}</span>
      </div>
      <p>${escapeHtml(row.detail || row.action_type || "暂无详情")}</p>
    </article>
  `).join("");
}

function renderLeaderboard(result) {
  state.leaderboard = {
    kind: result.kind,
    page: result.page,
    totalPages: result.total_pages
  };

  document.querySelectorAll(".rank-tab").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.kind === result.kind);
  });

  const list = document.querySelector("#leaderboard-list");
  list.innerHTML = "";
  if (!result.items.length) {
    list.innerHTML = `<article class="stack-item"><strong>暂无排行榜数据</strong><p>等更多道友踏入仙途后，这里自然会热闹起来。</p></article>`;
    return;
  }

  for (const item of result.items) {
    const desc = result.kind === "stone"
      ? `${item.spiritual_stone} 灵石`
      : result.kind === "realm"
        ? `${item.realm_stage}${item.realm_layer}层`
        : (item.artifact_name || "暂无已装备法宝");

    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${item.rank}. ${escapeHtml(item.name)}</strong>
        <span class="badge badge--normal">${escapeHtml(desc)}</span>
      </div>
    `;
    list.appendChild(card);
  }

  document.querySelector("#rank-page").textContent = `第 ${result.page} 页 / 共 ${result.total_pages} 页`;
  document.querySelector("#rank-prev").disabled = result.page <= 1;
  document.querySelector("#rank-next").disabled = result.page >= result.total_pages;
}

function applyProfileBundle(bundle) {
  if (!bundle) return;
  renderWikiArea();
  renderProfile(bundle);
  renderSectArea(bundle);
  renderTaskArea(bundle);
  renderTechniqueArea(bundle);
  renderCraftArea(bundle);
  renderExploreArea(bundle);
  renderJournalArea(bundle);
  syncGiftPanelState(bundle);
  renderRedEnvelopeClaims(state.lastRedEnvelopeClaims || []);

  state.shopNameEditing = false;
  applyShopNameState(bundle?.profile?.shop_name || "游仙小铺");

  const settings = bundle?.settings || {};
  const rate = settings.rate ?? settings.coin_exchange_rate ?? 100;
  const fee = settings.fee_percent ?? settings.exchange_fee_percent ?? 1;
  const minExchange = settings.min_coin_exchange ?? 1;
  const exchangeEnabled = settings.coin_stone_exchange_enabled ?? true;
  const exchangeHint = document.querySelector("#exchange-hint");
  if (exchangeHint) {
    exchangeHint.textContent = exchangeEnabled
      ? `当前比例：1 片刻碎片 = ${rate} 灵石，手续费 ${fee}%，灵石兑换碎片最低消耗 ${minExchange} 灵石，不足 ${rate} 灵石一份的零头会保留。`
      : "灵石互兑功能当前已关闭，可联系管理员在后台重新开启。";
  }

  ensureSectionState("#journal-card", Boolean(bundle?.profile?.consented));
  ensureSectionState("#technique-card", Boolean(bundle?.profile?.consented));
  ensureSectionState("#auction-card", Boolean(bundle?.profile?.consented));
  ensureSectionState("#gift-card", Boolean(bundle?.profile?.consented));
}

function mergeBundleData(baseBundle, patchBundle) {
  const merged = { ...(baseBundle || {}) };
  for (const [key, value] of Object.entries(patchBundle || {})) {
    if (value && typeof value === "object" && !Array.isArray(value) && merged[key] && typeof merged[key] === "object" && !Array.isArray(merged[key])) {
      merged[key] = { ...merged[key], ...value };
      continue;
    }
    merged[key] = value;
  }
  return merged;
}

async function loadDeferredBundle({ silent = false } = {}) {
  if (state.deferredBundleLoaded || state.deferredBundleLoading) return state.profileBundle;
  state.deferredBundleLoading = true;
  try {
    const deferred = await postJson("/plugins/xiuxian/api/bootstrap/deferred");
    state.profileBundle = mergeBundleData(state.profileBundle, deferred);
    state.deferredBundleLoaded = true;
    applyProfileBundle(state.profileBundle);
    return state.profileBundle;
  } catch (error) {
    if (!silent) throw error;
    return state.profileBundle;
  } finally {
    state.deferredBundleLoading = false;
  }
}

function scheduleDeferredBootstrapWork() {
  const runner = () => {
    loadDeferredBundle({ silent: true }).catch(() => null);
    if (!state.wikiBundle) {
      refreshWikiBundle().catch(() => null);
    }
  };
  if (typeof window.requestIdleCallback === "function") {
    window.requestIdleCallback(runner, { timeout: 800 });
    return;
  }
  window.setTimeout(runner, 120);
}

async function refreshBundle() {
  state.deferredBundleLoaded = false;
  const payload = await postJson("/plugins/xiuxian/api/bootstrap");
  renderBottomNav(payload.bottom_nav || []);
  applyProfileBundle(payload.profile_bundle);
  scheduleDeferredBootstrapWork();
  return state.profileBundle;
}

async function refreshLeaderboard(kind = state.leaderboard.kind, page = state.leaderboard.page) {
  const result = await postJson("/plugins/xiuxian/api/leaderboard", { kind, page });
  renderLeaderboard(result);
}

async function bootstrap() {
  if (!tg) {
    setStatus("这个页面需要从 Telegram Mini App 中打开。", "error");
    return;
  }

  tg.ready();
  tg.expand();
  tg.setHeaderColor("#eef4ff");
  tg.setBackgroundColor("#eef4ff");

  renderWikiArea();
  state.deferredBundleLoaded = false;
  const payload = await postJson("/plugins/xiuxian/api/bootstrap");
  renderBottomNav(payload.bottom_nav || []);
  applyProfileBundle(payload.profile_bundle);
  scheduleDeferredBootstrapWork();
  if (payload.initial_leaderboard) {
    renderLeaderboard(payload.initial_leaderboard);
    return;
  }
  await refreshLeaderboard("stone", 1);
}

document.querySelector("#enter-path").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    const payload = await runButtonAction(button, "入道中…", () => postJson("/plugins/xiuxian/api/enter"));
    setStatus(`仙途已开，你的灵根是：${profileRootText(payload.profile)}`, "success");
    await popup("踏入仙途", `灵根抽取完成：${profileRootText(payload.profile)}`);
    await refreshBundle();
    await refreshLeaderboard("realm", 1);
  } catch (error) {
    const message = normalizeError(error, "踏入仙途失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#train-btn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    const payload = await runButtonAction(button, "吐纳中…", () => postJson("/plugins/xiuxian/api/train"));
    const growthText = attributeGrowthText(payload.attribute_growth || []);
    const efficiencyText = Number(payload.cultivation_efficiency_percent || 100) < 100
      ? `\n避世修为效率：${payload.cultivation_efficiency_percent}%（原始 ${payload.gain_raw || payload.gain}）`
      : "";
    setStatus(`本次修炼获得修为 ${payload.gain}、灵石 ${payload.stone_gain}${growthText ? `，${growthText}` : ""}。`, "success");
    await popup("吐纳成功", `修为 +${payload.gain}\n灵石 +${payload.stone_gain}${growthText ? `\n${growthText}` : ""}${efficiencyText}`);
    await refreshBundle();
    await refreshLeaderboard(state.leaderboard.kind, state.leaderboard.page);
  } catch (error) {
    const message = normalizeError(error, "吐纳修炼失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#break-btn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    const payload = await runButtonAction(button, "突破中…", () => postJson("/plugins/xiuxian/api/breakthrough", { use_pill: false }));
    const tone = payload.success ? "success" : "warning";
    const message = `点数 ${payload.roll} / 成功率 ${payload.success_rate}%`;
    setStatus(`突破判定完成：${message}`, tone);
    await popup(payload.success ? "突破成功" : "突破失败", message, tone);
    await refreshBundle();
    await refreshLeaderboard("realm", 1);
  } catch (error) {
    const message = normalizeError(error, "突破失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#break-pill-btn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    const payload = await runButtonAction(button, "服丹突破中…", () => postJson("/plugins/xiuxian/api/breakthrough", { use_pill: true }));
    const tone = payload.success ? "success" : "warning";
    const detail = `点数 ${payload.roll} / 成功率 ${payload.success_rate}%`;
    setStatus(`服用破境丹后已完成突破判定：${detail}`, tone);
    await popup(payload.success ? "突破成功" : "突破失败", detail, tone);
    await refreshBundle();
    await refreshLeaderboard("realm", 1);
  } catch (error) {
    const message = normalizeError(error, "服用破境丹突破失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#retreat-start-btn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    const payload = await runButtonAction(button, "闭关中…", () => postJson("/plugins/xiuxian/api/retreat/start", {
      hours: Number(document.querySelector("#retreat-hours").value || 1)
    }));
    const efficiencyText = Number(payload.cultivation_efficiency_percent || 100) < 100
      ? ` 当前避世效率 ${payload.cultivation_efficiency_percent}%（原始 ${payload.estimated_gain_raw || payload.estimated_gain}）。`
      : "";
    const message = `预计获得 ${payload.estimated_gain} 修为，预计消耗 ${payload.estimated_cost} 灵石。${efficiencyText}`;
    setStatus(`闭关已开始：${message}`, "success");
    await popup("闭关开始", message);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "开始闭关失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#retreat-finish-btn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    const payload = await runButtonAction(button, "出关中…", () => postJson("/plugins/xiuxian/api/retreat/finish"));
    const settled = payload.settled || { gain: 0, cost: 0 };
    const efficiencyText = Number(settled.cultivation_efficiency_percent || 100) < 100
      ? ` 避世效率 ${settled.cultivation_efficiency_percent}%（原始 ${settled.gain_raw || settled.gain}）。`
      : "";
    const baseMessage = `本次闭关获得修为 ${settled.gain}，消耗灵石 ${settled.cost}。${efficiencyText}`;
    const message = settled.insufficient_stone
      ? `${baseMessage}由于中途灵石不足，剩余闭关进度未继续结算。`
      : baseMessage;
    setStatus(message, settled.insufficient_stone ? "warning" : "success");
    await popup("闭关结算完成", message, settled.insufficient_stone ? "warning" : "success");
    await refreshBundle();
    await refreshLeaderboard("realm", 1);
  } catch (error) {
    const message = normalizeError(error, "出关结算失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#social-mode-btn")?.addEventListener("click", async (event) => {
  const button = event.currentTarget;
  const nextMode = currentSocialMode() === "secluded" ? "worldly" : "secluded";
  const nextLabel = nextMode === "secluded" ? "避世" : "入世";
  try {
    const payload = await runButtonAction(button, "切换中…", () => postJson("/plugins/xiuxian/api/social-mode", { social_mode: nextMode }));
    applyProfileBundle(payload.bundle);
    setStatus(`当前状态已切换为${nextLabel}。`, "success");
    await popup("状态已切换", `当前已切换为${nextLabel}。`, "success");
  } catch (error) {
    const message = normalizeError(error, "切换状态失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#coin-to-stone-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button[type='submit']");
  try {
    const payload = await runButtonAction(button, "兑换中…", () => postJson("/plugins/xiuxian/api/exchange", {
      direction: "coin_to_stone",
      amount: Number(document.querySelector("#coin-to-stone-amount").value || 0)
    }));
    const message = `消耗 ${payload.spent_coin} 片刻碎片，获得 ${payload.received_stone} 灵石。`;
    setStatus(`兑换成功：${message}`, "success");
    await popup("兑换成功", message);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "兑换灵石失败。");
    setStatus(message, "error");
    await popup("兑换失败", message, "error");
  }
});

document.querySelector("#stone-to-coin-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button[type='submit']");
  try {
    const payload = await runButtonAction(button, "兑换中…", () => postJson("/plugins/xiuxian/api/exchange", {
      direction: "stone_to_coin",
      amount: Number(document.querySelector("#stone-to-coin-amount").value || 0)
    }));
    const message = `消耗 ${payload.spent_stone} 灵石，获得 ${payload.received_coin} 片刻碎片。`;
    setStatus(`兑换成功：${message}`, "success");
    await popup("兑换成功", message);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "兑换碎片失败。");
    setStatus(message, "error");
    await popup("兑换失败", message, "error");
  }
});

document.querySelector("#gambling-exchange-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button[type='submit']");
  try {
    const payload = await runButtonAction(button, "兑换中…", () => postJson("/plugins/xiuxian/api/gambling/exchange", {
      count: Number(document.querySelector("#gambling-exchange-count")?.value || 0),
    }));
    if (payload.bundle) applyProfileBundle(payload.bundle);
    const result = payload.result || {};
    const message = `消耗 ${Number(result.total_cost_stone || 0)} 灵石，兑换 ${Number(result.exchange_count || 0)} 枚仙界奇石，当前持有 ${Number(result.immortal_stone_quantity || 0)} 枚。`;
    setStatus(message, "success");
    await popup("兑换成功", message);
  } catch (error) {
    const message = normalizeError(error, "兑换仙界奇石失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#gambling-open-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button[type='submit']");
  try {
    const payload = await runButtonAction(button, "开启中…", () => postJson("/plugins/xiuxian/api/gambling/open", {
      count: Number(document.querySelector("#gambling-open-count")?.value || 0),
    }));
    if (payload.bundle) applyProfileBundle(payload.bundle);
    const result = payload.result || {};
    const rareRows = (result.summary || []).filter((item) => item.broadcasted);
    const lines = [
      `开启数量：${Number(result.opened_count || 0)} 枚`,
      `获得：${result.summary_text || "未知奖励"}`,
      `剩余奇石：${Number(result.remaining_immortal_stone || 0)} 枚`,
    ];
    if (result.fortune_hint) {
      lines.push(result.fortune_hint);
    }
    if (rareRows.length) {
      lines.push(`已触发群播：${rareRows.map((item) => `${item.quality_label || "高品"} ${item.item_name || "未知物品"} x${Number(item.quantity || 0)}`).join("、")}`);
    }
    setStatus(`奇石开启完成：${result.summary_text || "奖励已发放。"}。`, "success");
    await popup("奇石开启完成", lines.join("\n"));
  } catch (error) {
    const message = normalizeError(error, "开启仙界奇石失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#shop-item-kind").addEventListener("change", renderInventorySelect);
document.querySelector("#auction-item-kind")?.addEventListener("change", renderAuctionInventorySelect);
document.querySelector("#official-recycle-kind")?.addEventListener("change", () => {
  populateOfficialRecycleInventorySelect();
  updateOfficialRecycleQuotePreview();
});
document.querySelector("#official-recycle-item-ref")?.addEventListener("change", () => updateOfficialRecycleQuotePreview());
document.querySelector("#official-recycle-quantity")?.addEventListener("input", () => updateOfficialRecycleQuotePreview());

document.querySelector("#shop-name-toggle")?.addEventListener("click", () => {
  state.shopNameEditing = !state.shopNameEditing;
  applyShopNameState(document.querySelector("#shop-name")?.value?.trim() || state.profileBundle?.profile?.shop_name || "游仙小铺");
  if (state.shopNameEditing) {
    document.querySelector("#shop-name")?.focus();
    document.querySelector("#shop-name")?.select();
  }
});

document.querySelector("#personal-shop-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button[type='submit']");
  try {
    const payload = await runButtonAction(button, "上架中…", () => postJson("/plugins/xiuxian/api/shop/personal", {
      shop_name: document.querySelector("#shop-name").value.trim(),
      item_kind: document.querySelector("#shop-item-kind").value,
      item_ref_id: Number(document.querySelector("#shop-item-ref").value || 0),
      quantity: Number(document.querySelector("#shop-quantity").value || 1),
      price_stone: Number(document.querySelector("#shop-price").value || 0),
      broadcast: document.querySelector("#shop-broadcast").checked
    }));
    const discountText = payload.broadcast_discount ? `，魅力减免 ${payload.broadcast_discount} 灵石播报费` : "";
    const message = `已上架 ${payload.listing.item_name}，售价 ${payload.listing.price_stone} 灵石${discountText}。`;
    setStatus(message, "success");
    await popup("上架成功", message);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "上架个人店铺失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#official-recycle-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button[type='submit']");
  try {
    const payload = await runButtonAction(button, "回收中…", () => postJson("/plugins/xiuxian/api/recycle/official", {
      item_kind: document.querySelector("#official-recycle-kind")?.value || "artifact",
      item_ref_id: Number(document.querySelector("#official-recycle-item-ref")?.value || 0),
      quantity: Number(document.querySelector("#official-recycle-quantity")?.value || 1),
    }));
    const result = payload?.result || {};
    const message = `已回收 ${result.item_name || "物品"} x${Number(result.quantity || 0)}，到账 ${Number(result.total_price_stone || 0)} 灵石。`;
    if (payload?.bundle) {
      applyProfileBundle(payload.bundle);
    } else {
      await refreshBundle();
    }
    setStatus(message, "success");
    await popup("回收成功", message);
  } catch (error) {
    const message = normalizeError(error, "提交官网回收失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#personal-auction-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button[type='submit']");
  try {
    const payload = await runButtonAction(button, "发起中…", () => postJson("/plugins/xiuxian/api/auction/personal", {
      item_kind: document.querySelector("#auction-item-kind").value,
      item_ref_id: Number(document.querySelector("#auction-item-ref").value || 0),
      quantity: Number(document.querySelector("#auction-quantity").value || 1),
      opening_price_stone: Number(document.querySelector("#auction-opening-price").value || 0),
      bid_increment_stone: Number(document.querySelector("#auction-bid-increment").value || 1),
      buyout_price_stone: Number(document.querySelector("#auction-buyout-price").value || 0) || null,
    }));
    const itemName = payload.auction?.item_name || "拍品";
    const buyoutPrice = Number(payload.auction?.buyout_price_stone || 0);
    const pushWarning = String(payload.push_warning || "").trim();
    const message = `${itemName} 已发起群拍，起拍价 ${payload.auction?.opening_price_stone || 0} 灵石，单次加价 ${payload.auction?.bid_increment_stone || 1} 灵石${buyoutPrice > 0 ? `，一口价 ${buyoutPrice} 灵石` : ""}。${pushWarning || "群消息已推送并置顶。"}`
      .trim();
    if (payload.bundle) {
      applyProfileBundle(payload.bundle);
    } else {
      await refreshBundle();
    }
    setStatus(message, pushWarning ? "warning" : "success");
    await popup(pushWarning ? "拍卖已创建，但置顶失败" : "拍卖已发起", message, pushWarning ? "warning" : "success");
  } catch (error) {
    const message = normalizeError(error, "发起拍卖失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#personal-shop-list")?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-cancel-id]");
  if (!button || button.disabled) return;
  try {
    const payload = await runButtonAction(button, "取消中…", () => postJson("/plugins/xiuxian/api/shop/cancel", {
      item_id: Number(button.dataset.cancelId)
    }));
    const message = payload?.result?.item_name
      ? `已取消 ${payload.result.item_name} 的上架。`
      : "已取消该商品的上架。";
    setStatus(message, "success");
    await popup("取消成功", message);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "取消上架失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#artifact-list").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-equip-id], [data-artifact-bind-id], [data-artifact-unbind-id]");
  if (!button || button.disabled) return;
  try {
    let payload;
    let message = "";
    if (button.dataset.artifactBindId) {
      payload = await runButtonAction(button, "绑定中…", () => postJson("/plugins/xiuxian/api/artifact/bind", {
        artifact_id: Number(button.dataset.artifactBindId)
      }));
      message = `已绑定 ${payload.artifact.name} 1 件。`;
    } else if (button.dataset.artifactUnbindId) {
      payload = await runButtonAction(button, "解绑中…", () => postJson("/plugins/xiuxian/api/artifact/unbind", {
        artifact_id: Number(button.dataset.artifactUnbindId)
      }));
      message = `已解绑 ${payload.artifact.name} 1 件${payload.cost ? `，消耗 ${payload.cost} 灵石` : ""}。`;
    } else {
      payload = await runButtonAction(button, "处理中…", () => postJson("/plugins/xiuxian/api/artifact/equip", {
        artifact_id: Number(button.dataset.equipId)
      }));
      const actionText = payload.action === "unequipped" ? "已卸下法宝" : "已装备法宝";
      message = `${actionText}：${payload.artifact_name}`;
      await refreshLeaderboard(state.leaderboard.kind, state.leaderboard.page);
    }
    setStatus(message, "success");
    await popup("操作成功", message);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "法宝操作失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#pill-list").addEventListener("click", async (event) => {
  const singleButton = event.target.closest("[data-pill-id]");
  const batchButton = event.target.closest("[data-pill-batch-id]");
  const button = batchButton || singleButton;
  if (!button || button.disabled) return;
  try {
    const pillId = Number(batchButton ? button.dataset.pillBatchId : button.dataset.pillId);
    let quantity = 1;
    if (batchButton) {
      const quantityInput = button.closest(".stack-item")?.querySelector(`[data-pill-quantity-for="${pillId}"]`);
      quantity = Math.max(Number(quantityInput?.value || 1), 1);
    }
    const payload = await runButtonAction(button, batchButton ? "批量服用中…" : "服用中…", () => postJson("/plugins/xiuxian/api/pill/use", {
      pill_id: pillId,
      quantity
    }));
    const usedQuantity = Math.max(Number(payload.used_quantity || quantity || 1), 1);
    const statusMessage = usedQuantity > 1
      ? `已批量服用 ${payload.pill.name} x${usedQuantity}。`
      : `已服用 ${payload.pill.name}。`;
    const message = payload.summary ? `${statusMessage}\n${payload.summary}` : statusMessage;
    setStatus(statusMessage, "success");
    await popup(usedQuantity > 1 ? "批量服用成功" : "服用成功", message);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "服用丹药失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#talisman-list").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-talisman-id], [data-talisman-bind-id], [data-talisman-unbind-id]");
  if (!button || button.disabled) return;
  try {
    let payload;
    let message = "";
    let title = "操作成功";
    if (button.dataset.talismanBindId) {
      payload = await runButtonAction(button, "绑定中…", () => postJson("/plugins/xiuxian/api/talisman/bind", {
        talisman_id: Number(button.dataset.talismanBindId)
      }));
      message = `已绑定 ${payload.talisman.name} 1 张。`;
    } else if (button.dataset.talismanUnbindId) {
      payload = await runButtonAction(button, "解绑中…", () => postJson("/plugins/xiuxian/api/talisman/unbind", {
        talisman_id: Number(button.dataset.talismanUnbindId)
      }));
      message = `已解绑 ${payload.talisman.name} 1 张${payload.cost ? `，消耗 ${payload.cost} 灵石` : ""}。`;
    } else {
      payload = await runButtonAction(button, "激活中…", () => postJson("/plugins/xiuxian/api/talisman/activate", {
        talisman_id: Number(button.dataset.talismanId)
      }));
      message = `已激活 ${payload.talisman.name}，将于下一场斗法生效。`;
      title = "激活成功";
    }
    setStatus(message, "success");
    await popup(title, message);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "激活符箓失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

async function purchaseItem(button) {
  try {
    const payload = await runButtonAction(button, "购买中…", () => postJson("/plugins/xiuxian/api/shop/purchase", {
      item_id: Number(button.dataset.buyId),
      quantity: 1
    }));
    const itemName = payload.item?.item_name || "商品";
    const discountText = payload.discount_amount ? `，魅力减免 ${payload.discount_amount} 灵石` : "";
    const message = `购买 ${itemName} 成功，共消耗 ${payload.total_cost} 灵石${discountText}。`;
    setStatus(message, "success");
    await popup("购买成功", message);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "购买商品失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
}

document.querySelector("#official-shop-list").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-buy-id]");
  if (!button || button.disabled) return;
  await purchaseItem(button);
});

document.querySelector("#community-shop-list").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-buy-id]");
  if (!button || button.disabled) return;
  await purchaseItem(button);
});

document.querySelector("#sect-list")?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-sect-id]");
  if (!button || button.disabled) return;
  try {
    const payload = await runButtonAction(button, "加入中…", () => postJson("/plugins/xiuxian/api/sect/join", {
      sect_id: Number(button.dataset.sectId)
    }));
    setStatus("宗门加入成功。", "success");
    await popup("加入成功", "宗门关系已建立。");
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "加入宗门失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#sect-salary-btn")?.addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    const payload = await runButtonAction(button, "领取中…", () => postJson("/plugins/xiuxian/api/sect/salary"));
    setStatus(`已领取宗门俸禄 ${payload.salary} 灵石。`, "success");
    await popup("领取成功", `已领取宗门俸禄 ${payload.salary} 灵石。`);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "领取俸禄失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#sect-leave-btn")?.addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    const payload = await runButtonAction(button, "叛出中…", () => postJson("/plugins/xiuxian/api/sect/leave"));
    const sectName = payload?.sect?.previous_sect?.name || "当前宗门";
    const betrayal = payload?.sect?.betrayal || {};
    const penalty = Number(betrayal.stone_penalty || 0);
    const contribution = Number(betrayal.contribution_cleared || 0);
    const cooldownUntil = betrayal.cooldown_until ? formatDate(betrayal.cooldown_until) : "";
    if (payload?.bundle) {
      applyProfileBundle(payload.bundle);
    } else {
      await refreshBundle();
    }
    const lines = [`你已经叛出 ${sectName}。`];
    if (penalty > 0) lines.push(`宗门收回供奉灵石 ${penalty}。`);
    if (contribution > 0) lines.push(`宗门贡献清零 ${contribution}。`);
    if (cooldownUntil) lines.push(`叛宗余罚将持续到 ${cooldownUntil}。`);
    const message = lines.join("\n");
    setStatus(message, "success");
    await popup("叛出成功", message);
  } catch (error) {
    const message = normalizeError(error, "叛出宗门失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#task-image-upload")?.addEventListener("click", async (event) => {
  const button = event.currentTarget;
  const fileInput = document.querySelector("#task-image-file");
  const targetInput = document.querySelector("#task-image");
  const file = fileInput?.files?.[0];
  try {
    const payload = await runButtonAction(button, "上传中…", () =>
      uploadImage("/plugins/xiuxian/api/upload-image", file, "tasks")
    );
    targetInput.value = payload.url;
    if (fileInput) {
      fileInput.value = "";
    }
    setStatus("题图上传成功，已自动回填地址。", "success");
    await popup("上传成功", "题图已上传并写入当前任务表单。");
  } catch (error) {
    const message = normalizeError(error, "题图上传失败。");
    setStatus(message, "error");
    await popup("上传失败", message, "error");
  }
});

document.querySelector("#red-image-upload")?.addEventListener("click", async (event) => {
  const button = event.currentTarget;
  const fileInput = document.querySelector("#red-image-file");
  const targetInput = document.querySelector("#red-image");
  const file = fileInput?.files?.[0];
  try {
    const payload = await runButtonAction(button, "上传中…", () =>
      uploadImage("/plugins/xiuxian/api/upload-image", file, "red-envelopes")
    );
    targetInput.value = payload.url;
    if (fileInput) {
      fileInput.value = "";
    }
    setStatus("红包封面上传成功，已自动回填地址。", "success");
    await popup("上传成功", "红包封面图已上传并写入当前表单。");
  } catch (error) {
    const message = normalizeError(error, "红包封面上传失败。");
    setStatus(message, "error");
    await popup("上传失败", message, "error");
  }
});

document.querySelector("#task-form-legacy")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form?.querySelector("button[type='submit']");
  try {
    const payload = await runButtonAction(button, "发布中…", () => postJson("/plugins/xiuxian/api/task/create", {
      title: document.querySelector("#task-title").value.trim(),
      description: document.querySelector("#task-description").value.trim(),
      task_scope: document.querySelector("#task-scope").value,
      task_type: document.querySelector("#task-type").value,
      question_text: document.querySelector("#task-question").value.trim(),
      answer_text: document.querySelector("#task-answer").value.trim(),
      image_url: document.querySelector("#task-image").value.trim(),
      reward_stone: Number(document.querySelector("#task-reward-stone").value || 0),
      max_claimants: Number(document.querySelector("#task-max-claimants").value || 1),
      active_in_group: document.querySelector("#task-push-group").checked
    }));
    setStatus("悬赏任务已发布。", "success");
    await popup("发布成功", `任务【${payload.task.title}】已发布。`);
    form?.reset?.();
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "发布任务失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#task-list")?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-task-id][data-task-action]");
  if (!button || button.disabled) return;
  const action = button.dataset.taskAction || "claim";
  try {
    if (action === "cancel") {
      const payload = await runButtonAction(button, "撤销中…", () => postJson("/plugins/xiuxian/api/task/cancel", {
        task_id: Number(button.dataset.taskId)
      }));
      const taskTitle = payload.result?.task?.title || "该任务";
      const message = `任务《${taskTitle}》已撤销。`;
      setStatus(message, "success");
      await popup("撤销成功", message);
    } else {
      const payload = await runButtonAction(button, "领取中…", () => postJson("/plugins/xiuxian/api/task/claim", {
        task_id: Number(button.dataset.taskId)
      }));
      const submitted = payload.result?.submitted_item;
      if (submitted?.item) {
        const itemName = submitted.item.name || "任务物品";
        const quantity = submitted.quantity || 0;
        const rewardText = taskRewardText(payload.result?.task || {});
        const message = `已提交 ${itemName} × ${quantity}，任务已直接完成。奖励：${rewardText}`;
        setStatus(message, "success");
        await popup("提交完成", message);
      } else {
        const message = "任务已接取，请按要求完成后再领取奖励。";
        setStatus(message, "success");
        await popup("接取成功", message);
      }
    }
    await refreshBundle();
  } catch (error) {
    const fallback = action === "cancel" ? "撤销任务失败。" : "领取任务失败。";
    const message = normalizeError(error, fallback);
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#technique-list")?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-technique-id]");
  if (!button || button.disabled) return;
  try {
    const payload = await runButtonAction(button, "切换中…", () => postJson("/plugins/xiuxian/api/technique/activate", {
      technique_id: Number(button.dataset.techniqueId)
    }));
    const techniqueName = payload.technique?.name || "功法";
    const message = `已切换为 ${techniqueName}。`;
    setStatus(message, "success");
    await popup("切换成功", message);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "切换功法失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#recipe-list")?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-recipe-id]");
  if (!button || button.disabled) return;
  try {
    const payload = await runButtonAction(button, "炼制中…", () => postJson("/plugins/xiuxian/api/recipe/craft", {
      recipe_id: Number(button.dataset.recipeId)
    }));
    const result = payload.result;
    const tone = result.success ? "success" : "warning";
    const message = result.success ? "炼制成功，成品已发放。" : "炼制失败，材料已消耗。";
    setStatus(message, tone);
    const detailRows = [`${message}`, `成功率 ${result.success_rate}%`];
    if (result.result_item?.name) detailRows.push(`目标成品：${result.result_item.name}`);
    if (result.reward) detailRows.push(`获得：${grantedItemName(result.reward) || "成品已入库"}`);
    await popup(result.success ? "炼制成功" : "炼制失败", detailRows.join("\n"), tone);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "炼制失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#recipe-fragment-synthesis-list")?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-recipe-synthesis-id]");
  if (!button || button.disabled) return;
  try {
    const payload = await runButtonAction(button, "参悟中…", () => postJson("/plugins/xiuxian/api/recipe/synthesize", {
      recipe_id: Number(button.dataset.recipeSynthesisId)
    }));
    const result = payload.result || {};
    const recipeName = result.recipe?.name || "配方";
    const materialName = result.fragment_material?.name || "残页";
    const requiredQuantity = Number(result.required_quantity || 1);
    const itemName = result.result_item?.name || result.recipe?.result_item?.name || "成品";
    const message = `已消耗 ${materialName} × ${requiredQuantity}，成功参悟 ${recipeName}。`;
    setStatus(message, "success");
    await popup("参悟成功", [message, `对应成品：${itemName}`].join("\n"));
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "参悟配方失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#scene-list")?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-scene-id]");
  if (!button || button.disabled) return;
  const sceneId = Number(button.dataset.sceneId);
  const minutes = Number(document.querySelector(`[data-scene-minutes='${sceneId}']`)?.value || 10);
  try {
    const payload = await runButtonAction(button, "派遣中…", () => postJson("/plugins/xiuxian/api/explore/start", {
      scene_id: sceneId,
      minutes
    }));
    setStatus("探索已开始。", "success");
    await popup("探索开始", `已派出角色探索，预计 ${minutes} 分钟后可领取。`);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "开始探索失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#exploration-active")?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-explore-claim]");
  if (!button || button.disabled) return;
  try {
    const payload = await runButtonAction(button, "领取中…", () => postJson("/plugins/xiuxian/api/explore/claim", {
      exploration_id: Number(button.dataset.exploreClaim)
    }));
    const result = payload.result || {};
    const death = result.death || {};
    setStatus(death.died ? "探索已结算，秘境中遭逢重创。" : "探索奖励已领取。", death.died ? "warning" : "success");
    const lines = [];
    if (result.exploration?.event_text) lines.push(result.exploration.event_text);
    if (result.exploration?.outcome_payload?.risk_note) lines.push(result.exploration.outcome_payload.risk_note);
    if (death.died) {
      if (Array.isArray(death.reasons) && death.reasons.length) lines.push(`阵亡原因：${death.reasons.join("；")}`);
      if (typeof death.stone_loss === "number") lines.push(`灵石损失 -${death.stone_loss}`);
      if (typeof death.cultivation_loss === "number") lines.push(`修为损失 -${death.cultivation_loss}`);
      if (Array.isArray(death.artifact_losses) && death.artifact_losses.length) {
        lines.push(`遗失装备：${death.artifact_losses.map((item) => item.artifact?.name || "未命名法宝").join("、")}`);
      }
    } else {
      if (typeof result.stone_delta === "number") lines.push(`灵石变化 ${result.stone_delta >= 0 ? "+" : ""}${result.stone_delta}`);
      if (result.reward_item) lines.push(`基础掉落：${grantedItemName(result.reward_item) || "已发放"}`);
      if (result.bonus_reward) lines.push(`奇遇额外：${grantedItemName(result.bonus_reward) || "已发放"}`);
      const growthText = attributeGrowthText(result.attribute_growth || []);
      if (growthText) lines.push(growthText);
    }
    await popup(death.died ? "探索失败" : "领取成功", lines.join("\n") || "探索奖励已发放到你的背包与档案。", death.died ? "warning" : "success");
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "领取探索奖励失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#red-envelope-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form?.querySelector("button[type='submit']");
  try {
    const payload = await runButtonAction(button, "发送中…", () => postJson("/plugins/xiuxian/api/red-envelope/create", {
      cover_text: document.querySelector("#red-cover").value.trim(),
      image_url: document.querySelector("#red-image").value.trim(),
      mode: document.querySelector("#red-mode").value,
      amount_total: Number(document.querySelector("#red-amount").value || 0),
      count_total: Number(document.querySelector("#red-count").value || 1),
      target_tg: document.querySelector("#red-target").value ? Number(document.querySelector("#red-target").value) : null
    }));
    setStatus("灵石红包已发往群内。", "success");
    await popup("发送成功", `红包【${payload.result.envelope.cover_text}】已发出。`);
    form?.reset?.();
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "发送红包失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#gift-target-search-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = document.querySelector("#gift-player-search");
  const query = document.querySelector("#gift-player-query")?.value || "";
  try {
    await runButtonAction(button, "搜索中…", () => searchGiftPlayers(query));
    if (!state.giftSearchResults.length) {
      setStatus("没有找到匹配的道友。", "warning");
    }
  } catch (error) {
    const message = normalizeError(error, "搜索道友失败。");
    setStatus(message, "error");
    await popup("搜索失败", message, "error");
  }
});

document.querySelector("#gift-player-query")?.addEventListener("input", (event) => {
  const keyword = event.currentTarget?.value || "";
  if (state.giftSearchTimer) window.clearTimeout(state.giftSearchTimer);
  if (!String(keyword).trim()) {
    state.giftSearchQuery = "";
    state.giftSearchResults = [];
    renderGiftSearchResults([]);
    return;
  }
  state.giftSearchTimer = window.setTimeout(() => {
    searchGiftPlayers(keyword).catch((error) => {
      const message = normalizeError(error, "搜索道友失败。");
      setStatus(message, "error");
    });
  }, 240);
});

document.querySelector("#gift-player-search-results")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-gift-target-tg]");
  if (!button) return;
  setGiftTarget({
    tg: Number(button.dataset.giftTargetTg || 0),
    display_label: button.dataset.giftTargetLabel || "",
    username: button.dataset.giftTargetUsername || "",
  });
  state.giftSearchQuery = "";
  state.giftSearchResults = [];
  const queryInput = document.querySelector("#gift-player-query");
  if (queryInput) queryInput.value = "";
  renderGiftSearchResults([]);
  setStatus(`已选中 ${button.dataset.giftTargetLabel || `TG ${button.dataset.giftTargetTg || ""}`}。`, "success");
});

document.querySelector("#gift-target-selected")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-clear-gift-target]");
  if (!button) return;
  setGiftTarget(null);
  setStatus("已清除赠送目标。", "warning");
});

document.querySelector("#gender-set-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form?.querySelector("button[type='submit']");
  const gender = document.querySelector("#gender-select")?.value || "male";
  try {
    const payload = await runButtonAction(button, "设置中…", () => postJson("/plugins/xiuxian/api/gender/set", {
      gender,
    }));
    if (payload.bundle) applyProfileBundle(payload.bundle);
    const result = payload.result || {};
    setStatus(result.message || "性别设置已更新。", "success");
    await popup("设置成功", result.message || "性别设置已更新。");
  } catch (error) {
    const message = normalizeError(error, "设置性别失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#marriage-search-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = document.querySelector("#marriage-player-search");
  const query = document.querySelector("#marriage-player-query")?.value || "";
  try {
    await runButtonAction(button, "搜索中…", () => searchMarriagePlayers(query));
    if (!state.marriageSearchResults.length) {
      setStatus("没有找到匹配的道友。", "warning");
    }
  } catch (error) {
    const message = normalizeError(error, "搜索道友失败。");
    setStatus(message, "error");
    await popup("搜索失败", message, "error");
  }
});

document.querySelector("#marriage-player-query")?.addEventListener("input", (event) => {
  const keyword = event.currentTarget?.value || "";
  if (state.marriageSearchTimer) window.clearTimeout(state.marriageSearchTimer);
  if (!String(keyword).trim()) {
    state.marriageSearchQuery = "";
    state.marriageSearchResults = [];
    renderMarriageSearchResults([]);
    return;
  }
  state.marriageSearchTimer = window.setTimeout(() => {
    searchMarriagePlayers(keyword).catch((error) => {
      const message = normalizeError(error, "搜索道友失败。");
      setStatus(message, "error");
    });
  }, 240);
});

document.querySelector("#marriage-player-search-results")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-marriage-target-tg]");
  if (!button) return;
  setMarriageTarget({
    tg: Number(button.dataset.marriageTargetTg || 0),
    display_label: button.dataset.marriageTargetLabel || "",
    username: button.dataset.marriageTargetUsername || "",
  });
  state.marriageSearchQuery = "";
  state.marriageSearchResults = [];
  const queryInput = document.querySelector("#marriage-player-query");
  if (queryInput) queryInput.value = "";
  renderMarriageSearchResults([]);
  setStatus(`已选中 ${button.dataset.marriageTargetLabel || `TG ${button.dataset.marriageTargetTg || ""}`}。`, "success");
});

document.querySelector("#marriage-target-selected")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-clear-marriage-target]");
  if (!button) return;
  setMarriageTarget(null);
  setStatus("已清除姻缘目标。", "warning");
});

document.querySelector("#marriage-request-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form?.querySelector("button[type='submit']");
  const target = currentMarriageTarget();
  if (!target) {
    const message = "请先搜索并选中一位道友。";
    setStatus(message, "warning");
    await popup("无法递交", message, "warning");
    return;
  }
  try {
    const payload = await runButtonAction(button, "递交中…", () => postJson("/plugins/xiuxian/api/marriage/request", {
      target_tg: target.tg,
      message: document.querySelector("#marriage-request-message")?.value?.trim?.() || "",
    }));
    if (payload.bundle) applyProfileBundle(payload.bundle);
    const result = payload.result || {};
    setMarriageTarget(null);
    const messageInput = document.querySelector("#marriage-request-message");
    if (messageInput) messageInput.value = "";
    setStatus(result.message || "结缘信物已送出。", "success");
    await popup("信物已送出", result.message || "结缘信物已送出。");
  } catch (error) {
    const message = normalizeError(error, "递交结缘信物失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#mentorship-search-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = document.querySelector("#mentorship-player-search");
  const query = document.querySelector("#mentorship-player-query")?.value || "";
  try {
    await runButtonAction(button, "搜索中…", () => searchMentorshipPlayers(query));
    if (!state.mentorshipSearchResults.length) {
      setStatus("没有找到匹配的道友。", "warning");
    }
  } catch (error) {
    const message = normalizeError(error, "搜索道友失败。");
    setStatus(message, "error");
    await popup("搜索失败", message, "error");
  }
});

document.querySelector("#mentorship-player-query")?.addEventListener("input", (event) => {
  const keyword = event.currentTarget?.value || "";
  if (state.mentorshipSearchTimer) window.clearTimeout(state.mentorshipSearchTimer);
  if (!String(keyword).trim()) {
    state.mentorshipSearchQuery = "";
    state.mentorshipSearchResults = [];
    renderMentorshipSearchResults([]);
    return;
  }
  state.mentorshipSearchTimer = window.setTimeout(() => {
    searchMentorshipPlayers(keyword).catch((error) => {
      const message = normalizeError(error, "搜索道友失败。");
      setStatus(message, "error");
    });
  }, 240);
});

document.querySelector("#mentorship-player-search-results")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-mentorship-target-tg]");
  if (!button) return;
  setMentorshipTarget({
    tg: Number(button.dataset.mentorshipTargetTg || 0),
    display_label: button.dataset.mentorshipTargetLabel || "",
    username: button.dataset.mentorshipTargetUsername || "",
  });
  state.mentorshipSearchQuery = "";
  state.mentorshipSearchResults = [];
  const queryInput = document.querySelector("#mentorship-player-query");
  if (queryInput) queryInput.value = "";
  renderMentorshipSearchResults([]);
  setStatus(`已选中 ${button.dataset.mentorshipTargetLabel || `TG ${button.dataset.mentorshipTargetTg || ""}`}。`, "success");
});

document.querySelector("#mentorship-target-selected")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-clear-mentorship-target]");
  if (!button) return;
  setMentorshipTarget(null);
  setStatus("已清除师徒目标。", "warning");
});

document.querySelector("#mentorship-request-role")?.addEventListener("change", () => {
  syncMentorshipRequestComposer(state.profileBundle);
});

document.querySelector("#mentorship-request-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form?.querySelector("button[type='submit']");
  const target = currentMentorshipTarget();
  if (!target) {
    const message = "请先搜索并选择目标道友。";
    setStatus(message, "warning");
    return await popup("缺少目标", message, "warning");
  }
  const sponsorRole = document.querySelector("#mentorship-request-role")?.value || "disciple";
  try {
    const payload = await runButtonAction(button, "递交中…", () => postJson("/plugins/xiuxian/api/mentorship/request", {
      target_tg: Number(target.tg || 0),
      sponsor_role: sponsorRole,
      message: document.querySelector("#mentorship-request-message")?.value?.trim?.() || "",
    }));
    if (payload.bundle) applyProfileBundle(payload.bundle);
    setMentorshipTarget(null);
    const requestText = payload.result?.request?.sponsor_role_label || mentorshipRequestRoleLabel(sponsorRole);
    setStatus(`已向 ${target.display_label || `TG ${target.tg}`} 递出${requestText}。`, "success");
    await popup("拜帖已送达", payload.result?.message || "对方稍后可在师徒传承页处理你的拜帖。");
    form?.reset?.();
    document.querySelector("#mentorship-request-role").value = "disciple";
    syncMentorshipRequestComposer(state.profileBundle);
  } catch (error) {
    const message = normalizeError(error, "递交师徒拜帖失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#gift-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form?.querySelector("button[type='submit']");
  const target = currentGiftTarget();
  if (!target) {
    const message = "请先搜索并选择收礼道友。";
    setStatus(message, "warning");
    return await popup("缺少目标", message, "warning");
  }
  try {
    const payload = await runButtonAction(button, "赠送中…", () => postJson("/plugins/xiuxian/api/gift", {
      target_tg: Number(target.tg || 0),
      amount: Number(document.querySelector("#gift-amount").value || 0)
    }));
    const targetName = payload.result?.receiver?.display_label || target.display_label || `TG ${target.tg}`;
    const amount = payload.result?.amount || 0;
    const message = `已向 ${targetName} 赠送 ${amount} 灵石。`;
    setStatus(message, "success");
    await popup("赠送成功", message);
    document.querySelector("#gift-amount").value = "100";
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "灵石赠送失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#item-gift-kind")?.addEventListener("change", () => {
  renderItemGiftInventorySelect(state.profileBundle);
});

document.querySelector("#item-gift-ref")?.addEventListener("change", () => {
  renderItemGiftInventorySelect(state.profileBundle);
});

document.querySelector("#item-gift-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form?.querySelector("button[type='submit']");
  const target = currentGiftTarget();
  if (!target) {
    const message = "请先搜索并选择收礼道友。";
    setStatus(message, "warning");
    return await popup("缺少目标", message, "warning");
  }
  try {
    const giftQuantity = Number(document.querySelector("#item-gift-quantity").value || 1);
    const payload = await runButtonAction(button, "赠送中…", () => postJson("/plugins/xiuxian/api/gift/item", {
      target_tg: Number(target.tg || 0),
      item_kind: document.querySelector("#item-gift-kind").value,
      item_ref_id: Number(document.querySelector("#item-gift-ref").value || 0),
      quantity: giftQuantity,
    }));
    const result = payload.result || {};
    const itemName = result.item?.artifact?.name
      || result.item?.pill?.name
      || result.item?.talisman?.name
      || result.item?.material?.name
      || "物品";
    const targetName = target.display_label || (target.username ? `@${target.username}` : `TG ${target.tg}`);
    const message = `已向 ${targetName} 赠送 ${itemName} × ${giftQuantity}。`;
    setStatus(message, "success");
    await popup("物品赠送成功", message);
    document.querySelector("#item-gift-quantity").value = "1";
    if (payload.bundle) {
      applyProfileBundle(payload.bundle);
    } else {
      await refreshBundle();
    }
  } catch (error) {
    const message = normalizeError(error, "物品赠送失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelectorAll(".rank-tab").forEach((button) => {
  button.addEventListener("click", async () => {
    try {
      await refreshLeaderboard(button.dataset.kind, 1);
    } catch (error) {
      const message = normalizeError(error, "加载排行榜失败。");
      setStatus(message, "error");
    }
  });
});

document.querySelector("#rank-prev").addEventListener("click", async () => {
  if (state.leaderboard.page <= 1) return;
  await refreshLeaderboard(state.leaderboard.kind, state.leaderboard.page - 1);
});

document.querySelector("#rank-next").addEventListener("click", async () => {
  if (state.leaderboard.page >= state.leaderboard.totalPages) return;
  await refreshLeaderboard(state.leaderboard.kind, state.leaderboard.page + 1);
});

function itemAffixTags(item, effects = {}) {
  const rows = [];
  const values = {
    attack: effects.attack_bonus ?? item.attack_bonus,
    defense: effects.defense_bonus ?? item.defense_bonus,
    bone: effects.bone_bonus ?? item.bone_bonus,
    comprehension: effects.comprehension_bonus ?? item.comprehension_bonus,
    divineSense: effects.divine_sense_bonus ?? item.divine_sense_bonus,
    fortune: effects.fortune_bonus ?? item.fortune_bonus,
    qiBlood: effects.qi_blood_bonus ?? item.qi_blood_bonus,
    trueYuan: effects.true_yuan_bonus ?? item.true_yuan_bonus,
    bodyMovement: effects.body_movement_bonus ?? item.body_movement_bonus,
    duel: effects.duel_rate_bonus ?? item.duel_rate_bonus,
    cultivation: effects.cultivation_bonus ?? item.cultivation_bonus,
    breakthrough: effects.breakthrough_bonus ?? item.breakthrough_bonus,
  };
  if (Number(values.attack || 0)) rows.push(`<span class="tag">攻击 ${escapeHtml(values.attack)}</span>`);
  if (Number(values.defense || 0)) rows.push(`<span class="tag">防御 ${escapeHtml(values.defense)}</span>`);
  if (Number(values.bone || 0)) rows.push(`<span class="tag">根骨 ${escapeHtml(values.bone)}</span>`);
  if (Number(values.comprehension || 0)) rows.push(`<span class="tag">悟性 ${escapeHtml(values.comprehension)}</span>`);
  if (Number(values.divineSense || 0)) rows.push(`<span class="tag">神识 ${escapeHtml(values.divineSense)}</span>`);
  if (Number(values.fortune || 0)) rows.push(`<span class="tag">机缘 ${escapeHtml(values.fortune)}</span>`);
  if (Number(values.qiBlood || 0)) rows.push(`<span class="tag">气血 ${escapeHtml(values.qiBlood)}</span>`);
  if (Number(values.trueYuan || 0)) rows.push(`<span class="tag">真元 ${escapeHtml(values.trueYuan)}</span>`);
  if (Number(values.bodyMovement || 0)) rows.push(`<span class="tag">身法 ${escapeHtml(values.bodyMovement)}</span>`);
  if (Number(values.duel || 0)) rows.push(`<span class="tag">斗法 +${escapeHtml(values.duel)}%</span>`);
  if (Number(values.cultivation || 0)) rows.push(`<span class="tag">修炼 +${escapeHtml(values.cultivation)}</span>`);
  if (Number(values.breakthrough || 0)) rows.push(`<span class="tag">突破 +${escapeHtml(values.breakthrough)}</span>`);
  return rows.join("");
}

const _legacyRenderArtifactList = renderArtifactList;
const _legacyRenderTalismanList = renderTalismanList;
const _legacyRenderPillList = renderPillList;
const _legacyRenderProfile = renderProfile;

renderArtifactList = function renderArtifactList(items, retreating, equipLimit, equippedCount) {
  const root = document.querySelector("#artifact-list");
  if (!root || !items.length) return _legacyRenderArtifactList(items, retreating, equipLimit, equippedCount);
  root.innerHTML = "";
  for (const row of items) {
    const item = row.artifact;
    const effects = item.resolved_effects || {};
    const disabled = !item.usable || retreating;
    const reason = item.equipped ? "" : fallbackReason(item.unusable_reason, "当前不满足装备条件");
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        <span class="badge badge--normal">x${escapeHtml(row.quantity)}</span>
      </div>
      <p>${escapeHtml(item.description || "暂无描述")}</p>
      <div class="item-tags">
        <span class="tag ${item.artifact_type === "support" ? "support" : ""}">${escapeHtml(item.artifact_type_label || artifactTypeLabel(item.artifact_type))}</span>
        <span class="tag">${escapeHtml(item.rarity || "凡品")}</span>
        ${itemAffixTags(item, effects)}
      </div>
      <p>境界要求：${escapeHtml(item.min_realm_stage ? `${item.min_realm_stage}${item.min_realm_layer}层` : "无限制")}</p>
      ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : ""}
      <button type="button" data-equip-id="${item.id}" ${disabled ? "disabled" : ""}>${escapeHtml(item.action_label || (item.equipped ? "卸下法宝" : "装备法宝"))}</button>
    `;
    root.appendChild(card);
  }
};

renderTalismanList = function renderTalismanList(items, retreating) {
  const root = document.querySelector("#talisman-list");
  if (!root || !items.length) return _legacyRenderTalismanList(items, retreating);
  root.innerHTML = "";
  for (const row of items) {
    const item = row.talisman;
    const effects = item.resolved_effects || {};
    const disabled = !item.usable || retreating;
    const reason = item.active ? "" : fallbackReason(item.unusable_reason, "当前无法启用该符箓");
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        <span class="badge badge--normal">x${escapeHtml(row.quantity)}</span>
      </div>
      <p>${escapeHtml(item.description || "暂无描述")}</p>
      <div class="item-tags">
        <span class="tag">${escapeHtml(item.rarity || "凡品")}</span>
        ${itemAffixTags(item, effects)}
      </div>
      ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : ""}
      <button type="button" data-talisman-id="${item.id}" ${disabled ? "disabled" : ""}>${item.active ? "已待生效" : "激活到下一场斗法"}</button>
    `;
    root.appendChild(card);
  }
};

renderPillList = function renderPillList(items, retreating) {
  const root = document.querySelector("#pill-list");
  if (!root || !items.length) return _legacyRenderPillList(items, retreating);
  root.innerHTML = "";
  for (const row of items) {
    const item = row.pill;
    const effects = item.resolved_effects || {};
    const disabled = !item.usable || retreating;
    const reason = fallbackReason(item.unusable_reason, "当前无法使用该丹药");
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        <span class="badge badge--normal">x${escapeHtml(row.quantity)}</span>
      </div>
      <p>${escapeHtml(item.description || "暂无描述")}</p>
      <div class="item-tags">
        <span class="tag">${escapeHtml(item.rarity || "凡品")}</span>
        <span class="tag">${escapeHtml(item.pill_type_label || item.pill_type)}</span>
        <span class="tag">主效果 ${escapeHtml(item.effect_value)}</span>
        <span class="tag">丹毒 ${escapeHtml(item.poison_delta)}</span>
        ${itemAffixTags(item, effects)}
      </div>
      ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : ""}
      <button type="button" data-pill-id="${item.id}" ${disabled ? "disabled" : ""}>服用丹药</button>
    `;
    root.appendChild(card);
  }
};

renderProfile = function renderProfile(bundle) {
  _legacyRenderProfile(bundle);
  const profile = bundle.profile || {};
  const stats = bundle.effective_stats || {};
  const currentTechnique = bundle.current_technique;
  const settings = bundle.settings || {};
  const grid = document.querySelector("#profile-grid");
  const rootText = document.querySelector("#root-text");
  const actionHint = document.querySelector("#action-hint");
  const socialSummary = document.querySelector("#social-mode-summary");
  const socialButton = document.querySelector("#social-mode-btn");
  const socialMode = currentSocialMode(bundle);
  const socialLabel = profile.social_mode_label || (socialMode === "secluded" ? "避世" : "入世");
  const socialLockReason = currentSocialInteractionLockReason(bundle);
  const duelLockReason = currentDuelLockReason(bundle);
  const seclusionEfficiency = Number(settings.seclusion_cultivation_efficiency_percent || 60);
  if (rootText) {
    rootText.textContent = `灵根：${profile.root_text || profileRootText(profile)} · 品质 ${profile.root_quality || "中品灵根"} · 五行修正 ${(profile.root_bonus ?? 0) >= 0 ? "+" : ""}${profile.root_bonus ?? 0}%`;
  }
  if (grid) {
    grid.innerHTML += `
      <article class="profile-item"><span>根骨</span><strong>${escapeHtml(stats.bone ?? profile.bone ?? 0)}</strong></article>
      <article class="profile-item"><span>悟性</span><strong>${escapeHtml(stats.comprehension ?? profile.comprehension ?? 0)}</strong></article>
      <article class="profile-item"><span>神识</span><strong>${escapeHtml(stats.divine_sense ?? profile.divine_sense ?? 0)}</strong></article>
      <article class="profile-item"><span>机缘</span><strong>${escapeHtml(stats.fortune ?? profile.fortune ?? 0)}</strong></article>
      <article class="profile-item"><span>气血</span><strong>${escapeHtml(stats.qi_blood ?? profile.qi_blood ?? 0)}</strong></article>
      <article class="profile-item"><span>真元</span><strong>${escapeHtml(stats.true_yuan ?? profile.true_yuan ?? 0)}</strong></article>
      <article class="profile-item"><span>身法</span><strong>${escapeHtml(stats.body_movement ?? profile.body_movement ?? 0)}</strong></article>
      <article class="profile-item"><span>攻击</span><strong>${escapeHtml(stats.attack_power ?? profile.attack_power ?? 0)}</strong></article>
      <article class="profile-item"><span>防御</span><strong>${escapeHtml(stats.defense_power ?? profile.defense_power ?? 0)}</strong></article>
      <article class="profile-item"><span>综合战力</span><strong>${escapeHtml(bundle.combat_power ?? 0)}</strong></article>
      <article class="profile-item"><span>当前功法</span><strong>${escapeHtml(currentTechnique?.name || "暂无")}</strong></article>
      <article class="profile-item"><span>当前状态</span><strong>${escapeHtml(socialLabel)}</strong></article>
    `;
  }
  if (actionHint && socialLockReason && !actionHint.textContent.includes(socialLockReason)) {
    actionHint.textContent = `${actionHint.textContent} ${socialLockReason}`.trim();
  }
  if (socialSummary) {
    socialSummary.textContent = socialMode === "secluded"
      ? `当前处于避世状态，斗法、抢劫与互赠已关闭，修为收益按 ${seclusionEfficiency}% 结算。`
      : "当前处于入世状态，可与其他道友正常互动。";
  }
  if (socialButton) {
    socialButton.textContent = socialMode === "secluded" ? "切换为入世" : "切换为避世";
    setDisabled(
      socialButton,
      !bundle?.capabilities?.can_toggle_social_mode,
      bundle?.capabilities?.social_mode_toggle_reason || "当前无法切换状态",
    );
  }
  const giftInteractionReason = duelLockReason || socialLockReason;
  setDisabled(document.querySelector("#gift-form button[type='submit']"), Boolean(giftInteractionReason), giftInteractionReason);
  setDisabled(document.querySelector("#item-gift-form button[type='submit']"), Boolean(giftInteractionReason), giftInteractionReason || "先选择赠送对象。");
  syncGiftPanelState(bundle);
};

const _enhancedRenderProfile = renderProfile;
renderProfile = function renderProfileWithAdminEntry(bundle) {
  _enhancedRenderProfile(bundle);
  ensureSectionState("#technique-card", Boolean(bundle?.profile?.consented));
  syncAdminEntry(bundle);
  syncUserTaskComposer();
};

function qualityBadgeHtml(label, color, className = "tag") {
  const safeLabel = escapeHtml(label || "凡品");
  const style = buildDecorBadgeStyle(color, "#9ca3af");
  return `<span class="${className}" style="${style}">${safeLabel}</span>`;
}

function inventorySearchValue(selector) {
  return String(document.querySelector(selector)?.value || "").trim().toLowerCase();
}

function textQueryMatches(query, values = []) {
  if (!query) return true;
  const haystack = values
    .flatMap((value) => Array.isArray(value) ? value : [value])
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(query);
}

function inventoryMatches(item, query, extraFields = []) {
  if (!query) return true;
  const haystack = [
    item?.name,
    item?.description,
    item?.rarity,
    item?.quality_label,
    item?.artifact_type_label,
    item?.artifact_role_label,
    item?.equip_slot_label,
    item?.pill_type_label,
    item?.quality_feature,
    item?.quality_description,
    ...extraFields.map((key) => item?.[key]),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(query);
}

function sortInventoryRowsByQuality(rows, pickItem, qualityKey = "rarity_level") {
  return [...(rows || [])].sort((left, right) => {
    const leftItem = pickItem(left) || {};
    const rightItem = pickItem(right) || {};
    const leftQuality = Number(leftItem?.[qualityKey] || 0);
    const rightQuality = Number(rightItem?.[qualityKey] || 0);
    if (leftQuality !== rightQuality) return rightQuality - leftQuality;
    return String(leftItem?.name || "").localeCompare(String(rightItem?.name || ""), "zh-Hans-CN");
  });
}

function rerenderInventoryLists() {
  const bundle = state.profileBundle;
  if (!bundle?.profile?.consented) return;
  const retreating = Boolean(bundle.capabilities?.is_in_retreat);
  const equippedArtifacts = bundle.equipped_artifacts || [];
  const equipLimit = Number(bundle.settings?.artifact_equip_limit || bundle.capabilities?.artifact_equip_limit || 1);
  renderArtifactList(bundle.artifacts || [], retreating, equipLimit, equippedArtifacts.length);
  renderTalismanList(bundle.talismans || [], retreating);
  renderPillList(bundle.pills || [], retreating);
  renderCraftArea(bundle);
}

renderCraftArea = function renderCraftArea(bundle) {
  const materialRoot = document.querySelector("#material-list");
  const recipeRoot = document.querySelector("#recipe-list");
  if (!materialRoot || !recipeRoot) return;

  const sourceMaterials = bundle.materials || [];
  const materialQuery = inventorySearchValue("#material-search");
  const materials = sortInventoryRowsByQuality(
    sourceMaterials.filter((row) => inventoryMatches(row.material || {}, materialQuery, ["quality_feature", "quality_description"])),
    (row) => row.material || {},
    "quality_level"
  );
  materialRoot.innerHTML = materials.length
    ? materials.map((row) => `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(row.material.name)}</strong>
          ${qualityBadgeHtml(row.material.quality_label || row.material.quality_level, row.material.quality_color, "badge badge--normal")}
        </div>
        <p>数量 ${escapeHtml(row.quantity)}</p>
        <p class="muted">${escapeHtml(row.material.quality_feature || row.material.quality_description || "")}</p>
      </article>
    `).join("")
    : sourceMaterials.length
      ? `<article class="stack-item"><strong>未找到匹配材料</strong><p>换个名称、品质或用途关键词再试。</p></article>`
      : `<article class="stack-item"><strong>暂无炼制材料</strong><p>可通过探索、任务或主人发放获得。</p></article>`;

  const recipes = bundle.recipes || [];
  const recipeQuery = inventorySearchValue("#recipe-search");
  const filteredRecipes = recipes.filter((recipe) => textQueryMatches(recipeQuery, [
    recipe.name,
    recipe.recipe_kind_label,
    recipe.result_item?.name,
    (recipe.ingredients || []).map((item) => item.material?.name),
    (recipe.ingredients || []).map((item) => item.source_text),
    recipe.source,
    recipe.obtained_note,
  ]));
  recipeRoot.innerHTML = "";
  if (!filteredRecipes.length) {
    recipeRoot.innerHTML = recipes.length
      ? `<article class="stack-item"><strong>未找到匹配配方</strong><p>可按配方名、成品、材料或获取途径继续搜索。</p></article>`
      : `<article class="stack-item"><strong>暂无配方</strong></article>`;
    return;
  }
  for (const recipe of filteredRecipes) {
    const ingredientTags = (recipe.ingredients || [])
      .map((item) => `<span class="tag">${escapeHtml(item.material?.name || "材料")} × ${escapeHtml(item.quantity)}</span>`)
      .join("");
    const sourceCards = (recipe.ingredients || [])
      .map((item) => `
        <article class="recipe-source-item">
          <strong>${escapeHtml(item.material?.name || "材料")} × ${escapeHtml(item.quantity)}</strong>
          <p>${escapeHtml(item.source_text || (item.sources || []).join("、") || "暂未补充获取路径")}</p>
        </article>
      `)
      .join("");
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(recipe.name)}</strong>
        <span class="badge badge--normal">${escapeHtml(recipe.recipe_kind_label || recipe.recipe_kind)}</span>
      </div>
      <p>${escapeHtml(recipe.source ? `来源：${recipe.source}${recipe.obtained_note ? ` · ${recipe.obtained_note}` : ""}` : "已掌握配方，可随时开炉。")}</p>
      <div class="info-grid">
        <article class="info-chip">
          <span>炼成目标</span>
          <strong>${escapeHtml(recipe.result_item?.name || "成品")} × ${escapeHtml(recipe.result_quantity)}</strong>
        </article>
        <article class="info-chip">
          <span>基础成功率</span>
          <strong>${escapeHtml(recipe.base_success_rate)}%</strong>
        </article>
        <article class="info-chip">
          <span>所需材料数</span>
          <strong>${escapeHtml((recipe.ingredients || []).length)}</strong>
        </article>
      </div>
      <div class="item-tags">${ingredientTags || `<span class="tag">未配置材料</span>`}</div>
      <div class="recipe-source-list">${sourceCards || `<article class="recipe-source-item"><strong>获取路径待补充</strong><p>当前配方没有记录材料来源。</p></article>`}</div>
      <button type="button" data-recipe-id="${recipe.id}">开始炼制</button>
    `;
    recipeRoot.appendChild(card);
  }
};

renderArtifactList = function renderArtifactList(items, retreating, equipLimit, equippedCount) {
  const root = document.querySelector("#artifact-list");
  if (!root) return;
  root.innerHTML = "";
  const artifactQuery = inventorySearchValue("#artifact-search");
  const rows = sortInventoryRowsByQuality(
    (items || []).filter((row) => inventoryMatches(row.artifact || {}, artifactQuery, ["artifact_set_name", "min_realm_stage"])),
    (row) => row.artifact || {},
    "rarity_level"
  );
  if (!rows.length) {
    root.innerHTML = (items || []).length
      ? `<article class="stack-item"><strong>未找到匹配法宝</strong><p>可按名称、品质、槽位或套装继续检索。</p></article>`
      : `<article class="stack-item"><strong>暂无法宝</strong><p>管理后台发放或在${escapeHtml(officialShopName())}购买后会出现在这里。</p></article>`;
    return;
  }
  const cardsArray = [];
  for (const row of rows) {
    const item = row.artifact;
    const effects = item.resolved_effects || {};
    const disabled = !item.usable || retreating;
    const bindableQuantity = Number(row.unbound_quantity ?? row.quantity ?? 0);
    const unbindableQuantity = Number(row.bound_quantity ?? 0);
    const canBind = bindableQuantity > 0;
    const canUnbind = unbindableQuantity > 0;
    const unbindCost = Number(state.profileBundle?.settings?.equipment_unbind_cost || 0);
    const reason = item.equipped
      ? ""
      : fallbackReason(
          item.unusable_reason,
          retreating
            ? "闭关期间无法切换法宝"
            : equippedCount >= equipLimit
              ? `当前最多只能装备 ${equipLimit} 件法宝`
              : "当前不满足装备条件"
        );
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        <span class="badge badge--normal">x${escapeHtml(row.quantity)}</span>
      </div>
      <p>${escapeHtml(item.description || "暂无描述")}</p>
      <div class="item-tags">
        <span class="tag ${item.artifact_type === "support" ? "support" : ""}">${escapeHtml(item.artifact_type_label || artifactTypeLabel(item.artifact_type))}</span>
        ${qualityBadgeHtml(item.rarity || "凡品", item.quality_color, "tag")}
        ${unbindableQuantity > 0 ? `<span class="tag">已绑定 ${escapeHtml(unbindableQuantity)}</span>` : ""}
        ${bindableQuantity > 0 ? `<span class="tag">未绑定 ${escapeHtml(bindableQuantity)}</span>` : ""}
        ${itemAffixTags(item, effects)}
      </div>
      <p>境界要求：${escapeHtml(item.min_realm_stage ? `${item.min_realm_stage}${item.min_realm_layer}层` : "无限制")}</p>
      <p>可交易：${escapeHtml(row.tradeable_quantity ?? 0)} ｜ 可提交：${escapeHtml(row.consumable_quantity ?? 0)}</p>
      ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : ""}
      <div class="inline-action-buttons">
        <button type="button" data-equip-id="${item.id}" ${disabled ? "disabled" : ""}>${escapeHtml(item.action_label || (item.equipped ? "卸下法宝" : "装备法宝"))}</button>
        <button type="button" class="ghost" data-artifact-bind-id="${item.id}" ${canBind ? "" : "disabled"}>绑定1件</button>
        <button type="button" class="ghost" data-artifact-unbind-id="${item.id}" ${canUnbind ? "" : "disabled"}>解绑1件${unbindCost > 0 ? `（${escapeHtml(unbindCost)}灵石）` : ""}</button>
      </div>
    `;
    cardsArray.push({ card, item });
  }
  renderGroupedCards(root, cardsArray, item => item.rarity || "凡品");
};

renderTalismanList = function renderTalismanList(items, retreating) {
  const root = document.querySelector("#talisman-list");
  if (!root) return;
  root.innerHTML = "";
  const talismanQuery = inventorySearchValue("#talisman-search");
  const rows = sortInventoryRowsByQuality(
    (items || []).filter((row) => inventoryMatches(row.talisman || {}, talismanQuery, ["min_realm_stage"])),
    (row) => row.talisman || {},
    "rarity_level"
  );
  if (!rows.length) {
    root.innerHTML = (items || []).length
      ? `<article class="stack-item"><strong>未找到匹配符箓</strong><p>可以按名称、效果或境界要求搜索。</p></article>`
      : `<article class="stack-item"><strong>暂无符箓</strong><p>符箓会在下一场斗法中生效，后续可通过商店、掉落或发放获得。</p></article>`;
    return;
  }
  const cardsArray = [];
  for (const row of rows) {
    const item = row.talisman;
    const effects = item.resolved_effects || {};
    const disabled = item.active || !item.usable || retreating;
    const bindableQuantity = Number(row.unbound_quantity ?? row.quantity ?? 0);
    const unbindableQuantity = Number(row.bound_quantity ?? 0);
    const canBind = bindableQuantity > 0;
    const canUnbind = unbindableQuantity > 0;
    const unbindCost = Number(state.profileBundle?.settings?.equipment_unbind_cost || 0);
    const reason = item.active
      ? "当前已有待生效符箓"
      : fallbackReason(item.unusable_reason, retreating ? "闭关期间无法启用符箓" : "当前不满足启用条件");
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        <span class="badge badge--normal">x${escapeHtml(row.quantity)}</span>
      </div>
      <p>${escapeHtml(item.description || "暂无描述")}</p>
      <div class="item-tags">
        ${qualityBadgeHtml(item.rarity || "凡品", item.quality_color, "tag")}
        ${unbindableQuantity > 0 ? `<span class="tag">已绑定 ${escapeHtml(unbindableQuantity)}</span>` : ""}
        ${bindableQuantity > 0 ? `<span class="tag">未绑定 ${escapeHtml(bindableQuantity)}</span>` : ""}
        ${itemAffixTags(item, effects)}
      </div>
      <p>斗法内最多显化 ${escapeHtml(item.effect_uses || 1)} 次，斗法结束后会自动消散。</p>
      <p>境界要求：${escapeHtml(item.min_realm_stage ? `${item.min_realm_stage}${item.min_realm_layer}层` : "无限制")}</p>
      <p>可交易：${escapeHtml(row.tradeable_quantity ?? 0)} ｜ 可提交：${escapeHtml(row.consumable_quantity ?? 0)}</p>
      ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : ""}
      <div class="inline-action-buttons">
        <button type="button" data-talisman-id="${item.id}" ${disabled ? "disabled" : ""}>${item.active ? "已待生效" : "激活到下一场斗法"}</button>
        <button type="button" class="ghost" data-talisman-bind-id="${item.id}" ${canBind ? "" : "disabled"}>绑定1件</button>
        <button type="button" class="ghost" data-talisman-unbind-id="${item.id}" ${canUnbind ? "" : "disabled"}>解绑1件${unbindCost > 0 ? `（${escapeHtml(unbindCost)}灵石）` : ""}</button>
      </div>
    `;
    cardsArray.push({ card, item });
  }
  renderGroupedCards(root, cardsArray, item => item.rarity || "凡品");
};

renderPillList = function renderPillList(items, retreating) {
  const root = document.querySelector("#pill-list");
  if (!root) return;
  root.innerHTML = "";
  const pillQuery = inventorySearchValue("#pill-search");
  const rows = sortInventoryRowsByQuality(
    (items || []).filter((row) => inventoryMatches(row.pill || {}, pillQuery, ["pill_type_label", "min_realm_stage"])),
    (row) => row.pill || {},
    "rarity_level"
  );
  if (!rows.length) {
    root.innerHTML = (items || []).length
      ? `<article class="stack-item"><strong>未找到匹配丹药</strong><p>可以按名称、丹类或效果关键词搜索。</p></article>`
      : `<article class="stack-item"><strong>暂无丹药</strong><p>${escapeHtml(officialShopName())}购买或主人发放后会出现在这里。</p></article>`;
    return;
  }
  const cardsArray = [];
  for (const row of rows) {
    const item = row.pill;
    const effects = item.resolved_effects || {};
    const disabled = !item.usable || retreating;
    const batchUsable = Boolean(item.batch_usable) && Number(row.quantity || 0) > 1;
    const batchMax = Math.max(Number(item.batch_use_max || row.quantity || 1), 1);
    const batchNote = Number(row.quantity || 0) > 1 ? String(item.batch_use_note || "").trim() : "";
    const reason = fallbackReason(item.unusable_reason, retreating ? "闭关期间无法服用丹药" : "当前无法使用该丹药");
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name)}</strong>
        <span class="badge badge--normal">x${escapeHtml(row.quantity)}</span>
      </div>
      <p>${escapeHtml(item.description || "暂无描述")}</p>
      <div class="item-tags">
        ${qualityBadgeHtml(item.rarity || "凡品", item.quality_color, "tag")}
        <span class="tag">${escapeHtml(item.pill_type_label || item.pill_type)}</span>
        <span class="tag">${escapeHtml(item.effect_value_label || "主效果")} ${escapeHtml(effects.effect_value ?? item.effect_value)}</span>
        <span class="tag">丹毒 ${escapeHtml(effects.poison_delta ?? item.poison_delta)}</span>
        ${itemAffixTags(item, effects)}
      </div>
      <p>境界要求：${escapeHtml(item.min_realm_stage ? `${item.min_realm_stage}${item.min_realm_layer}层` : "无限制")}</p>
      ${batchNote ? `<p class="muted">${escapeHtml(batchNote)}</p>` : ""}
      ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : ""}
      <div class="inline-actions">
        <button type="button" data-pill-id="${item.id}" ${disabled ? "disabled" : ""}>服用丹药</button>
        ${batchUsable ? `<input type="number" min="1" max="${escapeHtml(batchMax)}" value="${escapeHtml(Math.min(batchMax, 10))}" data-pill-quantity-for="${item.id}" ${disabled ? "disabled" : ""}>` : ""}
        ${batchUsable ? `<button type="button" class="ghost" data-pill-batch-id="${item.id}" ${disabled ? "disabled" : ""}>批量服用</button>` : ""}
      </div>
    `;
    cardsArray.push({ card, item });
  }
  renderGroupedCards(root, cardsArray, item => item.pill_type_label || item.pill_type || "其他");
};

["#artifact-search", "#talisman-search", "#pill-search", "#material-search"].forEach((selector) => {
  document.querySelector(selector)?.addEventListener("input", () => {
    rerenderInventoryLists();
  });
});

["#recipe-search", "#scene-search"].forEach((selector) => {
  document.querySelector(selector)?.addEventListener("input", () => {
    if (!state.profileBundle?.profile?.consented) return;
    renderCraftArea(state.profileBundle);
    renderExploreArea(state.profileBundle);
  });
});

function syncAdminEntry(bundle = state.profileBundle) {
  const root = document.querySelector("#hero-admin-entry");
  const button = document.querySelector("#open-admin-panel");
  const adminUrl = bundle?.capabilities?.admin_panel_url;
  const visible = Boolean(bundle?.capabilities?.is_admin && adminUrl);
  if (root) {
    root.classList.toggle("hidden", !visible);
  }
  if (button) {
    button.disabled = !visible;
    button.dataset.adminUrl = visible ? adminUrl : "";
  }
}

function syncUserTaskComposer() {
  const taskType = document.querySelector("#task-type")?.value || "custom";
  const isQuiz = taskType === "quiz";
  const title = document.querySelector("#task-title");
  const description = document.querySelector("#task-description");
  const pushGroup = document.querySelector("#task-push-group");
  const maxClaimants = document.querySelector("#task-max-claimants");
  const question = document.querySelector("#task-question");
  const answer = document.querySelector("#task-answer");
  const requiredKind = document.querySelector("#task-required-kind");
  const requiredRef = document.querySelector("#task-required-ref");
  const requiredQuantity = document.querySelector("#task-required-quantity");
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
  if (requiredKind) {
    if (isQuiz) requiredKind.value = "";
    requiredKind.disabled = isQuiz;
  }
  if (requiredQuantity) {
    if (isQuiz) requiredQuantity.value = "0";
    requiredQuantity.disabled = isQuiz;
  }
  if (requiredRef) {
    requiredRef.disabled = isQuiz;
  }
  renderTaskRequirementSelect();
}

function validateUserTaskComposer() {
  const publishButton = document.querySelector("#task-form button[type='submit']");
  const blockedReason = String(publishButton?.dataset.blockedReason || "").trim();
  if (blockedReason) {
    return { title: "当前无法发布", message: blockedReason, tone: "warning" };
  }

  const title = document.querySelector("#task-title")?.value || "";
  const description = document.querySelector("#task-description")?.value || "";
  const taskType = document.querySelector("#task-type")?.value || "custom";
  const question = document.querySelector("#task-question")?.value || "";
  const answer = document.querySelector("#task-answer")?.value || "";
  const requiredKind = document.querySelector("#task-required-kind")?.value || "";
  const requiredRef = Number(document.querySelector("#task-required-ref")?.value || 0);
  const requiredQuantity = Number(document.querySelector("#task-required-quantity")?.value || 0);
  const rewardStone = Number(document.querySelector("#task-reward-stone")?.value || 0);

  if (meaningfulTextLength(title) < 2) {
    return { title: "表单未完成", message: "任务标题至少填写 2 个字。", tone: "error" };
  }

  if (taskType === "quiz") {
    if (meaningfulTextLength(question) < 4) {
      return { title: "表单未完成", message: "答题任务必须填写清晰的题目内容。", tone: "error" };
    }
    if (!String(answer || "").trim()) {
      return { title: "表单未完成", message: "答题任务必须填写标准答案。", tone: "error" };
    }
  } else if (meaningfulTextLength(description) < 6) {
    return { title: "表单未完成", message: "普通任务必须填写至少 6 个字的任务说明。", tone: "error" };
  }

  if (requiredKind) {
    if (!requiredRef) {
      const requiredSelect = document.querySelector("#task-required-ref");
      const message = requiredSelect?.disabled
        ? "当前没有可选择的提交物，请先切换提交物类型或取消提交需求。"
        : "请选择任务需要提交的物品。";
      return { title: "表单未完成", message, tone: "error" };
    }
    if (requiredQuantity <= 0) {
      return { title: "表单未完成", message: "任务提交物数量必须大于 0。", tone: "error" };
    }
  }

  if (rewardStone <= 0) {
    return { title: "表单未完成", message: "悬赏任务必须设置奖励灵石。", tone: "error" };
  }

  return null;
}

document.querySelector("#task-type")?.addEventListener("change", syncUserTaskComposer);
document.querySelector("#task-required-kind")?.addEventListener("change", renderTaskRequirementSelect);

document.querySelector("#open-admin-panel")?.addEventListener("click", () => {
  const button = document.querySelector("#open-admin-panel");
  const adminUrl = button?.dataset.adminUrl || state.profileBundle?.capabilities?.admin_panel_url;
  if (adminUrl) {
    window.location.href = adminUrl;
  }
});

const userTaskForm = document.querySelector("#task-form");
if (userTaskForm) {
  userTaskForm.noValidate = true;
}

userTaskForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  event.stopImmediatePropagation();
  const form = event.currentTarget;
  const button = form?.querySelector("button[type='submit']");
  try {
    const validation = validateUserTaskComposer();
    if (validation) {
      setStatus(validation.message, validation.tone);
      await popup(validation.title, validation.message, validation.tone);
      return;
    }
    const payload = await runButtonAction(button, "发布中...", () => postJson("/plugins/xiuxian/api/task/create", {
      title: document.querySelector("#task-title").value.trim(),
      description: document.querySelector("#task-description").value.trim(),
      task_scope: document.querySelector("#task-scope").value,
      task_type: document.querySelector("#task-type").value,
      question_text: document.querySelector("#task-question").value.trim(),
      answer_text: document.querySelector("#task-answer").value.trim(),
      image_url: document.querySelector("#task-image").value.trim(),
      required_item_kind: document.querySelector("#task-required-kind").value || null,
      required_item_ref_id: Number(document.querySelector("#task-required-ref").value || 0) || null,
      required_item_quantity: Number(document.querySelector("#task-required-quantity").value || 0),
      reward_stone: Number(document.querySelector("#task-reward-stone").value || 0),
      max_claimants: Number(document.querySelector("#task-max-claimants").value || 1),
      active_in_group: document.querySelector("#task-push-group").checked
    }));
    const pushWarning = payload.push_warning;
    const publishCost = Number(state.profileBundle?.settings?.task_publish_cost || 0);
    const costText = publishCost > 0 ? `，消耗 ${publishCost} 灵石` : "";
    const message = pushWarning
      ? `任务《${payload.task.title}》已创建${costText}，但群内推送失败。\n${pushWarning}`
      : `任务《${payload.task.title}》已发布${costText}。`;
    setStatus(message, pushWarning ? "warning" : "success");
    await popup(pushWarning ? "创建已完成，但推送失败" : "发布成功", message, pushWarning ? "warning" : "success");
    form?.reset?.();
    const rewardStoneInput = document.querySelector("#task-reward-stone");
    if (rewardStoneInput) rewardStoneInput.value = "10";
    syncUserTaskComposer();
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "发布任务失败，请稍后重试");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
}, true);

function looksCorruptedText(value) {
  const text = String(value ?? "").trim();
  if (!text) return true;
  const markers = ["鍙", "鎿", "銆", "鏈", "璇", "闂", "鍒", "鐏", "淇", "寮", "缁", "锛"];
  let hits = 0;
  for (const marker of markers) {
    if (text.includes(marker)) hits += 1;
  }
  return hits >= 2;
}

function toneTitle(tone = "info") {
  if (tone === "error") return "操作失败";
  if (tone === "warning") return "需要注意";
  if (tone === "success") return "操作完成";
  return "状态更新";
}

function toneMessage(tone = "info") {
  if (tone === "error") return "操作没有成功，请稍后重试。";
  if (tone === "warning") return "当前操作已完成，但有额外信息需要留意。";
  if (tone === "success") return "操作已经完成。";
  return "正在同步当前状态。";
}

function readableUiText(value, tone = "info", fallback = "") {
  const text = String(value ?? "").trim();
  if (!text || looksCorruptedText(text)) {
    return fallback || toneMessage(tone);
  }
  return text;
}

function showToast(text, tone = "info") {
  const stack = document.querySelector("#toast-stack");
  if (!stack || !text) return;
  const node = document.createElement("article");
  node.className = `toast ${tone}`;
  node.textContent = text;
  stack.appendChild(node);
  setTimeout(() => {
    node.remove();
  }, 2600);
}

let popupResolver = null;

function closeInlinePopup() {
  const layer = document.querySelector("#modal-layer");
  if (layer) {
    layer.classList.add("hidden");
    layer.setAttribute("aria-hidden", "true");
  }
  document.body.classList.remove("is-modal-open");
  if (popupResolver) {
    const resolve = popupResolver;
    popupResolver = null;
    resolve();
  }
}

document.querySelector("#modal-close")?.addEventListener("click", closeInlinePopup);
document.querySelector("#modal-confirm")?.addEventListener("click", closeInlinePopup);
document.querySelector("[data-modal-close]")?.addEventListener("click", closeInlinePopup);
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeInlinePopup();
  }
});

setStatus = function setStatusRefined(text, tone = "info") {
  const safeText = readableUiText(text, tone, toneMessage(tone));
  const statusText = document.querySelector("#status-text");
  const chip = document.querySelector("#feedback-chip");
  if (statusText) statusText.textContent = safeText;
  if (chip) {
    chip.textContent = safeText;
    chip.className = `feedback-chip ${tone === "error" ? "error" : tone === "success" ? "success" : tone === "warning" ? "warning" : ""}`;
    chip.classList.remove("hidden");
  }
  if (tone !== "info") {
    showToast(safeText, tone);
  }
};

popup = async function popupRefined(title, message, tone = "success") {
  touchFeedback(tone);
  const layer = document.querySelector("#modal-layer");
  const label = document.querySelector("#modal-label");
  const titleNode = document.querySelector("#modal-title");
  const messageNode = document.querySelector("#modal-message");
  if (!layer || !label || !titleNode || !messageNode) {
    return;
  }
  if (popupResolver) {
    closeInlinePopup();
  }
  label.textContent = toneTitle(tone);
  titleNode.textContent = readableUiText(title, tone, toneTitle(tone));
  messageNode.textContent = readableUiText(message, tone, toneMessage(tone));
  layer.classList.remove("hidden");
  layer.setAttribute("aria-hidden", "false");
  document.body.classList.add("is-modal-open");
  layer.scrollTop = 0;
  messageNode.scrollTop = 0;
  return new Promise((resolve) => {
    popupResolver = resolve;
  });
};

renderProfile = function renderProfileRedesigned(bundle) {
  state.profileBundle = bundle;
  const profile = bundle.profile || {};
  const consented = Boolean(profile.consented);

  ensureSectionState("#enter-card", !consented, true);
  [
    "#profile-card",
    "#action-card",
    "#exchange-card",
    "#inventory-card",
    "#technique-card",
    "#official-shop-card",
    "#market-card",
    "#auction-card",
    "#leaderboard-card",
    "#sect-card",
    "#task-card",
    "#craft-card",
    "#explore-card",
    "#red-envelope-card",
    "#journal-card",
    "#gift-card",
  ].forEach((selector) => ensureSectionState(selector, consented));

  const realmBadge = document.querySelector("#realm-badge");
  const rootText = document.querySelector("#root-text");
  const heroRootPill = document.querySelector("#hero-root-pill");
  const profileGrid = document.querySelector("#profile-grid");
  const officialShopTitle = document.querySelector("#official-shop-title");

  if (!consented) {
    const deathAt = profile.death_at ? formatDate(profile.death_at) : "";
    const rebirthCount = Number(profile.rebirth_count || 0);
    const rebirthLocked = Boolean(profile.rebirth_locked || bundle?.capabilities?.rebirth_locked);
    const rebirthAvailableAt = profile.rebirth_available_at ? formatDate(profile.rebirth_available_at) : "";
    const rebirthRemaining = Number(profile.rebirth_cooldown_remaining_seconds || 0);
    const rebirthCooldownHours = Number(profile.rebirth_cooldown_hours || 0);
    const rebirthReason = String(profile.rebirth_cooldown_reason || bundle?.capabilities?.enter_reason || "").trim();
    const rebirthLockedText = rebirthLocked
      ? `转世重修冷却中，还需等待 ${formatRemainingDuration(rebirthRemaining)}${rebirthAvailableAt ? `，预计 ${rebirthAvailableAt} 后可重新踏入仙途。` : "。"}`
      : "";
    const enterButton = document.querySelector("#enter-path");
    setDisabled(enterButton, rebirthLocked, rebirthLockedText || rebirthReason || "当前无法踏入仙途");
    if (realmBadge) realmBadge.textContent = "未入道";
    if (heroRootPill) {
      heroRootPill.textContent = profile.death_at
        ? (rebirthLocked ? "残魂冷却中" : "残魂待续")
        : "等待踏入仙途";
    }
    if (rootText) {
      rootText.textContent = profile.death_at
        ? (
          rebirthLocked
            ? `上一世已于 ${deathAt || "未知时刻"} 陨落，当前转世次数 ${rebirthCount}。${rebirthLockedText}`
            : `上一世已于 ${deathAt || "未知时刻"} 陨落，当前转世次数 ${rebirthCount}。${rebirthCooldownHours > 0 ? `本次重修冷却 ${rebirthCooldownHours} 小时已结束，` : ""}可重新踏入仙途，重新入道后将重开道途。`
        )
        : "确认入道后将抽取灵根、开启境界与背包系统。";
    }
    setStatus(
      profile.death_at
        ? (rebirthLocked
          ? rebirthLockedText
          : `你已身死道消，当前可重新踏入仙途。${rebirthAvailableAt ? ` 本次冷却结束时间：${rebirthAvailableAt}` : ""}`)
        : "你还没有踏入仙途，确认后将建立修仙档案。",
      profile.death_at ? (rebirthLocked ? "error" : "warning") : "warning",
    );
    syncAdminEntry(bundle);
    syncUserTaskComposer();
    return;
  }

  const progress = bundle.progress || {};
  const settings = bundle.settings || {};
  const retreating = Boolean(bundle.capabilities?.is_in_retreat);
  const duelLockReason = currentDuelLockReason(bundle);
  const equippedArtifacts = bundle.equipped_artifacts || [];
  const equipLimit = settings.artifact_equip_limit || bundle.capabilities?.artifact_equip_limit || 1;
  const artifactNames = equippedArtifacts.length ? equippedArtifacts.map((item) => item.name).join("、") : "未装备";
  const talismanName = bundle.active_talisman?.name || "暂无";
  const retreatStatus = retreating ? `闭关中，预计 ${formatDate(profile.retreat_end_at)} 出关` : "当前未闭关";
  const rootLabel = profile.root_text || profileRootText(profile);
  const rootQuality = profile.root_quality || "灵根未定";
  const rootBonus = Number(profile.root_bonus || 0);
  const stats = bundle.effective_stats || {};
  const slaveNames = Array.isArray(profile.slave_names) ? profile.slave_names : [];
  const servitudeText = profile.master_name
    ? `炉鼎于 ${profile.master_name} 名下`
    : (slaveNames.length ? `名下 ${slaveNames.length} 名炉鼎` : "无炉鼎因果");
  const servitudeCooldownText = profile.master_name
    ? (profile.servitude_challenge_available_at ? formatDate(profile.servitude_challenge_available_at) : "可随时发起脱离挑战")
    : "无";

  if (realmBadge) {
    realmBadge.textContent = `${profile.realm_stage || "炼气"}${profile.realm_layer || 0}层`;
  }
  if (heroRootPill) {
    heroRootPill.textContent = `${rootQuality} · ${rootLabel}`;
  }
  if (rootText) {
    rootText.textContent = `灵根：${rootLabel}，五行修正 ${rootBonus >= 0 ? "+" : ""}${rootBonus}%`;
  }
  if (officialShopTitle) {
    officialShopTitle.textContent = officialShopName(bundle);
  }
  if (profileGrid) {
    profileGrid.innerHTML = `
      <article class="profile-item"><span>当前修为</span><strong>${escapeHtml(progress.current ?? profile.cultivation ?? 0)}</strong></article>
      <article class="profile-item"><span>下一层门槛</span><strong>${escapeHtml(progress.threshold ?? 0)}</strong></article>
      <article class="profile-item"><span>距离突破</span><strong>${escapeHtml(progress.remaining ?? 0)}</strong></article>
      <article class="profile-item"><span>灵石</span><strong>${escapeHtml(profile.spiritual_stone ?? 0)}</strong></article>
      <article class="profile-item"><span>根骨</span><strong>${escapeHtml(stats.bone ?? profile.bone ?? 0)}</strong></article>
      <article class="profile-item"><span>悟性</span><strong>${escapeHtml(stats.comprehension ?? profile.comprehension ?? 0)}</strong></article>
      <article class="profile-item"><span>神识</span><strong>${escapeHtml(stats.divine_sense ?? profile.divine_sense ?? 0)}</strong></article>
      <article class="profile-item"><span>机缘</span><strong>${escapeHtml(stats.fortune ?? profile.fortune ?? 0)}</strong></article>
      <article class="profile-item"><span>心志</span><strong>${escapeHtml(stats.willpower ?? profile.willpower ?? 0)}</strong></article>
      <article class="profile-item"><span>魅力</span><strong>${escapeHtml(stats.charisma ?? profile.charisma ?? 0)}</strong></article>
      <article class="profile-item"><span>因果</span><strong>${escapeHtml(stats.karma ?? profile.karma ?? 0)}</strong></article>
      <article class="profile-item"><span>丹毒</span><strong>${escapeHtml(profile.dan_poison ?? 0)} / 100</strong></article>
      <article class="profile-item"><span>法宝位</span><strong>${escapeHtml(equippedArtifacts.length)} / ${escapeHtml(equipLimit)}</strong></article>
      <article class="profile-item"><span>已装法宝</span><strong>${escapeHtml(artifactNames)}</strong></article>
      <article class="profile-item"><span>待生效符箓</span><strong>${escapeHtml(talismanName)}</strong></article>
      <article class="profile-item"><span>当前功法</span><strong>${escapeHtml(bundle.current_technique?.name || "暂无")}</strong></article>
      <article class="profile-item"><span>炉鼎关系</span><strong>${escapeHtml(servitudeText)}</strong></article>
      <article class="profile-item"><span>脱离冷却</span><strong>${escapeHtml(servitudeCooldownText)}</strong></article>
      <article class="profile-item"><span>闭关状态</span><strong>${escapeHtml(retreatStatus)}</strong></article>
      <article class="profile-item"><span>宗门贡献</span><strong>${escapeHtml(profile.sect_contribution ?? 0)}</strong></article>
      <article class="profile-item"><span>转世次数</span><strong>${escapeHtml(profile.rebirth_count ?? 0)}</strong></article>
      <article class="profile-item"><span>综合战力</span><strong>${escapeHtml(bundle.combat_power ?? stats.attack_power ?? 0)}</strong></article>
    `;
  }

  const hints = [];
  if (duelLockReason) {
    hints.push(duelLockReason);
  }
  if (retreating) {
    hints.push("闭关期间无法进行大部分主动操作。");
  } else {
    if (!bundle.capabilities?.can_train) hints.push("今日吐纳次数已用完。");
    if (!bundle.capabilities?.can_breakthrough) hints.push("当前还未满足突破条件。");
  }
  const actionHint = document.querySelector("#action-hint");
  if (actionHint) {
    actionHint.textContent = hints.join(" ") || "状态稳定，可以继续修炼、交易、探索或发布任务。";
  }

  const rate = settings.rate ?? settings.coin_exchange_rate ?? 100;
  const fee = settings.fee_percent ?? settings.exchange_fee_percent ?? 1;
  const minExchange = settings.min_coin_exchange ?? 1;
  const exchangeEnabled = settings.coin_stone_exchange_enabled ?? true;
  const exchangeHint = document.querySelector("#exchange-hint");
  if (exchangeHint) {
    exchangeHint.textContent = exchangeEnabled
      ? `当前比例：1 片刻碎片 = ${rate} 灵石，手续费 ${fee}%，灵石兑换碎片最低消耗 ${minExchange} 灵石，不足 ${rate} 灵石一份的零头会保留。${duelLockReason ? ` 当前状态：${duelLockReason}` : ""}`
      : `灵石互兑功能当前已关闭。${duelLockReason ? ` 当前状态：${duelLockReason}` : ""}`;
  }

  setDisabled(document.querySelector("#train-btn"), !bundle.capabilities?.can_train, "当前无法吐纳修炼");
  applyBreakthroughActionState(bundle, "当前无法尝试突破");
  setDisabled(document.querySelector("#retreat-start-btn"), !bundle.capabilities?.can_retreat, "当前无法开始闭关");
  setDisabled(document.querySelector("#retreat-finish-btn"), !retreating, "当前没有进行中的闭关");
  const exchangeActionDisabled = Boolean(duelLockReason) || !exchangeEnabled;
  const exchangeActionReason = !exchangeEnabled ? "灵石互兑功能当前已关闭。" : duelLockReason;
  ["#coin-to-stone-amount", "#stone-to-coin-amount"]
    .forEach((selector) => setDisabled(document.querySelector(selector), retreating || exchangeActionDisabled, exchangeActionReason));
  setDisabled(document.querySelector("#coin-to-stone-form button[type='submit']"), retreating || exchangeActionDisabled, exchangeActionReason);
  setDisabled(document.querySelector("#stone-to-coin-form button[type='submit']"), retreating || exchangeActionDisabled, exchangeActionReason);

  const shopDisabledReason = retreating ? "闭关期间无法经营店铺。" : duelLockReason;
  ["#shop-item-kind", "#shop-item-ref", "#shop-quantity", "#shop-price", "#shop-name", "#shop-broadcast"]
    .forEach((selector) => setDisabled(document.querySelector(selector), retreating || Boolean(duelLockReason), shopDisabledReason));
  setDisabled(document.querySelector("#shop-name-toggle"), retreating || Boolean(duelLockReason), shopDisabledReason);
  setDisabled(document.querySelector("#personal-shop-form button[type='submit']"), retreating || Boolean(duelLockReason), shopDisabledReason);
  const officialRecycleDisabledReason = retreating ? "闭关期间无法进行官方回收。" : duelLockReason;
  ["#official-recycle-kind", "#official-recycle-item-ref", "#official-recycle-quantity"]
    .forEach((selector) => setDisabled(document.querySelector(selector), retreating || Boolean(duelLockReason), officialRecycleDisabledReason));
  setDisabled(document.querySelector("#official-recycle-form button[type='submit']"), retreating || Boolean(duelLockReason), officialRecycleDisabledReason);
  const auctionDisabledReason = retreating ? "闭关期间无法发起拍卖。" : duelLockReason;
  ["#auction-item-kind", "#auction-item-ref", "#auction-quantity", "#auction-opening-price", "#auction-bid-increment", "#auction-buyout-price"]
    .forEach((selector) => setDisabled(document.querySelector(selector), retreating || Boolean(duelLockReason), auctionDisabledReason));
  setDisabled(document.querySelector("#personal-auction-form button[type='submit']"), retreating || Boolean(duelLockReason), auctionDisabledReason);
  setDisabled(document.querySelector("#gift-form button[type='submit']"), Boolean(duelLockReason), duelLockReason);
  setDisabled(document.querySelector("#red-envelope-form button[type='submit']"), Boolean(duelLockReason), duelLockReason);

  const auctionFeeDisplay = document.querySelector("#auction-fee-display");
  if (auctionFeeDisplay) {
    auctionFeeDisplay.value = `${Number(settings.auction_fee_percent || 0)}%（后台设定）`;
  }
  const auctionDurationDisplay = document.querySelector("#auction-duration-display");
  if (auctionDurationDisplay) {
    auctionDurationDisplay.value = `${Number(settings.auction_duration_minutes || 60)} 分钟`;
  }

  renderArtifactList(bundle.artifacts || [], retreating, equipLimit, equippedArtifacts.length);
  renderTalismanList(bundle.talismans || [], retreating);
  renderPillList(bundle.pills || [], retreating);
  renderOfficialShop(bundle.official_shop || [], retreating);
  renderOfficialRecyclePanel(bundle, retreating);
  renderPersonalShop(bundle.personal_shop || []);
  renderCommunityShop(bundle.community_shop || [], retreating);
  renderInventorySelect();
  renderAuctionInventorySelect();
  renderPersonalAuctions(bundle.personal_auctions || []);
  renderCommunityAuctions(bundle.community_auctions || []);
  renderJournalArea(bundle);
  syncAdminEntry(bundle);
  syncUserTaskComposer();
};

function titleEffectSummary(effects = {}) {
  const rows = [];
  if (Number(effects.attack_bonus || 0)) rows.push(`攻击 ${effects.attack_bonus}`);
  if (Number(effects.defense_bonus || 0)) rows.push(`防御 ${effects.defense_bonus}`);
  if (Number(effects.bone_bonus || 0)) rows.push(`根骨 ${effects.bone_bonus}`);
  if (Number(effects.comprehension_bonus || 0)) rows.push(`悟性 ${effects.comprehension_bonus}`);
  if (Number(effects.divine_sense_bonus || 0)) rows.push(`神识 ${effects.divine_sense_bonus}`);
  if (Number(effects.fortune_bonus || 0)) rows.push(`机缘 ${effects.fortune_bonus}`);
  if (Number(effects.qi_blood_bonus || 0)) rows.push(`气血 ${effects.qi_blood_bonus}`);
  if (Number(effects.true_yuan_bonus || 0)) rows.push(`真元 ${effects.true_yuan_bonus}`);
  if (Number(effects.body_movement_bonus || 0)) rows.push(`身法 ${effects.body_movement_bonus}`);
  if (Number(effects.duel_rate_bonus || 0)) rows.push(`斗法 ${effects.duel_rate_bonus}%`);
  if (Number(effects.cultivation_bonus || 0)) rows.push(`修炼 ${effects.cultivation_bonus}`);
  if (Number(effects.breakthrough_bonus || 0)) rows.push(`突破 ${effects.breakthrough_bonus}`);
  return rows.join(" · ") || "暂无额外效果";
}

function renderTitleAchievementArea(bundle) {
  const currentRoot = document.querySelector("#current-title-summary");
  const titleRoot = document.querySelector("#title-list");
  const achievementRoot = document.querySelector("#achievement-list");
  if (!currentRoot || !titleRoot || !achievementRoot) return;

  const currentTitle = bundle.current_title || null;
  const effectiveStats = bundle.effective_stats || {};
  const charisma = Number(effectiveStats.charisma ?? bundle.profile?.charisma ?? 0);
  const karma = Number(effectiveStats.karma ?? bundle.profile?.karma ?? 0);
  const destinyHint = "魅力会压低官坊成交价与坊市播报成本，因果会抬高突破把握、委托收益与秘境趋吉避凶。";
  currentRoot.innerHTML = currentTitle ? `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${titleColoredNameHtml(currentTitle.name, currentTitle.color)}</strong>
        <span class="badge badge--normal">已佩戴</span>
      </div>
      <p>${escapeHtml(currentTitle.description || "这道名帖已经烙印在你的修仙名帖上。")}</p>
      <p>${escapeHtml(titleEffectSummary(currentTitle.resolved_effects || currentTitle))}</p>
      <p>名帖气运：魅力 ${escapeHtml(charisma)} · 因果 ${escapeHtml(karma)}</p>
      <p class="muted">${escapeHtml(destinyHint)}</p>
      <div class="inline-action-buttons">
        <button type="button" class="ghost" data-title-clear="1">暂不佩戴</button>
      </div>
    </article>
  ` : `<article class="stack-item"><strong>当前未佩戴称号</strong><p>获得称号后可在这里切换展示与效果。</p><p>名帖气运：魅力 ${escapeHtml(charisma)} · 因果 ${escapeHtml(karma)}</p><p class="muted">${escapeHtml(destinyHint)}</p></article>`;

  const titles = bundle.titles || [];
  if (!titles.length) {
    titleRoot.innerHTML = `<article class="stack-item"><strong>尚未获得称号</strong><p>后续可通过管理员发放或成就奖励获得新称号。</p></article>`;
  } else {
    titleRoot.innerHTML = titles.map((row) => {
      const title = row.title || {};
      return `
        <article class="stack-item">
          <div class="stack-item-head">
            <strong>${titleColoredNameHtml(title.name || "未命名称号", title.color)}</strong>
            <span class="badge badge--normal">${title.equipped ? "佩戴中" : "已拥有"}</span>
          </div>
          <p>${escapeHtml(title.description || "暂无称号描述")}</p>
          <p>${escapeHtml(titleEffectSummary(title.resolved_effects || title))}</p>
          <div class="inline-action-buttons">
            <button type="button" data-title-equip="${title.id}" ${title.equipped ? "disabled" : ""}>${title.equipped ? "当前佩戴" : "佩戴称号"}</button>
          </div>
        </article>
      `;
    }).join("");
  }

  const achievements = bundle.achievements || [];
  if (!achievements.length) {
    achievementRoot.innerHTML = `<article class="stack-item"><strong>当前没有已配置成就</strong><p>管理员在后台创建成就后，这里会展示你的进度。</p></article>`;
    return;
  }
  achievementRoot.innerHTML = achievements.map((row) => `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(row.name || "未命名成就")}</strong>
        <span class="badge badge--normal">${row.unlocked ? "已达成" : `${escapeHtml(row.current_value || 0)} / ${escapeHtml(row.target_value || 0)}`}</span>
      </div>
      <p>${escapeHtml(row.description || (row.metric_label ? `追踪 ${row.metric_label}` : "暂无成就描述"))}</p>
      <p>条件：${escapeHtml(row.metric_label || row.metric_key)} 达到 ${escapeHtml(row.target_value || 0)}，当前进度 ${escapeHtml(row.current_value || 0)}。</p>
      <p>奖励：${escapeHtml(row.reward_summary || "无额外奖励")}</p>
    </article>
  `).join("");
}

function renderMentorshipArea(bundle) {
  const selfRoot = document.querySelector("#mentorship-self-summary");
  const mentorRoot = document.querySelector("#mentorship-mentor-current");
  const discipleRoot = document.querySelector("#mentorship-disciple-list");
  const incomingRoot = document.querySelector("#mentorship-incoming-list");
  const outgoingRoot = document.querySelector("#mentorship-outgoing-list");
  if (!selfRoot || !mentorRoot || !discipleRoot || !incomingRoot || !outgoingRoot) return;

  const mentorship = bundle?.mentorship || {};
  const selfProfile = mentorship.self_profile || {};
  const mentorRelation = mentorship.mentor_relation || null;
  const discipleRelations = mentorship.disciple_relations || [];
  const incomingRequests = mentorship.incoming_requests || [];
  const outgoingRequests = mentorship.outgoing_requests || [];

  selfRoot.innerHTML = `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(selfProfile.display_name_with_title || selfProfile.display_label || bundle?.profile?.display_label || "当前角色")}</strong>
        <span class="badge badge--normal">可收徒 ${escapeHtml(mentorship.used_slots || 0)} / ${escapeHtml(mentorship.mentor_capacity || 0)}</span>
      </div>
      <p>${escapeHtml(mentorship.request_hint || "当前可处理师徒相关事务。")}</p>
      <div class="item-tags">
        <span class="tag">当前师尊 ${escapeHtml(mentorRelation?.mentor_profile?.display_label || "暂无")}</span>
        <span class="tag">门下弟子 ${escapeHtml(discipleRelations.length)}</span>
        <span class="tag">剩余名额 ${escapeHtml(mentorship.available_slots || 0)}</span>
      </div>
    </article>
  `;

  if (!mentorRelation) {
    mentorRoot.innerHTML = `<article class="stack-item"><strong>当前没有师尊</strong><p>可在下方搜索高境界道友，递上拜师申请。</p></article>`;
  } else {
    const mentorProfile = mentorRelation.mentor_profile || {};
    mentorRoot.innerHTML = `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>师尊：${escapeHtml(mentorProfile.display_name_with_title || mentorProfile.display_label || "未具名师尊")}</strong>
          <span class="badge badge--normal">${escapeHtml(mentorRelation.bond_label || "初结师缘")}</span>
        </div>
        <p>境界 ${escapeHtml(mentorProfile.realm_text || "未知")} · 战力 ${escapeHtml(mentorProfile.combat_power || 0)}</p>
        <p>师徒缘 ${escapeHtml(mentorRelation.bond_value || 0)} ｜ 传道 ${escapeHtml(mentorRelation.teach_count || 0)} 次 ｜ 问道 ${escapeHtml(mentorRelation.consult_count || 0)} 次</p>
        <p>${escapeHtml(mentorRelation.graduation_hint || "完成传道、问道与境界成长后，可申请出师。")}</p>
        ${mentorRelation.consult_reason ? `<p class="reason-text">${escapeHtml(mentorRelation.consult_reason)}</p>` : ""}
        <div class="inline-action-buttons">
          <button type="button" data-mentorship-consult="1" ${mentorRelation.can_consult_today ? "" : "disabled"}>今日问道</button>
          <button type="button" class="ghost" data-mentorship-graduate-target="${escapeHtml(mentorProfile.tg || 0)}" ${mentorRelation.graduation_ready ? "" : "disabled"}>申请出师</button>
          <button type="button" class="ghost" data-mentorship-dissolve-target="${escapeHtml(mentorProfile.tg || 0)}">离开师门</button>
        </div>
      </article>
    `;
  }

  if (!discipleRelations.length) {
    discipleRoot.innerHTML = `<article class="stack-item"><strong>当前没有门下弟子</strong><p>可搜索后发出收徒邀请，建立自己的传承。</p></article>`;
  } else {
    discipleRoot.innerHTML = discipleRelations.map((relation) => {
      const discipleProfile = relation.disciple_profile || {};
      return `
        <article class="stack-item">
          <div class="stack-item-head">
            <strong>弟子：${escapeHtml(discipleProfile.display_name_with_title || discipleProfile.display_label || "未具名弟子")}</strong>
            <span class="badge badge--normal">${escapeHtml(relation.bond_label || "初结师缘")}</span>
          </div>
          <p>境界 ${escapeHtml(discipleProfile.realm_text || "未知")} · 战力 ${escapeHtml(discipleProfile.combat_power || 0)}</p>
          <p>师徒缘 ${escapeHtml(relation.bond_value || 0)} ｜ 传道 ${escapeHtml(relation.teach_count || 0)} 次 ｜ 问道 ${escapeHtml(relation.consult_count || 0)} 次</p>
          <p>${escapeHtml(relation.graduation_hint || "继续传道与历练，等待出师。")}</p>
          ${relation.teach_reason ? `<p class="reason-text">${escapeHtml(relation.teach_reason)}</p>` : ""}
          <div class="inline-action-buttons">
            <button type="button" data-mentorship-teach="${escapeHtml(discipleProfile.tg || 0)}" ${relation.can_teach_today ? "" : "disabled"}>今日传道</button>
            <button type="button" class="ghost" data-mentorship-graduate-target="${escapeHtml(discipleProfile.tg || 0)}" ${relation.graduation_ready ? "" : "disabled"}>准许出师</button>
            <button type="button" class="ghost" data-mentorship-dissolve-target="${escapeHtml(discipleProfile.tg || 0)}">解除关系</button>
          </div>
        </article>
      `;
    }).join("");
  }

  if (!incomingRequests.length) {
    incomingRoot.innerHTML = `<article class="stack-item"><strong>没有待处理名帖</strong><p>别人发来的拜师申请或收徒邀请会显示在这里。</p></article>`;
  } else {
    incomingRoot.innerHTML = incomingRequests.map((item) => `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(item.sponsor_profile?.display_label || "匿名道友")}</strong>
          <span class="badge badge--normal">${escapeHtml(item.sponsor_role_label || "师徒拜帖")}</span>
        </div>
        <p>拟定关系：师尊 ${escapeHtml(item.mentor_profile?.display_label || "未知")} ｜ 徒弟 ${escapeHtml(item.disciple_profile?.display_label || "未知")}</p>
        <p>到期：${escapeHtml(formatDate(item.expires_at))}</p>
        ${item.message ? `<p>${escapeHtml(item.message)}</p>` : ""}
        <div class="inline-action-buttons">
          <button type="button" data-mentorship-request-action="accept" data-mentorship-request-id="${escapeHtml(item.id)}">同意</button>
          <button type="button" class="ghost" data-mentorship-request-action="reject" data-mentorship-request-id="${escapeHtml(item.id)}">婉拒</button>
        </div>
      </article>
    `).join("");
  }

  if (!outgoingRequests.length) {
    outgoingRoot.innerHTML = `<article class="stack-item"><strong>没有你发出的待处理名帖</strong><p>你递出的拜帖，在对方处理前会暂存这里。</p></article>`;
  } else {
    outgoingRoot.innerHTML = outgoingRequests.map((item) => `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(item.counterpart_profile?.display_label || "匿名道友")}</strong>
          <span class="badge badge--normal">${escapeHtml(item.sponsor_role_label || "师徒拜帖")}</span>
        </div>
        <p>到期：${escapeHtml(formatDate(item.expires_at))}</p>
        ${item.message ? `<p>${escapeHtml(item.message)}</p>` : ""}
        <div class="inline-action-buttons">
          <button type="button" class="ghost" data-mentorship-request-action="cancel" data-mentorship-request-id="${escapeHtml(item.id)}">撤回拜帖</button>
        </div>
      </article>
    `).join("");
  }

  syncMentorshipRequestComposer(bundle);
}

function marriageDisplayName(profile = {}, fallback = "未具名道友") {
  return profile.display_name_with_title || profile.display_label || fallback;
}

function renderMarriageArea(bundle) {
  const selfRoot = document.querySelector("#marriage-self-summary");
  const currentRoot = document.querySelector("#marriage-current-summary");
  const incomingRoot = document.querySelector("#marriage-incoming-list");
  const outgoingRoot = document.querySelector("#marriage-outgoing-list");
  if (!selfRoot || !currentRoot || !incomingRoot || !outgoingRoot) return;

  const marriage = bundle?.marriage || {};
  const selfProfile = marriage.self_profile || bundle?.profile || {};
  const currentMarriage = marriage.current_marriage || null;
  const incomingRequests = marriage.incoming_requests || [];
  const outgoingRequests = marriage.outgoing_requests || [];

  selfRoot.innerHTML = `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(marriageDisplayName(selfProfile, "当前角色"))}</strong>
        <span class="badge badge--normal">${escapeHtml(marriage.gender_label || "未设性别")}</span>
      </div>
      <p>${escapeHtml(marriage.request_hint || "当前可处理姻缘事务。")}</p>
      <div class="item-tags">
        <span class="tag">性别 ${escapeHtml(marriage.gender_label || "未设置")}</span>
        <span class="tag">道侣 ${escapeHtml(currentMarriage?.spouse_profile?.display_label || "暂无")}</span>
        <span class="tag">共享灵石 ${escapeHtml(currentMarriage?.shared_spiritual_stone_total ?? bundle?.profile?.spiritual_stone ?? 0)}</span>
      </div>
    </article>
  `;

  if (!currentMarriage) {
    currentRoot.innerHTML = `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>当前暂无道侣</strong>
          <span class="badge badge--normal">待结缘</span>
        </div>
        <p>${escapeHtml(marriage.shared_assets_hint || "结为道侣后，灵石与背包会自动共享。")}</p>
      </article>
    `;
  } else {
    const spouseProfile = currentMarriage.spouse_profile || {};
    currentRoot.innerHTML = `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>道侣：${escapeHtml(marriageDisplayName(spouseProfile, "未具名道侣"))}</strong>
          <span class="badge badge--normal">${escapeHtml(currentMarriage.bond_label || "新缔良缘")}</span>
        </div>
        <p>境界 ${escapeHtml(spouseProfile.realm_text || "未知")} · 战力 ${escapeHtml(spouseProfile.combat_power || 0)}</p>
        <p>缘分 ${escapeHtml(currentMarriage.bond_value || 0)} ｜ 双修 ${escapeHtml(currentMarriage.dual_cultivation_count || 0)} 次</p>
        <p>${escapeHtml(marriage.shared_assets_hint || "婚后灵石与背包已共享。")}</p>
        ${currentMarriage.dual_cultivate_reason ? `<p class="reason-text">${escapeHtml(currentMarriage.dual_cultivate_reason)}</p>` : ""}
        <div class="inline-action-buttons">
          <button type="button" data-marriage-dual-cultivate="1" ${currentMarriage.can_dual_cultivate_today ? "" : "disabled"}>今日双修</button>
          <button type="button" class="ghost" data-marriage-divorce="1">和离分家</button>
        </div>
      </article>
    `;
  }

  if (!incomingRequests.length) {
    incomingRoot.innerHTML = `<article class="stack-item"><strong>没有待处理结缘信物</strong><p>别人发来的道侣请求会显示在这里。</p></article>`;
  } else {
    incomingRoot.innerHTML = incomingRequests.map((item) => `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(item.sponsor_profile?.display_label || "匿名道友")}</strong>
          <span class="badge badge--normal">待你回应</span>
        </div>
        <p>对方性别：${escapeHtml(item.sponsor_profile?.gender_label || "未设置")} ｜ 到期：${escapeHtml(formatDate(item.expires_at))}</p>
        ${item.message ? `<p>${escapeHtml(item.message)}</p>` : ""}
        <div class="inline-action-buttons">
          <button type="button" data-marriage-request-action="accept" data-marriage-request-id="${escapeHtml(item.id)}">同意</button>
          <button type="button" class="ghost" data-marriage-request-action="reject" data-marriage-request-id="${escapeHtml(item.id)}">婉拒</button>
        </div>
      </article>
    `).join("");
  }

  if (!outgoingRequests.length) {
    outgoingRoot.innerHTML = `<article class="stack-item"><strong>没有你送出的结缘信物</strong><p>你发出的道侣请求，在对方处理前会保存在这里。</p></article>`;
  } else {
    outgoingRoot.innerHTML = outgoingRequests.map((item) => `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(item.counterpart_profile?.display_label || "匿名道友")}</strong>
          <span class="badge badge--normal">待对方回应</span>
        </div>
        <p>对方性别：${escapeHtml(item.counterpart_profile?.gender_label || "未设置")} ｜ 到期：${escapeHtml(formatDate(item.expires_at))}</p>
        ${item.message ? `<p>${escapeHtml(item.message)}</p>` : ""}
        <div class="inline-action-buttons">
          <button type="button" class="ghost" data-marriage-request-action="cancel" data-marriage-request-id="${escapeHtml(item.id)}">撤回信物</button>
        </div>
      </article>
    `).join("");
  }

  syncGenderComposer(bundle);
  syncMarriageRequestComposer(bundle);
}

function furnaceDisplayName(profile = {}, fallback = "未具名道友") {
  return profile.display_name_with_title || profile.display_label || profile.master_name || fallback;
}

function renderFurnaceArea(bundle) {
  const selfRoot = document.querySelector("#furnace-self-summary");
  const rosterRoot = document.querySelector("#furnace-roster-list");
  if (!selfRoot || !rosterRoot) return;

  const profile = bundle?.profile || {};
  const masterProfile = bundle?.master_profile || null;
  const furnaceRows = Array.isArray(bundle?.slave_profiles) ? bundle.slave_profiles : [];
  const harvestPercent = Number(bundle?.settings?.furnace_harvest_cultivation_percent ?? 10);
  const challengeTime = profile.servitude_challenge_available_at
    ? formatDate(profile.servitude_challenge_available_at)
    : "可随时发起脱离挑战";

  if (profile.master_name) {
    selfRoot.innerHTML = `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(furnaceDisplayName(profile, "当前角色"))}</strong>
          <span class="badge badge--normal">炉鼎</span>
        </div>
        <p>你当前归于 ${escapeHtml(profile.master_name)} 名下，主人每天可对你采补一次。</p>
        <div class="item-tags">
          <span class="tag">当前境界 ${escapeHtml(profile.realm_stage || "炼气")}${escapeHtml(profile.realm_layer || 0)}层</span>
          <span class="tag">脱离冷却 ${escapeHtml(challengeTime)}</span>
          <span class="tag">采补比例 ${escapeHtml(harvestPercent)}%</span>
        </div>
        <p class="muted">采补会按你当前境界的修为门槛折算给主人修为，不是简单等额转移。</p>
      </article>
    `;
    rosterRoot.innerHTML = `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>主人：${escapeHtml(furnaceDisplayName(masterProfile || {}, profile.master_name || "未具名主人"))}</strong>
          <span class="badge badge--normal">归属中</span>
        </div>
        <p>境界 ${escapeHtml(masterProfile?.realm_stage || "未知")}${escapeHtml(masterProfile?.realm_layer || "-")}层</p>
        <p>若想解除当前归属，需要通过炉鼎对决向主人发起脱离挑战。</p>
      </article>
    `;
    return;
  }

  if (furnaceRows.length) {
    selfRoot.innerHTML = `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(furnaceDisplayName(profile, "当前角色"))}</strong>
          <span class="badge badge--normal">主人</span>
        </div>
        <p>你名下共有 ${escapeHtml(furnaceRows.length)} 名炉鼎，每天可对每名炉鼎采补一次。</p>
        <div class="item-tags">
          <span class="tag">采补比例 ${escapeHtml(harvestPercent)}%</span>
          <span class="tag">炉鼎数量 ${escapeHtml(furnaceRows.length)}</span>
          <span class="tag">今日可操作 ${escapeHtml(furnaceRows.filter((item) => item.can_harvest_today).length)}</span>
        </div>
        <p class="muted">采补收益会按主人与炉鼎各自当前境界门槛折算。</p>
      </article>
    `;
    rosterRoot.innerHTML = furnaceRows.map((item) => {
      const available = Boolean(item.can_harvest_today);
      const gain = Number(item.estimated_harvest_gain || 0);
      const loss = Number(item.estimated_harvest_loss || 0);
      const reason = available ? "" : fallbackReason(item.harvest_reason, "当前暂不可采补。");
      return `
        <article class="stack-item">
          <div class="stack-item-head">
            <strong>${escapeHtml(furnaceDisplayName(item, item.display_label || `TG ${item.tg || 0}`))}</strong>
            <span class="badge badge--normal">${available ? "今日可采补" : "暂不可采补"}</span>
          </div>
          <p>境界 ${escapeHtml(item.realm_text || `${item.realm_stage || "炼气"}${item.realm_layer || 0}层`)} · 当前修为 ${escapeHtml(item.cultivation ?? 0)}</p>
          <div class="item-tags">
            <span class="tag">抽取比例 ${escapeHtml(item.harvest_percent ?? harvestPercent)}%</span>
            <span class="tag">预计主人 +${escapeHtml(gain)}</span>
            <span class="tag">预计炉鼎 -${escapeHtml(loss)}</span>
          </div>
          ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : `<p>本次可抽取其当前修为 ${escapeHtml(loss)} 点，折算为你 ${escapeHtml(gain)} 点修为。</p>`}
          <div class="inline-action-buttons">
            <button type="button" data-furnace-harvest-target="${escapeHtml(item.tg || 0)}" ${available ? "" : "disabled"}>${available ? "今日采补" : "今日不可采补"}</button>
          </div>
        </article>
      `;
    }).join("");
    return;
  }

  selfRoot.innerHTML = `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(furnaceDisplayName(profile, "当前角色"))}</strong>
        <span class="badge badge--normal">自由身</span>
      </div>
      <p>当前未与任何人形成炉鼎因果，也没有名下炉鼎。</p>
      <div class="item-tags">
        <span class="tag">采补比例 ${escapeHtml(harvestPercent)}%</span>
        <span class="tag">当前状态 自由</span>
      </div>
    </article>
  `;
  rosterRoot.innerHTML = `<article class="stack-item"><strong>暂无可采补对象</strong><p>只有通过炉鼎对决建立关系后，主人才可每天进行一次采补。</p></article>`;
}

const baseRenderProfileWithTitles = renderProfile;
renderProfile = function renderProfileWithTitles(bundle) {
  baseRenderProfileWithTitles(bundle);
  const consented = Boolean(bundle?.profile?.consented);
  ensureSectionState("#title-card", consented);
  if (!consented) {
    syncFoldToolbar();
    return;
  }
  const currentTitleName = bundle.current_title?.name || "未佩戴称号";
  const currentTitleColor = bundle.current_title?.color || "";
  const heroRootPill = document.querySelector("#hero-root-pill");
  if (heroRootPill) {
    heroRootPill.innerHTML = `称号 · ${titleColoredNameHtml(currentTitleName, currentTitleColor)}`;
  }
  const rootText = document.querySelector("#root-text");
  if (rootText) {
    const profile = bundle.profile || {};
    const rootLabel = profile.root_text || profileRootText(profile);
    const rootBonus = Number(profile.root_bonus || 0);
    rootText.innerHTML = `称号：${titleColoredNameHtml(currentTitleName, currentTitleColor)} · 灵根：${escapeHtml(rootLabel)}，五行修正 ${rootBonus >= 0 ? "+" : ""}${escapeHtml(rootBonus)}%`;
  }
  const profileGrid = document.querySelector("#profile-grid");
  if (profileGrid) {
    profileGrid.insertAdjacentHTML(
      "beforeend",
      `<article class="profile-item"><span>当前称号</span><strong>${titleColoredNameHtml(currentTitleName, currentTitleColor)}</strong></article>`
      + `<article class="profile-item"><span>成就解锁</span><strong>${escapeHtml(bundle.achievement_unlocked_count || 0)} / ${escapeHtml(bundle.achievement_total_count || 0)}</strong></article>`
    );
  }
  renderTitleAchievementArea(bundle);
  syncFoldToolbar();
};

document.addEventListener("click", async (event) => {
  const equipButton = event.target.closest("[data-title-equip]");
  const clearButton = event.target.closest("[data-title-clear]");
  if (!equipButton && !clearButton) return;
  const button = equipButton || clearButton;
  try {
    await runButtonAction(button, clearButton ? "卸下中..." : "佩戴中...", async () => {
      const titleId = clearButton ? null : Number(equipButton.dataset.titleEquip || 0) || null;
      await postJson("/plugins/xiuxian/api/title/equip", { title_id: titleId });
      await refreshBundle();
      await popup("称号已更新", clearButton ? "你已经暂时卸下当前称号。" : "修仙名帖上的称号已经切换。");
    });
  } catch (error) {
    await popup("操作失败", normalizeError(error, "称号切换失败。"), "error");
  }
});

const renderTitleAchievementAreaBase = renderTitleAchievementArea;
renderTitleAchievementArea = function renderTitleAchievementAreaEnhanced(bundle) {
  renderTitleAchievementAreaBase(bundle);
  const syncButton = document.querySelector("#title-group-sync-btn");
  const syncHint = document.querySelector("#title-sync-hint");
  const currentTitleName = bundle.current_title?.name || "";
  if (syncHint) {
    syncHint.textContent = currentTitleName
      ? `当前佩戴「${currentTitleName}」，若你在群内拥有管理员身份，可尝试同步到群头衔。`
      : "请先佩戴称号，再同步到群头衔。";
  }
  if (syncButton) {
    setDisabled(syncButton, !currentTitleName, currentTitleName ? "" : "当前未佩戴称号");
  }
};

const renderTechniqueAreaBase = renderTechniqueArea;
renderTechniqueArea = function renderTechniqueAreaEnhanced(bundle) {
  renderTechniqueAreaBase(bundle);
  const hint = document.querySelector("#technique-discovery-hint");
  if (!hint) return;
  const owned = Number(bundle.technique_owned_count ?? (bundle.techniques || []).length ?? 0);
  const total = Number(bundle.technique_total_count ?? 0);
  const capacity = Number(bundle.profile?.technique_capacity ?? 0);
  hint.textContent = `已掌握 ${owned}${total ? ` / ${total}` : ""} 门功法，当前最多可启用 ${capacity} 门功法位。功法需要先探索获得，是否切换由你自行决定。`;
};

const renderCraftAreaBase = renderCraftArea;
renderCraftArea = function renderCraftAreaEnhanced(bundle) {
  renderCraftAreaBase(bundle);
  const hint = document.querySelector("#recipe-discovery-hint");
  const synthesisRoot = document.querySelector("#recipe-fragment-synthesis-list");
  const discovered = Number(bundle.recipe_discovered_count ?? (bundle.recipes || []).length ?? 0);
  const total = Number(bundle.recipe_total_count ?? 0);
  if (hint) {
    hint.textContent = `已发现 ${discovered}${total ? ` / ${total}` : ""} 张配方。残页可先参悟成完整配方，再进行炼制。`;
  }
  if (!synthesisRoot) return;
  const syntheses = bundle.recipe_fragment_syntheses || [];
  synthesisRoot.innerHTML = "";
  if (!syntheses.length) {
    synthesisRoot.innerHTML = `<article class="stack-item"><strong>暂无可参悟配方</strong><p>尚未持有对应残页，或相关配方都已掌握。</p></article>`;
    return;
  }
  for (const item of syntheses) {
    const disabled = !item.can_synthesize;
    const reason = disabled ? `缺少 ${item.required_material_name || "残页"}，当前仅有 ${item.owned_quantity || 0} / ${item.required_quantity || 1}。` : "";
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.recipe_name || "未知配方")}</strong>
        <span class="badge badge--normal">${escapeHtml(item.recipe_kind_label || item.recipe_kind || "配方")}</span>
      </div>
      <p>参悟后解锁：${escapeHtml(item.result_item_name || item.result_item?.name || "成品")}</p>
      <div class="info-grid">
        <article class="info-chip">
          <span>所需残页</span>
          <strong>${escapeHtml(item.required_material_name || "残页")} × ${escapeHtml(item.required_quantity || 1)}</strong>
        </article>
        <article class="info-chip">
          <span>当前持有</span>
          <strong>${escapeHtml(item.owned_quantity || 0)}</strong>
        </article>
      </div>
      ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : `<p>残页足够后可直接参悟为完整配方。</p>`}
      <button type="button" data-recipe-synthesis-id="${item.recipe_id}" ${disabled ? "disabled" : ""}>${escapeHtml(disabled ? "残页不足" : "参悟配方")}</button>
    `;
    synthesisRoot.appendChild(card);
  }
};

const renderProfileWithDiscoveriesBase = renderProfile;
renderProfile = function renderProfileWithDiscoveries(bundle) {
  renderProfileWithDiscoveriesBase(bundle);
  if (!bundle?.profile?.consented) return;
  const statusText = document.querySelector("#status-text");
  if (statusText) {
    const name = bundle.profile?.display_name_with_title || bundle.profile?.display_label || "道友";
    statusText.textContent = `${name} 当前已踏入仙途，可展开下方模块继续修炼、探索与经营。`;
  }
  const profileGrid = document.querySelector("#profile-grid");
  if (profileGrid) {
    const activeSets = (bundle.active_artifact_sets || []).filter((item) => item.active);
    const activeSetText = activeSets.length
      ? activeSets.map((item) => `${item.name}(${item.equipped_count}/${item.required_count})`).join("、")
      : "暂无激活";
    const techniqueCount = Number(bundle.technique_owned_count ?? (bundle.techniques || []).length ?? 0);
    profileGrid.insertAdjacentHTML(
      "beforeend",
      `<article class="profile-item"><span>已掌握功法</span><strong>${escapeHtml(techniqueCount)}</strong></article>`
      + `<article class="profile-item"><span>法宝套装</span><strong>${escapeHtml(activeSetText)}</strong></article>`
    );
  }
};

document.querySelector("#title-group-sync-btn")?.addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    await runButtonAction(button, "同步中...", async () => {
      await postJson("/plugins/xiuxian/api/title/group-sync", {});
      await refreshBundle();
      await popup("同步成功", "当前佩戴称号已尝试同步到群组头衔。若群内未生效，请确认你是否为该群管理员，以及 bot 是否拥有修改管理员头衔的权限。");
    });
  } catch (error) {
    await popup("同步失败", normalizeError(error, "群头衔同步失败。"), "error");
  }
});

const renderArtifactListBase = renderArtifactList;
renderArtifactList = function renderArtifactListEnhanced(items, retreating, equipLimit, equippedCount) {
  renderArtifactListBase(items, retreating, equipLimit, equippedCount);
  const root = document.querySelector("#artifact-list");
  if (!root) return;
  root.innerHTML = "";
  const artifactQuery = inventorySearchValue("#artifact-search");
  const rows = sortInventoryRowsByQuality(
    (items || []).filter((row) => inventoryMatches(row.artifact || {}, artifactQuery, ["artifact_set_name", "min_realm_stage"])),
    (row) => row.artifact || {},
    "rarity_level"
  );
  if (!rows.length) {
    root.innerHTML = (items || []).length
      ? `<article class="stack-item"><strong>未找到匹配法宝</strong><p>可按名称、品质、槽位或套装继续检索。</p></article>`
      : `<article class="stack-item"><strong>暂无法宝</strong><p>管理后台发放或在${escapeHtml(officialShopName())}购买后会出现在这里。</p></article>`;
    return;
  }
  for (const row of rows) {
    const item = row.artifact || {};
    const effects = item.resolved_effects || {};
    const disabled = !item.usable || retreating;
    const bindableQuantity = Number(row.unbound_quantity ?? row.quantity ?? 0);
    const unbindableQuantity = Number(row.bound_quantity ?? 0);
    const canBind = bindableQuantity > 0;
    const canUnbind = unbindableQuantity > 0;
    const unbindCost = Number(state.profileBundle?.settings?.equipment_unbind_cost || 0);
    const reason = item.equipped
      ? ""
      : fallbackReason(item.unusable_reason, retreating ? "闭关期间无法切换法宝" : "当前不满足装备条件");
    const activeSet = item.artifact_set_name ? `${item.artifact_set_name}` : "无套装";
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.name || "未命名法宝")}</strong>
        <span class="badge badge--normal">x${escapeHtml(row.quantity ?? 0)}</span>
      </div>
      <p>${escapeHtml(item.description || "暂无描述")}</p>
      <div class="item-tags">
        <span class="tag ${item.artifact_type === "support" ? "support" : ""}">${escapeHtml(item.artifact_type_label || artifactTypeLabel(item.artifact_type))}</span>
        <span class="tag">${escapeHtml(item.equip_slot_label || item.equip_slot || "槽位未定")}</span>
        <span class="tag">${escapeHtml(item.artifact_role_label || item.artifact_role || "定位未定")}</span>
        <span class="tag">${escapeHtml(activeSet)}</span>
        ${qualityBadgeHtml(item.rarity || "凡品", item.quality_color, "tag")}
        ${unbindableQuantity > 0 ? `<span class="tag">已绑定 ${escapeHtml(unbindableQuantity)}</span>` : ""}
        ${bindableQuantity > 0 ? `<span class="tag">未绑定 ${escapeHtml(bindableQuantity)}</span>` : ""}
        ${itemAffixTags(item, effects)}
      </div>
      <p>境界要求：${escapeHtml(item.min_realm_stage ? `${item.min_realm_stage}${item.min_realm_layer}层` : "无限制")}</p>
      <p>可交易：${escapeHtml(row.tradeable_quantity ?? 0)} ｜ 可提交：${escapeHtml(row.consumable_quantity ?? 0)}</p>
      ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : ""}
      <div class="inline-action-buttons">
        <button type="button" data-equip-id="${item.id}" ${disabled ? "disabled" : ""}>${escapeHtml(item.action_label || (item.equipped ? "卸下法宝" : "装备法宝"))}</button>
        <button type="button" class="ghost" data-artifact-bind-id="${item.id}" ${canBind ? "" : "disabled"}>绑定1件</button>
        <button type="button" class="ghost" data-artifact-unbind-id="${item.id}" ${canUnbind ? "" : "disabled"}>解绑1件${unbindCost > 0 ? `（${escapeHtml(unbindCost)}灵石）` : ""}</button>
      </div>
    `;
    root.appendChild(card);
  }
};

function sectRequirementSummary(sect = {}) {
  const rows = [];
  if (sect.min_realm_stage) rows.push(`境界 ${sect.min_realm_stage}${sect.min_realm_layer || 1}层`);
  if (Number(sect.min_bone || 0) > 0) rows.push(`根骨 ${sect.min_bone}`);
  if (Number(sect.min_comprehension || 0) > 0) rows.push(`悟性 ${sect.min_comprehension}`);
  if (Number(sect.min_divine_sense || 0) > 0) rows.push(`神识 ${sect.min_divine_sense}`);
  if (Number(sect.min_fortune || 0) > 0) rows.push(`机缘 ${sect.min_fortune}`);
  if (Number(sect.min_charisma || 0) > 0) rows.push(`魅力 ${sect.min_charisma}`);
  if (Number(sect.min_willpower || 0) > 0) rows.push(`心志 ${sect.min_willpower}`);
  if (Number(sect.min_karma || 0) > 0) rows.push(`因果 ${sect.min_karma}`);
  if (Number(sect.min_body_movement || 0) > 0) rows.push(`身法 ${sect.min_body_movement}`);
  if (Number(sect.min_stone || 0) > 0) rows.push(`灵石 ${sect.min_stone}`);
  return rows.join(" · ") || "几乎无门槛";
}

function sectBonusSummary(sect = {}, role = null) {
  const rows = [];
  const attack = Number(sect.attack_bonus || 0) + Number(role?.attack_bonus || 0);
  const defense = Number(sect.defense_bonus || 0) + Number(role?.defense_bonus || 0);
  const duel = Number(sect.duel_rate_bonus || 0) + Number(role?.duel_rate_bonus || 0);
  const cultivation = Number(sect.cultivation_bonus || 0) + Number(role?.cultivation_bonus || 0);
  const fortune = Number(sect.fortune_bonus || 0);
  const movement = Number(sect.body_movement_bonus || 0);
  if (attack) rows.push(`攻击 ${attack > 0 ? "+" : ""}${attack}`);
  if (defense) rows.push(`防御 ${defense > 0 ? "+" : ""}${defense}`);
  if (duel) rows.push(`斗法 ${duel > 0 ? "+" : ""}${duel}%`);
  if (cultivation) rows.push(`修炼 ${cultivation > 0 ? "+" : ""}${cultivation}`);
  if (fortune) rows.push(`机缘 ${fortune > 0 ? "+" : ""}${fortune}`);
  if (movement) rows.push(`身法 ${movement > 0 ? "+" : ""}${movement}`);
  return rows.join(" · ") || "暂无额外加成";
}

renderSectArea = function renderSectAreaEnhanced(bundle) {
  const currentRoot = document.querySelector("#sect-current");
  const listRoot = document.querySelector("#sect-list");
  const salaryButton = document.querySelector("#sect-salary-btn");
  const leaveButton = document.querySelector("#sect-leave-btn");
  if (!currentRoot || !listRoot || !salaryButton || !leaveButton) return;

  const current = bundle.current_sect;
  const duelLockReason = currentDuelLockReason(bundle);
  leaveButton.textContent = "叛出宗门";
  currentRoot.innerHTML = "";
  if (current) {
    const role = current.current_role || null;
    const contribution = bundle.profile?.sect_contribution ?? 0;
    currentRoot.innerHTML = `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(current.name)}</strong>
          <span class="badge badge--normal">${escapeHtml(current.camp_label || current.camp || "宗门")}</span>
        </div>
        <p>${escapeHtml(current.description || "暂无宗门简介")}</p>
        <div class="item-tags">
          <span class="tag">职位 ${escapeHtml(role?.role_name || "门下弟子")}</span>
          <span class="tag">成员 ${escapeHtml((current.roster || []).length)}</span>
          <span class="tag">贡献 ${escapeHtml(contribution)}</span>
          <span class="tag">月俸 ${escapeHtml(role?.monthly_salary ?? 0)} 灵石</span>
          ${current.entry_technique_name ? `<span class="tag">入门功法 ${escapeHtml(current.entry_technique_name)}</span>` : ""}
        </div>
        <p>宗门加成：${escapeHtml(sectBonusSummary(current, role))}</p>
        ${current.entry_hint ? `<p>${escapeHtml(current.entry_hint)}</p>` : ""}
      </article>
    `;
    setDisabled(salaryButton, Boolean(duelLockReason), duelLockReason);
    setDisabled(leaveButton, Boolean(duelLockReason), duelLockReason);
  } else {
    currentRoot.innerHTML = `<article class="stack-item"><strong>暂未加入宗门</strong><p>满足门槛后，即可在下方挑选正邪宗门与入门路线。</p></article>`;
    setDisabled(salaryButton, true);
    setDisabled(leaveButton, true);
  }

  listRoot.innerHTML = "";
  const sects = bundle.sects || [];
  if (!sects.length) {
    listRoot.innerHTML = `<article class="stack-item"><strong>暂无可加入宗门</strong></article>`;
    return;
  }

  for (const sect of sects) {
    const disabled = current?.id === sect.id || !sect.joinable;
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(sect.name)}</strong>
        <span class="badge badge--normal">${escapeHtml(sect.camp_label || sect.camp || "宗门")}</span>
      </div>
      <p>${escapeHtml(sect.description || "暂无简介")}</p>
      <div class="item-tags">
        <span class="tag">${escapeHtml(sectRequirementSummary(sect))}</span>
        <span class="tag">成员 ${escapeHtml(sect.member_count ?? 0)}</span>
        ${sect.entry_technique_name ? `<span class="tag">入门赠 ${escapeHtml(sect.entry_technique_name)}</span>` : ""}
      </div>
      <p>宗门加成：${escapeHtml(sectBonusSummary(sect))}</p>
      ${sect.entry_hint ? `<p>${escapeHtml(sect.entry_hint)}</p>` : ""}
      ${disabled && sect.join_reason ? `<p class="reason-text">${escapeHtml(sect.join_reason)}</p>` : ""}
      <button type="button" data-sect-id="${sect.id}" ${disabled ? "disabled" : ""}>${current?.id === sect.id ? "已加入" : "加入宗门"}</button>
    `;
    listRoot.appendChild(card);
  }
};

function commissionRequirementText(item = {}) {
  if (!item.min_realm_stage) return "无门槛";
  return `${item.min_realm_stage}${item.min_realm_layer || 1}层`;
}

function renderCommissionArea(bundle) {
  const root = document.querySelector("#commission-list");
  if (!root) return;
  const commissions = Array.isArray(bundle?.commissions) ? bundle.commissions : [];
  if (!commissions.length) {
    root.innerHTML = `<article class="stack-item"><strong>暂无可承接的坊市委托</strong><p>踏入仙途后，坊市会根据你的境界开放灵石差事。</p></article>`;
    return;
  }

  root.innerHTML = commissions.map((item) => {
    const requirement = commissionRequirementText(item);
    const rewardText = `灵石 ${item.reward_stone_min || 0}-${item.reward_stone_max || 0} · 修为 ${item.reward_cultivation_min || 0}-${item.reward_cultivation_max || 0}`;
    const cooldownText = `${item.cooldown_hours || 0} 小时`;
    const disabled = !item.available;
    const reason = item.available ? "" : fallbackReason(item.reason, "当前暂不可承接该委托。");
    const timeText = item.next_available_at
      ? `下次可接：${formatDate(item.next_available_at)}`
      : (item.last_claimed_at ? `上次完成：${formatDate(item.last_claimed_at)}` : "首次承接无冷却");
    return `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(item.name || "未命名委托")}</strong>
          <span class="badge badge--normal">${disabled ? "冷却/未解锁" : "可接取"}</span>
        </div>
        <p>${escapeHtml(item.summary || item.description || "暂无说明")}</p>
        <div class="item-tags">
          <span class="tag">门槛 ${escapeHtml(requirement)}</span>
          <span class="tag">冷却 ${escapeHtml(cooldownText)}</span>
          <span class="tag">${escapeHtml(rewardText)}</span>
        </div>
        ${item.description ? `<p>${escapeHtml(item.description)}</p>` : ""}
        <p>${escapeHtml(timeText)}</p>
        ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : ""}
        <button type="button" data-commission-key="${escapeHtml(item.key || "")}" ${disabled ? "disabled" : ""}>${disabled ? "暂不可接" : "承接委托"}</button>
      </article>
    `;
  }).join("");
}

const renderProfileWithCommissionBoardBase = renderProfile;
renderProfile = function renderProfileWithCommissionBoard(bundle) {
  renderProfileWithCommissionBoardBase(bundle);
  const consented = Boolean(bundle?.profile?.consented);
  ensureSectionState("#furnace-card", consented);
  ensureSectionState("#mentorship-card", consented);
  ensureSectionState("#commission-card", consented);
  if (!consented) {
    syncFoldToolbar();
    return;
  }
  renderFurnaceArea(bundle);
  renderMentorshipArea(bundle);
  renderCommissionArea(bundle);
  syncFoldToolbar();
};

document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-furnace-harvest-target]");
  if (!button || button.disabled) return;

  try {
    const targetTg = Number(button.dataset.furnaceHarvestTarget || 0);
    const payload = await runButtonAction(button, "采补中…", () => postJson("/plugins/xiuxian/api/furnace/harvest", {
      target_tg: targetTg,
    }));
    if (payload.bundle) applyProfileBundle(payload.bundle);
    const result = payload.result || {};
    const lines = [String(result.message || "本次采补已完成。").trim()];
    lines.push(`主人修为 +${Number(result.master_gain || 0)}`);
    lines.push(`炉鼎当前修为 -${Number(result.furnace_loss || 0)}`);
    if (Array.isArray(result.upgraded_layers) && result.upgraded_layers.length) {
      lines.push(`层数提升：${result.upgraded_layers.map((layer) => `${layer}层`).join("、")}`);
    }
    setStatus(result.message || "采补完成。", "success");
    await popup("采补完成", lines.join("\n"));
  } catch (error) {
    const message = normalizeError(error, "采补炉鼎失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

function farmStatusBadgeClass(status) {
  if (status === "ready") return "badge badge--normal";
  if (status === "overdue") return "badge badge--danger";
  if (status === "growing") return "badge badge--pending";
  return "badge badge--unknown";
}

function formatCountdownSeconds(seconds) {
  const totalSeconds = Math.max(Number(seconds || 0), 0);
  if (totalSeconds < 60) return "不到 1 分钟";
  const totalMinutes = Math.ceil(totalSeconds / 60);
  if (totalMinutes < 60) return `${totalMinutes} 分钟`;
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours < 24) return `${hours} 小时${minutes ? `${minutes} 分钟` : ""}`;
  const days = Math.floor(hours / 24);
  const remainHours = hours % 24;
  return `${days} 天${remainHours ? `${remainHours} 小时` : ""}`;
}

function farmTimingText(plot = {}) {
  if (!plot.unlocked) {
    return plot.locked_reason || plot.unlock_requirement_text || "满足条件后可开垦该地块。";
  }
  if (!plot.occupied) {
    return "当前空置，可在上方选择灵种后播种。";
  }
  if (plot.status === "growing") {
    return `距离成熟约 ${formatCountdownSeconds(plot.seconds_until_mature)}。`;
  }
  if (plot.status === "ready") {
    return `已成熟，建议在 ${formatDate(plot.harvest_deadline_at)} 前收获。`;
  }
  if (plot.status === "overdue") {
    return `已错过最佳采收期，继续拖延会持续减产。`;
  }
  return "灵药状态稳定，可继续观察。";
}

function renderFarmArea(bundle) {
  const summaryRoot = document.querySelector("#farm-summary");
  const catalogRoot = document.querySelector("#farm-material-catalog");
  const plotRoot = document.querySelector("#farm-plot-list");
  const slotSelect = document.querySelector("#farm-slot-select");
  const materialSelect = document.querySelector("#farm-material-select");
  const hint = document.querySelector("#farm-plant-hint");
  if (!summaryRoot || !catalogRoot || !plotRoot || !slotSelect || !materialSelect || !hint) return;

  summaryRoot.classList.add("farm-summary-grid");
  const farm = bundle?.farm || {};
  const plots = Array.isArray(farm.plots) ? farm.plots : [];
  const materials = Array.isArray(farm.plantable_materials) ? farm.plantable_materials : [];
  const selectedSlot = String(slotSelect.value || (farm.empty_slots || [])[0] || "");
  const selectedMaterial = String(materialSelect.value || (materials.find((item) => item.plantable_now)?.id || ""));

  summaryRoot.innerHTML = `
    <article class="info-chip">
      <span>已开垦地块</span>
      <strong>${escapeHtml(farm.unlocked_count || 0)} / ${escapeHtml(farm.slot_count || plots.length || 0)}</strong>
    </article>
    <article class="info-chip">
      <span>空闲地块</span>
      <strong>${escapeHtml(farm.empty_count || 0)} 块</strong>
    </article>
    <article class="info-chip">
      <span>可收获</span>
      <strong>${escapeHtml(farm.ready_count || 0)} 块</strong>
    </article>
    <article class="info-chip">
      <span>下一株成熟</span>
      <strong>${escapeHtml(farm.next_mature_at ? formatDate(farm.next_mature_at) : "暂无")}</strong>
    </article>
  `;

  const emptySlots = plots
    .filter((plot) => plot.unlocked && !plot.occupied)
    .map((plot) => ({ value: String(plot.slot_index), label: `${plot.slot_index} 号灵田` }));
  const availableMaterials = materials
    .filter((item) => item.plantable_now)
    .map((item) => ({
      value: String(item.id),
      label: `${item.name} · ${item.seed_price_stone || 0} 灵石 · ${item.growth_label || `${item.growth_minutes || 0} 分钟`}`,
    }));

  setSelectOptions(
    slotSelect,
    emptySlots.length ? emptySlots : [{ value: "", label: "暂无空闲地块" }],
    selectedSlot,
  );
  slotSelect.disabled = !emptySlots.length;
  setSelectOptions(
    materialSelect,
    availableMaterials.length ? availableMaterials : [{ value: "", label: "当前无可播种灵种" }],
    selectedMaterial,
  );
  materialSelect.disabled = !emptySlots.length || !availableMaterials.length;

  if (!plots.length) {
    plotRoot.innerHTML = `<article class="stack-item"><strong>灵田尚未开启</strong><p>踏入仙途后会自动获得基础药圃。</p></article>`;
  } else {
    plotRoot.innerHTML = plots.map((plot) => {
      const plotClass = [
        "stack-item",
        "farm-plot-card",
        plot.status === "ready" ? "is-ready" : "",
        plot.status === "overdue" ? "is-overdue" : "",
        !plot.unlocked ? "is-locked" : "",
      ].filter(Boolean).join(" ");
      const progressBar = plot.occupied ? `
        <div class="farm-progress">
          <span class="farm-progress-bar" style="width:${escapeHtml(Math.max(Math.min(Number(plot.progress_percent || 0), 100), 0))}%"></span>
        </div>
      ` : "";
      const actionButtons = !plot.unlocked ? `
        <div class="inline-action-buttons">
          <button type="button" data-farm-action="unlock" data-farm-slot="${escapeHtml(plot.slot_index)}" ${plot.can_unlock ? "" : "disabled"}>
            解锁地块${plot.unlock_cost_stone ? `（${escapeHtml(plot.unlock_cost_stone)} 灵石）` : ""}
          </button>
        </div>
      ` : plot.occupied ? `
        <div class="inline-action-buttons">
          <button type="button" class="ghost" data-farm-action="water" data-farm-slot="${escapeHtml(plot.slot_index)}" ${plot.can_water ? "" : "disabled"}>浇灌</button>
          <button type="button" class="ghost" data-farm-action="fertilize" data-farm-slot="${escapeHtml(plot.slot_index)}" ${plot.can_fertilize ? "" : "disabled"}>
            施肥${plot.fertilize_cost_stone ? `（${escapeHtml(plot.fertilize_cost_stone)} 灵石）` : ""}
          </button>
          <button type="button" class="ghost" data-farm-action="clear_pest" data-farm-slot="${escapeHtml(plot.slot_index)}" ${plot.can_clear_pest ? "" : "disabled"}>除虫</button>
          <button type="button" data-farm-action="harvest" data-farm-slot="${escapeHtml(plot.slot_index)}" ${plot.can_harvest ? "" : "disabled"}>收获</button>
        </div>
      ` : `<p class="muted">上方选择灵种后，可播种到这块空置灵田。</p>`;
      const tags = [
        plot.occupied ? `基础产量 ${plot.base_yield || 0}` : "空置地块",
        plot.occupied ? `当前预估 ${plot.yield_preview || 0}` : "等待播种",
        ...(plot.care_tags || []),
      ];
      return `
        <article class="${plotClass}">
          <div class="stack-item-head">
            <strong>${escapeHtml(plot.slot_index)} 号灵田${plot.material?.name ? ` · ${escapeHtml(plot.material.name)}` : ""}</strong>
            <span class="${farmStatusBadgeClass(plot.status)}">${escapeHtml(plot.status_label || "状态未知")}</span>
          </div>
          <p>${escapeHtml(farmTimingText(plot))}</p>
          ${plot.occupied ? `<p>可用于：${escapeHtml(plot.recipe_summary || "丹方材料")}</p>` : ""}
          <div class="item-tags">
            ${tags.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}
            ${!plot.unlocked && plot.unlock_requirement_text ? `<span class="tag">${escapeHtml(plot.unlock_requirement_text)}</span>` : ""}
          </div>
          ${plot.occupied ? `<p>成熟时间：${escapeHtml(formatDate(plot.mature_at))}</p>` : ""}
          ${plot.occupied ? `<p>最佳采收截止：${escapeHtml(formatDate(plot.harvest_deadline_at))}</p>` : ""}
          ${progressBar}
          ${plot.locked_reason && !plot.unlocked ? `<p class="reason-text">${escapeHtml(plot.locked_reason)}</p>` : ""}
          ${actionButtons}
        </article>
      `;
    }).join("");
  }

  const materialQuery = inventorySearchValue("#farm-material-search");
  const filteredMaterials = materials.filter((item) => textQueryMatches(materialQuery, [
    item.name,
    item.quality_label,
    item.unlock_requirement_text,
    item.recipe_summary,
    item.recipe_names || [],
  ]));

  if (!filteredMaterials.length) {
    catalogRoot.innerHTML = materials.length
      ? `<article class="stack-item"><strong>未找到匹配灵种</strong><p>可按材料名、丹方名或境界要求继续搜索。</p></article>`
      : `<article class="stack-item"><strong>当前没有可种植药材</strong><p>只有真正用于丹药炼制的材料，才会出现在灵田目录里。</p></article>`;
  } else {
    catalogRoot.innerHTML = filteredMaterials.map((item) => `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(item.name)}</strong>
          ${qualityBadgeHtml(item.quality_label || item.quality_level, item.quality_color, "badge badge--normal")}
        </div>
        <p>适用丹方：${escapeHtml(item.recipe_summary || (item.recipe_names || []).join("、") || "暂无")}</p>
        <div class="item-tags">
          <span class="tag">种子 ${escapeHtml(item.seed_price_stone || 0)} 灵石</span>
          <span class="tag">成长 ${escapeHtml(item.growth_label || `${item.growth_minutes || 0} 分钟`)}</span>
          <span class="tag">产量 ${escapeHtml(item.yield_label || `${item.yield_min || 0}-${item.yield_max || 0}`)}</span>
          <span class="tag">${escapeHtml(item.unlock_requirement_text || "入道后即可种植")}</span>
        </div>
        ${item.plantable_now ? "" : `<p class="reason-text">当前境界不足，尚不能种植这味灵药。</p>`}
        ${item.plantable_now && !item.seed_affordable ? `<p class="reason-text">当前灵石不足，播种至少需要 ${escapeHtml(item.seed_price_stone || 0)} 灵石。</p>` : ""}
        <div class="inline-action-buttons">
          <button type="button" class="ghost" data-farm-pick-material="${escapeHtml(item.id)}" ${item.plantable_now && emptySlots.length ? "" : "disabled"}>选作灵种</button>
        </div>
      </article>
    `).join("");
  }

  if (!emptySlots.length) {
    hint.textContent = "当前没有空闲灵田，可先收获成熟作物或开垦新的地块。";
  } else if (!availableMaterials.length) {
    hint.textContent = "你当前境界下暂无可播种灵种，先提升修为或查看下方药材目录。";
  } else {
    hint.textContent = `当前有 ${emptySlots.length} 块空闲灵田，可播种 ${availableMaterials.length} 种丹方材料。`;
  }
}

const renderProfileWithFarmBase = renderProfile;
renderProfile = function renderProfileWithFarm(bundle) {
  renderProfileWithFarmBase(bundle);
  const consented = Boolean(bundle?.profile?.consented);
  ensureSectionState("#farm-card", consented);
  if (!consented) {
    syncFoldToolbar();
    return;
  }
  renderFarmArea(bundle);
  syncFoldToolbar();
};

const renderProfileWithMarriageBase = renderProfile;
renderProfile = function renderProfileWithMarriage(bundle) {
  renderProfileWithMarriageBase(bundle);
  const consented = Boolean(bundle?.profile?.consented);
  const genderLocked = Boolean(bundle?.capabilities?.gender_required);
  const genderLockReason = String(bundle?.capabilities?.gender_lock_reason || "").trim();
  ensureSectionState("#marriage-card", consented, genderLocked);
  if (!consented) {
    syncFoldToolbar();
    return;
  }

  renderMarriageArea(bundle);
  const profileGrid = document.querySelector("#profile-grid");
  if (profileGrid) {
    profileGrid.insertAdjacentHTML(
      "beforeend",
      `<article class="profile-item"><span>性别</span><strong>${escapeHtml(bundle?.marriage?.gender_label || "未设置")}</strong></article>`
      + `<article class="profile-item"><span>道侣</span><strong>${escapeHtml(bundle?.marriage?.current_marriage?.spouse_profile?.display_label || "暂无")}</strong></article>`
    );
  }

  if (genderLocked) {
    [
      "#action-card",
      "#exchange-card",
      "#inventory-card",
      "#technique-card",
      "#official-shop-card",
      "#market-card",
      "#auction-card",
      "#leaderboard-card",
      "#sect-card",
      "#task-card",
      "#craft-card",
      "#explore-card",
      "#red-envelope-card",
      "#gift-card",
      "#title-card",
      "#furnace-card",
      "#mentorship-card",
      "#commission-card",
      "#farm-card",
      "#fishing-card",
    ].forEach((selector) => ensureSectionState(selector, false));
    if (genderLockReason) {
      setStatus(genderLockReason, "warning");
    }
  }
  syncFoldToolbar();
};

document.querySelector("#farm-material-search")?.addEventListener("input", () => {
  if (!state.profileBundle?.profile?.consented) return;
  renderFarmArea(state.profileBundle);
});

document.querySelector("#farm-material-catalog")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-farm-pick-material]");
  if (!button) return;
  const materialSelect = document.querySelector("#farm-material-select");
  if (!materialSelect) return;
  materialSelect.value = button.dataset.farmPickMaterial || "";
  document.querySelector("#farm-plant-form")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
});

document.querySelector("#farm-plant-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget?.querySelector("button[type='submit']");
  const slotIndex = Number(document.querySelector("#farm-slot-select")?.value || 0);
  const materialId = Number(document.querySelector("#farm-material-select")?.value || 0);
  if (!button || slotIndex <= 0 || materialId <= 0) {
    const message = "请选择空闲地块和要播种的灵药。";
    setStatus(message, "warning");
    await popup("无法播种", message, "warning");
    return;
  }
  try {
    const payload = await runButtonAction(button, "播种中…", () => postJson("/plugins/xiuxian/api/farm/plant", {
      slot_index: slotIndex,
      material_id: materialId,
    }));
    if (payload.bundle) applyProfileBundle(payload.bundle);
    const result = payload.result || {};
    const lines = [result.message || "灵药已经播入灵田。"];
    if (Number(result.seed_cost_stone || 0) > 0) {
      lines.push(`消耗灵石 ${result.seed_cost_stone}`);
    }
    if (result.mature_at) {
      lines.push(`预计成熟：${formatDate(result.mature_at)}`);
    }
    setStatus(result.message || "播种完成。", "success");
    await popup("播种完成", lines.join("\n"));
  } catch (error) {
    const message = normalizeError(error, "播种灵药失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#farm-plot-list")?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-farm-action]");
  if (!button || button.disabled) return;
  const action = button.dataset.farmAction || "";
  const slotIndex = Number(button.dataset.farmSlot || 0);
  if (slotIndex <= 0) return;

  let path = "";
  let body = { slot_index: slotIndex };
  let title = "灵田操作";
  let pendingText = "处理中…";
  if (action === "unlock") {
    path = "/plugins/xiuxian/api/farm/unlock";
    title = "开垦完成";
    pendingText = "开垦中…";
  } else if (action === "harvest") {
    path = "/plugins/xiuxian/api/farm/harvest";
    title = "收获完成";
    pendingText = "收获中…";
  } else {
    path = "/plugins/xiuxian/api/farm/care";
    body = { ...body, action };
    title = action === "water" ? "浇灌完成" : action === "fertilize" ? "施肥完成" : "除虫完成";
    pendingText = action === "water" ? "浇灌中…" : action === "fertilize" ? "施肥中…" : "除虫中…";
  }

  try {
    const payload = await runButtonAction(button, pendingText, () => postJson(path, body));
    if (payload.bundle) applyProfileBundle(payload.bundle);
    const result = payload.result || {};
    const lines = [result.message || "灵田操作已完成。"];
    if (Number(result.quantity || 0) > 0) {
      lines.push(`收获数量 ${result.quantity}`);
    }
    if (Number(result.stone_cost || 0) > 0) {
      lines.push(`消耗灵石 ${result.stone_cost}`);
    }
    if (Number(result.unlock_cost_stone || 0) > 0) {
      lines.push(`消耗灵石 ${result.unlock_cost_stone}`);
    }
    if (result.mature_at) {
      lines.push(`新的成熟时间：${formatDate(result.mature_at)}`);
    }
    setStatus(result.message || "灵田操作已完成。", "success");
    await popup(title, lines.join("\n"));
  } catch (error) {
    const message = normalizeError(error, "灵田操作失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

function renderFishingArea(bundle) {
  const summaryRoot = document.querySelector("#fishing-summary");
  const listRoot = document.querySelector("#fishing-spot-list");
  const noteRoot = document.querySelector("#fishing-note");
  if (!summaryRoot || !listRoot || !noteRoot) return;

  const fishing = bundle?.fishing || {};
  const spots = Array.isArray(fishing.spots) ? fishing.spots : [];
  noteRoot.textContent = fishing.note || "高品阶物品基础概率更低，机缘会抬升高品掉率。";
  summaryRoot.innerHTML = `
    <article class="info-chip">
      <span>当前机缘</span>
      <strong>${escapeHtml(fishing.current_fortune || bundle?.effective_stats?.fortune || bundle?.profile?.fortune || 0)}</strong>
    </article>
    <article class="info-chip">
      <span>可用钓场</span>
      <strong>${escapeHtml(fishing.available_spot_count || 0)} 处</strong>
    </article>
    <article class="info-chip">
      <span>玩法提示</span>
      <strong>高品更稀有</strong>
    </article>
    <article class="info-chip">
      <span>概率关联</span>
      <strong>机缘越高越容易出高品</strong>
    </article>
  `;

  if (!spots.length) {
    listRoot.innerHTML = `<article class="stack-item"><strong>暂无钓场</strong><p>踏入仙途后会开放可用水域。</p></article>`;
    return;
  }

  listRoot.innerHTML = spots.map((spot) => {
    const oddsTags = (spot.odds_preview || []).map((item) => `${item.label} ${item.chance_percent}%`);
    const rewardCards = (spot.reward_preview || []).map((item) => `
      <article class="recipe-source-item">
        <strong>${escapeHtml(item.name || "未知物品")}</strong>
        <p>${escapeHtml(item.kind_label || item.kind || "物品")} · ${escapeHtml(item.quality_label || "凡品")}</p>
      </article>
    `).join("");
    const statusClass = spot.available ? "badge badge--normal" : "badge badge--unknown";
    const reason = spot.available ? "" : (spot.available_reason || "当前还不能在此抛竿。");
    return `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>${escapeHtml(spot.name || "未命名钓场")}</strong>
          <span class="${statusClass}">${spot.available ? "可抛竿" : "暂不可用"}</span>
        </div>
        <p>${escapeHtml(spot.description || "暂无说明")}</p>
        <div class="item-tags">
          <span class="tag">耗费 ${escapeHtml(spot.cast_cost_stone || 0)} 灵石</span>
          <span class="tag">门槛 ${escapeHtml(spot.requirement_text || "入道后即可")}</span>
          <span class="tag">品阶带 ${escapeHtml(spot.quality_band_label || "未标注")}</span>
          <span class="tag">产出 ${escapeHtml((spot.kind_labels || []).join(" / ") || "物品")}</span>
        </div>
        ${(oddsTags || []).length ? `<div class="item-tags">${oddsTags.map((text) => `<span class="tag">${escapeHtml(text)}</span>`).join("")}</div>` : ""}
        <div class="recipe-source-list">${rewardCards || `<article class="recipe-source-item"><strong>暂无预览</strong><p>此钓场的样本奖励尚未生成。</p></article>`}</div>
        ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : ""}
        <button type="button" data-fishing-spot="${escapeHtml(spot.key || "")}" ${spot.available ? "" : "disabled"}>前往抛竿</button>
      </article>
    `;
  }).join("");
}

const renderProfileWithFishingBase = renderProfile;
renderProfile = function renderProfileWithFishing(bundle) {
  renderProfileWithFishingBase(bundle);
  const consented = Boolean(bundle?.profile?.consented);
  ensureSectionState("#fishing-card", consented);
  if (!consented) {
    syncFoldToolbar();
    return;
  }
  renderFishingArea(bundle);
  syncFoldToolbar();
};

document.querySelector("#fishing-spot-list")?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-fishing-spot]");
  if (!button || button.disabled) return;
  const spotKey = button.dataset.fishingSpot || "";
  try {
    const payload = await runButtonAction(button, "抛竿中…", () => postJson("/plugins/xiuxian/api/fishing/cast", {
      spot_key: spotKey,
    }));
    if (payload.bundle) applyProfileBundle(payload.bundle);
    const result = payload.result || {};
    const rewardName = result.reward_item?.name || "未知物品";
    const lines = [result.message || "你已经顺利完成本次垂钓。"];
    lines.push(`获得：${rewardName}${Number(result.quantity || 0) > 1 ? ` ×${Number(result.quantity || 0)}` : ""}`);
    lines.push(`类型：${result.reward_kind_label || result.reward_kind || "物品"}`);
    lines.push(`品阶：${result.quality_label || "凡品"}`);
    if (Number(result.cast_cost_stone || 0) > 0) {
      lines.push(`耗费灵石：${Number(result.cast_cost_stone || 0)}`);
    }
    if (Number(result.fortune_used || 0) > 0) {
      lines.push(`本次结算机缘：${Number(result.fortune_used || 0)}`);
    }
    setStatus(result.message || "垂钓完成。", "success");
    await popup("垂钓完成", lines.join("\n"));
  } catch (error) {
    const message = normalizeError(error, "本次抛竿失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

function formatChancePercent(value) {
  const amount = Number(value || 0);
  if (!Number.isFinite(amount) || amount <= 0) return "0%";
  return `${amount.toFixed(amount >= 10 ? 2 : 3).replace(/\.?0+$/, "")}%`;
}

function gamblingQuantityText(entry = {}) {
  const min = Math.max(Number(entry.quantity_min || 1), 1);
  const max = Math.max(Number(entry.quantity_max || min), min);
  return min === max ? `x${min}` : `x${min}-${max}`;
}

function renderGamblingArea(bundle) {
  const summaryRoot = document.querySelector("#gambling-summary");
  const noteRoot = document.querySelector("#gambling-note");
  const listRoot = document.querySelector("#gambling-pool-list");
  const exchangeInput = document.querySelector("#gambling-exchange-count");
  const openInput = document.querySelector("#gambling-open-count");
  if (!summaryRoot || !noteRoot || !listRoot) return;

  const gambling = bundle?.gambling || {};
  const preview = Array.isArray(gambling.pool_preview) ? gambling.pool_preview : [];
  const exchangeMax = Math.max(Number(gambling.exchange_max_count || 1), 1);
  const openMax = Math.max(Number(gambling.open_max_count || 1), 1);
  if (exchangeInput) {
    exchangeInput.max = String(exchangeMax);
    if (!exchangeInput.value || Number(exchangeInput.value || 0) > exchangeMax) {
      exchangeInput.value = "1";
    }
  }
  if (openInput) {
    openInput.max = String(openMax);
    if (!openInput.value || Number(openInput.value || 0) > openMax) {
      openInput.value = "1";
    }
  }

  summaryRoot.innerHTML = `
    <article class="info-chip">
      <span>持有奇石</span>
      <strong>${escapeHtml(gambling.owned_count || 0)} 枚</strong>
    </article>
    <article class="info-chip">
      <span>兑换价格</span>
      <strong>${escapeHtml(gambling.exchange_cost_stone || 0)} 灵石 / 枚</strong>
    </article>
    <article class="info-chip">
      <span>单次上限</span>
      <strong>兑 ${escapeHtml(exchangeMax)} / 开 ${escapeHtml(openMax)}</strong>
    </article>
    <article class="info-chip">
      <span>当前机缘</span>
      <strong>${escapeHtml(gambling.fortune_value || bundle?.effective_stats?.fortune || bundle?.profile?.fortune || 0)}</strong>
    </article>
  `;
  noteRoot.textContent = `${gambling.fortune_hint || "当前机缘未触发额外稀有加成。"} ${Number(gambling.broadcast_quality_level || 0) > 0 ? `抽到${gambling.broadcast_quality_level}阶及以上奖励时会自动群播。` : ""}`.trim();

  if (!preview.length) {
    listRoot.innerHTML = `<article class="stack-item"><strong>当前赌坊奖池未配置</strong><p>请等待主人在后台配置奖励后再来开启仙界奇石。</p></article>`;
    return;
  }

  listRoot.innerHTML = preview.map((entry) => `
    <article class="stack-item">
      <div class="stack-item-head">
        <strong>${escapeHtml(entry.item_name || "未知物品")}</strong>
        ${qualityBadgeHtml(entry.quality_label || "凡品", entry.quality_color, "badge badge--normal")}
      </div>
      <p>${escapeHtml(entry.item_kind_label || entry.item_kind || "物品")} · 当前概率 ${escapeHtml(formatChancePercent(entry.chance_percent || 0))}</p>
      <div class="item-tags">
        <span class="tag">掉落数量 ${escapeHtml(gamblingQuantityText(entry))}</span>
        <span class="tag">基础权重 ${escapeHtml(entry.base_weight || 0)}</span>
        <span class="tag">修正权重 ${escapeHtml(Number(entry.effective_weight || 0).toFixed(3).replace(/\.?0+$/, ""))}</span>
      </div>
    </article>
  `).join("");
}

const renderProfileWithGamblingBase = renderProfile;
renderProfile = function renderProfileWithGambling(bundle) {
  renderProfileWithGamblingBase(bundle);
  const consented = Boolean(bundle?.profile?.consented);
  const genderLocked = Boolean(bundle?.capabilities?.gender_required);
  const visible = consented && !genderLocked;
  ensureSectionState("#gambling-card", visible);
  if (!visible) {
    syncFoldToolbar();
    return;
  }

  renderGamblingArea(bundle);
  const gambling = bundle?.gambling || {};
  const retreating = Boolean(bundle?.capabilities?.is_in_retreat);
  const duelLockReason = currentDuelLockReason(bundle);
  const poolBlockedReason = Number(gambling.pool_size || 0) > 0 ? "" : "当前赌坊奖池尚未配置。";
  const disabledReason = retreating ? "闭关期间无法进入赌坊。" : (duelLockReason || poolBlockedReason);
  ["#gambling-exchange-count", "#gambling-open-count"].forEach((selector) => {
    setDisabled(document.querySelector(selector), Boolean(disabledReason), disabledReason);
  });
  setDisabled(document.querySelector("#gambling-exchange-form button[type='submit']"), Boolean(disabledReason), disabledReason);
  setDisabled(document.querySelector("#gambling-open-form button[type='submit']"), Boolean(disabledReason), disabledReason);
  syncFoldToolbar();
};

document.querySelector("#commission-list")?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-commission-key]");
  if (!button || button.disabled) return;
  try {
    const payload = await runButtonAction(button, "承接中...", () => postJson("/plugins/xiuxian/api/commission/claim", {
      commission_key: button.dataset.commissionKey || "",
    }));
    const result = payload.commission || {};
    const title = result.name || "坊市委托";
    const stoneGain = Number(result.stone_gain || 0);
    const cultivationGain = Number(result.cultivation_gain || 0);
    const detail = result.detail || "委托已经顺利完成。";
    const growthText = attributeGrowthText(result.attribute_growth || []);
    const message = `${title} 完成，灵石 +${stoneGain}，修为 +${cultivationGain}${growthText ? `，${growthText}` : ""}。`;
    await refreshBundle();
    setStatus(message, "success");
    await popup("委托完成", `${detail}\n灵石 +${stoneGain}\n修为 +${cultivationGain}${growthText ? `\n${growthText}` : ""}`);
    await refreshLeaderboard(state.leaderboard.kind, state.leaderboard.page);
  } catch (error) {
    const message = normalizeError(error, "承接灵石委托失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.addEventListener("click", async (event) => {
  const requestButton = event.target.closest("[data-marriage-request-action]");
  const dualButton = event.target.closest("[data-marriage-dual-cultivate]");
  const divorceButton = event.target.closest("[data-marriage-divorce]");
  if (!requestButton && !dualButton && !divorceButton) return;

  try {
    if (requestButton) {
      const action = requestButton.dataset.marriageRequestAction || "accept";
      const requestId = Number(requestButton.dataset.marriageRequestId || 0);
      const pendingText = action === "accept" ? "处理中…" : action === "reject" ? "婉拒中…" : "撤回中…";
      const payload = await runButtonAction(requestButton, pendingText, () => postJson("/plugins/xiuxian/api/marriage/request/respond", {
        request_id: requestId,
        action,
      }));
      if (payload.bundle) applyProfileBundle(payload.bundle);
      const result = payload.result || {};
      const title = action === "accept" ? "已结为道侣" : action === "reject" ? "已婉拒" : "已撤回";
      setStatus(result.message || title, action === "accept" ? "success" : "warning");
      await popup(title, result.message || "操作已完成。", action === "accept" ? "success" : "warning");
      return;
    }

    if (dualButton) {
      const payload = await runButtonAction(dualButton, "双修中…", () => postJson("/plugins/xiuxian/api/marriage/dual-cultivate", {}));
      if (payload.bundle) applyProfileBundle(payload.bundle);
      const result = payload.result || {};
      const lines = [result.message || "本次双修已完成。"];
      lines.push(`你获得修为 +${Number(result.actor_gain || 0)}`);
      lines.push(`道侣获得修为 +${Number(result.spouse_gain || 0)}`);
      lines.push(`缘分 +${Number(result.bond_gain || 0)}`);
      setStatus(result.message || "道侣双修完成。", "success");
      await popup("双修完成", lines.join("\n"));
      return;
    }

    if (divorceButton) {
      const payload = await runButtonAction(divorceButton, "分家中…", () => postJson("/plugins/xiuxian/api/marriage/divorce", {}));
      if (payload.bundle) applyProfileBundle(payload.bundle);
      const result = payload.result || {};
      const lines = [result.message || "双方已经和离。"];
      lines.push(`${result.husband_name || "男方"} 灵石 ${Number(result.husband_stone || 0)}`);
      lines.push(`${result.wife_name || "女方"} 灵石 ${Number(result.wife_stone || 0)}`);
      setStatus(result.message || "和离分家已完成。", "warning");
      await popup("和离分家", lines.join("\n"), "warning");
    }
  } catch (error) {
    const message = normalizeError(error, "姻缘操作失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.addEventListener("click", async (event) => {
  const requestButton = event.target.closest("[data-mentorship-request-action]");
  const teachButton = event.target.closest("[data-mentorship-teach]");
  const consultButton = event.target.closest("[data-mentorship-consult]");
  const graduateButton = event.target.closest("[data-mentorship-graduate-target]");
  const dissolveButton = event.target.closest("[data-mentorship-dissolve-target]");
  if (!requestButton && !teachButton && !consultButton && !graduateButton && !dissolveButton) return;

  try {
    if (requestButton) {
      const action = requestButton.dataset.mentorshipRequestAction || "accept";
      const requestId = Number(requestButton.dataset.mentorshipRequestId || 0);
      const pendingText = action === "accept" ? "处理中…" : action === "reject" ? "婉拒中…" : "撤回中…";
      const payload = await runButtonAction(requestButton, pendingText, () => postJson("/plugins/xiuxian/api/mentorship/request/respond", {
        request_id: requestId,
        action,
      }));
      if (payload.bundle) applyProfileBundle(payload.bundle);
      const result = payload.result || {};
      const title = action === "accept" ? "师徒已结成" : action === "reject" ? "已婉拒" : "已撤回";
      setStatus(result.message || title, action === "accept" ? "success" : "warning");
      await popup(title, result.message || "操作已完成。", action === "accept" ? "success" : "warning");
      return;
    }

    if (teachButton) {
      const discipleTg = Number(teachButton.dataset.mentorshipTeach || 0);
      const payload = await runButtonAction(teachButton, "传道中…", () => postJson("/plugins/xiuxian/api/mentorship/teach", {
        disciple_tg: discipleTg,
      }));
      if (payload.bundle) applyProfileBundle(payload.bundle);
      const result = payload.result || {};
      const growthText = attributeGrowthText(result.attribute_growth || [], "额外感悟");
      const message = result.message || `本次传道已完成，弟子修为 +${result.disciple_gain || 0}。`;
      setStatus(message, "success");
      await popup(
        "传道完成",
        `${message}\n师徒缘 +${result.bond_gain || 0}${growthText ? `\n${growthText}` : ""}`,
      );
      return;
    }

    if (consultButton) {
      const payload = await runButtonAction(consultButton, "问道中…", () => postJson("/plugins/xiuxian/api/mentorship/consult", {}));
      if (payload.bundle) applyProfileBundle(payload.bundle);
      const result = payload.result || {};
      const growthText = attributeGrowthText(result.attribute_growth || [], "额外领悟");
      const message = result.message || `本次问道已完成，修为 +${result.disciple_gain || 0}。`;
      setStatus(message, "success");
      await popup(
        "问道完成",
        `${message}\n师徒缘 +${result.bond_gain || 0}${growthText ? `\n${growthText}` : ""}`,
      );
      return;
    }

    if (graduateButton) {
      const targetTg = Number(graduateButton.dataset.mentorshipGraduateTarget || 0);
      const payload = await runButtonAction(graduateButton, "出师中…", () => postJson("/plugins/xiuxian/api/mentorship/graduate", {
        target_tg: targetTg,
      }));
      if (payload.bundle) applyProfileBundle(payload.bundle);
      const result = payload.result || {};
      const titleRewards = (result.title_rewards || [])
        .map((item) => item?.title?.name)
        .filter(Boolean)
        .join("、");
      const message = result.message || "本段师徒传承已正式完成。";
      setStatus(message, "success");
      await popup(
        "正式出师",
        `${message}\n师尊修为 +${result.mentor_gain || 0}\n弟子修为 +${result.disciple_gain || 0}${titleRewards ? `\n称号：${titleRewards}` : ""}`,
      );
      return;
    }

    if (dissolveButton) {
      const targetTg = Number(dissolveButton.dataset.mentorshipDissolveTarget || 0);
      const payload = await runButtonAction(dissolveButton, "处理中…", () => postJson("/plugins/xiuxian/api/mentorship/dissolve", {
        target_tg: targetTg,
      }));
      if (payload.bundle) applyProfileBundle(payload.bundle);
      const result = payload.result || {};
      setStatus(result.message || "师徒关系已解除。", "warning");
      await popup("关系已解除", result.message || "师徒关系已解除。", "warning");
    }
  } catch (error) {
    const message = normalizeError(error, "师徒操作失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#wiki-search")?.addEventListener("input", (event) => {
  state.wikiSearchQuery = String(event.target?.value || "").trim();
  renderWikiArea();
});

document.querySelector("#wiki-filter-row")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-wiki-filter]");
  if (!button) return;
  state.wikiFilter = button.dataset.wikiFilter || "all";
  renderWikiArea();
});

document.querySelector("#wiki-featured-list")?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-wiki-entry]");
  if (!button) return;
  await openWikiEntry(button.dataset.wikiEntry || "");
});

document.querySelector("#wiki-result-list")?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-wiki-entry]");
  if (!button) return;
  await openWikiEntry(button.dataset.wikiEntry || "");
});

setupFoldToolbar();

bootstrap().catch(async (error) => {
  const message = normalizeError(error, "修仙面板初始化失败。");
  setStatus(message, "error");
  await popup("初始化失败", message, "error");
});

// --- Redesign Additions: Card Sorting Buttons ---
const boardGrid = document.querySelector(".board-grid");
if (boardGrid) {
  const cards = Array.from(boardGrid.querySelectorAll(".fold-card"));
  cards.forEach(card => {
    const summary = card.querySelector(".fold-summary");
    if (summary) {
      const controls = document.createElement("div");
      controls.className = "card-sort-controls";
      
      const upBtn = document.createElement("button");
      upBtn.type = "button";
      upBtn.className = "ghost card-up";
      upBtn.innerHTML = "↑上移";
      upBtn.onclick = (e) => { e.preventDefault(); e.stopPropagation(); moveCard(card, -1); };

      const downBtn = document.createElement("button");
      downBtn.type = "button";
      downBtn.className = "ghost card-down";
      downBtn.innerHTML = "↓下移";
      downBtn.onclick = (e) => { e.preventDefault(); e.stopPropagation(); moveCard(card, 1); };

      controls.appendChild(upBtn);
      controls.appendChild(downBtn);
      
      const titleDiv = summary.querySelector("div");
      if (titleDiv) {
        titleDiv.appendChild(controls);
      }
    }
  });

  const savedOrder = localStorage.getItem("xiuxian_layout_order");
  if (savedOrder) {
    try {
      const orderIds = JSON.parse(savedOrder);
      const cardMap = new Map();
      cards.forEach(card => cardMap.set(card.id, card));
      
      orderIds.forEach(id => {
        if (cardMap.has(id)) {
          boardGrid.appendChild(cardMap.get(id));
          cardMap.delete(id);
        }
      });
      cardMap.forEach(card => boardGrid.appendChild(card));
    } catch (e) {
      console.error("Failed to restore layout order", e);
    }
  }

  window.moveCard = (card, direction) => {
    const index = Array.from(boardGrid.children).indexOf(card);
    if (direction === -1 && index > 0) {
      boardGrid.insertBefore(card, boardGrid.children[index - 1]);
    } else if (direction === 1 && index < boardGrid.children.length - 1) {
      boardGrid.insertBefore(card, boardGrid.children[index + 2]);
    }
    
    const newOrder = Array.from(boardGrid.querySelectorAll(".fold-card"))
      .map(c => c.id).filter(Boolean);
    localStorage.setItem("xiuxian_layout_order", JSON.stringify(newOrder));
    setupFoldToolbar();
  };
}

// --- Redesign Additions: FABs (Admin) ---
const fabAdmin = document.getElementById("fab-admin");

if (fabAdmin) {
  const observer = new MutationObserver(() => {
    const heroAdmin = document.getElementById("hero-admin-entry");
    if (heroAdmin && !heroAdmin.classList.contains("hidden")) {
      fabAdmin.classList.remove("hidden");
    } else {
      fabAdmin.classList.add("hidden");
    }
  });
  const heroAdmin = document.getElementById("hero-admin-entry");
  if (heroAdmin) {
    observer.observe(heroAdmin, { attributes: true, attributeFilter: ["class"] });
    if (!heroAdmin.classList.contains("hidden")) {
      fabAdmin.classList.remove("hidden");
    }
  }

  fabAdmin.addEventListener("click", () => {
    const adminBtn = document.getElementById("open-admin-panel");
    if (adminBtn) adminBtn.click();
  });
}

function renderGroupedCards(root, cardsHtmlArray, groupingFn) {
  if (cardsHtmlArray.length <= 5) {
    cardsHtmlArray.forEach(({card}) => root.appendChild(card));
    return;
  }
  const groups = new Map();
  cardsHtmlArray.forEach(({card, item}) => {
    const key = groupingFn(item) || "其他";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(card);
  });
  
  if (groups.size === 1) {
    cardsHtmlArray.forEach(({card}) => root.appendChild(card));
    return;
  }
  
  groups.forEach((cards, key) => {
    const details = document.createElement("details");
    details.className = "mini-fold";
    details.open = true;
    details.innerHTML = `<summary class="mini-fold-summary"><h3>${escapeHtml(key)} (${cards.length})</h3><span class="summary-tip">折叠分组</span></summary>`;
    const body = document.createElement("div");
    body.className = "mini-fold-body stack-list";
    cards.forEach(c => body.appendChild(c));
    details.appendChild(body);
    root.appendChild(details);
  });
}
