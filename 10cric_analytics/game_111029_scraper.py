import asyncio
import sys
import os
from typing import Dict, Any, List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.scraper_base import BaseScraper
from utils.playwright_helpers import human_scroll

class Game111029Scraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="game_111029",
            url="https://www.10cric247.com/game/?launch=111029"
        )

    async def scrape(self) -> Dict[str, Any]:
        await self.init_browser()
        
        try:
            success = await self.navigate_with_retry()
            if not success:
                raise Exception("Failed to navigate to game launcher page.")

            # Games may take a few seconds to load assets or iframes
            await asyncio.sleep(5)
            await human_scroll(self.page)
            await asyncio.sleep(2)

            metadata = await self.capture_metadata()

            # Identify categories or providers
            categories = ["Game Launcher"]
            # Look for provider names or categories on page
            provider_selectors = [
                ".provider-name",
                ".game-provider",
                ".brand-name",
                "[class*='provider']",
                ".category-badge"
            ]
            for selector in provider_selectors:
                elements = await self.page.query_selector_all(selector)
                for el in elements:
                    text = await el.inner_text()
                    text = text.strip()
                    if text and text not in categories and len(text) < 40:
                        categories.append(text)

            # Public content: game details, status, login prompt, iframe info
            public_content = []
            
            # Check for iframe source or container
            try:
                iframe_elements = await self.page.query_selector_all("iframe")
                for iframe in iframe_elements:
                    src = await iframe.get_attribute("src")
                    if src:
                        public_content.append(f"Iframe src: {src[:100]}...")
            except Exception as e:
                self.logger.debug(f"Failed to check for iframe elements: {e}")

            # Check for game title or warning/login messages
            content_selectors = [
                ".game-title",
                ".game-name",
                ".login-required",
                ".login-prompt",
                ".warning-message",
                "h1", "h2", "h3",
                ".error-message",
                ".btn-login",
                "button"
            ]

            for selector in content_selectors:
                elements = await self.page.query_selector_all(selector)
                for el in elements:
                    text = await el.inner_text()
                    text = text.strip()
                    if text and text not in public_content and len(text) > 3 and len(text) < 150:
                        public_content.append(text)
                if len(public_content) >= 10:
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
            self.logger.info("Game 111029 Scraper run successfully.")
            return result

        except Exception as e:
            self.logger.error(f"Error executing Game 111029 Scraper: {e}", exc_info=True)
            raise e
        finally:
            await self.close_browser()

if __name__ == "__main__":
    scraper = Game111029Scraper()
    asyncio.run(scraper.scrape())
