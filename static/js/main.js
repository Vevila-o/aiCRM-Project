// =========================================================
// 首頁功能邏輯 - 會員查詢
// =========================================================

/**
 * 根據輸入的會員編號檢查並顯示會員類型 (綁定到 input 的 oninput 事件)
 */
// 🔄 改為從後端 API 查詢會員
async function checkMemberId() {
  const memberIdInput     = document.getElementById('memberInput');
  const memberTypeDisplay = document.getElementById('memberTypeDisplay');
  const memberTypeSpan    = document.getElementById('customerType');
  const learnMoreBtn      = document.getElementById('detailBtn');

  const inputMemberId = memberIdInput.value.trim();

  // 未輸入：回到預設提示
  if (!inputMemberId) {
    memberTypeDisplay.classList.remove('is-high','is-risk','is-new','is-error');
    memberTypeDisplay.classList.add('is-empty');
    memberTypeSpan.textContent = '請輸入會員編號...';
    learnMoreBtn.disabled = true;
    sessionStorage.removeItem('currentMemberId');
    sessionStorage.removeItem('currentMemberData');
    return;
  }

  try {
    const resp = await fetch(`/api/member/?id=${encodeURIComponent(inputMemberId)}`);
    if (!resp.ok) {
      memberTypeDisplay.classList.remove('is-high','is-risk','is-new','is-empty');
      memberTypeDisplay.classList.add('is-error');
      memberTypeSpan.textContent = '查詢發生錯誤';
      learnMoreBtn.disabled = true;
      return;
    }

    const data = await resp.json();

    if (!data.found) {
      // ❌ 資料庫沒有這個會員
      memberTypeDisplay.classList.remove('is-high','is-risk','is-new','is-empty');
      memberTypeDisplay.classList.add('is-error');
      memberTypeSpan.textContent = '查無此會員資料';
      learnMoreBtn.disabled = true;
      sessionStorage.removeItem('currentMemberId');
      sessionStorage.removeItem('currentMemberData');
      return;
    }

    // ✅ 有找到會員
    const member = data.customer;          // 後端回傳的會員物件（含 memberType）
    const memberType = member.memberType;  // 例如：高價值顧客 / 高風險顧客 / 新進顧客 / 一般顧客

    memberTypeSpan.textContent = memberType;

    // 更新顏色 class
    memberTypeDisplay.classList.remove('is-empty','is-error','is-high','is-risk','is-new');
    if (memberType === '忠誠顧客' || memberType === '潛在高價值顧客' || memberType === '普通顧客') {
      memberTypeDisplay.classList.add('is-high');
    } else if (memberType === '沉睡顧客'|| memberType === '潛在流失顧客') {
      memberTypeDisplay.classList.add('is-risk');
    } else if (memberType === '新客/低價值顧客') {
      memberTypeDisplay.classList.add('is-new');
    }

    // 「查看更多」啟用
    learnMoreBtn.disabled = false;

    // 存到 sessionStorage，customer.html 會用到
    sessionStorage.setItem('currentMemberId', inputMemberId);
    sessionStorage.setItem('currentMemberData', JSON.stringify(member));

  } catch (err) {
    console.error(err);
    memberTypeDisplay.classList.remove('is-high','is-risk','is-new','is-empty');
    memberTypeDisplay.classList.add('is-error');
    memberTypeSpan.textContent = '連線失敗，請稍後再試';
    learnMoreBtn.disabled = true;
  }
}

function navigateToCustomerDetail() {
  const id = sessionStorage.getItem('currentMemberId');
  if (id) {
    // Django 版：用 /customer/?id=xxx
    window.location.href = `/customer/?id=${encodeURIComponent(id)}`;
  } else {
    alert('導向失敗：請先輸入有效的會員編號。');
  }
}



// =========================================================
// Dashboard 模擬資料 & 初始化
// =========================================================

