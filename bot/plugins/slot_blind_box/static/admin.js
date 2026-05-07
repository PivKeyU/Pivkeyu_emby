const tg = window.Telegram?.WebApp || null;
const storageKey = "slot-blind-box-admin-token";

function readLocalStorage(key) {
  try {
    return window.localStorage.getItem(key) || "";
  } catch (error) {
    return "";
  }
}

function writeLocalStorage(key, value) {
  try {
    if (value) {
      window.localStorage.setItem(key, value);
    } else {
      window.localStorage.removeItem(key);
    }
  } catch (error) {
    setStatus("浏览器阻止了本地保存，本次仍会使用输入的令牌验证。", "warning");
  }
}

const state = {
  token: readLocalStorage(storageKey),
  initData: tg?.initData || "",
  authMode: null,
  payload: null,
  recordPage: 1,
  recordPageSize: 10,
  recordFilter: "all",
  records: []
};

const refs = {
  status: document.querySelector("#admin-status"),
  authMode: document.querySelector("#admin-auth-mode"),
  tokenInput: document.querySelector("#admin-token"),
  tokenForm: document.querySelector("#token-form"),
  tokenSubmit: document.querySelector("#token-submit"),
  settingsForm: document.querySelector("#settings-form"),
  settingsSubmit: document.querySelector("#settings-submit"),
  prizeForm: document.querySelector("#prize-form"),
  prizeSubmit: document.querySelector("#prize-submit"),
  redeemCodeForm: document.querySelector("#redeem-code-form"),
  redeemCodeSubmit: document.querySelector("#redeem-code-submit"),
  prizeList: document.querySelector("#admin-prize-list"),
  redeemCodeList: document.querySelector("#admin-redeem-code-list"),
  recordList: document.querySelector("#admin-record-list"),
  recordFilter: document.querySelector("#admin-record-filter"),
  recordPrev: document.querySelector("#admin-record-prev"),
  recordNext: document.querySelector("#admin-record-next"),
  recordPageInfo: document.querySelector("#admin-record-page-info"),
  prizeCount: document.querySelector("#admin-prize-count"),
  activeCount: document.querySelector("#admin-active-count"),
  spinCount: document.querySelector("#admin-spin-count"),
  userCount: document.querySelector("#admin-user-count"),
  blankRate: document.querySelector("#admin-blank-rate"),
  totalWeight: document.querySelector("#admin-total-weight")
};

