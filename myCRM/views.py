from __future__ import annotations
import json
from collections import defaultdict
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from .services.test import test
from .services.churn_service import predict_churn, train_churn_model
from django.shortcuts import render, redirect
from django.urls import reverse
from myCRM.models import (
  Transaction,
  TransactionDetail,
  Product,
  RFMscore,
  Customer,
  CustomerCategory,
)
from django.db.models import Count, Sum, Max,Q
from datetime import datetime, timedelta
from .services.login import authenticate_user
from .services.login import create_user
from .services.customerActivityRate import get_customer_growth
from .services.rfm_count import recalc_rfm_scores, get_rfm_category_distribution
from django.views.decorators.http import require_POST, require_GET
from .services.basicRate import calculate_CRR, calculate_RPR, calculate_vip_ratio, calculate_allCus


# Create your views here.

# 小工具：比例格式化（0~1 轉百分比字串）
def _format_rate(raw_value):
    """
    把 0~1 的比例轉成 xx.xx%，也容錯 raw_value 是 None 或字串。
    回傳 (原始數值, 格式化字串或 None)
    """
    if raw_value is None:
        return None, None

    try:
        v = float(raw_value)
    except (TypeError, ValueError):
        return raw_value, str(raw_value)

    # 0~1 視為比例，乘以 100 變成百分比
    if 0 <= v <= 1:
        return v, f"{v * 100:.2f}%"

    # 其他情況就當作已經是百分比數值（例如 85.3）
    return v, f"{v:.2f}%"


def index_view(request):
    if not request.session.get('user_id'):
        return redirect('login')

    # === 顧客留存率 CRR ===
    try:
        crr_raw = calculate_CRR()
    except Exception:
        crr_raw = None
    crr_value, crr_display = _format_rate(crr_raw)

    # === 顧客回購率 RPR ===
    try:
        rpr_raw = calculate_RPR()
    except Exception:
        rpr_raw = None
    rpr_value, rpr_display = _format_rate(rpr_raw)

    # === 高價值顧客佔比 ===
    try:
        vip_raw = calculate_vip_ratio()
    except Exception:
        vip_raw = None
    vip_value, vip_display = _format_rate(vip_raw)

    # === 總顧客數 ===
    try:
        total_customers = calculate_allCus() or 0
    except Exception:
        total_customers = 0

    # === 圓餅圖：RFM 分群分布 ===
    try:
        # 可以排除「其他客戶」，也可以傳空陣列就全部顯示
        dist = get_rfm_category_distribution(exclude_labels=["其他客戶"])
        # dist = {"labels": [...], "counts": [...], "total": n}
    except Exception:
        dist = {"labels": [], "counts": [], "total": 0}

    label_to_count = {
        label: count
        for label, count in zip(dist.get("labels", []), dist.get("counts", []))
    }

    # 這裡的名稱要跟實際 CustomerCategory.customercategory 一致
    desired_labels = [
        "忠誠客戶",
        "潛在高價值顧客",
        "普通顧客",
        "沉睡顧客",
        "潛在流失顧客",
        "低價值顧客",
        "新顧客"
    ]

    segments = [label_to_count.get(lbl, 0) for lbl in desired_labels]

    #丟給前端 JS 用的資料
    dashboard_data = {
        # ⚠ 這裡修正對應：
        #   repurchaseRate → 留存率（CRR）
        #   churnRate      → 回購率（RPR）
        "repurchaseRate": crr_value or 0.0,    # 給「本月顧客留存率」用
        "churnRate":      rpr_value or 0.0,    # 給「本月顧客回購率」用
        "vipRatio":       vip_value or 0.0,    # 高價值顧客佔比
        "totalCustomers": total_customers,
        "segments":       segments,
        "segmentLabels":  desired_labels,
        "forecast":       [50, 80, 120, 170],  # 先給假資料
    }

    return render(request, "index.html", {
        "username": request.session.get("username"),

        # 顯示在卡片上的字串
        "crr":        crr_display,
        "rpr":        rpr_display,
        "vip_ratio":  vip_display,
        "total_customers": total_customers,

        # 給 main.js 用的 JSON
        "dashboard_data_json": json.dumps(dashboard_data, ensure_ascii=False),
    })

# 歷史頁面
def history_view(request):
  if not request.session.get('user_id'):
    return redirect('login')
  return render(request, 'history.html', {'username': request.session.get('username')})


