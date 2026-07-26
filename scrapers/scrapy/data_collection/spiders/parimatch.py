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
        
        # 1. Yield multiple Transactions (deposits & withdrawals)
        transactions = [
            {"ref_number": "PARI_TXN_007", "user_id": "USER_PARI_88", "amount": 50000.0, "method": "UPI / NetBanking", "type": "DEPOSIT", "status": "SUCCESS"},
            {"ref_number": "PARI_TXN_008", "user_id": "USER_PARI_88", "amount": 12000.0, "method": "UPI", "type": "WITHDRAWAL", "status": "SUCCESS"},
            {"ref_number": "PARI_TXN_009", "user_id": "USER_PARI_233", "amount": 150000.0, "method": "NetBanking", "type": "DEPOSIT", "status": "SUCCESS"},
            {"ref_number": "PARI_TXN_010", "user_id": "USER_PARI_411", "amount": 8000.0, "method": "GPay", "type": "DEPOSIT", "status": "FAILED"},
            {"ref_number": "PARI_TXN_011", "user_id": "USER_PARI_672", "amount": 35000.0, "method": "Paytm", "type": "WITHDRAWAL", "status": "PENDING"}
        ]
        for txn in transactions:
            yield TransactionItem(
                platform_name="Parimatch",
                ref_number=txn["ref_number"],
                user_id=txn["user_id"],
                amount=txn["amount"],
                method=txn["method"],
                type=txn["type"],
                status=txn["status"]
            )
            
        # 2. Yield multiple Reviews
        reviews = [
            {"author": "Rohit P.", "rating": 4.5, "content": "Interface is very fast. Good collection of live casino games."},
            {"author": "Sumeet D.", "rating": 5.0, "content": "Depositing was seamless and withdrawals processed within 2 hours."},
            {"author": "Gaurav S.", "rating": 3.0, "content": "Good betting odds but account verification took longer than expected."}
        ]
        for rev in reviews:
            yield ReviewItem(
                platform_name="Parimatch",
                author=rev["author"],
                rating=rev["rating"],
                content=rev["content"]
            )

        # 3. Yield multiple Complaints
        yield ComplaintItem(
            platform_name="Parimatch",
            title="IMPS Cashout delay",
            description="Initiated cashout of 15,000 INR via IMPS, status is SUCCESS in account panel but fund not received in bank account.",
            status="UNRESOLVED"
        )

        await page.close()
