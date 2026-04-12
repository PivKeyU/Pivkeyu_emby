const storageKey = "pivkeyu-admin-token";
const DEFAULT_BACK_PATH = "/miniapp";

const LEVEL_META = {
  a: {
    code: "a",
    text: "白名单用户",
    shortText: "白名单",
    description: "拥有更高权限和更稳定线路的高级用户。",
    tone: "vip"
  },
  b: {
    code: "b",
    text: "正常用户",
    shortText: "正常",
    description: "已开通并可正常使用的大多数用户。",
    tone: "normal"
  },
  c: {
    code: "c",
    text: "已封禁用户",
    shortText: "已封禁",
    description: "当前已被禁用，需要主人处理后才能恢复。",
    tone: "danger"
  },
  d: {
    code: "d",
    text: "未注册用户",
    shortText: "未注册",
    description: "仅录入了账号信息，还没有有效的 Emby 账号。",
    tone: "pending"
  }
};

const UNKNOWN_LEVEL = {
  code: "?",
  text: "未知状态",
  shortText: "未知",
  description: "系统无法识别这个等级，请检查数据。",
  tone: "unknown"
};

const tgApp = window.Telegram?.WebApp || null;
const tgBackButton = tgApp?.BackButton || null;
const backState = {
  fallbackPath: DEFAULT_BACK_PATH,
  returnTo: "",
  referrerPath: ""
};

const state = {
  page: 1,
  pageSize: 20,
  query: "",
  selectedTg: null,
  codesPage: 1,
  codesPageSize: 20,
  codeStatus: "all",
  visibleCodes: [],
  selectedCodes: new Set(),
  visibleUsers: [],
  token: localStorage.getItem(storageKey) || "",
  authMode: null,
  telegramInitData: tgApp?.initData || "",
  telegramUser: tgApp?.initDataUnsafe?.user || null
};

const refs = {
  adminStatus: document.querySelector("#admin-status"),
  authTitle: document.querySelector("#auth-title"),
  authStatus: document.querySelector("#auth-status"),
  authModePill: document.querySelector("#auth-mode-pill"),
  selectedUserPill: document.querySelector("#selected-user-pill"),
  pageBackButton: document.querySelector("#page-back-button"),
  tokenPanel: document.querySelector("#token-panel"),
  tokenForm: document.querySelector("#token-form"),
  tokenInput: document.querySelector("#admin-token"),
  editorStatus: document.querySelector("#editor-status"),
  pageLabel: document.querySelector("#page-label"),
  userList: document.querySelector("#user-list"),
  codeList: document.querySelector("#code-list"),
  codeResult: document.querySelector("#code-create-result"),
  codeResultTitle: document.querySelector("#code-create-result-title"),
  codeResultMeta: document.querySelector("#code-create-result-meta"),
  codeOutput: document.querySelector("#code-create-output"),
  codeCreateForm: document.querySelector("#code-create-form"),
  codeCreateSubmit: document.querySelector("#code-create-submit"),
  codeCreateCopy: document.querySelector("#code-create-copy"),
  codeCreateSuffixMode: document.querySelector("#code-create-suffix-mode"),
  codeCreateSuffixText: document.querySelector("#code-create-suffix-text"),
  codeStatusButtons: [...document.querySelectorAll("[data-code-status]")],
  codeSelectPage: document.querySelector("#codes-select-page"),
  codeClearSelection: document.querySelector("#codes-clear-selection"),
  codeDeleteSelected: document.querySelector("#codes-delete-selected"),
  codePrevPage: document.querySelector("#codes-prev-page"),
  codeNextPage: document.querySelector("#codes-next-page"),
  codePageLabel: document.querySelector("#codes-page-label"),
  autoUpdateForm: document.querySelector("#auto-update-form"),
  autoUpdateSave: document.querySelector("#auto-update-save"),
  autoUpdateStatus: document.querySelector("#auto-update-status"),
  autoUpdateGitRepo: document.querySelector("#auto-update-git-repo"),
  autoUpdateDockerImage: document.querySelector("#auto-update-docker-image"),
  autoUpdateComposeService: document.querySelector("#auto-update-compose-service"),
  autoUpdateContainerName: document.querySelector("#auto-update-container-name"),
  autoUpdateInterval: document.querySelector("#auto-update-interval"),
  autoUpdateEnabledText: document.querySelector("#update-enabled-text"),
  autoUpdateLastChecked: document.querySelector("#update-last-checked"),
  autoUpdateLastStatus: document.querySelector("#update-last-status"),
  autoUpdateCommitSha: document.querySelector("#update-commit-sha"),
  autoUpdateNote: document.querySelector("#update-note"),
  migrationExportButton: document.querySelector("#migration-export-button"),
  migrationImportForm: document.querySelector("#migration-import-form"),
  migrationImportFile: document.querySelector("#migration-import-file"),
  migrationRestoreConfig: document.querySelector("#migration-restore-config"),
  migrationRestartAfterImport: document.querySelector("#migration-restart-after-import"),
  migrationImportSubmit: document.querySelector("#migration-import-submit"),
  migrationNote: document.querySelector("#migration-note"),
  pluginList: document.querySelector("#plugin-list"),
  pluginImportForm: document.querySelector("#plugin-import-form"),
  pluginImportFile: document.querySelector("#plugin-import-file"),
  pluginImportEnabled: document.querySelector("#plugin-import-enabled"),
  pluginImportReplace: document.querySelector("#plugin-import-replace"),
  pluginImportSubmit: document.querySelector("#plugin-import-submit"),
  levelLegend: document.querySelector("#level-legend"),
  prevPage: document.querySelector("#prev-page"),
  nextPage: document.querySelector("#next-page"),
  saveUser: document.querySelector("#save-user"),
  navButtons: [...document.querySelectorAll("[data-section-target]")]
};

refs.tokenInput.value = state.token;

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

function withReturnTo(path, returnTo = currentRelativePath()) {
  const safePath = toSameOriginPath(path, "");
  if (!safePath) {
    return "";
  }

  const url = new URL(safePath, window.location.origin);
  const safeReturnTo = toSameOriginPath(returnTo, "");
  if (safeReturnTo) {
    url.searchParams.set("return_to", safeReturnTo);
  }
  return `${url.pathname}${url.search}${url.hash}`;
}

function getLevelMeta(levelCode) {
  return LEVEL_META[(levelCode || "").toLowerCase()] || UNKNOWN_LEVEL;
}

function isNarrowScreen() {
  return window.matchMedia("(max-width: 1039px)").matches;
}