// 🔹 新增：圖表相關的全域變數（只用在圖表 & 放大，不動其他邏輯）
let pieChartRef = null;      // 圓餅圖實例
let lineChartRef = null;     // 折線圖實例
let zoomedChart  = null;     // 放大視窗中的圖表
let dashboardData = null;    // 儀表板資料（折線圖季/年用）
let lineMode = "quarter";    // 目前折線圖模式

// 從後端抓資料
// 從後端注入的全域變數取得儀表板資料
async function fetchDashboardData() {
  if (window.dashboardBootstrapData && typeof window.dashboardBootstrapData === "object") {
    return window.dashboardBootstrapData;
  }

  // 保險：沒有資料時避免程式爆掉
  return {
    repurchaseRate: 0,
    churnRate: 0,
    vipRatio: 0,
    totalCustomers: 0,
    segments: [0, 0, 0, 0, 0, 0],
    forecast: [0, 0, 0, 0],
  };
}



// --- 首頁AI 行銷建議區塊：資料＆互動 ---
const SEG_CONTENT = {
  high: {
    title: '高價值顧客 — 建議',
    bullets: [
      'VIP 維繫：會員升級、專屬活動、生日禮',
      '提高客單：組合搭配 / 加價購（Cross-sell / Upsell）',
      '情感連結：感謝信 + 回饋券'
    ],
    label: '高價值顧客'
  },
  risk: {
    title: '高風險顧客 — 建議',
    bullets: [
      '挽回誘因：回流折扣或免運',
      '找出原因：簡短問卷（產品/價格/服務）',
      '再互動：再行銷廣告 + 簡訊提醒'
    ],
    label: '高風險顧客'
  },
  new: {
    title: '新進顧客 — 建議',
    bullets: [
      '新手引導：開箱指南 / 使用教學',
      '首次回購：限定 72 小時優惠',
      '信任建立：社群口碑與使用者故事'
    ],
    label: '新進顧客'
  }
};

const panel      = document.getElementById('segPanel');
const tabs       = Array.from(document.querySelectorAll('.seg-tab'));
const seeMoreBtn = document.getElementById('seeMoreBtn');

let currentSeg = 'high'; // 預設

function renderSeg(segKey) {
  const data = SEG_CONTENT[segKey];
  if (!data || !panel) return;

  // 建立內容 DOM
  const wrapper = document.createElement('div');
  wrapper.className = 'fade';
  wrapper.innerHTML = `
    <h4 class="seg-title">${data.title}</h4>
    <ul class="seg-list">
      ${data.bullets.map(b => `<li>${b}</li>`).join('')}
    </ul>
  `;

  // 先清空舊內容，再掛上新內容並做淡入動畫
  panel.innerHTML = '';
  panel.appendChild(wrapper);

  // 下一個 frame 再加 show，觸發 transition
  requestAnimationFrame(() => wrapper.classList.add('show'));

  // 更新「查看更多」按鈕目標
  if (seeMoreBtn) {
    seeMoreBtn.onclick = () => {
      const url = `ai-suggestion.html?seg=${encodeURIComponent(segKey)}`;
      window.location.href = url;
    };
  }
}

// 標籤事件
tabs.forEach(btn => {
  btn.addEventListener('click', () => {
    const segKey = btn.dataset.seg;
    if (segKey === currentSeg) return;

    // active 狀態
    tabs.forEach(b => {
      const isActive = b === btn;
      b.classList.toggle('is-active', isActive);
      b.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    currentSeg = segKey;
    renderSeg(segKey);
  });
});

// 初始載入 AI 區塊
renderSeg(currentSeg);

/* ===========================
   折線圖 季 / 年切換
=========================== */

function renderForecastChart(mode, data) {
  const ctx = document.getElementById("lineChart");
  if (!ctx) return;

  // ✅ 記住目前模式與資料，之後放大 / 切換會用到
  lineMode = mode;
  dashboardData = data;

  if (lineChartRef) lineChartRef.destroy();

  const labels = mode === "quarter"
    ? ["Q1", "Q2", "Q3", "Q4"]
    : ["2021", "2022", "2023", "2024"];

  const values = mode === "quarter"
    ? data.forecast
    : [200, 260, 320, 410]; // 可改成後端資料

  lineChartRef = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: mode === "quarter" ? "季預測" : "年預測",
        data: values,
        borderColor: "#33b7e1",
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      scales: { y: { beginAtZero: true } }
    }
  });
}

