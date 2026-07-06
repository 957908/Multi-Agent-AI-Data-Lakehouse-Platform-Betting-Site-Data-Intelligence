import asyncio
import sys
import os
from typing import Dict, Any, List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.scraper_base import BaseScraper
from utils.playwright_helpers import human_scroll

class CasinoScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="casino",
            url="https://www.10cric247.com/casino/"
        )

    async def scrape(self) -> Dict[str, Any]:
        await self.init_browser()
        
        try:
            success = await self.navigate_with_retry()
            if not success:
                raise Exception("Failed to navigate to the casino page.")

            await asyncio.sleep(3)
            await human_scroll(self.page)
            await asyncio.sleep(2)

            metadata = await self.capture_metadata()

            # Categories (e.g. Slots, New Games, Crash, Table, Popular, Jackpots)
            categories = []
            category_selectors = [
                ".casino-category",
                ".category-tab",
                ".game-category",
                "[class*='category'] a",
                "[class*='tab-menu'] a",
                ".sub-menu a",
                "nav.casino-nav a",
                "h2.category-title",
                ".category-name"
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

            # If none, fallback to simple section titles on page
            if not categories:
                self.logger.info("Category selectors not matched. Trying header element fallback...")
                elements = await self.page.query_selector_all("h2, h3")
                for el in elements:
                    text = await el.inner_text()
                    text = text.strip()
                    if text and text not in categories and len(text) < 40:
                        categories.append(text)

            # Public content: casino game names
            public_content = []
            game_selectors = [
                ".game-name",
                ".game-title",
                ".game-card-title",
                "[class*='game-name']",
                "[class*='game-card'] h3",
                "[class*='game-card'] h4",
                ".game-item-name",
                ".game-info h4"
            ]

            for selector in game_selectors:
                elements = await self.page.query_selector_all(selector)
                for el in elements:
                    text = await el.inner_text()
                    text = text.strip()
                    if text and text not in public_content and len(text) > 2 and len(text) < 100:
                        public_content.append(text)
                if len(public_content) >= 10:
                    break

            # Try parsing images alternate text as game names if text lists are empty
            if not public_content:
                self.logger.info("Text selectors for games empty. Trying img[alt] attributes...")
                img_elements = await self.page.query_selector_all("img[alt]")
                for img in img_elements:
                    alt_text = await img.get_attribute("alt")
                    if alt_text:
                        alt_text = alt_text.strip()
                        if alt_text and alt_text not in public_content and len(alt_text) > 3 and len(alt_text) < 80:
                            if not any(word in alt_text.lower() for word in ["logo", "banner", "icon", "background", "button", "play"]):
                                public_content.append(alt_text)

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
            self.logger.info("Casino Scraper run successfully.")
            return result

        except Exception as e:
            self.logger.error(f"Error executing Casino Scraper: {e}", exc_info=True)
            raise e
        finally:
            await self.close_browser()

if __name__ == "__main__":
    scraper = CasinoScraper()
    asyncio.run(scraper.scrape())
