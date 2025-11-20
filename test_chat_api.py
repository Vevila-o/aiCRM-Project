#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試聊天 API 的 HTTP 500 錯誤問題
"""

import requests
import json
import sys

def test_chat_api():
    """測試聊天 API"""
    
    # API 端點
    chat_url = "http://127.0.0.1:8000/chat/"
    init_url = "http://127.0.0.1:8000/ai-suggestion/init/"
    
    print("=== 測試聊天系統 API ===")
    
    # 1. 測試初始化 API
    print("\n1. 測試 AI 建議初始化 API...")
    try:
        params = {"categoryID": 1, "period": "month"}
        response = requests.get(init_url, params=params)
        print(f"   狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   回應資料: {json.dumps(data, ensure_ascii=False, indent=2)[:200]}...")
        else:
            print(f"   錯誤回應: {response.text[:500]}")
            
    except Exception as e:
        print(f"   初始化 API 錯誤: {e}")
    
    # 2. 測試聊天 API
    print("\n2. 測試聊天 API...")
    try:
        chat_data = {
            "message": "你好，請推薦一些優惠券給忠誠客戶",
            "categoryID": 1,
            "userID": 1
        }
        
        response = requests.post(
            chat_url, 
            json=chat_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   回應資料: {json.dumps(data, ensure_ascii=False, indent=2)[:300]}...")
        else:
            print(f"   錯誤回應: {response.text[:500]}")
            
    except Exception as e:
        print(f"   聊天 API 錯誤: {e}")
    
    # 3. 測試執行建議 API
    print("\n3. 測試執行建議 API...")
    try:
        execute_url = "http://127.0.0.1:8000/ai-suggestion/execute/"
        execute_data = {
            "categoryID": 1,
            "guideline": "測試優惠券建議",
            "outcome": "測試預期成果",
            "userID": 1
        }
        
        response = requests.post(
            execute_url,
            json=execute_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   回應資料: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"   錯誤回應: {response.text[:500]}")
            
    except Exception as e:
        print(f"   執行建議 API 錯誤: {e}")

if __name__ == "__main__":
    test_chat_api()