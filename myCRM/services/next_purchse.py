from __future__ import annotations

import pandas as pd
import numpy as np
import json
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from django.db.models import Count, Max, Sum

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
    _TORCH_AVAILABLE = True
except Exception:
    _TORCH_AVAILABLE = False

from myCRM.models import Transaction, Customer
from .rfm_count import rfm_score_from_raw


# ==================== 輔助函數 ====================

def _parse_as_of(as_of: Optional[str]) -> date:
    """將字串轉為日期物件"""
    if not as_of:
        return date.today()
    return datetime.strptime(as_of, "%Y-%m-%d").date()


def _model_dir() -> str:
    """取得模型目錄"""
    return os.path.dirname(os.path.abspath(__file__))


def _lstm_model_path() -> str:
    """LSTM 模型路徑"""
    return os.path.join(_model_dir(), "next_purchase_lstm.pth")


def _lstm_meta_path() -> str:
    """LSTM 模型元資料路徑"""
    return os.path.join(_model_dir(), "next_purchase_lstm.meta.json")


def _scaler_path() -> str:
    """特徵標準化器路徑"""
    return os.path.join(_model_dir(), "next_purchase_scaler.json")


# ==================== LSTM 模型定義 ====================

class PurchaseTimeLSTM(nn.Module):
    """
    使用 LSTM 預測顧客下次購買時間間隔
    
    輸入：顧客的歷史購買序列（交易間隔天數、金額、RFM特徵等）
    輸出：預測的下次購買天數
    """
    
    def __init__(
        self,
        input_size: int = 6,      # 每筆交易的特徵數量
        hidden_size: int = 64,     # LSTM 隱藏層大小
        num_layers: int = 2,       # LSTM 層數
        dropout: float = 0.2,      # Dropout 比例
    ):
        super(PurchaseTimeLSTM, self).__init__()
        
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM 層
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        
        # 全連接層
        self.fc1 = nn.Linear(hidden_size, 32)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(32, 1)
        
    def forward(self, x):
        """
        前向傳播
        x: shape (batch_size, sequence_length, input_size)
        """
        # LSTM 輸出
        lstm_out, (h_n, c_n) = self.lstm(x)
        
        # 取最後一個時間步的輸出
        last_output = lstm_out[:, -1, :]
        
        # 全連接層
        out = self.fc1(last_output)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc2(out)
        
        return out


# ==================== 資料集類別 ====================

class PurchaseDataset(Dataset):
    """PyTorch 資料集類別"""
    
    def __init__(self, sequences, targets):
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.FloatTensor(targets)
        
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]


# ==================== 資料準備函數 ====================

def _build_purchase_sequences(
    min_transactions: int = 3,
    max_sequence_length: int = 10,
    as_of: Optional[str] = None,
) -> Tuple[List[List[List[float]]], List[float], Dict[str, Any]]:
    """
    建立購買序列資料
    
    Returns:
        sequences: 每位顧客的購買序列特徵 [客戶數, 序列長度, 特徵數]
        targets: 每位顧客的下次購買天數 [客戶數]
        stats: 資料統計資訊
    """
    as_of_date = _parse_as_of(as_of)
    
    # 取得所有交易記錄（按客戶和日期排序）
    transactions = (
        Transaction.objects
        .filter(transdate__lte=as_of_date)
        .order_by('customerid', 'transdate')
        .values('customerid', 'transdate', 'totalprice')
    )
    
    # 按客戶分組
    customer_transactions: Dict[int, List] = {}
    for trans in transactions:
        cid = trans['customerid']
        if cid not in customer_transactions:
            customer_transactions[cid] = []
        customer_transactions[cid].append({
            'date': trans['transdate'],
            'price': float(trans['totalprice'] or 0),
        })
    
    sequences = []
    targets = []
    customer_ids = []
    
    for cid, trans_list in customer_transactions.items():
        if len(trans_list) < min_transactions + 1:
            # 至少需要 min_transactions 筆歷史 + 1 筆作為目標
            continue
        
        # 計算交易間隔
        intervals = []
        prices = []
        for i in range(len(trans_list) - 1):
            date1 = trans_list[i]['date']
            date2 = trans_list[i + 1]['date']
            if isinstance(date1, datetime):
                date1 = date1.date()
            if isinstance(date2, datetime):
                date2 = date2.date()
            
            interval = (date2 - date1).days
            intervals.append(interval)
            prices.append(trans_list[i]['price'])
        
        # 如果間隔數量不足，跳過
        if len(intervals) < min_transactions:
            continue
        
        # 計算 RFM 特徵（基於歷史交易）
        total_trans = len(trans_list) - 1
        total_spent = sum(prices)
        avg_interval = float(np.mean(intervals[:-1])) if len(intervals) > 1 else float(intervals[0])
        
        # 建立序列（使用倒數第 max_sequence_length 到倒數第二筆交易）
        seq_intervals = intervals[-(max_sequence_length+1):-1]
        seq_prices = prices[-(max_sequence_length+1):-1]
        
        # 填充序列至固定長度
        seq_len = len(seq_intervals)
        if seq_len < max_sequence_length:
            # 用平均值填充
            pad_len = max_sequence_length - seq_len
            seq_intervals = [float(avg_interval)] * pad_len + seq_intervals
            avg_price = float(np.mean(seq_prices)) if seq_prices else 0.0
            seq_prices = [float(avg_price)] * pad_len + seq_prices
        
        # 建立特徵序列
        sequence_features = []
        for i in range(max_sequence_length):
            # 每個時間步的特徵：
            # 1. 交易間隔天數
            # 2. 交易金額
            # 3. 累積交易次數
            # 4. 累積交易金額
            # 5. 平均間隔
            # 6. 平均金額
            features = [
                float(seq_intervals[i]),
                float(seq_prices[i]),
                float(i + 1),  # 累積次數
                float(sum(seq_prices[:i+1])),  # 累積金額
                float(np.mean(seq_intervals[:i+1])),  # 平均間隔
                float(np.mean(seq_prices[:i+1])),  # 平均金額
            ]
            sequence_features.append(features)
        
        sequences.append(sequence_features)
        targets.append(float(intervals[-1]))  # 最後一個間隔作為目標
        customer_ids.append(cid)
    
    stats = {
        'total_customers': int(len(sequences)),
        'sequence_length': int(max_sequence_length),
        'feature_size': 6,
        'avg_target': float(np.mean(targets)) if targets else 0.0,
        'std_target': float(np.std(targets)) if targets else 0.0,
    }
    
    return sequences, targets, stats