function normalizeError(error, fallback = "操作失败，请稍后再试。") {
  const message = String(error?.message || fallback || "").trim();
  if (!message) return fallback;
  if (message === "Failed to fetch") {
    return "网络请求失败，请稍后重试。";
  }
  if (message.startsWith("Unexpected token")) {
    return "服务返回了异常数据，请稍后重试。";
  }
  if (message === "Internal Server Error") {
    return "服务暂时不可用，请稍后重试。";
  }
  return message;
}

function touchFeedback(tone = "success") {
  if (!tgApp?.HapticFeedback) return;
  if (tone === "error") {
    tgApp.HapticFeedback.notificationOccurred("error");
    return;
  }
  if (tone === "warning") {
    tgApp.HapticFeedback.notificationOccurred("warning");
    return;
  }
  tgApp.HapticFeedback.notificationOccurred("success");
}

function toneTitle(tone = "info") {
  if (tone === "error") return "操作失败";
  if (tone === "warning") return "请注意";
  if (tone === "success") return "操作成功";
  return "系统提示";
}

function toneMessage(tone = "info") {
  if (tone === "error") return "处理过程中出现异常，请稍后重试。";
  if (tone === "warning") return "请确认当前操作后继续。";
  if (tone === "success") return "操作已经完成。";
  return "正在同步当前状态。";
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

function handleBackNavigation() {
  const modalLayer = document.querySelector("#modal-layer");
  if (modalLayer && !modalLayer.classList.contains("hidden")) {
    closeInlinePopup();
    return;
  }

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

  if (refs.pageBackButton) {
    refs.pageBackButton.textContent = hasPrevious ? "返回上一级" : "返回首页";
    refs.pageBackButton.addEventListener("click", handleBackNavigation);
  }

  if (tgBackButton) {
    tgBackButton.offClick?.(handleBackNavigation);
    tgBackButton.onClick(handleBackNavigation);
    tgBackButton.show();
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
window.addEventListener("beforeunload", () => {
  tgBackButton?.offClick?.(handleBackNavigation);
});

async function popup(title, message, tone = "success") {
  touchFeedback(tone);
  const layer = document.querySelector("#modal-layer");
  const label = document.querySelector("#modal-label");
  const titleNode = document.querySelector("#modal-title");
  const messageNode = document.querySelector("#modal-message");

  if (!layer || !label || !titleNode || !messageNode) {
    window.alert(`${title}\n\n${message}`);
    return;
  }

  if (popupResolver) {
    closeInlinePopup();
  }

  label.textContent = toneTitle(tone);
  titleNode.textContent = title || toneTitle(tone);
  messageNode.textContent = message || toneMessage(tone);
  layer.classList.remove("hidden");
  layer.setAttribute("aria-hidden", "false");
  document.body.classList.add("is-modal-open");

  return new Promise((resolve) => {
    popupResolver = resolve;
  });
}

function setAdminStatus(text, tone = "info") {
  refs.adminStatus.textContent = text;
  refs.adminStatus.dataset.tone = tone;
}

function setAuthMode(mode = null) {
  const meta = {
    telegram: { text: "主人直登", tone: "normal" },
    token: { text: "令牌登录", tone: "vip" },
    none: { text: "待认证", tone: "pending" }
  }[mode || "none"];

  refs.authModePill.className = `badge badge--${meta.tone}`;
  refs.authModePill.textContent = meta.text;
}

function setSelectedUserPill(text = "未选中用户") {
  refs.selectedUserPill.textContent = text;
}

function setAuthCopy(title, status) {
  refs.authTitle.textContent = title;
  refs.authStatus.textContent = status;
}

function setActiveNav(sectionId) {
  refs.navButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.sectionTarget === sectionId);
  });
}

function focusSection(sectionId, smooth = true) {
  const section = document.getElementById(sectionId);
  if (!section) return;
  section.open = true;
  setActiveNav(sectionId);
  section.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" });
}

function toggleSections(open) {
  document.querySelectorAll(".fold-card").forEach((card) => {
    card.open = open;
  });
}

function authHeaders() {
  if (state.authMode === "telegram" && state.telegramInitData) {
    return { "X-Telegram-Init-Data": state.telegramInitData };
  }

  if (state.token) {
    return { "X-Admin-Token": state.token };
  }

  return {};
}

async function readPayload(response) {
  const raw = await response.text();
  if (!raw) {
    return { code: response.ok ? 200 : response.status, data: null };
  }
  try {
    return JSON.parse(raw);
  } catch {
    throw new Error(raw.trim() || `请求失败（HTTP ${response.status}）`);
  }
}

async function api(path, options = {}) {
  const headers = {
    ...authHeaders(),
    ...(options.headers || {})
  };

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }

  const response = await fetch(path, {
    ...options,
    headers
  });
  const payload = await readPayload(response);

  if (!response.ok || payload.code !== 200) {
    throw new Error(payload.detail || payload.message || `请求失败（HTTP ${response.status}）`);
  }

  return payload;
}

