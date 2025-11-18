# myCRM/services/ai_suggestion_service.py
import re
from datetime import datetime
from myCRM.models import AiSuggection
from myCRM.services.churn_service import predict_churn    # ⭐ 正確的 import

# -----------------------------
# 解析 ChatGPT 回覆格式
# -----------------------------
SUGGESTION_PATTERN = re.compile(
    r"AI\s*建議方針[:：]\s*(.*?)\s*預期成果[:：]\s*(.*)",
    re.S
)


def parse_chatgpt_suggestion(text: str):
    """
    從 ChatGPT 回覆中解析出：
    - 行銷建議（list）
    - 預期成果（list）
    """
    m = SUGGESTION_PATTERN.search(text)
    if not m:
        return None, None

    raw_strategy = m.group(1).strip()
    raw_outcome = m.group(2).strip()

    def split_lines(s):
        # 以換行 / 項目符號 / 數字編號切段
        items = re.split(r"[\n•\-\d]+\s*", s)
        return [i.strip() for i in items if i.strip()]

    return split_lines(raw_strategy), split_lines(raw_outcome)


# -----------------------------
# 初始模型建議（頁面一載入就會用）
# -----------------------------
def get_initial_suggestion(category_id: int):
    """
    用 CatBoost 模型計算該類型顧客的流失分析摘要
    並自動生成一份「AI 建議方針 + 預期成果」的提示詞
    """

    # 用你原本的 CatBoost 函數
    all_rows = predict_churn()

    # 找出對應 categoryID 的那一群
    target = next((r for r in all_rows if int(r["categoryID"]) == int(category_id)), None)

    if not target:
        avg_prob = 0
        total = 0
        high = 0
    else:
        avg_prob = target.get("probability", 0)
        total = 1
        high = 1 if target.get("risk_level") == "high" else 0

    # 給 ChatGPT 的 system / user 提示內容
    system_text = f"""
你是一位資深行銷顧問，現在你要根據該客群的 CatBoost 流失預測結果產生行銷建議。

請務必輸出「以下兩段」：

AI 建議方針：
（請列出至少 3 點具體的行銷行動，條列式）

預期成果：
（請列出至少 3 點具體指標，例如回購率、營收成長、流失率下降等）

# 模型摘要
- 類別 ID：{category_id}
- 該類別總人數：{total}
- 平均流失機率：{avg_prob:.2f}
- 高風險顧客數量：{high}

請務必照上述標題格式輸出（一定要有「AI 建議方針：」「預期成果：」），方便系統解析。
"""
    return system_text


# -----------------------------
# 寫入 AiSuggection 的功能（執行建議）
# -----------------------------
def save_final_suggestion(category_id, guideline, expected, user_id):
    """
    最終使用者選定的建議，寫入 ai_suggection 表
    """
    AiSuggection.objects.create(
        categoryID=category_id,
        userID=str(user_id),
        aiRecommedGuideline=guideline,
        expectedResults=expected,
        suggestDate=datetime.now()
    )
