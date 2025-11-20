#從chatgpt回覆裡抓出"建議優惠券""預期成果"
#初次進入頁面時用catboost做摘要+給chatgpt的提示詞
import re
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Max
from myCRM.models import AiSuggection, Campaign, Customer, Transaction, RFMscore
from myCRM.services.churn_service import predict_churn
from myCRM.services.rfm_count import recalc_rfm_scores, get_rfm_category_distribution
from myCRM.services.next_purchse import predict_next_purchase_batch
from myCRM.services.customerActivityRate import get_customer_growth, get_customer_activity  

SEGMENT_NAME = {
    1: "忠誠顧客",
    2: "潛在高價值顧客",
    3: "普通顧客",
    4: "低價值顧客",
    5: "沉睡顧客",
    6: "潛在流失顧客",
    7: "新顧客",
}
#chatgpt回覆格式
SUGGESTION_PATTERN = re.compile(
    r"建議優惠券[:：]\s*(.*?)\s*預期成果[:：]\s*(.*)",
    re.S
)


def parse_chatgpt_suggestion(text: str):
    """
    從 ChatGPT 回覆中解析出：
    - 建議優惠券（list）
    - 預期成果（list）
    """
    m = SUGGESTION_PATTERN.search(text)
    if not m:
        return None, None

    raw_strategy = m.group(1).strip()
    raw_outcome = m.group(2).strip()

    def split_lines(s):
        items = re.split(r"\n+", s.strip())
        return [i.lstrip("- ").strip() for i in items if i.strip()]


    return split_lines(raw_strategy), split_lines(raw_outcome)


# 綜合模型數據分析函數
def get_comprehensive_customer_analysis(category_id: int = None, top_customers: int = 20):
    """
    綜合分析顧客數據，整合RFM模型、CatBoost流失率預測、LSTM下次購買天數預測，以及客群消費狀態
    
    Args:
        category_id: 特定客群ID，若為None則分析所有客群
        top_customers: 要分析的前N位客戶數量
    
    Returns:
        dict: 包含所有模型預測結果和客群分析的綜合報告
    """
    
    # 1. RFM分析 - 重新計算所有顧客的RFM分數
    print("正在更新RFM分數...")
    recalc_rfm_scores()
    
    # 2. 獲取RFM客群分佈
    rfm_distribution = get_rfm_category_distribution(exclude_labels=['其他'])
    
    # 3. CatBoost流失率預測
    print("正在進行流失率預測...")
    churn_predictions = predict_churn()
    
    # 4. LSTM下次購買天數預測
    print("正在預測下次購買時間...")
    try:
        next_purchase_predictions = predict_next_purchase_batch(top_n=top_customers)
    except Exception as e:
        print(f"LSTM預測失敗: {e}")
        next_purchase_predictions = []
    
    # 5. 顧客成長率和活躍度分析
    growth_analysis = get_customer_growth(period="month", points=6)
    activity_analysis = get_customer_activity(period="quarter", points=4)
    
    # 6. 客群消費狀態統計
    consumption_stats = _get_consumption_statistics(category_id)
    
    # 7. 整合特定客群的詳細分析
    if category_id:
        category_analysis = _get_category_detailed_analysis(category_id, churn_predictions, next_purchase_predictions)
    else:
        category_analysis = None
    
    # 8. 建立綜合報告
    comprehensive_report = {
        "analysis_time": timezone.now().isoformat(),
        "statistics": consumption_stats,  # 主要統計數據，測試腳本期望的格式
        "rfm_analysis": {
            "distribution": rfm_distribution,
            "total_customers": rfm_distribution.get("total", 0)
        },
        "churn_analysis": {
            "total_analyzed": len(churn_predictions),
            "high_risk_count": sum(1 for p in churn_predictions if p.get("risk_level") == "high"),
            "medium_risk_count": sum(1 for p in churn_predictions if p.get("risk_level") == "medium"),
            "low_risk_count": sum(1 for p in churn_predictions if p.get("risk_level") == "low"),
            "average_churn_probability": round(sum(p.get("probability", 0) for p in churn_predictions) / len(churn_predictions), 3) if churn_predictions else 0,
            "predictions": churn_predictions[:top_customers]  # 只返回前N個客戶的詳細預測
        },
        "next_purchase_analysis": {
            "total_predictions": len(next_purchase_predictions),
            "average_predicted_days": round(sum(p.get("predicted_days", 0) for p in next_purchase_predictions) / len(next_purchase_predictions), 1) if next_purchase_predictions else 0,
            "predictions": next_purchase_predictions
        },
        "growth_analysis": growth_analysis,
        "activity_analysis": activity_analysis,
        "consumption_statistics": consumption_stats,  # 保留原始鍵名作為備份
        "category_specific_analysis": category_analysis
    }
    
    return comprehensive_report


