console.log("ai-suggestion.js loaded");


// 從首頁取得 seg/period，產生左上角標題
const urlParams = new URLSearchParams(window.location.search);
const seg    = urlParams.get("seg");      //ex:lotal/low_value...
const period = urlParams.get("period");   // month / quarter

// 顧客類型中文名稱
const SEG_NAME = {
  lotal:          "忠誠客戶",
  potential_high: "潛在高價值顧客",
  regular:        "普通顧客",
  low_value:      "低價值顧客",
  dormant:        "沉睡顧客",
  at_risk:        "潛在流失顧客",
  new:            "新客"
};

//區間中文名稱
const PERIOD_NAME = {
  month:   "本月",
  quarter: "本季",
};

// 根據seg+period寫入標題文字
function renderTitle() {
  const titleEl = document.getElementById("suggestionTitle");
  if (!titleEl) return;

  const segName    = SEG_NAME[seg]    || "顧客";
  const periodName = PERIOD_NAME[period] || "";

  if (periodName) {
    titleEl.textContent = `根據${periodName}${segName}資料，給你以下行銷建議：`;
  } else {
    titleEl.textContent = `根據${segName}資料，給你以下建議優惠券：`;
  }
}



// =========================================================
// 後端 API 路徑（依你 Django 架構）
// =========================================================
const API_INIT     = "/ai-suggestion/init/";
const API_CHAT     = "/chat/";
const API_EXECUTE  = "/ai-suggestion/execute/";


// =========================================================
// 右側聊天 — DOM
// =========================================================
const askBtn  = document.getElementById("askBtn");
const qEl     = document.getElementById("q");
const chatBox = document.getElementById("chatMessages");
const clearBtn= document.getElementById("clearBtn");


// =========================================================
 // 左側建議欄 DOM + 分頁
// =========================================================
const suggestionListEl = document.getElementById("suggestionList");
const paginationEl     = document.getElementById("pagination");

let suggestions = [];      // 全部資料
let currentPage = 1;
const PAGE_SIZE = 3;


// =========================================================
// 一開始根據首頁 seg=xxx 推回 categoryID（1~7）
// =========================================================
function getCategoryIdFromSeg() {
  const params = new URLSearchParams(window.location.search);
  const segParam = params.get("seg");

  switch (segParam) {
    case "lotal":          return 1; // 忠誠
    case "potential_high": return 2; // 潛在高價值
    case "dormant":        return 3; // 沉睡
    case "regular":        return 4; // 普通
    case "at_risk":        return 5; // 潛在流失
    case "new":            return 7; // 新客
    case "low_value":      return 6; // 低價值
    default:               return null;
  }
}

const CATEGORY_ID = getCategoryIdFromSeg();


// =========================================================
// 1. 初始載入 — 從後端要模型建議
// =========================================================
async function loadInitialSuggestion() {
  try {
    const resp = await fetch(`${API_INIT}?categoryID=${CATEGORY_ID}&period=${encodeURIComponent(period || "")}`);
    if (!resp.ok) {
      console.error("初始建議載入失敗：HTTP", resp.status);
      return;
    }
    const data = await resp.json();

    //左 第一筆建議
    if (data.initial) {
      suggestions.unshift(data.initial);
      renderSuggestionList();
    }

    //右 等同於使用者先問一次+ai回答一次
    if (data.question && data.reply) {
      
      appendMessage("user", data.question);
      appendMessage("ai", data.reply);
    }    

  } catch (err) {
    console.error("初始建議載入失敗:", err);
  }
}


// =========================================================
// 分頁 — 取得目前頁的三筆
// =========================================================
function getPagedSuggestions() {
  const start = (currentPage - 1) * PAGE_SIZE;
  return suggestions.slice(start, start + PAGE_SIZE);
}


// =========================================================
// 渲染建議列表
// =========================================================
function renderSuggestionList() {
  if (!suggestionListEl) return;

  const total = suggestions.length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (currentPage > totalPages) currentPage = totalPages;

  const pageData = getPagedSuggestions();

  if (!total) {
    suggestionListEl.innerHTML = `
      <p class="empty-info">
        目前無 AI 建議。<br>
        稍後會產生初始建議並顯示在這裡。
      </p>
    `;
    if (paginationEl) paginationEl.innerHTML = "";
    return;
  }

  let html = "";

  pageData.forEach((item, indexInPage) => {
    const index = (currentPage - 1) * PAGE_SIZE + indexInPage + 1;

    const strat  = (item.strategy_points || []).map(s => `<li>${s}</li>`).join("");
    const outc   = (item.outcome_points  || []).map(s => `<li>${s}</li>`).join("");
    

    html += `
      <article class="suggestion-item">
        <header class="suggestion-header">
          <span class="suggestion-index">第 ${index} 筆行銷建議</span>
          ${item.tag ? `<span class="suggestion-tag">${item.tag}</span>` : ""}
          ${item.executed ? `<span class="executed-label">已執行</span>` : ""}
        </header>

        <div class="suggestion-body">
          <div class="suggestion-col">
            <h4>建議優惠券：</h4>
            <ul>${strat || "<li>無推薦優惠券</li>"}</ul>
          </div>

          <div class="suggestion-col">
            <h4>預期成果：</h4>
            <ul>${outc}</ul>
          </div>
        </div>

        <footer class="suggestion-footer">
          <button class="btn execute-btn" data-id="${item.id}">執行此建議</button>
        </footer>
      </article>
    `;
  });

  suggestionListEl.innerHTML = html;
  renderPagination(totalPages);
  bindExecuteButtons();
}



