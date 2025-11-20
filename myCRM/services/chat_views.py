# myCRM/services/chat_views.py
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError

from openai import OpenAI

from myCRM.models import ChatRecord, AiSuggection
from myCRM.services.ai_suggestion_service import (
    parse_chatgpt_suggestion,
    get_initial_suggestion,
    save_final_suggestion,
    get_comprehensive_customer_analysis,  # 新增綜合分析
    SEGMENT_NAME,  # 客群名稱映射
)

# 設置日誌
logger = logging.getLogger(__name__)

# 初始化OpenAI客戶端
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    logger.error(f"OpenAI client initialization failed: {e}")
    client = None


def _get_enhanced_analysis_context(category_id: int) -> Dict[str, Any]:
    """
    獲取增強的客群分析上下文信息
    """
    try:
        # 獲取綜合分析數據
        comprehensive_data = get_comprehensive_customer_analysis(
            category_id=category_id, 
            top_customers=10
        )
        
        category_analysis = comprehensive_data.get('category_specific_analysis', {})
        general_stats = comprehensive_data.get('consumption_statistics', {})
        
        context = {
            'category_name': SEGMENT_NAME.get(category_id, f'客群{category_id}'),
            'total_customers': category_analysis.get('total_customers_in_category', 0),
            'churn_probability': category_analysis.get('churn_analysis', {}).get('average_churn_probability', 0),
            'high_risk_count': category_analysis.get('churn_analysis', {}).get('high_risk_count', 0),
            'avg_next_purchase_days': category_analysis.get('next_purchase_analysis', {}).get('average_next_purchase_days', 0),
            'customers_buying_soon': len(category_analysis.get('next_purchase_analysis', {}).get('customers_buying_soon', [])),
            'rfm_scores': category_analysis.get('rfm_statistics', {}),
            'general_revenue': general_stats.get('total_revenue', 0),
            'general_conversion_rate': general_stats.get('purchase_conversion_rate', 0)
        }
        
        return context
        
    except Exception as e:
        logger.warning(f"Failed to get comprehensive analysis for category {category_id}: {e}")
        return {
            'category_name': SEGMENT_NAME.get(category_id, f'客群{category_id}'),
            'total_customers': 0,
            'churn_probability': 0,
            'error': '無法獲取詳細分析數據'
        }


# API：ai建議頁面初始載入->給1筆模型分析+ChatGPT建議
@csrf_exempt
@require_http_methods(["GET"])
def ai_suggestion_init(request):
    """
    前端一打開 ai-suggestion.html，就會呼叫這個 API，
    提供基於綜合客戶分析的智能優惠券建議：
    - 整合RFM、CatBoost流失預測、LSTM購買預測
    - 右側聊天區會顯示這次問答
    - 左側列表會顯示從這次回答解析出的「建議優惠券 / 預期成果」
    """
    if not client:
        return JsonResponse({"error": "OpenAI service unavailable"}, status=503)
    
    try:
        category_id = int(request.GET.get("categoryID", 1))
        if category_id not in range(1, 8):  # 有效客群ID範圍
            category_id = 1
    except (ValueError, TypeError):
        category_id = 1
        
    period = request.GET.get("period", "month")
    
    period_text = {
        "month": "本月",
        "quarter": "本季",
    }.get(period, "這段期間")
    
    # 獲取增強的分析上下文
    analysis_context = _get_enhanced_analysis_context(category_id)
    
    # 構建更詳細的用戶問題
    user_question = (
        f"基於我們的綜合客戶分析系統（整合RFM模型、CatBoost流失預測、LSTM購買預測），"
        f"針對「{period_text}、{analysis_context['category_name']}」客群（共{analysis_context['total_customers']}位客戶）的分析結果：\n\n"
        f"- 平均流失機率：{analysis_context['churn_probability']:.1%}\n"
        f"- 高風險客戶數：{analysis_context['high_risk_count']}人\n"
        f"- 預期下次購買天數：{analysis_context.get('avg_next_purchase_days', 'N/A')}天\n"
        f"- 即將購買客戶數：{analysis_context['customers_buying_soon']}人\n\n"
        "請幫我設計具體的優惠券方案（包括優惠券類型與使用門檻、開始時間、結束時間），"
        "以及根據這些優惠券方案推估的預期成效（例如回購率、營收、流失率的變化）。"
    )
    
    # 取得模型摘要+提示詞（保持原有邏輯）
    system_text = get_initial_suggestion(category_id)

    try:
        # 呼叫ChatGPT
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_question}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        full_text = completion.choices[0].message.content.strip()
        
        # 解析ChatGPT回覆 → 建議優惠券/預期成果
        coupon, outcome = parse_chatgpt_suggestion(full_text)
        
        # 構建建議項目
        item = {
            "id": f"init-{datetime.now().timestamp()}",
            "strategy_points": coupon or [],
            "outcome_points": outcome or [],
            "executed": False,
            "tag": "AI綜合分析建議",
            "analysis_context": analysis_context,  # 添加分析上下文
        }
        
        logger.info(f"Generated AI suggestion for category {category_id}")
        
        return JsonResponse({
            "success": True,
            "initial": item,              # 左側列表用
            "question": user_question,     # 右側聊天使用者Q
            "reply": full_text,           # 右側聊天AI回覆全文
            "analysis_summary": analysis_context  # 分析摘要
        })
        
    except Exception as e:
        logger.error(f"AI suggestion generation failed: {e}")
        return JsonResponse({
            "success": False,
            "error": "AI建議生成失敗，請稍後再試",
            "analysis_summary": analysis_context
        }, status=500)