def _normalize_data(
    sequences: List[List[List[float]]],
    targets: List[float],
    scaler_params: Optional[Dict] = None,
) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """
    標準化序列資料
    
    Returns:
        normalized_sequences: 標準化後的序列
        normalized_targets: 標準化後的目標值
        scaler_params: 標準化參數（用於反向轉換）
    """
    sequences_array = np.array(sequences)
    targets_array = np.array(targets).reshape(-1, 1)
    
    if scaler_params is None:
        # 計算標準化參數
        # 對每個特徵維度計算 mean 和 std
        seq_flat = sequences_array.reshape(-1, sequences_array.shape[-1])
        seq_mean = np.mean(seq_flat, axis=0)
        seq_std = np.std(seq_flat, axis=0) + 1e-8  # 避免除以零
        
        target_mean = np.mean(targets_array)
        target_std = np.std(targets_array) + 1e-8
        
        scaler_params = {
            'seq_mean': seq_mean.tolist(),
            'seq_std': seq_std.tolist(),
            'target_mean': float(target_mean),
            'target_std': float(target_std),
        }
    else:
        seq_mean = np.array(scaler_params['seq_mean'])
        seq_std = np.array(scaler_params['seq_std'])
        target_mean = scaler_params['target_mean']
        target_std = scaler_params['target_std']
    
    # 標準化
    normalized_sequences = (sequences_array - seq_mean) / seq_std
    normalized_targets = (targets_array - target_mean) / target_std
    
    return normalized_sequences, normalized_targets.flatten(), scaler_params


def _denormalize_predictions(
    predictions: np.ndarray,
    scaler_params: Dict,
) -> np.ndarray:
    """將預測值反標準化"""
    target_mean = scaler_params['target_mean']
    target_std = scaler_params['target_std']
    return predictions * target_std + target_mean


# ==================== 訓練函數 ====================

