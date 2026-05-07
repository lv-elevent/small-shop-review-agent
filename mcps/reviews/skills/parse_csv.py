"""
Skill: parse_csv
功能：解析评论 CSV 文件成 DataFrame
"""

import pandas as pd
from pathlib import Path

def parse_review_csv(file_path: str) -> pd.DataFrame:
    """
    解析 CSV 文件并标准化列名
    file_path: 上传后保存的本地路径
    """
    df = pd.read_csv(file_path)
    # 标准化列名
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df