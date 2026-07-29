"""
SentinelX Scraping Scheduler
─────────────────────────────
Replaces Apache Airflow for scheduling scraping jobs.
Uses APScheduler (pure Python, no Docker required).

Runs each spider on a configurable interval.
Logs every run with timestamp, status, and output file path.

Usage:
    python scrapers/scheduler.py

Requirements:
    pip install apscheduler
"""

import subprocess
import sys
import os
import logging
from datetime import datetime, timezone
from pathlib import Path

try:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
except ImportError:
    print("[ERROR] APScheduler not installed. Run: pip install apscheduler")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
SCRAPY_DIR = PROJECT_ROOT / "scrapers" / "scrapy"
LOG_DIR = PROJECT_ROOT / "scrapers" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "scheduler.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("SentinelXScheduler")

# Spider schedule — (spider_name, interval_hours)
SPIDER_SCHEDULE = [
    ("melbet",   6),   # Scrape Melbet deposit page every 6 hours
    ("cric10",   6),   # Scrape 10Cric deposit page every 6 hours
    ("bet22",    6),   # Scrape 22play deposit page every 6 hours
    ("mostbet",  12),  # Less frequent for smaller platforms
    ("parimatch",12),
    ("stake",    12),
]


# ─────────────────────────────────────────────────────────────────────────────
# Job runner
# ─────────────────────────────────────────────────────────────────────────────
def run_spider(spider_name: str):
    """
    Run a single Scrapy spider as a subprocess.
    Logs outcome with timestamp, exit code, and output file location.
    Never generates fake data — if spider fails, logs the error.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    log_file = LOG_DIR / f"{spider_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    output_file = SCRAPY_DIR / "scraped_data" / f"{spider_name}_data.json"

    logger.info(f"[SCHEDULER] Starting spider: {spider_name} | Run started: {started_at}")

    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "scrapy", "crawl", spider_name,
                "-o", str(output_file),
            ],
            cwd=str(SCRAPY_DIR),
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per spider
            encoding="utf-8",
            errors="replace"
        )

        # Save stdout/stderr to run log
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"Spider: {spider_name}\n")
            f.write(f"Started: {started_at}\n")
            f.write(f"Exit Code: {result.returncode}\n\n")
            f.write("=== STDOUT ===\n")
            f.write(result.stdout or "(empty)")
            f.write("\n\n=== STDERR ===\n")
            f.write(result.stderr or "(empty)")

        if result.returncode == 0:
            logger.info(
                f"[SCHEDULER ✓] Spider {spider_name} completed successfully. "
                f"Output: {output_file} | Log: {log_file}"
            )
        else:
            logger.error(
                f"[SCHEDULER ✗] Spider {spider_name} exited with code {result.returncode}. "
                f"Check log: {log_file}"
            )

    except subprocess.TimeoutExpired:
        logger.error(f"[SCHEDULER TIMEOUT] Spider {spider_name} exceeded 5 minutes. Killed.")
    except Exception as e:
        logger.error(f"[SCHEDULER ERROR] Spider {spider_name} failed with exception: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Scheduler events
# ─────────────────────────────────────────────────────────────────────────────
def job_listener(event):
    if event.exception:
        logger.error(f"[SCHEDULER] Job {event.job_id} raised an exception: {event.exception}")
    else:
        logger.info(f"[SCHEDULER] Job {event.job_id} completed successfully.")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    for spider_name, interval_hours in SPIDER_SCHEDULE:
        scheduler.add_job(
            func=run_spider,
            args=[spider_name],
            trigger=IntervalTrigger(hours=interval_hours),
            id=f"spider_{spider_name}",
            name=f"SentinelX → {spider_name} deposit page scraper",
            replace_existing=True,
            misfire_grace_time=600,  # Allow up to 10 min late start
        )
        logger.info(f"[SCHEDULER] Scheduled: {spider_name} every {interval_hours}h")

    logger.info(
        f"[SCHEDULER] SentinelX Scraping Scheduler running. "
        f"{len(SPIDER_SCHEDULE)} spiders scheduled. Press Ctrl+C to stop."
    )

    # Run all spiders immediately on startup (then follow schedule)
    for spider_name, _ in SPIDER_SCHEDULE:
        logger.info(f"[SCHEDULER] Running initial scrape: {spider_name}")
        run_spider(spider_name)

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("[SCHEDULER] Shutdown requested by user.")
        scheduler.shutdown()