async function patchPlugin(pluginId, payload) {
  return api(`/admin-api/plugins/${encodeURIComponent(pluginId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

async function importPluginArchive(file, options = {}) {
  const body = new FormData();
  body.append("file", file);
  body.append("enabled", String(Boolean(options.enabled)));
  body.append("replace_existing", String(Boolean(options.replaceExisting)));
  return api("/admin-api/plugins/import", {
    method: "POST",
    body
  });
}

function resolveDownloadFilename(contentDisposition, fallback = "pivkeyu-migration.zip") {
  if (!contentDisposition) {
    return fallback;
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }

  const plainMatch = contentDisposition.match(/filename=\"?([^\";]+)\"?/i);
  return plainMatch?.[1] || fallback;
}

async function downloadMigrationBundle() {
  const response = await fetch("/admin-api/system/migration/export", {
    headers: authHeaders()
  });

  if (!response.ok) {
    const payload = await readPayload(response);
    throw new Error(payload.detail || payload.message || `请求失败（HTTP ${response.status}）`);
  }

  const blob = await response.blob();
  const filename = resolveDownloadFilename(
    response.headers.get("content-disposition"),
    `pivkeyu-migration-${Date.now()}.zip`
  );
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

async function importMigrationArchive(file, options = {}) {
  const body = new FormData();
  body.append("file", file);
  body.append("restore_config_file", String(Boolean(options.restoreConfig)));
  body.append("restart_after_import", String(Boolean(options.restartAfterImport)));
  return api("/admin-api/system/migration/import", {
    method: "POST",
    body
  });
}

function toLocalValue(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function fromLocalValue(value) {
  return value ? new Date(value).toISOString() : null;
}

function fmtDateTime(value) {
  if (!value) return "未设置";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "未设置";
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function formatCount(value) {
  return Number(value ?? 0).toLocaleString("zh-CN");
}

function fmtActor(actor) {
  if (!actor) return "暂无信息";
  const parts = [
    actor.tg_display_label || `TG ${actor.tg}`,
    actor.tg ? `TG ${actor.tg}` : "",
    actor.tg_username ? `@${actor.tg_username}` : "",
    actor.emby_name ? `Emby ${actor.emby_name}` : "",
    actor.embyid ? `ID ${actor.embyid}` : "",
    actor.lv_text || ""
  ].filter(Boolean);
  return parts.join(" · ");
}

function setCodeSummary(summary = {}) {
  document.querySelector("#codes-total").textContent = formatCount(summary.all);
  document.querySelector("#codes-unused").textContent = formatCount(summary.unused);
  document.querySelector("#codes-used").textContent = formatCount(summary.used);
  document.querySelector("#codes-exhausted").textContent = formatCount(summary.exhausted);

  refs.codeStatusButtons.forEach((button) => {
    const status = button.dataset.codeStatus;
    const count = summary[status];
    const labelMap = {
      all: "全部",
      unused: "未使用",
      used: "已使用"
    };
    button.textContent = typeof count === "number" ? `${labelMap[status]} (${formatCount(count)})` : labelMap[status];
    button.classList.toggle("is-active", status === state.codeStatus);
  });
}

function syncCodeSelectionActions() {
  const visibleCodes = state.visibleCodes.map((item) => item.code);
  const allVisibleSelected = visibleCodes.length > 0 && visibleCodes.every((code) => state.selectedCodes.has(code));
  refs.codeSelectPage.textContent = allVisibleSelected ? "取消本页" : "全选本页";
  refs.codeDeleteSelected.disabled = state.selectedCodes.size === 0;
  refs.codeDeleteSelected.textContent = state.selectedCodes.size ? `删除已选 (${state.selectedCodes.size})` : "删除已选";
  refs.codeClearSelection.disabled = state.selectedCodes.size === 0;
}

function renderCodeCreateResult(payload) {
  refs.codeResult.classList.remove("hidden");
  refs.codeResultTitle.textContent = `${payload.type_text}生成完成`;
  refs.codeResultMeta.textContent = `${payload.days} 天 · ${payload.count} 个 · ${payload.method} 模式 · 每码 ${payload.usage_limit} 次`;
  refs.codeOutput.value = (payload.items || []).map((item) => item.display || item.code || "").filter(Boolean).join("\n");
}

async function runButtonAction(button, pendingText, handler) {
  if (!button) {
    return handler();
  }

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

function renderLevelLegend() {
  refs.levelLegend.innerHTML = "";

  Object.values(LEVEL_META).forEach((meta) => {
    const item = document.createElement("article");
    item.className = "level-chip";
    item.innerHTML = `
      <div class="level-chip-head">
        <strong>${escapeHtml(meta.text)} (${escapeHtml(meta.code.toUpperCase())})</strong>
        <span class="badge badge--${escapeHtml(meta.tone)}">${escapeHtml(meta.shortText)}</span>
      </div>
      <p>${escapeHtml(meta.description)}</p>
    `;
    refs.levelLegend.appendChild(item);
  });
}

function setSummary(data) {
  document.querySelector("#summary-total").textContent = formatCount(data.total_users);
  document.querySelector("#summary-active").textContent = formatCount(data.active_accounts);
  document.querySelector("#summary-banned").textContent = formatCount(data.banned_users);
  document.querySelector("#summary-currency").textContent = formatCount(data.total_currency);
}

function setAutoUpdate(data = {}) {
  refs.autoUpdateEnabledText.textContent = data.status ? "已启用" : "已关闭";
  refs.autoUpdateLastChecked.textContent = fmtDateTime(data.last_checked_at);
  refs.autoUpdateLastStatus.textContent = data.last_status || "未运行";
  refs.autoUpdateCommitSha.textContent = data.commit_sha ? String(data.commit_sha).slice(0, 7) : "未记录";
  refs.autoUpdateStatus.checked = Boolean(data.status);
  refs.autoUpdateGitRepo.value = data.git_repo || "";
  refs.autoUpdateDockerImage.value = data.docker_image || "";
  refs.autoUpdateComposeService.value = data.compose_service || "";
  refs.autoUpdateContainerName.value = data.container_name || "";
  refs.autoUpdateInterval.value = Number(data.check_interval_minutes || 30);
  refs.autoUpdateNote.textContent = data.up_description || data.last_error || "保存后会按设定间隔检查 GitHub 与 Docker 镜像。";
  refs.autoUpdateNote.dataset.tone = data.last_error ? "error" : "info";
}

function renderUsers(items) {
  refs.userList.innerHTML = "";

  if (!items.length) {
    refs.userList.innerHTML = `
      <article class="user-card">
        <div class="user-name">没有查到记录</div>
        <p class="user-meta stack-empty">可以更换关键词，或者翻页继续查看。</p>
      </article>
    `;
    return;
  }

  for (const item of items) {
    const level = getLevelMeta(item.lv);
    const primaryName = item.tg_display_label || item.name || item.embyid || `TG ${item.tg}`;
    const secondaryBits = [
      `账号 ID ${escapeHtml(item.tg)}`,
      item.embyid ? `Emby ID ${escapeHtml(item.embyid)}` : "",
      item.name ? `Emby 名称 ${escapeHtml(item.name)}` : ""
    ].filter(Boolean);
    const secondary = secondaryBits.join(" · ");
    const card = document.createElement("button");
    card.type = "button";
    card.className = `user-card${state.selectedTg === item.tg ? " is-selected" : ""}`;
    card.innerHTML = `
      <div class="user-card-top">
        <div>
          <div class="user-name">${escapeHtml(primaryName)}</div>
          <div class="user-subline">${secondary}</div>
        </div>
        <span class="badge badge--${escapeHtml(item.lv_tone || level.tone)}">${escapeHtml(item.lv_text || level.text)}</span>
      </div>
      <div class="user-meta">
        <div>账户余额：${escapeHtml(item.iv ?? 0)} · 注册/续期天数：${escapeHtml(item.us ?? 0)}</div>
        <div>到期时间：${escapeHtml(fmtDateTime(item.ex))}</div>
      </div>
    `;
    card.addEventListener("click", () => loadUser(item.tg));
    refs.userList.appendChild(card);
  }
}

function renderCodes(items) {
  refs.codeList.innerHTML = "";

  if (!items.length) {
    refs.codeList.innerHTML = `
      <article class="user-card">
        <div class="user-name">当前分类没有注册码</div>
        <p class="user-meta stack-empty">可以切换到其他分类，或先批量生成一批新的注册码。</p>
      </article>
    `;
    syncCodeSelectionActions();
    return;
  }

  for (const item of items) {
    const card = document.createElement("article");
    card.className = "code-card";
    const redeemerHtml = item.redeemers?.length
      ? item.redeemers.map((redeemer) => `
          <div class="code-actor-line">
            <strong>第 ${escapeHtml(redeemer.use_index)} 次</strong>
            <span>${escapeHtml(fmtActor(redeemer.actor))}</span>
            <span>${escapeHtml(fmtDateTime(redeemer.redeemed_at))}</span>
          </div>
        `).join("")
      : `<p class="plugin-meta stack-empty">还没有使用记录。</p>`;

    card.innerHTML = `
      <div class="code-card-top">
        <label class="code-check">
          <input type="checkbox" data-code-select="${escapeHtml(item.code)}" ${state.selectedCodes.has(item.code) ? "checked" : ""}>
          <span>选择</span>
        </label>
        <div class="code-card-badges">
          <span class="badge badge--${item.kind === "renew" ? "vip" : "normal"}">${escapeHtml(item.kind_text)}</span>
          <span class="badge badge--${item.status === "unused" ? "pending" : "normal"}">${escapeHtml(item.status_text)}</span>
          ${item.is_exhausted ? `<span class="badge badge--danger">已用尽</span>` : ""}
        </div>
      </div>
      <div class="user-name code-value">${escapeHtml(item.code)}</div>
      <div class="user-subline">天数 ${escapeHtml(item.days)} · 使用进度 ${escapeHtml(item.use_count)}/${escapeHtml(item.use_limit)} · 剩余 ${escapeHtml(item.remaining_uses)}</div>
      <div class="code-info-grid">
        <section class="code-info-block">
          <h4>邀请人 / 创建人</h4>
          <p>${escapeHtml(fmtActor(item.creator))}</p>
        </section>
        <section class="code-info-block">
          <h4>最近使用者</h4>
          <p>${escapeHtml(fmtActor(item.latest_redeemer))}</p>
          <p class="plugin-meta">最近时间：${escapeHtml(fmtDateTime(item.usedtime))}</p>
        </section>
      </div>
      <section class="code-info-block">
        <h4>被邀请人 / 使用者详情</h4>
        <div class="code-redeemer-list">${redeemerHtml}</div>
      </section>
    `;
    refs.codeList.appendChild(card);
  }

  syncCodeSelectionActions();
}

function renderPlugins(items) {
  refs.pluginList.innerHTML = "";

  if (!items.length) {
    refs.pluginList.innerHTML = `
      <article class="plugin-card">
        <div class="plugin-name">暂无插件</div>
        <p class="plugin-meta stack-empty">当前没有发现可展示的扩展玩法。</p>
      </article>
    `;
    return;
  }

  for (const item of items) {
    const hasError = Boolean(item.error);
    const disablePending = Boolean(item.runtime_disable_pending);
    const migration = item.migration_summary || {};
    const installScopeText = item.install_scope === "runtime" ? "运行时插件" : "内置插件";
    const pluginTypeText = item.plugin_type === "core"
      ? "核心扩展"
      : item.plugin_type === "builtin"
        ? "内建插件"
        : "运行时玩法";
    const permissionsText = item.permissions?.length ? item.permissions.join("、") : "未声明";
    let stateText = "未启用";
    let tone = "unknown";
    if (hasError) {
      stateText = "启动异常";
      tone = "danger";
    } else if (item.requires_container_rebuild && !item.loaded) {
      stateText = "待重建";
      tone = "pending";
    } else if (disablePending) {
      stateText = "停用待重启";
      tone = "pending";
    } else if (item.loaded) {
      stateText = "已加载";
      tone = "normal";
    } else if (item.enabled) {
      stateText = "待命";
      tone = "pending";
    }
    const card = document.createElement("article");
    card.className = "plugin-card";

    const actions = [];
    actions.push(
      `<button type="button" class="ghost-button" data-plugin-enable="${escapeHtml(item.id)}" data-plugin-enabled="${item.enabled ? "1" : "0"}">
        ${item.enabled ? "禁用插件" : "启用插件"}
      </button>`
    );
    if (item.admin_path) {
      actions.push(`<a class="ghost-button" href="${escapeHtml(withReturnTo(item.admin_path))}">打开插件后台</a>`);
    }
    if (item.miniapp_path && item.enabled) {
      actions.push(`<a class="ghost-button" href="${escapeHtml(item.miniapp_path)}">打开插件页面</a>`);
      actions.push(
        `<button type="button" class="ghost-button" data-plugin-toggle="${escapeHtml(item.id)}" data-plugin-visible="${item.bottom_nav_visible ? "1" : "0"}">
          ${item.bottom_nav_visible ? "从首页底栏隐藏" : "显示到首页底栏"}
        </button>`
      );
    }

    card.innerHTML = `
      <div class="plugin-card-top">
        <div class="plugin-name">${escapeHtml(item.name)}</div>
        <span class="badge badge--${escapeHtml(tone)}">${escapeHtml(stateText)}</span>
      </div>
      <p class="plugin-meta">${escapeHtml(item.description || "暂无描述")}</p>
      <div class="plugin-meta">插件标识：${escapeHtml(item.id)} · 版本 ${escapeHtml(item.version)}</div>
      <div class="plugin-meta">来源：${escapeHtml(installScopeText)} · 类型：${escapeHtml(pluginTypeText)}</div>
      <div class="plugin-meta">默认状态：${item.manifest_enabled ? "启用" : "禁用"} · 当前状态：${item.enabled ? "启用" : "禁用"}</div>
      <div class="plugin-meta">权限声明：${escapeHtml(permissionsText)}</div>
      ${item.miniapp_path ? `<div class="plugin-meta">首页入口：${escapeHtml(item.miniapp_label || item.name)} · 底栏${item.bottom_nav_visible ? "已显示" : "已隐藏"}</div>` : ""}
      ${migration.supported ? `<div class="plugin-meta">插件迁移：已执行 ${escapeHtml(migration.applied ?? 0)} / ${escapeHtml(migration.total ?? 0)}${migration.pending ? ` · 待执行 ${escapeHtml(migration.pending)}` : ""}</div>` : ""}
      ${item.requires_restart ? `<div class="plugin-meta">说明：该插件声明本次安装或更新后需要重启才能完全生效。</div>` : ""}
      ${item.requires_container_rebuild ? `<div class="plugin-meta">说明：该插件需要重建 Docker 容器或补齐依赖后才能完全启用。</div>` : ""}
      ${item.permission_review_required ? `<div class="plugin-meta">权限审查：存在未登记权限 ${escapeHtml((item.unknown_permissions || []).join("、") || "未说明")}，建议先人工确认。</div>` : ""}
      ${item.missing_python_dependencies?.length ? `<div class="plugin-meta">缺少依赖：${escapeHtml(item.missing_python_dependencies.join("、"))}</div>` : ""}
      ${item.overrides_builtin ? `<div class="plugin-meta">说明：当前运行时插件已覆盖同名内置插件。</div>` : ""}
      ${disablePending ? `<div class="plugin-meta">说明：当前进程仍保留该插件，重启本女仆后会完全停用。</div>` : ""}
      ${item.error ? `<div class="plugin-meta">错误信息：${escapeHtml(item.error)}</div>` : ""}
      ${actions.length ? `<div class="plugin-actions">${actions.join("")}</div>` : ""}
    `;
    refs.pluginList.appendChild(card);
  }
}

function fillEditor(item) {
  const level = getLevelMeta(item.lv);

  document.querySelector("#field-tg").value = item.tg ?? "";
  document.querySelector("#field-lv").value = item.lv ?? "d";
  document.querySelector("#field-name").value = item.name ?? "";
  document.querySelector("#field-embyid").value = item.embyid ?? "";
  document.querySelector("#field-iv").value = item.iv ?? 0;
  document.querySelector("#field-us").value = item.us ?? 0;
  document.querySelector("#field-pwd").value = item.pwd ?? "";
  document.querySelector("#field-pwd2").value = item.pwd2 ?? "";
  document.querySelector("#field-cr").value = toLocalValue(item.cr);
  document.querySelector("#field-ex").value = toLocalValue(item.ex);
  document.querySelector("#field-ch").value = toLocalValue(item.ch);

  refs.editorStatus.textContent = `当前正在编辑账号 ${item.tg} · ${item.lv_text || level.text}`;
  setSelectedUserPill(`正在编辑 ${item.tg_display_label || item.name || item.embyid || `TG ${item.tg}`}`);
}

async function loadSummary() {
  const result = await api("/admin-api/summary");
  setSummary(result.data);
  setAutoUpdate(result.data.auto_update || {});
}

async function loadAutoUpdate() {
  const result = await api("/admin-api/system/auto-update");
  setAutoUpdate(result.data || {});
}

async function loadPlugins() {
  const result = await api("/admin-api/plugins");
  renderPlugins(result.data);
}

async function loadUsers() {
  const params = new URLSearchParams({
    page: String(state.page),
    page_size: String(state.pageSize)
  });

  if (state.query) {
    params.set("q", state.query);
  }

  const result = await api(`/admin-api/users?${params.toString()}`);
  const { items, page, page_size, total } = result.data;
  state.visibleUsers = items;
  renderUsers(items);

  const totalPages = Math.max(1, Math.ceil(total / page_size));
  refs.pageLabel.textContent = `第 ${page} 页 / 共 ${totalPages} 页`;
  refs.prevPage.disabled = page <= 1;
  refs.nextPage.disabled = page >= totalPages;
}

async function loadCodes() {
  const params = new URLSearchParams({
    status: state.codeStatus,
    page: String(state.codesPage),
    page_size: String(state.codesPageSize)
  });

  const result = await api(`/admin-api/codes?${params.toString()}`);
  const { items, page, page_size, total, summary } = result.data;
  state.visibleCodes = items;
  setCodeSummary(summary);
  renderCodes(items);

  const totalPages = Math.max(1, Math.ceil(total / page_size));
  refs.codePageLabel.textContent = `第 ${page} 页 / 共 ${totalPages} 页`;
  refs.codePrevPage.disabled = page <= 1;
  refs.codeNextPage.disabled = page >= totalPages;
}

async function loadUser(tg) {
  try {
    const result = await api(`/admin-api/users/${tg}`);
    state.selectedTg = tg;
    fillEditor(result.data);
    renderUsers(state.visibleUsers);
    setAdminStatus(`已载入账号 ${tg} 的资料，可以开始编辑。`);
    setActiveNav("editor-section");

    if (isNarrowScreen()) {
      focusSection("editor-section");
    }
  } catch (error) {
    const message = normalizeError(error);
    setAdminStatus(`载入用户资料失败：${message}`, "error");
    showToast(`载入用户资料失败：${message}`, "error");
    await popup("载入失败", message, "error");
  }
}

async function refreshDashboard() {
  await Promise.all([loadSummary(), loadAutoUpdate(), loadPlugins(), loadUsers(), loadCodes()]);
}

async function tryTelegramAuth() {
  if (!state.telegramInitData) {
    return false;
  }

  state.authMode = "telegram";
  setAuthMode("telegram");

  const name = state.telegramUser?.first_name || "主人";
  setAuthCopy("主人直登", `正在以主人身份验证，当前账号：${name}`);
  setAdminStatus("正在通过主人直登加载后台数据。");

  try {
    await refreshDashboard();
    refs.tokenPanel.open = false;
    setAuthCopy("主人直登", `已通过主人身份登录，当前账号：${name}`);
    setAdminStatus("主人身份验证通过，后台数据已同步。", "success");
    return true;
  } catch (error) {
    const message = normalizeError(error);
    state.authMode = null;
    setAuthMode(null);
    setAuthCopy("主人登录", `自动登录失败：${message}`);
    setAdminStatus("自动登录失败，可改用后台令牌继续访问。", "warning");
    refs.tokenPanel.open = true;
    return false;
  }
}

async function tryTokenAuth(options = {}) {
  const { notify = false } = options;
  if (!state.token) {
    return false;
  }

  state.authMode = "token";
  setAuthMode("token");
  setAuthCopy("令牌登录", "正在验证后台令牌...");
  setAdminStatus("正在验证后台令牌并加载管理数据。");

  try {
    await refreshDashboard();
    setAuthCopy("令牌登录", "后台令牌验证通过，当前页面已连接管理接口。");
    setAdminStatus("后台令牌验证通过，数据已加载。", "success");
    if (notify) {
      showToast("后台令牌验证通过。", "success");
      await popup("验证通过", "后台令牌验证通过，当前页面已连接管理接口。", "success");
    }
    return true;
  } catch (error) {
    const message = normalizeError(error);
    state.authMode = null;
    setAuthMode(null);
    setAuthCopy("主人登录", `令牌登录失败：${message}`);
    setAdminStatus("后台令牌验证失败，请检查后重试。", "error");
    refs.tokenPanel.open = true;
    if (notify) {
      showToast(`令牌登录失败：${message}`, "error");
      await popup("验证失败", message, "error");
    }
    return false;
  }
}

async function saveUser(event) {
  event.preventDefault();

  if (!state.selectedTg) {
    refs.editorStatus.textContent = "请先从用户列表选择一个账号，再保存修改。";
    showToast("请先从用户列表选择一个账号。", "warning");
    await popup("无法保存", "请先从用户列表选择一个账号，再保存修改。", "warning");
    return;
  }

  const payload = {
    lv: document.querySelector("#field-lv").value,
    name: document.querySelector("#field-name").value || null,
    embyid: document.querySelector("#field-embyid").value || null,
    iv: Number(document.querySelector("#field-iv").value || 0),
    us: Number(document.querySelector("#field-us").value || 0),
    pwd: document.querySelector("#field-pwd").value || null,
    pwd2: document.querySelector("#field-pwd2").value || null,
    cr: fromLocalValue(document.querySelector("#field-cr").value),
    ex: fromLocalValue(document.querySelector("#field-ex").value),
    ch: fromLocalValue(document.querySelector("#field-ch").value)
  };

  try {
    const result = await runButtonAction(refs.saveUser, "正在保存...", () => api(`/admin-api/users/${state.selectedTg}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    }));
    fillEditor(result.data);
    await Promise.all([loadSummary(), loadUsers()]);
    refs.editorStatus.textContent = `账号 ${state.selectedTg} 的资料已保存。`;
    setAdminStatus(`账号 ${state.selectedTg} 的资料已更新。`, "success");
    showToast(`账号 ${state.selectedTg} 已保存。`, "success");
    await popup("保存成功", `账号 ${state.selectedTg} 的资料已更新。`, "success");
  } catch (error) {
    const message = normalizeError(error);
    refs.editorStatus.textContent = `保存失败：${message}`;
    setAdminStatus(`保存失败：${message}`, "error");
    showToast(`保存失败：${message}`, "error");
    await popup("保存失败", message, "error");
  }
}

