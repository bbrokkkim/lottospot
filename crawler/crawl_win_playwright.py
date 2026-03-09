"""
crawl_win_playwright.py
Playwright 헤드리스 브라우저로 동행복권 당첨 판매점 API 우회 크롤링
"""
import asyncio
import json
import logging
import os
import time
from datetime import date, timedelta

import pymysql
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
log = logging.getLogger(__name__)

ROUND_1_DATE = date(2002, 12, 7)
BASE_URL = "https://www.dhlottery.co.kr"


def get_current_round() -> int:
    days = (date.today() - ROUND_1_DATE).days
    return days // 7 + 1


def round_to_date(rnd: int) -> str:
    return (ROUND_1_DATE + timedelta(weeks=rnd - 1)).isoformat()


def match_store(cur, item: dict) -> int | None:
    lat = item.get("shpLat")
    lng = item.get("shpLot")
    name = (item.get("shpNm") or "").strip()
    addr = (item.get("shpAddr") or "").strip()

    if lat and lng:
        try:
            cur.execute(
                """SELECT id FROM lotto_store
                   WHERE ST_Distance_Sphere(location, ST_GeomFromText(%s, 4326)) < 100
                   ORDER BY ST_Distance_Sphere(location, ST_GeomFromText(%s, 4326))
                   LIMIT 1""",
                (f"POINT({float(lat)} {float(lng)})", f"POINT({float(lat)} {float(lng)})"),
            )
            row = cur.fetchone()
            if row:
                return row[0]
        except Exception:
            pass

    if name and addr:
        cur.execute(
            "SELECT id FROM lotto_store WHERE name = %s AND address LIKE %s LIMIT 1",
            (name, f"%{addr[:15]}%"),
        )
        row = cur.fetchone()
        if row:
            return row[0]

    if name:
        cur.execute("SELECT id FROM lotto_store WHERE name = %s LIMIT 1", (name,))
        row = cur.fetchone()
        if row:
            return row[0]

    return None


async def fetch_winners_playwright(page, rnd: int, rank: int) -> list[dict]:
    url = f"{BASE_URL}/wnprchsplcsrch/selectLtWnShp.do?srchWnShpRnk={rank}&srchLtEpsd={rnd}&srchShpLctn="
    for attempt in range(3):
        try:
            resp = await page.request.get(url, timeout=20000)
            if resp.status == 200:
                body = await resp.json()
                return body.get("data", {}).get("list", [])
            log.warning("[%d회/%d등] HTTP %d", rnd, rank, resp.status)
        except Exception as e:
            log.warning("[%d회/%d등] 시도 %d 실패: %s", rnd, rank, attempt + 1, e)
            await asyncio.sleep(3)
    return []


async def crawl(start_round: int, end_round: int):
    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", "12341234"),
        database=os.getenv("DB_NAME", "lottospot"),
        charset="utf8mb4",
    )
    cur = conn.cursor()

    # 기존 목업 데이터 초기화 (실제 데이터로 교체)
    cur.execute("TRUNCATE TABLE winning_history")
    conn.commit()
    log.info("기존 이력 초기화 완료")

    insert_sql = """
        INSERT IGNORE INTO winning_history (store_id, round, win_rank, win_date, created_at)
        VALUES (%s, %s, %s, %s, NOW())
    """

    total_inserted = 0
    total_no_match = 0
    batch = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            extra_http_headers={
                "Referer": f"{BASE_URL}/wnprchsplcsrch/home",
                "Accept-Language": "ko-KR,ko;q=0.9",
            },
        )
        page = await context.new_page()

        # 홈페이지 방문 없이 직접 API 호출 (타임아웃 우회)
        log.info("크롤링 시작: %d~%d회차", start_round, end_round)

        for rnd in range(start_round, end_round + 1):
            win_date = round_to_date(rnd)

            for rank in [1, 2]:
                winners = await fetch_winners_playwright(page, rnd, rank)

                for item in winners:
                    store_id = match_store(cur, item)
                    if store_id:
                        batch.append((store_id, rnd, rank, win_date))
                    else:
                        total_no_match += 1

                await asyncio.sleep(0.5)

            if rnd % 50 == 0 and batch:
                cur.executemany(insert_sql, batch)
                conn.commit()
                total_inserted += len(batch)
                batch = []
                log.info("[%d/%d회] 저장: 누적 %d건 (매칭실패 %d건)", rnd, end_round, total_inserted, total_no_match)

        if batch:
            cur.executemany(insert_sql, batch)
            conn.commit()
            total_inserted += len(batch)

        await browser.close()

    cur.close()
    conn.close()
    log.info("완료: %d건 삽입, %d건 매칭 실패", total_inserted, total_no_match)


if __name__ == "__main__":
    current = get_current_round()
    log.info("현재 최신 회차: %d", current)
    asyncio.run(crawl(1, current))
