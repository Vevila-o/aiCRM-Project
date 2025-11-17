from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from django.db.models import Count, Max, Sum

try:
    from catboost import CatBoostClassifier
    _CATBOOST_AVAILABLE = True
except Exception:  # pragma: no cover
    _CATBOOST_AVAILABLE = False


from myCRM.models import Transaction
from .rfm_count import rfm_score_from_raw, classify_customer


def _parse_as_of(as_of: Optional[str]) -> date:
    if not as_of:
        return date.today()
    return datetime.strptime(as_of, "%Y-%m-%d").date()


def _model_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _model_path() -> str:
    return os.path.join(_model_dir(), "churn_model.cbm")


def _meta_path() -> str:
    return os.path.join(_model_dir(), "churn_model.meta.json")


def _build_rfm(as_of: Optional[str] = None, window_days: int = 365) -> List[Dict[str, Any]]:
    as_of_date = _parse_as_of(as_of)
    window_start = as_of_date - timedelta(days=window_days)

    last_dates = (
        Transaction.objects
        .filter(transdate__lte=as_of_date)
        .values("customerid")
        .annotate(last_date=Max("transdate"))
    )

    last_date_by_cust: Dict[int, date] = {}
    for row in last_dates:
        cid = row.get("customerid")
        if cid is None:
            continue
        last_date_by_cust[int(cid)] = row.get("last_date")

    window_stats = (
        Transaction.objects
        .filter(transdate__gte=window_start, transdate__lte=as_of_date)
        .values("customerid")
        .annotate(freq=Count("transactionid"), money=Sum("totalprice"))
    )

    freq_by_cust: Dict[int, int] = {}
    money_by_cust: Dict[int, float] = {}
    for row in window_stats:
        cid = row.get("customerid")
        if cid is None:
            continue
        freq_by_cust[int(cid)] = int(row.get("freq") or 0)
        total = row.get("money")
        money_by_cust[int(cid)] = float(total) if total is not None else 0.0

    results: List[Dict[str, Any]] = []
    for cid, last_dt in last_date_by_cust.items():
        recency_days = (as_of_date - last_dt).days if last_dt else 10**9
        freq = freq_by_cust.get(cid, 0)
        money = money_by_cust.get(cid, 0.0)
        
        # 計算 RFM 分數
        r_score, f_score, m_score = rfm_score_from_raw(
            int(recency_days), int(freq), float(money)
        )
        
        # 計算客戶分類
        category_id = classify_customer(r_score, f_score, m_score)
        
        results.append({
            "customerid": cid,
            "recency_days": int(recency_days),
            "frequency": int(freq),
            "monetary": float(money),
            "rScore": r_score,
            "fScore": f_score,
            "mScore": m_score,
            "categoryID": category_id,
        })

    return results


def _make_labels(data: List[Dict[str, Any]], churn_threshold_days: int) -> List[int]:
    """舊版標籤生成（基於當前 recency，有洩漏風險）"""
    return [1 if int(d.get("recency_days", 0)) > churn_threshold_days else 0 for d in data]


def _build_rfm_with_future_label(
    as_of: Optional[str] = None,
    window_days: int = 365,
    churn_threshold_days: int = 90,
) -> List[Dict[str, Any]]:
    """
    建立訓練資料，使用「未來視窗」定義流失標籤：
    - 特徵：過去 window_days 的 RFM 行為
    - 標籤：as_of 之後 churn_threshold_days 天內是否有再消費
        0 = 未流失（未來有消費）
        1 = 流失（未來沒有消費）
    """
    as_of_date = _parse_as_of(as_of)
    window_start = as_of_date - timedelta(days=window_days)
    future_end = as_of_date + timedelta(days=churn_threshold_days)

    # 先用原本的 _build_rfm 計算過去行為（特徵）
    base_rows = _build_rfm(as_of=as_of, window_days=window_days)
    if not base_rows:
        return []

    # 查詢「未來視窗」內有消費的客戶
    future_qs = (
        Transaction.objects
        .filter(transdate__gt=as_of_date, transdate__lte=future_end)
        .values_list("customerid", flat=True)
        .distinct()
    )
    future_active: set = {int(cid) for cid in future_qs if cid is not None}

    # 為每位客戶加上標籤
    results: List[Dict[str, Any]] = []
    for row in base_rows:
        cid = int(row.get("customerid"))
        # 未來有消費 → label=0（未流失）
        # 未來沒消費 → label=1（流失）
        label = 0 if cid in future_active else 1
        new_row = dict(row)
        new_row["label"] = int(label)
        results.append(new_row)

    return results