async function createCodes(event) {
  event.preventDefault();

  const payload = {
    days: Number(document.querySelector("#code-create-days").value || 0),
    count: Number(document.querySelector("#code-create-count").value || 0),
    method: document.querySelector("#code-create-method").value,
    type: document.querySelector("#code-create-type").value,
    usage_limit: Number(document.querySelector("#code-create-usage-limit").value || 1),
    suffix_mode: refs.codeCreateSuffixMode.value,
    suffix_text: refs.codeCreateSuffixText.value.trim() || null
  };

  try {
    const result = await runButtonAction(refs.codeCreateSubmit, "生成中...", () => api("/admin-api/codes", {
      method: "POST",
      body: JSON.stringify(payload)
    }));
    renderCodeCreateResult(result.data);
    state.selectedCodes.clear();
    await loadCodes();
    setAdminStatus(`${result.data.type_text}已生成 ${result.data.count} 个。`, "success");
    showToast(`${result.data.type_text}已生成 ${result.data.count} 个。`, "success");
    focusSection("codes-section", false);
  } catch (error) {
    const message = normalizeError(error);
    setAdminStatus(`生成注册码失败：${message}`, "error");
    showToast(`生成失败：${message}`, "error");
    await popup("生成失败", message, "error");
  }
}

async function saveAutoUpdate(event) {
  event.preventDefault();

  const payload = {
    status: refs.autoUpdateStatus.checked,
    git_repo: refs.autoUpdateGitRepo.value.trim() || null,
    docker_image: refs.autoUpdateDockerImage.value.trim() || null,
    compose_service: refs.autoUpdateComposeService.value.trim() || null,
    container_name: refs.autoUpdateContainerName.value.trim() || null,
    check_interval_minutes: Number(refs.autoUpdateInterval.value || 30)
  };

  try {
    const result = await runButtonAction(refs.autoUpdateSave, "保存中...", () => api("/admin-api/system/auto-update", {
      method: "PATCH",
      body: JSON.stringify(payload)
    }));
    setAutoUpdate(result.data || {});
    setAdminStatus("自动更新配置已保存。", "success");
    showToast("自动更新配置已保存。", "success");
    await popup("保存成功", "自动更新配置已保存，新的定时规则已经生效。", "success");
  } catch (error) {
    const message = normalizeError(error);
    setAdminStatus(`保存自动更新配置失败：${message}`, "error");
    showToast(`保存失败：${message}`, "error");
    await popup("保存失败", message, "error");
  }
}

