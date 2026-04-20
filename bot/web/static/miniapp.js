const LEVEL_META = {
  a: {
    text: "真传弟子",
    shortText: "真传",
    description: "掌门亲传，享天地至纯灵气与无上功法秘境。",
    tone: "vip"
  },
  b: {
    text: "内门弟子",
    shortText: "内门",
    description: "已入道途之修者，可历练寻常秘境。",
    tone: "normal"
  },
  c: {
    text: "走火入魔",
    shortText: "魔道",
    description: "此子已堕魔道或修为尽失，被天地大道所弃。",
    tone: "danger"
  },
  d: {
    text: "凡夫俗子",
    shortText: "凡人",
    description: "毫无灵力波动，尚欠缺道缘引其入法门。",
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
    text: "天机蒙蔽",
    shortText: "迷雾",
    description: "天机难测，系统暂无法洞悉尊驾的命格。",
    tone: "unknown"
  };
}

function normalizeError(error) {
  const message = String(error?.message || "").trim();
  if (!message || message === "Failed to fetch" || message.startsWith("Unexpected token")) {
    return "天机反噬，灵力传音失败，请稍后重试。";
  }
  if (message === "Internal Server Error") {
    return "大阵波荡，暂时无法接引，请稍后再行叩关。";
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
    count.textContent = `当前可缩地成寸 ${cards.length} 处道场`;
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
        <div class="plugin-mark">幻</div>
        <div class="plugin-main">
          <div class="plugin-head">
            <strong>灵气匮乏</strong>
            <span class="plugin-state is-off">死寂</span>
          </div>
          <p class="plugin-copy">此处尚无可用之洞天秘境，请静待灵气复苏，或飞剑传书联系尊者。</p>
          <div class="plugin-foot">
            <div class="plugin-meta-row">
              <span class="plugin-meta">阵法核心缺失</span>
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
    const stateText = hasError ? "法阵崩落" : plugin.loaded ? "灵光大盛" : "沉星潜渊";
    const mark = escapeHtml(String(plugin.miniapp_icon || plugin.icon || plugin.name?.slice?.(0, 1) || "卷").trim().slice(0, 2));
    const description = escapeHtml(plugin.description || "古籍遗漏，不记其详。");
    const name = escapeHtml(plugin.miniapp_label || plugin.name || "无名宝殿");
    const version = escapeHtml(plugin.version || "鸿蒙 0.0");
    const errorText = hasError ? `<p class="plugin-warning">阵脉逆行：${escapeHtml(plugin.error)}</p>` : "";

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
            <span class="plugin-meta">天地历纪 ${version}</span>
          </div>
          <button class="plugin-open" onclick="window.location.href='${escapeHtml(plugin.miniapp_path)}';">挪移阵眼</button>
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
  return user?.first_name || user?.last_name || user?.username || "散修无名";
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
    welcomeText.textContent = "道友请回，凡俗灵器无法窥探洞府全貌。";
    heroNote.textContent = "当今天地法则限制，请使用灵力飞梭 (小程式) 入内。";
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
      throw new Error(result.detail || result.message || "洞府灵脉断绝。");
    }

    const { telegram_user, account, meta, permissions } = result.data;
    let visiblePlugins = (meta.plugins || []).filter((item) => item.miniapp_path);
    const loadedCount = visiblePlugins.filter((item) => item.loaded).length;
    const levelMeta = getLevelMeta(account?.lv || (account ? "" : "d"));
    const displayName = resolveDisplayName(telegram_user);
    const accountTone = account?.lv_tone || levelMeta.tone;

    document.title = `${meta.brand || "修仙纪元"} · 洞府`;

    badge.className = `badge badge--${accountTone}`;
    badge.textContent = account?.lv_short_text || account?.lv_text || levelMeta.shortText || levelMeta.text;
    levelDesc.textContent = account?.lv_description || levelMeta.description;

    document.querySelector("#tg-id").textContent = telegram_user.id || "未结印";
    document.querySelector("#tg-name").textContent = displayName;
    document.querySelector("#account-iv").textContent = account?.iv ?? 0;
    document.querySelector("#account-name").textContent = account?.name || "未结缘";
    document.querySelector("#account-ex").textContent = formatDate(account?.ex, "日月恒长");
    document.querySelector("#account-us").textContent = account?.us ?? 0;

    document.querySelector("#brand-name").textContent = meta.brand || "飘渺宗";
    document.querySelector("#currency-name").textContent = meta.currency || "灵石";
    document.querySelector("#hero-name").textContent = displayName;
    document.querySelector("#hero-id").textContent = telegram_user.id || "凡骨无名";

    pluginCount.textContent = `天书显字 ${loadedCount} / ${visiblePlugins.length}`;
    pluginCountPill.textContent = `${visiblePlugins.length} 处阵法`;
    rolePill.textContent = permissions?.is_admin ? "掌门尊者" : "寻道散修";

    if (permissions?.is_admin && permissions?.admin_url) {
      adminEntryCard.classList.remove("hidden");
      adminEntryButton.onclick = () => {
        window.location.href = withReturnTo(permissions.admin_url);
      };
    } else {
      adminEntryCard.classList.add("hidden");
      adminEntryButton.onclick = null;
    }

    welcomeText.textContent = `紫气东来，${displayName} 道友，您的修真坦途已在眼前展现。`;
    heroNote.textContent = account?.name
      ? `灵机交感，目前已绑定灵犀印 ${account.name}，大限为 ${formatDate(account.ex, "天地难量")}。`
      : "道友尚未结下灵犀之印，若欲踏长生坦途，请尽快缔结前缘。";

    // Sort visible plugins and render
    const savedOrderStr = localStorage.getItem(`xiuxian_order_${userId}`);
    if (savedOrderStr) {
      try {
        const savedOrder = JSON.parse(savedOrderStr);
        visiblePlugins.sort((a, b) => {
          const nameA = a.miniapp_label || a.name || "无名宝殿";
          const nameB = b.miniapp_label || b.name || "无名宝殿";
          let iA = savedOrder.indexOf(nameA);
          let iB = savedOrder.indexOf(nameB);
          if(iA === -1) iA = 999;
          if(iB === -1) iB = 999;
          return iA - iB;
        });
      } catch (e) { console.error("排序玉简解读失败", e); }
    }
    
    renderPlugins(visiblePlugins);
    
    // Init SortableJS for Drag-and-Drop
    const pluginGrid = document.querySelector("#plugin-grid");
    if (pluginGrid && typeof Sortable !== "undefined") {
      new Sortable(pluginGrid, {
        animation: 150,
        ghostClass: 'sortable-ghost',
        dragClass: 'sortable-drag',
        onEnd: function () {
          const items = pluginGrid.querySelectorAll('.plugin-title');
          const newOrder = Array.from(items).map(el => el.textContent.trim());
          localStorage.setItem(`xiuxian_order_${userId}`, JSON.stringify(newOrder));
        }
      });
    }

    renderBottomNav(meta.bottom_nav || []);
  } catch (error) {
    const message = normalizeError(error);
    welcomeText.textContent = `天机反噬：${message}`;
    heroNote.textContent = "灵符焚毁，请稍后再试，或放纸鹤请掌门修补法阵。";
    levelDesc.textContent = "灵根未卜，造化莫测。";
    renderPlugins([]);
    renderBottomNav([]);
  }
}

document.querySelector("#plugin-grid").addEventListener("click", (event) => {
  // Check if click was on or within the button, if so handle normally, else redirect
  if (event.target.closest('button')) return; 
  
  const card = event.target.closest("[data-open-path]");
  if (!card) {
    return;
  }
  window.location.href = card.dataset.openPath;
});

setupFoldToolbar();
bootstrapMiniApp();
