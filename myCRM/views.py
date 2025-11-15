from __future__ import annotations
import json
from django.http import HttpResponse, JsonResponse
from .services.test import test
from .services.churn_service import predict_churn, train_churn_model
from django.shortcuts import render, redirect
from django.urls import reverse
from myCRM.models import Transaction, RFMscore, Customer
from django.db.models import Count, Sum, Max
from datetime import datetime, timedelta
from .services.login import authenticate_user
from .services.login import create_user

#登入相關


# Create your views here.
#'''
# 測試檔案
# def test_test(requset):
#   result = test()
#   return HttpResponse(result)
# 
# '''




#首頁
def index_view(request):
  if not request.session.get('user_id'):
    return redirect('login')
  return render(request, 'index.html', {'username': request.session.get('username')})



  """顯示歷史頁面（需登入）。"""
def history_view(request):

  if not request.session.get('user_id'):
    return redirect('login')
  return render(request, 'history.html', {'username': request.session.get('username')})


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



# =============首頁測試檔案
# 🔹 共用測試資料（首頁查詢 & 詳細頁共用）
TEST_MEMBERS = {
    "12345": {"id": "12345", "name": "Alice", "memberType": "高價值顧客"},
    "99999": {"id": "99999", "name": "Bob",   "memberType": "高風險顧客"},
    "55555": {"id": "55555", "name": "Cindy", "memberType": "新進顧客"},
    }
    
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

    base = TEST_MEMBERS.get(member_id)
    if not base:
        return render(request, "customer.html", {"member": None})

    member = {
        "customerID": base["id"],
        "customerName": base["name"],
        "gender": "(不願透露)",
        "customerRegion": "(不願透露)",
        "memberType": base["memberType"],
        "customerJoinDay": "2025-11-11",
        "totalSpending": 87940,
        # 🔹 多筆消費紀錄，date 用 YYYY-MM-DD 方便排序
        "consumptions": [
            {
                "date": "2025-11-11",
                "amount": 500,
                "items": ["品項1", "品項2", "品項3"],
            },
            {
                "date": "2024-03-08",
                "amount": 1200,
                "items": ["耳機", "手機膜"],
            },
            {
                "date": "2023-12-25",
                "amount": 800,
                "items": ["聖誕節活動商品A", "活動商品B"],
            },
        ],
    }
    return render(request, "customer.html", {"member": member})

# ===== 首頁用的測試 API（如果還要用就保留）=====
def member_api(request):
    member_id = request.GET.get("id", "").strip()

    if member_id in TEST_MEMBERS:
        return JsonResponse({"found": True, "customer": TEST_MEMBERS[member_id]})
    return JsonResponse({"found": False})

#===========


#===============RFM分數計算=================
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

def calculate_rfm(request):
    #取得今天日期
    today=datetime.now()

    #計算rfm指標
    transactions=Transaction.objects.filter(transDate__lt=today).values('customerID').annotate(
        recency=Max('transDate'),
        frequency=Count('transactionID'),
        monetary=Sum('totalprice')
    )

    for t in transactions:
        #計算recency的天數（今天以前的消費日期）
        recency_days=(today-t['recency']).days
        recency_score=5 if recency_days<=30 else (4 if recency_days<=60 else (3 if recency_days<=90 else (2 if recency_days<=120 else 1)))
        
        #計算frequency數
        frequency=t['frequency']
        frequency_score=5 if frequency>=10 else (4 if frequency>=7 else (3 if frequency>=4 else (2 if frequency>=2 else 1)))
        
        #計算monetary
        monetary=t['monetary']
        monetary_score=5 if monetary>=1000 else (4 if monetary>=500 else (3 if monetary>=300 else (2 if monetary>=100 else 1)))
        
        #計算rfm的總分
        RFMscore_value=recency_score+frequency_score+monetary_score

        #判斷顧客類型
        customer_category_id=classify_customer(recency_score,frequency_score,monetary_score)

        #查詢RFMscore表來得到categoryID寫入Customer表
        try:
            rfm=RFMscore.objects.get(customerID=t['customerID'])
            categoryID=rfm.categoryID  #取RFMscore表的categoryID
        except RFMscore.DoesNotExist:
            categoryID=None  #如果RFMscore中沒有找到對應記錄 設為None

        #存RFM計算結果
        RFMscore.objects.update_or_create(
            customerID=t['customerID'],
            defaults={
                'rScore': recency_score,
                'fScore': frequency_score,
                'mScore': monetary_score,
                'RFMscore': RFMscore_value,
                'categoryID': customer_category_id,
                'RFMupdate':today
            }
        )
        
        #根據RFMscore的categoryID更新Customer表的categoryID
        if categoryID is not None:
            Customer.objects.filter(customerID=t['customerID']).update(categoryID=categoryID)

    #回傳所有結果到前端
    transactions=RFMscore.objects.all()
    return render(request,'rfm.html',{'transactions':transactions})



def churn_chart(request):
  """回傳一個 HTML 頁面，頁面會使用 Chart.js 呼叫 `/churn/` API 並繪製風險排行榜圖表。"""
  # 可接受 query params 並直接傳給 API
  return render(request, 'churn_chart.html')


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


##----------登入註冊相關頁面-----------



## 顧客活躍度

def customer_activity(request):
  """依據月/季/年區間統計顧客活躍度。"""
  today = datetime.now().date()
  period_key = request.GET.get("period", "month")
  if period_key not in ACTIVITY_PERIODS:
    period_key = "month"
  period_info = ACTIVITY_PERIODS[period_key]
  since_date = today - timedelta(days=period_info["days"])

  activity_queryset = (
    Transaction.objects
    .filter(transDate__gte=since_date, transDate__lte=today)
    .values("customerID")
    .annotate(
      last_purchase=Max("transDate"),
      orders=Count("transactionID"),
      total_spent=Sum("totalprice"),
    )
  )

  customer_ids = [row["customerID"] for row in activity_queryset]
  customer_lookup = Customer.objects.filter(customerID__in=customer_ids).in_bulk(field_name="customerID")

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

    customer = customer_lookup.get(row["customerID"])
    activities.append({
      "customer_id": row["customerID"],
      "customer_name": getattr(customer, "customername", "未知顧客"),
      "orders": orders,
      "total_spent": total_spent,
      "last_purchase": row["last_purchase"],
      "recency_days": recency_days,
      "activity_level": activity_level,
    })

  activities.sort(key=lambda x: (0 if x["activity_level"] == "高活躍" else (1 if x["activity_level"] == "中活躍" else 2),
                                 x["recency_days"] if x["recency_days"] is not None else 9999,
                                 -x["orders"]))

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
