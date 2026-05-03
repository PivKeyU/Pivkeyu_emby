const LEVEL_META = {
  a: {
    text: "白名单用户",
    shortText: "白名单",
    description: "享有最高权限，可访问全部媒体库。",
    tone: "vip"
  },
  b: {
    text: "普通用户",
    shortText: "普通",
    description: "已绑定 Emby 账号，可正常使用观影服务。",
    tone: "normal"
  },
  c: {
    text: "已封禁",
    shortText: "封禁",
    description: "账号已被管理员封禁，无法使用任何服务。",
    tone: "danger"
  },
  d: {
    text: "未注册",
    shortText: "未注册",
    description: "尚未绑定 Emby 账号，请联系管理员或使用注册码开通。",
    tone: "pending"
  }
};
const MINIAPP_BOOTSTRAP_CACHE_PREFIX = "miniapp_bootstrap";
let currentInviteBundle = null;
let currentMiniAppUserId = "default";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getLevelMeta(code) {
  return LEVEL_META[(code || "").toLowerCase()] || {
    text: "未知状态",
    shortText: "未知",
    description: "系统暂时无法判断当前账号状态。",
    tone: "unknown"
  };
}

function normalizeError(error) {
  const message = String(error?.message || "").trim();
  if (
    !message
    || message === "Failed to fetch"
    || message.startsWith("Unexpected token")
    || message.includes("Unexpected end of JSON input")
  ) {
    return "网络连接失败，请稍后重试。";
  }
  if (message === "Internal Server Error") {
    return "服务器内部错误，请稍后再试。";
  }
  return message;
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

function formatDate(value, fallback = "") {
  if (!value) return fallback;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? fallback : date.toLocaleString("zh-CN");
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

function visibleFoldCards() {
  return [...document.querySelectorAll(".fold-card")].filter((card) => !card.classList.contains("hidden"));
}

function syncFoldToolbar() {
  const toolbar = document.querySelector("#fold-toolbar");
  if (!toolbar) return;

  const cards = visibleFoldCards();
  toolbar.classList.toggle("hidden", cards.length < 2);

  const count = document.querySelector("#fold-count");
  if (count) {
    count.textContent = `共 ${cards.length} 个模块`;
  }

  const openAllButton = document.querySelector("[data-fold-open-all]");
  const closeAllButton = document.querySelector("[data-fold-close-all]");
  if (openAllButton) {
    openAllButton.disabled = !cards.some((card) => !card.open);
  }
  if (closeAllButton) {
    closeAllButton.disabled = !cards.some((card) => card.open);
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
  document.querySelectorAll(".fold-card").forEach((card) => {
    card.addEventListener("toggle", syncFoldToolbar);
  });
  syncFoldToolbar();
}

function renderPlugins(items) {
  const pluginGrid = document.querySelector("#plugin-grid");
  pluginGrid.innerHTML = "";

  if (!items.length) {
    pluginGrid.innerHTML = `
      <article class="plugin-item">
        <div class="plugin-mark">空</div>
        <div class="plugin-main">
          <div class="plugin-head">
            <strong>暂无可用模块</strong>
            <span class="plugin-state is-off">未启用</span>
          </div>
          <p class="plugin-copy">当前没有已启用的功能模块，请联系管理员开启。</p>
          <div class="plugin-foot">
            <div class="plugin-meta-row">
              <span class="plugin-meta">无可用模块</span>
            </div>
            <span class="plugin-ghost">暂未开启</span>
          </div>
        </div>
      </article>
    `;
    return;
  }

  for (const plugin of items) {
    const item = document.createElement("a");
    const hasError = Boolean(plugin.error);
    const stateClass = hasError ? "is-error" : plugin.loaded ? "is-on" : "is-off";
    const stateText = hasError ? "加载失败" : plugin.loaded ? "运行中" : "未加载";
    const mark = escapeHtml(String(plugin.miniapp_icon || plugin.icon || plugin.name?.slice?.(0, 1) || "模").trim().slice(0, 2));
    const description = escapeHtml(plugin.description || "暂无描述信息。");
    const name = escapeHtml(plugin.miniapp_label || plugin.name || "未命名模块");
    const version = escapeHtml(plugin.version || "v0.0");
    const errorText = hasError ? `<p class="plugin-warning">错误：${escapeHtml(plugin.error)}</p>` : "";

    item.className = "plugin-item";
    item.href = "javascript:void(0);";
    item.dataset.openPath = plugin.miniapp_path;
    item.innerHTML = `
      <div class="plugin-mark">${mark}</div>
      <div class="plugin-main">
        <div class="plugin-head">
          <strong class="plugin-title">${name}</strong>
          <span class="plugin-state ${stateClass}">${stateText}</span>
        </div>
        <p class="plugin-copy">${description}</p>
        ${errorText}
        <div class="plugin-foot">
          <div class="plugin-meta-row">
            <span class="plugin-meta">${version}</span>
          </div>
          <button class="plugin-open" onclick="window.location.href='${escapeHtml(plugin.miniapp_path)}';">进入</button>
        </div>
      </div>
    `;
    pluginGrid.appendChild(item);
  }
}

function renderBottomNav(items) {
  const nav = document.querySelector("#bottom-nav");
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

function renderInviteRecords(records = [], type = "group_join") {
  const root = document.querySelector(type === "account_open" ? "#invite-open-records" : "#invite-records");
  if (!root) return;
  if (!records.length) {
    root.innerHTML = `
      <article class="stack-item">
        <strong>暂无邀请记录</strong>
        <p>${type === "account_open" ? "提交开号申请后，这里会显示最近的审核状态。" : "成功发送邀请链接后，这里会显示最近的入群邀请状态。"}</p>
      </article>
    `;
    return;
  }
  root.innerHTML = records.map((item) => `
    <article class="stack-item">
      <strong>${type === "account_open" ? "申请 TG" : "邀请 TG"} ${escapeHtml(item.invitee_tg)} · ${escapeHtml(item.status_text || item.status || "待处理")}</strong>
      <p>${type === "account_open" ? `申请天数：${escapeHtml(item.invite_days || 0)} 天` : `目标群：${escapeHtml(item.target_chat_id || "-")}`} · 创建：${escapeHtml(formatDate(item.created_at, "未知"))}</p>
      ${type === "account_open" ? `<p>审核：${escapeHtml(formatDate(item.reviewed_at, "待审核"))}</p>` : ""}
      ${type === "account_open" ? "" : `<p>过期：${escapeHtml(formatDate(item.expires_at, "未设置"))}</p>`}
    </article>
  `).join("");
}

function renderInviteBundle(invite = {}) {
  currentInviteBundle = invite || {};
  const card = document.querySelector("#invite-card");
  const openCard = document.querySelector("#invite-open-card");
  if (!card) return;
  const settings = invite.settings || {};
  const permissions = invite.permissions || {};
  const groupJoin = invite.group_join || invite || {};
  const accountOpen = invite.account_open || {};
  const enabled = Boolean(settings.enabled);
  card.classList.toggle("hidden", !enabled);
  openCard?.classList.toggle("hidden", !enabled);
  if (!enabled) {
    syncFoldToolbar();
    return;
  }

  const status = document.querySelector("#invite-status");
  const count = Number(groupJoin.available_credits || invite.available_credits || 0);
  const canCreate = Boolean(permissions.can_create && count > 0);
  document.querySelector("#invite-credit-count").textContent = String(count);
  document.querySelector("#invite-expire-hours").textContent = `${settings.expire_hours || 24} 小时`;
  if (status) {
    if (!permissions.has_viewing_access) {
      status.textContent = "当前账号没有 Emby 观影资格，暂时不能获取入群资格。";
    } else if (permissions.group_invite_revoked) {
      status.textContent = "你的入群邀请资格已被后台撤销。";
    } else if (count <= 0) {
      status.textContent = permissions.group_invite_used
        ? "你已经使用过本次入群邀请资格。"
        : "当前没有可用的入群邀请资格。";
    } else {
      status.textContent = "填写被邀请人的 TGID 后，机器人会把专属入群链接私聊发送给对方。";
    }
  }

  const submit = document.querySelector("#invite-submit");
  if (submit) {
    submit.disabled = !canCreate;
    submit.textContent = canCreate ? "发送邀请链接" : "暂无可用入群资格";
  }
  renderInviteRecords(groupJoin.records || invite.records || [], "group_join");

  const openStatus = document.querySelector("#invite-open-status");
  const openCount = Number(accountOpen.available_credits || 0);
  const canCreateOpen = Boolean(permissions.can_create && permissions.has_account_open_application_qualification);
  document.querySelector("#invite-open-credit-count").textContent = String(openCount);
  document.querySelector("#invite-open-days").textContent = `${settings.account_open_days || 30} 天`;
  if (openStatus) {
    if (!permissions.has_viewing_access) {
      openStatus.textContent = "当前账号没有 Emby 观影资格，暂时不能申请开号资格。";
    } else if (permissions.account_open_application_revoked) {
      openStatus.textContent = "你的开号申请资格已被后台撤销。";
    } else if (permissions.account_open_application_used) {
      openStatus.textContent = "你已经提交或完成过开号申请，不能重复申请。";
    } else {
      openStatus.textContent = "填写群组中未开通用户的 TGID 后，会提交给后台审核。";
    }
  }
  const openSubmit = document.querySelector("#invite-open-submit");
  if (openSubmit) {
    openSubmit.disabled = !canCreateOpen;
    openSubmit.textContent = canCreateOpen ? "提交开号申请" : "暂无申请资格";
  }
  renderInviteRecords(accountOpen.records || [], "account_open");
  syncFoldToolbar();
}

function resolveDisplayName(user) {
  return user?.first_name || user?.last_name || user?.username || "未知用户";
}

function readLocalStorage(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeLocalStorage(key, value) {
  try {
    if (value == null) {
      window.localStorage.removeItem(key);
      return;
    }
    window.localStorage.setItem(key, value);
  } catch {
    // ignore storage failures
  }
}

function miniAppBootstrapCacheKey(userId) {
  return `${MINIAPP_BOOTSTRAP_CACHE_PREFIX}:${userId || "anon"}`;
}

function hydrateMiniAppBootstrapCache(userId) {
  const raw = readLocalStorage(miniAppBootstrapCacheKey(userId));
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || !parsed.telegram_user || !parsed.meta) {
      writeLocalStorage(miniAppBootstrapCacheKey(userId), null);
      return null;
    }
    return parsed;
  } catch {
    writeLocalStorage(miniAppBootstrapCacheKey(userId), null);
    return null;
  }
}

function storeMiniAppBootstrapCache(userId, payload) {
  if (!payload || typeof payload !== "object") return;
  writeLocalStorage(miniAppBootstrapCacheKey(userId), JSON.stringify(payload));
}

function applyMiniAppBootstrapData(data, userId) {
  const welcomeText = document.querySelector("#welcome-text");
  const heroNote = document.querySelector("#hero-note");
  const adminEntryCard = document.querySelector("#admin-entry-card");
  const adminEntryButton = document.querySelector("#admin-entry-button");
  const badge = document.querySelector("#account-level-badge");
  const levelDesc = document.querySelector("#account-level-desc");
  const pluginCount = document.querySelector("#plugin-count");
  const pluginCountPill = document.querySelector("#plugin-count-pill");
  const rolePill = document.querySelector("#role-pill");
  const { telegram_user, account, meta, permissions } = data;
  let visiblePlugins = (meta.plugins || []).filter((item) => item.miniapp_path);
  const loadedCount = visiblePlugins.filter((item) => item.loaded).length;
  const levelMeta = getLevelMeta(account?.lv || (account ? "" : "d"));
  const displayName = resolveDisplayName(telegram_user);
  const accountTone = account?.lv_tone || levelMeta.tone;

  document.title = `${meta.brand || "片刻面板"}`;

  badge.className = `badge badge--${accountTone}`;
  badge.textContent = account?.lv_short_text || account?.lv_text || levelMeta.shortText || levelMeta.text;
  levelDesc.textContent = account?.lv_description || levelMeta.description;

  document.querySelector("#tg-id").textContent = telegram_user.id || "-";
  document.querySelector("#tg-name").textContent = displayName;
  document.querySelector("#account-iv").textContent = account?.iv ?? 0;
  document.querySelector("#account-name").textContent = account?.name || "未绑定";
  document.querySelector("#account-ex").textContent = formatDate(account?.ex, "永久");
  document.querySelector("#account-us").textContent = account?.us ?? 0;

  document.querySelector("#brand-name").textContent = meta.brand || "Emby";
  document.querySelector("#currency-name").textContent = meta.currency || "积分";
  document.querySelector("#hero-name").textContent = displayName;
  document.querySelector("#hero-id").textContent = telegram_user.id || "-";

  pluginCount.textContent = `已加载 ${loadedCount} / ${visiblePlugins.length}`;
  pluginCountPill.textContent = `${visiblePlugins.length} 个模块`;
  rolePill.textContent = permissions?.is_admin ? "管理员" : "普通用户";

  if (permissions?.is_admin && permissions?.admin_url) {
    adminEntryCard.classList.remove("hidden");
    adminEntryButton.onclick = () => {
      window.location.href = withReturnTo(permissions.admin_url);
    };
  } else {
    adminEntryCard.classList.add("hidden");
    adminEntryButton.onclick = null;
  }

  welcomeText.textContent = `欢迎回来，${displayName}。`;
  heroNote.textContent = account?.name
    ? `当前已绑定 Emby 账号 ${account.name}，到期时间 ${formatDate(account.ex, "永久")}。`
    : "你尚未绑定 Emby 账号，请使用注册码开通或联系管理员。";

  const savedOrderStr = localStorage.getItem(`miniapp_order_${userId}`);
  if (savedOrderStr) {
    try {
      const savedOrder = JSON.parse(savedOrderStr);
      visiblePlugins.sort((a, b) => {
        const nameA = a.miniapp_label || a.name || "";
        const nameB = b.miniapp_label || b.name || "";
        let iA = savedOrder.indexOf(nameA);
        let iB = savedOrder.indexOf(nameB);
        if (iA === -1) iA = 999;
        if (iB === -1) iB = 999;
        return iA - iB;
      });
    } catch (error) {
      console.error("排序数据读取失败", error);
    }
  }

  renderPlugins(visiblePlugins);
  renderBottomNav(meta.bottom_nav || []);
  renderInviteBundle(data.invite || {});
}

function bindPluginGridNavigation() {
  const pluginGrid = document.querySelector("#plugin-grid");
  if (!pluginGrid || pluginGrid.dataset.bound === "1") return;
  pluginGrid.dataset.bound = "1";
  pluginGrid.addEventListener("click", (event) => {
    if (event.target.closest("button")) return;
    const card = event.target.closest("[data-open-path]");
    if (!card) return;
    window.location.href = card.dataset.openPath;
  });
}

async function bootstrapMiniApp() {
  const tg = window.Telegram?.WebApp;
  const welcomeText = document.querySelector("#welcome-text");
  const heroNote = document.querySelector("#hero-note");
  const adminEntryCard = document.querySelector("#admin-entry-card");
  const adminEntryButton = document.querySelector("#admin-entry-button");
  const badge = document.querySelector("#account-level-badge");
  const levelDesc = document.querySelector("#account-level-desc");
  const pluginCount = document.querySelector("#plugin-count");
  const pluginCountPill = document.querySelector("#plugin-count-pill");
  const rolePill = document.querySelector("#role-pill");

  if (!tg) {
    welcomeText.textContent = "请在 Telegram 小程序中打开此页面。";
    heroNote.textContent = "当前环境不支持直接访问，请使用 Telegram 客户端打开。";
    return;
  }

  tg.ready();
  tg.expand();
  bindPluginGridNavigation();
  const userId = tg.initDataUnsafe?.user?.id || "default";
  currentMiniAppUserId = userId;
  const cachedData = hydrateMiniAppBootstrapCache(userId);
  if (cachedData) {
    applyMiniAppBootstrapData(cachedData, userId);
  }

  try {
    const response = await fetch("/miniapp-api/bootstrap", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ init_data: tg.initData })
    });
    const result = await readResponsePayload(response);

    if (!response.ok || result.code !== 200) {
      throw new Error(result.detail || result.message || "服务器连接失败。");
    }

    storeMiniAppBootstrapCache(userId, result.data);
    applyMiniAppBootstrapData(result.data, userId);

  } catch (error) {
    const message = normalizeError(error);
    if (!cachedData) {
      welcomeText.textContent = `连接失败：${message}`;
      heroNote.textContent = "请检查网络后重试，或联系管理员。";
      levelDesc.textContent = "账号状态未知。";
      renderPlugins([]);
      renderBottomNav([]);
      return;
    }
    heroNote.textContent = `已展示本地缓存，最新数据同步失败：${message}`;
  }
}

