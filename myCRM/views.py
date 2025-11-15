from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User #django內建的User
from django.contrib import messages
from django.http import HttpResponse
from .services.test import test

#登入後會來這裡
@login_required
def home_view(request):
    return render(request, 'index.html')

#登入
#前端表單的帳號欄位 name="username" 帳號是員工編號employeeID
# 註冊時把employeeID存進django的User.username  authenticate()用username=employeeID來登入
#負責登入驗證 session 權限的是django內建auth_user表 

#登入畫面與處理
def login_view(request):
    if request.method == 'POST':
        login_account = request.POST.get('username')  # 表單欄位 name="username"->員工編號
        password = request.POST.get('password')  # 表單欄位 name="password"

        # 檢查帳號密碼是否輸入
        if not login_account or not password:
            return render(request, 'login.html', {
                'error': '請輸入帳號與密碼',
                'username': login_account,
            })

        user = authenticate(request, username=login_account, password=password) # 用django內建的User做驗證 username ->employeeID
        if user is not None:
            login(request, user)  # 建立session
            return redirect('index')  #登入成功回首頁
        else:
            # 登入失敗回傳錯誤訊息
            return render(request, 'login.html', {
                'error': '帳號或密碼錯誤'
            })

    # GET顯示登入畫面
    return render(request, 'login.html')

@login_required
def index_view(request):
    return render(request, 'index.html')

#登出
def logout_view(request):
    logout(request)
    return redirect('login')

#註冊
#把employeeID存進username 之後登入就用employeeID當帳號


def register_view(request):
    if request.method == 'POST':
        
        employee_id = request.POST.get('employeeID')   # 員工編號
        username = request.POST.get('username')        # 使用者名稱
        password = request.POST.get('password') # 密碼
        confirm_password = request.POST.get('confirm_password') # 確認密碼

        errors = []

        #基本檢查
        if not employee_id or not username or not password or not confirm_password:
            errors.append("所有欄位都必須填寫")
            
        if password != confirm_password:
            errors.append("兩次輸入的密碼不一樣")

        #檢查django內建User-用employeeID當登入帳號
        if User.objects.filter(username=employee_id).exists():
            errors.append("這個員工編號已經註冊過了")
            
        #員工編號必須是純數字
        if not employee_id.isdigit():
            errors.append("員工編號只能輸入數字。") 

        if errors:
            return render(request, 'register.html', {
                'errors': errors,
                'employeeID': employee_id,
                'username': username,
            })

        #建django的User 用employeeID當登入帳號
        django_user = User.objects.create_user(
            username=employee_id,   #登入時輸入的就是employeeID
            password=password,
            first_name=username     #把userName存在first_name用來顯示
        )


        messages.success(request, "註冊成功！請使用您的帳號登入。")

        # 註冊完導去登入頁
        return redirect('login')

    # GET顯示註冊畫面
    return render(request, 'register.html')
