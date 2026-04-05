const LEVEL_META = {
  a: {
    text: "白名单用户",
    shortText: "白名单",
    description: "拥有更高权限和更稳定线路的高级用户。",
    tone: "vip"
  },
  b: {
    text: "正常用户",
    shortText: "正常",
    description: "已开通并可正常使用的大多数用户。",
    tone: "normal"
  },
  c: {
    text: "已封禁用户",
    shortText: "封禁",
    description: "当前账号已被禁用，需要主人处理或等待恢复。",
    tone: "danger"
  },
  d: {
    text: "未注册用户",
    shortText: "未注册",
    description: "仅录入了聊天账号信息，还没有绑定有效的 Emby 账号。",
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
    description: "系统暂时无法识别当前账号状态。",
    tone: "unknown"
  };
}

function normalizeError(error) {
  const message = String(error?.message || "").trim();
  if (!message || message === "Failed to fetch" || message.startsWith("Unexpected token")) {
    return "网络请求失败，请稍后重试。";
  }
  if (message === "Internal Server Error") {
    return "服务暂时不可用，请稍后重试。";
  }
  return message;
}

function formatDate(value, fallback = "未设置") {
  if (!value) return fallback;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? fallback : date.toLocaleString("zh-CN");
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
            <strong>暂无可用页面</strong>
            <span class="plugin-state is-off">待开放</span>
          </div>
          <p class="plugin-copy">当前没有可直接进入的插件页面，请等待模块加载或联系主人检查配置。</p>
          <div class="plugin-foot">
            <div class="plugin-meta-row">
              <span class="plugin-meta">页面入口为空</span>
            </div>
            <span class="plugin-ghost">稍后再试</span>
          </div>
        </div>
      </article>
    `;
    return;
  }

  for (const plugin of items) {
    const item = document.createElement("article");
    const hasError = Boolean(plugin.error);
    const stateClass = hasError ? "is-error" : plugin.loaded ? "is-on" : "is-off";
    const stateText = hasError ? "异常" : plugin.loaded ? "已加载" : "待命";
    const mark = escapeHtml(String(plugin.miniapp_icon || plugin.icon || plugin.name?.slice?.(0, 1) || "页").trim().slice(0, 2));
    const description = escapeHtml(plugin.description || "暂未提供说明。");
    const name = escapeHtml(plugin.miniapp_label || plugin.name || "未命名页面");
    const version = escapeHtml(plugin.version || "0.0.0");
    const errorText = hasError ? `<p class="plugin-warning">启动异常：${escapeHtml(plugin.error)}</p>` : "";

    item.className = "plugin-item";
    item.innerHTML = `
      <div class="plugin-mark">${mark}</div>
      <div class="plugin-main">
        <div class="plugin-head">
          <strong>${name}</strong>
          <span class="plugin-state ${stateClass}">${stateText}</span>
        </div>
        <p class="plugin-copy">${description}</p>
        ${errorText}
        <div class="plugin-foot">
          <div class="plugin-meta-row">
            <span class="plugin-meta">版本 ${version}</span>
          </div>
          <button class="plugin-open" data-open-path="${escapeHtml(plugin.miniapp_path)}">进入页面</button>
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
  return user?.first_name || user?.last_name || user?.username || "未命名用户";
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
    welcomeText.textContent = "请在小程序内打开此页面。";
    heroNote.textContent = "当前环境无法获取账号凭证。";
    return;
  }

  tg.ready();
  tg.expand();

  try {
    const response = await fetch("/miniapp-api/bootstrap", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ init_data: tg.initData })
    });
    const result = await response.json();

    if (!response.ok || result.code !== 200) {
      throw new Error(result.detail || result.message || "首页数据加载失败。");
    }

    const { telegram_user, account, meta, permissions } = result.data;
    const visiblePlugins = (meta.plugins || []).filter((item) => item.miniapp_path);
    const loadedCount = visiblePlugins.filter((item) => item.loaded).length;
    const levelMeta = getLevelMeta(account?.lv || (account ? "" : "d"));
    const displayName = resolveDisplayName(telegram_user);
    const accountTone = account?.lv_tone || levelMeta.tone;

    document.title = `${meta.brand || "首页面板"} · 首页`;

    badge.className = `badge badge--${accountTone}`;
    badge.textContent = account?.lv_short_text || account?.lv_text || levelMeta.shortText || levelMeta.text;
    levelDesc.textContent = account?.lv_description || levelMeta.description;

    document.querySelector("#tg-id").textContent = telegram_user.id || "-";
    document.querySelector("#tg-name").textContent = displayName;
    document.querySelector("#account-iv").textContent = account?.iv ?? 0;
    document.querySelector("#account-name").textContent = account?.name || "未绑定";
    document.querySelector("#account-ex").textContent = formatDate(account?.ex, "未绑定");
    document.querySelector("#account-us").textContent = account?.us ?? 0;

    document.querySelector("#brand-name").textContent = meta.brand || "未设置";
    document.querySelector("#currency-name").textContent = meta.currency || "未设置";
    document.querySelector("#hero-name").textContent = displayName;
    document.querySelector("#hero-id").textContent = telegram_user.id || "-";

    pluginCount.textContent = `已加载 ${loadedCount} / ${visiblePlugins.length}`;
    pluginCountPill.textContent = `${visiblePlugins.length} 个入口`;
    rolePill.textContent = permissions?.is_admin ? "主人" : "普通用户";

    if (permissions?.is_admin && permissions?.admin_url) {
      adminEntryCard.classList.remove("hidden");
      adminEntryButton.onclick = () => {
        window.location.href = permissions.admin_url;
      };
    } else {
      adminEntryCard.classList.add("hidden");
      adminEntryButton.onclick = null;
    }

    welcomeText.textContent = `欢迎回来，${displayName}。这里汇总了当前账号状态和可用页面入口。`;
    heroNote.textContent = account?.name
      ? `当前已绑定 Emby 账号 ${account.name}，到期时间 ${formatDate(account.ex, "未设置")}。`
      : "你还没有绑定 Emby 账号，绑定后即可直接使用站点功能。";

    renderPlugins(visiblePlugins);
    renderBottomNav(meta.bottom_nav || []);
  } catch (error) {
    const message = normalizeError(error);
    welcomeText.textContent = `加载失败：${message}`;
    heroNote.textContent = "请稍后重试，或联系主人检查小程序配置。";
    levelDesc.textContent = "当前无法获取账号状态。";
    renderPlugins([]);
    renderBottomNav([]);
  }
}

document.querySelector("#plugin-grid").addEventListener("click", (event) => {
  const button = event.target.closest("[data-open-path]");
  if (!button) {
    return;
  }
  window.location.href = button.dataset.openPath;
});

bootstrapMiniApp();
