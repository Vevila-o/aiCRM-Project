// 讀取 URL 的 ?seg 參數，決定顯示哪個客群
const params = new URLSearchParams(window.location.search);
const initialSeg = params.get("seg") || "vip"; // 預設高價值顧客

// 根據參數預設下拉選單的值
document.addEventListener("DOMContentLoaded", () => {
  const select = document.getElementById("segmentSelect");
  if (initialSeg === "high" || initialSeg === "vip") select.value = "vip";
  if (initialSeg === "risk") select.value = "risk";
  if (initialSeg === "new") select.value = "new";

  // 觸發一次顧客內容載入
  loadSegmentContent(select.value);
});

// 監聽下拉變化
document.getElementById("segmentSelect").addEventListener("change", e => {
  loadSegmentContent(e.target.value);
});

// 範例載入內容（你原本的邏輯可以放這裡）
function loadSegmentContent(type) {
  const content = document.getElementById("content");
  if (type === "vip") {
    content.innerHTML = `<h4>高價值顧客建議</h4><p>建議維繫忠誠、推出 VIP 專屬優惠。</p>`;
  } else if (type === "risk") {
    content.innerHTML = `<h4>高風險顧客建議</h4><p>建議發送關懷訊息、提供回購誘因。</p>`;
  } else if (type === "new") {
    content.innerHTML = `<h4>新進顧客建議</h4><p>建議提供首購優惠或歡迎簡訊。</p>`;
  }
}

const BACKEND_ENDPOINT = "/api/chat";
const LS_HISTORY_KEY   = "AI_SUGGESTION_HISTORY";

const DATA = {
  vip:{
    title:"高價值顧客",
    features:["RFM 平均分數：5-5-5","平均消費金額：NT$ 8,000 / 月","最近購買日：30 天內"],
    plans:[
      "維繫忠誠：推出 VIP 專屬優惠或會員升級制度",
      "提升單價：搭配推薦產品組合（Cross-selling）",
      "情感連結：寄送感謝信或專屬生日優惠"
    ],
    outcomes:["回購率提升 10%","平均客單價提升 8%"],
    channels:"Email、LINE 官方帳號、App 推播"
  },
  risk:{
    title:"高風險顧客",
    features:["RFM 平均分數：2-1-1","平均消費金額：NT$ 800 / 月","最近購買日：超過 90 天"],
    plans:[
      "挽回關係：提供回流專屬 1 次性折扣／免運券",
      "降低流失：發送關懷問卷蒐集流失原因並回饋點數",
      "重新喚起：推薦低門檻入手商品或組合"
    ],
    outcomes:["回流率提升 6%","退訂率下降 3%"],
    channels:"SNS 再行銷、EDM、簡訊"
  },
  new:{
    title:"新進顧客",
    features:["RFM 平均分數：3-4-1","平均消費金額：NT$ 1,500 / 月","最近購買日：7 天內首次成交"],
    plans:[
      "加速熟悉：新手引導內容（如何挑選／使用指南）",
      "第二單激勵：7 天內下次消費 9 折券",
      "收集偏好：導入產品喜好標籤以利個人化推薦"
    ],
    outcomes:["次月第二單率提升 12%","名單標籤完整度達 80%"],
    channels:"歡迎信系列、站內訊息、App 新手任務"
  }
};

const contentEl=document.getElementById("content");
const selectEl=document.getElementById("segmentSelect");
const askBtn=document.getElementById("askBtn");
const qEl=document.getElementById("q");
const chatBox=document.getElementById("chatMessages");
const clearBtn=document.getElementById("clearBtn");

function renderSegment(key){
  const d=DATA[key];
  const li=arr=>arr.map(x=>`<li>${x}</li>`).join("");
  contentEl.innerHTML=`
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
renderSegment("vip");
selectEl.addEventListener("change",e=>renderSegment(e.target.value));

function loadHistory(){
  try{
    const raw=localStorage.getItem(LS_HISTORY_KEY);
    const arr=raw?JSON.parse(raw):[];
    return Array.isArray(arr)?arr:[];
  }catch{return []}
}
function saveHistory(his){localStorage.setItem(LS_HISTORY_KEY,JSON.stringify(his));}
function clearHistory(){localStorage.removeItem(LS_HISTORY_KEY);}
let history=loadHistory();

function renderMessages(){
  chatBox.innerHTML="";
  history.forEach(m=>appendMessage(m.role==="assistant"?"ai":"user",m.content));
  chatBox.scrollTop=chatBox.scrollHeight;
}
function appendMessage(role,text,isLoading=false){
  const msg=document.createElement("div");
  msg.className=`msg ${role}`;
  const bubble=document.createElement("div");
  bubble.className="bubble"+(isLoading?" loading":"");
  bubble.textContent=text;
  msg.appendChild(bubble);
  chatBox.appendChild(msg);
  chatBox.scrollTop=chatBox.scrollHeight;
  return bubble;
}
renderMessages();

async function sendToBackend({segment,messages}){
  const resp=await fetch(BACKEND_ENDPOINT,{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({segment,messages})
  });
  if(!resp.ok){
    const t=await resp.text().catch(()=> "");
    throw new Error(`後端錯誤：${resp.status} ${t}`);
  }
  const data=await resp.json();
  if(!data||typeof data.reply!=="string") throw new Error("回傳格式錯誤，需為 { reply: string }");
  return data.reply.trim();
}

async function ask(question){
  const seg=document.getElementById("segmentSelect").value;
  appendMessage("user",question);
  const loading=appendMessage("ai","正在思考中…",true);
  history.push({role:"user",content:question});
  try{
    const reply=await sendToBackend({segment:seg,messages:history});
    loading.textContent=reply;
    loading.classList.remove("loading");
    history.push({role:"assistant",content:reply});
    saveHistory(history);
  }catch(err){
    loading.textContent=`❗發生錯誤：${err.message}`;
    loading.classList.remove("loading");
  }
}
askBtn.addEventListener("click",()=>{
  const q=(qEl.value||"").trim();
  if(!q)return;
  ask(q);
  qEl.value="";
});
clearBtn.addEventListener("click",()=>{
  history=[];
  clearHistory();
  renderMessages();
});
(function(){
  const url=new URL(window.location.href);
  const q=url.searchParams.get("q");
  if(q){
    qEl.value=q;
    ask(q);
    url.searchParams.delete("q");
    window.history.replaceState({}, "", url.pathname);
  }
})();