async function deleteSelectedCodes() {
  const codes = [...state.selectedCodes];
  if (!codes.length) {
    setAdminStatus("请先勾选需要删除的注册码。", "warning");
    showToast("请先勾选需要删除的注册码。", "warning");
    return;
  }

  const confirmed = window.confirm(`确认删除选中的 ${codes.length} 个注册码吗？已使用记录也会一并删除。`);
  if (!confirmed) {
    return;
  }

  try {
    const result = await runButtonAction(refs.codeDeleteSelected, "删除中...", () => api("/admin-api/codes/delete", {
      method: "POST",
      body: JSON.stringify({ codes })
    }));
    state.selectedCodes.clear();
    await loadCodes();
    setAdminStatus(`已删除 ${result.data.deleted} 个注册码。`, "success");
    showToast(`已删除 ${result.data.deleted} 个注册码。`, "success");
    await popup("删除完成", `已删除 ${result.data.deleted} 个注册码，对应使用记录删除 ${result.data.redeem_deleted} 条。`, "success");
  } catch (error) {
    const message = normalizeError(error);
    setAdminStatus(`删除注册码失败：${message}`, "error");
    showToast(`删除失败：${message}`, "error");
    await popup("删除失败", message, "error");
  }
}

function bindNavigation() {
  refs.navButtons.forEach((button) => {
    button.addEventListener("click", () => {
      focusSection(button.dataset.sectionTarget);
    });
  });

  document.querySelector("[data-open-all]")?.addEventListener("click", () => {
    toggleSections(true);
  });

  document.querySelector("[data-close-all]")?.addEventListener("click", () => {
    toggleSections(false);
  });
}