// 統一切換季 / 年（卡片 + 放大視窗一起更新）
function setLineMode(mode) {
  if (!dashboardData) return;

  const mainSelector  = document.getElementById("forecastSelector");
  const modalSelector = document.getElementById("chartModalSelector");

  if (mainSelector)  mainSelector.value  = mode;
  if (modalSelector) modalSelector.value = mode;

  renderForecastChart(mode, dashboardData);

  if (zoomedChart && zoomedChart.config.type === "line" && lineChartRef) {
    zoomedChart.data    = lineChartRef.data;
    zoomedChart.options = {
      ...zoomedChart.options,
      ...lineChartRef.options
    };
    zoomedChart.update();
  }
}

// 綁定兩個下拉（卡片上的 + 彈窗裡的）
function setupLineSelectors() {
  const mainSelector  = document.getElementById("forecastSelector");
  const modalSelector = document.getElementById("chartModalSelector");

  if (mainSelector) {
    mainSelector.addEventListener("change", function () {
      setLineMode(this.value);
    });
  }

  if (modalSelector) {
    modalSelector.addEventListener("change", function () {
      setLineMode(this.value);
    });
  }
}

/* ========================
   圖表彈窗共用邏輯
======================== */

/**
 * 開啟彈窗，根據目前的 chart 實例重畫一份放大版
 */
function openChartModal(chartInstance, title) {
  const chartModal    = document.getElementById("chartModal");
  const zoomCanvas    = document.getElementById("zoomCanvas");
  const titleEl       = document.getElementById("chartModalTitle");
  const modalSelector = document.getElementById("chartModalSelector");

  if (!chartModal || !zoomCanvas || !chartInstance) return;

  // 設定彈窗標題文字（顧客分群比例圖 / 顧客消費預測...）
  if (titleEl) {
    titleEl.textContent = title || "";
  }

  // 折線圖放大時：顯示季/年下拉；圓餅圖：隱藏
  if (modalSelector) {
    if (chartInstance.config.type === "line") {
      modalSelector.classList.remove("hidden");
      modalSelector.disabled = false;
      modalSelector.value = lineMode;
    } else {
      modalSelector.classList.add("hidden");
      modalSelector.disabled = true;
    }
  }

  chartModal.classList.remove("hidden");
  document.body.style.overflow = "hidden";

  // 清掉舊的放大圖
  if (zoomedChart) {
    zoomedChart.destroy();
    zoomedChart = null;
  }

  const ctx = zoomCanvas.getContext("2d");

  // 維持原本圖表比例
  const baseOptions = chartInstance.config.options || {};
  const popupOptions = {
    ...baseOptions,
    responsive: true,
    maintainAspectRatio: true
  };

  zoomedChart = new Chart(ctx, {
    type: chartInstance.config.type,
    data: chartInstance.config.data,
    options: popupOptions
  });
}


/**
 * 關閉彈窗
 */
function closeChartModal() {
  const chartModal = document.getElementById("chartModal");
  if (!chartModal) return;

  chartModal.classList.add("hidden");
  document.body.style.overflow = "";

  if (zoomedChart) {
    zoomedChart.destroy();
    zoomedChart = null;
  }
}

/**
 * 綁定彈窗關閉按鈕、背景點擊關閉
 */
function setupModalEvents() {
  const chartModal = document.getElementById("chartModal");
  if (!chartModal) return;

  const chartCloseBtn = chartModal.querySelector(".chart-close-btn");

  // 按 ✕ 關閉
  if (chartCloseBtn) {
    chartCloseBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      closeChartModal();
    });
  }

  // 點黑色背景關閉（如果你不想要，可以把這段註解掉）
  chartModal.addEventListener("click", (e) => {
    if (e.target === chartModal) {
      closeChartModal();
    }
  });
}

