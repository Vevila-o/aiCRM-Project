#===============RFM分數計算=================

from django.shortcuts import render, redirect
from myCRM.models import Transaction, RFMscore, Customer, CustomerCategory
from datetime import datetime
from django.db.models import Count, Sum, Max
#分類邏輯
def classify_customer(recency_score, frequency_score, monetary_score):
    # 忠誠客戶: 最近活躍、消費金額高、頻繁交易
    if recency_score >= 4 and frequency_score >= 5 and monetary_score >= 5:
        return 1
    
    # 潛在高價值客戶: 消費金額高但交易次數較少
    if recency_score >= 3 and frequency_score >= 3 and monetary_score >= 4:
        return 2  
    
    # 沉睡客戶: 無近期消費但過去曾經活躍
    if recency_score <= 2 and frequency_score >= 3 and monetary_score >= 3:
        return 3
    
    # 低價值客戶: 消費金額非常少、頻率也非常低（最差的一群）
    if recency_score <= 1 and frequency_score <= 1 and monetary_score <= 1:
        return 6

    # 潛在流失客戶: 最近不常來（recency_score 偏低）
    # 且「交易頻率偏低」或「金額偏低」，放寬條件讓這一群人變多一點
    if recency_score <= 3 and (frequency_score <= 3 or monetary_score <= 3):
        return 5
    
    # 普通客戶: 有消費但沒有很活躍（前面都不符合時，一律歸到普通客戶）
    return 4


## rfm 參數規則工具
def rfm_score_from_raw(recency_days: int, frequency: int, monetary: float):
    """
    把原始 recency_days / frequency / monetary
    轉成 R / F / M 分數（完全照你原本的規則）
    """
    # R 分數
    if recency_days <= 30:
        r_score = 5
    elif recency_days <= 60:
        r_score = 4
    elif recency_days <= 90:
        r_score = 3
    elif recency_days <= 120:
        r_score = 2
    else:
        r_score = 1

    # F 分數
    if frequency >= 15:
        f_score = 5
    elif frequency >= 10:
        f_score = 4
    elif frequency >= 6:
        f_score = 3
    elif frequency >= 2:
        f_score = 2
    else:
        f_score = 1

    # M 分數
    if monetary >= 2500:
        m_score = 5
    elif monetary >= 2000:
        m_score = 4
    elif monetary >= 500:
        m_score = 3
    elif monetary >= 100:
        m_score = 2
    else:
        m_score = 1

    return r_score, f_score, m_score





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
    this_month_start = today.replace(day=1)  # 🔹 本月第一天，判斷「本月新註冊」用

    # 先取得所有加入時間在今天以前的顧客
    all_customers = Customer.objects.filter(customerjoinday__lt=today)

    # 查詢所有顧客在今日以前的交易紀錄，並做 R、F、M 聚合
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

    # 將查詢結果轉換為字典，方便查找
    transaction_dict = {row['customerid']: row for row in qs}

    # 依照每位顧客計算 RFM 分數並寫入資料庫
    for customer in all_customers:
        customer_id = customer.customerid

        # =========================================================
        # 🔹 新增條件：本月內註冊的會員，視為「新顧客」
        #    （假設使用 categoryID = 7 當作『新顧客』）
        # =========================================================
        if customer.customerjoinday and customer.customerjoinday >= this_month_start:
            RFMscore.objects.update_or_create(
                customerID=customer_id,
                defaults={
                    "rScore": 0,
                    "fScore": 0,
                    "mScore": 0,
                    "RFMscore": 0,
                    "categoryID": 7,          # 👈 這裡代表「新顧客」
                    "RFMupdate": datetime.now(),
                }
            )
            Customer.objects.filter(customerid=customer_id).update(categoryid=8)
            continue

        if customer_id not in transaction_dict:
            # 已加入但尚未消費的顧客，歸類到 8
            RFMscore.objects.update_or_create(
                customerID=customer_id,
                defaults={
                    "rScore": 0,
                    "fScore": 0,
                    "mScore": 0,
                    "RFMscore": 0,
                    "categoryID": 8,
                    "RFMupdate": datetime.now(),
                }
            )
            Customer.objects.filter(customerid=customer_id).update(categoryid=7)
            continue

        row = transaction_dict[customer_id]
        last_dt = row["recency"]

        # transdate 可能是 datetime 或 date，統一轉換為 date
        last_date = last_dt.date() if isinstance(last_dt, datetime) else last_dt
        recency_days = (today - last_date).days
        frequency = row["frequency"] or 0
        monetary = row["monetary"] or 0

        # 改成呼叫共用工具
        recency_score, frequency_score, monetary_score = rfm_score_from_raw(
            recency_days,
            frequency,
            monetary,
        )


        # RFM 總分
        rfm_value = recency_score + frequency_score + monetary_score

        # 分群類型（呼叫上面的分類邏輯）
        category_id = classify_customer(recency_score, frequency_score, monetary_score)

        # 更新 RFMscore 表（若無則建立）
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

        # 同時更新 Customer 類別（如果有 categoryid 欄位）
        Customer.objects.filter(customerid=customer_id).update(categoryid=category_id)

    # 回傳全部 RFMscore 給 view 用來 render
    return RFMscore.objects.all()


def get_rfm_category_distribution(exclude_labels=None):
    """
    Aggregate customer counts per RFM category.
    Labels matching any value in exclude_labels (e.g. '其他') are skipped.
    Returns {"labels": [...], "counts": [...], "total": int}.
    """
    label_map = {
        str(cat.categoryid): (cat.customercategory or f"分類{cat.categoryid}")
        for cat in CustomerCategory.objects.all()
    }
    excluded = {label.strip() for label in exclude_labels} if exclude_labels else set()

    rows = (
        Customer.objects
        .exclude(categoryid__isnull=True)
        .exclude(categoryid__exact="")
        .values("categoryid")
        .annotate(count=Count("customerid"))
        .order_by("-count")
    )

    labels = []
    counts = []
    total = 0

    for row in rows:
        category_id = row["categoryid"]
        label = label_map.get(str(category_id), str(category_id))
        if not label:
            continue
        label = label.strip()
        if label in excluded:
            continue
        labels.append(label)
        counts.append(row["count"])
        total += row["count"]

    return {
        "labels": labels,
        "counts": counts,
        "total": total,
    }
