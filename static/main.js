// index.js 完整程式碼

// 宣告一個空物件，用於儲存從 JSON 檔案載入的會員資料
let MEMBER_DATA = {}; 

// =========================================================
// 資料載入邏輯 (從 members.json 檔案)
// =========================================================

async function loadMemberData() {
    try {
        const response = await fetch('members.json'); 
        if (!response.ok) {
            throw new Error(`無法載入 JSON 檔案: ${response.status} ${response.statusText}`);
        }
        MEMBER_DATA = await response.json(); 
        console.log("會員資料載入成功！");
    } catch (error) {
        console.error('載入會員資料失敗:', error);
        MEMBER_DATA = {}; 
        
        // 在載入失敗時顯示提示
        const initialPrompt = document.getElementById('initialPrompt');
        if (initialPrompt) {
             initialPrompt.textContent = '資料載入失敗，請檢查 members.json';
             initialPrompt.style.color = '#dc3545';
        }
    }
}

document.addEventListener('DOMContentLoaded', loadMemberData);


// =========================================================
// 首頁功能邏輯
// =========================================================

/**
 * 根據輸入的會員編號檢查並顯示會員類型 (綁定到 input 的 oninput 事件)
 */
function checkMemberId() {
    // 1. 取得 DOM 元素
    const memberIdInput = document.getElementById('memberInput'); 
    const memberTypeDisplay = document.getElementById('memberTypeDisplay'); 
    const memberTypeSpan = document.getElementById('memberType'); // 已經改為 #memberType
    const learnMoreBtn = document.getElementById('learnMoreBtn');   // 已經改為 #learnMoreBtn
    const initialPrompt = document.getElementById('initialPrompt');
    
    const inputMemberId = memberIdInput.value.trim();

    // 2. 檢查資料是否已載入
    if (Object.keys(MEMBER_DATA).length === 0) {
        // ... (如果載入失敗，會顯示 loadMemberData 中的錯誤提示)
        return;
    }
    
    // 預設設定
    memberTypeDisplay.classList.add('hidden');
    initialPrompt.classList.remove('hidden'); 
    initialPrompt.textContent = '請輸入會員編號...';
    initialPrompt.style.color = '#6c757d';


    if (inputMemberId.length >= 5) {
        const member = MEMBER_DATA[inputMemberId]; 

        if (member) {
            // 找到會員：隱藏提示，顯示結果卡片
            initialPrompt.classList.add('hidden');
            memberTypeDisplay.classList.remove('hidden'); 
            
            memberTypeSpan.textContent = member.memberType;
            // 根據會員類型設定顏色
            memberTypeSpan.style.color = member.memberType === '高價值顧客' ? '#1a6d36' : '#007bff'; 
            learnMoreBtn.classList.remove('hidden');
            
            // 3. 【關鍵】將找到的會員資料儲存到 sessionStorage
            sessionStorage.setItem('currentMemberId', inputMemberId);
            sessionStorage.setItem('currentMemberData', JSON.stringify(member));
        } else {
            // 查無此會員：顯示提示
            initialPrompt.classList.remove('hidden');
            initialPrompt.textContent = '查無此會員編號。';
            initialPrompt.style.color = '#dc3545';
            
            memberTypeDisplay.classList.add('hidden');
            sessionStorage.removeItem('currentMemberId');
            sessionStorage.removeItem('currentMemberData');
        }
    } else {
        // 輸入不足：顯示原始提示
        memberTypeDisplay.classList.add('hidden');
        sessionStorage.removeItem('currentMemberId');
        sessionStorage.removeItem('currentMemberData');
    }
}

/**
 * 導向到會員詳情頁面 (綁定到按鈕的 onclick 事件)
 */
function navigateToCustomerDetail() {
    // 4. 【關鍵】檢查 sessionStorage 中是否有資料，如果有則執行導向
    if (sessionStorage.getItem('currentMemberId')) {
        window.location.href = 'customer.html';
    } else {
        alert('導向失敗：請先輸入有效的會員編號。');
    }
}



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

async function initDashboard() {
  const data = await fetchDashboardData();

  // 更新數字
  document.getElementById("repurchaseRate").textContent = `${(data.repurchaseRate * 100).toFixed(0)}%`;
  document.getElementById("churnRate").textContent = `${(data.churnRate * 100).toFixed(0)}%`;
  document.getElementById("vipRatio").textContent = `${(data.vipRatio * 100).toFixed(0)}%`;
  document.getElementById("totalCustomers").textContent = `${data.totalCustomers} 人`;
  document.getElementById("customerType").textContent = data.customerType;

  // 顧客分群比例圖
  const pieCtx = document.getElementById("pieChart");
  new Chart(pieCtx, {
    type: "pie",
    data: {
      labels: ["高價值顧客", "一般顧客", "低價值顧客", "新顧客"],
      datasets: [
        {
          data: data.segments,
          backgroundColor: ["#33b7e1", "#7cd1f9", "#bce4ff", "#e0f7ff"],
        },
      ],
    },
  });

  // 顧客消費預測圖
  const lineCtx = document.getElementById("lineChart");
  new Chart(lineCtx, {
    type: "line",
    data: {
      labels: ["第1季", "第2季", "第3季", "第4季"],
      datasets: [
        {
          label: "預測消費金額",
          data: data.forecast,
          borderColor: "#33b7e1",
          tension: 0.3,
          fill: false,
        },
      ],
    },
    options: {
      scales: {
        y: { beginAtZero: true },
      },
    },
  });
}

initDashboard();


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

const panel = document.getElementById('segPanel');
const tabs = Array.from(document.querySelectorAll('.seg-tab'));
const seeMoreBtn = document.getElementById('seeMoreBtn');

let currentSeg = 'high'; // 預設

function renderSeg(segKey) {
  const data = SEG_CONTENT[segKey];
  if (!data) return;

  // 建立內容 DOM
  const wrapper = document.createElement('div');
  wrapper.className = 'fade';
  wrapper.innerHTML = `
    <h4 class="seg-title">${data.title}</h4>
    <ul class="seg-list">
      ${data.bullets.map(b => `<li>● ${b}</li>`).join('')}
    </ul>
  `;

  // 先清空舊內容，再掛上新內容並做淡入動畫
  panel.innerHTML = '';
  panel.appendChild(wrapper);
  // 下一個 frame 再加 show，觸發 transition
  requestAnimationFrame(() => wrapper.classList.add('show'));

  // 更新「查看更多」按鈕目標
  seeMoreBtn.onclick = () => {
    // 帶 query 參數到 ai-suggestion.html
    const url = `ai-suggestion.html?seg=${encodeURIComponent(segKey)}`;
    window.location.href = url;
  };
}

// 標籤事件
tabs.forEach(btn => {
  btn.addEventListener('click', () => {
    const segKey = btn.dataset.seg;
    if (segKey === currentSeg) return;

    // active 狀態
    tabs.forEach(b => {
      b.classList.toggle('is-active', b === btn);
      b.setAttribute('aria-selected', b === btn ? 'true' : 'false');
    });

    currentSeg = segKey;
    renderSeg(segKey);
  });
});

// 初始載入
renderSeg(currentSeg);

