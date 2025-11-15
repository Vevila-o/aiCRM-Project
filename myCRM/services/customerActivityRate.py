from datetime import date
from calendar import monthrange
from django.db.models import Count
from django.db.models.functions import TruncMonth
from myCRM.models import Customer


# ========== 顧客成長率服務（折線圖） ==========

def _shift_month(base: date, offset: int) -> date:
  """
  Move a date forward/backward by offset months while clamping the day.
  """
  month_index = base.month - 1 + offset
  year = base.year + month_index // 12
  month = month_index % 12 + 1
  day = min(base.day, monthrange(year, month)[1])
  return base.replace(year=year, month=month, day=day)


def _quarter_start(base: date) -> date:
  quarter = (base.month - 1) // 3
  month = quarter * 3 + 1
  return base.replace(month=month, day=1)


def _quarter_label(start: date) -> str:
  quarter = (start.month - 1) // 3 + 1
  return f"{start.year} Q{quarter}"


def _collect_monthly_counts():
  """
  Returns a dict mapping month-start date -> new customer count.
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
    counts[month_dt.date()] = row["count"]
  return counts


def get_customer_growth(period: str = "month", points: int = 12):
  """
  Calculate customer growth for the last N periods (month or quarter).

  Returns:
  {
      "period": "month"|"quarter",
      "labels": [...],
      "growth_rates": [...],   # percent values
      "new_customers": [...],  # new customers per period
      "totals": [...],         # cumulative totals at end of period
  }
  """
  period = (period or "month").lower()
  if period not in {"month", "quarter"}:
    period = "month"
  points = max(1, points)

  if period == "month":
    months_per_period = 1
    start_anchor = date.today().replace(day=1)
    label_func = lambda d: d.strftime("%Y-%m")
  else:
    months_per_period = 3
    start_anchor = _quarter_start(date.today())
    label_func = _quarter_label

  month_counts = _collect_monthly_counts()
  anchors = []
  current = start_anchor
  for _ in range(points):
    anchors.append(current)
    current = _shift_month(current, -months_per_period)
  anchors.reverse()

  if not anchors:
    return {
      "period": period,
      "labels": [],
      "growth_rates": [],
      "new_customers": [],
      "totals": [],
    }

  base_total = Customer.objects.filter(customerjoinday__lt=anchors[0]).count()
  cumulative = base_total
  labels = []
  growth_rates = []
  new_counts = []
  totals = []

  for start in anchors:
    new_count = 0
    for offset in range(months_per_period):
      month_key = _shift_month(start, offset)
      new_count += month_counts.get(month_key, 0)

    prev_total = cumulative
    cumulative += new_count
    growth_rate = (new_count / prev_total * 100.0) if prev_total else (0.0 if new_count == 0 else 100.0)

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