async function createInviteFromMiniApp(event) {
  event.preventDefault();
  const tg = window.Telegram?.WebApp;
  if (!tg) return;
  const inviteeTg = Number(document.querySelector("#invitee-tg")?.value || 0);
  const note = document.querySelector("#invite-note")?.value?.trim() || "";
  if (!inviteeTg) {
    window.alert("请先填写被邀请人的 TGID。");
    return;
  }
  const button = document.querySelector("#invite-submit");
  const previous = button?.textContent || "";
  if (button) {
    button.disabled = true;
    button.textContent = "发送中...";
  }
  try {
    const response = await fetch("/miniapp-api/invites/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        init_data: tg.initData,
        invitee_tg: inviteeTg,
        note
      })
    });
    const result = await readResponsePayload(response);
    if (!response.ok || result.code !== 200) {
      throw new Error(result.detail || result.message || "邀请发送失败。");
    }
    renderInviteBundle(result.data?.invite || {});
    document.querySelector("#invite-form")?.reset();
    window.alert("邀请链接已由机器人私聊发送给被邀请人。");
  } catch (error) {
    renderInviteBundle(currentInviteBundle || {});
    window.alert(normalizeError(error));
  } finally {
    if (button) {
      button.textContent = previous || "发送邀请链接";
    }
    renderInviteBundle(currentInviteBundle || {});
    storeMiniAppBootstrapCache(currentMiniAppUserId, {
      ...(hydrateMiniAppBootstrapCache(currentMiniAppUserId) || {}),
      invite: currentInviteBundle
    });
  }
}

