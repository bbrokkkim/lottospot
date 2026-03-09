"""DB에서 최신 round + 1 출력 (GitHub Actions에서 시작 회차 결정용)"""
import os
import pymysql
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

conn = pymysql.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 3306)),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASS", "12341234"),
    database=os.getenv("DB_NAME", "lottospot"),
    charset="utf8mb4",
)
cur = conn.cursor()
cur.execute("SELECT COALESCE(MAX(round), 0) + 1 FROM winning_history")
print(cur.fetchone()[0])
cur.close()
conn.close()
