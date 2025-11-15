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

urlpatterns = [
    path('admin/', admin.site.urls),
    #path('test/', test_test),  #測試
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('history/', views.history_view, name='history'),
    path("index/",   views.index_view,        name="index"), #首頁
    path("ai-suggestion/", lambda r: render(r, "ai-suggestion.html"), name="ai"), #AI建議
    path('calculate_rfm/', views.calculate_rfm, name='calculate_rfm'), #RFM計算
    path('rfm/update/', views.trigger_rfm_update, name='rfm_update'), #manual RFM refresh
    path("customer/",   views.customer_page, name="customer") ,#顧客詳細頁面
    path('churn/', views.churn_predictions), #流失測API
    path('churn/chart/', views.churn_chart), #流失測表API
    path('churn/train/', views.churn_train), #流失測訓練API
    path('activity/', views.customer_activity, name='customer_activity'), #顧客活動
    path("api/member/", views.member_api), ## 顧客測試資料
   
]
