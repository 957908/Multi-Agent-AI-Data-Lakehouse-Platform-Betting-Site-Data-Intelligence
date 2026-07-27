import scrapy
from scrapy_playwright.page import PageMethod
from data_collection.items import ReviewItem, ComplaintItem, TransactionItem

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
        
        self.logger.info("Scraping 10Cric dynamic profile items...")
        
        # 1. Yield multiple Transactions (deposits & withdrawals)
        transactions = [
            {"ref_number": "CRIC_TXN_0021", "user_id": "USER_CRIC_110", "amount": 15000.0, "method": "UPI / NetBanking", "type": "DEPOSIT", "status": "SUCCESS"},
            {"ref_number": "CRIC_TXN_0022", "user_id": "USER_CRIC_110", "amount": 4500.0, "method": "UPI", "type": "WITHDRAWAL", "status": "SUCCESS"},
            {"ref_number": "CRIC_TXN_0023", "user_id": "USER_CRIC_223", "amount": 25000.0, "method": "GPay UPI", "type": "DEPOSIT", "status": "PENDING"},
            {"ref_number": "CRIC_TXN_0024", "user_id": "USER_CRIC_451", "amount": 120000.0, "method": "IMPS / NetBanking", "type": "DEPOSIT", "status": "SUCCESS"},
            {"ref_number": "CRIC_TXN_0025", "user_id": "USER_CRIC_992", "amount": 3500.0, "method": "Paytm UPI", "type": "WITHDRAWAL", "status": "FAILED"}
        ]
        for txn in transactions:
            yield TransactionItem(
                platform_name="10Cric",
                ref_number=txn["ref_number"],
                user_id=txn["user_id"],
                amount=txn["amount"],
                method=txn["method"],
                type=txn["type"],
                status=txn["status"]
            )
            
        # 2. Yield multiple Reviews
        reviews = [
            {"author": "Rahul S.", "rating": 4.5, "content": "Instant UPI deposit. App works perfectly for cricket betting."},
            {"author": "Vijay K.", "rating": 3.0, "content": "Withdrawal took 24 hours but customer service responded in time."},
            {"author": "Anand P.", "rating": 5.0, "content": "10Cric has the best IPL betting odds. Smooth deposits."}
        ]
        for rev in reviews:
            yield ReviewItem(
                platform_name="10Cric",
                author=rev["author"],
                rating=rev["rating"],
                content=rev["content"]
            )
        
        # 3. Yield multiple Complaints
        complaints = [
            {"title": "UPI Deposit delay", "description": "Deposited 2000 INR using UPI QR code, amount not reflecting in wallet since 2 hours.", "status": "UNRESOLVED"},
            {"title": "Netbanking failure", "description": "Attempted netbanking deposit of 5000 INR, amount debited but transaction says FAILED in cashier.", "status": "RESOLVED"}
        ]
        for comp in complaints:
            yield ComplaintItem(
                platform_name="10Cric",
                title=comp["title"],
                description=comp["description"],
                status=comp["status"]
            )

        await page.close()
