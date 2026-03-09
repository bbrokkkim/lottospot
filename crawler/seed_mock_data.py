"""
seed_mock_data.py
서울 전역 로또 판매점 현실적 목업 데이터를 생성하여 DB에 적재합니다.
실제 판매점 분포(약 6,000개)를 반영해 구별로 현실적인 좌표와 당첨 이력을 생성합니다.

실행:
  python seed_mock_data.py
  python seed_mock_data.py --stores 300  # 개수 지정
"""
import argparse
import os
import random
from datetime import date, timedelta

import pymysql
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# 서울 25개 구 중심 좌표 + 판매점 비중 (인구 밀도 반영)
DISTRICTS = [
    ("강남구",  37.5172, 127.0473, 12),
    ("서초구",  37.4837, 127.0324,  9),
    ("송파구",  37.5145, 127.1059, 10),
    ("마포구",  37.5614, 126.9088,  8),
    ("영등포구",37.5264, 126.8963,  8),
    ("강서구",  37.5509, 126.8495,  7),
    ("노원구",  37.6542, 127.0568,  7),
    ("관악구",  37.4784, 126.9516,  6),
    ("은평구",  37.6027, 126.9291,  6),
    ("강북구",  37.6396, 127.0253,  5),
    ("도봉구",  37.6688, 127.0471,  5),
    ("중랑구",  37.6063, 127.0927,  5),
    ("성북구",  37.5894, 127.0167,  5),
    ("동대문구",37.5744, 127.0396,  5),
    ("광진구",  37.5384, 127.0822,  5),
    ("성동구",  37.5635, 127.0370,  5),
    ("용산구",  37.5326, 126.9902,  4),
    ("중구",    37.5641, 126.9979,  4),
    ("종로구",  37.5730, 126.9794,  4),
    ("동작구",  37.5124, 126.9393,  4),
    ("강동구",  37.5301, 127.1237,  4),
    ("서대문구",37.5791, 126.9368,  4),
    ("양천구",  37.5171, 126.8667,  4),
    ("구로구",  37.4955, 126.8877,  4),
    ("금천구",  37.4602, 126.9001,  3),
]

STORE_NAME_PREFIXES = ["행운","대박","황금","복권","로또","희망","미래","기쁨","천운","행복",
                        "럭키","명당","일등","당첨","꿈의","신나는","즐거운","최고","으뜸","제일"]
STORE_NAME_SUFFIXES = ["복권방","로또방","복권","판매점","복권나라","로또천국","복권점","슈퍼","편의점","마트"]

ROAD_NAMES = ["대로","로","길","로","로","대로","로","길"]

def rand_name():
    return random.choice(STORE_NAME_PREFIXES) + random.choice(STORE_NAME_SUFFIXES)

def rand_address(district):
    road_num = random.randint(1, 200)
    bldg_num = random.randint(1, 50)
    road = f"{district[:2]}{random.choice(ROAD_NAMES)}"
    return f"서울특별시 {district} {road} {road_num}", f"{bldg_num}호"

def rand_coord(base_lat, base_lng, spread=0.025):
    return (
        round(base_lat + random.uniform(-spread, spread), 6),
        round(base_lng + random.uniform(-spread, spread), 6),
    )

def generate_stores(total):
    total_weight = sum(w for *_, w in DISTRICTS)
    stores = []
    for name, blat, blng, weight in DISTRICTS:
        count = max(1, round(total * weight / total_weight))
        for _ in range(count):
            lat, lng = rand_coord(blat, blng)
            addr, detail = rand_address(name)
            stores.append({
                "name": rand_name(),
                "address": addr,
                "address_detail": detail,
                "lat": lat,
                "lng": lng,
                "phone": f"02-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
                "is_open": 1,
            })
    return stores[:total]

