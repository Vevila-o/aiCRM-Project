"""
Django Views for 綜合客戶分析系統

使用方法:
1. 在 urls.py 中添加路由
2. 訪問對應的 URL 來獲取分析結果
"""

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from myCRM.services.ai_suggestion_service import get_comprehensive_customer_analysis

@require_http_methods(["GET"])
def comprehensive_analysis_api(request):
    """
    API 端點：獲取綜合客戶分析結果
    
    參數：
    - category_id (可選): 特定客群ID
    - top_customers (可選): 要分析的客戶數量，默認20
    
    返回：JSON格式的綜合分析報告
    """
    try:
        # 獲取請求參數
        category_id = request.GET.get('category_id')
        top_customers = int(request.GET.get('top_customers', 20))
        
        # 轉換category_id為整數（如果提供）
        if category_id:
            category_id = int(category_id)
        
        # 執行綜合分析
        analysis_result = get_comprehensive_customer_analysis(
            category_id=category_id,
            top_customers=top_customers
        )
        
        return JsonResponse({
            'success': True,
            'data': analysis_result
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def comprehensive_analysis_dashboard(request):
    """
    儀表板頁面：展示綜合客戶分析結果
    """
    try:
        # 獲取綜合分析結果
        analysis_result = get_comprehensive_customer_analysis(top_customers=15)
        
        # 準備模板上下文
        context = {
            'analysis_data': analysis_result,
            'total_customers': analysis_result['rfm_analysis']['total_customers'],
            'churn_summary': analysis_result['churn_analysis'],
            'growth_data': analysis_result['growth_analysis'],
            'activity_data': analysis_result['activity_analysis'],
            'consumption_stats': analysis_result['consumption_statistics']
        }
        
        return render(request, 'comprehensive_analysis_dashboard.html', context)
        
    except Exception as e:
        return render(request, 'error.html', {
            'error_message': f'分析過程中發生錯誤: {str(e)}'
        })


@require_http_methods(["GET"])
def category_analysis_api(request, category_id):
    """
    API 端點：獲取特定客群的詳細分析
    
    參數：
    - category_id: 客群ID (URL參數)
    - top_customers (可選): 要分析的客戶數量，默認10
    """
    try:
        top_customers = int(request.GET.get('top_customers', 10))
        
        # 執行特定客群分析
        analysis_result = get_comprehensive_customer_analysis(
            category_id=category_id,
            top_customers=top_customers
        )
        
        # 提取特定客群的分析結果
        category_analysis = analysis_result.get('category_specific_analysis')
        
        if not category_analysis:
            return JsonResponse({
                'success': False,
                'error': f'找不到客群 ID {category_id} 的分析結果'
            }, status=404)
        
        return JsonResponse({
            'success': True,
            'data': {
                'category_analysis': category_analysis,
                'general_stats': {
                    'total_customers': analysis_result['rfm_analysis']['total_customers'],
                    'average_churn_probability': analysis_result['churn_analysis']['average_churn_probability']
                }
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# 使用示例的輔助函數
def get_analysis_summary(category_id=None):
    """
    輔助函數：獲取分析摘要
    可在其他視圖或模板中使用
    """
    try:
        analysis = get_comprehensive_customer_analysis(category_id=category_id, top_customers=10)
        
        summary = {
            'total_customers': analysis['rfm_analysis']['total_customers'],
            'high_risk_customers': analysis['churn_analysis']['high_risk_count'],
            'churn_rate': analysis['churn_analysis']['average_churn_probability'],
            'recent_activity_rate': analysis['consumption_statistics']['recent_activity_rate'],
            'total_revenue': analysis['consumption_statistics']['total_revenue']
        }
        
        if category_id and analysis.get('category_specific_analysis'):
            cat_data = analysis['category_specific_analysis']
            summary.update({
                'category_name': cat_data['category_name'],
                'category_customers': cat_data['total_customers_in_category'],
                'category_churn_rate': cat_data['churn_analysis']['average_churn_probability'],
                'customers_buying_soon': len(cat_data['next_purchase_analysis']['customers_buying_soon'])
            })
        
        return summary
        
    except Exception as e:
        return {'error': str(e)}


# 模板上下文處理器 (可在 settings.py 中註冊)
def analysis_context_processor(request):
    """
    上下文處理器：為所有模板提供基本的分析統計
    """
    try:
        summary = get_analysis_summary()
        return {
            'global_analysis_summary': summary
        }
    except:
        return {
            'global_analysis_summary': {}
        }