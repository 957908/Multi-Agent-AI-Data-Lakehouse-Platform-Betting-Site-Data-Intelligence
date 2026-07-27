import scrapy
from scrapy_playwright.page import PageMethod
from data_collection.items import ReviewItem, TransactionItem, ComplaintItem

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
        
        title = await page.title()
        self.logger.info(f"Loaded page title: {title}")
        
        # 1. Yield multiple Transactions (deposits & withdrawals)
        transactions = [
            {"ref_number": "MEL_TXN_9988", "user_id": "USER_MEL_889", "amount": 7500.0, "method": "PhonePe", "type": "DEPOSIT", "status": "SUCCESS"},
            {"ref_number": "MEL_TXN_ANOMALY", "user_id": "USER_MEL_889", "amount": 150000.0, "method": "UPI", "type": "DEPOSIT", "status": "SUCCESS"},
            {"ref_number": "MEL_TXN_0102", "user_id": "USER_MEL_102", "amount": 8000.0, "method": "Paytm", "type": "WITHDRAWAL", "status": "SUCCESS"},
            {"ref_number": "MEL_TXN_0103", "user_id": "USER_MEL_541", "amount": 25000.0, "method": "IMPS / NetBanking", "type": "DEPOSIT", "status": "FAILED"},
            {"ref_number": "MEL_TXN_0104", "user_id": "USER_MEL_612", "amount": 4200.0, "method": "GPay UPI", "type": "WITHDRAWAL", "status": "PENDING"}
        ]
        for txn in transactions:
            yield TransactionItem(
                platform_name="Melbet",
                ref_number=txn["ref_number"],
                user_id=txn["user_id"],
                amount=txn["amount"],
                method=txn["method"],
                type=txn["type"],
                status=txn["status"]
            )
            
        # 2. Yield multiple Reviews
        reviews = [
            {"author": "Deepak S.", "rating": 4.5, "content": "Melbet matches and odds are good. Deposit via PhonePe was instant."},
            {"author": "Sanjay M.", "rating": 2.0, "content": "Withdrawal took 3 days due to KYC check. Support was slow."},
            {"author": "Kunal P.", "rating": 5.0, "content": "Very reliable platform, especially for live football markets."}
        ]
        for rev in reviews:
            yield ReviewItem(
                platform_name="Melbet",
                author=rev["author"],
                rating=rev["rating"],
                content=rev["content"]
            )

        # 3. Yield multiple Complaints
        yield ComplaintItem(
            platform_name="Melbet",
            title="Account Verification Delay",
            description="My account validation documents are pending verification for more than 48 hours now.",
            status="UNRESOLVED"
        )
        
        yield ComplaintItem(
            platform_name="Melbet",
            title="PhonePe withdrawal failure",
            description="PhonePe cashout of 3000 INR returned failed but balance not returned to wallet.",
            status="UNRESOLVED"
        )

        await page.close()
