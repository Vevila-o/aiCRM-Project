#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試聊天功能的各個組件
"""

import os
import sys
import django
from pathlib import Path

# 設定 Django 環境
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiCRM.settings')

try:
    django.setup()
    print("✅ Django 環境設定成功")
except Exception as e:
    print(f"❌ Django 環境設定失敗: {e}")
    sys.exit(1)

def test_imports():
    """測試匯入是否正常"""
    print("\n=== 測試匯入 ===")
    
    try:
        from django.conf import settings
        print(f"✅ Django 設定載入成功")
        
        # 測試 OpenAI API 金鑰
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if api_key:
            print(f"✅ OpenAI API 金鑰已設定 (長度: {len(api_key)})")
        else:
            print("❌ OpenAI API 金鑰未設定")
            
    except Exception as e:
        print(f"❌ 設定載入失敗: {e}")
    
    try:
        from openai import OpenAI
        print("✅ OpenAI 套件匯入成功")
    except Exception as e:
        print(f"❌ OpenAI 套件匯入失敗: {e}")
    
    try:
        from myCRM.models import Customer, RFMScore, ChatRecord
        print("✅ Django 模型匯入成功")
    except Exception as e:
        print(f"❌ Django 模型匯入失敗: {e}")
    
    try:
        from myCRM.services.ai_suggestion_service import get_comprehensive_customer_analysis
        print("✅ AI 建議服務匯入成功")
    except Exception as e:
        print(f"❌ AI 建議服務匯入失敗: {e}")

def test_database():
    """測試資料庫連接"""
    print("\n=== 測試資料庫連接 ===")
    
    try:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        print("✅ 資料庫連接成功")
    except Exception as e:
        print(f"❌ 資料庫連接失敗: {e}")
        return False
    
    try:
        from myCRM.models import Customer
        customer_count = Customer.objects.count()
        print(f"✅ 客戶資料查詢成功 (共 {customer_count} 筆)")
    except Exception as e:
        print(f"❌ 客戶資料查詢失敗: {e}")
        return False
        
    return True

def test_openai_connection():
    """測試 OpenAI API 連接"""
    print("\n=== 測試 OpenAI API 連接 ===")
    
    try:
        from django.conf import settings
        from openai import OpenAI
        
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # 測試簡單的 API 調用
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Hello, can you respond with just 'OK'?"}
            ],
            max_tokens=10
        )
        
        reply = response.choices[0].message.content.strip()
        print(f"✅ OpenAI API 連接成功，回應: '{reply}'")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI API 連接失敗: {e}")
        return False

def test_comprehensive_analysis():
    """測試綜合分析功能"""
    print("\n=== 測試綜合分析功能 ===")
    
    try:
        from myCRM.services.ai_suggestion_service import get_comprehensive_customer_analysis
        
        # 測試分析功能
        analysis = get_comprehensive_customer_analysis()
        
        if analysis and 'statistics' in analysis:
            stats = analysis['statistics']
            print(f"✅ 綜合分析成功")
            print(f"   - 總客戶數: {stats.get('total_customers', 'N/A')}")
            print(f"   - 總收入: {stats.get('total_revenue', 'N/A')}")
            print(f"   - 活躍率: {stats.get('activity_rate', 'N/A')}")
            return True
        else:
            print("❌ 綜合分析回傳資料格式錯誤")
            return False
            
    except Exception as e:
        print(f"❌ 綜合分析失敗: {e}")
        return False

def main():
    print("🚀 開始測試聊天系統組件...")
    
    # 測試各個組件
    test_imports()
    
    if not test_database():
        print("\n💥 資料庫測試失敗，停止後續測試")
        return
    
    if not test_openai_connection():
        print("\n💥 OpenAI API 測試失敗，停止後續測試")
        return
        
    if not test_comprehensive_analysis():
        print("\n💥 綜合分析測試失敗")
        return
    
    print("\n🎉 所有組件測試通過！聊天系統應該可以正常運作。")

if __name__ == "__main__":
    main()