// =========================================================
// 渲染分頁
// =========================================================
function renderPagination(totalPages) {
  if (!paginationEl) return;

  if (totalPages <= 1) {
    paginationEl.innerHTML = "";
    return;
  }

  let html = "";

  html += `
    <button class="page-btn" data-page="first" ${currentPage===1?"disabled":""}>第一頁</button>
    <button class="page-btn" data-page="prev"  ${currentPage===1?"disabled":""}>上一頁</button>
  `;

  for (let p = 1; p <= totalPages; p++) {
    html += `
      <button class="page-btn ${p===currentPage?"is-active":""}" data-page="${p}">${p}</button>
    `;
  }

  html += `
    <button class="page-btn" data-page="next" ${currentPage===totalPages?"disabled":""}>下一頁</button>
    <button class="page-btn" data-page="last" ${currentPage===totalPages?"disabled":""}>最後一頁</button>
  `;

  paginationEl.innerHTML = html;

  const btns = paginationEl.querySelectorAll(".page-btn");
  btns.forEach(btn => {
    btn.addEventListener("click", () => {
      const page = btn.dataset.page;

      if (page === "first")      currentPage = 1;
      else if (page === "prev")  currentPage = Math.max(1, currentPage - 1);
      else if (page === "next")  currentPage = Math.min(totalPages, currentPage + 1);
      else if (page === "last")  currentPage = totalPages;
      else                       currentPage = parseInt(page, 10);

      renderSuggestionList();
    });
  });
}


// =========================================================
// 綁定執行按鈕
// =========================================================
function bindExecuteButtons() {
  const btns = document.querySelectorAll(".execute-btn");
  btns.forEach(btn => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      executeSuggestion(id);
    });
  });
}



//執行建議->寫入ai_suggection+ campaign

async function executeSuggestion(id) {
  const target = suggestions.find(s => String(s.id) === String(id));
  if (!target) return;

  const ok = window.confirm("確定接受此建議？若同意將發送對應優惠券方案！");
  if (!ok) return;

  try {
    await fetch(API_EXECUTE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        categoryID: CATEGORY_ID,
        guideline: (target.strategy_points || []).join("\n"),//guideline 整段建議優惠券文字->給後端
        outcome:   (target.outcome_points  || []).join("\n"),//outcome 整段預期成果
        // TODO：這裡可以改成後端 session 的 user_id
        userID: 1
      })
    });

    target.executed = true;
    renderSuggestionList();
    alert("已寫入資料庫");

  } catch (err) {
    console.error("執行建議失敗", err);
  }
}



// =========================================================
// 右側聊天 + 自動插入建議
// =========================================================
function appendMessage(role, text, loading=false) {
  const msg = document.createElement("div");
  msg.className = `msg ${role}`;

  const bubble = document.createElement("div");
  bubble.className = `bubble ${loading?"loading":""}`;
  bubble.textContent = text;

  msg.appendChild(bubble);
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
  return bubble;
}

async function sendChatToBackend(text) {
  const resp = await fetch(API_CHAT, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({
      message:   text,
      categoryID: CATEGORY_ID,
      userID:    1
    })
  });

  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }
  const data = await resp.json();
  return data;
}

async function ask(question) {
  appendMessage("user", question);
  const loadingBubble = appendMessage("ai", "思考中…", true);

  try {
    const data = await sendChatToBackend(question);

    loadingBubble.textContent = data.reply;
    loadingBubble.classList.remove("loading");

    // 若回覆有建議 → 自動加入左側欄
    if (data.newSuggestion) {
      suggestions.unshift(data.newSuggestion);
      currentPage = 1;
      renderSuggestionList();
    }
  } catch (err) {
    loadingBubble.textContent = `錯誤：${err}`;
    loadingBubble.classList.remove("loading");
  }
}

if (askBtn) {
  askBtn.addEventListener("click", () => {
    const text = qEl.value.trim();
    if (!text) return;
    ask(text);
    qEl.value = "";
  });
}

if (clearBtn) {
  clearBtn.addEventListener("click", () => {
    chatBox.innerHTML = "";
  });
}


// =========================================================
// 初始化：先畫標題，再載入模型建議
// =========================================================
renderTitle();
loadInitialSuggestion();
renderSuggestionList();
