import asyncio
import sys
import os
import pandas as pd
from datetime import datetime
import argparse

# Import all scrapers
from live_betting_scraper import LiveBettingScraper
from sports_scraper import SportsScraper
from casino_scraper import CasinoScraper
from live_casino_scraper import LiveCasinoScraper
from game_111029_scraper import Game111029Scraper
from game_106581_scraper import Game106581Scraper
from virtual_sports_scraper import VirtualSportsScraper
from promotions_scraper import PromotionsScraper

async def run_scraper(scraper_instance, results_list):
    name = scraper_instance.name
    url = scraper_instance.url
    print(f"\n==================================================")
    print(f"Starting Scraper: {name}")
    print(f"Target URL: {url}")
    print(f"==================================================")
    
    start_time = datetime.now()
    status = "SUCCESS"
    error_msg = ""
    extracted_data = None
    
    try:
        extracted_data = await scraper_instance.scrape()
    except Exception as e:
        status = "FAILED"
        error_msg = str(e)
        print(f"Scraper {name} failed: {e}")
        
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Save statistics
    results_list.append({
        "scraper": name,
        "url": url,
        "status": status,
        "duration_seconds": duration,
        "error": error_msg,
        "headings_count": len(extracted_data["headings"]) if extracted_data else 0,
        "categories_count": len(extracted_data["categories"]) if extracted_data else 0,
        "public_content_count": len(extracted_data["public_content"]) if extracted_data else 0,
        "timestamp": start_time.isoformat()
    })
    
    # Stream data to Kafka
    if extracted_data and status == "SUCCESS":
        try:
            print(f"Streaming {name} extracted data to Kafka...")
            from kafka_producer import KafkaDataProducer
            producer = KafkaDataProducer()
            producer.publish("10cric-raw-data", {
                "scraper": name,
                "data": extracted_data,
                "timestamp": datetime.now().isoformat()
            })
            producer.close()
        except Exception as ke:
            print(f"[WARNING] Error streaming 10cric data to Kafka: {ke}")



async def main():
    parser = argparse.ArgumentParser(description="10cric247.com Site Analyzer Runner")
    parser.add_argument(
        "--scraper", 
        type=str, 
        choices=["live_betting", "sports", "casino", "live_casino", "game_111029", "game_106581", "virtual_sports", "promotions", "all"],
        default="all",
        help="Specify which scraper to run, or 'all' to run all sequentially (default: all)"
    )
    args = parser.parse_args()

    scrapers = {
        "live_betting": LiveBettingScraper(),
        "sports": SportsScraper(),
        "casino": CasinoScraper(),
        "live_casino": LiveCasinoScraper(),
        "game_111029": Game111029Scraper(),
        "game_106581": Game106581Scraper(),
        "virtual_sports": VirtualSportsScraper(),
        "promotions": PromotionsScraper()
    }

    results = []

    if args.scraper == "all":
        # Run all sequentially
        for name, instance in scrapers.items():
            await run_scraper(instance, results)
    else:
        # Run specific scraper
        instance = scrapers[args.scraper]
        await run_scraper(instance, results)

    # Save summary using Pandas
    df = pd.DataFrame(results)
    print("\n================ Execution Summary ================")
    print(df.to_string(index=False))
    print("==================================================")
    
    summary_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "json", "execution_summary.json")
    df.to_json(summary_path, orient="records", indent=4)
    print(f"Summary JSON saved to {summary_path}")

if __name__ == "__main__":
    asyncio.run(main())
