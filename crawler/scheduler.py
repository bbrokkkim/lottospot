"""
scheduler.py
APScheduler를 사용한 복권판매점 데이터 수집 주간 자동 실행 스케줄러.

스케줄: 매주 토요일 23:30
로그: logs/scheduler.log
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

# 프로젝트 루트 경로
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CRAWLER_DIR = Path(__file__).resolve().parent
_LOG_DIR = _PROJECT_ROOT / "logs"
_LOG_FILE = _LOG_DIR / "scheduler.log"

load_dotenv(_CRAWLER_DIR / ".env")

# 로그 디렉터리 생성
_LOG_DIR.mkdir(parents=True, exist_ok=True)

# 로거 설정: stdout + 파일 동시 출력
_formatter = logging.Formatter(
    fmt="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
_file_handler.setFormatter(_formatter)

_stream_handler = logging.StreamHandler(sys.stdout)
_stream_handler.setFormatter(_formatter)

logging.basicConfig(level=logging.INFO, handlers=[_file_handler, _stream_handler])
logger = logging.getLogger("scheduler")


def run_collect_stores(sido: str | None = None, test_mode: bool = False) -> None:
    """
    collect_stores.py를 서브프로세스로 실행합니다.

    Parameters
    ----------
    sido : str | None
        시도 필터 (예: '서울'). None이면 전체 수집.
    test_mode : bool
        True이면 --test 플래그를 추가합니다.
    """
    collect_script = _CRAWLER_DIR / "collect_stores.py"
    if not collect_script.exists():
        logger.error("collect_stores.py를 찾을 수 없습니다: %s", collect_script)
        return

    cmd = [sys.executable, str(collect_script)]
    if test_mode:
        cmd.append("--test")
    if sido:
        cmd.extend(["--sido", sido])

    logger.info("collect_stores.py 실행 시작: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(_CRAWLER_DIR),
            env={**os.environ},  # 부모 환경변수 상속
            timeout=3600,  # 최대 1시간
        )

        if result.stdout:
            for line in result.stdout.splitlines():
                logger.info("[collect_stores] %s", line)

        if result.stderr:
            for line in result.stderr.splitlines():
                logger.warning("[collect_stores:stderr] %s", line)

        if result.returncode == 0:
            logger.info("collect_stores.py 정상 완료 (exit code=0)")
        else:
            logger.error(
                "collect_stores.py 비정상 종료 (exit code=%d)", result.returncode
            )

    except subprocess.TimeoutExpired:
        logger.error("collect_stores.py 실행 타임아웃 (1시간 초과)")
    except Exception as exc:
        logger.exception("collect_stores.py 실행 중 예외 발생: %s", exc)


def weekly_job() -> None:
    """매주 토요일 23:30에 실행되는 스케줄 작업."""
    logger.info("=" * 60)
    logger.info("주간 복권판매점 데이터 수집 작업 시작")
    logger.info("=" * 60)
    run_collect_stores()
    logger.info("주간 복권판매점 데이터 수집 작업 완료")
    logger.info("=" * 60)


def build_scheduler() -> BlockingScheduler:
    """
    BlockingScheduler를 생성하고 주간 작업을 등록합니다.

    스케줄: 매주 토요일 23:30 (KST 기준, Asia/Seoul)
    """
    scheduler = BlockingScheduler(timezone="Asia/Seoul")

    trigger = CronTrigger(
        day_of_week="sat",  # 토요일
        hour=23,
        minute=30,
        timezone="Asia/Seoul",
    )

    scheduler.add_job(
        func=weekly_job,
        trigger=trigger,
        id="weekly_collect_stores",
        name="주간 복권판매점 데이터 수집",
        replace_existing=True,
        misfire_grace_time=3600,  # 1시간 내 지연 실행 허용
        coalesce=True,            # 여러 번 미실행된 경우 한 번만 실행
    )

    return scheduler


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="복권판매점 데이터 수집 스케줄러",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="스케줄 대기 없이 즉시 수집 작업을 실행합니다",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="테스트 모드로 즉시 실행 (--run-now와 함께 사용)",
    )
    parser.add_argument(
        "--sido",
        type=str,
        default=None,
        help="시도 필터 (즉시 실행 모드에서 사용)",
    )
    args = parser.parse_args()

    if args.run_now:
        logger.info("즉시 실행 모드")
        run_collect_stores(sido=args.sido, test_mode=args.test)
        return

    logger.info("스케줄러 시작 - 매주 토요일 23:30 (Asia/Seoul) 자동 실행")
    logger.info("로그 파일: %s", _LOG_FILE)

    scheduler = build_scheduler()

    # 등록된 작업 정보 출력
    for job in scheduler.get_jobs():
        logger.info(
            "등록된 작업: id=%s | name=%s | next_run=%s",
            job.id,
            job.name,
            job.next_run_time,
        )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("스케줄러 종료 요청 수신. 안전하게 종료합니다.")
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
