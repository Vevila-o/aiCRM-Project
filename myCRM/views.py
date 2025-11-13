from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .services.test import test
from .services.churn_service import predict_churn, train_churn_model

# Create your views here.
#'''
# 測試檔案
# def test_test(requset):
#   result = test()
#   return HttpResponse(result)
# 
# '''



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


def homePage(request):
  return render(request,'index.html')


def churn_chart(request):
  """回傳一個 HTML 頁面，頁面會使用 Chart.js 呼叫 `/churn/` API 並繪製風險排行榜圖表。"""
  # 可接受 query params 並直接傳給 API
  return render(request, 'churn_chart.html')
