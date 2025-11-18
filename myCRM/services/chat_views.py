# myCRM/services/chat_views.py
import os
import json
from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from openai import OpenAI

from myCRM.models import ChatRecord, AiSuggection
from myCRM.services.ai_suggestion_service import (
    parse_chatgpt_suggestion,
    get_initial_suggestion,
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))



# API：AI 建議頁面初始載入 → 給 1 筆「模型分析 + ChatGPT 建議」
@csrf_exempt
def ai_suggestion_init(request):
    """
    前端一打開 ai-suggestion.html，就會呼叫這個 API，
    產生 1 筆初始建議（不寫入資料庫）
    """

    try:
        category_id = int(request.GET.get("categoryID", 1))
    except:
        category_id = 1

    # 取得模型摘要（字串）
    system_text = get_initial_suggestion(category_id)

    # 呼叫 ChatGPT
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": system_text}],
    )
    full_text = completion.choices[0].message.content.strip()

    # 解析 ChatGPT → 建議方針 / 預期成果
    strategies, outcomes = parse_chatgpt_suggestion(full_text)

    item = {
        "id": f"init-{datetime.now().timestamp()}",
        "strategy_points": strategies or [],
        "outcome_points": outcomes or [],
        "executed": False,
        "tag": "模型分析建議",
    }

    return JsonResponse({"initial": item})



# ===================================================================
#  API 2：聊天用（右側 ChatGPT 對話框）
# ===================================================================
@csrf_exempt
def chat(request):
    """
    右側聊天用：
    - 使用者問問題
    - ChatGPT 回答
    - 存入 chat_record table
    - 若回答符合格式 → 自動產生新的建議項目（左側欄位）
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        user_msg = (data.get("message") or "").strip()
        category_id = int(data.get("categoryID") or 0)
        user_id = int(data.get("userID") or 1)  # 之後可改成 request.user.id
    except Exception as e:
        return JsonResponse({"error": f"invalid json: {e}"}, status=400)

    if not user_msg:
        return JsonResponse({"error": "message required"}, status=400)
    if not category_id:
        return JsonResponse({"error": "categoryID required"}, status=400)

    # 送交 ChatGPT
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "你是一位中文行銷策略顧問。回答要實用且清楚。"},
            {"role": "user", "content": user_msg},
        ],
    )
    reply = completion.choices[0].message.content.strip()

    # ⭐ 寫入 chat_record（注意欄位名稱）
    ChatRecord.objects.create(
        user_id=user_id,           # 對應 FK: user
        categoryID=category_id,
        userContent=user_msg,
        aiContent=reply,
    )

    # ⭐ 判斷回覆是否有 "AI 建議方針: ... 預期成果: ..."
    strategies, outcomes = parse_chatgpt_suggestion(reply)

    new_suggestion = None
    if strategies and outcomes:
        new_suggestion = {
            "id": f"chat-{datetime.now().timestamp()}",
            "strategy_points": strategies,
            "outcome_points": outcomes,
            "executed": False,
            "tag": "ChatGPT 微調建議",
        }

    return JsonResponse(
        {
            "reply": reply,
            "newSuggestion": new_suggestion,  # 左側自動新增
        }
    )


# ===================================================================
# ⭐ API 3：執行建議（寫入 ai_suggection 表）
# ===================================================================
@csrf_exempt
def execute_suggestion(request):
    """
    使用者按下「執行此建議」
    -> 寫入 ai_suggection
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        category_id = int(data.get("categoryID"))
        guideline = data.get("guideline") or ""
        outcome = data.get("outcome") or ""
        user_id = int(data.get("userID") or 1)
    except Exception:
        return JsonResponse({"error": "invalid json"}, status=400)

    AiSuggection.objects.create(
        categoryID=category_id,
        userID=str(user_id),
        aiRecommedGuideline=guideline,
        expectedResults=outcome,
        suggestDate=datetime.now(),
    )

    return JsonResponse({"status": "ok"})