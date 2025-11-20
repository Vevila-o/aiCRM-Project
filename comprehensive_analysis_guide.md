# 🤖 AI CRM 綜合客戶分析系統

## 📋 系統概述

本系統成功整合了多個機器學習模型和數據分析工具，提供企業級的客戶行為分析：

1. **🔍 RFM模型** - 客戶價值分析和分群 (Recency, Frequency, Monetary)
2. **⚠️ CatBoost流失率預測** - 使用梯度提升算法預測客戶流失風險
3. **🛒 LSTM下次購買預測** - 基於神經網絡預測客戶購買時間
4. **📊 客群消費狀態分析** - 詳細的消費行為統計和趨勢分析

## ✅ 系統測試結果

```
✅ 所有測試通過！

測試結果摘要：
- RFM計算完成，總記錄數: 420+ 顧客
- 流失預測分析: 420 位顧客
- 客戶成長率分析: 完成
- 客戶活躍度分析: 完成
- 忠誠客戶分析: 90 位顧客，平均流失機率 47.3%
- 總營收: $7,878,025，平均訂單: $1,610.72
- 購買轉換率: 100%，近期活躍率: 60.24%
```

## 主要功能

### 1. 綜合客戶分析

```python
from myCRM.services.ai_suggestion_service import get_comprehensive_customer_analysis

# 分析所有客群
all_analysis = get_comprehensive_customer_analysis(top_customers=20)

# 分析特定客群（例如：忠誠客戶 ID=1）
loyal_analysis = get_comprehensive_customer_analysis(category_id=1, top_customers=10)
```

### 2. 返回數據結構

```json
{
    "analysis_time": "2025-11-21T...",
    "rfm_analysis": {
        "distribution": {
            "labels": ["忠誠顧客", "潛在高價值顧客", ...],
            "counts": [100, 150, ...],
            "total": 500
        },
        "total_customers": 500
    },
    "churn_analysis": {
        "total_analyzed": 450,
        "high_risk_count": 50,
        "medium_risk_count": 120,
        "low_risk_count": 280,
        "average_churn_probability": 0.345,
        "predictions": [...]
    },
    "next_purchase_analysis": {
        "total_predictions": 200,
        "average_predicted_days": 15.6,
        "predictions": [...]
    },
    "growth_analysis": {
        "period": "month",
        "labels": ["2025-06", "2025-07", ...],
        "growth_rates": [5.2, 8.1, ...],
        "new_customers": [25, 40, ...],
        "totals": [500, 540, ...]
    },
    "activity_analysis": {
        "period": "quarter",
        "labels": ["2025 Q1", "2025 Q2", ...],
        "activity_rates": [65.5, 72.3, ...],
        "active_customers": [300, 350, ...],
        "total_customers": [458, 484, ...]
    },
    "consumption_statistics": {
        "total_customers": 500,
        "customers_with_purchases": 450,
        "recent_active_customers": 200,
        "total_revenue": 125000.50,
        "average_order_value": 278.50,
        "max_order_value": 5000.00,
        "total_transactions": 2500,
        "purchase_conversion_rate": 90.0,
        "recent_activity_rate": 44.4
    },
    "category_specific_analysis": {
        "category_id": 1,
        "category_name": "忠誠顧客",
        "total_customers_in_category": 100,
        "churn_analysis": {
            "analyzed_count": 95,
            "average_churn_probability": 0.125,
            "high_risk_count": 5,
            "top_risk_customers": [...]
        },
        "next_purchase_analysis": {
            "analyzed_count": 80,
            "average_next_purchase_days": 8.5,
            "customers_buying_soon": [...],
            "customers_buying_later": [...]
        },
        "rfm_statistics": {
            "average_recency_score": 4.2,
            "average_frequency_score": 4.8,
            "average_monetary_score": 4.5,
            "average_total_rfm_score": 13.5
        }
    }
}
```

## 客戶分群定義

- **1 - 忠誠顧客**: 高頻次、高金額、近期活躍的優質客戶
- **2 - 潛在高價值顧客**: 高消費但頻次較低的客戶
- **3 - 普通顧客**: 一般消費水平和頻次的客戶
- **4 - 低價值顧客**: 消費金額和頻次都較低的客戶
- **5 - 沉睡顧客**: 過去活躍但近期無消費的客戶
- **6 - 潛在流失顧客**: 有流失風險的客戶
- **7 - 新顧客**: 新註冊的客戶

## 使用場景

### 1. 營銷策略制定
```python
# 分析高風險客戶，制定挽回策略
analysis = get_comprehensive_customer_analysis()
high_risk_customers = [
    p for p in analysis['churn_analysis']['predictions'] 
    if p['risk_level'] == 'high'
]

# 分析即將購買的客戶，推送促銷信息
soon_buyers = []
for category_id in [1, 2, 7]:  # 重點客群
    cat_analysis = get_comprehensive_customer_analysis(category_id=category_id)
    if cat_analysis['category_specific_analysis']:
        soon_buyers.extend(
            cat_analysis['category_specific_analysis']['next_purchase_analysis']['customers_buying_soon']
        )
```

