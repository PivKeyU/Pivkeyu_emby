const tg = window.Telegram?.WebApp || null;

const state = {
  initData: tg?.initData || "",
  payload: null,
  symbols: ["🎁", "◇", "🎫", "★"],
  spinning: false,
  reelTimers: []
};

const refs = {
  title: document.querySelector("#slot-title"),
  notice: document.querySelector("#slot-notice"),
  status: document.querySelector("#app-status"),
  adminEntry: document.querySelector("#slot-admin-entry"),
  spinButton: document.querySelector("#spin-button"),
  refreshButton: document.querySelector("#refresh-button"),
  resultPanel: document.querySelector("#result-panel"),
  reels: Array.from(document.querySelectorAll(".reel")),
  pityMeter: document.querySelector("#pity-meter"),
  limitMeter: document.querySelector("#limit-meter"),
  balanceCount: document.querySelector("#balance-count"),
  spinCost: document.querySelector("#spin-cost"),
  dailyGiftCount: document.querySelector("#daily-gift-count"),
  ticketCount: document.querySelector("#ticket-count"),
  spinCount: document.querySelector("#spin-count"),
  winCount: document.querySelector("#win-count"),
  blankCount: document.querySelector("#blank-count"),
  prizeCount: document.querySelector("#prize-count"),
  blankRate: document.querySelector("#blank-rate"),
  myStreak: document.querySelector("#my-streak"),
  prizeList: document.querySelector("#prize-list"),
  recordList: document.querySelector("#record-list"),
  backpackList: document.querySelector("#backpack-list"),
  marketList: document.querySelector("#market-list"),
  redeemForm: document.querySelector("#redeem-form"),
  redeemSubmit: document.querySelector("#redeem-submit"),
  transferForm: document.querySelector("#transfer-form"),
  transferSubmit: document.querySelector("#transfer-submit"),
  listingForm: document.querySelector("#listing-form"),
  listingSubmit: document.querySelector("#listing-submit"),
  bottomNav: document.querySelector("#bottom-nav")
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
  if (!refs.status) return;
  refs.status.textContent = text;
  refs.status.dataset.tone = tone;
}

async function request(url, payload) {
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {})
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

function randomSymbol() {
  const symbols = state.symbols.length ? state.symbols : ["🎁", "◇", "★"];
  return symbols[Math.floor(Math.random() * symbols.length)] || "◇";
}

function startReels() {
  stopReels();
  state.spinning = true;
  refs.reels.forEach((reel, index) => {
    reel.classList.add("spinning");
    state.reelTimers[index] = window.setInterval(() => {
      reel.textContent = randomSymbol();
    }, 70 + index * 20);
  });
}

function stopReels(finalReels = []) {
  state.reelTimers.forEach((timer) => window.clearInterval(timer));
  state.reelTimers = [];
  refs.reels.forEach((reel, index) => {
    reel.classList.remove("spinning");
    reel.textContent = finalReels[index] || reel.textContent || randomSymbol();
  });
  state.spinning = false;
}

async function settleReels(finalReels) {
  state.reelTimers.forEach((timer) => window.clearInterval(timer));
  state.reelTimers = [];
  for (let index = 0; index < refs.reels.length; index += 1) {
    await new Promise((resolve) => window.setTimeout(resolve, 180 + index * 80));
    refs.reels[index].classList.remove("spinning");
    refs.reels[index].textContent = finalReels[index] || randomSymbol();
  }
  state.spinning = false;
}

function renderBottomNav(items = []) {
  if (!refs.bottomNav) return;
  if (!items.length) {
    refs.bottomNav.classList.add("hidden");
    return;
  }
  refs.bottomNav.classList.remove("hidden");
  const currentPath = window.location.pathname;
  refs.bottomNav.innerHTML = items.map((item) => {
    const active = item.path === currentPath ? "active" : "";
    return `
      <a class="${active}" href="${escapeHtml(item.path)}">
        <span class="nav-icon">${escapeHtml(item.icon || "◇")}</span>
        <span>${escapeHtml(item.label || item.id || "入口")}</span>
      </a>
    `;
  }).join("");
}

