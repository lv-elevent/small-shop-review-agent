"""
简单测试 CSV 解析与校验
"""

from mcps.reviews.skills.parse_csv import parse_review_csv
from mcps.reviews.skills.validate_data import validate_data

if __name__ == "__main__":
    df = parse_review_csv("data/uploads/sample_reviews.csv")
    print("Parsed DataFrame:", df.head())
    results = validate_data(df)
    print("Validate Results:", results)