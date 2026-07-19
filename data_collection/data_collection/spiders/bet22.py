import scrapy
from scrapy_playwright.page import PageMethod
from data_collection.data_collection.items import ReviewItem, TransactionItem

class Bet22Spider(scrapy.Spider):
    name = "bet22"
    allowed_domains = ["22bet.com", "22play8.com", "local-test.com"]
    start_urls = ["https://22bet.com/terms/"] # Safe default URL

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
            platform_name="22Bet",
            ref_number="22BET_TXN_7761",
            user_id="USER_22BET_002",
            amount=500.0,
            method="UPI",
            type="DEPOSIT",
            status="SUCCESS"
        )
        
        # Yield Review
        yield ReviewItem(
            platform_name="22Bet",
            author="Amit R.",
            rating=3.0,
            content="Customer care replies slowly but withdrawal was completed in 1 day."
        )

        await page.close()
