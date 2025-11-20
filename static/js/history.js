// 顧客分群對應的優惠券（先做 忠誠顧客 & 潛在高價值顧客）
// 之後後端可以把這整個物件換成 API 回傳資料
const SEGMENT_COUPONS = {
  loyal: [
    {
      title: "全館 9 折券",
      description: "感謝您長期支持，回饋專屬折扣，部分特價品除外。",
      expire: "有效期限：2025/12/31",
      code: "LOYAL-9OFF"
    },
    {
      title: "滿 500 折 80 元",
      description: "單筆消費滿 500 元即可折抵 80 元，可與點數並用。",
      expire: "有效期限：2025/12/20",
      code: "LOYAL-80"
    },
    {
      title: "生日禮：免費小點心兌換券",
      description: "生日當月可兌換指定小點心乙份，限用一次。",
      expire: "有效期限：2025/11/30",
      code: "BDAY-GIFT"
    },
    {
      title: "任選兩件 85 折",
      description: "限生活用品與飲料品項，折扣以結帳系統顯示為主。",
      expire: "有效期限：2025/12/15",
      code: "LOYAL-ITEM85"
    },
    {
      title: "會員專屬 100 元購物金",
      description: "單筆滿 450 元即可折抵，部分酒類與菸品不適用。",
      expire: "有效期限：2025/12/25",
      code: "LOYAL-100"
    }
  ],

  // 潛在高價值顧客
  potential_vip: [
    {
      title: "滿 300 折 50 元",
      description: "鼓勵您多嘗試不同品類，一次買齊更划算。",
      expire: "有效期限：2025/12/30",
      code: "PVIP-50"
    },
    {
      title: "指定零食第二件半價",
      description: "精選零食、餅乾、巧克力等商品適用。",
      expire: "有效期限：2025/12/25",
      code: "PVIP-SNACK50"
    },
    {
      title: "冰品 + 飲料組合 88 折",
      description: "任選一杯飲料搭配一款冰品享 88 折優惠。",
      expire: "有效期限：2025/12/28",
      code: "PVIP-ICE88"
    },
    {
      title: "滿 600 贈 50 元電子抵用券",
      description: "抵用券將於隔日入帳，可於下次消費使用。",
      expire: "有效期限：2025/12/31",
      code: "PVIP-EC50"
    },
    {
      title: "週末雙倍點數券",
      description: "限週五至週日使用，結帳時請主動出示此券。",
      expire: "有效期限：2025/12/22",
      code: "PVIP-2XPOINT"
    }
  ],

  // 其餘分群目前暫無優惠券，後端之後可填入陣列
  regular: [],
  low_value: [],
  sleeping: [],
  churn_risk: [],
  new: []
};

// DOM
const selectEl = document.getElementById("segmentSelect");
const titleEl = document.getElementById("segmentTitleTop");
const couponListEl = document.getElementById("couponList");

// 如果這頁沒有相關 DOM，就不繼續執行（安全防呆）
if (selectEl && titleEl && couponListEl) {

  // 渲染優惠券列表
  function renderCoupons(key) {
    const list = SEGMENT_COUPONS[key] || [];

    // 更新上方膠囊標題（用 option 的文字）
    const selectedOption = selectEl.options[selectEl.selectedIndex];
    titleEl.textContent = selectedOption ? selectedOption.textContent : "顧客分群";

    // 清空列表
    couponListEl.innerHTML = "";

    // 沒有優惠券時顯示提示文字
    if (list.length === 0) {
      const empty = document.createElement("p");
      empty.className = "coupon-empty";
      empty.textContent = "暫時無發放優惠券";
      couponListEl.appendChild(empty);
      return;
    }

    // 有優惠券就產生卡片
    list.forEach(coupon => {
      const card = document.createElement("div");
      card.className = "coupon-card";

      card.innerHTML = `
        <h3 class="coupon-title">${coupon.title}</h3>
        <p class="coupon-desc">${coupon.description}</p>
        <p class="coupon-meta">${coupon.expire}｜代碼：${coupon.code}</p>
      `;

      couponListEl.appendChild(card);
    });
  }

  // 初始載入：用 select 的預設值，沒有就用 loyal
  const defaultKey = selectEl.value || "loyal";
  renderCoupons(defaultKey);

  // 下拉選單切換顧客分群
  selectEl.addEventListener("change", e => {
    renderCoupons(e.target.value);
  });
}
