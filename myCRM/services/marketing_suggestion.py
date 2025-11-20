# myCRM/services/marketing_suggestion.py
from __future__ import annotations

from typing import Dict, Any, List, Optional
from statistics import mean

from django.utils import timezone

# 這是你自己的 CatBoost 流失預測服務
from .churn_service import predict_churn


# 7 種價值顧客對應的中文名稱（可依你的 RFM 規則調整）
CATEGORY_LABELS: Dict[int, str] = {
    1: "忠誠客戶",
    2: "潛在高價值顧客",
    3: "普通顧客",
    4: "低價值顧客",
    5: "沉睡顧客",
    6: "潛在流失顧客",
    7: "新顧客",
}


def _window_days_for_period(period: str) -> int:
    """
    月 / 季 對應到 churn_service 需要的 window_days。

    period:
        - "month"   → 30 天
        - "quarter" → 90 天
        其他值則回傳 365（保險用）
    """
    if period == "month":
        return 30
    if period == "quarter":
        return 90
    return 365


def catboost_segment_summary(
    category_id: int,
    period: str,
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """
    以 churn_service.predict_churn() 的結果為基礎，整理出某一個 categoryID 的摘要：

    回傳的 summary 會包含：
        - segment_name: 中文名稱（例如「忠誠客戶」）
        - period: "month" / "quarter"
        - window_days: 對應的視窗天數
        - total_customers: 此分群的顧客數
        - avg_probability: 平均流失機率
        - max_probability / min_probability
        - high_risk_count / medium_risk_count / low_risk_count
        - high_examples: 幾個高風險顧客的小樣本（給 AI 看趨勢用）
        - now_str: 目前日期字串（YYYY-MM-DD）
    """
    window_days = _window_days_for_period(period)

    # 呼叫 CatBoost 預測服務，拿到所有顧客的預測結果
    results: List[Dict[str, Any]] = predict_churn(
        as_of=as_of,
        window_days=window_days,
    )

    # 過濾成只剩下指定 categoryID 的顧客
    seg_rows: List[Dict[str, Any]] = [
        r for r in results
        if int(r.get("categoryID", 0)) == int(category_id)
    ]

    total = len(seg_rows)
    if total == 0:
        # 沒資料也要回傳一個完整的結構，讓前端和 ChatGPT 知道「資料不足」
        return {
            "segment_name": CATEGORY_LABELS.get(category_id, f"顧客類型 {category_id}"),
            "period": period,
            "window_days": window_days,
            "total_customers": 0,
            "avg_probability": None,
            "max_probability": None,
            "min_probability": None,
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 0,
            "high_examples": [],
            "now_str": timezone.localtime(timezone.now()).strftime("%Y-%m-%d"),
        }

    # 把 probability 抽出來計算平均 / 最大 / 最小
    probs = [float(r.get("probability", 0.0)) for r in seg_rows]
    avg_prob = mean(probs)
    max_prob = max(probs)
    min_prob = min(probs)

    # 風險分布
    high_rows = [r for r in seg_rows if r.get("risk_level") == "high"]
    med_rows = [r for r in seg_rows if r.get("risk_level") == "medium"]
    low_rows = [r for r in seg_rows if r.get("risk_level") == "low"]

    # 挑幾個高風險實例給 AI 參考（只給關鍵欄位，避免太長）
    high_examples = [
        {
            "customerid": r.get("customerid"),
            "probability": float(r.get("probability", 0.0)),
            "recency_days": int(r.get("recency_days", 0)),
            "frequency": int(r.get("frequency", 0)),
            "monetary": float(r.get("monetary", 0.0)),
        }
        for r in high_rows[:5]
    ]

    return {
        "segment_name": CATEGORY_LABELS.get(category_id, f"顧客類型 {category_id}"),
        "period": period,
        "window_days": window_days,
        "total_customers": total,
        "avg_probability": avg_prob,
        "max_probability": max_prob,
        "min_probability": min_prob,
        "high_risk_count": len(high_rows),
        "medium_risk_count": len(med_rows),
        "low_risk_count": len(low_rows),
        "high_examples": high_examples,
        "now_str": timezone.localtime(timezone.now()).strftime("%Y-%m-%d"),
    }


def build_system_prompt(summary: Dict[str, Any]) -> str:
    """
    把上面的摘要轉成給 ChatGPT 的 system prompt，
    並且明確要求它用「建議優惠券/ 預期成果」兩段式回應。
    而且以優惠券行銷為主。
    """
    seg = summary.get("segment_name", "")
    period = summary.get("period", "")
    total = summary.get("total_customers", 0)
    avg_p = summary.get("avg_probability", None)
    high_cnt = summary.get("high_risk_count", 0)
    med_cnt = summary.get("medium_risk_count", 0)
    low_cnt = summary.get("low_risk_count", 0)
    now_str = summary.get("now_str", "")

    if avg_p is not None:
        avg_text = f"{avg_p * 100:.1f}%"
    else:
        avg_text = "資料量不足"

    # 高風險實例列表
    high_ex_lines: List[str] = []
    for ex in summary.get("high_examples", []):
        line = (
            f"- 顧客 {ex['customerid']}：流失機率約 {ex['probability'] * 100:.1f}%，"
            f"最近未來店天數 {ex['recency_days']} 天，"
            f"過去消費次數 {ex['frequency']} 次，金額約 {ex['monetary']:.0f} 元"
        )
        high_ex_lines.append(line)

    high_ex_text = "\n".join(high_ex_lines) if high_ex_lines else "（略）"

    return f"""
你是一位實體零售通路的行銷顧問，請根據以下「顧客流失模型（CatBoost）」給出的數據，
幫我設計【具體可執行】的行銷活動建議。

分析日期：{now_str}
顧客群組：{seg}
觀察區間類型：{period}（window_days={summary.get("window_days")}）
總顧客數：{total} 位
平均流失機率：約 {avg_text}
風險分布：高風險 {high_cnt} 位 / 中風險 {med_cnt} 位 / 低風險 {low_cnt} 位

以下是部分高風險顧客的範例（僅供你掌握輪廓，不需要逐一回應）：
{high_ex_text}

請根據以上資訊，產出一份「針對這個顧客分群」的行銷活動建議，並務必回答到以下兩點內容：


1. 你產出的重點是「優惠券方案」，而不是一般行銷活動文案。
   - 優惠券類型可以包含：滿額折抵、滿件折扣、指定品項折扣、迎新禮、生日禮、免運券等。
   - 每一條精簡寫出優惠類型、開始時間、結束期限。
   - 使用者想知道詳情要在右邊和你討論

2. 請特別著重這三種顧客：
   - 潛在高價值顧客
   - 忠誠客戶
   - 新顧客
   對這三種顧客可以給「相對有吸引力」但仍在合理成本內的優惠券，
   目標是提升回購率、客單價、維持長期關係。

3. 對於沉睡顧客、低價值顧客、潛在流失顧客等：
   - 如果分析後認為「不適合投入太多行銷成本或發放優惠券」，請在【建議優惠券】裡寫：無推薦優惠券
   - 並在【預期成果】中，具體說明「為何不建議發券」，
     例如：毛利過低、再行銷成本過高、歷史消費極少、長期不來店等。

4. 新顧客的優惠力度可以比其他客群「稍大一點」來提高第二次消費機會，
   但仍需考量公司毛利，避免造成虧損。
   - 可以是「首購後 30 天內第二單滿額 9 折」、「新客限定生活必需品 95 折」等。
   - 請在預期成果中說明這樣設計的理由。(這是參考，詳細折扣請參考模型分析)

5. 你的語氣要像給行銷團隊 / 工程師看的規格說明，要能直接落地實作：
   - 具體標出金額、百分比、檔期、目標族群
   - 避免空泛的形容詞（例如「加強關係」、「多互動」）而沒有具體作法。

【輸出格式（請照以下標題與結構）】

建議優惠券:
- 第一個具體優惠券建議（包含門檻、折扣方式、適用品類 / 排除品類、適用族群與簡短理由）
- 第二個具體優惠券建議
- 第三個具體優惠券建議
（若你判斷「不適合發券」，這一段請只寫：無推薦優惠券）

預期成果:
- 對回購率、客單價、活躍度或流失率的預期影響（可用大約百分比或區間描述）
- 若為「無推薦優惠券」，請說明不發券在成本與效益上的考量理由
"""