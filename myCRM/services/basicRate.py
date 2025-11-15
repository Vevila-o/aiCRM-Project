#==========首頁前三個比率計算========
from django.db.models import Count, Sum, Max
from django.shortcuts import render, redirect
from myCRM.models import Customer, Transaction
from datetime import datetime, timedelta,date
from django.db.models import Count
from django.db.models.functions import TruncDate

## 顧客留存率
def calculate_CRR():
    """Calculate monthly Customer Retention Rate (CRR).

   CRR =（上個月和本月都曾購買過商品的顧客數量）/（上月購買過商品的顧客數量） 
   回傳值： - 可計算時返回 0 到 1 之間的浮點數 - 如果上個月沒有顧客（未定義），則傳回 None
    """
    today = date.today()
    # current month/year and previous month/year
    first_day = today.replace(day=1)
    prev_day = first_day - timedelta(days=1)
    cur_year, cur_month = first_day.year, first_day.month
    prev_year, prev_month = prev_day.year, prev_day.month

    # 顧客集合：使用 Transaction 的 transdate / customerid
    prev_qs = (
        Transaction.objects
        .filter(transdate__year=prev_year, transdate__month=prev_month)
        .values_list('customerid', flat=True)
        .distinct()
    )
    cur_qs = (
        Transaction.objects
        .filter(transdate__year=cur_year, transdate__month=cur_month)
        .values_list('customerid', flat=True)
        .distinct()
    )

    prev_set = set([int(c) for c in prev_qs if c is not None])
    cur_set = set([int(c) for c in cur_qs if c is not None])

    prev_count = len(prev_set)
    cur_count = len(cur_set)

    if prev_count == 0:
        return None

    retained = len(prev_set.intersection(cur_set))
    crr = float(retained) / float(prev_count)
    return crr


## 本月回購率
def calculate_RPR():
    """
    Calculate monthly Repeat Purchase Rate (RPR).

    定義：
    RPR = （本月交易≧2筆的顧客數量）/（本月有交易的顧客總數）

    回傳：0~1 的浮點數，若本月沒有顧客消費則回傳 None
    """

    today = date.today()
    first_day = today.replace(day=1)
    cur_year, cur_month = first_day.year, first_day.month

    # 將 transdate 取出日期部分（TruncDate）
    monthly_qs = (
    Transaction.objects
    .filter(transdate__year=cur_year, transdate__month=cur_month)
    .values('customerid', 'transactionid')  # 換成你的欄位名
    .distinct()
    .values('customerid')
    .annotate(order_count=Count('transactionid'))
)

    total_customers = monthly_qs.count()
    if total_customers == 0:
        return None

    repeat_customers = monthly_qs.filter(order_count__gte=2).count()
    rpr = repeat_customers / total_customers

    return rpr


## 高價值顧客占比
def calculate_vip_ratio():
    """
    使用categoryID來計算高價值顧客佔比，
    categoryID 為 1 的顧客被列為高價值顧客
    """
    totalCus = Customer.objects.count()
    vipCus = Customer.objects.filter(categoryid__in=['1']).count()
    if totalCus == 0:
        return None
    vip_ratio = float(vipCus) / float(totalCus)
    return vip_ratio

## 總顧客人數
def calculate_allCus():
    """
    計算截止到今天為止已加入的顧客總數。
    只計算 customerjoinday <= 今天 的顧客。
    """
    today = date.today()
    totalCus = Customer.objects.filter(customerjoinday__lte=today).count()
    return totalCus

    