if (refs.tokenInput) {
  refs.tokenInput.value = state.token;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setStatus(text, tone = "info") {
  if (!refs.status) return;
  refs.status.textContent = text;
  refs.status.dataset.tone = tone;
}

function authHeaders() {
  if (state.authMode === "telegram" && state.initData) {
    return { "X-Telegram-Init-Data": state.initData };
  }
  if (state.token) {
    return { "X-Admin-Token": state.token };
  }
  return {};
}

async function request(method, url, payload) {
  let response;
  try {
    response = await fetch(url, {
      method,
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: payload ? JSON.stringify(payload) : undefined
    });
  } catch (error) {
    throw new Error("网络请求失败，请确认后台服务正在运行。");
  }
  const raw = await response.text();
  let data = {};
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch (error) {
    throw new Error(raw || `请求失败（HTTP ${response.status}）`);
  }
  if (!response.ok || data.code !== 200) {
    throw new Error(data.detail || data.message || `请求失败（HTTP ${response.status}）`);
  }
  return data.data;
}

function field(selector) {
  return document.querySelector(selector);
}

function numberValue(selector, fallback = 0) {
  const value = Number(field(selector)?.value ?? fallback);
  return Number.isFinite(value) ? value : fallback;
}

function checked(selector) {
  return Boolean(field(selector)?.checked);
}

function levelMap(prefix) {
  return {
    a: numberValue(`#${prefix}-a`, 0),
    b: numberValue(`#${prefix}-b`, 0),
    c: numberValue(`#${prefix}-c`, 0),
    d: numberValue(`#${prefix}-d`, 0)
  };
}

function rewardTypeLabel(type, quantity = 0) {
  if (type === "free_spin_ticket") return `抽奖券 ${quantity || 1} 张`;
  if (type === "group_invite_credit") return "邀请资格";
  if (type === "account_open_credit") return `开号资格 x${quantity || 1}`;
  if (type === "emby_currency") return `Emby 货币 ${quantity || 0}`;
  return "普通奖品";
}

function grantsPayload(prefix = "redeem-grant") {
  return {
    free_spin_ticket: numberValue(`#${prefix}-ticket`, 0),
    group_invite_credit: numberValue(`#${prefix}-group`, 0),
    account_open_credit: numberValue(`#${prefix}-account`, 0)
  };
}

function grantsLabel(grants = {}) {
  const parts = [];
  if (Number(grants.free_spin_ticket || 0) > 0) parts.push(`抽奖券 x${grants.free_spin_ticket}`);
  if (Number(grants.group_invite_credit || 0) > 0) parts.push(`邀请资格 x${grants.group_invite_credit}`);
  if (Number(grants.account_open_credit || 0) > 0) parts.push(`开号资格 x${grants.account_open_credit}`);
  return parts.join(" · ") || "无发放内容";
}

function normalizedRecordType(record = {}) {
  const type = String(record.reward_type || "").trim();
  if (type) return type;
  return record.outcome === "blank" ? "blank" : "manual";
}

function recordTypeLabel(record = {}) {
  const type = normalizedRecordType(record);
  if (type === "emby_currency") return `💰 ${record.reward_quantity || 0} ${record.reward_label || "货币"}`;
  if (type === "free_spin_ticket") return `🎟️ 抽奖券 x${record.reward_quantity || 1}`;
  if (type === "group_invite_credit") return `📨 邀请资格 x${record.reward_quantity || 1}`;
  if (type === "account_open_credit") return `🪪 开号资格 x${record.reward_quantity || 1}`;
  if (type === "blank" || record.outcome === "blank") return "🍀 轮空";
  return "🎁 普通奖品";
}

function recordMatchesFilter(record = {}, filter = "all") {
  if (filter === "all") return true;
  if (filter === "win") return record.outcome === "win";
  return normalizedRecordType(record) === filter;
}

function renderRecords(records = state.records) {
  state.records = Array.isArray(records) ? records : [];
  const filtered = state.records.filter((record) => recordMatchesFilter(record, state.recordFilter));
  const totalPages = Math.max(Math.ceil(filtered.length / state.recordPageSize), 1);
  state.recordPage = Math.min(Math.max(state.recordPage, 1), totalPages);
  const start = (state.recordPage - 1) * state.recordPageSize;
  const pageItems = filtered.slice(start, start + state.recordPageSize);
  if (!pageItems.length) {
    refs.recordList.innerHTML = `<div class="empty">暂无匹配记录。</div>`;
  } else {
    refs.recordList.innerHTML = pageItems.map((record) => `
      <article class="record-item" data-outcome="${escapeHtml(record.outcome)}">
        <div class="record-line">
          <strong>${escapeHtml(record.prize_icon || "🍀")} ${escapeHtml(record.prize_name || "轮空")}</strong>
          <span class="status-pill">${escapeHtml(recordTypeLabel(record))}</span>
        </div>
        <p class="muted">${escapeHtml(record.user_display || record.user_id || "未知用户")} · ${escapeHtml(record.created_at || "")}${record.pity_triggered ? " · 保底" : ""}</p>
      </article>
    `).join("");
  }
  if (refs.recordPageInfo) refs.recordPageInfo.textContent = `${state.recordPage}/${totalPages} · ${filtered.length} 条`;
  if (refs.recordPrev) refs.recordPrev.disabled = state.recordPage <= 1;
  if (refs.recordNext) refs.recordNext.disabled = state.recordPage >= totalPages;
}

function renderPrizes(prizes = []) {
  if (!prizes.length) {
    refs.prizeList.innerHTML = `<div class="empty">当前还没有奖品。</div>`;
    return;
  }
  refs.prizeList.innerHTML = prizes.map((prize) => `
    <article class="admin-prize">
      <div class="admin-prize-head">
        <div>
          <h3>${escapeHtml(prize.icon || "🎁")} ${escapeHtml(prize.name)}</h3>
          <p class="muted">${escapeHtml(prize.description || "")}</p>
        </div>
        <span class="status-pill">${prize.enabled ? "启用" : "停用"}</span>
      </div>
      <div class="admin-prize-meta">
        <span class="status-pill">概率 ${escapeHtml(prize.computed_rate ?? 0)}%</span>
        <span class="status-pill">权重 ${escapeHtml(prize.weight)}</span>
        <span class="status-pill">库存 ${Number(prize.stock) < 0 ? "不限" : escapeHtml(prize.stock)}</span>
        <span class="status-pill">${escapeHtml(prize.reward_label || rewardTypeLabel(prize.reward_type, prize.free_spin_quantity))}</span>
        <span class="status-pill">${prize.guarantee_eligible ? "参与保底" : "不参与保底"}</span>
        <span class="status-pill">${prize.broadcast_enabled ? "中奖播报" : "不播报"}</span>
        ${prize.broadcast_image_url ? `<span class="status-pill">有播报图</span>` : ""}
      </div>
      <div class="admin-prize-actions">
        <button type="button" class="secondary" data-edit="${escapeHtml(prize.id)}">编辑</button>
        <button type="button" class="secondary" data-toggle="${escapeHtml(prize.id)}">${prize.enabled ? "停用" : "启用"}</button>
        <button type="button" class="secondary" data-delete="${escapeHtml(prize.id)}">删除</button>
      </div>
    </article>
  `).join("");

  refs.prizeList.querySelectorAll("[data-toggle]").forEach((button) => {
    button.addEventListener("click", async () => {
      const prize = prizes.find((item) => item.id === button.dataset.toggle);
      if (!prize) return;
      try {
        const payload = await request("PATCH", `/plugins/slot-box/admin-api/prize/${encodeURIComponent(prize.id)}`, {
          enabled: !prize.enabled
        });
        applyPayload(payload);
        setStatus("奖品状态已更新。", "success");
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });

  refs.prizeList.querySelectorAll("[data-edit]").forEach((button) => {
    button.addEventListener("click", async () => {
      const prize = prizes.find((item) => item.id === button.dataset.edit);
      if (!prize) return;
      const patch = promptPrizePatch(prize);
      if (!patch) return;
      try {
        button.disabled = true;
        button.textContent = "保存中";
        const payload = await request("PATCH", `/plugins/slot-box/admin-api/prize/${encodeURIComponent(prize.id)}`, patch);
        applyPayload(payload);
        setStatus("奖品信息已更新。", "success");
      } catch (error) {
        setStatus(String(error.message || error), "error");
      } finally {
        button.disabled = false;
        button.textContent = "编辑";
      }
    });
  });

  refs.prizeList.querySelectorAll("[data-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      const prize = prizes.find((item) => item.id === button.dataset.delete);
      if (!prize || !window.confirm(`确认删除奖品「${prize.name}」吗？`)) return;
      try {
        const payload = await request("DELETE", `/plugins/slot-box/admin-api/prize/${encodeURIComponent(prize.id)}`);
        applyPayload(payload);
        setStatus("奖品已删除。", "success");
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });
}

function renderRedeemCodes(codes = []) {
  if (!refs.redeemCodeList) return;
  if (!codes.length) {
    refs.redeemCodeList.innerHTML = `<div class="empty">还没有兑换码。</div>`;
    return;
  }
  refs.redeemCodeList.innerHTML = codes.map((code) => `
    <article class="admin-prize">
      <div class="admin-prize-head">
        <div>
          <h3>${escapeHtml(code.code)}</h3>
          <p class="muted">${escapeHtml(code.title || "兑换码")}</p>
        </div>
        <span class="status-pill">${code.enabled ? "启用" : "停用"}</span>
      </div>
      <div class="admin-prize-meta">
        <span class="status-pill">已用 ${escapeHtml(code.used_count || 0)}/${escapeHtml(code.max_uses || 0)}</span>
        <span class="status-pill">单人 ${escapeHtml(code.per_user_limit || 1)}</span>
        <span class="status-pill">${escapeHtml(grantsLabel(code.grants || {}))}</span>
      </div>
      <div class="admin-prize-actions">
        <button type="button" class="secondary" data-edit-code="${escapeHtml(code.code)}">编辑</button>
        <button type="button" class="secondary" data-toggle-code="${escapeHtml(code.code)}">${code.enabled ? "停用" : "启用"}</button>
        <button type="button" class="secondary" data-delete-code="${escapeHtml(code.code)}">删除</button>
      </div>
    </article>
  `).join("");

  refs.redeemCodeList.querySelectorAll("[data-toggle-code]").forEach((button) => {
    button.addEventListener("click", async () => {
      const code = codes.find((item) => item.code === button.dataset.toggleCode);
      if (!code) return;
      try {
        const payload = await request("PATCH", `/plugins/slot-box/admin-api/redeem-code/${encodeURIComponent(code.code)}`, {
          enabled: !code.enabled
        });
        applyPayload(payload);
        setStatus("兑换码状态已更新。", "success");
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });

  refs.redeemCodeList.querySelectorAll("[data-edit-code]").forEach((button) => {
    button.addEventListener("click", async () => {
      const code = codes.find((item) => item.code === button.dataset.editCode);
      if (!code) return;
      const patch = promptRedeemCodePatch(code);
      if (!patch) return;
      try {
        const payload = await request("PATCH", `/plugins/slot-box/admin-api/redeem-code/${encodeURIComponent(code.code)}`, patch);
        applyPayload(payload);
        setStatus("兑换码已更新。", "success");
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });

  refs.redeemCodeList.querySelectorAll("[data-delete-code]").forEach((button) => {
    button.addEventListener("click", async () => {
      const codeValue = button.dataset.deleteCode;
      if (!window.confirm(`确认删除兑换码 ${codeValue} 吗？`)) return;
      try {
        const payload = await request("DELETE", `/plugins/slot-box/admin-api/redeem-code/${encodeURIComponent(codeValue)}`);
        applyPayload(payload);
        setStatus("兑换码已删除。", "success");
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });
}

function parseBooleanPrompt(message, currentValue) {
  const raw = window.prompt(message, currentValue ? "true" : "false");
  if (raw === null) return null;
  const normalized = raw.trim().toLowerCase();
  if (["true", "1", "yes", "y", "是", "开", "开启"].includes(normalized)) return true;
  if (["false", "0", "no", "n", "否", "关", "关闭"].includes(normalized)) return false;
  window.alert("请输入 true 或 false。");
  return parseBooleanPrompt(message, currentValue);
}

function promptPrizePatch(prize) {
  const name = window.prompt("奖品名称：", prize.name || "");
  if (name === null) return null;
  const icon = window.prompt("图标：", prize.icon || "🎁");
  if (icon === null) return null;
  const weight = window.prompt("中奖权重：", prize.weight ?? 0);
  if (weight === null) return null;
  const stock = window.prompt("库存（-1 表示不限）：", prize.stock ?? -1);
  if (stock === null) return null;
  const rewardType = window.prompt("奖品类型（manual / free_spin_ticket / group_invite_credit / account_open_credit / emby_currency）：", prize.reward_type || "manual");
  if (rewardType === null) return null;
  const freeSpinQuantity = window.prompt("奖励数量（货币类型为到账数量）：", prize.free_spin_quantity ?? 0);
  if (freeSpinQuantity === null) return null;
  const description = window.prompt("奖品描述：", prize.description || "");
  if (description === null) return null;
  const deliveryText = window.prompt("发奖说明：", prize.delivery_text || "");
  if (deliveryText === null) return null;
  const broadcastImageUrl = window.prompt("播报图片地址（可留空）：", prize.broadcast_image_url || "");
  if (broadcastImageUrl === null) return null;
  const enabled = parseBooleanPrompt("是否启用（true/false）：", prize.enabled);
  if (enabled === null) return null;
  const guaranteeEligible = parseBooleanPrompt("是否参与保底（true/false）：", prize.guarantee_eligible);
  if (guaranteeEligible === null) return null;
  const broadcastEnabled = parseBooleanPrompt("中奖后是否群播报（true/false）：", prize.broadcast_enabled);
  if (broadcastEnabled === null) return null;
  return {
    name: name.trim(),
    icon: icon.trim(),
    weight: Number(weight || 0),
    stock: Number(stock || 0),
    reward_type: rewardType.trim(),
    free_spin_quantity: Number(freeSpinQuantity || 0),
    description: description.trim(),
    delivery_text: deliveryText.trim(),
    broadcast_image_url: broadcastImageUrl.trim(),
    enabled,
    guarantee_eligible: guaranteeEligible,
    broadcast_enabled: broadcastEnabled
  };
}

function promptRedeemCodePatch(code) {
  const title = window.prompt("兑换码名称：", code.title || "兑换码");
  if (title === null) return null;
  const maxUses = window.prompt("总使用次数（0 表示不限）：", code.max_uses ?? 1);
  if (maxUses === null) return null;
  const perUserLimit = window.prompt("单人使用次数：", code.per_user_limit ?? 1);
  if (perUserLimit === null) return null;
  const ticket = window.prompt("发放抽奖券数量：", code.grants?.free_spin_ticket ?? 0);
  if (ticket === null) return null;
  const group = window.prompt("发放邀请资格数量：", code.grants?.group_invite_credit ?? 0);
  if (group === null) return null;
  const account = window.prompt("发放开号资格数量：", code.grants?.account_open_credit ?? 0);
  if (account === null) return null;
  const enabled = parseBooleanPrompt("是否启用（true/false）：", code.enabled);
  if (enabled === null) return null;
  return {
    title: title.trim(),
    max_uses: Number(maxUses || 0),
    per_user_limit: Number(perUserLimit || 1),
    enabled,
    grants: {
      free_spin_ticket: Number(ticket || 0),
      group_invite_credit: Number(group || 0),
      account_open_credit: Number(account || 0)
    }
  };
}

function applyPayload(payload = {}) {
  state.payload = payload;
  const settings = payload.settings || {};
  const stats = payload.stats || {};
  const probabilities = payload.probabilities || {};

  field("#setting-title").value = settings.title || "";
  field("#setting-notice").value = settings.notice || "";
  field("#setting-blank-label").value = settings.blank_label || "";
  field("#setting-blank-icon").value = settings.blank_icon || "";
  field("#setting-blank-weight").value = settings.blank_weight ?? 0;
  field("#setting-pity-after").value = settings.pity_after ?? 1;
  field("#setting-daily-limit").value = settings.daily_limit ?? 0;
  field("#setting-spin-cost").value = settings.spin_cost_iv ?? 0;
  field("#setting-currency").value = settings.currency_name || "";
  field("#setting-cooldown").value = settings.cooldown_seconds ?? 0;
  field("#setting-record-limit").value = settings.record_limit ?? 300;
  ["a", "b", "c", "d"].forEach((level) => {
    field(`#setting-limit-${level}`).value = settings.daily_limit_by_level?.[level] ?? 0;
    field(`#setting-gift-${level}`).value = settings.daily_gift_by_level?.[level] ?? 0;
  });
  field("#setting-enabled").checked = Boolean(settings.enabled);
  field("#setting-blank-enabled").checked = Boolean(settings.blank_enabled);
  field("#setting-pity-enabled").checked = Boolean(settings.pity_enabled);

  refs.prizeCount.textContent = String(stats.prize_count ?? 0);
  refs.activeCount.textContent = String(stats.active_prize_count ?? 0);
  refs.spinCount.textContent = String(stats.spin_count ?? 0);
  refs.userCount.textContent = String(stats.user_count ?? 0);
  refs.blankRate.textContent = `轮空 ${probabilities.blank_rate ?? 0}%`;
  refs.totalWeight.textContent = `总权重 ${probabilities.total_weight ?? 0}`;

  renderPrizes(payload.prizes || []);
  renderRedeemCodes(payload.redeem_codes || []);
  state.recordPage = 1;
  renderRecords(payload.records || []);
}

async function bootstrap(forceToken = false) {
  if (state.initData && !forceToken) {
    state.authMode = "telegram";
    refs.authMode.textContent = "主人直登";
    const payload = await request("POST", "/plugins/slot-box/admin-api/bootstrap", {
      init_data: state.initData
    });
    applyPayload(payload);
    setStatus("已通过 Telegram 主人身份进入后台。", "success");
    return;
  }

  if (!state.token) {
    throw new Error("缺少后台令牌");
  }
  state.authMode = "token";
  refs.authMode.textContent = "令牌登录";
  const payload = await request("POST", "/plugins/slot-box/admin-api/bootstrap", {
    token: state.token
  });
  applyPayload(payload);
  setStatus("后台令牌验证通过。", "success");
}

refs.tokenForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const previous = refs.tokenSubmit.textContent;
  state.token = refs.tokenInput?.value.trim() || "";
  writeLocalStorage(storageKey, state.token);
  refs.tokenSubmit.disabled = true;
  refs.tokenSubmit.textContent = "验证中";
  setStatus("正在验证后台令牌。", "info");
  try {
    await bootstrap(true);
  } catch (error) {
    setStatus(String(error.message || error), "error");
  } finally {
    refs.tokenSubmit.disabled = false;
    refs.tokenSubmit.textContent = previous;
  }
});

refs.settingsForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const previous = refs.settingsSubmit.textContent;
  refs.settingsSubmit.disabled = true;
  refs.settingsSubmit.textContent = "保存中";
  try {
    const payload = await request("POST", "/plugins/slot-box/admin-api/settings", {
      enabled: checked("#setting-enabled"),
      title: field("#setting-title").value.trim(),
      notice: field("#setting-notice").value.trim(),
      blank_enabled: checked("#setting-blank-enabled"),
      blank_label: field("#setting-blank-label").value.trim(),
      blank_icon: field("#setting-blank-icon").value.trim(),
      blank_weight: numberValue("#setting-blank-weight", 0),
      pity_enabled: checked("#setting-pity-enabled"),
      pity_after: numberValue("#setting-pity-after", 1),
      daily_limit: numberValue("#setting-daily-limit", 0),
      spin_cost_iv: numberValue("#setting-spin-cost", 0),
      currency_name: field("#setting-currency").value.trim(),
      daily_limit_by_level: levelMap("setting-limit"),
      daily_gift_by_level: levelMap("setting-gift"),
      cooldown_seconds: numberValue("#setting-cooldown", 0),
      record_limit: numberValue("#setting-record-limit", 300)
    });
    applyPayload(payload);
    setStatus("玩法设置已保存。", "success");
  } catch (error) {
    setStatus(String(error.message || error), "error");
  } finally {
    refs.settingsSubmit.disabled = false;
    refs.settingsSubmit.textContent = previous;
  }
});

refs.prizeForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const previous = refs.prizeSubmit.textContent;
  refs.prizeSubmit.disabled = true;
  refs.prizeSubmit.textContent = "创建中";
  try {
    const payload = await request("POST", "/plugins/slot-box/admin-api/prize", {
      name: field("#prize-name").value.trim(),
      icon: field("#prize-icon").value.trim(),
      description: field("#prize-description").value.trim(),
      delivery_text: field("#prize-delivery").value.trim(),
      reward_type: field("#prize-reward-type").value,
      free_spin_quantity: numberValue("#prize-free-spin-quantity", 0),
      broadcast_image_url: field("#prize-broadcast-image").value.trim(),
      weight: numberValue("#prize-weight", 10),
      stock: numberValue("#prize-stock", -1),
      enabled: checked("#prize-enabled"),
      guarantee_eligible: checked("#prize-guarantee"),
      broadcast_enabled: checked("#prize-broadcast")
    });
    applyPayload(payload);
    refs.prizeForm.reset();
    field("#prize-icon").value = "🎁";
    field("#prize-weight").value = 10;
    field("#prize-stock").value = -1;
    field("#prize-reward-type").value = "manual";
    field("#prize-free-spin-quantity").value = 0;
    field("#prize-enabled").checked = true;
    field("#prize-guarantee").checked = true;
    field("#prize-broadcast").checked = false;
    setStatus("奖品已创建。", "success");
  } catch (error) {
    setStatus(String(error.message || error), "error");
  } finally {
    refs.prizeSubmit.disabled = false;
    refs.prizeSubmit.textContent = previous;
  }
});


refs.recordFilter?.addEventListener("change", (event) => {
  state.recordFilter = event.target.value || "all";
  state.recordPage = 1;
  renderRecords();
});

refs.recordPrev?.addEventListener("click", () => {
  state.recordPage -= 1;
  renderRecords();
});

refs.recordNext?.addEventListener("click", () => {
  state.recordPage += 1;
  renderRecords();
});

refs.redeemCodeForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const previous = refs.redeemCodeSubmit.textContent;
  refs.redeemCodeSubmit.disabled = true;
  refs.redeemCodeSubmit.textContent = "生成中";
  try {
    const payload = await request("POST", "/plugins/slot-box/admin-api/redeem-code", {
      code: field("#redeem-code-value").value.trim(),
      title: field("#redeem-code-title").value.trim(),
      max_uses: numberValue("#redeem-code-max-uses", 1),
      per_user_limit: numberValue("#redeem-code-per-user", 1),
      enabled: checked("#redeem-code-enabled"),
      grants: grantsPayload()
    });
    applyPayload(payload);
    refs.redeemCodeForm.reset();
    field("#redeem-code-title").value = "兑换码";
    field("#redeem-code-max-uses").value = 1;
    field("#redeem-code-per-user").value = 1;
    field("#redeem-code-enabled").checked = true;
    setStatus("兑换码已生成。", "success");
  } catch (error) {
    setStatus(String(error.message || error), "error");
  } finally {
    refs.redeemCodeSubmit.disabled = false;
    refs.redeemCodeSubmit.textContent = previous;
  }
});

(async () => {
  if (tg) {
    tg.ready();
    tg.expand();
    tg.setHeaderColor("#17120f");
    tg.setBackgroundColor("#111111");
  }
  try {
    await bootstrap();
  } catch (error) {
    refs.authMode.textContent = "待认证";
    setStatus(String(error.message || error), "error");
  }
})();
