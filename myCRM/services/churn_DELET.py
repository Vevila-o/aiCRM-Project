from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
import os

from django.db.models import Count, Sum, Max

try:
    from catboost import CatBoostClassifier
    _CATBOOST_AVAILABLE = True
except Exception:  # pragma: no cover
    _CATBOOST_AVAILABLE = False

from myCRM.models import Transaction
from myCRM.models import Customer  # 修正拼字錯誤
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    roc_auc_score,
    f1_score,
    precision_score,
    recall_score,
)
from .rfm_count import rfm_score_from_raw

##工具

# 將字串轉為日期 'date' 物件
def _parse_as_of(as_of: Optional[str]) -> date:
    if not as_of:  # 如果資料中沒有提供日期就選用今天
        return date.today()
    # 支援 yyyy-mm-dd
    return datetime.strptime(as_of, "%Y-%m-%d").date()


# 模型檔案的儲存位置
def _model_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "churn_model.cbm")


# 建立 RFM 特徵
def _build_rfm(as_of: Optional[str] = None, window_days: int = 365) -> List[Dict[str, Any]]:
    """
    以交易主檔計算每位顧客 RFM：
    - recency_days: 距離最近一筆交易的天數（所有歷史，不限視窗）
    - frequency: 視窗內交易次數
    - monetary: 視窗內交易金額總和
    僅納入有歷史交易紀錄的客戶。
    """
    # 交易天數解釋
    """ 
    as_of_date = 想要資料計算到哪一天，此日期為今天(ex:紀錄日期今天為11/13)
    window_days = 是過去多少天的交易紀錄(ex:預設為365天，代表從11/13往前推365天到11/14的交易紀錄都納入計算)，
                  目的是避免顧客太久以前的資料加進來計算 
    as_of_date - timedelta(days=window_days) = 365天前的日期
    ex : 2025/11/13 - 365天 = 2024/11/14
    """
    as_of_date = _parse_as_of(as_of)
    window_start = as_of_date - timedelta(days=window_days) #windows_days 代表過去到今天的全部天數


# 最近交易日
    """ 
    這像是sql的group by 功能，找出每個customer的最後交易日期
    SQL:
        SELECT customerid, MAX(transdate) AS last_date
        FROM Transaction
        WHERE transdate <= as_of_date
        GROUP BY customerid;
    """
    last_dates = (
        Transaction.objects
        .filter(transdate__lte=as_of_date) # 交易日期 = 視窗起始日期
        .values("customerid")
        .annotate(last_date=Max("transdate"))
    )
   

    last_date_by_cust: Dict[int, date] = {} # 剛剛的尋找結果會放入在這個字典裡面
    for row in last_dates:
        cid = row.get("customerid")
        if cid is None:
            continue
        last_date_by_cust[int(cid)] = row.get("last_date")

# 視窗內的 frequency / monetary
    window_stats = (
        Transaction.objects
        # filter 只抓取式窗範圍內的交易
          # transdate__gte=window_start 交易日期 = 視窗起始日期
          # transdate__lte=as_of_date 交易日期 = 當天(前面設定為今天)
        .filter(transdate__gte=window_start, transdate__lte=as_of_date) 
        .values("customerid") # 之後只關心customerid此欄，意思為要以customerid為單位做group by
        # annotate = 幫每個customerid計算剩下欄位的次數跟總和，這邊要計算F M
        .annotate(freq=Count("transactionid"), money=Sum("totalprice"))
    )

    freq_by_cust: Dict[int, int] = {}
    money_by_cust: Dict[int, float] = {}
    for row in window_stats:
        cid = row.get("customerid")
        if cid is None:
            continue
        freq_by_cust[int(cid)] = int(row.get("freq") or 0)
        # 可能為 None
        total = row.get("money")
        money_by_cust[int(cid)] = float(total) if total is not None else 0.0

    results: List[Dict[str, Any]] = []
    for cid, last_dt in last_date_by_cust.items():
        recency_days = (as_of_date - last_dt).days if last_dt else 10**9
        freq = freq_by_cust.get(cid, 0)
        money = money_by_cust.get(cid, 0.0)
        r_score, f_score, m_score = rfm_score_from_raw(recency_days, freq, money)

        results.append({
            "customerid": cid,
            "recency_days": int(recency_days),
            "frequency": int(freq),
            "monetary": float(money),
            "rScore": r_score,
            "fScore": f_score,
            "mScore": m_score,
        })

    return results


def _make_labels(data: List[Dict[str, Any]], churn_threshold_days: int = 90) -> List[int]:
    """以 recency_days > 閾值 當作流失標籤（1=流失，0=未流失）。"""
    labels: List[int] = []
    for row in data:
        labels.append(1 if int(row.get("recency_days", 0)) > churn_threshold_days else 0)
    return labels