def train_churn_model(
    as_of: Optional[str] = None,
    window_days: int = 365,
    churn_threshold_days: int = 90,
    iterations: int = 300,
    depth: int = 6,
    learning_rate: float = 0.1,
    val_size: float = 0.2,
    use_recency: bool = False,
    use_rfm_scores: bool = True,  # 新增：預設使用 RFM 分數
) -> Dict[str, Any]:
    if not _CATBOOST_AVAILABLE:
        raise RuntimeError("catboost 未安裝，請先安裝 catboost 後再訓練")

    # 使用未來標籤版本（避免標籤洩漏）
    data = _build_rfm_with_future_label(
        as_of=as_of,
        window_days=window_days,
        churn_threshold_days=churn_threshold_days,
    )
    if not data:
        return {"message": "沒有可用的交易資料，無法訓練", "samples": 0}

    # 特徵選擇：優先使用 RFM 分數
    if use_rfm_scores:
        feature_names = ["rScore", "fScore", "mScore"]
        X = [[float(d.get(k, 0)) for k in feature_names] for d in data]
    else:
        # 使用原始 RFM 數值
        feature_names = ["frequency", "monetary"] + (["recency_days"] if use_recency else [])
        X = [[float(d.get(k, 0.0)) for k in feature_names] for d in data]
    
    # 使用 _build_rfm_with_future_label 已經計算好的標籤
    y = [int(row.get("label", 0)) for row in data]

    # 嘗試切分驗證集；若無 sklearn 則全量訓練
    try:
        from sklearn.model_selection import train_test_split
        X_tr, X_val, y_tr, y_val = train_test_split(
            X, y, test_size=val_size, random_state=42, stratify=y
        )
        have_val = True
    except Exception:
        X_tr, y_tr, X_val, y_val, have_val = X, y, [], [], False

    model = CatBoostClassifier(
        iterations=iterations,
        learning_rate=learning_rate,
        depth=depth,
        loss_function="Logloss",
        random_seed=42,
        verbose=False,
        auto_class_weights="Balanced",
    )
    model.fit(X_tr, y_tr, verbose=False)

    val_metrics: Dict[str, Any] = {
        "val_accuracy": None,
        "val_auc": None,
        "val_f1": None,
        "val_precision": None,
        "val_recall": None,
    }
    if have_val and X_val:
        try:
            from sklearn.metrics import accuracy_score, roc_auc_score, f1_score, precision_score, recall_score
            y_val_pred = model.predict(X_val)
            y_val_pred = [int(p[0]) if isinstance(p, (list, tuple)) else int(p) for p in y_val_pred]
            
            # 計算 AUC（需要正類機率）
            y_val_prob = None
            val_auc = None
            if len(set(y_val)) > 1:
                try:
                    proba = model.predict_proba(X_val)
                    # CatBoost 回傳 numpy array，shape (n_samples, n_classes)
                    # 取第二列（正類 label=1 的機率）
                    if hasattr(proba, 'shape') and len(proba.shape) == 2:
                        y_val_prob = proba[:, 1].tolist()
                    else:
                        y_val_prob = [float(p[1]) if isinstance(p, (list, tuple)) and len(p) > 1 else float(p) for p in proba]
                    val_auc = float(roc_auc_score(y_val, y_val_prob))
                except Exception as e:
                    val_auc = None
            
            val_metrics.update({
                "val_accuracy": float(accuracy_score(y_val, y_val_pred)),
                "val_auc": val_auc,
                "val_f1": float(f1_score(y_val, y_val_pred, zero_division=0)),
                "val_precision": float(precision_score(y_val, y_val_pred, zero_division=0)),
                "val_recall": float(recall_score(y_val, y_val_pred, zero_division=0)),
            })
        except Exception as e:
            pass

    # 儲存模型與中繼資料
    model.save_model(_model_path())
    meta = {
        "as_of": _parse_as_of(as_of).isoformat() if as_of else date.today().isoformat(),
        "window_days": window_days,
        "churn_threshold_days": churn_threshold_days,
        "features": feature_names,
        "use_recency": use_recency,
        "use_rfm_scores": use_rfm_scores,
        "samples_total": len(X),
        "samples_train": len(X_tr),
        "samples_val": len(X_val),
        **val_metrics,
    }
    try:
        with open(_meta_path(), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)
    except Exception:
        pass

    # 四捨五入輸出
    out = {
        "message": "模型訓練完成",
        "model_path": _model_path(),
        **meta,
    }
    for k in ["val_accuracy", "val_auc", "val_f1", "val_precision", "val_recall"]:
        if out[k] is not None:
            out[k] = round(float(out[k]), 4)
    return out


