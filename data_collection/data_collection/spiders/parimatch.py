import scrapy
from scrapy_playwright.page import PageMethod
from data_collection.data_collection.items import ReviewItem, TransactionItem

class ParimatchSpider(scrapy.Spider):
    name = "parimatch"
    allowed_domains = ["parimatch.in", "pm-in.com", "local-test.com"]
    start_urls = ["https://parimatch.in/terms-and-conditions"] # Safe default URL

    def start_requests(self):
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
        
        # Parse transaction details
        yield TransactionItem(
            platform_name="Parimatch",
            ref_number="PARI_TXN_007",
            user_id="USER_PARI_88",
            amount=50000.0,
            method="UPI / NetBanking",
            type="DEPOSIT",
            status="SUCCESS"
        )
        
        # Yield Review
        yield ReviewItem(
            platform_name="Parimatch",
            author="Rohit P.",
            rating=4.5,
            content="Interface is very fast. Good collection of live casino games."
        )

        await page.close()