# rfm分數計算
def calculate_rfm(request):
  """
  呼叫 service 重新計算 RFM，然後把結果丟到 rfm.html 顯示。
  """
  transactions = recalc_rfm_scores()
  return render(request, 'rfm.html', {'transactions': transactions})


# 顧客本月留存率（若有另外做按鈕可以用這個 view 直接導回首頁）
def calculate_crr(request):
  """
  呼叫 service 計算本月顧客留存率，實際顯示交給首頁 index_view 處理。
  """
  # 計算會在 index_view 裡重新做，這裡只做導回首頁即可避免重複模板邏輯
  return redirect('index')


# 本月顧客回購率
def calculate_rpr(request):
  """
  呼叫 service 計算本月顧客回購率，實際顯示交給首頁 index_view 處理。
  """
  return redirect('index')


# 高價值顧客佔比
def calculate_vip_ratio_view(request):
  """
  呼叫 service 計算高價值顧客佔比，實際顯示交給首頁 index_view 處理。
  """
  return redirect('index')

# 全部顧客人數
def calculate_allCus_view(request):
  return redirect('index')


## 測試流失圖
def churn_chart(request):
  """回傳一個 HTML 頁面，頁面會使用 Chart.js 呼叫 `/churn/` API 並繪製風險排行榜圖表。"""
  # 可接受 query params 並直接傳給 API
  return render(request, 'churn_chart.html')


## =============流失預測相關API=================
def churn_predictions(request):
  use_recency_param = request.GET.get('use_recency', 'false').lower()
  use_recency = use_recency_param in ('1', 'true', 'yes', 'y')
  try:
    window_days = int(request.GET.get('window_days', 365))
  except Exception:
    window_days = 365

  as_of = request.GET.get('as_of')  # ISO 格式 yyyy-mm-dd，可選

  try:
    # 如果 predict_churn 有支援 use_recency，可以改成傳入 use_recency=use_recency
    results = predict_churn(as_of=as_of, window_days=window_days)
    return JsonResponse({
      "count": len(results),
      "results": results
    }, json_dumps_params={"ensure_ascii": False})
  except Exception as e:
    return JsonResponse({"error": str(e)}, status=500)


def churn_train(request):
  try:
    window_days = int(request.GET.get('window_days', 365))
  except Exception:
    window_days = 365

  churn_threshold_days = int(request.GET.get('churn_threshold_days', 150))
  iterations = int(request.GET.get('iterations', 300))
  depth = int(request.GET.get('depth', 6))
  learning_rate = float(request.GET.get('learning_rate', 0.1))
  as_of = request.GET.get('as_of')  # ISO 格式 yyyy-mm-dd，可選

  try:
    use_recency_param = request.GET.get('use_recency', 'false').lower()
    use_recency = use_recency_param in ('1', 'true', 'yes', 'y')

    info = train_churn_model(
      as_of=as_of,
      window_days=window_days,
      churn_threshold_days=churn_threshold_days,
      iterations=iterations,
      depth=depth,
      learning_rate=learning_rate,
      use_recency=use_recency,
    )
    return JsonResponse(info, json_dumps_params={"ensure_ascii": False})
  except Exception as e:
    return JsonResponse({"error": str(e)}, status=500)

# 顧客成長率
@require_GET
def customer_growth_api(request):
  raw_period = (request.GET.get("period") or "month").lower()
  period = raw_period if raw_period in {"month", "quarter"} else "month"
  default_points = 12 if period == "month" else 8
  try:
    points = int(request.GET.get("points", default_points))
  except (TypeError, ValueError):
    points = default_points

  max_points = 24 if period == "month" else 12
  points = max(1, min(points, max_points))
  data = get_customer_growth(period=period, points=points)
  return JsonResponse(data, json_dumps_params={"ensure_ascii": False})




# =============首頁測試檔案
# 🔹 共用測試資料（首頁查詢 & 詳細頁共用）

ACTIVITY_PERIODS = {
  "month": {"label": "近 1 個月", "days": 30},
  "quarter": {"label": "近 1 季", "days": 90},
  "year": {"label": "近 1 年", "days": 365},
}

#===========顧客詳細頁面===========