def _risk_level(p: float) -> str:
    if p >= 0.66:
        return "high"
    if p >= 0.33:
        return "medium"
    return "low"


def _risk_from_rfm(row: Dict[str, Any]) -> float:
    r = max(0, float(row.get("recency_days", 0)))
    f = max(0, float(row.get("frequency", 0)))
    m = max(0, float(row.get("monetary", 0.0)))
    r_norm = min(1.0, r / 180.0)
    f_norm = 1.0 - min(1.0, f / 6.0)
    m_norm = 1.0 - min(1.0, m / 10000.0)
    score = 0.5 * r_norm + 0.3 * f_norm + 0.2 * m_norm
    return max(0.0, min(1.0, score))


def predict_churn(
    as_of: Optional[str] = None,
    window_days: int = 365,
) -> List[Dict[str, Any]]:
    rfm = _build_rfm(as_of=as_of, window_days=window_days)

    model_path = _model_path()
    meta_path = _meta_path()
    use_model = _CATBOOST_AVAILABLE and os.path.exists(model_path)

    if use_model:
        model = CatBoostClassifier()
        model.load_model(model_path)
        # 預設使用 RFM 分數
        features = ["rScore", "fScore", "mScore"]
        try:
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    features = meta.get("features", features)
        except Exception:
            pass

        X = [[float(d.get(k, 0)) for k in features] for d in rfm]
        proba = model.predict_proba(X)

        # 處理 CatBoost 回傳的機率（numpy array 或 list）
        if hasattr(proba, 'shape') and len(proba.shape) == 2:
            # numpy array: shape (n_samples, 2)，取第二列（正類機率）
            y_prob = proba[:, 1].tolist()
        else:
            # list of lists/tuples
            y_prob = [float(p[1]) if isinstance(p, (list, tuple)) and len(p) > 1 else float(p) for p in proba]

        results: List[Dict[str, Any]] = []
        for row, prob in zip(rfm, y_prob):
            prob = max(0.0, min(1.0, float(prob)))
            results.append({**row, "probability": prob, "risk_level": _risk_level(prob)})
        results.sort(key=lambda x: x["probability"], reverse=True)
        return results

    # 無模型：退化為啟發式
    results: List[Dict[str, Any]] = []
    for row in rfm:
        p = _risk_from_rfm(row)
        results.append({**row, "probability": p, "risk_level": _risk_level(p)})
    results.sort(key=lambda x: x["probability"], reverse=True)
    return results


def predict_churn_for_customer(
    customer_id: int,
    as_of: Optional[str] = None,
    window_days: int = 365,
) -> Dict[str, Any]:
    res = predict_churn(as_of=as_of, window_days=window_days)
    for r in res:
        if int(r.get("customerid")) == int(customer_id):
            return r
    raise ValueError(f"customer_id={customer_id} 無交易紀錄或不在視窗內")

