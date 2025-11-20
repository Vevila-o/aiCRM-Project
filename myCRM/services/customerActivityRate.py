# myCRM/services/customerActivityRate.py

from datetime import date, timedelta
from calendar import monthrange
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth, TruncWeek, TruncQuarter

from myCRM.models import Customer   # 如果 app 名稱不是 myCRM，記得改這行


# ========== 顧客成長率服務（折線圖） ==========

def _shift_month(base: date, offset: int) -> date:
    """
    讓日期往前 / 往後移動 offset 個「月份」，並且自動處理天數溢位問題。
    例如：2025-01-31 往後一個月 -> 2025-02-28
    """
    month_index = base.month - 1 + offset
    year = base.year + month_index // 12
    month = month_index % 12 + 1
    day = min(base.day, monthrange(year, month)[1])
    return base.replace(year=year, month=month, day=day)


def _quarter_start(base: date) -> date:
    """
    把日期壓成「該季的第一天」：
    2025-02-10 -> 2025-01-01（Q1）
    2025-06-05 -> 2025-04-01（Q2）
    """
    quarter = (base.month - 1) // 3
    month = quarter * 3 + 1
    return base.replace(month=month, day=1)


def _quarter_label(start: date) -> str:
    """
    產生季的標籤，例如 2025 Q1。
    """
    quarter = (start.month - 1) // 3 + 1
    return f"{start.year} Q{quarter}"


def _collect_monthly_counts():
    """
    查出「每個月份新增顧客數」：
    回傳 dict: { date(YYYY-MM-01) -> 當月新加入顧客數 }
    """
    rows = (
        Customer.objects
        .exclude(customerjoinday__isnull=True)
        .annotate(month=TruncMonth("customerjoinday"))
        .values("month")
        .annotate(count=Count("customerid"))
        .order_by("month")
    )

    counts = {}
    for row in rows:
        month_dt = row["month"]
        if month_dt is None:
            continue
        # month_dt可能是datetime或date類型，統一處理
        if hasattr(month_dt, 'date'):
            month_key = month_dt.date()
        else:
            month_key = month_dt
        counts[month_key] = row["count"]
    return counts


def get_customer_activity(period: str = "quarter", points: int = 4):
    """
    計算「顧客活躍度」數據，支援季度和周度分析。
    
    period:
        "quarter" -> 以季度為單位分析顧客活躍度
        "week"    -> 以周為單位分析顧客活躍度
    
    points:
        要回傳幾個時間點（最近 N 個季度 / 周）
    
    回傳格式：
    {
        "period": "quarter" | "week",
        "labels": [...],           # X 軸標籤
        "activity_rates": [...],   # 顧客活躍度（% 數值）
        "active_customers": [...], # 活躍顧客數
        "total_customers": [...],  # 總顧客數
    }
    
    活躍度定義：
        - 季度：該季內有進行任何活動的顧客比例
        - 周：該周內有進行任何活動的顧客比例
    """
    # 1. 參數整理
    period = (period or "quarter").lower()
    if period not in {"quarter", "week"}:
        period = "quarter"
    
    points = max(1, int(points or 4))
    
    # 2. 取得時間範圍
    today = date.today()
    time_periods = _get_time_periods(period, points, today)
    
    if not time_periods:
        return {
            "period": period,
            "labels": [],
            "activity_rates": [],
            "active_customers": [],
            "total_customers": [],
        }
    
    # 3. 計算每個時間段的顧客活躍度
    labels = []
    activity_rates = []
    active_customers = []
    total_customers = []
    
    for period_info in time_periods:
        start_date = period_info['start']
        end_date = period_info['end']
        label = period_info['label']
        
        # 計算該期間內的總顧客數（截至期間結束）
        total_count = Customer.objects.filter(
            customerjoinday__lte=end_date
        ).count()
        
        # 計算該期間內活躍的顧客數
        # 使用 customerlastdaybuy 欄位來判斷活躍度
        active_count = Customer.objects.filter(
            customerjoinday__lte=end_date,
            customerlastdaybuy__gte=start_date,
            customerlastdaybuy__lte=end_date
        ).count()
        
        # 計算活躍率
        if total_count > 0:
            activity_rate = (active_count / total_count) * 100.0
        else:
            activity_rate = 0.0
        
        labels.append(label)
        activity_rates.append(round(activity_rate, 2))
        active_customers.append(active_count)
        total_customers.append(total_count)
    
    return {
        "period": period,
        "labels": labels,
        "activity_rates": activity_rates,
        "active_customers": active_customers,
        "total_customers": total_customers,
    }