async function createAccountOpenInviteFromMiniApp(event) {
  event.preventDefault();
  const tg = window.Telegram?.WebApp;
  if (!tg) return;
  const inviteeTg = Number(document.querySelector("#invite-open-invitee-tg")?.value || 0);
  const note = document.querySelector("#invite-open-note")?.value?.trim() || "";
  if (!inviteeTg) {
    window.alert("请先填写被邀请人的 TGID。");
    return;
  }
  const button = document.querySelector("#invite-open-submit");
  const previous = button?.textContent || "";
  if (button) {
    button.disabled = true;
    button.textContent = "发放中...";
  }
  try {
    const response = await fetch("/miniapp-api/invites/account-open/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        init_data: tg.initData,
        invitee_tg: inviteeTg,
        note
      })
    });
    const result = await readResponsePayload(response);
    if (!response.ok || result.code !== 200) {
      throw new Error(result.detail || result.message || "开号资格发放失败。");
    }
    renderInviteBundle(result.data?.invite || {});
    document.querySelector("#invite-open-form")?.reset();
    window.alert("开号申请已提交，请等待管理员审核。");
  } catch (error) {
    renderInviteBundle(currentInviteBundle || {});
    window.alert(normalizeError(error));
  } finally {
    if (button) {
      button.textContent = previous || "提交开号申请";
    }
    renderInviteBundle(currentInviteBundle || {});
    storeMiniAppBootstrapCache(currentMiniAppUserId, {
      ...(hydrateMiniAppBootstrapCache(currentMiniAppUserId) || {}),
      invite: currentInviteBundle
    });
  }
}

setupFoldToolbar();
document.querySelector("#invite-form")?.addEventListener("submit", createInviteFromMiniApp);
document.querySelector("#invite-open-form")?.addEventListener("submit", createAccountOpenInviteFromMiniApp);
bootstrapMiniApp();