/**
 * 給卡片用：點某個卡片 → 取得圖表實例 → 開彈窗
 * getChartInstance：一個回傳對應 Chart 實例的 function
 */
function enableChartPopup(boxId, getChartInstance) {
  const box = document.getElementById(boxId);
  if (!box) return;

  box.style.cursor = "pointer";
  
  box.addEventListener("click", (e) => {
    e.stopPropagation();

    const chartInstance = getChartInstance && getChartInstance();
    if (!chartInstance) {
      console.warn(`Chart instance not found for ${boxId}`);
      return;
    }

    // 從卡片裡抓標題文字（顧客分群比例圖 / 顧客消費預測）
    const titleNode = box.querySelector("h3");
    const titleText = titleNode ? titleNode.textContent.trim() : "";

    console.log(`Opening modal for: ${titleText}`);
    openChartModal(chartInstance, titleText);
  });
}


/* ===========================
   Dashboard 初始化（合併版本）
=========================== */


async function initDashboard() {
  const data = await fetchDashboardData();

  // 更新數字
  const repurchaseDom = document.getElementById("repurchaseRate");
  const churnDom      = document.getElementById("churnRate");
  const vipDom        = document.getElementById("vipRatio");
  const totalDom      = document.getElementById("totalCustomers");

  if (repurchaseDom) repurchaseDom.textContent = `${(data.repurchaseRate * 100).toFixed(0)}%`;
  if (churnDom)      churnDom.textContent      = `${(data.churnRate * 100).toFixed(0)}%`;
  if (vipDom)        vipDom.textContent        = `${(data.vipRatio * 100).toFixed(0)}%`;
  if (totalDom)      totalDom.textContent      = `${data.totalCustomers} 人`;

  // 顧客分群比例圖（圓餅圖）── 改成有 ref，方便放大用
  const pieCtx = document.getElementById("pieChart");
  if (pieCtx) {
    pieChartRef = new Chart(pieCtx, {
      type: "pie",
      data: {
        labels: ["忠誠客戶","潛在高價值顧客", "普通顧客", "沉睡顧客", "潛在流失顧客", "低價值顧客","新顧客"],
        datasets: [{
          data: data.segments,
          backgroundColor: ["#33b7e1", "#7cd1f9", "#bce4ff", "#e0f7ff", "#ff9999", "#ffcccc","#dfd54eff"],
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        aspectRatio: 2,   // 讓圖在 320x360 的卡片裡完整顯示
        layout: {
          padding: 10
        },
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              boxWidth: 12,
              boxHeight: 12
            }
          }
        }
      }
    });

    // 點圓餅圖卡片 → 彈出視窗顯示放大版圓餅圖
    enableChartPopup("pieBox", () => pieChartRef);
  }

  // 折線圖預設載入「季」
  renderForecastChart("quarter", data);

  // 點折線圖卡片 → 彈出視窗顯示放大版折線圖
  enableChartPopup("lineBox", () => lineChartRef);

  // 初始化卡片上的季 / 年下拉（只設定預設值，事件綁在 setupLineSelectors 裡）
  const selector = document.getElementById("forecastSelector");
  if (selector) {
    selector.value = lineMode;
  }
}

/* ===========================
   DOM 載入完成後再初始化
=========================== */

document.addEventListener('DOMContentLoaded', () => {
  // 一進頁面先顯示「請輸入會員編號...」
  checkMemberId();

  // 綁定彈窗關閉事件（叉叉/背景）
  setupModalEvents();

  // 綁定季 / 年切換（卡片 + 放大視窗）
  setupLineSelectors();

  // 🚀 啟動儀表板（畫圖 & 綁定卡片點擊）
  initDashboard();
});
