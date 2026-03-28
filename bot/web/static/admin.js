const storageKey = "pivkeyu-admin-token";

const state = {
  page: 1,
  pageSize: 20,
  query: "",
  selectedTg: null,
  token: localStorage.getItem(storageKey) || ""
};

const tokenInput = document.querySelector("#admin-token");
const tokenStatus = document.querySelector("#token-status");
const editorStatus = document.querySelector("#editor-status");
const pageLabel = document.querySelector("#page-label");
const tableBody = document.querySelector("#user-table-body");
const pluginList = document.querySelector("#plugin-list");

tokenInput.value = state.token;

function authHeaders() {
  return state.token ? { "X-Admin-Token": state.token } : {};
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {})
    }
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }

  return response.json();
}

function setSummary(data) {
  document.querySelector("#summary-total").textContent = data.total_users;
  document.querySelector("#summary-active").textContent = data.active_accounts;
  document.querySelector("#summary-banned").textContent = data.banned_users;
  document.querySelector("#summary-currency").textContent = data.total_currency;
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

function renderUsers(items) {
  tableBody.innerHTML = "";

  if (!items.length) {
    tableBody.innerHTML = `<tr><td colspan="5">没有查到记录。</td></tr>`;
    return;
  }

  for (const item of items) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${item.tg}</td>
      <td>${item.name || "-"}</td>
      <td>${item.lv || "-"}</td>
      <td>${item.iv ?? 0}</td>
      <td>${item.embyid || "-"}</td>
    `;
    row.addEventListener("click", () => loadUser(item.tg));
    tableBody.appendChild(row);
  }
}

function renderPlugins(items) {
  pluginList.innerHTML = "";

  for (const item of items) {
    const card = document.createElement("article");
    const stateClass = item.loaded ? "is-on" : "is-off";
    const stateText = item.loaded ? "已装载" : item.enabled ? "装载失败" : "未启用";
    card.className = "plugin-card";
    card.innerHTML = `
      <header>
        <strong>${item.name}</strong>
        <span class="plugin-state ${stateClass}">${stateText}</span>
      </header>
      <p>${item.description || "暂无描述"}</p>
      <small>${item.id} · v${item.version}</small>
      ${item.error ? `<p class="muted">错误: ${item.error}</p>` : ""}
    `;
    pluginList.appendChild(card);
  }
}

function fillEditor(item) {
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
}

async function loadSummary() {
  const result = await api("/admin-api/summary");
  setSummary(result.data);
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
  renderUsers(result.data.items);
  pageLabel.textContent = `第 ${result.data.page} 页 / 共 ${Math.max(1, Math.ceil(result.data.total / result.data.page_size))} 页`;
  document.querySelector("#prev-page").disabled = result.data.page <= 1;
  document.querySelector("#next-page").disabled = result.data.page * result.data.page_size >= result.data.total;
}

async function loadUser(tg) {
  const result = await api(`/admin-api/users/${tg}`);
  state.selectedTg = tg;
  fillEditor(result.data);
  editorStatus.textContent = `当前正在编辑 TG ${tg}`;
}

async function saveUser(event) {
  event.preventDefault();

  if (!state.selectedTg) {
    editorStatus.textContent = "先选择一个用户再保存。";
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
    const result = await api(`/admin-api/users/${state.selectedTg}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
    fillEditor(result.data);
    editorStatus.textContent = `TG ${state.selectedTg} 已保存。`;
    await Promise.all([loadSummary(), loadUsers()]);
  } catch (error) {
    editorStatus.textContent = `保存失败: ${error.message}`;
  }
}

document.querySelector("#token-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  state.token = tokenInput.value.trim();
  localStorage.setItem(storageKey, state.token);
  tokenStatus.textContent = "Token 已保存，正在重新加载数据。";

  try {
    await Promise.all([loadSummary(), loadPlugins(), loadUsers()]);
    tokenStatus.textContent = "连接成功。";
  } catch (error) {
    tokenStatus.textContent = `连接失败: ${error.message}`;
  }
});

document.querySelector("#search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  state.page = 1;
  state.query = document.querySelector("#search-input").value.trim();
  await loadUsers();
});

document.querySelector("#prev-page").addEventListener("click", async () => {
  if (state.page <= 1) return;
  state.page -= 1;
  await loadUsers();
});

document.querySelector("#next-page").addEventListener("click", async () => {
  state.page += 1;
  await loadUsers();
});

document.querySelector("#editor-form").addEventListener("submit", saveUser);

(async () => {
  if (!state.token) {
    tokenStatus.textContent = "先输入管理 Token。";
    return;
  }

  try {
    await Promise.all([loadSummary(), loadPlugins(), loadUsers()]);
    tokenStatus.textContent = "连接成功。";
  } catch (error) {
    tokenStatus.textContent = `连接失败: ${error.message}`;
  }
})();
