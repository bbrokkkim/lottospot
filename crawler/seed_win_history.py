"""
seed_win_history.py
기존 lotto_store 판매점에 현실적인 당첨 이력을 생성합니다.
lotto_store 테이블은 건드리지 않고 winning_history만 적재합니다.

실행:
  python seed_win_history.py
  python seed_win_history.py --rounds 50  # 최근 50회차만
"""
import argparse
import os
import random
from datetime import date, timedelta

import pymysql
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# 1회차 시작일: 2002-12-07, 매주 토요일
ROUND_1_DATE = date(2002, 12, 7)
CURRENT_ROUND = 1163  # 2026년 3월 기준 대략적 회차


def round_to_date(rnd: int) -> date:
    return ROUND_1_DATE + timedelta(weeks=rnd - 1)


def main(num_rounds: int):
    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", "12341234"),
        database=os.getenv("DB_NAME", "lottospot"),
        charset="utf8mb4",
    )
    cur = conn.cursor()

    # 기존 이력 초기화
    cur.execute("TRUNCATE TABLE winning_history")
    conn.commit()
    print("기존 당첨 이력 초기화 완료")

    # 판매점 ID 조회
    cur.execute("SELECT id FROM lotto_store ORDER BY id")
    store_ids = [row[0] for row in cur.fetchall()]
    total_stores = len(store_ids)
    print(f"판매점 {total_stores}개 로드")

    # 처리 회차 범위
    start_round = max(1, CURRENT_ROUND - num_rounds + 1)
    end_round = CURRENT_ROUND

    histories = []
    used = set()  # (store_id, round, rank) 중복 방지

    # 실제 당첨 통계 기반:
    # 1등: 회차당 평균 8개 당첨점 (자동 6 + 수동 2 정도)
    # 2등: 회차당 평균 30~50개 당첨점
    for rnd in range(start_round, end_round + 1):
        win_date = round_to_date(rnd).isoformat()

        # 1등 당첨점 (회차당 5~12개)
        n_1st = random.randint(5, 12)
        winners_1st = random.sample(store_ids, min(n_1st, total_stores))
        for sid in winners_1st:
            key = (sid, rnd, 1)
            if key not in used:
                used.add(key)
                histories.append((sid, rnd, 1, win_date))

        # 2등 당첨점 (회차당 30~60개)
        n_2nd = random.randint(30, 60)
        winners_2nd = random.sample(store_ids, min(n_2nd, total_stores))
        for sid in winners_2nd:
            key = (sid, rnd, 2)
            if key not in used:
                used.add(key)
                histories.append((sid, rnd, 2, win_date))

    print(f"{start_round}~{end_round}회차 ({num_rounds}회) 이력 생성: {len(histories)}건")

    # 일괄 삽입
    sql = """
        INSERT IGNORE INTO winning_history (store_id, round, win_rank, win_date, created_at)
        VALUES (%s, %s, %s, %s, NOW())
    """
    batch_size = 1000
    for i in range(0, len(histories), batch_size):
        cur.executemany(sql, histories[i:i + batch_size])
        conn.commit()
        print(f"  {min(i + batch_size, len(histories))}/{len(histories)} 삽입...")

    cur.close()
    conn.close()

    rank1 = [h for h in histories if h[2] == 1]
    rank2 = [h for h in histories if h[2] == 2]
    stores_with_1st = len(set(h[0] for h in rank1))
    stores_with_2nd = len(set(h[0] for h in rank2))

    print(f"\n=== 완료 ===")
    print(f"총 이력: {len(histories)}건")
    print(f"1등: {len(rank1)}건 ({stores_with_1st}개 판매점, {stores_with_1st/total_stores*100:.1f}%)")
    print(f"2등: {len(rank2)}건 ({stores_with_2nd}개 판매점, {stores_with_2nd/total_stores*100:.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=200, help="생성할 회차 수 (기본 200회)")
    args = parser.parse_args()
    main(args.rounds)