def _risk_from_rfm(row: Dict[str, Any]) -> float:
    """
    無模型時的簡易風險分數（0~1）：
    - 最近購買時間越久（recency_days 大） → 風險越高
    - 購買次數越少（frequency 小） → 風險越高
    - 消費金額越低（monetary 小） → 風險越高
    """
    r = max(0, float(row.get("recency_days", 0)))
    f = max(0, float(row.get("frequency", 0)))
    m = max(0, float(row.get("monetary", 0.0)))

    # 粗略正規化，避免除以零：
    r_norm = min(1.0, r / 180.0)       # 超過 180 天就當成最高風險
    f_norm = 1.0 - min(1.0, f / 6.0)   # 6 次以後視為安全，以下風險高
    m_norm = 1.0 - min(1.0, m / 10000.0)  # 消費越高風險越低

    # 權重可調（你可以自己改比例）
    score = 0.5 * r_norm + 0.3 * f_norm + 0.2 * m_norm
    return max(0.0, min(1.0, score))


def _risk_level(p: float) -> str:
    if p >= 0.66:
        return "high"
    if p >= 0.33:
        return "medium"
    return "low"


def train_churn_model(
    as_of: Optional[str] = None,
    window_days: int = 365,
    churn_threshold_days: int = 90,
    iterations: int = 300,
    depth: int = 6,
    learning_rate: float = 0.1,
    val_size: float = 0.2,
    use_recency: bool = False,
    use_rfm_scores: bool = True,
    auto_class_weights: Optional[str] = "Balanced",
) -> Dict[str, Any]:
    """
    訓練 CatBoost 並在驗證集回報評估指標。
    - use_recency=False 可避免把標籤規則的主要訊號（recency_days）直接暴露給模型，降低洩漏風險。
    - val_size 決定驗證集比例。
    """
    if not _CATBOOST_AVAILABLE:
        raise RuntimeError("catboost 未安裝，請先於 requirements.txt 加入 catboost 並安裝依賴。")

    # 準備資料
    data = _build_rfm(as_of=as_of, window_days=window_days)
    if not data:
        return {"message": "沒有可用的交易資料，無法訓練", "samples": 0}

    # 特徵組裝
    if use_rfm_scores:
        # 用 自建RFM模型分數當特徵
        X = [[d["rScore"], d["fScore"], d["mScore"]] for d in data]
        feature_names = ["rScore", "fScore", "mScore"]
    else:
        # 保留原來的選項：用原始 R/F/M
        if use_recency:
            X = [[d["recency_days"], d["frequency"], d["monetary"]] for d in data]
            feature_names = ["recency_days", "frequency", "monetary"]
        else:
            X = [[d["frequency"], d["monetary"]] for d in data]
            feature_names = ["frequency", "monetary"]

    y = _make_labels(data, churn_threshold_days=churn_threshold_days)

    # 檢查類別數量
    num_pos = sum(1 for t in y if t == 1)
    num_neg = len(y) - num_pos
    has_both_classes = num_pos > 0 and num_neg > 0

    # 單一類別時無法做 stratify 或算 AUC -> 退而回報訓練集表觀分數
    if not has_both_classes or val_size <= 0 or val_size >= 1:
        model = CatBoostClassifier(
            iterations=iterations,
            learning_rate=learning_rate,
            depth=depth,
            loss_function="Logloss",
            random_seed=42,
            verbose=False,
            auto_class_weights=auto_class_weights,
        )
        model.fit(X, y, verbose=False)

        # 訓練集表觀指標（僅作參考）
        y_pred = model.predict(X)
        y_pred = [int(p[0]) if isinstance(p, (list, tuple)) else int(p) for p in y_pred]
        try:
            # predict_proba 取正類機率
            proba = model.predict_proba(X)
            y_prob = [float(p[1]) if isinstance(p, (list, tuple)) else float(p) for p in proba]
            auc = float(roc_auc_score(y, y_prob)) if has_both_classes else None
        except Exception:
            auc = None

        path = _model_path()
        model.save_model(path)

        return {
            "message": "模型訓練完成（只有單一類別或無法切分，以下為訓練集指標、僅供參考）",
            "model_path": path,
            "samples": len(X),
            "as_of": _parse_as_of(as_of).isoformat() if as_of else date.today().isoformat(),
            "window_days": window_days,
            "churn_threshold_days": churn_threshold_days,
            "features": feature_names,
            "train_accuracy": round(float(accuracy_score(y, y_pred)), 4),
            "train_auc": round(float(auc), 4) if auc is not None else None,
        }

    # 正常情況：切訓練/驗證
    X_tr, X_val, y_tr, y_val = train_test_split(
        X, y,
        test_size=val_size,
        random_state=42,
        stratify=y,
    )

    model = CatBoostClassifier(
        iterations=iterations,
        learning_rate=learning_rate,
        depth=depth,
        loss_function="Logloss",
        random_seed=42,
        verbose=False,
        auto_class_weights=auto_class_weights,
    )
    model.fit(X_tr, y_tr, verbose=False)

    # 驗證集預測
    y_val_pred = model.predict(X_val)
    y_val_pred = [int(p[0]) if isinstance(p, (list, tuple)) else int(p) for p in y_val_pred]

        # 取正類機率（AUC/F1/Precision/Recall 等要用）
    try:
        proba_val = model.predict_proba(X_val)

        def get_pos_proba(p):
            # p 可能是 list / tuple / numpy array / 單一 float
            if isinstance(p, (list, tuple)):
                if len(p) >= 2:
                    # 二元分類常見情況：[p0, p1] → 取正類 p1
                    return float(p[1])
                elif len(p) == 1:
                    # 只有一個機率，就當成正類機率
                    return float(p[0])
                else:
                    return 0.5
            try:
                # numpy array 或單一數值
                return float(p)
            except Exception:
                return 0.5

        y_val_prob = [get_pos_proba(p) for p in proba_val]
    except Exception:
        y_val_prob = None


    # 計算指標
    val_accuracy = float(accuracy_score(y_val, y_val_pred))
    # AUC 需要兩個類別且有機率
    if y_val_prob is not None and len(set(y_val)) > 1:
        try:
            val_auc = float(roc_auc_score(y_val, y_val_prob))
        except Exception:
            val_auc = None
    else:
        val_auc = None

    val_f1 = float(f1_score(y_val, y_val_pred, zero_division=0))
    val_precision = float(precision_score(y_val, y_val_pred, zero_division=0))
    val_recall = float(recall_score(y_val, y_val_pred, zero_division=0))

    # 儲存模型
    path = _model_path()
    model.save_model(path)

    return {
        "message": "模型訓練完成",
        "model_path": path,
        "samples_total": len(X),
        "samples_train": len(X_tr),
        "samples_val": len(X_val),
        "as_of": _parse_as_of(as_of).isoformat() if as_of else date.today().isoformat(),
        "window_days": window_days,
        "churn_threshold_days": churn_threshold_days,
        "features": feature_names,
        "use_recency": use_recency,
        "val_accuracy": round(val_accuracy, 4),
        "val_auc": round(val_auc, 4) if val_auc is not None else None,
        "val_f1": round(val_f1, 4),
        "val_precision": round(val_precision, 4),
        "val_recall": round(val_recall, 4),
    }
