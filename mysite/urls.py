from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.http import JsonResponse

# 🔹 共用測試資料（首頁查詢 & 詳細頁共用）
TEST_MEMBERS = {
    "12345": {"id": "12345", "name": "Alice", "memberType": "高價值顧客"},
    "99999": {"id": "99999", "name": "Bob",   "memberType": "高風險顧客"},
    "55555": {"id": "55555", "name": "Cindy", "memberType": "新進顧客"},
}

# ===== 首頁用的測試 API（如果還要用就保留）=====
def member_api(request):
    member_id = request.GET.get("id", "").strip()

    if member_id in TEST_MEMBERS:
        return JsonResponse({"found": True, "customer": TEST_MEMBERS[member_id]})
    return JsonResponse({"found": False})


# ===== 會員詳細資料頁（做法 A）=====
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

urlpatterns = [
    path("admin/", admin.site.urls),
    path("",       lambda r: render(r, "login.html"),          name="login"),
    path("history/", lambda r: render(r, "history.html"),      name="history"),
    path("index/",   lambda r: render(r, "index.html"),        name="index"),
    path("ai-suggestion/", lambda r: render(r, "ai-suggestion.html"), name="ai"),

    path("api/member/", member_api),
    path("customer/",   customer_page, name="customer"),
]
