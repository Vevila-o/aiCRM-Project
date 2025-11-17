// 活動資料
const ACTIVITY_DATA = {
    spring: {
      title: "超市 × 門市聯名「春季集點換好禮」",
      period: "2025/03/01 - 2025/03/31",
      metrics: {
        newMain: "276 位",
        newSub: "新客成長 +48％",
        vipMain: "參與率 62％",
        vipSub: "平均消費提升 22％",
        effMain: "營收 +31％",
        effSub: "集點換禮帶動生活用品成長"
      },
      description:
        "春季集點活動主打「買越多、回饋越多」，鎖定家庭客與固定來店顧客。顧客在超市每消費滿一定金額即可累積點數，集滿可至門市兌換指定商品或折價券。周三與周六設為雙倍點數日，強化『指定時間來店』的誘因，並在收銀區明顯位置放上集點說明，讓首次來店的顧客也能快速理解參加方式。活動後期再透過簡訊與 LINE 通知提醒點數即將到期，進一步刺激第二次與第三次回購。",
      summary: [
        "活動期間新增會員 276 位，新客成長 +48％，其中家庭客佔比將近六成。",
        "高價值顧客參與率 62％，於雙倍點數日的平均消費金額較平日多出 22％。",
        "集點兌換商品以清潔用品、衛生紙與廚房小物最受歡迎，有效帶動生活用品區銷售。",
        "整體營收較活動前月成長 31％，其中平日晚間與週末午後為來客高峰。"
      ]
    },
    summer: {
      title: "夏季冰品 & 飲料買一送一週",
      period: "2025/07/15 - 2025/07/21",
      metrics: {
        newMain: "392 位",
        newSub: "首次購買冰品的新客 +56％",
        vipMain: "VIP 消費 +38％",
        vipSub: "冰品 + 飲料組合最受歡迎",
        effMain: "營收 +45％",
        effSub: "冰品類銷量成長 110％"
      },
      description:
        "夏季冰品週鎖定學生與上班族客群，以『指定冰品、飲料買一送一』作為主打話題。搭配門市滿額折扣，鼓勵顧客順手添購餅乾、零食與即食品，加深「一站式涼夏補給」的印象。門市現場設計了小型拍照區，顧客只要打卡上傳即可獲得小零食，加強社群曝光與口碑擴散。活動期間中午與下班時段人流明顯拉高，部分門市甚至需要加派人力補貨與維持排隊動線。",
      summary: [
        "活動期間，共有 392 位顧客首次購買冰品，新客成長率達 56％，其中學生族群占比最高。",
        "VIP 顧客的平均週消費比平時多 38％，以冰品搭配家庭號飲料的組合最受歡迎。",
        "冰品類銷量翻倍成長（+110％），也帶動餅乾與零食區銷量增加約 28％。",
        "整體營收相較於一般夏季週平均成長 45％，為當季最成功的檔期活動之一。"
      ]
    },
    yearend: {
      title: "年終超市「滿額抽家電」大促",
      period: "2025/12/20 - 2025/12/31",
      metrics: {
        newMain: "182 位",
        newSub: "新增會員 +29％",
        vipMain: "VIP 參與率 78％",
        vipSub: "高單價禮盒銷售明顯成長",
        effMain: "營收 +52％",
        effSub: "帶動年節備貨與高單價商品"
      },
      description:
        "年終滿額抽活動以小家電、超市購物金與實用生活用品作為獎項，鼓勵顧客在單一檔期完成年節與日常備貨。消費滿額即可獲得抽獎券，VIP 顧客享有加倍抽獎機會，將原本只買日用品的顧客轉化為高單價禮盒與家庭清潔組的主要客群。門市於收銀台附近設置獎品展示區，並在結帳時主動提醒抽獎資格，提升參與率與期待感。抽獎結果於社群及門市公告欄同步公布，增加透明度與信任感。",
      summary: [
        "活動期間新增 182 位會員，會員數成長 29％，其中不少為第一次參與抽獎的新客。",
        "VIP 顧客參與率達 78％，平均購買金額提升 44％，高單價禮盒與家用品組合銷售明顯增加。",
        "年節相關商品（禮盒、飲料箱、清潔用品）銷量較前一檔期成長約 36％。",
        "活動檔期整體營收較前一檔期成長 52％，被內部評估為全年投資報酬率最高的行銷活動。"
      ]
    }
  };
  
  // DOM 元素
  const selectEl = document.getElementById("activitySelect");
  const titleTopEl = document.getElementById("activityTitleTop");
  const titleBottomEl = document.getElementById("activityTitleBottom");
  
  const metricNewMainEl = document.getElementById("metricNewMain");
  const metricNewSubEl = document.getElementById("metricNewSub");
  const metricVipMainEl = document.getElementById("metricVipMain");
  const metricVipSubEl = document.getElementById("metricVipSub");
  const metricEffMainEl = document.getElementById("metricEffMain");
  const metricEffSubEl = document.getElementById("metricEffSub");
  
  const periodEl = document.getElementById("detailPeriod");
  const descEl = document.getElementById("detailDescription");
  const summaryListEl = document.getElementById("detailSummary");
  
  // 渲染函式
  function renderActivity(key) {
    const data = ACTIVITY_DATA[key] || ACTIVITY_DATA.spring;
  
    titleTopEl.textContent = data.title;
    titleBottomEl.textContent = data.title;
  
    metricNewMainEl.textContent = data.metrics.newMain;
    metricNewSubEl.textContent = data.metrics.newSub;
    metricVipMainEl.textContent = data.metrics.vipMain;
    metricVipSubEl.textContent = data.metrics.vipSub;
    metricEffMainEl.textContent = data.metrics.effMain;
    metricEffSubEl.textContent = data.metrics.effSub;
  
    periodEl.textContent = data.period;
    descEl.textContent = data.description;
  
    // 重繪摘要列表
    summaryListEl.innerHTML = "";
    data.summary.forEach(item => {
      const li = document.createElement("li");
      li.textContent = item;
      summaryListEl.appendChild(li);
    });
  }
  
  // 初始：預設 spring
  renderActivity("spring");
  
  // 下拉切換活動
  selectEl.addEventListener("change", e => {
    renderActivity(e.target.value);
  });
  