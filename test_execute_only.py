#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
單獨測試執行建議 API
"""

import requests
import json

def test_execute_suggestion():
    """測試執行建議 API"""
    
    execute_url = "http://127.0.0.1:8000/ai-suggestion/execute/"
    
    execute_data = {
        "categoryID": 1,
        "guideline": "滿1000元8折優惠券｜開始時間:2025-12-01｜結束時間:2025-12-31",
        "outcome": "預期提升回購率15%，增加客單價200元",
        "userID": 1
    }
    
    try:
        print("測試執行建議 API...")
        response = requests.post(
            execute_url,
            json=execute_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"成功回應: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"錯誤回應: {response.text}")
            
    except Exception as e:
        print(f"測試失敗: {e}")

if __name__ == "__main__":
    test_execute_suggestion()