function renderPrizes(prizes = []) {
  if (!prizes.length) {
    refs.prizeList.innerHTML = `<div class="empty">当前奖池为空。</div>`;
    return;
  }
  refs.prizeList.innerHTML = prizes.map((prize) => `
    <article class="prize-card">
      <div class="prize-card-head">
        <span class="prize-icon">${escapeHtml(prize.icon || "🎁")}</span>
        <span class="rate-text">${escapeHtml(prize.computed_rate ?? 0)}%</span>
      </div>
      <h3>${escapeHtml(prize.name)}</h3>
      <p class="muted">${escapeHtml(prize.description || "")}</p>
      <p class="muted">库存 ${Number(prize.stock) < 0 ? "不限" : escapeHtml(prize.stock)}</p>
    </article>
  `).join("");
}

function renderRecords(records = []) {
  if (!records.length) {
    refs.recordList.innerHTML = `<div class="empty">暂无抽取记录。</div>`;
    return;
  }
  refs.recordList.innerHTML = records.map((record) => `
    <article class="record-item" data-outcome="${escapeHtml(record.outcome)}">
      <div class="record-line">
        <strong>${escapeHtml(record.prize_icon || "◇")} ${escapeHtml(record.prize_name || "轮空")}</strong>
        <span class="status-pill">${record.outcome === "win" ? "中奖" : "未中"}</span>
      </div>
      <p class="muted">${escapeHtml(record.created_at || "")}${record.pity_triggered ? " · 保底" : ""}</p>
    </article>
  `).join("");
}

function renderBackpack(items = []) {
  if (!refs.backpackList) return;
  if (!items.length) {
    refs.backpackList.innerHTML = `<div class="empty">背包为空。</div>`;
    return;
  }
  refs.backpackList.innerHTML = items.map((item) => `
    <article class="prize-card">
      <div class="prize-card-head">
        <span class="prize-icon">${escapeHtml(item.icon || "◇")}</span>
        <span class="rate-text">x${escapeHtml(item.quantity ?? 0)}</span>
      </div>
      <h3>${escapeHtml(item.label || item.type)}</h3>
      <p class="muted">可转赠或上架交易。</p>
    </article>
  `).join("");
}

function renderMarket(listings = []) {
  if (!refs.marketList) return;
  if (!listings.length) {
    refs.marketList.innerHTML = `<div class="empty">暂无上架物品。</div>`;
    return;
  }
  const myId = Number(state.payload?.account?.tg || 0);
  refs.marketList.innerHTML = listings.map((item) => `
    <article class="record-item">
      <div class="record-line">
        <strong>${escapeHtml(item.item_icon || "◇")} ${escapeHtml(item.item_label || item.item_type)} x${escapeHtml(item.quantity)}</strong>
        <span class="status-pill">${escapeHtml(item.price_iv)} ${escapeHtml(state.payload?.settings?.currency_name || "")}</span>
      </div>
      <p class="muted">卖家：${escapeHtml(item.seller_display || item.seller_tg)} · ${escapeHtml(item.created_at || "")}</p>
      <div class="form-actions">
        ${Number(item.seller_tg) === myId
          ? `<button type="button" class="secondary" data-cancel-listing="${escapeHtml(item.id)}">下架</button>`
          : `<button type="button" class="secondary" data-buy-listing="${escapeHtml(item.id)}">购买</button>`}
      </div>
    </article>
  `).join("");

  refs.marketList.querySelectorAll("[data-buy-listing]").forEach((button) => {
    button.addEventListener("click", async () => {
      await mutateWithButton(button, "购买中", "/plugins/slot-box/api/listing/purchase", {
        init_data: state.initData,
        listing_id: button.dataset.buyListing
      }, "购买完成。");
    });
  });

  refs.marketList.querySelectorAll("[data-cancel-listing]").forEach((button) => {
    button.addEventListener("click", async () => {
      await mutateWithButton(button, "下架中", "/plugins/slot-box/api/listing/cancel", {
        init_data: state.initData,
        listing_id: button.dataset.cancelListing
      }, "已下架。");
    });
  });
}