def train_next_purchase_model(
    min_transactions: int = 3,
    max_sequence_length: int = 10,
    hidden_size: int = 64,
    num_layers: int = 2,
    dropout: float = 0.2,
    learning_rate: float = 0.001,
    epochs: int = 100,
    batch_size: int = 32,
    val_split: float = 0.2,
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """
    訓練 LSTM 模型預測下次購買時間
    
    Args:
        min_transactions: 最少交易次數
        max_sequence_length: 序列最大長度
        hidden_size: LSTM 隱藏層大小
        num_layers: LSTM 層數
        dropout: Dropout 比例
        learning_rate: 學習率
        epochs: 訓練輪數
        batch_size: 批次大小
        val_split: 驗證集比例
        as_of: 資料截止日期
    
    Returns:
        訓練結果字典
    """
    if not _TORCH_AVAILABLE:
        raise RuntimeError("PyTorch 未安裝，請先安裝 torch")
    
    # 準備資料
    print("正在準備資料...")
    sequences, targets, stats = _build_purchase_sequences(
        min_transactions=min_transactions,
        max_sequence_length=max_sequence_length,
        as_of=as_of,
    )
    
    if len(sequences) == 0:
        return {"message": "沒有足夠的資料進行訓練", "samples": 0}
    
    print(f"總樣本數: {len(sequences)}")
    
    # 標準化資料
    normalized_seqs, normalized_targets, scaler_params = _normalize_data(
        sequences, targets
    )
    
    # 切分訓練集和驗證集
    n_samples = len(normalized_seqs)
    n_val = int(n_samples * val_split)
    n_train = n_samples - n_val
    
    indices = np.random.permutation(n_samples)
    train_indices = indices[:n_train]
    val_indices = indices[n_train:]
    
    X_train = normalized_seqs[train_indices]
    y_train = normalized_targets[train_indices]
    X_val = normalized_seqs[val_indices]
    y_val = normalized_targets[val_indices]
    
    # 建立資料集和資料載入器
    train_dataset = PurchaseDataset(X_train, y_train)
    val_dataset = PurchaseDataset(X_val, y_val)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    # 建立模型
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = PurchaseTimeLSTM(
        input_size=stats['feature_size'],
        hidden_size=hidden_size,
        num_layers=num_layers,
        dropout=dropout,
    ).to(device)
    
    # 損失函數和優化器
    # Adam 增加權重，找到參數最佳解，越低越好
    # 損失函數 是來使用調節器來接近真實值的機制，損失函數越小使梯度下降
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    
    # 訓練循環
    print("開始訓練...")
    train_losses = []
    val_losses = []
    best_val_loss = float('inf')
    
    for epoch in range(epochs):
        # 訓練階段
        model.train()
        train_loss = 0.0
        for batch_x, batch_y in train_loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            
            optimizer.zero_grad()
            outputs = model(batch_x).squeeze()
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
        
        train_loss /= len(train_loader)
        train_losses.append(train_loss)
        
        # 驗證階段
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x = batch_x.to(device)
                batch_y = batch_y.to(device)
                
                outputs = model(batch_x).squeeze()
                loss = criterion(outputs, batch_y)
                val_loss += loss.item()
        
        val_loss /= len(val_loader)
        val_losses.append(val_loss)
        
        # 儲存最佳模型
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), _lstm_model_path())
        
        if (epoch + 1) % 10 == 0:
            print(f"Epoch [{epoch+1}/{epochs}], Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")
    
    # 計算驗證集 MAE
    model.eval()
    val_predictions = []
    val_actuals = []
    
    with torch.no_grad():
        for batch_x, batch_y in val_loader:
            batch_x = batch_x.to(device)
            outputs = model(batch_x).squeeze()
            val_predictions.extend(outputs.cpu().numpy())
            val_actuals.extend(batch_y.numpy())
    
    # 反標準化
    val_predictions = _denormalize_predictions(np.array(val_predictions), scaler_params)
    val_actuals = _denormalize_predictions(np.array(val_actuals), scaler_params)
    
    mae = float(np.mean(np.abs(val_predictions - val_actuals)))
    rmse = float(np.sqrt(np.mean((val_predictions - val_actuals) ** 2)))
    
    # 儲存標準化參數
    with open(_scaler_path(), 'w', encoding='utf-8') as f:
        json.dump(scaler_params, f, ensure_ascii=False)
    
    # 儲存元資料
    meta = {
        'as_of': _parse_as_of(as_of).isoformat(),
        'min_transactions': int(min_transactions),
        'max_sequence_length': int(max_sequence_length),
        'hidden_size': int(hidden_size),
        'num_layers': int(num_layers),
        'samples_total': int(n_samples),
        'samples_train': int(n_train),
        'samples_val': int(n_val),
        'val_mae': float(mae),
        'val_rmse': float(rmse),
        'avg_target_days': float(stats['avg_target']),
    }
    
    with open(_lstm_meta_path(), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False)
    
    return {
        'message': '模型訓練完成',
        'model_path': _lstm_model_path(),
        **meta,
        'val_mae': float(round(mae, 2)),
        'val_rmse': float(round(rmse, 2)),
    }


# ==================== 預測函數 ====================

