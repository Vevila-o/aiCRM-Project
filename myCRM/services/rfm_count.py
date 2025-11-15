#===============RFM分數計算=================

from django.shortcuts import render, redirect
from myCRM.models import Transaction, RFMscore, Customer
from datetime import datetime
from django.db.models import Count, Sum, Max
#分類邏輯
def classify_customer(recency_score,frequency_score,monetary_score):
    #忠誠客戶:最近活躍 消費金額高 頻繁交易
    if recency_score>=4 and frequency_score>=5 and monetary_score>=5:
        return 1
    
    #潛在高價值客戶:消費金額高但交易次數較少
    if recency_score>=3 and frequency_score>=3 and monetary_score>=4:
        return 2  
    
    #沉睡客戶:無近期消費但過去曾經活躍
    if recency_score<=2 and frequency_score>=3 and monetary_score>=3:
        return 3
    
    #潛在流失客戶:消費金額少或長時間無消費
    if recency_score<=2 and frequency_score<=2 and monetary_score<=2:
        return 5
    
    #低價值客戶:消費金額少 頻率也較低
    if recency_score<2 and frequency_score<2 and monetary_score<2:
        return 6 
    
    #普通客戶:有消費但沒有很活躍
    return 4 

def recalc_rfm_scores():
    """
    重新計算所有顧客的 RFM 分數：
    - R（Recency）最近消費間隔天數
    - F（Frequency）交易次數
    - M（Monetary）消費總金額
    並更新：
      - RFMscore 資料表
      - Customer 資料表中的客戶分類（categoryid）
    """

    today = datetime.now().date()  # 取得今天的日期（避免 date/datetime 型別衝突）

    # ------------------------------------------------------------
    # 查詢所有顧客在今日以前的交易紀錄，並做 R、F、M 聚合
    # ------------------------------------------------------------
    qs = (
        Transaction.objects
        .filter(transdate__lt=today)
        .values("customerid")
        .annotate(
            recency=Max("transdate"),            # 最近交易日
            frequency=Count("transactionid"),    # 交易筆數
            monetary=Sum("totalprice"),          # 總金額
        )
    )

    # ------------------------------------------------------------
    # 依照每位顧客計算 RFM 分數並寫入資料庫
    # ------------------------------------------------------------
    for row in qs:
        customer_id = row["customerid"]
        last_dt = row["recency"]

        if last_dt is None:  # 無交易紀錄
            continue

        # transdate 可能是 datetime 或 date，統一轉換為 date
        last_date = last_dt.date() if isinstance(last_dt, datetime) else last_dt
        recency_days = (today - last_date).days

        # R 分數（最近消費越近分數越高）
        recency_score = (
            5 if recency_days <= 30 else
            4 if recency_days <= 60 else
            3 if recency_days <= 90 else
            2 if recency_days <= 120 else
            1
        )

        # F 分數（交易越多分數越高）
        frequency = row["frequency"] or 0
        frequency_score = (
            5 if frequency >= 10 else
            4 if frequency >= 7 else
            3 if frequency >= 4 else
            2 if frequency >= 2 else
            1
        )

        # M 分數（金額越高分數越高）
        monetary = row["monetary"] or 0
        monetary_score = (
            5 if monetary >= 1000 else
            4 if monetary >= 500 else
            3 if monetary >= 300 else
            2 if monetary >= 100 else
            1
        )

        # RFM 總分
        rfm_value = recency_score + frequency_score + monetary_score

        # 分群類型（呼叫上面的分類邏輯）
        category_id = classify_customer(recency_score, frequency_score, monetary_score)

        # ------------------------------------------------------------
        # 更新 RFMscore 表（若無則建立）
        # ------------------------------------------------------------
        RFMscore.objects.update_or_create(
            customerID=customer_id,
            defaults={
                "rScore": recency_score,
                "fScore": frequency_score,
                "mScore": monetary_score,
                "RFMscore": rfm_value,
                "categoryID": category_id,
                "RFMupdate": datetime.now(),
            }
        )

        # ------------------------------------------------------------
        # 同時更新 Customer 類別（如果有 categoryid 欄位）
        # ------------------------------------------------------------
        Customer.objects.filter(customerid=customer_id).update(categoryid=category_id)

    # 回傳全部 RFMscore 給 view 用來 render
    return RFMscore.objects.all()