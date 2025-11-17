"""
LSTM 下次購買時間預測模型使用範例
"""

import os
import django

# Django 設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiCRM.settings')
django.setup()

from myCRM.services.next_purchse import (
    train_next_purchase_model,
    predict_next_purchase_time,
    predict_next_purchase_batch,
)


def example_train_model():
    """訓練模型範例"""
    print("=" * 60)
    print("開始訓練 LSTM 模型...")
    print("=" * 60)
    
    result = train_next_purchase_model(
        min_transactions=3,        # 最少交易次數
        max_sequence_length=10,    # 序列長度（使用最近 10 筆交易）
        hidden_size=64,            # LSTM 隱藏層大小
        num_layers=2,              # LSTM 層數
        dropout=0.2,               # Dropout 比例
        learning_rate=0.001,       # 學習率
        epochs=100,                # 訓練輪數
        batch_size=128,             # 批次大小
        val_split=0.2,             # 驗證集比例
    )
    
    print("\n訓練結果:")
    print(f"總樣本數: {result['samples_total']}")
    print(f"訓練集: {result['samples_train']}")
    print(f"驗證集: {result['samples_val']}")
    print(f"平均誤差 (MAE): {result['val_mae']:.2f} 天")
    print(f"均方根誤差 (RMSE): {result['val_rmse']:.2f} 天")
    print(f"歷史平均間隔: {result['avg_target_days']:.2f} 天")
    print(f"模型路徑: {result['model_path']}")


def example_predict_single_customer():
    """預測單一客戶範例"""
    print("\n" + "=" * 60)
    print("預測單一客戶的下次購買時間")
    print("=" * 60)
    
    # 替換成您的客戶 ID
    customer_id = 141
    
    try:
        result = predict_next_purchase_time(customer_id)
        
        print(f"\n客戶 ID: {result['customer_id']}")
        print(f"最後購買日期: {result['last_purchase_date']}")
        print(f"預測下次購買天數: {result['predicted_days']} 天")
        print(f"預測下次購買日期: {result['predicted_date']}")
        print(f"歷史平均間隔: {result['avg_interval_history']} 天")
        print(f"總交易次數: {result['total_transactions']}")
        
    except Exception as e:
        print(f"預測失敗: {e}")


def example_predict_batch():
    """批次預測範例"""
    print("\n" + "=" * 60)
    print("批次預測多位客戶")
    print("=" * 60)
    
    # 預測前 10 位客戶
    results = predict_next_purchase_batch(top_n=10)
    
    print(f"\n找到 {len(results)} 位客戶的預測結果:\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. 客戶 {result['customer_id']:3d} | "
              f"最後購買: {result['last_purchase_date']} | "
              f"預測 {result['predicted_days']:3d} 天後 | "
              f"預測日期: {result['predicted_date']}")


def example_find_likely_purchasers():
    """找出近期可能購買的客戶"""
    print("\n" + "=" * 60)
    print("找出未來 7 天內可能購買的客戶")
    print("=" * 60)
    
    results = predict_next_purchase_batch()
    
    # 篩選出 7 天內可能購買的客戶
    likely_purchasers = [r for r in results if r['predicted_days'] <= 7]
    
    print(f"\n找到 {len(likely_purchasers)} 位客戶可能在 7 天內購買:\n")
    
    for i, result in enumerate(likely_purchasers[:20], 1):  # 顯示前 20 位
        print(f"{i:2d}. 客戶 {result['customer_id']:3d} | "
              f"預測 {result['predicted_days']:2d} 天後購買 | "
              f"預測日期: {result['predicted_date']}")


if __name__ == '__main__':
    # 1. 訓練模型（首次使用時執行）
    example_train_model()
    
    # 2. 預測單一客戶
    example_predict_single_customer()
    
    # 3. 批次預測
    example_predict_batch()
    
    # 4. 找出近期可能購買的客戶
    example_find_likely_purchasers()