function syncSuffixField() {
  const fixed = refs.codeCreateSuffixMode.value === "fixed";
  refs.codeCreateSuffixText.disabled = !fixed;
  if (!fixed) {
    refs.codeCreateSuffixText.value = "";
  }
}

refs.codeCreateForm?.addEventListener("submit", createCodes);
refs.autoUpdateForm?.addEventListener("submit", saveAutoUpdate);
refs.codeCreateSuffixMode?.addEventListener("change", syncSuffixField);
refs.codeCreateCopy?.addEventListener("click", async () => {
  const value = refs.codeOutput.value.trim();
  if (!value) {
    return;
  }

  try {
    await navigator.clipboard.writeText(value);
    showToast("生成结果已复制。", "success");
  } catch (error) {
    showToast("复制失败，请手动选择内容。", "warning");
  }
});

refs.codeStatusButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    state.codeStatus = button.dataset.codeStatus || "all";
    state.codesPage = 1;
    try {
      await loadCodes();
      setActiveNav("codes-section");
      setAdminStatus(`注册码列表已切换到“${button.textContent}”。`);
    } catch (error) {
      const message = normalizeError(error);
      setAdminStatus(`加载注册码失败：${message}`, "error");
      showToast(`加载失败：${message}`, "error");
    }
  });
});

