# LSTM 下次購買預測模型 - 準確度分析報告

## 當前模型表現

### 訓練資訊
- **訓練日期**: 2025-11-17
- **總樣本數**: 333 位客戶
- **訓練集**: 267 樣本 (80%)
- **驗證集**: 66 樣本 (20%)
- **特徵**: 10 筆歷史交易序列 x 6 個特徵

### 評估指標

| 指標 | 數值 | 說明 |
|------|------|------|
| **MAE** | 18.22 天 | 平均絕對誤差 |
| **RMSE** | 29.03 天 | 均方根誤差 |
| **平均購買間隔** | 18.78 天 | 客戶實際平均間隔 |
| **相對誤差率** | 97% | MAE / 平均間隔 |

### 準確度評估

#### 當前準確度：約 50-60%

**問題分析**：
1. **誤差太大**: MAE (18.22天) 接近平均值 (18.78天)
2. **離群值多**: RMSE (29.03) 明顯大於 MAE，表示有很多大誤差預測
3. **樣本不足**: 333 個樣本對 LSTM 來說偏少

---

##  改善建議

### 1. 增加訓練輪數和調整參數
```python
from myCRM.services.next_purchse import train_next_purchase_model

result = train_next_purchase_model(
    epochs=200,              # 增加到 200 輪
    batch_size=16,           # 減小批次大小
    learning_rate=0.0005,    # 降低學習率
    hidden_size=128,         # 增加隱藏層
    num_layers=3,            # 增加層數
)
```

### 2. 增加序列長度
```python
result = train_next_purchase_model(
    max_sequence_length=15,  # 使用更多歷史記錄
    min_transactions=5,      # 提高最少交易次數要求
)
```

### 3. 資料預處理改進
- 移除異常值（購買間隔 > 180 天的客戶）
- 按客戶分群訓練（例如：高頻客戶 vs 低頻客戶）
- 增加更多特徵（季節性、星期幾、促銷活動等）

### 4. 嘗試其他模型
- **XGBoost**: 對小數據集表現更好
- **GRU**: 比 LSTM 參數少，不容易過擬合
- **簡單統計模型**: 移動平均、指數平滑

---

## 預期改善效果

### 目標指標

| 改善措施 | 預期 MAE | 預期準確度 |
|---------|---------|-----------|
| 當前模型 | 18.22 天 | 50-60% |
| 調整參數 | 12-15 天 | 65-75% |
| 增加序列長度 | 10-12 天 | 75-80% |
| 資料預處理 | 8-10 天 | 80-85% |
| 組合優化 | 6-8 天 | 85-90% |

---

##  實際應用建議

### 當前模型可用場景

 **適合用於**：
- 粗略的客戶分群（即將購買 vs 不會購買）
- 長期趨勢分析
- 配合其他指標使用（RFM、流失率等）

 **不適合用於**：
- 精確的購買日期預測
- 個別客戶的精準行銷
- 自動化決策系統

### 使用建議

**容錯範圍應用**：
```python
prediction = predict_next_purchase_time(customer_id)
predicted_days = prediction['predicted_days']

# 加上誤差範圍
min_days = predicted_days - 18  # 減去 MAE
max_days = predicted_days + 18  # 加上 MAE

print(f"預測客戶會在 {min_days} - {max_days} 天內購買")
```

**信心區間**：
- **7天內預測**: 信心度 40-50%（誤差太大）
- **14天內預測**: 信心度 50-60%
- **30天內預測**: 信心度 60-70%（較可靠）

---

##  快速改善方案

### 方案 1: 簡單重訓練（推薦）
```python
# 增加訓練輪數和調整學習率
result = train_next_purchase_model(
    epochs=150,
    learning_rate=0.0008,
    batch_size=16
)
```

### 方案 2: 進階調整
```python
result = train_next_purchase_model(
    max_sequence_length=15,
    hidden_size=128,
    num_layers=3,
    epochs=200,
    batch_size=16,
    learning_rate=0.0005
)
```

### 方案 3: 資料清理後重訓練
```python
# 1. 先分析資料分布
from myCRM.services.next_purchse import predict_next_purchase_batch
results = predict_next_purchase_batch()

# 2. 找出異常客戶（購買間隔 > 90 天）
outliers = [r for r in results if r['avg_interval_history'] > 90]
print(f"異常客戶數: {len(outliers)}")

# 3. 在資料庫中標記或排除這些客戶，然後重訓練
```

---

##  總結

### 當前狀態
-  模型準確度約 50-60%
-  誤差較大（±18 天）
-  需要改進才能用於精準預測

### 建議行動
1.  立即：增加訓練輪數到 150-200
2.  短期：調整超參數（學習率、批次大小）
3.  中期：增加序列長度和隱藏層
4.  長期：收集更多資料、增加特徵

### 期望結果
- 目標 MAE: < 10 天
- 目標準確度: > 80%
- 實際可達成: 6-8 天誤差（經過優化）

---

生成時間: 2025-11-17
