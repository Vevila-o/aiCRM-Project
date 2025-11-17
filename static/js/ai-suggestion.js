console.log("ai-suggestion.js loaded");

// 後端 API 路徑 & 本機歷史記錄 key
const BACKEND_ENDPOINT = "/chat/";
const LS_HISTORY_KEY   = "AI_SUGGESTION_HISTORY";

// 左側說明卡的靜態資料（依顧客群組）
const DATA = {
  vip: {
    title: "高價值顧客",
    features: [
      "RFM 平均分數：5-5-5",
      "平均消費金額：NT$ 8,000 / 月",
      "最近購買日：30 天內"
    ],
    plans: [
      "維繫忠誠：推出 VIP 專屬優惠或會員升級制度",
      "提升單價：搭配推薦產品組合（Cross-selling）",
      "情感連結：寄送感謝信或專屬生日優惠"
    ],
    outcomes: ["回購率提升 10%", "平均客單價提升 8%"],
    channels: "Email、LINE 官方帳號、App 推播"
  },
  risk: {
    title: "高風險顧客",
    features: [
      "RFM 平均分數：2-1-1",
      "平均消費金額：NT$ 800 / 月",
      "最近購買日：超過 90 天"
    ],
    plans: [
      "挽回關係：提供回流專屬 1 次性折扣／免運券",
      "降低流失：發送關懷問卷蒐集流失原因並回饋點數",
      "重新喚起：推薦低門檻入手商品或組合"
    ],
    outcomes: ["回流率提升 6%", "退訂率下降 3%"],
    channels: "SNS 再行銷、EDM、簡訊"
  },
  new: {
    title: "新進顧客",
    features: [
      "RFM 平均分數：3-4-1",
      "平均消費金額：NT$ 1,500 / 月",
      "最近購買日：7 天內首次成交"
    ],
    plans: [
      "加速熟悉：新手引導內容（如何挑選／使用指南）",
      "第二單激勵：7 天內下次消費 9 折券",
      "收集偏好：導入產品喜好標籤以利個人化推薦"
    ],
    outcomes: ["次月第二單率提升 12%", "名單標籤完整度達 80%"],
    channels: "歡迎信系列、站內訊息、App 新手任務"
  }
};

// 取得 DOM 元件
const contentEl = document.getElementById("content");
const selectEl  = document.getElementById("segmentSelect");
const askBtn    = document.getElementById("askBtn");
const qEl       = document.getElementById("q");
const chatBox   = document.getElementById("chatMessages");
const clearBtn  = document.getElementById("clearBtn");

// 把下拉選單的 1~7 轉成 DATA 的 key
function valueToKey(val) {
  switch (val) {
    case "1": // 忠誠客戶
    case "2": // 潛在高價值客戶
      return "vip";
    case "5": // 潛在流失
    case "7": // 低價值客戶
      return "risk";
    case "6": // 新客
      return "new";
    default:
      return null;
  }
}

// 渲染左側說明卡
function renderSegment(key) {
  const d = DATA[key];
  if (!d) {
    contentEl.innerHTML = "";
    return;
  }
  const li = arr => arr.map(x => `<li>${x}</li>`).join("");
  contentEl.innerHTML = `
    <h2>${d.title}</h2>
    <p class="section-title">特徵：</p>
    <ul>${li(d.features)}</ul>
    <p class="section-title">AI 建議方針：</p>
    <ul>${li(d.plans)}</ul>
    <p class="section-title">預期成果：</p>
    <ul>${li(d.outcomes)}</ul>
    <p class="section-title">建議管道：</p>
    <p style="margin:.25rem 0 0 1rem">${d.channels}</p>
  `;
}

// 右側輸入框 placeholder 文字，會跟下拉選單一起變
function updatePlaceholder() {
  const label = selectEl.options[selectEl.selectedIndex]?.text || "顧客";
  qEl.placeholder = `例：請為『${label}』擬 3 則關懷簡訊範本`;
}

// ✅ 初始化（確保一進頁就有預設顧客＋左側卡片＋右側 placeholder）
window.addEventListener("DOMContentLoaded", () => {
  // 1️⃣ 如果一開始沒有值，就強制選「忠誠客戶」（value = 1）
  if (!selectEl.value) {
    selectEl.value = "1";
  }

  // 2️⃣ 根據目前選單的值，決定左側說明卡要顯示哪一組
  const initKey = valueToKey(selectEl.value); // 會轉成 vip / risk / new
  if (initKey) {
    renderSegment(initKey);  // 一進來就渲染左側，不會是空白
  }

  // 3️⃣ 同步更新右側輸入框的 placeholder
  updatePlaceholder();

  // 4️⃣ 之後每次切換選單，同時改左側卡片 + placeholder
  selectEl.addEventListener("change", e => {
    const key = valueToKey(e.target.value);
    if (key) {
      renderSegment(key);
    } else {
      contentEl.innerHTML = "";
    }
    updatePlaceholder();
  });
});

// ---- 聊天記錄（存在瀏覽器 localStorage） ----
function loadHistory() {
  try {
    const raw = localStorage.getItem(LS_HISTORY_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}
function saveHistory(his) {
  localStorage.setItem(LS_HISTORY_KEY, JSON.stringify(his));
}
function clearHistory() {
  localStorage.removeItem(LS_HISTORY_KEY);
}

let history = loadHistory();

function renderMessages() {
  chatBox.innerHTML = "";
  history.forEach(m =>
    appendMessage(m.role === "assistant" ? "ai" : "user", m.content)
  );
  chatBox.scrollTop = chatBox.scrollHeight;
}

function appendMessage(role, text, isLoading = false) {
  const msg = document.createElement("div");
  msg.className = `msg ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble" + (isLoading ? " loading" : "");
  bubble.textContent = text;
  msg.appendChild(bubble);
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
  return bubble;
}

renderMessages();

async function sendToBackend(message, categoryID) {
  const resp = await fetch(BACKEND_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: message,
      categoryID: categoryID
    })
  });

  if (!resp.ok) {
    const t = await resp.text().catch(() => "");
    throw new Error(`後端錯誤：${resp.status} ${t}`);
  }
  const data = await resp.json();
  if (!data || typeof data.reply !== "string") {
    throw new Error("回傳格式錯誤，需為 { reply: string }");
  }
  return data.reply.trim();
}

// ---- 問問題主流程 ----
async function ask(question) {
  const categoryID = selectEl.value;  // 這裡直接就是 1~7

  appendMessage("user", question);
  const loading = appendMessage("ai", "正在思考中…", true);

  // 本機歷史（只管前端顯示）
  history.push({ role: "user", content: question });

  try {
    const reply = await sendToBackend(question, categoryID);

    loading.textContent = reply;
    loading.classList.remove("loading");

    history.push({ role: "assistant", content: reply });
    saveHistory(history);

  } catch (err) {
    loading.textContent = `❗發生錯誤：${err.message}`;
    loading.classList.remove("loading");
  }
}

// 按鈕事件：送出問題
askBtn.addEventListener("click", () => {
  const q = (qEl.value || "").trim();
  if (!q) return;
  ask(q);
  qEl.value = "";
});

// 按鈕事件：清除本機對話
clearBtn.addEventListener("click", () => {
  history = [];
  clearHistory();
  renderMessages();
});