def _get_time_periods(period: str, points: int, end_date: date):
    """
    生成時間週期列表
    """
    periods = []
    
    if period == "quarter":
        # 季度分析
        current_quarter_start = _quarter_start(end_date)
        
        for i in range(points):
            quarter_start = _shift_month(current_quarter_start, -i * 3)
            quarter_end = _shift_month(quarter_start, 3) - timedelta(days=1)
            
            periods.append({
                'start': quarter_start,
                'end': min(quarter_end, end_date) if i == 0 else quarter_end,
                'label': _quarter_label(quarter_start)
            })
        
        periods.reverse()  # 由舊到新排序
        
    elif period == "week":
        # 周分析
        # 找到當週的開始（週一）
        days_since_monday = end_date.weekday()
        current_week_start = end_date - timedelta(days=days_since_monday)
        
        for i in range(points):
            week_start = current_week_start - timedelta(weeks=i)
            week_end = week_start + timedelta(days=6)
            
            periods.append({
                'start': week_start,
                'end': min(week_end, end_date) if i == 0 else week_end,
                'label': f"第{points-i}周"
            })
        
        periods.reverse()  # 由舊到新排序
    
    return periods


def get_customer_growth(period: str = "month", points: int = 12):
    """
    計算「顧客成長率」折線圖用的資料。

    period:
        "month"   -> 以月份為一個點，例如 2025-01, 2025-02...
        "quarter" -> 以季度為一個點，例如 2025 Q1, 2025 Q2...

    points:
        要回傳幾個點（最近 N 個月 / 季）

    回傳格式（給前端 JS 用）：
    {
        "period": "month" | "quarter",
        "labels": [...],         # X 軸標籤（字串）
        "growth_rates": [...],   # 顧客成長率（% 數值，四捨五入兩位）
        "new_customers": [...],  # 每期間的新客數
        "totals": [...],         # 每期間結束時的累積顧客總數
    }

    顧客成長率定義：
        growth_rate = 當期新客數 / 期初顧客數 * 100
        - 若期初顧客數 = 0 且當期新客 = 0 -> 0%
        - 若期初顧客數 = 0 且當期新客 > 0 -> 100%
    """
    # 1. 參數整理
    period = (period or "month").lower()
    if period not in {"month", "quarter"}:
        period = "month"

    points = max(1, int(points or 1))

    # 2. 決定每一點代表幾個月、起始 anchor、標籤函式
    if period == "month":
        months_per_period = 1
        start_anchor = date.today().replace(day=1)      # 本月 1 號
        label_func = lambda d: d.strftime("%Y-%m")      # 例如 2025-03
    else:
        months_per_period = 3
        start_anchor = _quarter_start(date.today())     # 本季開頭
        label_func = _quarter_label                     # 例如 2025 Q1

    # 3. 把每個月份的新客數先算好
    month_counts = _collect_monthly_counts()

    # 4. 建 recent N 個期間的「起始日」列表 anchors
    anchors = []
    current = start_anchor
    for _ in range(points):
        anchors.append(current)
        current = _shift_month(current, -months_per_period)
    anchors.reverse()   # 由舊到新

    if not anchors:
        return {
            "period": period,
            "labels": [],
            "growth_rates": [],
            "new_customers": [],
            "totals": [],
        }

    # 5. 算第一個期間之前，系統已經累積多少顧客（當作初始底數）
    base_total = Customer.objects.filter(
        customerjoinday__lt=anchors[0]
    ).count()
    cumulative = base_total

    labels = []
    growth_rates = []
    new_counts = []
    totals = []

    # 6. 一期一期往後算
    for start in anchors:
        # (1) 這一期新客數 = 這一期涵蓋的月份加總
        new_count = 0
        for offset in range(months_per_period):
            month_key = _shift_month(start, offset)
            new_count += month_counts.get(month_key, 0)

        # (2) 成長率 = 新客 / 期初總數
        prev_total = cumulative
        cumulative += new_count   # 更新累積顧客數

        if prev_total:
            growth_rate = new_count / prev_total * 100.0
        else:
            growth_rate = 0.0 if new_count == 0 else 100.0

        # (3) 填入陣列
        labels.append(label_func(start))
        new_counts.append(new_count)
        totals.append(cumulative)
        growth_rates.append(round(growth_rate, 2))

    return {
        "period": period,
        "labels": labels,
        "growth_rates": growth_rates,
        "new_customers": new_counts,
        "totals": totals,
    }
