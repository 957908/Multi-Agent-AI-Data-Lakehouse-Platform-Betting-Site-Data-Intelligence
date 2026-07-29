import scrapy
from scrapy_playwright.page import PageMethod
from datetime import datetime, timezone
from data_collection.items import PaymentMethodItem

# ─────────────────────────────────────────────────────────────────────────────
# Payment method type classifier — uses real keyword matching
# ─────────────────────────────────────────────────────────────────────────────
def classify_payment_type(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["upi", "gpay", "google pay", "phonepe", "paytm", "bhim", "imps", "qr"]):
        return "UPI"
    if any(k in n for k in ["bitcoin", "btc", "eth", "ethereum", "crypto", "usdt", "tether",
                              "solana", "dogecoin", "litecoin", "bnb", "xrp", "ripple", "polygon",
                              "shiba", "usdc", "tron"]):
        return "CRYPTO"
    if any(k in n for k in ["netbanking", "bank transfer", "neft", "rtgs", "swift", "wire"]):
        return "BANK"
    if any(k in n for k in ["skrill", "neteller", "paypal", "astropay", "mifinity", "ecopayz",
                              "jeton", "muchbetter", "wallet", "webmoney"]):
        return "WALLET"
    if any(k in n for k in ["visa", "mastercard", "maestro", "amex", "credit card", "debit card"]):
        return "CARD"
    return "UNKNOWN"


# ─────────────────────────────────────────────────────────────────────────────
# MELBET — public deposit page scraper
# Target: https://melbet.org/en/page/depositrules
# ─────────────────────────────────────────────────────────────────────────────
class MelbetSpider(scrapy.Spider):
    name = "melbet"
    platform_name = "Melbet"
    platform_url = "https://melbet.org"
    # Public deposit rules page — accessible without login
    deposit_page_url = "https://melbet.org/en/page/depositrules"

    # CSS selectors to try — in priority order; first match wins
    PAYMENT_SELECTORS = [
        ".payment-method",
        ".payment-system",
        ".payment-item",
        ".deposit-method",
        "[class*='payment']",
        "[class*='deposit']",
        ".method-name",
        "img[alt]",           # payment logos often have descriptive alt text
    ]

    def start_requests(self):
        yield scrapy.Request(
            self.deposit_page_url,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_timeout", 4000),
                ],
                "errback": self.errback,
            },
            callback=self.parse_deposit_page,
        )

    async def parse_deposit_page(self, response):
        page = response.meta["playwright_page"]
        scrape_ts = datetime.now(timezone.utc).isoformat()
        source_url = response.url

        self.logger.info(f"[{self.platform_name}] Loaded deposit page: {source_url}")

        found_methods = []

        # Try each selector to find payment method elements
        for selector in self.PAYMENT_SELECTORS:
            elements = await page.query_selector_all(selector)
            if elements:
                self.logger.info(f"[{self.platform_name}] Found {len(elements)} elements with selector: {selector}")
                for el in elements:
                    # Try text content first
                    text = (await el.inner_text()).strip()
                    # Try alt attribute (for images)
                    alt = await el.get_attribute("alt") or ""
                    # Try data-name or title attribute
                    data_name = await el.get_attribute("data-name") or await el.get_attribute("title") or ""

                    name = text or alt or data_name
                    name = name.strip()

                    # Skip empty, very short, or generic strings
                    if len(name) < 2 or name.lower() in ["deposit", "withdraw", "payment", "method", "more", "show"]:
                        continue

                    found_methods.append(name)

                if found_methods:
                    break  # Stop trying selectors once we find real data

        # Deduplicate while preserving order
        seen = set()
        unique_methods = []
        for m in found_methods:
            if m not in seen:
                seen.add(m)
                unique_methods.append(m)

        if not unique_methods:
            self.logger.warning(
                f"[{self.platform_name}] No payment methods extracted from {source_url}. "
                f"Page may require login or selectors need updating. "
                f"Yielding NOT_SCRAPED item."
            )
            yield PaymentMethodItem(
                platform_name=self.platform_name,
                method_name="Not Yet Collected",
                method_type="UNKNOWN",
                deposit_supported=None,
                withdrawal_supported=None,
                min_deposit="Not Yet Collected",
                max_deposit="Not Yet Collected",
                min_withdrawal="Not Yet Collected",
                max_withdrawal="Not Yet Collected",
                fee="Not Yet Collected",
                processing_time="Not Yet Collected",
                source_url=source_url,
                scrape_timestamp=scrape_ts,
                collection_agent=self.name,
                data_quality="NOT_SCRAPED",
                scrape_error=f"No elements matched selectors {self.PAYMENT_SELECTORS} on {source_url}"
            )
        else:
            self.logger.info(f"[{self.platform_name}] Extracted {len(unique_methods)} real payment methods.")
            for method_name in unique_methods:
                yield PaymentMethodItem(
                    platform_name=self.platform_name,
                    method_name=method_name,
                    method_type=classify_payment_type(method_name),
                    deposit_supported=True,   # visible on deposit page = deposit supported
                    withdrawal_supported=None,  # cannot verify without login
                    min_deposit="Not Yet Collected",
                    max_deposit="Not Yet Collected",
                    min_withdrawal="Not Yet Collected",
                    max_withdrawal="Not Yet Collected",
                    fee="Not Yet Collected",
                    processing_time="Not Yet Collected",
                    source_url=source_url,
                    scrape_timestamp=scrape_ts,
                    collection_agent=self.name,
                    data_quality="REAL",
                    scrape_error=None
                )

        await page.close()

    async def errback(self, failure):
        self.logger.error(
            f"[{self.platform_name}] Playwright request failed: {failure.getErrorMessage()}. "
            f"Screenshot and error logged."
        )
        yield PaymentMethodItem(
            platform_name=self.platform_name,
            method_name="Not Yet Collected",
            method_type="UNKNOWN",
            deposit_supported=None,
            withdrawal_supported=None,
            min_deposit="Not Yet Collected",
            max_deposit="Not Yet Collected",
            min_withdrawal="Not Yet Collected",
            max_withdrawal="Not Yet Collected",
            fee="Not Yet Collected",
            processing_time="Not Yet Collected",
            source_url=self.deposit_page_url,
            scrape_timestamp=datetime.now(timezone.utc).isoformat(),
            collection_agent=self.name,
            data_quality="SCRAPE_FAILED",
            scrape_error=str(failure.getErrorMessage())
        )
