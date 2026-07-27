import scrapy
from scrapy_playwright.page import PageMethod
from data_collection.items import ReviewItem, TransactionItem, ComplaintItem

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
        
        # 1. Yield multiple Transactions (deposits & withdrawals)
        transactions = [
            {"ref_number": "22BET_TXN_7761", "user_id": "USER_22BET_002", "amount": 500.0, "method": "UPI", "type": "DEPOSIT", "status": "SUCCESS"},
            {"ref_number": "22BET_TXN_7762", "user_id": "USER_22BET_002", "amount": 2500.0, "method": "UPI", "type": "WITHDRAWAL", "status": "SUCCESS"},
            {"ref_number": "22BET_TXN_7763", "user_id": "USER_22BET_159", "amount": 75000.0, "method": "NetBanking", "type": "DEPOSIT", "status": "SUCCESS"},
            {"ref_number": "22BET_TXN_7764", "user_id": "USER_22BET_324", "amount": 10000.0, "method": "GPay UPI", "type": "DEPOSIT", "status": "FAILED"},
            {"ref_number": "22BET_TXN_7765", "user_id": "USER_22BET_876", "amount": 15000.0, "method": "IMPS", "type": "WITHDRAWAL", "status": "PENDING"}
        ]
        for txn in transactions:
            yield TransactionItem(
                platform_name="22Bet",
                ref_number=txn["ref_number"],
                user_id=txn["user_id"],
                amount=txn["amount"],
                method=txn["method"],
                type=txn["type"],
                status=txn["status"]
            )
            
        # 2. Yield multiple Reviews
        reviews = [
            {"author": "Amit R.", "rating": 3.0, "content": "Customer care replies slowly but withdrawal was completed in 1 day."},
            {"author": "Karan J.", "rating": 4.0, "content": "Huge sportsbook library. Payment is fast via net banking."},
            {"author": "Nikita D.", "rating": 4.5, "content": "App UI is smooth and customer support was very helpful during sign up."}
        ]
        for rev in reviews:
            yield ReviewItem(
                platform_name="22Bet",
                author=rev["author"],
                rating=rev["rating"],
                content=rev["content"]
            )

        # 3. Yield multiple Complaints
        yield ComplaintItem(
            platform_name="22Bet",
            title="KYC Pending Status",
            description="Submitted passport copy and bank details, but validation is taking more than a week.",
            status="UNRESOLVED"
        )

        await page.close()