function renderResult(result) {
  if (!result) return;
  refs.resultPanel.classList.remove("hidden");
  refs.resultPanel.dataset.outcome = result.outcome || "blank";
  const prize = result.prize || {};
  refs.resultPanel.innerHTML = `
    <div class="record-line">
      <h3>${escapeHtml(result.title || "结果")}</h3>
      <span class="status-pill">${result.pity_triggered ? "保底触发" : result.outcome === "win" ? "中奖" : "轮空"}</span>
    </div>
    <p class="muted">${escapeHtml(result.message || "")}</p>
    <p class="muted">本次消耗：${escapeHtml(result.payment_label || "-")}</p>
    ${prize.name ? `<p class="muted">奖品：${escapeHtml(prize.icon || "🎁")} ${escapeHtml(prize.name)}</p>` : ""}
  `;
}

function applyPayload(payload = {}) {
  state.payload = payload;
  state.symbols = payload.meta?.symbols || state.symbols;
  const settings = payload.settings || {};
  const stats = payload.stats || {};
  const userStats = payload.user_stats || {};
  const probabilities = payload.probabilities || {};
  const limits = payload.limits || {};
  const account = payload.account || null;
  refs.title.textContent = settings.title || "老虎机盲盒";
  refs.notice.textContent = settings.notice || "";
  refs.spinButton.disabled = !settings.enabled || state.spinning || Boolean(payload.limits?.wait_seconds);
  refs.balanceCount.textContent = account ? String(account.iv ?? 0) : "无账号";
  refs.spinCost.textContent = `${limits.spin_cost_iv ?? settings.spin_cost_iv ?? 0}`;
  refs.dailyGiftCount.textContent = `${limits.daily_free_remaining ?? 0}/${limits.daily_gift_total ?? 0}`;
  refs.ticketCount.textContent = String(limits.free_spin_tickets ?? userStats.free_spin_tickets ?? 0);
  refs.spinCount.textContent = String(userStats.total_spins ?? 0);
  refs.winCount.textContent = String(userStats.win_count ?? 0);
  refs.blankCount.textContent = String(userStats.blank_count ?? 0);
  refs.prizeCount.textContent = String(stats.active_prize_count ?? 0);
  refs.blankRate.textContent = `轮空 ${probabilities.blank_rate ?? 0}%`;
  refs.myStreak.textContent = `连续未中 ${userStats.miss_streak ?? 0}`;

  if (settings.pity_enabled) {
    refs.pityMeter.textContent = `保底 ${userStats.miss_streak ?? 0}/${settings.pity_after || 1}`;
  } else {
    refs.pityMeter.textContent = "保底关闭";
  }

  const dailyRemaining = payload.limits?.daily_remaining;
  const waitSeconds = Number(payload.limits?.wait_seconds || 0);
  if (waitSeconds > 0) {
    refs.limitMeter.textContent = `冷却 ${waitSeconds}s`;
  } else if (dailyRemaining === null || dailyRemaining === undefined) {
    refs.limitMeter.textContent = "次数不限";
  } else {
    refs.limitMeter.textContent = `剩余 ${dailyRemaining} · ${limits.user_level_text || "未知"}`;
    if (Number(dailyRemaining) <= 0) refs.spinButton.disabled = true;
  }

  if (payload.permissions?.admin_url) {
    refs.adminEntry.href = payload.permissions.admin_url;
    refs.adminEntry.classList.remove("hidden");
  } else {
    refs.adminEntry.classList.add("hidden");
  }

  renderPrizes(payload.prizes || []);
  renderRecords(payload.records || []);
  renderBackpack(payload.backpack || []);
  renderMarket(payload.market_listings || []);
  renderBottomNav(payload.meta?.bottom_nav || []);
}