#API 2：聊天用（右邊chatGPT對話框）
@csrf_exempt
@require_http_methods(["POST"])
def chat(request):
    """
    增強版聊天API：
    - 使用者問問題
    - ChatGPT基於綜合分析數據回答
    - 存入chat_record table
    - 若回答符合「建議優惠券 / 預期成果」格式 → 自動產生新的建議項目（左側欄位）
    - 支持上下文感知的對話
    """
    if not client:
        return JsonResponse({"error": "OpenAI service unavailable"}, status=503)

    try:
        data = json.loads(request.body.decode("utf-8"))
        user_msg = (data.get("message") or "").strip()
        category_id = int(data.get("categoryID") or 0)
        user_id = int(data.get("userID") or 1)  # 之後可改成 request.user.id
        
        # 新增：獲取對話歷史上下文（可選）
        include_context = data.get("includeContext", True)
        
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning(f"Invalid request data: {e}")
        return JsonResponse({"error": "Invalid JSON format or data types"}, status=400)

    # 參數驗證
    if not user_msg:
        return JsonResponse({"error": "message required"}, status=400)
    if not category_id or category_id not in range(1, 8):
        return JsonResponse({"error": "valid categoryID (1-7) required"}, status=400)
    if len(user_msg) > 1000:  # 限制消息長度
        return JsonResponse({"error": "message too long (max 1000 characters)"}, status=400)

    # 獲取當前客群的分析上下文
    analysis_context = _get_enhanced_analysis_context(category_id) if include_context else {}
    
    # 構建增強的系統提示詞
    context_info = ""
    if analysis_context and not analysis_context.get('error'):
        context_info = f"""
        
當前客群分析數據：
- 客群：{analysis_context['category_name']}
- 客戶總數：{analysis_context['total_customers']}人
- 平均流失機率：{analysis_context['churn_probability']:.1%}
- 高風險客戶：{analysis_context['high_risk_count']}人
- 即將購買客戶：{analysis_context['customers_buying_soon']}人
- 平均下次購買天數：{analysis_context.get('avg_next_purchase_days', 'N/A')}天
"""
    
    system_prompt = f"""
你是一位專業的中文AI行銷顧問，專門基於數據分析設計「優惠券方案」。
你擁有客戶的RFM分析、流失預測和購買行為預測數據。{context_info}

使用者會針對優惠券方案提出問題或調整要求。請依照下列原則回答：

1. 先基於客群數據判斷使用者提出的調整是否合理（成本效益、客群價值、行為模式）。

2. 如果判斷「合理且值得推薦」：
   回覆時務必使用這個格式：

   建議優惠券:
   - 具體優惠券描述｜開始時間:YYYY-MM-DD｜結束時間:YYYY-MM-DD
   （可以有多條，每條都要包含完整的時間信息）

   預期成果:
   - 基於數據分析，說明執行該優惠券後在回購率、客單價、流失率等的具體預期影響

3. 如果判斷「不合理或不建議」：
   - 清楚說明「為何不建議」，引用相關的客群數據
   - 千萬不要輸出「建議優惠券:」標題，避免系統誤判

4. 對於高風險流失或低價值客群，如果不適合發券：
   在【建議優惠券】中寫：無推薦優惠券
   在【預期成果】中基於數據解釋原因

請保持專業、數據導向的建議風格。
"""

    try:
        # 構建對話消息
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        # 可選：添加最近的對話歷史
        if include_context:
            recent_chats = ChatRecord.objects.filter(
                categoryID=category_id
            ).order_by('-chatID')[:3]  # 最近3條對話
            
            for chat in reversed(recent_chats):  # 按時間順序
                messages.append({"role": "user", "content": chat.userContent})
                messages.append({"role": "assistant", "content": chat.aiContent})
        
        # 添加當前用戶消息
        messages.append({"role": "user", "content": user_msg})
        
        # 送交 ChatGPT
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=1200
        )
        reply = completion.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"ChatGPT API call failed: {e}")
        return JsonResponse({
            "error": "AI服務暫時不可用，請稍後再試",
            "success": False
        }, status=500)

    try:
        # 寫入chat_record
        ChatRecord.objects.create(
            user_id=user_id,           
            categoryID=category_id,
            userContent=user_msg,
            aiContent=reply,
        )
        
        # 判斷回覆是否有「建議優惠券: ... 預期成果: ...」
        coupon, outcome = parse_chatgpt_suggestion(reply)
        
        new_suggestion = None
        if coupon and outcome:
            new_suggestion = {
                "id": f"chat-{datetime.now().timestamp()}",
                "strategy_points": coupon,
                "outcome_points": outcome,
                "executed": False,
                "tag": "AI智能微調建議",
                "analysis_context": analysis_context,  # 添加分析上下文
            }
            
        logger.info(f"Chat processed for category {category_id}, user {user_id}")
        
        return JsonResponse({
            "success": True,
            "reply": reply,
            "newSuggestion": new_suggestion,  # 左邊自動新增
            "analysis_context": analysis_context  # 返回分析上下文
        })
        
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        return JsonResponse({
            "success": False,
            "error": "對話處理失敗，請重試"
        }, status=500)


