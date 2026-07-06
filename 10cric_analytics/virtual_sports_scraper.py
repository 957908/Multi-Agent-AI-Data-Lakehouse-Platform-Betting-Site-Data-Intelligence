import asyncio
import sys
import os
from typing import Dict, Any, List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.scraper_base import BaseScraper
from utils.playwright_helpers import human_scroll

class VirtualSportsScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="virtual_sports",
            url="https://www.10cric247.com/virtual-sport/"
        )

    async def scrape(self) -> Dict[str, Any]:
        await self.init_browser()
        
        try:
            success = await self.navigate_with_retry()
            if not success:
                raise Exception("Failed to navigate to virtual sports page.")

            await asyncio.sleep(3)
            await human_scroll(self.page)
            await asyncio.sleep(2)

            metadata = await self.capture_metadata()

            # Categories (e.g. Virtual Cricket, Virtual Tennis, Virtual Soccer)
            categories = []
            category_selectors = [
                ".virtual-sport-category",
                ".category-tab",
                ".virtual-category",
                "[class*='category'] a",
                "[class*='tab-menu'] a",
                "h2.category-title",
                ".category-name",
                ".virtual-nav a",
                ".sport-menu-item"
            ]
            
            for selector in category_selectors:
                elements = await self.page.query_selector_all(selector)
                for el in elements:
                    text = await el.inner_text()
                    text = text.strip()
                    if text and text not in categories and len(text) < 40:
                        categories.append(text)
                if categories:
                    break

            if not categories:
                self.logger.info("Category selectors not matched. Trying header element fallback...")
                elements = await self.page.query_selector_all("h2, h3")
                for el in elements:
                    text = await el.inner_text()
                    text = text.strip()
                    if text and text not in categories and len(text) < 40:
                        categories.append(text)

            # Public content: virtual matches, leagues, team names, or virtual event titles
            public_content = []
            event_selectors = [
                ".virtual-match-name",
                ".match-title",
                ".event-title",
                ".team-name",
                "[class*='match-card']",
                "[class*='event-row']",
                ".teams",
                "h3", "h4", "h5"
            ]

            for selector in event_selectors:
                elements = await self.page.query_selector_all(selector)
                for el in elements:
                    text = await el.inner_text()
                    text = text.strip().replace('\n', ' vs ')
                    if text and text not in public_content and len(text) > 3 and len(text) < 150:
                        if not any(word in text.lower() for word in ["terms", "privacy", "about", "rules", "contact", "support"]):
                            public_content.append(text)
                if len(public_content) >= 5:
                    break

            result = {
                "page_url": metadata["page_url"],
                "page_title": metadata["page_title"],
                "headings": metadata["headings"],
                "categories": categories,
                "public_content": public_content,
                "timestamp": self.timestamp
            }

            await self.take_screenshot()
            await self.save_html()
            self.save_json(result)
            self.logger.info("Virtual Sports Scraper run successfully.")
            return result

        except Exception as e:
            self.logger.error(f"Error executing Virtual Sports Scraper: {e}", exc_info=True)
            raise e
        finally:
            await self.close_browser()

if __name__ == "__main__":
    scraper = VirtualSportsScraper()
    asyncio.run(scraper.scrape())
