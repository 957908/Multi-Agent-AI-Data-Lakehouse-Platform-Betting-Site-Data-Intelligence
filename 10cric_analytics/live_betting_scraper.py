import asyncio
import sys
import os
from typing import Dict, Any, List

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.scraper_base import BaseScraper
from utils.playwright_helpers import human_scroll

class LiveBettingScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="live_betting",
            url="https://www.10cric247.com/live-betting/"
        )

    async def scrape(self) -> Dict[str, Any]:
        await self.init_browser()
        
        try:
            success = await self.navigate_with_retry()
            if not success:
                raise Exception("Failed to navigate to the live betting page.")

            # Let dynamic content load and scroll to trigger lazy-load assets
            await asyncio.sleep(3)
            await human_scroll(self.page)
            await asyncio.sleep(2)

            # Extract basic metadata
            metadata = await self.capture_metadata()

            # Identify categories
            categories = []
            # Selectors for sidebar categories, live sports menus, active tabs
            category_selectors = [
                ".sport-menu-item",
                ".sports-menu a",
                ".live-sport-tab",
                "[class*='sport-tab']",
                "[class*='category-item']",
                ".sports-list li",
                ".navigation-item",
                "aside a"
            ]
            
            for selector in category_selectors:
                elements = await self.page.query_selector_all(selector)
                for el in elements:
                    text = await el.inner_text()
                    text = text.strip()
                    if text and text not in categories and len(text) < 50:
                        categories.append(text)
                if categories:
                    break

            # If no specific categories found, fallback to header navigation links
            if not categories:
                self.logger.info("Category selectors not matched. Trying fallback header category links...")
                elements = await self.page.query_selector_all("nav a, header a")
                for el in elements:
                    text = await el.inner_text()
                    text = text.strip()
                    if text and text not in categories and len(text) < 30:
                        categories.append(text)

            # Extract active live sports/match names (public content)
            public_content = []
            # Match card, event name, team name, live details selectors
            event_selectors = [
                ".event-name",
                ".match-title",
                ".event-title",
                ".team-name",
                "[class*='match-card']",
                "[class*='event-row']",
                ".live-event-name",
                ".teams",
                "h3", "h4", "h5"
            ]

            for selector in event_selectors:
                elements = await self.page.query_selector_all(selector)
                for el in elements:
                    text = await el.inner_text()
                    text = text.strip().replace('\n', ' vs ')
                    if text and text not in public_content and len(text) > 3 and len(text) < 150:
                        # Exclude headers or standard layout links
                        if not any(word in text.lower() for word in ["terms", "privacy", "about", "rules", "contact", "support"]):
                            public_content.append(text)
                if len(public_content) >= 5:
                    break

            # Build result
            result = {
                "page_url": metadata["page_url"],
                "page_title": metadata["page_title"],
                "headings": metadata["headings"],
                "categories": categories,
                "public_content": public_content,
                "timestamp": self.timestamp
            }

            # Capture screenshots & HTML snapshot
            await self.take_screenshot()
            await self.save_html()
            
            # Save results
            self.save_json(result)
            self.logger.info("Live Betting Scraper run successfully.")
            return result

        except Exception as e:
            self.logger.error(f"Error executing Live Betting Scraper: {e}", exc_info=True)
            raise e
        finally:
            await self.close_browser()

if __name__ == "__main__":
    scraper = LiveBettingScraper()
    asyncio.run(scraper.scrape())
