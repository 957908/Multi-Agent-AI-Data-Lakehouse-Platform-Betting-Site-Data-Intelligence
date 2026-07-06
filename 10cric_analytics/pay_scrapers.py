import asyncio
import os
import re
import json
from datetime import datetime
from playwright.async_api import async_playwright

# -------------------------
# CONFIGURATION
# -------------------------

BASE_URL = "https://www.10cric247.com/"
CASHIER_URL = "https://www.10cric247.com/?modalId=cashier"

AUTH_FILE = "auth/auth_state.json"

os.makedirs("auth", exist_ok=True)
os.makedirs("html", exist_ok=True)
os.makedirs("json", exist_ok=True)
os.makedirs("screenshots", exist_ok=True)

# -------------------------
# REGEX
# -------------------------

UPI_REGEX = re.compile(
    r"[a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+"
)

BTC_REGEX = re.compile(
    r"(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,90}"
)

ETH_REGEX = re.compile(
    r"0x[a-fA-F0-9]{40}"
)

# -------------------------
# EXTRACTORS
# -------------------------

def extract_upi(text):
    match = UPI_REGEX.search(text)
    return match.group() if match else None


def extract_crypto(text):

    btc = BTC_REGEX.search(text)
    if btc:
        return {
            "network": "BTC",
            "address": btc.group()
        }

    eth = ETH_REGEX.search(text)
    if eth:
        return {
            "network": "ERC20",
            "address": eth.group()
        }

    return {}


# -------------------------
# SAVE
# -------------------------

async def save_output(
    page,
    method_name,
    data
):

    safe = (
        method_name
        .replace("/", "_")
        .replace(" ", "_")
    )

    await page.screenshot(
        path=f"screenshots/{safe}.png",
        full_page=True
    )

    with open(
        f"html/{safe}.html",
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            await page.content()
        )

    with open(
        f"json/{safe}.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


# -------------------------
# SCRAPER
# -------------------------

class PaymentScraper:

    async def login(self, browser):

        if os.path.exists(AUTH_FILE):

            print(
                "[INFO] Loading session..."
            )

            return await browser.new_context(
                storage_state=AUTH_FILE
            )

        context = await browser.new_context()

        page = await context.new_page()

        await page.goto(BASE_URL)

        print()
        print(
            "Login manually."
        )

        input(
            "Press ENTER after login..."
        )

        await context.storage_state(
            path=AUTH_FILE
        )

        return context

    async def discover_methods(
        self,
        page
    ):

        print(
            "[INFO] Discovering methods..."
        )

        methods = []

        text = await page.locator(
            "body"
        ).inner_text()

        print()
        print("=" * 50)
        print(text)
        print("=" * 50)

        known_methods = [
            "iCash.One",
            "QR Mobile Payments",
            "Crypto To FIAT"
        ]

        for item in known_methods:
            if item in text:
                methods.append(item)

        print(
            "FOUND:",
            methods
        )

        return methods

    async def scrape_method(
        self,
        page,
        method
    ):

        print(
            f"[INFO] {method}"
        )

        text = await page.locator(
            "body"
        ).inner_text()

        data = {

            "site":
                "generic",

            "payment_method":
                method,

            "upi_id":
                extract_upi(text),

            "crypto":
                extract_crypto(text),

            "scraped_at":
                datetime.now()
                .isoformat(),

            "url":
                page.url
        }

        await save_output(
            page,
            method,
            data
        )

    async def run(self):

        async with async_playwright() as p:

            browser = await p.chromium.launch(
                headless=False
            )

            context = await self.login(
                browser
            )

            page = await context.new_page()

            await page.goto(
                CASHIER_URL
            )

            await page.wait_for_timeout(
                10000
            )

            methods = await self.discover_methods(
                page
            )

            print(
                "[FOUND]",
                methods
            )

            for method in methods:

                try:

                    await self.scrape_method(
                        page,
                        method
                    )

                except Exception as e:

                    print(
                        "[ERROR]",
                        method,
                        e
                    )

            await browser.close()


# -------------------------
# MAIN
# -------------------------

if __name__ == "__main__":

    scraper = PaymentScraper()

    asyncio.run(
        scraper.run()
    )