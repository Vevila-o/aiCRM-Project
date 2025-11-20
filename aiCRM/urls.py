"""

URL configuration for aiCRM project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/

Examples:
Function views
    1. Add an import:  from my_app import views

    2. Add a URL to urlpatterns:  path('', views.home, name='home')

Class-based views
    1. Add an import:  from other_app.views import Home

    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')

Including another URLconf

    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

"""
from django.contrib import admin
from django.urls import path, include
from myCRM import views
from django.shortcuts import render, redirect
from django.http import JsonResponse
from myCRM.services import chat_views




urlpatterns = [
    path('admin/', admin.site.urls),
    #path('test/', test_test),  #測試
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('history/', views.history_view, name='history'),
    path("index/",   views.index_view,        name="index"), #首頁
    path('calculate_rfm/', views.calculate_rfm, name='calculate_rfm'), #RFM計算
    path('rfm/update/', views.trigger_rfm_update, name='rfm_update'), #manual RFM refresh
    path("customer/",   views.customer_page, name="customer") ,#顧客詳細頁面
    path('churn/', views.churn_predictions), #流失測API
    path('churn/chart/', views.churn_chart), #流失測表API
    path('churn/train/', views.churn_train), #流失測訓練API
    path('next-purchase/chart/', views.next_purchase_chart, name='next_purchase_chart'), #下次購買預測圖表
    path('next-purchase/', views.next_purchase_predictions), #下次購買預測API
    path('next-purchase/single/', views.next_purchase_single), #單一客戶下次購買預測
    path('next-purchase/train/', views.next_purchase_train), #下次購買模型訓練
    path('activity/', views.customer_activity, name='customer_activity'), #顧客活動
    path("api/member/", views.member_api), ## 顧客測試資料
    path("api/customer-growth/", views.customer_growth_api, name="customer_growth_api"),
    path('chat/', chat_views.chat, name='chat'),  # AI聊天機器人
    path("ai-suggestion/", views.ai_suggestion_page, name="ai_suggestion"), #AI建議
    path("ai-suggestion/init/", chat_views.ai_suggestion_init, name="ai_suggestion_init"), #AI建議初始化
    path("ai-suggestion/execute/", chat_views.execute_suggestion, name="execute_suggestion"), #執行AI建議
    
    ]