const tg = window.Telegram?.WebApp;

const state = {
  initData: tg?.initData || "",
  profileBundle: null,
  leaderboard: { kind: "stone", page: 1, totalPages: 1 },
  shopNameEditing: false
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
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

async function popupLegacy(title, message, tone = "success") {
  touchFeedback(tone);
  if (tg?.showPopup) {
    await tg.showPopup({
      title,
      message,
      buttons: [{ type: "close", text: "知道了" }]
    });
    return;
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
    await tg.showPopup({
      title,
      message,
      buttons: [{ type: "close", text: "知道了" }]
    });
    return;
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

function formatDate(value) {
  if (!value) return "未开始";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "未知" : date.toLocaleString("zh-CN");
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
  nav.innerHTML = "";
  for (const item of items) {
    const link = document.createElement("a");
    link.href = item.path;
    link.textContent = item.label;
    nav.appendChild(link);
  }
}

function ensureSectionState(selector, visible, openWhenVisible = false) {
  const section = document.querySelector(selector);
  if (!section) return;
  section.classList.toggle("hidden", !visible);
  if (visible && openWhenVisible) {
    section.open = true;
  }
}

function renderInventorySelect() {
  const select = document.querySelector("#shop-item-ref");
  const kind = document.querySelector("#shop-item-kind").value;
  const bundle = state.profileBundle;
  if (!bundle) return;

  let rows = [];
  if (kind === "artifact") rows = bundle.artifacts;
  if (kind === "pill") rows = bundle.pills;
  if (kind === "talisman") rows = bundle.talismans;

  select.innerHTML = "";
  const available = rows.filter((row) => row.quantity > 0);
  if (!available.length) {
    select.innerHTML = `<option value="">暂无可上架物品</option>`;
    return;
  }

  for (const row of available) {
    const item = row[kind];
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = `${item.name} · 库存 ${row.quantity}`;
    select.appendChild(option);
  }
}

function taskRequirementRows(kind) {
  const bundle = state.profileBundle || {};
  if (kind === "artifact") {
    return (bundle.artifacts || [])
      .filter((row) => Number(row.quantity || 0) > 0)
      .map((row) => ({ value: row.artifact.id, label: `${row.artifact.name} · 库存 ${row.quantity}` }));
  }
  if (kind === "pill") {
    return (bundle.pills || [])
      .filter((row) => Number(row.quantity || 0) > 0)
      .map((row) => ({ value: row.pill.id, label: `${row.pill.name} · 库存 ${row.quantity}` }));
  }
  if (kind === "talisman") {
    return (bundle.talismans || [])
      .filter((row) => Number(row.quantity || 0) > 0)
      .map((row) => ({ value: row.talisman.id, label: `${row.talisman.name} · 库存 ${row.quantity}` }));
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
      "#official-shop-card",
      "#market-card",
      "#leaderboard-card",
      "#sect-card",
      "#task-card",
      "#craft-card",
      "#explore-card",
      "#red-envelope-card"
    ].forEach((selector) => ensureSectionState(selector, false));
    setStatus("你还没有踏入仙途，确认后会立即抽取灵根并创建修仙档案。", "warning");
    return;
  }

  ensureSectionState("#enter-card", false);
  ensureSectionState("#profile-card", true, true);
  ensureSectionState("#action-card", true, true);
  ensureSectionState("#exchange-card", true);
  ensureSectionState("#inventory-card", true);
  ensureSectionState("#official-shop-card", true);
  ensureSectionState("#market-card", true);
  ensureSectionState("#leaderboard-card", true);
  ensureSectionState("#sect-card", true);
  ensureSectionState("#task-card", true);
  ensureSectionState("#craft-card", true);
  ensureSectionState("#explore-card", true);
  ensureSectionState("#red-envelope-card", true);

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

  document.querySelector("#exchange-hint").textContent =
    `当前比例：1 片刻碎片 = ${bundle.settings.rate} 灵石，手续费 ${bundle.settings.fee_percent}%，灵石兑换碎片最低 ${bundle.settings.min_coin_exchange} 灵石。`;

  setDisabled(document.querySelector("#train-btn"), !bundle.capabilities?.can_train, "当前无法吐纳修炼");
  setDisabled(document.querySelector("#break-btn"), !bundle.capabilities?.can_breakthrough, "当前无法尝试突破");
  setDisabled(document.querySelector("#break-pill-btn"), !bundle.capabilities?.can_breakthrough, "当前无法尝试突破");
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
    "#official-shop-card",
    "#market-card",
    "#leaderboard-card",
    "#sect-card",
    "#task-card",
    "#craft-card",
    "#explore-card",
    "#red-envelope-card",
    "#journal-card",
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
    realmBadge.textContent = `${profile.realm_stage || "凡人"}${profile.realm_layer || 0}层`;
  }
  if (rootText) {
    rootText.textContent = `灵根：${profileRootText(profile)} · 斗法修正 ${profile.root_bonus >= 0 ? "+" : ""}${profile.root_bonus || 0}%`;
  }
  if (profileGrid) {
    profileGrid.innerHTML = `
      <article class="profile-item"><span>境界</span><strong>${escapeHtml(profile.realm_stage || "凡人")}${escapeHtml(profile.realm_layer || 0)}层</strong></article>
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
  const minExchange = settings.min_coin_exchange ?? 100;
  const exchangeHint = document.querySelector("#exchange-hint");
  if (exchangeHint) {
    exchangeHint.textContent = `当前比例：1 片刻碎片 = ${rate} 灵石，手续费 ${fee}%，灵石兑换碎片最低 ${minExchange} 灵石。`;
  }

  setDisabled(document.querySelector("#train-btn"), !bundle.capabilities?.can_train, "当前无法吐纳修炼");
  setDisabled(document.querySelector("#break-btn"), !bundle.capabilities?.can_breakthrough, "当前无法尝试突破");
  setDisabled(document.querySelector("#break-pill-btn"), !bundle.capabilities?.can_breakthrough, "当前无法使用筑基丹突破");
  setDisabled(document.querySelector("#retreat-start-btn"), !bundle.capabilities?.can_retreat, "当前无法开始闭关");
  setDisabled(document.querySelector("#retreat-finish-btn"), !retreating, "当前没有进行中的闭关");

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
    root.innerHTML = `<article class="stack-item"><strong>暂无法宝</strong><p>管理后台发放或在风月阁购买后会出现在这里。</p></article>`;
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
    root.innerHTML = `<article class="stack-item"><strong>暂无丹药</strong><p>风月阁购买或主人发放后会出现在这里。</p></article>`;
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
        <span class="tag">效果值 ${escapeHtml(effects.effect_value ?? item.effect_value)}</span>
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
    root.innerHTML = `<article class="stack-item"><strong>风月阁暂无商品</strong><p>等主人上架后，这里会自动显示。</p></article>`;
    return;
  }

  for (const item of items) {
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.item_name)}</strong>
        <span class="badge badge--vip">${escapeHtml(item.price_stone)} 灵石</span>
      </div>
      <p>${escapeHtml(item.item_kind_label)} · 库存 ${escapeHtml(item.quantity)} · ${escapeHtml(item.shop_name)}</p>
      <button type="button" data-buy-id="${item.id}" ${retreating ? "disabled" : ""}>购买 1 件</button>
    `;
    root.appendChild(card);
  }
}

function renderPersonalShop(items) {
  const root = document.querySelector("#personal-shop-list");
  root.innerHTML = "";
  if (!items.length) {
    root.innerHTML = `<article class="stack-item"><strong>你的店铺暂时空空如也</strong><p>可以从背包里选择法宝、符箓或丹药上架。</p></article>`;
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

  for (const item of items) {
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(item.item_name)}</strong>
        <span class="badge badge--normal">${escapeHtml(item.price_stone)} 灵石</span>
      </div>
      <p>${escapeHtml(item.item_kind_label)} · 库存 ${escapeHtml(item.quantity)} · ${escapeHtml(item.shop_name)}</p>
      <button type="button" data-buy-id="${item.id}" ${retreating ? "disabled" : ""}>购买 1 件</button>
    `;
    root.appendChild(card);
  }
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
  const sects = bundle.sects || [];
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
      <button type="button" data-task-id="${task.id}" ${disabled ? "disabled" : ""}>${actionLabel}</button>
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

function renderExploreArea(bundle) {
  const sceneRoot = document.querySelector("#scene-list");
  const activeRoot = document.querySelector("#exploration-active");
  if (!sceneRoot || !activeRoot) return;

  const active = bundle.active_exploration;
  activeRoot.innerHTML = "";
  if (active && !active.claimed) {
    const canClaim = new Date(active.end_at).getTime() <= Date.now();
    activeRoot.innerHTML = `
      <article class="stack-item">
        <div class="stack-item-head">
          <strong>探索进行中</strong>
          <span class="badge badge--normal">${escapeHtml(active.reward_kind_label || active.reward_kind || "奖励")}</span>
        </div>
        <p>${escapeHtml(active.event_text || "未知遭遇")}</p>
        <p>结束时间：${escapeHtml(formatDate(active.end_at))}</p>
        <button type="button" data-explore-claim="${active.id}" ${canClaim ? "" : "disabled"}>${canClaim ? "领取奖励" : "尚未结束"}</button>
      </article>
    `;
  } else {
    activeRoot.innerHTML = `<article class="stack-item"><strong>当前没有待领取探索</strong></article>`;
  }

  sceneRoot.innerHTML = "";
  const scenes = bundle.scenes || [];
  if (!scenes.length) {
    sceneRoot.innerHTML = `<article class="stack-item"><strong>暂无探索场景</strong></article>`;
    return;
  }
  for (const scene of scenes) {
    const card = document.createElement("article");
    card.className = "stack-item";
    card.innerHTML = `
      <div class="stack-item-head">
        <strong>${escapeHtml(scene.name)}</strong>
        <span class="badge badge--normal">最多 ${escapeHtml(scene.max_minutes)} 分钟</span>
      </div>
      <p>${escapeHtml(scene.description || "暂无场景描述")}</p>
      <label>探索时长
        <select data-scene-minutes="${scene.id}">
          <option value="10">10 分钟</option>
          <option value="30">30 分钟</option>
          <option value="60">60 分钟</option>
        </select>
      </label>
      <button type="button" data-scene-id="${scene.id}">开始探索</button>
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
    root.innerHTML = `<article class="stack-item"><strong>暂无法宝</strong><p>去风月阁挑几件趁手的宝贝，再来装配吧。</p></article>`;
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
        <button type="button" data-cancel-id="${item.id}" class="ghost">取消上架</button>
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
  const rows = bundle.journal || [];
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

async function refreshBundle() {
  const payload = await postJson("/plugins/xiuxian/api/bootstrap");
  renderBottomNav(payload.bottom_nav || []);
  renderProfile(payload.profile_bundle);
  renderSectArea(payload.profile_bundle);
  renderTaskArea(payload.profile_bundle);
  renderTechniqueArea(payload.profile_bundle);
  renderCraftArea(payload.profile_bundle);
  renderExploreArea(payload.profile_bundle);
  renderJournalArea(payload.profile_bundle);
  renderRedEnvelopeClaims(state.lastRedEnvelopeClaims || []);

  state.shopNameEditing = false;
  applyShopNameState(payload.profile_bundle?.profile?.shop_name || "游仙小铺");

  const settings = payload.profile_bundle?.settings || {};
  const rate = settings.rate ?? settings.coin_exchange_rate ?? 100;
  const fee = settings.fee_percent ?? settings.exchange_fee_percent ?? 1;
  const minExchange = settings.min_coin_exchange ?? 100;
  const exchangeHint = document.querySelector("#exchange-hint");
  if (exchangeHint) {
    exchangeHint.textContent = `当前比例：1 片刻碎片 = ${rate} 灵石，手续费 ${fee}%，灵石兑换碎片最低 ${minExchange} 灵石。`;
  }

  ensureSectionState("#journal-card", Boolean(payload.profile_bundle?.profile?.consented));
  return payload.profile_bundle;
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

  await refreshBundle();
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
    setStatus(`本次修炼获得修为 ${payload.gain}、灵石 ${payload.stone_gain}。`, "success");
    await popup("吐纳成功", `修为 +${payload.gain}\n灵石 +${payload.stone_gain}`);
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
    setStatus(`服用筑基丹后已完成突破判定：${detail}`, tone);
    await popup(payload.success ? "突破成功" : "突破失败", detail, tone);
    await refreshBundle();
    await refreshLeaderboard("realm", 1);
  } catch (error) {
    const message = normalizeError(error, "服用筑基丹突破失败。");
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
    const message = `预计获得 ${payload.estimated_gain} 修为，预计消耗 ${payload.estimated_cost} 灵石。`;
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
    const message = `本次闭关获得修为 ${settled.gain}，消耗灵石 ${settled.cost}。`;
    setStatus(message, "success");
    await popup("闭关结算完成", message);
    await refreshBundle();
    await refreshLeaderboard("realm", 1);
  } catch (error) {
    const message = normalizeError(error, "出关结算失败。");
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

document.querySelector("#shop-item-kind").addEventListener("change", renderInventorySelect);

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
    const message = `已上架 ${payload.listing.item_name}，售价 ${payload.listing.price_stone} 灵石。`;
    setStatus(message, "success");
    await popup("上架成功", message);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "上架个人店铺失败。");
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
  const button = event.target.closest("[data-equip-id]");
  if (!button || button.disabled) return;
  try {
    const payload = await runButtonAction(button, "处理中…", () => postJson("/plugins/xiuxian/api/artifact/equip", {
      artifact_id: Number(button.dataset.equipId)
    }));
    const actionText = payload.action === "unequipped" ? "已卸下法宝" : "已装备法宝";
    const message = `${actionText}：${payload.artifact_name}`;
    setStatus(message, "success");
    await popup("操作成功", message);
    await refreshBundle();
    await refreshLeaderboard(state.leaderboard.kind, state.leaderboard.page);
  } catch (error) {
    const message = normalizeError(error, "法宝操作失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#pill-list").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-pill-id]");
  if (!button || button.disabled) return;
  try {
    const payload = await runButtonAction(button, "服用中…", () => postJson("/plugins/xiuxian/api/pill/use", {
      pill_id: Number(button.dataset.pillId)
    }));
    const message = `已服用 ${payload.pill.name}。`;
    setStatus(message, "success");
    await popup("服用成功", message);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "服用丹药失败。");
    setStatus(message, "error");
    await popup("操作失败", message, "error");
  }
});

