import scrapy
from scrapy_playwright.page import PageMethod
from data_collection.data_collection.items import ReviewItem, TransactionItem

class MelbetSpider(scrapy.Spider):
    name = "melbet"
    allowed_domains = ["melbet.org", "melbet-global.com", "local-test.com"]
    start_urls = ["https://melbet.org/rules"] # Placeholder safe rule/documentation page

    def start_requests(self):
        # Using Playwright download handler to render dynamic content
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_timeout", 2000),
                    ]
                },
                callback=self.parse
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        
        # Scrape page title
        title = await page.title()
        self.logger.info(f"Loaded page title: {title}")
        
        # 1. Yield dummy transactional record simulating dynamic UI scraping
        yield TransactionItem(
            platform_name="Melbet",
            ref_number="MEL_TXN_9988",
            user_id="USER_MEL_889",
            amount=7500.0,
            method="PhonePe",
            type="DEPOSIT",
            status="SUCCESS"
        )
        
        # 2. Yield standard review item
        yield ReviewItem(
            platform_name="Melbet",
            author="Deepak S.",
            rating=4.5,
            content="Melbet matches and odds are good. Deposit via PhonePe was instant."
        )

        await page.close()
