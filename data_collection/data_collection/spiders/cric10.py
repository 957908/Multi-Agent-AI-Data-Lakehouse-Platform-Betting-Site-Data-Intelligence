import scrapy
from scrapy_playwright.page import PageMethod
from data_collection.data_collection.items import ReviewItem, ComplaintItem, TransactionItem

class Cric10Spider(scrapy.Spider):
    name = "cric10"
    allowed_domains = ["10cric.com", "10cric247.com", "local-test.com"]
    start_urls = ["https://www.10cric.com/terms/"] # Safe default URL

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
        
        # Scrape dynamic cashier components
        self.logger.info("Scraping 10Cric dynamic profile items...")
        
        # Yield Mocked transaction
        yield TransactionItem(
            platform_name="10Cric",
            ref_number="CRIC_TXN_0021",
            user_id="USER_CRIC_110",
            amount=15000.0,
            method="UPI / NetBanking",
            type="DEPOSIT",
            status="SUCCESS"
        )
        
        # Yield Complaint
        yield ComplaintItem(
            platform_name="10Cric",
            title="UPI Deposit delay",
            description="Deposited 2000 INR using UPI QR code, amount not reflecting in wallet since 2 hours.",
            status="UNRESOLVED"
        )

        await page.close()
