async function bootstrapMiniApp() {
  const tg = window.Telegram?.WebApp;
  const welcomeText = document.querySelector("#welcome-text");

  if (!tg) {
    welcomeText.textContent = "当前页面需要从 Telegram Mini App 中打开。";
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
      throw new Error(result.detail || result.message || "Mini App 初始化失败");
    }

    const { telegram_user, account, meta } = result.data;

    document.querySelector("#tg-id").textContent = telegram_user.id;
    document.querySelector("#tg-name").textContent = telegram_user.first_name || telegram_user.username || "未命名用户";
    document.querySelector("#account-lv").textContent = account?.lv || "未绑定";
    document.querySelector("#account-iv").textContent = account?.iv ?? 0;
    document.querySelector("#account-name").textContent = account?.name || "尚未绑定 Emby";
    document.querySelector("#account-ex").textContent = account?.ex ? new Date(account.ex).toLocaleString() : "暂无";
    welcomeText.textContent = `欢迎回来，${telegram_user.first_name || "用户"}。当前品牌是 ${meta.brand}，主货币是 ${meta.currency}。`;

    const pluginRow = document.querySelector("#plugin-row");
    for (const plugin of meta.plugins) {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = `${plugin.name}${plugin.loaded ? "" : " · 待启用"}`;
      pluginRow.appendChild(chip);
    }
  } catch (error) {
    welcomeText.textContent = `初始化失败: ${error.message}`;
  }
}

bootstrapMiniApp();