def predict_churn(
    as_of: Optional[str] = None,
    window_days: int = 365,
) -> List[Dict[str, Any]]:
    """
    以已訓練模型進行預測；若無模型，退化為基於 RFM 的啟發式風險分數。
    回傳每位客戶的：customerid, recency_days, frequency, monetary, probability, risk_level。
    """
    rfm = _build_rfm(as_of=as_of, window_days=window_days)

    path = _model_path()
    use_model = _CATBOOST_AVAILABLE and os.path.exists(path)

    if use_model:
        model = CatBoostClassifier()
        model.load_model(path)

        # 和訓練時保持一致：用 rScore / fScore / mScore
        X = [[d["rScore"], d["fScore"], d["mScore"]] for d in rfm]




        proba = model.predict_proba(X)

        # 兼容 list 或 numpy array
        def get_pos(p):
            try:
                # [p0, p1]
                return float(p[1])
            except Exception:
                return float(p)

        probs = [get_pos(p) for p in proba]
        results: List[Dict[str, Any]] = []
        for row, p in zip(rfm, probs):
            p = max(0.0, min(1.0, float(p)))
            results.append({
                **row,
                "probability": p,
                "risk_level": _risk_level(p),
            })
        # 依風險排序
        results.sort(key=lambda x: x["probability"], reverse=True)
        return results

    # 無模型：啟發式分數（用 _risk_from_rfm）
    results: List[Dict[str, Any]] = []
    for row in rfm:
        p = _risk_from_rfm(row)  # 0~1 的風險機率估計
        results.append({
            **row,
            "probability": p,
            "risk_level": _risk_level(p),
        })
    results.sort(key=lambda x: x["probability"], reverse=True)
    return results


def predict_churn_for_customer(
    customer_id: int,
    as_of: Optional[str] = None,
    window_days: int = 365,
) -> Dict[str, Any]:
    """回傳單一顧客的預測結果（若找不到顧客交易紀錄則拋錯）。"""
    results = predict_churn(as_of=as_of, window_days=window_days)
    for row in results:
        if int(row.get("customerid")) == int(customer_id):
            return row
    raise ValueError(f"customer_id={customer_id} 無交易紀錄或不存在於訓練/視窗內")
