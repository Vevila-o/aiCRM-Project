"""
URL 配置示例
將這些 URL 模式添加到您的主要 urls.py 文件中
"""

from django.urls import path
from analysis_views import (
    comprehensive_analysis_api,
    comprehensive_analysis_dashboard,
    category_analysis_api
)

# 綜合分析系統的 URL 模式
analysis_urlpatterns = [
    # API 端點
    path('api/comprehensive-analysis/', comprehensive_analysis_api, name='comprehensive_analysis_api'),
    path('api/category-analysis/<int:category_id>/', category_analysis_api, name='category_analysis_api'),
    
    # 儀表板頁面
    path('dashboard/comprehensive-analysis/', comprehensive_analysis_dashboard, name='comprehensive_analysis_dashboard'),
]

# 使用示例：
# 在您的主要 urls.py 中:
# 
# from django.contrib import admin
# from django.urls import path, include
# 
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', include(analysis_urlpatterns)),
#     # 其他 URL 模式...
# ]

# 或者直接添加到現有的 urlpatterns 中:
# urlpatterns += analysis_urlpatterns