
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
    if (memberType === '高價值顧客') {
      memberTypeDisplay.classList.add('is-high');
    } else if (memberType === '高風險顧客') {
      memberTypeDisplay.classList.add('is-risk');
    } else if (memberType === '新進顧客') {
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

// 模擬從後端抓資料
async function fetchDashboardData() {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        repurchaseRate: 0.32,
        churnRate: 0.08,
        vipRatio: 0.29,
        totalCustomers: 8920,
        customerType: "高價值顧客",
        segments: [40, 25, 20, 15],
        forecast: [50, 80, 120, 170],
      });
    }, 1000);
  });
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
let lineChartRef = null;

function renderForecastChart(mode, data) {
  const ctx = document.getElementById("lineChart");
  if (!ctx) return;

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
      scales: { y: { beginAtZero: true } }
    }
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

  // 顧客分群比例圖（圓餅圖）
  const pieCtx = document.getElementById("pieChart");
  if (pieCtx) {
    new Chart(pieCtx, {
      type: "pie",
      data: {
        labels: ["高價值顧客", "一般顧客", "低價值顧客", "新顧客"],
        datasets: [{
          data: data.segments,
          backgroundColor: ["#33b7e1", "#7cd1f9", "#bce4ff", "#e0f7ff"],
        }]
      }
    });
  }

  // 折線圖預設載入「季」
  renderForecastChart("quarter", data);

  // 綁定季 / 年切換
  const selector = document.getElementById("forecastSelector");
  if (selector) {
    selector.addEventListener("change", function () {
      renderForecastChart(this.value, data);
    });
  }
}

/* ================================
   點擊卡片：置中放大 / 再點縮回
================================ */
function enableClickZoom(boxId) {
  const box = document.getElementById(boxId);
  if (!box) return;

  box.addEventListener("click", function (e) {
    // 避免冒泡到 document 的關閉事件
    e.stopPropagation();
    const isZoomed = box.classList.toggle("is-zoomed");

    // 如果放大中，就鎖住 body 捲動（可選）
    if (isZoomed) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
  });
}

// 點擊畫面其他地方，關掉所有放大的卡片
document.addEventListener("click", () => {
  const zoomedCards = document.querySelectorAll(".chart-zoom.is-zoomed");
  if (zoomedCards.length === 0) return;

  zoomedCards.forEach(card => card.classList.remove("is-zoomed"));
  document.body.style.overflow = "";
});

// 啟用在三個卡片上
enableClickZoom("pieBox");
enableClickZoom("lineBox");
enableClickZoom("memberBox");

// 頁面載入完成後，先跑一次 checkMemberId()，顯示「請輸入會員編號...」
document.addEventListener('DOMContentLoaded', () => {
  checkMemberId();
});


// 🚀 啟動儀表板
initDashboard();