refs.codePrevPage?.addEventListener("click", async () => {
  if (state.codesPage <= 1) {
    return;
  }

  state.codesPage -= 1;
  try {
    await loadCodes();
  } catch (error) {
    const message = normalizeError(error);
    setAdminStatus(`注册码翻页失败：${message}`, "error");
    showToast(`翻页失败：${message}`, "error");
  }
});

refs.codeNextPage?.addEventListener("click", async () => {
  state.codesPage += 1;
  try {
    await loadCodes();
  } catch (error) {
    const message = normalizeError(error);
    setAdminStatus(`注册码翻页失败：${message}`, "error");
    showToast(`翻页失败：${message}`, "error");
  }
});

refs.codeSelectPage?.addEventListener("click", () => {
  const visibleCodes = state.visibleCodes.map((item) => item.code);
  const allVisibleSelected = visibleCodes.length > 0 && visibleCodes.every((code) => state.selectedCodes.has(code));

  visibleCodes.forEach((code) => {
    if (allVisibleSelected) {
      state.selectedCodes.delete(code);
    } else {
      state.selectedCodes.add(code);
    }
  });

  renderCodes(state.visibleCodes);
});

refs.codeClearSelection?.addEventListener("click", () => {
  state.selectedCodes.clear();
  renderCodes(state.visibleCodes);
});

refs.codeDeleteSelected?.addEventListener("click", deleteSelectedCodes);

refs.migrationExportButton?.addEventListener("click", async () => {
  try {
    await runButtonAction(refs.migrationExportButton, "打包中...", downloadMigrationBundle);
    const message = "迁移压缩包已开始下载，包含数据库快照、插件信息和当前运行时数据。";
    setAdminStatus(message, "success");
    refs.migrationNote.textContent = message;
    refs.migrationNote.dataset.tone = "info";
    showToast("迁移压缩包已开始下载。", "success");
  } catch (error) {
    const message = normalizeError(error);
    setAdminStatus(`导出迁移压缩包失败：${message}`, "error");
    refs.migrationNote.textContent = `导出失败：${message}`;
    refs.migrationNote.dataset.tone = "error";
    showToast(`导出失败：${message}`, "error");
    await popup("导出失败", message, "error");
  }
});

refs.migrationImportForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = refs.migrationImportFile?.files?.[0];
  if (!file) {
    setAdminStatus("请先选择迁移 ZIP 压缩包。", "warning");
    refs.migrationNote.textContent = "请先选择迁移 ZIP 压缩包，再执行导入。";
    refs.migrationNote.dataset.tone = "info";
    showToast("请先选择迁移 ZIP。", "warning");
    await popup("缺少文件", "请先选择迁移 ZIP 压缩包，再执行导入。", "warning");
    return;
  }

  const confirmed = window.confirm("导入迁移压缩包会覆盖压缩包内包含的数据库和插件数据；如果勾选了配置恢复，还会覆盖 data/config.json。是否继续？");
  if (!confirmed) {
    return;
  }

  try {
    const result = await runButtonAction(event.submitter || refs.migrationImportSubmit, "导入中...", () => importMigrationArchive(file, {
      restoreConfig: refs.migrationRestoreConfig?.checked,
      restartAfterImport: refs.migrationRestartAfterImport?.checked
    }));
    const payload = result.data || {};
    const restoredTableCount = payload.database?.restored_tables?.length || 0;
    const restoredDataCount = payload.data?.count || 0;
    const warnings = Array.isArray(payload.warnings) ? payload.warnings : [];
    const restartScheduled = Boolean(payload.restart_scheduled);
    let message = `迁移压缩包已导入，已恢复 ${restoredTableCount} 张数据表和 ${restoredDataCount} 项运行时数据。`;
    if (payload.config?.restored) {
      message += " 已同步恢复配置文件。";
    }

    if (restartScheduled) {
      message += " Bot 即将自动重启，请稍后重新进入后台。";
    } else {
      message += " 请尽快手动重启 Bot，以加载新的配置和插件状态。";
    }
    if (warnings.length) {
      message += ` 注意：${warnings.join("；")}`;
    }

    refs.migrationImportForm.reset();
    refs.migrationNote.textContent = message;
    refs.migrationNote.dataset.tone = warnings.length ? "error" : "info";
    setAdminStatus(message, restartScheduled ? "warning" : "success");
    showToast(restartScheduled ? "迁移数据已导入，Bot 即将重启。" : "迁移数据已导入。", restartScheduled ? "warning" : "success");
    await popup(restartScheduled ? "导入成功，即将重启" : "导入成功", message, restartScheduled ? "warning" : "success");
  } catch (error) {
    const message = normalizeError(error);
    setAdminStatus(`导入迁移压缩包失败：${message}`, "error");
    refs.migrationNote.textContent = `导入失败：${message}`;
    refs.migrationNote.dataset.tone = "error";
    showToast(`导入失败：${message}`, "error");
    await popup("导入失败", message, "error");
  }
});

refs.codeList?.addEventListener("change", (event) => {
  const checkbox = event.target.closest("[data-code-select]");
  if (!checkbox) {
    return;
  }

  const code = checkbox.dataset.codeSelect;
  if (!code) {
    return;
  }

  if (checkbox.checked) {
    state.selectedCodes.add(code);
  } else {
    state.selectedCodes.delete(code);
  }
  syncCodeSelectionActions();
});

refs.tokenForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  state.token = refs.tokenInput.value.trim();
  localStorage.setItem(storageKey, state.token);
  await runButtonAction(event.submitter, "正在验证...", () => tryTokenAuth({ notify: true }));
});

document.querySelector("#search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  state.page = 1;
  state.query = document.querySelector("#search-input").value.trim();
  try {
    await runButtonAction(event.submitter, "搜索中...", loadUsers);
    setAdminStatus(state.query ? `已完成搜索，关键词“${state.query}”的结果已更新。` : "已刷新全部用户列表。");
    setActiveNav("users-section");
    showToast(state.query ? `搜索完成：${state.query}` : "用户列表已刷新。", "success");
  } catch (error) {
    const message = normalizeError(error);
    setAdminStatus(`搜索失败：${message}`, "error");
    showToast(`搜索失败：${message}`, "error");
  }
});

