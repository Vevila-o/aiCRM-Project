"""
測試下次購買預測 API 的 JSON 序列化
"""

import os
import django
import json

# Django 設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiCRM.settings')
django.setup()

from myCRM.services.next_purchse import predict_next_purchase_time, predict_next_purchase_batch

def test_single_prediction():
    """測試單一客戶預測的 JSON 序列化"""
    print("=" * 60)
    print("測試單一客戶預測")
    print("=" * 60)
    
    try:
        # 預測客戶 141
        result = predict_next_purchase_time(141)
        
        # 嘗試 JSON 序列化
        json_str = json.dumps(result, ensure_ascii=False)
        print("✅ JSON 序列化成功！")
        print(f"\n結果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 檢查資料類型
        print(f"\n資料類型檢查:")
        for key, value in result.items():
            print(f"  {key}: {type(value).__name__} = {value}")
        
    except TypeError as e:
        print(f"❌ JSON 序列化失敗: {e}")
    except Exception as e:
        print(f"❌ 預測失敗: {e}")


def test_batch_prediction():
    """測試批次預測的 JSON 序列化"""
    print("\n" + "=" * 60)
    print("測試批次預測（前 5 位客戶）")
    print("=" * 60)
    
    try:
        # 預測前 5 位客戶
        results = predict_next_purchase_batch(top_n=5)
        
        # 嘗試 JSON 序列化
        json_str = json.dumps(results, ensure_ascii=False)
        print(f"✅ JSON 序列化成功！共 {len(results)} 筆資料")
        
        # 顯示第一筆資料
        if results:
            print(f"\n第一筆資料:")
            print(json.dumps(results[0], ensure_ascii=False, indent=2))
            
            # 檢查資料類型
            print(f"\n資料類型檢查:")
            for key, value in results[0].items():
                print(f"  {key}: {type(value).__name__} = {value}")
        
    except TypeError as e:
        print(f"❌ JSON 序列化失敗: {e}")
    except Exception as e:
        print(f"❌ 預測失敗: {e}")


if __name__ == '__main__':
    test_single_prediction()
    test_batch_prediction()
