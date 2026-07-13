const tg = window.Telegram?.WebApp;
const state = {
  token: localStorage.getItem("doupo_admin_token") || "",
  initData: tg?.initData || "",
  bootstrap: null,
};

function setStatus(text) {
  const node = document.querySelector("#admin-status");
  if (node) node.textContent = String(text || "");
}

function headers(withJson = true) {
  const h = {};
  if (withJson) h["Content-Type"] = "application/json";
  if (state.token) h["x-admin-token"] = state.token;
  if (state.initData) h["x-telegram-init-data"] = state.initData;
  return h;
}

async function request(method, path, body = null) {
  const response = await fetch(path, {
    method,
    headers: headers(body !== null),
    body: body === null ? undefined : JSON.stringify(body),
  });
  const raw = await response.text();
  const payload = raw ? JSON.parse(raw) : { code: response.status, data: null };
  if (!response.ok || payload.code !== 200) {
    throw new Error(payload.detail || payload.message || "请求失败");
  }
  return payload.data;
}

function safeJson(text, fallback = {}) {
  try {
    const data = JSON.parse(String(text || "").trim() || "{}");
    if (data && typeof data === "object") return data;
  } catch {}
  return fallback;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function fillActionForm(item = {}) {
  document.querySelector("#action-key").value = item.action_key || "";
  document.querySelector("#action-name").value = item.name || "";
  document.querySelector("#action-type").value = item.action_type || "train";
  document.querySelector("#action-cooldown").value = Number(item.cooldown_seconds || 0);
  document.querySelector("#action-desc").value = item.description || "";
  document.querySelector("#action-reward").value = JSON.stringify(item.reward_config || {}, null, 2);
  document.querySelector("#action-requirement").value = JSON.stringify(item.requirement_config || {}, null, 2);
  document.querySelector("#action-enabled").checked = Boolean(item.enabled ?? true);
  document.querySelector("#action-sort").value = Number(item.sort_order || 0);
  setStatus(`已载入行动：${item.name || item.action_key || ""}`);
}

function itemCostSummary(reward = {}) {
  const costs = [];
  const itemCosts = reward.item_costs || {};
  if (Array.isArray(itemCosts)) {
    itemCosts.forEach((item) => {
      const key = item.item_key || item.key;
      const qty = Number(item.quantity || item.qty || 0);
      if (key && qty > 0) costs.push(`${key} x${qty}`);
    });
  } else if (itemCosts && typeof itemCosts === "object") {
    Object.entries(itemCosts).forEach(([key, qty]) => {
      if (Number(qty || 0) > 0) costs.push(`${key} x${Number(qty || 0)}`);
    });
  }
  if (reward.gold_cost) costs.push(`gold x${Number(reward.gold_cost)}`);
  if (reward.core_cost) costs.push(`core x${Number(reward.core_cost)}`);
  return costs.join(" + ");
}

function renderActionList(data = {}) {
  const list = document.querySelector("#action-list");
  if (!list) return;
  const rows = Array.isArray(data.actions) ? data.actions : [];
  list.innerHTML = rows.map((item) => {
    const req = item.requirement_config || {};
    const requirement = item.action_type === "breakthrough" ? "九星圆满 / 动态丹药与金币" : [
      req.realm_stage_min ? `境界 ${req.realm_stage_min}` : "",
      req.realm_stars_min ? `${Number(req.realm_stars_min)} 星` : "",
      req.gold_min ? `金币 ${Number(req.gold_min)}` : "",
      req.core_min ? `魔核 ${Number(req.core_min)}` : "",
      req.alchemy_min ? `炼药 ${Number(req.alchemy_min)}` : "",
      req.fire_min ? `火候 ${Number(req.fire_min)}` : "",
      req.sect_contribution_min ? `贡献 ${Number(req.sect_contribution_min)}` : "",
      req.pill_min ? `丹药 ${Number(req.pill_min)}` : "",
      req.technique_level_min ? `斗技 ${Number(req.technique_level_min)}` : "",
      req.fire_progress_min ? `线索 ${Number(req.fire_progress_min)}` : "",
      req.boss_score_min ? `Boss ${Number(req.boss_score_min)}` : "",
      req.tower_floor_min ? `塔层 ${Number(req.tower_floor_min)}` : "",
      req.auction_credit_min ? `拍卖 ${Number(req.auction_credit_min)}` : "",
    ].filter(Boolean).join(" / ") || "无门槛";
    const recipe = item.action_type === "alchemy" ? itemCostSummary(item.reward_config || {}) : "";
    return `
      <li>
        <span>${escapeHtml(item.action_key)} - ${escapeHtml(item.name)} (${escapeHtml(item.action_type_label || item.action_type)}) · ${escapeHtml(requirement)}${recipe ? ` · 配方 ${escapeHtml(recipe)}` : ""}</span>
        <button type="button" class="ghost mini" data-edit-action="${escapeHtml(item.action_key)}">编辑</button>
      </li>
    `;
  }).join("") || "<li>暂无行动</li>";
  list.querySelectorAll("[data-edit-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const key = button.getAttribute("data-edit-action");
      const item = rows.find((row) => row.action_key === key);
      if (item) fillActionForm(item);
    });
  });
}

