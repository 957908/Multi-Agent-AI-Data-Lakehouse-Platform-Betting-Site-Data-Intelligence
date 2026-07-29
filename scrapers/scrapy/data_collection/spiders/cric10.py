import scrapy
from scrapy_playwright.page import PageMethod
from datetime import datetime, timezone
from data_collection.items import PaymentMethodItem
from data_collection.spiders.melbet import classify_payment_type


class Cric10Spider(scrapy.Spider):
    name = "cric10"
    platform_name = "10Cric"
    platform_url = "https://www.10cric.com"
    deposit_page_url = "https://www.10cric.com/en-in/banking/"

    PAYMENT_SELECTORS = [
        ".payment-method",
        ".payment-system",
        ".payment-item",
        ".banking-method",
        ".deposit-option",
        "[class*='payment']",
        "[class*='banking']",
        "[class*='deposit']",
        ".method-name",
        "img[alt]",
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

        for selector in self.PAYMENT_SELECTORS:
            elements = await page.query_selector_all(selector)
            if elements:
                self.logger.info(f"[{self.platform_name}] Found {len(elements)} elements with: {selector}")
                for el in elements:
                    text = (await el.inner_text()).strip()
                    alt = await el.get_attribute("alt") or ""
                    data_name = await el.get_attribute("data-name") or await el.get_attribute("title") or ""
                    name = (text or alt or data_name).strip()
                    if len(name) < 2 or name.lower() in ["deposit", "withdraw", "payment", "method", "more", "show", "back"]:
                        continue
                    found_methods.append(name)
                if found_methods:
                    break

        seen = set()
        unique_methods = []
        for m in found_methods:
            if m not in seen:
                seen.add(m)
                unique_methods.append(m)

        if not unique_methods:
            self.logger.warning(f"[{self.platform_name}] No payment methods extracted. Deposit page may require authentication.")
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
                scrape_error=f"No payment method elements found on {source_url}"
            )
        else:
            self.logger.info(f"[{self.platform_name}] Extracted {len(unique_methods)} real payment methods.")
            for method_name in unique_methods:
                yield PaymentMethodItem(
                    platform_name=self.platform_name,
                    method_name=method_name,
                    method_type=classify_payment_type(method_name),
                    deposit_supported=True,
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
                    data_quality="REAL",
                    scrape_error=None
                )

        await page.close()

    async def errback(self, failure):
        self.logger.error(f"[{self.platform_name}] Request failed: {failure.getErrorMessage()}")
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