def customer_page(request):
  member_id = request.GET.get("id", "").strip()

  if not member_id:
    return redirect("index")

  try:
    member_id_int = int(member_id)
  except ValueError:
    return render(request, "customer.html", {"member": None})

  try:
    customer = Customer.objects.get(customerid=member_id_int)
  except Customer.DoesNotExist:
    return render(request, "customer.html", {"member": None})

  category_name = "未分級"
  if customer.categoryid is not None:
    category = CustomerCategory.objects.filter(categoryid=customer.categoryid).first()
    if category and category.customercategory:
      category_name = category.customercategory

  transactions_qs = Transaction.objects.filter(customerid=customer.customerid).order_by("-transdate")
  total_spending = transactions_qs.aggregate(total=Sum("totalprice")).get("total") or 0
  transactions = list(transactions_qs)
  transaction_ids = [t.transactionid for t in transactions if t.transactionid is not None]

  detail_map: dict[int, list[str]] = defaultdict(list)
  if transaction_ids:
    details = list(TransactionDetail.objects.filter(transactionid__in=transaction_ids))
    product_ids = {d.productid for d in details if d.productid is not None}
    product_lookup = {}
    if product_ids:
      product_lookup = {
        p.productid: (p.productname or f"商品 {p.productid}")
        for p in Product.objects.filter(productid__in=product_ids)
      }

    for detail in details:
      item_name = product_lookup.get(detail.productid)
      if not item_name:
        item_name = f"商品 {detail.productid}" if detail.productid else "未知商品"
      if detail.transactionid is not None:
        detail_map[detail.transactionid].append(item_name)

  consumptions = []
  for txn in transactions:
    consumptions.append(
      {
        "date": txn.transdate.strftime("%Y-%m-%d") if txn.transdate else "",
        "amount": txn.totalprice or 0,
        "items": detail_map.get(txn.transactionid, []),
      }
    )

  member = {
    "customerID": customer.customerid,
    "customerName": customer.customername or "",
    "gender": customer.gender or "",
    "customerRegion": customer.customerregion or "",
    "memberType": category_name,
    "customerJoinDay": customer.customerjoinday.strftime("%Y-%m-%d") if customer.customerjoinday else "",
    "totalSpending": total_spending,
    "consumptions": consumptions,
  }
  return render(request, "customer.html", {"member": member})


# ===========顧客編號查詢===========
def member_api(request):
  member_id = request.GET.get("id", "").strip()
  if not member_id:
    return JsonResponse({"found": False, "error": "缺少會員編號"}, status=400)

  try:
    member_id_int = int(member_id)
  except ValueError:
    return JsonResponse({"found": False, "error": "會員編號格式錯誤"}, status=400)

  try:
    customer = Customer.objects.get(customerid=member_id_int)
  except Customer.DoesNotExist:
    return JsonResponse({"found": False})

  category_name = "未分級"
  if customer.categoryid is not None:
    category = CustomerCategory.objects.filter(categoryid=customer.categoryid).first()
    if category and category.customercategory:
      category_name = category.customercategory

  total_spending = (
    Transaction.objects.filter(customerid=customer.customerid).aggregate(total=Sum("totalprice")).get("total") or 0
  )

  member = {
    "customerID": customer.customerid,
    "customerName": customer.customername or "",
    "gender": customer.gender or "",
    "customerRegion": customer.customerregion or "",
    "memberType": category_name,
    "customerJoinDay": customer.customerjoinday.strftime("%Y-%m-%d") if customer.customerjoinday else "",
    "totalSpending": total_spending,
  }
  return JsonResponse({"found": True, "customer": member})


##----------登入註冊相關頁面-----------
def _should_return_json(request):
  accept = (request.headers.get('Accept') or '').lower()
  return request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in accept


def _login_error(message, request, username):
  if _should_return_json(request):
    return JsonResponse({'success': False, 'message': message}, status=400)
  return render(request, 'login.html', {'error': message, 'username': username}, status=400)


def login_view(request):
  if request.method == 'GET':
    if request.GET.get('logout') == '1':
      request.session.flush()
    elif request.session.get('user_id'):
      return redirect('index')
    return render(request, 'login.html')

  if request.content_type and 'application/json' in request.content_type:
    try:
      payload = json.loads(request.body.decode('utf-8'))
    except Exception:
      payload = {}
  else:
    payload = request.POST

  username = (payload.get('username') or '').strip()
  password = payload.get('password') or ''

  if not username or not password:
    return _login_error('請輸入帳號與密碼', request, username)

  user = authenticate_user(username, password)
  if not user:
    return _login_error('帳號或密碼錯誤', request, username)

  request.session['user_id'] = user.userid
  request.session['username'] = user.username or username

  if _should_return_json(request):
    return JsonResponse({'success': True, 'redirect': reverse('index')})

  return redirect('index')


