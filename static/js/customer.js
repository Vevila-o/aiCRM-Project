// customer.js

// 小工具：從網址抓 ?id=12345
function getMemberIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get("id");
  }
  
  // 小工具：把會員資料填進頁面
  function fillCustomerDetail(member) {
    const memberId   = member.customerID    || member.id   || "";
    const name       = member.customerName  || member.name || "";
    const gender     = member.gender        || "";
    const region     = member.customerRegion || member.region || "";
    const memberType = member.memberType    || "";
    const joinDate   = member.customerJoinDay || member.joinDate || "";
    const totalSpend = member.totalSpending || member.total_spending || "";
  
    document.getElementById("detailMemberId").textContent      = memberId;
    document.getElementById("detailCustomerName").textContent  = name;
    document.getElementById("detailGender").textContent        = gender || "—";
    document.getElementById("detailRegion").textContent        = region || "—";
  
    document.getElementById("detailMemberType").textContent    = memberType || "—";
    document.getElementById("detailJoinDate").textContent      = joinDate   || "—";
    document.getElementById("detailTotalSpending").textContent = totalSpend || "0";
  
    // 以下消費紀錄（你之後可以改成真的資料）
    document.getElementById("detailConsumptionDate").textContent = "尚未提供";
    document.getElementById("detailConsumptionAmount").textContent = "0";
  
    const itemsList = document.getElementById("consumptionItemsList");
    itemsList.innerHTML = "";
    const li = document.createElement("li");
    li.textContent = "目前尚未提供消費項目";
    itemsList.appendChild(li);
  }
  
  document.addEventListener("DOMContentLoaded", async () => {
    let memberData = null;
  
    // 先從 sessionStorage 拿資料
    const stored = sessionStorage.getItem("currentMemberData");
    if (stored) {
      try {
        memberData = JSON.parse(stored);
      } catch (e) {
        console.error("解析 sessionStorage 失敗", e);
      }
    }
  
    // 若 sessionStorage 沒資料，再試 URL 的 id
    if (!memberData) {
      const memberId = getMemberIdFromUrl();
      if (memberId) {
        try {
          const resp = await fetch(`/api/member/?id=${encodeURIComponent(memberId)}`);
          if (resp.ok) {
            const data = await resp.json();
            if (data.found) {
              memberData = data.customer;
            }
          }
        } catch (err) {
          console.error("向後端查詢會員失敗", err);
        }
      }
    }
  
    // ❗若真的沒有會員資料 → 顯示「查無會員」
    if (!memberData) {
      document.getElementById("detailCustomerName").textContent  = "查無會員資料";
      document.getElementById("detailMemberId").textContent      = "—";
      document.getElementById("detailGender").textContent        = "—";
      document.getElementById("detailRegion").textContent        = "—";
      document.getElementById("detailMemberType").textContent    = "—";
      document.getElementById("detailJoinDate").textContent      = "—";
      document.getElementById("detailTotalSpending").textContent = "0";
      return;
    }
  
    // 正常 → 填寫畫面
    fillCustomerDetail(memberData);
  });
  document.addEventListener("DOMContentLoaded", () => {
    const typeSpan = document.querySelector(".highlight-type");

    if (!typeSpan) return;

    const typeText = typeSpan.textContent.trim();

    // 對應不同顧客類型 → 套不同 class
    const typeMap = {
        "高價值顧客": "vip",
        "高風險顧客": "risk",
        "新進顧客": "new",
    };

    const className = typeMap[typeText];
    if (className) {
        typeSpan.classList.add(className);
    }
});