refs.prevPage.addEventListener("click", async () => {
  if (state.page <= 1) {
    return;
  }

  state.page -= 1;
  try {
    await loadUsers();
  } catch (error) {
    const message = normalizeError(error);
    setAdminStatus(`翻页失败：${message}`, "error");
    showToast(`翻页失败：${message}`, "error");
  }
});

refs.nextPage.addEventListener("click", async () => {
  state.page += 1;
  try {
    await loadUsers();
  } catch (error) {
    const message = normalizeError(error);
    setAdminStatus(`翻页失败：${message}`, "error");
    showToast(`翻页失败：${message}`, "error");
  }
});

document.querySelector("#editor-form").addEventListener("submit", saveUser);

refs.pluginImportForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = refs.pluginImportFile?.files?.[0];
  if (!file) {
    setAdminStatus("请先选择一个插件 ZIP 压缩包。", "warning");
    showToast("请先选择插件 ZIP。", "warning");
    await popup("缺少文件", "请先选择一个插件 ZIP 压缩包，再执行导入。", "warning");
    return;
  }

  try {
    const result = await runButtonAction(event.submitter || refs.pluginImportSubmit, "导入中...", () => importPluginArchive(file, {
      enabled: refs.pluginImportEnabled?.checked,
      replaceExisting: refs.pluginImportReplace?.checked
    }));
    await loadPlugins();
    refs.pluginImportForm.reset();

    const plugin = result.data || {};
    const pendingRestart = Boolean(plugin.restart_required);
    const pendingRebuild = Boolean(plugin.container_rebuild_required);
    const hasError = Boolean(plugin.error);
    let tone = "success";
    let message = `插件 ${plugin.id || file.name} 已导入。`;

    if (pendingRebuild) {
      tone = "warning";
      message = `插件 ${plugin.id || file.name} 已导入，但需要重建 Docker 容器后才能完全启用。建议切换到本地构建模式后执行：docker compose up -d --build pivkeyu_emby`;
    } else if (hasError) {
      tone = "warning";
      message = `插件 ${plugin.id || file.name} 已导入，但加载时报错：${plugin.error}`;
    } else if (!plugin.enabled) {
      tone = "success";
      message = `插件 ${plugin.id || file.name} 已导入，当前保持禁用状态。`;
    } else if (pendingRestart) {
      tone = "warning";
      message = `插件 ${plugin.id || file.name} 已导入，但变更需要重启后才能完全生效。`;
    } else if (plugin.replaced) {
      message = `插件 ${plugin.id || file.name} 已覆盖导入并完成同步。`;
    } else {
      message = `插件 ${plugin.id || file.name} 已导入并完成同步。`;
    }

    if (plugin.replaced && plugin.backup_path) {
      message += ` 旧版本已备份到 ${plugin.backup_path}。`;
    }
    if (plugin.permission_review_required && plugin.unknown_permissions?.length) {
      message += ` 请确认新增权限：${plugin.unknown_permissions.join("、")}。`;
    }

    setAdminStatus(message, tone);
    showToast(message, tone);
    await popup(hasError ? "导入完成，但存在异常" : "导入成功", message, tone);
  } catch (error) {
    const message = normalizeError(error);
    setAdminStatus(`导入插件失败：${message}`, "error");
    showToast(`导入失败：${message}`, "error");
    await popup("导入失败", message, "error");
  }
});

refs.pluginList.addEventListener("click", async (event) => {
  const enableButton = event.target.closest("[data-plugin-enable]");
  if (enableButton) {
    const pluginId = enableButton.dataset.pluginEnable;
    const nextEnabled = enableButton.dataset.pluginEnabled !== "1";

    try {
      const result = await runButtonAction(enableButton, "更新中...", () => patchPlugin(pluginId, { enabled: nextEnabled }));
      await loadPlugins();
      const pendingRestart = Boolean(result?.data?.restart_required);
      const message = nextEnabled
        ? `插件 ${pluginId} 已启用。`
        : pendingRestart
          ? `插件 ${pluginId} 已设为禁用，重启本女仆后会完全停用。`
          : `插件 ${pluginId} 已禁用。`;
      setAdminStatus(message, pendingRestart ? "warning" : "success");
      showToast(message, pendingRestart ? "warning" : "success");
      await popup(pendingRestart ? "已更新，等待重启" : "更新成功", message, pendingRestart ? "warning" : "success");
    } catch (error) {
      const message = normalizeError(error);
      setAdminStatus(`更新插件启用状态失败：${message}`, "error");
      showToast(`更新失败：${message}`, "error");
      await popup("更新失败", message, "error");
    }
    return;
  }

  const navButton = event.target.closest("[data-plugin-toggle]");
  if (!navButton) {
    return;
  }

  const pluginId = navButton.dataset.pluginToggle;
  const nextVisible = navButton.dataset.pluginVisible !== "1";

  try {
    await runButtonAction(navButton, "更新中...", () => patchPlugin(pluginId, { bottom_nav_visible: nextVisible }));
    await loadPlugins();
    setAdminStatus(`插件 ${pluginId} 的首页底栏显示状态已更新。`, "success");
    showToast(`插件 ${pluginId} 的显示状态已更新。`, "success");
    await popup("更新成功", `插件 ${pluginId} 的首页底栏显示状态已更新。`, "success");
  } catch (error) {
    const message = normalizeError(error);
    setAdminStatus(`更新插件显示状态失败：${message}`, "error");
    showToast(`更新失败：${message}`, "error");
    await popup("更新失败", message, "error");
  }
});

(async () => {
  renderLevelLegend();
  bindNavigation();
  setAuthMode(null);
  setSelectedUserPill();
  syncSuffixField();
  syncCodeSelectionActions();

  if (tgApp) {
    tgApp.ready();
    tgApp.expand();
    tgApp.setHeaderColor("#f8f9fa");
    tgApp.setBackgroundColor("#f8f9fa");
  }

  setupBackNavigation();

  const telegramOk = await tryTelegramAuth();
  if (telegramOk) {
    return;
  }

  const tokenOk = await tryTokenAuth();
  if (tokenOk) {
    return;
  }

  setAuthCopy("主人登录", "当前未通过主人身份认证。你仍然可以在浏览器中手动输入后台令牌。");
  setAdminStatus("等待主人完成身份验证后再加载后台数据。", "warning");
  refs.tokenPanel.open = true;
})();
