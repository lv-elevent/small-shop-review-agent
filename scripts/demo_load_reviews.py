import csv
from pathlib import Path
from loguru import logger
from src.small_shop_agent.storage.sqlite_session import get_session
from datetime import datetime
import json

BATCH_ID = "batch_demo_1"
CSV_PATH = Path("data/uploads/sample_reviews.csv")

TRACE_ID = f"trace_{BATCH_ID}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

TRACE_STEPS = [
    "input_validation",
    "data_cleaning",
    "classification",
    "sentiment_analysis",
    "issue_aggregation",
    "evidence_check",
    "reply_drafting",
    "safety_check",
    "human_approval",
    "eval_run"
]

def insert_batch_and_reviews():
    """读取 CSV 并写入 review_batches + reviews"""
    if not CSV_PATH.exists():
        logger.error(f"CSV 文件不存在: {CSV_PATH}")
        return

    with get_session() as conn:
        # 写 batch
        conn.execute("""
        INSERT OR IGNORE INTO review_batches(batch_id, store_type, source_type, total_rows)
        VALUES (?, 'coffee_shop', 'demo_mode', ?)
        """, (BATCH_ID, sum(1 for _ in open(CSV_PATH, encoding="utf-8")) - 1))

        # 写 reviews
        reader = csv.DictReader(open(CSV_PATH, encoding="utf-8"))
        for row in reader:
            review_id = row["review_id"]
            rating = int(row["rating"])
            text = row["review_text"]
            conn.execute("""
            INSERT OR IGNORE INTO reviews(batch_id, review_id, review_text, rating)
            VALUES (?, ?, ?, ?)
            """, (BATCH_ID, review_id, text, rating))

    logger.success("Batch 和 Reviews 写入完成")

def insert_demo_analysis_and_traces():
    """写默认 review_analysis + traces"""
    with get_session() as conn:
        # review_analysis 默认主题/情绪
        cursor = conn.execute("SELECT review_id, review_text FROM reviews WHERE batch_id=?", (BATCH_ID,))
        for review_id, text in cursor.fetchall():
            # 默认填充
            topics = json.dumps(["service"])
            primary_topic = "service"
            sentiment = "positive" if int(text.count("好")) > 0 else "negative"
            severity = 1 if sentiment == "positive" else 4
            is_negative_candidate = 1 if sentiment == "negative" else 0
            conn.execute("""
            INSERT OR IGNORE INTO review_analysis(batch_id, review_id, topics, primary_topic, sentiment, severity, is_negative_candidate)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (BATCH_ID, review_id, topics, primary_topic, sentiment, severity, is_negative_candidate))

        # Trace 写入每一步
        for step in TRACE_STEPS:
            conn.execute("""
            INSERT INTO traces(trace_id, batch_id, step_name, input_summary, output_summary, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (TRACE_ID, BATCH_ID, step, f"Demo input for {step}", f"Demo output for {step}", "passed"))

    logger.success("Review Analysis + Trace 写入完成")

if __name__ == "__main__":
    insert_batch_and_reviews()
    insert_demo_analysis_and_traces()
    logger.success("第一阶段 Demo 数据加载完成")