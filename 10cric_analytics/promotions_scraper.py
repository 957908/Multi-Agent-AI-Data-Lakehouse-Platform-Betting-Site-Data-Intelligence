import asyncio
import sys
import os
from typing import Dict, Any, List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.scraper_base import BaseScraper
from utils.playwright_helpers import human_scroll

class PromotionsScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="promotions",
            url="https://www.10cric247.com/promotions/offers/"
        )

    async def scrape(self) -> Dict[str, Any]:
        await self.init_browser()
        
        try:
            success = await self.navigate_with_retry()
            if not success:
                raise Exception("Failed to navigate to promotions page.")

            await asyncio.sleep(3)
            await human_scroll(self.page)
            await asyncio.sleep(2)

            metadata = await self.capture_metadata()

            # Categories (e.g. Welcome Offers, Sports Offers, Casino Offers, Weekly)
            categories = []
            category_selectors = [
                ".promo-category",
                ".promotion-tab",
                "[class*='category'] a",
                "[class*='tab-menu'] a",
                "h2.category-title",
                ".category-name",
                ".promo-nav a",
                ".promo-filter a"
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

            # Public content: promotion offer titles, promo codes, descriptions
            public_content = []
            promo_selectors = [
                ".promo-title",
                ".promotion-title",
                ".offer-title",
                "[class*='promo-card'] h3",
                "[class*='promo-card'] h4",
                "[class*='offer'] h3",
                ".promo-item-name",
                ".promo-card-content h3",
                "h3", "h4"
            ]

            for selector in promo_selectors:
                elements = await self.page.query_selector_all(selector)
                for el in elements:
                    text = await el.inner_text()
                    text = text.strip()
                    if text and text not in public_content and len(text) > 3 and len(text) < 150:
                        if not any(word in text.lower() for word in ["terms", "privacy", "about", "rules", "contact", "support"]):
                            public_content.append(text)
                if len(public_content) >= 5:
                    break

            # Try parsing images alt text if text title list is empty
            if not public_content:
                self.logger.info("Promo selectors empty. Trying img[alt] attributes...")
                img_elements = await self.page.query_selector_all("img[alt]")
                for img in img_elements:
                    alt_text = await img.get_attribute("alt")
                    if alt_text:
                        alt_text = alt_text.strip()
                        if alt_text and alt_text not in public_content and len(alt_text) > 3 and len(alt_text) < 80:
                            if not any(word in alt_text.lower() for word in ["logo", "banner", "icon", "background", "button"]):
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
            self.logger.info("Promotions Scraper run successfully.")
            return result

        except Exception as e:
            self.logger.error(f"Error executing Promotions Scraper: {e}", exc_info=True)
            raise e
        finally:
            await self.close_browser()

if __name__ == "__main__":
    scraper = PromotionsScraper()
    asyncio.run(scraper.scrape())