def predict_next_purchase_time(
    customer_id: int,
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """
    預測單一顧客的下次購買時間
    
    Args:
        customer_id: 客戶 ID
        as_of: 預測基準日期
    
    Returns:
        預測結果字典
    """
    if not _TORCH_AVAILABLE:
        raise RuntimeError("PyTorch 未安裝")
    
    # 載入模型和參數
    model_path = _lstm_model_path()
    meta_path = _lstm_meta_path()
    scaler_path = _scaler_path()
    
    if not os.path.exists(model_path):
        raise FileNotFoundError("模型尚未訓練，請先執行 train_next_purchase_model()")
    
    # 載入元資料
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    
    with open(scaler_path, 'r', encoding='utf-8') as f:
        scaler_params = json.load(f)
    
    max_sequence_length = meta['max_sequence_length']
    
    # 取得客戶交易記錄
    as_of_date = _parse_as_of(as_of)
    transactions = (
        Transaction.objects
        .filter(customerid=customer_id, transdate__lte=as_of_date)
        .order_by('transdate')
        .values('transdate', 'totalprice')
    )
    
    trans_list = list(transactions)
    if len(trans_list) < 2:
        raise ValueError(f"客戶 {customer_id} 的交易記錄不足（需至少 2 筆）")
    
    # 計算交易間隔和金額
    intervals = []
    prices = []
    for i in range(len(trans_list) - 1):
        date1 = trans_list[i]['transdate']
        date2 = trans_list[i + 1]['transdate']
        if isinstance(date1, datetime):
            date1 = date1.date()
        if isinstance(date2, datetime):
            date2 = date2.date()
        
        interval = (date2 - date1).days
        intervals.append(interval)
        prices.append(float(trans_list[i]['totalprice'] or 0))
    
    # 建立序列
    avg_interval = float(np.mean(intervals))
    avg_price = float(np.mean(prices))
    
    seq_intervals = intervals[-max_sequence_length:]
    seq_prices = prices[-max_sequence_length:]
    
    # 填充至固定長度
    if len(seq_intervals) < max_sequence_length:
        pad_len = max_sequence_length - len(seq_intervals)
        seq_intervals = [float(avg_interval)] * pad_len + seq_intervals
        seq_prices = [float(avg_price)] * pad_len + seq_prices
    
    # 建立特徵
    sequence_features = []
    for i in range(max_sequence_length):
        features = [
            float(seq_intervals[i]),
            float(seq_prices[i]),
            float(i + 1),
            float(sum(seq_prices[:i+1])),
            float(np.mean(seq_intervals[:i+1])),
            float(np.mean(seq_prices[:i+1])),
        ]
        sequence_features.append(features)
    
    # 標準化
    sequence_array = np.array([sequence_features])
    seq_mean = np.array(scaler_params['seq_mean'])
    seq_std = np.array(scaler_params['seq_std'])
    normalized_seq = (sequence_array - seq_mean) / seq_std
    
    # 載入模型
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = PurchaseTimeLSTM(
        input_size=6,
        hidden_size=meta['hidden_size'],
        num_layers=meta['num_layers'],
    ).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    
    # 預測
    with torch.no_grad():
        input_tensor = torch.FloatTensor(normalized_seq).to(device)
        prediction = model(input_tensor).cpu().numpy()[0][0]
    
    # 反標準化
    predicted_days = _denormalize_predictions(np.array([prediction]), scaler_params)[0]
    predicted_days = max(1, int(round(float(predicted_days))))  # 至少 1 天，確保是 int
    
    # 計算預測日期
    last_purchase_date = trans_list[-1]['transdate']
    if isinstance(last_purchase_date, datetime):
        last_purchase_date = last_purchase_date.date()
    
    predicted_date = last_purchase_date + timedelta(days=predicted_days)
    
    return {
        'customer_id': int(customer_id),
        'last_purchase_date': last_purchase_date.isoformat(),
        'predicted_days': int(predicted_days),
        'predicted_date': predicted_date.isoformat(),
        'avg_interval_history': float(round(avg_interval, 1)),
        'total_transactions': int(len(trans_list)),
    }


def predict_next_purchase_batch(
    as_of: Optional[str] = None,
    top_n: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    批次預測所有符合條件的顧客下次購買時間
    
    Args:
        as_of: 預測基準日期
        top_n: 只返回前 N 位客戶
    
    Returns:
        預測結果列表
    """
    # 取得所有有足夠交易記錄的客戶
    as_of_date = _parse_as_of(as_of)
    
    customers_with_trans = (
        Transaction.objects
        .filter(transdate__lte=as_of_date)
        .values('customerid')
        .annotate(trans_count=Count('transactionid'))
        .filter(trans_count__gte=2)
        .order_by('-trans_count')
    )
    
    if top_n:
        customers_with_trans = customers_with_trans[:top_n]
    
    results = []
    for row in customers_with_trans:
        cid = row['customerid']
        try:
            prediction = predict_next_purchase_time(cid, as_of=as_of)
            results.append(prediction)
        except Exception:
            # 跳過預測失敗的客戶
            continue
    
    # 按預測天數排序（即將購買的排前面）
    results.sort(key=lambda x: x['predicted_days'])
    
    return results