function metricItem(label, value, note = "") {
  return `<article><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong>${note ? `<small>${escapeHtml(note)}</small>` : ""}</article>`;
}

function renderAdminMetrics(data = {}) {
  const accountSummary = data.game_accounts?.summary || {};
  const playerSearch = data.player_search || {};
  const root = document.querySelector("#admin-metrics");
  if (root) {
    root.innerHTML = [
      metricItem("斗破玩家", Number(playerSearch.total || 0), "独立角色档案"),
      metricItem("统一账号", Number(accountSummary.total || 0), `${Number(accountSummary.bound || 0)} 个已绑定 TG`),
      metricItem("可用行动", (data.actions || []).filter((item) => item.enabled).length, `共 ${(data.actions || []).length} 项`),
      metricItem("账号异常", Number(accountSummary.disabled || 0), `${Number(accountSummary.unbound || 0)} 个待绑定`),
    ].join("");
  }
}

function renderPlayerSearch(data = {}) {
  const root = document.querySelector("#player-search-list");
  if (!root) return;
  const search = data.player_search || {};
  const rows = Array.isArray(search.items) ? search.items : [];
  root.innerHTML = rows.map((profile) => `
    <article class="admin-list-item">
      <div>
        <strong>${escapeHtml(profile.display_name || (profile.username ? `@${profile.username}` : `TG ${profile.tg}`))}</strong>
        <p class="section-copy">TG ${escapeHtml(profile.tg)} · ${escapeHtml(profile.realm_stage || "斗之气")} ${Number(profile.realm_stars || 1)} 星 · 战力 ${Number(profile.battle_power || 0)}</p>
      </div>
      <button type="button" class="ghost mini" data-select-player="${escapeHtml(profile.tg)}">选择</button>
    </article>
  `).join("") || `<article class="admin-empty">未找到匹配玩家</article>`;
  root.querySelectorAll("[data-select-player]").forEach((button) => {
    button.addEventListener("click", async () => {
      document.querySelector("#player-tg").value = button.dataset.selectPlayer || "";
      await loadPlayer();
    });
  });
}

function accountMetricSummary(summary = {}) {
  const root = document.querySelector("#account-summary");
  if (!root) return;
  root.innerHTML = [
    metricItem("账号总数", Number(summary.total || 0)),
    metricItem("已绑定", Number(summary.bound || 0)),
    metricItem("待绑定", Number(summary.unbound || 0)),
    metricItem("已停用", Number(summary.disabled || 0)),
  ].join("");
}