def _get_consumption_statistics(category_id: int = None):
    """
    獲取客群消費狀態統計
    """
    # 基本查詢條件
    base_query = Customer.objects.all()
    if category_id:
        base_query = base_query.filter(categoryid=category_id)
    
    # 消費統計
    stats = {}
    
    # 總客戶數
    stats["total_customers"] = base_query.count()
    
    # 有購買紀錄的客戶數
    customers_with_purchases = base_query.filter(
        customerid__in=Transaction.objects.values('customerid').distinct()
    ).count()
    stats["customers_with_purchases"] = customers_with_purchases
    
    # 最近30天活躍客戶
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    recent_active = base_query.filter(customerlastdaybuy__gte=thirty_days_ago).count()
    stats["recent_active_customers"] = recent_active
    
    # 消費金額統計
    if category_id:
        customer_ids = base_query.values_list('customerid', flat=True)
        transactions = Transaction.objects.filter(customerid__in=customer_ids)
    else:
        transactions = Transaction.objects.all()
    
    consumption_data = transactions.aggregate(
        total_revenue=Sum('totalprice'),
        average_order_value=Avg('totalprice'),
        max_order_value=Max('totalprice'),
        total_transactions=Count('transactionid')
    )
    
    stats.update({
        "total_revenue": round(consumption_data.get("total_revenue", 0) or 0, 2),
        "average_order_value": round(consumption_data.get("average_order_value", 0) or 0, 2),
        "max_order_value": round(consumption_data.get("max_order_value", 0) or 0, 2),
        "total_transactions": consumption_data.get("total_transactions", 0),
        "purchase_conversion_rate": round((customers_with_purchases / stats["total_customers"]) * 100, 2) if stats["total_customers"] > 0 else 0,
        "recent_activity_rate": round((recent_active / stats["total_customers"]) * 100, 2) if stats["total_customers"] > 0 else 0
    })
    
    return stats


def _get_category_detailed_analysis(category_id: int, churn_predictions: list, next_purchase_predictions: list):
    """
    獲取特定客群的詳細分析
    """
    # 篩選出該客群的預測結果
    category_churn = [p for p in churn_predictions if p.get("categoryID") == category_id]
    
    # 從next_purchase_predictions中找到對應客戶的預測
    category_customers = Customer.objects.filter(categoryid=category_id).values_list('customerid', flat=True)
    category_next_purchase = [p for p in next_purchase_predictions if p.get("customer_id") in category_customers]
    
    # RFM分佈
    rfm_scores = RFMscore.objects.filter(categoryID=category_id)
    rfm_stats = rfm_scores.aggregate(
        avg_r_score=Avg('rScore'),
        avg_f_score=Avg('fScore'),
        avg_m_score=Avg('mScore'),
        avg_rfm_total=Avg('RFMscore')
    )
    
    analysis = {
        "category_id": category_id,
        "category_name": SEGMENT_NAME.get(category_id, f"客群 {category_id}"),
        "total_customers_in_category": len(category_customers),
        "churn_analysis": {
            "analyzed_count": len(category_churn),
            "average_churn_probability": round(sum(p.get("probability", 0) for p in category_churn) / len(category_churn), 3) if category_churn else 0,
            "high_risk_count": sum(1 for p in category_churn if p.get("risk_level") == "high"),
            "top_risk_customers": sorted(category_churn, key=lambda x: x.get("probability", 0), reverse=True)[:5]
        },
        "next_purchase_analysis": {
            "analyzed_count": len(category_next_purchase),
            "average_next_purchase_days": round(sum(p.get("predicted_days", 0) for p in category_next_purchase) / len(category_next_purchase), 1) if category_next_purchase else 0,
            "customers_buying_soon": [p for p in category_next_purchase if p.get("predicted_days", 999) <= 7],  # 7天內會購買的客戶
            "customers_buying_later": [p for p in category_next_purchase if p.get("predicted_days", 0) > 30]  # 30天後才購買的客戶
        },
        "rfm_statistics": {
            "average_recency_score": round(rfm_stats.get("avg_r_score", 0) or 0, 2),
            "average_frequency_score": round(rfm_stats.get("avg_f_score", 0) or 0, 2),
            "average_monetary_score": round(rfm_stats.get("avg_m_score", 0) or 0, 2),
            "average_total_rfm_score": round(rfm_stats.get("avg_rfm_total", 0) or 0, 2)
        }
    }
    
    return analysis