def generate_win_history(store_ids):
    """판매점 ID 목록에 당첨 이력 생성. 약 15% 판매점에 1등, 40%에 2등 이력."""
    histories = []
    used = set()

    # 1등 당첨 (상위 15%)
    winners_1st = random.sample(store_ids, max(1, int(len(store_ids) * 0.15)))
    for sid in winners_1st:
        wins = random.randint(1, 5)
        base_date = date(2020, 1, 1)
        used_rounds = set()
        for _ in range(wins):
            for attempt in range(20):
                days = random.randint(0, 4 * 365)
                rnd = 900 + days // 7
                key = (sid, rnd, 1)
                if key not in used and rnd not in used_rounds:
                    used.add(key)
                    used_rounds.add(rnd)
                    histories.append({
                        "store_id": sid,
                        "round": rnd,
                        "win_rank": 1,
                        "win_date": (base_date + timedelta(days=days)).isoformat(),
                    })
                    break

    # 2등 당첨 (40%)
    winners_2nd = random.sample(store_ids, max(1, int(len(store_ids) * 0.40)))
    for sid in winners_2nd:
        wins = random.randint(1, 8)
        base_date = date(2020, 1, 1)
        for _ in range(wins):
            for attempt in range(20):
                days = random.randint(0, 4 * 365)
                rnd = 900 + days // 7
                key = (sid, rnd, 2)
                if key not in used:
                    used.add(key)
                    histories.append({
                        "store_id": sid,
                        "round": rnd,
                        "win_rank": 2,
                        "win_date": (base_date + timedelta(days=days)).isoformat(),
                    })
                    break

    return histories


def main(total_stores: int):
    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", "12341234"),
        database=os.getenv("DB_NAME", "lottospot"),
        charset="utf8mb4",
    )
    cur = conn.cursor()

    # 기존 목업 데이터 초기화
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    cur.execute("TRUNCATE TABLE winning_history")
    cur.execute("TRUNCATE TABLE lotto_store")
    cur.execute("SET FOREIGN_KEY_CHECKS=1")
    conn.commit()
    print(f"기존 데이터 초기화 완료")

    # 판매점 삽입
    stores = generate_stores(total_stores)
    sql = """
        INSERT INTO lotto_store
            (name, address, address_detail, lat, lng, location, phone, is_open, created_at, updated_at)
        VALUES
            (%s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s, %s, NOW(), NOW())
    """
    for s in stores:
        cur.execute(sql, (
            s["name"], s["address"], s["address_detail"],
            s["lat"], s["lng"],
            f"POINT({s['lat']} {s['lng']})",
            s["phone"], s["is_open"],
        ))
    conn.commit()

    # 삽입된 ID 조회
    cur.execute("SELECT id FROM lotto_store ORDER BY id")
    store_ids = [row[0] for row in cur.fetchall()]
    print(f"판매점 {len(store_ids)}건 삽입 완료")

    # 당첨 이력 삽입
    histories = generate_win_history(store_ids)
    sql2 = """
        INSERT IGNORE INTO winning_history (store_id, round, win_rank, win_date, created_at)
        VALUES (%s, %s, %s, %s, NOW())
    """
    cur.executemany(sql2, [
        (h["store_id"], h["round"], h["win_rank"], h["win_date"])
        for h in histories
    ])
    conn.commit()
    print(f"당첨 이력 {len(histories)}건 삽입 완료")

    cur.close()
    conn.close()

    # 통계
    print("\n=== 시뮬레이션 통계 ===")
    print(f"총 판매점: {len(store_ids)}개")
    rank1 = [h for h in histories if h["win_rank"] == 1]
    rank2 = [h for h in histories if h["win_rank"] == 2]
    print(f"1등 당첨 이력: {len(rank1)}건 ({len(set(h['store_id'] for h in rank1))}개 판매점)")
    print(f"2등 당첨 이력: {len(rank2)}건 ({len(set(h['store_id'] for h in rank2))}개 판매점)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stores", type=int, default=200, help="생성할 판매점 수 (기본 200)")
    args = parser.parse_args()
    main(args.stores)