function renderAccounts(data = {}) {
  accountMetricSummary(data.summary || {});
  const root = document.querySelector("#account-list");
  if (!root) return;
  const rows = Array.isArray(data.items) ? data.items : [];
  root.innerHTML = rows.map((account) => `
    <article class="admin-list-item ${account.enabled === false ? "is-disabled" : ""}">
      <div>
        <div class="admin-item-title">
          <strong>${escapeHtml(account.display_name || account.username)}</strong>
          <span class="tag">${account.enabled === false ? "已停用" : account.bound ? "已绑定" : "待绑定"}</span>
        </div>
        <p class="section-copy">账号 ${escapeHtml(account.username)} · ${escapeHtml(account.telegram_label || "未绑定 Telegram")}${account.tg ? ` · TG ${escapeHtml(account.tg)}` : ""}</p>
      </div>
      <div class="admin-item-actions">
        <button type="button" class="ghost mini" data-account-action="state" data-account-id="${account.id}" data-enabled="${account.enabled === false ? "true" : "false"}">${account.enabled === false ? "启用" : "停用"}</button>
        <button type="button" class="ghost mini" data-account-action="revoke" data-account-id="${account.id}">强制下线</button>
        ${account.bound ? `<button type="button" class="ghost mini danger-button" data-account-action="unbind" data-account-id="${account.id}">解绑 TG</button>` : ""}
      </div>
    </article>
  `).join("") || `<article class="admin-empty">没有符合条件的游戏账号</article>`;
  root.querySelectorAll("[data-account-action]").forEach((button) => {
    button.addEventListener("click", () => handleAccountAction(button).catch((error) => setStatus(error.message || String(error))));
  });
}

async function loadAccounts() {
  const params = new URLSearchParams({
    q: document.querySelector("#account-search-q")?.value || "",
    bound: document.querySelector("#account-bound-filter")?.value || "",
    enabled: document.querySelector("#account-enabled-filter")?.value || "",
    page: "1",
    page_size: "30",
  });
  const data = await request("GET", `/plugins/doupo/admin-api/accounts?${params}`);
  renderAccounts(data);
  return data;
}

async function handleAccountAction(button) {
  const accountId = Number(button.dataset.accountId || 0);
  const action = button.dataset.accountAction || "";
  if (!accountId) return;
  if (action === "state") {
    const enabled = button.dataset.enabled === "true";
    if (!window.confirm(`确认${enabled ? "启用" : "停用"}这个游戏账号？`)) return;
    await request("POST", `/plugins/doupo/admin-api/accounts/${accountId}/state`, { enabled });
  } else if (action === "unbind") {
    if (!window.confirm("确认解绑 Telegram？该账号会被强制下线，需要重新绑定后才能游戏。")) return;
    await request("POST", `/plugins/doupo/admin-api/accounts/${accountId}/unbind`, {});
  } else if (action === "revoke") {
    if (!window.confirm("确认让该账号的所有网页登录会话立即失效？")) return;
    await request("POST", `/plugins/doupo/admin-api/accounts/${accountId}/sessions/revoke`, {});
  }
  await loadAccounts();
  setStatus("账号操作已完成");
}