# 初始模型建議（頁面一載入就會用到）
def get_initial_suggestion(category_id: int):
    """
    用 CatBoost 模型計算該類型顧客的流失分析摘要
    並自動生成一份「建議優惠券 + 預期成果」的提示詞
    """
    seg_name = SEGMENT_NAME.get(category_id, f"顧客類型 {category_id}")

    # 用原本的CatBoost 函數
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

    # 給 ChatGPT 的 system /user提示內容
    system_text = f"""
你是一位專業的行銷顧問，熟悉我們的RFM分析與CatBoost顧客流失預測模型，現在你要幫我針對「{seg_name}（ID={category_id}）」產出優惠券建議。

請務必輸出以下兩段：

建議優惠券：
（請列出1-2個具體的優惠券方案，每一條請「單行」寫清楚以下三項：
  1. 優惠券類型 + 使用門檻，例如：
     - 滿額折扣券：滿 1,000 元 享 8 折
     - 折價券：滿 800 元折 150 元
     - 迎新禮：新客第二筆訂單享 7 折
     - 指定品項折扣：生鮮品項 9 折券

每一條請用「一句話」描述，例如：
  -滿千打八折｜開始時間2025-12-01｜結束時間2025-12-31
  -生鮮9折券｜開始時間2025-12-01｜結束時間2025-12-15
如果你判斷「不適合發放優惠券」，這一段請只寫：無推薦優惠券）

預期成果：
（請列出至少1點，最多3點，**一定要跟你上面設計的優惠券方案有關**，
  並用具體數字說明，例如：
  - 預期回購率提升2%～5%
  - 預期該客群營收成長10%～15%
  - 預期流失率下降5%～8%
  若為「無推薦優惠券」，請說明不發券在成本與效益上的理由。）

# 模型摘要
- 類別 ID：{category_id}
- 該類別總人數：{total}
- 平均流失機率：{avg_prob:.2f}
- 高風險顧客數量：{high}

【重要規則，請務必遵守】
1. 著重的顧客：
   - 1 忠誠客戶
   - 2 潛在高價值顧客
   - 7 新顧客
   這三種顧客可以給「相對有吸引力」但仍在合理成本內的優惠券，目標是提升回購率、客單價、維持長期關係。
2. 對 3 普通顧客、4 低價值顧客、5 沉睡顧客、6 潛在流失顧客：
   - 不要投入太多行銷成本。
   - 如果你判斷不適合發放優惠券，請在【建議優惠券】只寫：無推薦優惠券，
     並在【預期成果】中說明理由（例如毛利過低、再行銷成本過高、歷史消費極少、長期不來店等）。

3. 新顧客的優惠力度可以比其他客群「稍大一點」來提高第二次消費機會，
   但仍需考量公司毛利，避免造成虧損。
   - 可以是「首購後30天內第二單滿千七折」等。

4. 你的輸出格式一定要依照上面的兩個標題：
   - 建議優惠券：
   - 預期成果：
   方便系統解析與寫入資料庫。

5. **上面列出的例子（數字、文案）都只是範例，請不要直接照抄!!!!!**
   你需要根據此顧客類型的特性與模型摘要，自行分析合理的門檻與百分比。
"""
    return system_text


