# myCRM/services/marketing_suggestion.py
from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import date
from statistics import mean

from django.utils import timezone
from .churn_service import predict_churn

CATEGORY_LABELS = {
    1: "忠誠客戶",
    2: "潛在高價值顧客",
    3: "沉睡顧客",
    4: "普通顧客",
    5: "潛在流失顧客",
    6: "低價值顧客",
    7: "新顧客",
}

def _window_days_for_period(period: str) -> int:
    """
    月 / 季 對應到 churn_service 需要的 window_days。
    """
    if period == "month":
        return 30
    if period == "quarter":
        return 90
    # fallback：一年
    return 365


def catboost_segment_summary(
    category_id: int,
    period: str,
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """
    以 churn_service.predict_churn() 的結果為基礎，整理出某一個 categoryID 的摘要：
    - 總顧客數
    - 風險分布（high / medium / low）
    - 平均流失機率
    - 最高 / 最低機率
    等資訊給 ChatGPT 當「背景數據」。:contentReference[oaicite:3]{index=3}
    """
    window_days = _window_days_for_period(period)

    results = predict_churn(as_of=as_of, window_days=window_days)

    # 過濾成只剩下指定 categoryID 的顧客
    seg_rows: List[Dict[str, Any]] = [
        r for r in results
        if int(r.get("categoryID", 0)) == int(category_id)
    ]

    total = len(seg_rows)
    if total == 0:
        return {
            "segment_name": CATEGORY_LABELS.get(category_id, f"顧客類型 {category_id}"),
            "period": period,
            "window_days": window_days,
            "total_customers": 0,
            "avg_probability": None,
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 0,
            "high_examples": [],
            "now_str": timezone.localtime(timezone.now()).strftime("%Y-%m-%d"),
        }

    probs = [float(r.get("probability", 0.0)) for r in seg_rows]
    avg_prob = mean(probs)
    max_prob = max(probs)
    min_prob = min(probs)

    high = [r for r in seg_rows if r.get("risk_level") == "high"]
    med  = [r for r in seg_rows if r.get("risk_level") == "medium"]
    low  = [r for r in seg_rows if r.get("risk_level") == "low"]

    # 挑幾個高風險實例給 AI 參考（只給 ID 和機率，避免太長）
    high_examples = [
        {
            "customerid": r.get("customerid"),
            "probability": float(r.get("probability", 0.0)),
            "recency_days": int(r.get("recency_days", 0)),
            "frequency": int(r.get("frequency", 0)),
            "monetary": float(r.get("monetary", 0.0)),
        }
        for r in high[:5]
    ]

    return {
        "segment_name": CATEGORY_LABELS.get(category_id, f"顧客類型 {category_id}"),
        "period": period,
        "window_days": window_days,
        "total_customers": total,
        "avg_probability": avg_prob,
        "max_probability": max_prob,
        "min_probability": min_prob,
        "high_risk_count": len(high),
        "medium_risk_count": len(med),
        "low_risk_count": len(low),
        "high_examples": high_examples,
        "now_str": timezone.localtime(timezone.now()).strftime("%Y-%m-%d"),
    }


def build_system_prompt(summary: Dict[str, Any]) -> str:
    """
    把上面的摘要轉成給 ChatGPT 的 system prompt，
    明確要求它用「AI 建議方針 / 預期成果」兩段式回應。
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
        avg_text = f"{avg_p*100:.1f}%"
    else:
        avg_text = "資料量不足"

    high_ex_lines = []
    for ex in summary.get("high_examples", []):
        high_ex_lines.append(
            f"- 顧客 {ex['customerid']}：流失機率約 {ex['probability']*100:.1f}%，"
            f"最近未來店天數 {ex['recency_days']} 天，"
            f"過去消費次數 {ex['frequency']} 次，金額約 {ex['monetary']:.0f} 元"
        )
    high_ex_text = "\n".join(high_ex_lines) if high_ex_lines else "（略）"

    return f"""
你是一位實體零售通路的行銷顧問，請根據以下「顧客流失模型（CatBoost）」給出的數據，
幫我設計【具體可執行】的行銷活動建議。

分析日期：{now_str}
顧客群組：{seg}
觀察區間類型：{period}（window_days={summary.get("window_days")}）
此群組顧客數：{total} 人
預估平均流失機率：約 {avg_text}
風險分布：
- 高風險顧客數：{high_cnt} 人
- 中風險顧客數：{med_cnt} 人
- 低風險顧客數：{low_cnt} 人

高風險代表性顧客（部分樣本）：
{high_ex_text}

請依照下面這個固定格式回覆（一定要有這兩段標題）：

AI 建議方針：請寫出具體活動策略，例如：
- 針對哪一群人發送什麼樣的優惠 / 關懷訊息
- 要用什麼管道（簡訊、LINE、APP 推播、EDM、門市活動）
- 建議活動期間與執行節奏（例如兩週一次、先喚醒再加碼）

預期成果：請說明執行這個活動後，
- 對「流失率 / 留存率 / 回購率 / 營收 / 客單價」預期會有什麼變化（可大約量化）
- 例如：預期高風險族群的流失率可從 40% 降到 30%，整體營收提升 5% 等。
"""