document.querySelector("#talisman-list").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-talisman-id]");
  if (!button || button.disabled) return;
  try {
    const payload = await runButtonAction(button, "激活中…", () => postJson("/plugins/xiuxian/api/talisman/activate", {
      talisman_id: Number(button.dataset.talismanId)
    }));
    const message = `已激活 ${payload.talisman.name}，将于下一场斗法生效。`;
    setStatus(message, "success");
    await popup("激活成功", message);
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
    const message = `购买 ${itemName} 成功，共消耗 ${payload.total_cost} 灵石。`;
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
    const payload = await runButtonAction(button, "退出中…", () => postJson("/plugins/xiuxian/api/sect/leave"));
    const sectName = payload?.sect?.previous_sect?.name || "当前宗门";
    const message = `你已经离开 ${sectName}。`;
    setStatus(message, "success");
    await popup("退出成功", message);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "退出宗门失败。");
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
  const button = event.target.closest("[data-task-id]");
  if (!button || button.disabled) return;
  try {
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
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "领取任务失败。");
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
    await popup(result.success ? "炼制成功" : "炼制失败", `${message}\n成功率 ${result.success_rate}%`);
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "炼制失败。");
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
    setStatus("探索奖励已领取。", "success");
    await popup("领取成功", "探索奖励已发放到你的背包与档案。");
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

