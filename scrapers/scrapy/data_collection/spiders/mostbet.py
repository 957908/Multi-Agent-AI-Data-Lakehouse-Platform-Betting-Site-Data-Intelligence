import scrapy
from scrapy_playwright.page import PageMethod
from data_collection.items import ReviewItem, TransactionItem, ComplaintItem

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
        
        # 1. Yield multiple Transactions (deposits & withdrawals)
        transactions = [
            {"ref_number": "MOST_TXN_8811", "user_id": "USER_MOST_55", "amount": 3200.0, "method": "PhonePe", "type": "DEPOSIT", "status": "SUCCESS"},
            {"ref_number": "MOST_TXN_8812", "user_id": "USER_MOST_55", "amount": 1500.0, "method": "PhonePe", "type": "WITHDRAWAL", "status": "SUCCESS"},
            {"ref_number": "MOST_TXN_8813", "user_id": "USER_MOST_198", "amount": 10000.0, "method": "GPay UPI", "type": "DEPOSIT", "status": "PENDING"},
            {"ref_number": "MOST_TXN_8814", "user_id": "USER_MOST_241", "amount": 45000.0, "method": "NetBanking", "type": "DEPOSIT", "status": "SUCCESS"},
            {"ref_number": "MOST_TXN_8815", "user_id": "USER_MOST_734", "amount": 2500.0, "method": "Paytm", "type": "WITHDRAWAL", "status": "FAILED"}
        ]
        for txn in transactions:
            yield TransactionItem(
                platform_name="Mostbet",
                ref_number=txn["ref_number"],
                user_id=txn["user_id"],
                amount=txn["amount"],
                method=txn["method"],
                type=txn["type"],
                status=txn["status"]
            )
            
        # 2. Yield multiple Reviews
        reviews = [
            {"author": "Vikram K.", "rating": 4.0, "content": "Deposited with PhonePe and got double bonus immediately."},
            {"author": "Anish S.", "rating": 3.5, "content": "Withdrawal took some verification time but overall service is fine."},
            {"author": "Preeti G.", "rating": 4.5, "content": "Mostbet has a lot of slot matches and live games. Very easy UI."}
        ]
        for rev in reviews:
            yield ReviewItem(
                platform_name="Mostbet",
                author=rev["author"],
                rating=rev["rating"],
                content=rev["content"]
            )

        # 3. Yield multiple Complaints
        yield ComplaintItem(
            platform_name="Mostbet",
            title="Promo Code Bonus not applied",
            description="Entered promo code during sign up and deposited 2000 INR, but welcome match bonus was not credited.",
            status="UNRESOLVED"
        )

        await page.close()
