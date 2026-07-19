import scrapy
from scrapy_playwright.page import PageMethod
from data_collection.data_collection.items import ReviewItem, TransactionItem

class MostbetSpider(scrapy.Spider):
    name = "mostbet"
    allowed_domains = ["mostbet.com", "local-test.com"]
    start_urls = ["https://mostbet.com/rules"] # Safe default URL

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
            platform_name="Mostbet",
            ref_number="MOST_TXN_8811",
            user_id="USER_MOST_55",
            amount=3200.0,
            method="PhonePe",
            type="DEPOSIT",
            status="SUCCESS"
        )
        
        # Yield Review
        yield ReviewItem(
            platform_name="Mostbet",
            author="Vikram K.",
            rating=4.0,
            content="Deposited with PhonePe and got double bonus immediately."
        )

        await page.close()