document.querySelector("#gift-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form?.querySelector("button[type='submit']");
  try {
    const payload = await runButtonAction(button, "赠送中…", () => postJson("/plugins/xiuxian/api/gift", {
      target_tg: Number(document.querySelector("#gift-target").value || 0),
      amount: Number(document.querySelector("#gift-amount").value || 0)
    }));
    const targetName = payload.result?.receiver?.display_label || `TG ${payload.result?.receiver?.tg || ""}`;
    const amount = payload.result?.amount || 0;
    const message = `已向 ${targetName} 赠送 ${amount} 灵石。`;
    setStatus(message, "success");
    await popup("赠送成功", message);
    form?.reset?.();
    document.querySelector("#gift-amount").value = "100";
    await refreshBundle();
  } catch (error) {
    const message = normalizeError(error, "灵石赠送失败。");
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
  const grid = document.querySelector("#profile-grid");
  const rootText = document.querySelector("#root-text");
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
    `;
  }
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
  const safeColor = typeof color === "string" && color ? color : "#9ca3af";
  const style = safeColor.includes("gradient")
    ? `background:${safeColor};color:#fff;box-shadow:inset 0 0 0 1px rgba(255,255,255,.28);`
    : `background:${safeColor}22;color:${safeColor};box-shadow:inset 0 0 0 1px ${safeColor}33;`;
  return `<span class="${className}" style="${style}">${safeLabel}</span>`;
}

renderCraftArea = function renderCraftArea(bundle) {
  const materialRoot = document.querySelector("#material-list");
  const recipeRoot = document.querySelector("#recipe-list");
  if (!materialRoot || !recipeRoot) return;

  const materials = bundle.materials || [];
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
    : `<article class="stack-item"><strong>暂无炼制材料</strong><p>可通过探索、任务或主人发放获得。</p></article>`;

  const recipes = bundle.recipes || [];
  recipeRoot.innerHTML = "";
  if (!recipes.length) {
    recipeRoot.innerHTML = `<article class="stack-item"><strong>暂无配方</strong></article>`;
    return;
  }
  for (const recipe of recipes) {
    const ingredients = (recipe.ingredients || [])
      .map((item) => `${item.material?.name || "材料"}×${item.quantity}`)
      .join("、");
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
};

renderArtifactList = function renderArtifactList(items, retreating, equipLimit, equippedCount) {
  const root = document.querySelector("#artifact-list");
  if (!root) return;
  root.innerHTML = "";
  if (!items.length) {
    root.innerHTML = `<article class="stack-item"><strong>暂无法宝</strong><p>管理后台发放或在风月阁购买后会出现在这里。</p></article>`;
    return;
  }
  for (const row of items) {
    const item = row.artifact;
    const effects = item.resolved_effects || {};
    const disabled = !item.usable || retreating;
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
  if (!root) return;
  root.innerHTML = "";
  if (!items.length) {
    root.innerHTML = `<article class="stack-item"><strong>暂无符箓</strong><p>符箓会在下一场斗法中生效，后续可通过商店、掉落或发放获得。</p></article>`;
    return;
  }
  for (const row of items) {
    const item = row.talisman;
    const effects = item.resolved_effects || {};
    const disabled = item.active || !item.usable || retreating;
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
        ${itemAffixTags(item, effects)}
      </div>
      <p>境界要求：${escapeHtml(item.min_realm_stage ? `${item.min_realm_stage}${item.min_realm_layer}层` : "无限制")}</p>
      ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : ""}
      <button type="button" data-talisman-id="${item.id}" ${disabled ? "disabled" : ""}>${item.active ? "已待生效" : "激活到下一场斗法"}</button>
    `;
    root.appendChild(card);
  }
};

renderPillList = function renderPillList(items, retreating) {
  const root = document.querySelector("#pill-list");
  if (!root) return;
  root.innerHTML = "";
  if (!items.length) {
    root.innerHTML = `<article class="stack-item"><strong>暂无丹药</strong><p>风月阁购买或主人发放后会出现在这里。</p></article>`;
    return;
  }
  for (const row of items) {
    const item = row.pill;
    const effects = item.resolved_effects || {};
    const disabled = !item.usable || retreating;
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
        <span class="tag">主效果 ${escapeHtml(effects.effect_value ?? item.effect_value)}</span>
        <span class="tag">丹毒 ${escapeHtml(effects.poison_delta ?? item.poison_delta)}</span>
        ${itemAffixTags(item, effects)}
      </div>
      <p>境界要求：${escapeHtml(item.min_realm_stage ? `${item.min_realm_stage}${item.min_realm_layer}层` : "无限制")}</p>
      ${reason ? `<p class="reason-text">${escapeHtml(reason)}</p>` : ""}
      <button type="button" data-pill-id="${item.id}" ${disabled ? "disabled" : ""}>服用丹药</button>
    `;
    root.appendChild(card);
  }
};

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

document.querySelector("#task-type")?.addEventListener("change", syncUserTaskComposer);
document.querySelector("#task-required-kind")?.addEventListener("change", renderTaskRequirementSelect);

document.querySelector("#open-admin-panel")?.addEventListener("click", () => {
  const button = document.querySelector("#open-admin-panel");
  const adminUrl = button?.dataset.adminUrl || state.profileBundle?.capabilities?.admin_panel_url;
  if (adminUrl) {
    window.location.href = adminUrl;
  }
});

document.querySelector("#task-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  event.stopImmediatePropagation();
  const form = event.currentTarget;
  const button = form?.querySelector("button[type='submit']");
  try {
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
    const message = pushWarning
      ? `任务《${payload.task.title}》已创建，但群内推送失败。\n${pushWarning}`
      : `任务《${payload.task.title}》已发布。`;
    setStatus(message, pushWarning ? "warning" : "success");
    await popup(pushWarning ? "创建已完成，但推送失败" : "发布成功", message, pushWarning ? "warning" : "success");
    form?.reset?.();
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
    "#official-shop-card",
    "#market-card",
    "#leaderboard-card",
    "#sect-card",
    "#task-card",
    "#craft-card",
    "#explore-card",
    "#red-envelope-card",
    "#journal-card",
  ].forEach((selector) => ensureSectionState(selector, consented));

  const realmBadge = document.querySelector("#realm-badge");
  const rootText = document.querySelector("#root-text");
  const heroRootPill = document.querySelector("#hero-root-pill");
  const profileGrid = document.querySelector("#profile-grid");

  if (!consented) {
    if (realmBadge) realmBadge.textContent = "未入道";
    if (heroRootPill) heroRootPill.textContent = "等待踏入仙途";
    if (rootText) rootText.textContent = "确认入道后将抽取灵根、开启境界与背包系统。";
    setStatus("你还没有踏入仙途，确认后将建立修仙档案。", "warning");
    syncAdminEntry(bundle);
    syncUserTaskComposer();
    return;
  }

  const progress = bundle.progress || {};
  const settings = bundle.settings || {};
  const retreating = Boolean(bundle.capabilities?.is_in_retreat);
  const equippedArtifacts = bundle.equipped_artifacts || [];
  const equipLimit = settings.artifact_equip_limit || bundle.capabilities?.artifact_equip_limit || 1;
  const artifactNames = equippedArtifacts.length ? equippedArtifacts.map((item) => item.name).join("、") : "未装备";
  const talismanName = bundle.active_talisman?.name || "暂无";
  const retreatStatus = retreating ? `闭关中，预计 ${formatDate(profile.retreat_end_at)} 出关` : "当前未闭关";
  const rootLabel = profile.root_text || profileRootText(profile);
  const rootQuality = profile.root_quality || "灵根未定";
  const rootBonus = Number(profile.root_bonus || 0);
  const stats = bundle.effective_stats || {};

  if (realmBadge) {
    realmBadge.textContent = `${profile.realm_stage || "凡人"}${profile.realm_layer || 0}层`;
  }
  if (heroRootPill) {
    heroRootPill.textContent = `${rootQuality} · ${rootLabel}`;
  }
  if (rootText) {
    rootText.textContent = `灵根：${rootLabel}，五行修正 ${rootBonus >= 0 ? "+" : ""}${rootBonus}%`;
  }
  if (profileGrid) {
    profileGrid.innerHTML = `
      <article class="profile-item"><span>当前修为</span><strong>${escapeHtml(progress.current ?? profile.cultivation ?? 0)}</strong></article>
      <article class="profile-item"><span>下一层门槛</span><strong>${escapeHtml(progress.threshold ?? 0)}</strong></article>
      <article class="profile-item"><span>距离突破</span><strong>${escapeHtml(progress.remaining ?? 0)}</strong></article>
      <article class="profile-item"><span>灵石</span><strong>${escapeHtml(profile.spiritual_stone ?? 0)}</strong></article>
      <article class="profile-item"><span>丹毒</span><strong>${escapeHtml(profile.dan_poison ?? 0)} / 100</strong></article>
      <article class="profile-item"><span>法宝位</span><strong>${escapeHtml(equippedArtifacts.length)} / ${escapeHtml(equipLimit)}</strong></article>
      <article class="profile-item"><span>已装法宝</span><strong>${escapeHtml(artifactNames)}</strong></article>
      <article class="profile-item"><span>待生效符箓</span><strong>${escapeHtml(talismanName)}</strong></article>
      <article class="profile-item"><span>闭关状态</span><strong>${escapeHtml(retreatStatus)}</strong></article>
      <article class="profile-item"><span>宗门贡献</span><strong>${escapeHtml(profile.sect_contribution ?? 0)}</strong></article>
      <article class="profile-item"><span>综合战力</span><strong>${escapeHtml(bundle.combat_power ?? stats.attack_power ?? 0)}</strong></article>
    `;
  }

  const hints = [];
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
  const minExchange = settings.min_coin_exchange ?? 100;
  const exchangeHint = document.querySelector("#exchange-hint");
  if (exchangeHint) {
    exchangeHint.textContent = `当前比例：1 碎片 = ${rate} 灵石，手续费 ${fee}%，灵石兑碎片至少 ${minExchange} 灵石。`;
  }

  setDisabled(document.querySelector("#train-btn"), !bundle.capabilities?.can_train, "当前无法吐纳修炼");
  setDisabled(document.querySelector("#break-btn"), !bundle.capabilities?.can_breakthrough, "当前无法尝试突破");
  setDisabled(document.querySelector("#break-pill-btn"), !bundle.capabilities?.can_breakthrough, "当前无法使用筑基丹突破");
  setDisabled(document.querySelector("#retreat-start-btn"), !bundle.capabilities?.can_retreat, "当前无法开始闭关");
  setDisabled(document.querySelector("#retreat-finish-btn"), !retreating, "当前没有进行中的闭关");

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
  syncAdminEntry(bundle);
  syncUserTaskComposer();
};

bootstrap().catch(async (error) => {
  const message = normalizeError(error, "修仙面板初始化失败。");
  setStatus(message, "error");
  await popup("初始化失败", message, "error");
});
