"""
偵測 JSON 序列化問題
"""
import json
import numpy as np

# 測試不同的 numpy 類型
test_data = {
    'float32': np.float32(1.5),
    'float64': np.float64(2.5),
    'int32': np.int32(10),
    'int64': np.int64(20),
    'python_float': float(np.float32(1.5)),
    'python_int': int(np.int32(10)),
    'round_float32': round(np.float32(1.5), 2),
    'float_round_float32': float(round(np.float32(1.5), 2)),
}

for key, value in test_data.items():
    try:
        json.dumps({key: value})
        print(f"✅ {key}: {type(value).__name__} = {value} - OK")
    except TypeError as e:
        print(f"❌ {key}: {type(value).__name__} = {value} - FAIL: {e}")