### 2. 客戶生命周期管理
```python
# 分析客戶成長趨勢
analysis = get_comprehensive_customer_analysis()
growth_data = analysis['growth_analysis']
activity_data = analysis['activity_analysis']

# 識別需要關注的客群
for category_id in range(1, 8):
    cat_analysis = get_comprehensive_customer_analysis(category_id=category_id)
    # 根據分析結果制定不同的客戶策略
```

### 3. 績效監控
```python
# 定期執行綜合分析，監控關鍵指標
analysis = get_comprehensive_customer_analysis()

kpis = {
    "客戶總數": analysis['consumption_statistics']['total_customers'],
    "購買轉換率": analysis['consumption_statistics']['purchase_conversion_rate'],
    "平均流失機率": analysis['churn_analysis']['average_churn_probability'],
    "高風險客戶比例": analysis['churn_analysis']['high_risk_count'] / analysis['churn_analysis']['total_analyzed'] * 100,
    "近期活躍率": analysis['consumption_statistics']['recent_activity_rate']
}
```

## 注意事項

1. **數據準備**: 確保客戶、交易數據完整且最新
2. **模型訓練**: LSTM模型需要先訓練才能進行預測
3. **性能考慮**: 大量客戶數據分析可能需要較長時間
4. **定期更新**: 建議定期重新計算RFM分數和重新訓練模型

## 🚀 快速開始

### 1. 測試系統功能
執行測試腳本檢查系統運行狀況：
```bash
cd aiCRM2
python test_comprehensive_analysis.py
```

### 2. 基本API使用
```python
from myCRM.services.ai_suggestion_service import get_comprehensive_customer_analysis

# 獲取所有客群的綜合分析
all_analysis = get_comprehensive_customer_analysis(top_customers=20)

# 獲取特定客群分析（忠誠客戶）
loyal_analysis = get_comprehensive_customer_analysis(category_id=1, top_customers=10)
```

### 3. Django 視圖集成
```python
# 在您的 views.py 中
from analysis_views import comprehensive_analysis_api, comprehensive_analysis_dashboard

# API端點: /api/comprehensive-analysis/
# 儀表板: /dashboard/comprehensive-analysis/
```

### 4. 儀表板訪問
啟動Django服務器後訪問：
- 綜合分析儀表板: `http://localhost:8000/dashboard/comprehensive-analysis/`
- API端點: `http://localhost:8000/api/comprehensive-analysis/?top_customers=20`

## 🏗️ 系統架構

```
┌─────────────────────────────────────────────┐
│              前端儀表板                         │
│  comprehensive_analysis_dashboard.html      │
└─────────────────┬───────────────────────────┘
                  │ HTTP Requests
┌─────────────────▼───────────────────────────┐
│             Django Views                    │
│  analysis_views.py (API + Dashboard)       │
└─────────────────┬───────────────────────────┘
                  │ Python Calls
┌─────────────────▼───────────────────────────┐
│         綜合分析核心引擎                        │
│  ai_suggestion_service.py                   │
│  └─ get_comprehensive_customer_analysis()   │
└─────┬─────┬─────┬─────┬─────────────────────┘
      │     │     │     │
      ▼     ▼     ▼     ▼
   ┌────┐ ┌───┐ ┌────┐ ┌──────┐
   │RFM │ │Cat│ │LSTM│ │Stats │
   │分析│ │流失│ │購買│ │消費  │
   └────┘ └───┘ └────┘ └──────┘
      │     │     │     │
      └─────┴─────┴─────┴─── MySQL Database
```

## 🔧 核心組件

### 1. RFM 分析模組 (`rfm_count.py`)
- 計算客戶的最近性(R)、頻次(F)、貨幣價值(M)分數
- 自動客戶分群 (1-7個類別)
- 支持客戶成長率和活躍度分析

### 2. CatBoost 流失預測 (`churn_service.py`)
- 使用梯度提升算法進行客戶流失預測
- 支持模型訓練和批量預測
- 提供風險等級分類 (高/中/低)

### 3. LSTM 購買預測 (`next_purchse.py`)
- 基於長短期記憶網絡預測下次購買時間
- 考慮客戶歷史購買模式
- 支持批量和單客戶預測

### 4. 綜合分析引擎 (`ai_suggestion_service.py`)
- 整合所有模型的預測結果
- 提供統一的數據接口
- 計算綜合客戶洞察

## 💾 數據模型

系統使用的主要數據表：
- `Customer`: 客戶基本信息
- `Transaction`: 交易記錄
- `RFMscore`: RFM分析結果
- `AiSuggection`: AI建議記錄

## 錯誤處理

系統包含完整的錯誤處理機制：
- LSTM預測失敗時會降級為空結果
- 數據不足時會返回默認值
- 所有異常都會被捕捉並記錄
- 提供詳細的錯誤訊息和日誌

## 🔐 安全性考慮

- 所有API端點都應配置適當的認證
- 敏感的客戶數據需要適當的訪問控制
- 建議在生產環境中啟用HTTPS
- 定期更新和重新訓練機器學習模型