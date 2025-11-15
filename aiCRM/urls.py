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
from django.http import HttpResponse
from myCRM import views
from django.shortcuts import render, redirect
from django.http import JsonResponse

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')), #引引入用戶認證相關的URL
    path('',views.index_view, name='index'), #首頁
    path("history/", lambda r: render(r, "history.html"), name="history"), #歷史
    path("ai-suggestion/", lambda r: render(r, "ai-suggestion.html"), name="ai"), #AI建議
    #path("api/member/", member_api),
    #path("customer/",   customer_page, name="customer"),
    path('login/', views.login_view, name='login'),# 登入
    path('logout/', views.logout_view, name='logout'),# 登出
    path('register/', views.register_view, name='register'),
]