async function bootstrapAdmin(forceToken = false) {
  const payload = {
    player_query: document.querySelector("#player-search-q")?.value || "",
    player_page: 1,
    player_page_size: 20,
  };
  if (!forceToken && state.initData) payload.init_data = state.initData;
  else if (state.token) payload.token = state.token;
  const data = await request("POST", "/plugins/doupo/admin-api/bootstrap", payload);
  state.bootstrap = data;
  document.querySelector("#setting-enabled").checked = Boolean(data.settings?.exchange_enabled ?? true);
  document.querySelector("#setting-rate").value = Number(data.settings?.exchange_rate || 100);
  document.querySelector("#setting-min-gold").value = Number(data.settings?.min_gold_to_exchange || 100);
  document.querySelector("#setting-daily-gold-cap").value = Number(data.settings?.daily_gold_action_cap ?? 650);
  document.querySelector("#setting-daily-train-limit").value = Number(data.settings?.daily_train_limit ?? 5);
  document.querySelector("#setting-daily-expedition-limit").value = Number(data.settings?.daily_expedition_limit ?? 3);
  document.querySelector("#setting-daily-action-points").value = Number(data.settings?.daily_action_points ?? 12);
  document.querySelector("#setting-daily-douqi-soft-cap").value = Number(data.settings?.daily_douqi_soft_cap ?? 250);
  document.querySelector("#setting-daily-douqi-hard-cap").value = Number(data.settings?.daily_douqi_hard_cap ?? 400);
  document.querySelector("#setting-daily-douqi-overflow").value = Number(data.settings?.daily_douqi_overflow_percent ?? 20);
  document.querySelector("#setting-breakthrough-loss").value = Number(data.settings?.breakthrough_failure_douqi_loss_percent ?? 10);
  document.querySelectorAll("[data-action-limit]").forEach((input) => {
    const key = input.dataset.actionLimit || "";
    input.value = Number(data.settings?.daily_action_limits?.[key] ?? input.value ?? 0);
  });
  document.querySelectorAll("[data-action-point-cost]").forEach((input) => {
    const key = input.dataset.actionPointCost || "";
    input.value = Number(data.settings?.action_point_costs?.[key] ?? input.value ?? 0);
  });
  document.querySelector("#setting-duel-min-stake").value = Number(data.settings?.duel_min_stake || 0);
  document.querySelector("#setting-duel-max-stake").value = Number(data.settings?.duel_max_stake || 500);
  document.querySelector("#setting-duel-prepare-seconds").value = Number(data.settings?.duel_prepare_seconds || 8);
  document.querySelector("#setting-broadcast-enabled").checked = Boolean(data.settings?.broadcast_enabled ?? true);
  renderActionList(data);
  renderAdminMetrics(data);
  renderPlayerSearch(data);
  renderAccounts(data.game_accounts || {});
  setStatus("后台数据已加载");
}

async function saveSettings() {
  const dailyActionLimits = {};
  document.querySelectorAll("[data-action-limit]").forEach((input) => {
    dailyActionLimits[input.dataset.actionLimit || ""] = Number(input.value || 0);
  });
  const actionPointCosts = {};
  document.querySelectorAll("[data-action-point-cost]").forEach((input) => {
    actionPointCosts[input.dataset.actionPointCost || ""] = Number(input.value || 0);
  });
  const payload = {
    exchange_enabled: document.querySelector("#setting-enabled").checked,
    exchange_rate: Number(document.querySelector("#setting-rate").value || 100),
    min_gold_to_exchange: Number(document.querySelector("#setting-min-gold").value || 100),
    daily_gold_action_cap: Number(document.querySelector("#setting-daily-gold-cap").value || 650),
    daily_train_limit: Number(document.querySelector("#setting-daily-train-limit").value || 5),
    daily_expedition_limit: Number(document.querySelector("#setting-daily-expedition-limit").value || 0),
    daily_action_points: Number(document.querySelector("#setting-daily-action-points").value || 0),
    daily_action_limits: dailyActionLimits,
    action_point_costs: actionPointCosts,
    daily_douqi_soft_cap: Number(document.querySelector("#setting-daily-douqi-soft-cap").value || 0),
    daily_douqi_hard_cap: Number(document.querySelector("#setting-daily-douqi-hard-cap").value || 0),
    daily_douqi_overflow_percent: Number(document.querySelector("#setting-daily-douqi-overflow").value || 0),
    breakthrough_failure_douqi_loss_percent: Number(document.querySelector("#setting-breakthrough-loss").value || 0),
    duel_min_stake: Number(document.querySelector("#setting-duel-min-stake").value || 0),
    duel_max_stake: Number(document.querySelector("#setting-duel-max-stake").value || 500),
    duel_prepare_seconds: Number(document.querySelector("#setting-duel-prepare-seconds").value || 8),
    broadcast_enabled: document.querySelector("#setting-broadcast-enabled").checked,
  };
  await request("POST", "/plugins/doupo/admin-api/settings", payload);
  setStatus("设置已保存");
}

async function saveAction() {
  const payload = {
    action_key: document.querySelector("#action-key").value.trim(),
    name: document.querySelector("#action-name").value.trim(),
    action_type: document.querySelector("#action-type").value,
    cooldown_seconds: Number(document.querySelector("#action-cooldown").value || 0),
    description: document.querySelector("#action-desc").value.trim(),
    reward_config: safeJson(document.querySelector("#action-reward").value, {}),
    requirement_config: safeJson(document.querySelector("#action-requirement").value, {}),
    enabled: document.querySelector("#action-enabled").checked,
    sort_order: Number(document.querySelector("#action-sort").value || 0),
  };
  await request("POST", "/plugins/doupo/admin-api/actions", payload);
  await bootstrapAdmin();
  setStatus("行动已保存");
}