async function mutateWithButton(button, pendingText, url, payload, successText) {
  const previous = button.textContent;
  button.disabled = true;
  button.textContent = pendingText;
  try {
    const nextPayload = await request(url, payload);
    applyPayload(nextPayload);
    setStatus(successText, "success");
  } catch (error) {
    setStatus(String(error.message || error), "error");
  } finally {
    button.disabled = false;
    button.textContent = previous;
  }
}

async function bootstrap() {
  if (!state.initData) {
    throw new Error("请从 Telegram 小程序入口打开。");
  }
  const payload = await request("/plugins/slot-box/api/bootstrap", { init_data: state.initData });
  applyPayload(payload);
  setStatus("奖池已同步。", "success");
}

async function spin() {
  if (state.spinning) return;
  if (!state.initData) {
    setStatus("请从 Telegram 小程序入口打开。", "error");
    return;
  }
  refs.spinButton.disabled = true;
  refs.refreshButton.disabled = true;
  refs.resultPanel.classList.add("hidden");
  setStatus("转轮启动。", "info");
  startReels();
  const startedAt = Date.now();
  try {
    const payload = await request("/plugins/slot-box/api/spin", { init_data: state.initData });
    const delay = Math.max(900 - (Date.now() - startedAt), 0);
    if (delay) await new Promise((resolve) => window.setTimeout(resolve, delay));
    await settleReels(payload.result?.reels || []);
    applyPayload(payload);
    renderResult(payload.result);
    setStatus(payload.result?.outcome === "win" ? "已中奖。" : "本次轮空。", payload.result?.outcome === "win" ? "success" : "info");
  } catch (error) {
    stopReels();
    setStatus(String(error.message || error), "error");
  } finally {
    refs.refreshButton.disabled = false;
    const waitSeconds = Number(state.payload?.limits?.wait_seconds || 0);
    const dailyRemaining = state.payload?.limits?.daily_remaining;
    const dailyLimitReached = dailyRemaining !== null && dailyRemaining !== undefined && Number(dailyRemaining) <= 0;
    refs.spinButton.disabled = !state.payload?.settings?.enabled || waitSeconds > 0 || dailyLimitReached;
  }
}

refs.spinButton?.addEventListener("click", spin);
refs.refreshButton?.addEventListener("click", async () => {
  refs.refreshButton.disabled = true;
  setStatus("正在刷新。", "info");
  try {
    await bootstrap();
  } catch (error) {
    setStatus(String(error.message || error), "error");
  } finally {
    refs.refreshButton.disabled = false;
  }
});

refs.redeemForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const code = document.querySelector("#redeem-code")?.value.trim() || "";
  if (!code) return;
  await mutateWithButton(refs.redeemSubmit, "兑换中", "/plugins/slot-box/api/redeem", {
    init_data: state.initData,
    code
  }, "兑换成功。");
});

refs.transferForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await mutateWithButton(refs.transferSubmit, "转赠中", "/plugins/slot-box/api/transfer", {
    init_data: state.initData,
    item_type: document.querySelector("#transfer-type")?.value,
    quantity: Number(document.querySelector("#transfer-quantity")?.value || 1),
    target_tg: Number(document.querySelector("#transfer-target")?.value || 0)
  }, "转赠完成。");
});

refs.listingForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await mutateWithButton(refs.listingSubmit, "上架中", "/plugins/slot-box/api/listing", {
    init_data: state.initData,
    item_type: document.querySelector("#listing-type")?.value,
    quantity: Number(document.querySelector("#listing-quantity")?.value || 1),
    price_iv: Number(document.querySelector("#listing-price")?.value || 0)
  }, "上架成功。");
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
    setStatus(String(error.message || error), "error");
  }
})();