#API 3：執行建議（寫入ai_suggection表）
@csrf_exempt
@require_http_methods(["POST"])
def execute_suggestion(request):
    """
    使用者執行AI建議：
    - 保存建議到ai_suggection表
    - 創建優惠券活動到campaign表
    - 記錄執行日誌
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
        category_id = int(data.get("categoryID"))
        guideline = data.get("guideline", "").strip()
        outcome = data.get("outcome", "").strip()
        user_id = int(data.get("userID", 1))
        
        # 新增：建議來源標記
        suggestion_source = data.get("source", "chat")  # init, chat, manual
        
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning(f"Invalid execute suggestion data: {e}")
        return JsonResponse({"error": "Invalid request data"}, status=400)

    # 參數驗證
    if not category_id or category_id not in range(1, 8):
        return JsonResponse({"error": "Valid categoryID required"}, status=400)
    if not guideline:
        return JsonResponse({"error": "Guideline content required"}, status=400)

    try:
        # 執行建議保存
        suggest_id = save_final_suggestion(
            category_id=category_id,
            guideline=guideline,
            expected=outcome,
            user_id=user_id,
        )
        
        logger.info(f"Suggestion executed: ID={suggest_id}, Category={category_id}, User={user_id}, Source={suggestion_source}")
        
        return JsonResponse({
            "success": True,
            "status": "executed",
            "suggestID": suggest_id,
            "message": "建議已成功執行並創建優惠券活動"
        })
        
    except Exception as e:
        logger.error(f"Failed to execute suggestion: {e}")
        return JsonResponse({
            "success": False,
            "error": "建議執行失敗，請重試"
        }, status=500)


# 新增API：獲取客群分析摘要
@csrf_exempt
@require_http_methods(["GET"])
def get_category_analysis(request):
    """
    獲取特定客群的分析摘要
    """
    try:
        category_id = int(request.GET.get("categoryID", 1))
        if category_id not in range(1, 8):
            return JsonResponse({"error": "Invalid categoryID"}, status=400)
            
        analysis_context = _get_enhanced_analysis_context(category_id)
        
        return JsonResponse({
            "success": True,
            "category_id": category_id,
            "analysis": analysis_context
        })
        
    except Exception as e:
        logger.error(f"Failed to get category analysis: {e}")
        return JsonResponse({
            "success": False,
            "error": "無法獲取客群分析"
        }, status=500)