async function loadPlayer() {
  const tg = Number(document.querySelector("#player-tg").value || 0);
  if (tg <= 0) throw new Error("请填写正确 TG");
  const detail = await request("GET", `/plugins/doupo/admin-api/players/${tg}`);
  const profile = detail.profile || {};
  const actionPoints = detail.daily_usage?.action_points || {};
  const douqiIncome = detail.daily_usage?.douqi_income || {};
  document.querySelector("#player-detail").innerHTML = `
    <div class="admin-detail-grid">
      ${metricItem("玩家", profile.display_name || `TG ${profile.tg || tg}`)}
      ${metricItem("境界", `${profile.realm_stage || "斗之气"} ${Number(profile.realm_stars || 1)} 星`)}
      ${metricItem("斗气", Number(profile.douqi || 0))}
      ${metricItem("金币", Number(profile.gold || 0))}
      ${metricItem("战力", Number(profile.battle_power || 0))}
      ${metricItem("宗门", profile.sect_name || "未加入")}
      ${metricItem("今日行动力", `${Number(actionPoints.used || 0)} / ${Number(actionPoints.limit || 0) || "不限"}`)}
      ${metricItem("今日成长斗气", `${Number(douqiIncome.earned || 0)} / ${Number(douqiIncome.hard_cap || 0) || "不限"}`, `软上限 ${Number(douqiIncome.soft_cap || 0)}`)}
    </div>`;
}

async function grantResource() {
  const tg = Number(document.querySelector("#player-tg").value || 0);
  const payload = {
    resource: document.querySelector("#grant-resource").value,
    amount: Number(document.querySelector("#grant-amount").value || 0),
  };
  await request("POST", `/plugins/doupo/admin-api/players/${tg}/resource/grant`, payload);
  await loadPlayer();
  setStatus("资源调整完成");
}

async function resetAll() {
  if (!window.confirm("确认清空全部斗破玩家数据？此操作不可撤销，统一游戏账号不会被删除。")) return;
  await request("POST", "/plugins/doupo/admin-api/system/reset-player-data");
  setStatus("已重置全部斗破玩家数据");
}

document.querySelector("#admin-token").value = state.token;
document.querySelector("#admin-login-btn")?.addEventListener("click", async () => {
  state.token = document.querySelector("#admin-token").value.trim();
  localStorage.setItem("doupo_admin_token", state.token);
  await bootstrapAdmin(true);
});
document.querySelector("#save-settings-btn")?.addEventListener("click", () => saveSettings().catch((e) => setStatus(e.message || String(e))));
document.querySelector("#save-action-btn")?.addEventListener("click", () => saveAction().catch((e) => setStatus(e.message || String(e))));
document.querySelector("#load-player-btn")?.addEventListener("click", () => loadPlayer().catch((e) => setStatus(e.message || String(e))));
document.querySelector("#grant-btn")?.addEventListener("click", () => grantResource().catch((e) => setStatus(e.message || String(e))));
document.querySelector("#reset-all-btn")?.addEventListener("click", () => resetAll().catch((e) => setStatus(e.message || String(e))));
document.querySelector("#player-search-form")?.addEventListener("submit", (event) => {
  event.preventDefault();
  bootstrapAdmin().catch((error) => setStatus(error.message || String(error)));
});
document.querySelector("#account-search-form")?.addEventListener("submit", (event) => {
  event.preventDefault();
  loadAccounts().catch((error) => setStatus(error.message || String(error)));
});
document.querySelectorAll(".admin-nav a").forEach((link) => {
  link.addEventListener("click", (event) => {
    const target = document.querySelector(link.getAttribute("href") || "");
    if (!target) return;
    event.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

if (tg) {
  tg.ready();
  tg.expand();
}
bootstrapAdmin().catch((e) => setStatus(e.message || String(e)));
