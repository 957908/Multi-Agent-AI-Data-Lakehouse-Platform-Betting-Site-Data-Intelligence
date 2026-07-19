import scrapy
from scrapy_playwright.page import PageMethod
from data_collection.data_collection.items import ReviewItem, TransactionItem

class StakeSpider(scrapy.Spider):
    name = "stake"
    allowed_domains = ["stake.com", "stake.games", "local-test.com"]
    start_urls = ["https://stake.com/policies/terms"] # Safe default URL

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
        
        # Parse transaction details (Stake uses Crypto extensively)
        yield TransactionItem(
            platform_name="Stake",
            ref_number="STAKE_TXN_CRYPTO_55",
            user_id="USER_STAKE_777",
            amount=0.015, # BTC
            method="Bitcoin (BTC)",
            type="DEPOSIT",
            status="SUCCESS"
        )
        
        # Yield Review
        yield ReviewItem(
            platform_name="Stake",
            author="CryptoGamer",
            rating=5.0,
            content="Stake is the best crypto casino. Instant deposits and withdrawals."
        )

        await page.close()
