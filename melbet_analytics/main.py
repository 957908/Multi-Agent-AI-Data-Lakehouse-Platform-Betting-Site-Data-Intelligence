import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
import config
from config import logger, SESSION_FILE, REPORTS_DIR, SCREENSHOTS_DIR
from database import DatabaseManager
from login import get_authenticated_context
from dashboard import scrape_profile_info
from transaction_scraper import scrape_transactions
from bet_scraper import scrape_bets
from analytics import calculate_overall_metrics, generate_periodic_summaries
from exporter import export_to_json, export_to_csv, export_to_excel
from charts import generate_charts
from kafka_producer import KafkaDataProducer


async def run_pipeline(args):
    logger.info("=" * 60)
    logger.info("Starting Melbet Account Analytics Data Extraction Pipeline")
    logger.info("=" * 60)

    # Initialize SQLite Database
    db = DatabaseManager()

    # Manage Mock Mode
    server_process = None
    if args.mock:
        logger.info("Running in MOCK mode. Initializing local web server...")
        from mock_server import start_mock_server
        server_process, mock_url = start_mock_server()
        config.MELBET_URL = mock_url
        logger.info(f"Mock server running. Overriding MELBET_URL to {mock_url}")

    if args.force_login:
        logger.info("Force login enabled. Deleting existing session file...")
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
            logger.info("Session file cleared.")

    # Run Playwright Scraping
    scraped_data = None
    try:
        async with async_playwright() as p:
            # Login / Session retrieval
            context, page, is_new_login = await get_authenticated_context(p)
            
            # 1. Profile Collection
            profile = await scrape_profile_info(page)
            user_id = profile["user_id"]
            
            if user_id == "UNKNOWN":
                logger.error("Could not determine User ID. Aborting collection.")
                await context.close()
                return

            # Capture a dashboard screenshot for record-keeping
            screenshot_path = SCREENSHOTS_DIR / f"dashboard_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=str(screenshot_path))
            logger.info(f"Dashboard screenshot captured: {screenshot_path}")

            # 2. Scrape Transactions
            deposits, withdrawals = await scrape_transactions(page)
            
            # 3. Scrape Bets
            bets = await scrape_bets(page)
            
            # Close browser context
            await context.close()
            
            # Save raw data to database
            logger.info("Saving scraped data to SQLite database...")
            db.save_user(
                user_id=user_id,
                username=profile["username"],
                wallet_balance=profile["wallet_balance"],
                currency=profile["currency"],
                account_status=profile["account_status"]
            )
            
            if deposits:
                db.save_deposits(deposits, user_id)
            if withdrawals:
                db.save_withdrawals(withdrawals, user_id)
            if bets:
                db.save_bets(bets, user_id)
                
            logger.info("Database saving completed successfully.")
            
            # Stream Data to Kafka
            try:
                logger.info("Streaming scraped data to Kafka...")
                producer = KafkaDataProducer()
                
                producer.publish("melbet-profile", {
                    "user_id": user_id,
                    "profile": profile,
                    "timestamp": datetime.now().isoformat()
                })
                
                if deposits:
                    for d in deposits:
                        producer.publish("melbet-deposits", {**d, "user_id": user_id})
                if withdrawals:
                    for w in withdrawals:
                        producer.publish("melbet-withdrawals", {**w, "user_id": user_id})
                if bets:
                    for b in bets:
                        producer.publish("melbet-bets", {**b, "user_id": user_id})
                        
                producer.close()
            except Exception as ke:
                logger.warning(f"Error in Kafka streaming process: {ke}")

            
    except Exception as e:
        logger.critical(f"Critical error in scraping pipeline: {e}", exc_info=True)
        if server_process:
            server_process.terminate()
        sys.exit(1)

    # 4. Fetch All Integrated Data From Database
    logger.info("Retrieving complete history from SQLite database for analytics...")
    integrated_data = db.get_user_data(user_id)

    # 5. Run Analytics Calculations
    metrics = calculate_overall_metrics(integrated_data)
    summaries = generate_periodic_summaries(integrated_data)
    
    # Save computed metrics to DB
    db.save_analytics(user_id, metrics)

    # 6. Generate Exports
    logger.info("Generating reports and exports...")
    export_to_csv(integrated_data, user_id)
    json_report_path = export_to_json(integrated_data, metrics, summaries)
    excel_report_path = export_to_excel(integrated_data, metrics, summaries)
    
    # 7. Generate Visual Charts
    chart_paths = generate_charts(integrated_data, REPORTS_DIR)

    logger.info("=" * 60)
    logger.info("Pipeline executed successfully!")
    logger.info(f"JSON Report: {json_report_path}")
    logger.info(f"Excel Report: {excel_report_path}")
    if chart_paths:
        logger.info(f"Generated Charts: {', '.join(chart_paths)}")
    logger.info("=" * 60)

    # Clean up mock server if running
    if server_process:
        logger.info("Stopping mock server...")
        server_process.terminate()
        server_process.wait()
        logger.info("Mock server stopped.")

def main():
    parser = argparse.ArgumentParser(description="Melbet Account Analytics System Data Collector")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser in headless mode (default: True)")
    parser.add_argument("--headful", action="store_false", dest="headless", help="Run browser in visible mode")
    parser.add_argument("--force-login", action="store_true", help="Ignore saved session and force credential authentication")
    parser.add_argument("--mock", action="store_true", default=False, help="Run offline using local mock web pages")
    
    args = parser.parse_args()
    
    # Apply CLI args overrides to config
    config.BROWSER_HEADLESS = args.headless
    
    # Run async pipeline
    asyncio.run(run_pipeline(args))

if __name__ == "__main__":
    main()
