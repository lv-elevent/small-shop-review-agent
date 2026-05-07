"""
主 Agent 执行流程示例
"""

from mcps.reviews.skills.parse_csv import parse_review_csv
from mcps.reviews.skills.validate_data import validate_data
from mcps.reviews.skills.generate_draft import generate_reply_draft
from mcps.reviews.tools.csv_stats import csv_stats

def run_review_pipeline(file_path: str):
    # 1. 解析 CSV
    df = parse_review_csv(file_path)
    # 2. 校验数据
    results = validate_data(df)
    # 3. 获取统计信息
    stats = csv_stats(file_path)
    print("--- CSV 基本统计 ---")
    print(stats)
    print("--- 校验结果 ---")
    print(results)
    # 4. 生成 demo 草稿
    reviews = df["review_text"].tolist()[:5]
    for idx, txt in enumerate(reviews):
        draft = generate_reply_draft(txt)
        print(f"[Draft {idx+1}]:", draft)

if __name__ == "__main__":
    run_review_pipeline("data/uploads/sample_reviews.csv")