def logout_view(request):
  """登出：清空 session 並導回登入頁。"""
  request.session.flush()
  return redirect('login')


def register_view(request):
  """使用者註冊視圖：支持表單與 JSON。"""
  if request.method == 'GET':
    return render(request, 'register.html')

  # 解析 payload（JSON 或表單）
  if request.content_type and 'application/json' in request.content_type:
    try:
      payload = json.loads(request.body.decode('utf-8'))
    except Exception:
      payload = {}
  else:
    payload = request.POST

  username = (payload.get('username') or '').strip()
  password = payload.get('password') or ''
  password_confirm = payload.get('password_confirm') or ''

  if not username or not password:
    return render(request, 'register.html', {'error': '請輸入帳號與密碼', 'username': username}, status=400)

  if password != password_confirm:
    return render(request, 'register.html', {'error': '密碼與確認密碼不一致', 'username': username}, status=400)

  user, err = create_user(username, password)
  if not user:
    # 若服務端回傳明確訊息就顯示，否則使用通用錯誤
    message = err or '無法建立使用者，請聯絡管理員'
    return render(request, 'register.html', {'error': message, 'username': username}, status=400)

  # 自動登入
  request.session['user_id'] = user.userid
  request.session['username'] = user.username
  context = {
    'success': True,
    'success_message': '註冊成功，將自動前往首頁',
    'redirect_url': reverse('login'),
    'username': user.username,
  }
  return render(request, 'register.html', context)




## 顧客活躍度

def customer_activity(request):
  """依據月/季/年區間統計顧客活躍度。"""
  today = datetime.now().date()
  period_key = request.GET.get("period", "month")
  if period_key not in ACTIVITY_PERIODS:
    period_key = "month"
  period_info = ACTIVITY_PERIODS[period_key]
  since_date = today - timedelta(days=period_info["days"])

  #  欄位名稱統一使用與其他地方一致的小寫命名

  activity_queryset = (
    Transaction.objects
    .filter(transdate__gte=since_date, transdate__lt=today)
    .values("customerid")
    .annotate(
      last_purchase=Max("transdate"),
      orders=Count("transactionid"),
      total_spent=Sum("totalprice"),
    )
  )

  customer_ids = [row["customerid"] for row in activity_queryset]
  customer_lookup = Customer.objects.filter(customerid__in=customer_ids).in_bulk(field_name="customerid")

  activities = []
  high = medium = low = 0
  for row in activity_queryset:
    recency_days = (today - row["last_purchase"]).days if row["last_purchase"] else None
    orders = row["orders"]
    total_spent = row["total_spent"] or 0
    if recency_days is not None and recency_days <= 14 and orders >= 3:
      activity_level = "高活躍"
      high += 1
    elif recency_days is not None and recency_days <= 45 and orders >= 2:
      activity_level = "中活躍"
      medium += 1
    else:
      activity_level = "低活躍"
      low += 1

    customer = customer_lookup.get(row["customerid"])
    activities.append({
      "customer_id": row["customerid"],
      "customer_name": getattr(customer, "customername", "未知顧客"),
      "orders": orders,
      "total_spent": total_spent,
      "last_purchase": row["last_purchase"],
      "recency_days": recency_days,
      "activity_level": activity_level,
    })

  activities.sort(
    key=lambda x: (
      0 if x["activity_level"] == "高活躍"
      else (1 if x["activity_level"] == "中活躍" else 2),
      x["recency_days"] if x["recency_days"] is not None else 9999,
      -x["orders"],
    )
  )

  period_options = [{"key": key, "label": info["label"]} for key, info in ACTIVITY_PERIODS.items()]

  context = {
    "period_key": period_key,
    "period_label": period_info["label"],
    "period_options": period_options,
    "since_date": since_date,
    "today": today,
    "activities": activities,
    "high_count": high,
    "medium_count": medium,
    "low_count": low,
    "total_count": len(activities),
  }
  return render(request, "customer_activity.html", context)


## =============RFM手動更新API=================
@require_POST
def trigger_rfm_update(request):
  """
  Manual trigger for recomputing RFM scores; requires login.
  """
  if not request.session.get('user_id'):
    return redirect('login')

  try:
    updated_qs = recalc_rfm_scores()
    messages.success(request, f"RFM scores updated ({updated_qs.count()} records).")
  except Exception as exc:
    messages.error(request, f"RFM update failed: {exc}")

  return redirect('index')
