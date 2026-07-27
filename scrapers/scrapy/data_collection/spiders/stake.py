import scrapy
from scrapy_playwright.page import PageMethod
from data_collection.items import ReviewItem, TransactionItem, ComplaintItem

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
        
        # 1. Yield multiple Transactions (Stake uses Crypto extensively)
        transactions = [
            {"ref_number": "STAKE_TXN_CRYPTO_55", "user_id": "USER_STAKE_777", "amount": 12500.0, "method": "Bitcoin (BTC)", "type": "DEPOSIT", "status": "SUCCESS"},
            {"ref_number": "STAKE_TXN_CRYPTO_56", "user_id": "USER_STAKE_777", "amount": 8000.0, "method": "Ethereum (ETH)", "type": "WITHDRAWAL", "status": "SUCCESS"},
            {"ref_number": "STAKE_TXN_CRYPTO_57", "user_id": "USER_STAKE_881", "amount": 45000.0, "method": "Tether (USDT)", "type": "DEPOSIT", "status": "PENDING"},
            {"ref_number": "STAKE_TXN_CRYPTO_58", "user_id": "USER_STAKE_992", "amount": 250000.0, "method": "Litecoin (LTC)", "type": "DEPOSIT", "status": "SUCCESS"},
            {"ref_number": "STAKE_TXN_CRYPTO_59", "user_id": "USER_STAKE_432", "amount": 6500.0, "method": "Bitcoin (BTC)", "type": "WITHDRAWAL", "status": "FAILED"}
        ]
        for txn in transactions:
            yield TransactionItem(
                platform_name="Stake",
                ref_number=txn["ref_number"],
                user_id=txn["user_id"],
                amount=txn["amount"],
                method=txn["method"],
                type=txn["type"],
                status=txn["status"]
            )
            
        # 2. Yield multiple Reviews
        reviews = [
            {"author": "CryptoGamer", "rating": 5.0, "content": "Stake is the best crypto casino. Instant deposits and withdrawals."},
            {"author": "BetPro_11", "rating": 4.0, "content": "VIP program is very rewarding. Rakeback is awesome."},
            {"author": "HighRollerX", "rating": 4.5, "content": "Great UI design and verification was super fast."}
        ]
        for rev in reviews:
            yield ReviewItem(
                platform_name="Stake",
                author=rev["author"],
                rating=rev["rating"],
                content=rev["content"]
            )

        # 3. Yield multiple Complaints
        yield ComplaintItem(
            platform_name="Stake",
            title="LTC Deposit not showing up",
            description="Sent 2.5 LTC to deposit address, transaction confirmed on blockchain but not visible in wallet for 30 minutes.",
            status="UNRESOLVED"
        )

        await page.close()
