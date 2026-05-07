"""
Tool: csv_stats
功能：统计 CSV 的基本信息
"""

import pandas as pd

def csv_stats(file_path: str) -> dict:
    df = pd.read_csv(file_path)
    return {
        "total_rows": len(df),
        "columns": list(df.columns),
        "null_counts": df.isna().sum().to_dict()
    }