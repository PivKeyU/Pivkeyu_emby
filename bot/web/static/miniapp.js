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
  if (!message || message === "Failed to fetch" || message.startsWith("Unexpected token")) {
    return "网络连接失败，请稍后重试。";
  }
  if (message === "Internal Server Error") {
    return "服务器内部错误，请稍后再试。";
  }
  return message;
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

function resolveDisplayName(user) {
  return user?.first_name || user?.last_name || user?.username || "未知用户";
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
  const userId = tg.initDataUnsafe?.user?.id || 'default';

  try {
    const response = await fetch("/miniapp-api/bootstrap", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ init_data: tg.initData })
    });
    const result = await response.json();

    if (!response.ok || result.code !== 200) {
      throw new Error(result.detail || result.message || "服务器连接失败。");
    }

    const { telegram_user, account, meta, permissions } = result.data;
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

    // Sort visible plugins and render
    const savedOrderStr = localStorage.getItem(`miniapp_order_${userId}`);
    if (savedOrderStr) {
      try {
        const savedOrder = JSON.parse(savedOrderStr);
        visiblePlugins.sort((a, b) => {
          const nameA = a.miniapp_label || a.name || "";
          const nameB = b.miniapp_label || b.name || "";
          let iA = savedOrder.indexOf(nameA);
          let iB = savedOrder.indexOf(nameB);
          if(iA === -1) iA = 999;
          if(iB === -1) iB = 999;
          return iA - iB;
        });
      } catch (e) { console.error("排序数据读取失败", e); }
    }
    
    renderPlugins(visiblePlugins);

    // Save order on plugin grid reorder (touch-friendly: tap to open, no drag on mobile)
    const pluginGrid = document.querySelector("#plugin-grid");
    pluginGrid.addEventListener("click", (event) => {
      if (event.target.closest("button")) return;
      const card = event.target.closest("[data-open-path]");
      if (!card) return;
      window.location.href = card.dataset.openPath;
    });

    renderBottomNav(meta.bottom_nav || []);
  } catch (error) {
    const message = normalizeError(error);
    welcomeText.textContent = `连接失败：${message}`;
    heroNote.textContent = "请检查网络后重试，或联系管理员。";
    levelDesc.textContent = "账号状态未知。";
    renderPlugins([]);
    renderBottomNav([]);
  }
}

setupFoldToolbar();
bootstrapMiniApp();