#"建議優惠券"
DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")

def _parse_coupon_info(guideline_text: str):
    """
    解析優惠券資訊：
    - 若文字中含「無推薦優惠券」「不推薦給優惠」 → return {"has_coupon": False}
    - 否則嘗試抓：
        - type: 行內的「建議優惠券（XXX）」裡的 XXX
        - start_date, end_date: 文中出現的兩個 yyyy-mm-dd
    """
    text = guideline_text or ""
    if "無推薦優惠券" in text:
        return {"has_coupon": False}

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    coupon_type = None
    for ln in lines:
        if "建議優惠券" in ln:
            #抓「建議優惠券折扣券」裡面的「折扣券」
            m = re.search(r"建議優惠券[（(](.*?)[)）]", ln)
            if m:
                coupon_type = m.group(1).strip()
            else:
                coupon_type = ln
            break

    if not coupon_type and lines:
        coupon_type = lines[0]

    #抓日期
    dates = DATE_PATTERN.findall(text)
    start_date = dates[0] if len(dates) >= 1 else None
    end_date = dates[1] if len(dates) >= 2 else None

    return {
        "has_coupon": True,
        "type": coupon_type,
        "start_date": start_date,
        "end_date": end_date,
    }

# 寫入AiSuggection + campaign

def save_final_suggestion(category_id, guideline, expected, user_id):
    """
    最終使用者選定的建議
    1. 寫入ai_suggection表:
    - aiRecommendGuideline = "優惠" 或 "無建議優惠券"
    2. 若有優惠券 則寫入campaign表（優惠券發放紀錄）
    """
    
    text = (guideline or "").strip()
    
    # 判斷是否有推薦優惠券
    has_coupon = bool(text) and "無推薦優惠券" not in text
    
    #aiRecommendGuideline只存"優惠"或"無建議優惠券"
    ai_guideline_flag = "優惠" if has_coupon else "無建議優惠券"

#寫入aisuggestion表
    obj = AiSuggection.objects.create(
        categoryID=category_id,
        userID=str(user_id),
        aiRecommedGuideline=ai_guideline_flag,  # 注意：根據模型定義，字段名是aiRecommedGuideline
        expectedResults=expected or "",
        suggestDate=timezone.now()
    )
    
    #如有優惠券 寫進campaign
    if has_coupon:
        now = timezone.now()

        # 先抓第一行 當作優惠券類型 +門檻的文字
        first_line = text.splitlines()[0].strip()
        
        # 優惠券類型（左邊第一段，限制 45 字）
        coupon_type = first_line.split("｜")[0].strip()[:45] if "｜" in first_line else first_line[:45]

        #start end優先用chatgpt文字李的日期 抓不到就預設30天
    # 解析開始/結束日期（抓不到就用今天+30）
        m = re.search(
            r"開始時間[:：]\s*(\d{{4}}-\d{{2}}-\d{{2}}).*?結束時間[:：]\s*(\d{{4}}-\d{{2}}-\d{{2}})",
            text
        )
        if m:
            try:
                # 將字串轉為時區感知的datetime
                start_dt = timezone.make_aware(datetime.strptime(m.group(1), "%Y-%m-%d"))
                end_dt = timezone.make_aware(datetime.strptime(m.group(2), "%Y-%m-%d"))
            except Exception:
                start_dt = timezone.now()
                end_dt = start_dt + timedelta(days=30)
        else:
            start_dt = timezone.now()
            end_dt = start_dt + timedelta(days=30)
        

        # 獲取下一個可用的 campaignid
        max_campaign_id = Campaign.objects.aggregate(max_id=Max('campaignid'))['max_id'] or 0
        next_campaign_id = max_campaign_id + 1
        
        Campaign.objects.create(
            campaignid=next_campaign_id,          # 手動設定主鍵
            customerid=None,                      #######要改客群
            type=coupon_type or "未命名優惠券",
            givetime=timezone.now(),
            starttime=start_dt,
            endtime=end_dt,
            isuse="0",                            #還沒用
            # suggectid=obj.pk,             #連回ai_suggestion (Campaign模型中沒有這個字段，先註解)
        )
    return obj.pk

    

