import asyncio
import os
import re
import json
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Setup mock folders
os.makedirs("html", exist_ok=True)
os.makedirs("screenshots", exist_ok=True)
os.makedirs("json", exist_ok=True)
os.makedirs("auth", exist_ok=True)

SESSION_FILE = "auth/auth_state.json"
TARGET_URL = "https://www.10cric247.com/login"
FUNDS_URL = "https://www.10cric247.com/?modalId=cashier"

# Common Regex Patterns for extraction
UPI_REGEX = re.compile(r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}")
BTC_REGEX = re.compile(r"\b(1[a-km-zA-HJ-NP-Z1-9]{26,33}|3[a-km-zA-HJ-NP-Z1-9]{26,35}|bc1[a-zA-HJ-NP-Z0-9]{25,90})\b")
ETH_ERC20_REGEX = re.compile(r"\b0x[a-fA-F0-9]{40}\b")

async def extract_method_name(element):
    name = await element.get_attribute("data-name")
    if name:
        return name.strip()

    for attr in ("data-method", "data-payment", "aria-label", "title"):
        name = await element.get_attribute(attr)
        if name:
            return name.strip()

    text = await element.inner_text()
    if text:
        return text.strip().splitlines()[0].strip()

    return None

KNOWN_PAYMENT_TERMS = [
    "iCash.One",
    "QR Mobile",
    "Crypto",
    "Crypto to",
    "UPI",
    "Fiat",
    "Crypto to FIAT",
    "QR Mobile Payments",
]

PAYMENT_TILE_SELECTORS = [
    "div[class*='PaymentRouteCard']",
    "div[class*='PaymentRouteCardBase_root']",
    ".payment-method-item",
    ".payment-method",
    ".payment-item",
    "[data-name]",
    "button[class*='payment']",
    "a[class*='payment']",
    "div[class*='card']",
    "div[class*='payment']",
]

CASHIER_TILE_SELECTOR = ", ".join([s for s in PAYMENT_TILE_SELECTORS if s])

async def find_payment_method_elements(page):
    for selector in PAYMENT_TILE_SELECTORS:
        locator = page.locator(selector)
        count = await locator.count()
        if count == 0:
            continue

        matched_indices = []
        for i in range(count):
            try:
                text = await locator.nth(i).inner_text()
            except Exception:
                continue
            if not text:
                continue
            if any(term.lower() in text.lower() for term in KNOWN_PAYMENT_TERMS):
                matched_indices.append(i)

        if matched_indices:
            print(f"[INFO] Found {len(matched_indices)} payment method elements using selector: {selector}")
            return selector, matched_indices

    # fallback: scan broad clickable containers for known payment text
    fallback_selector = "div, button, a, li"
    locator = page.locator(fallback_selector)
    count = await locator.count()
    matched_indices = []
    for i in range(count):
        try:
            text = await locator.nth(i).inner_text()
        except Exception:
            continue
        if not text or len(text.strip()) < 5:
            continue
        if any(term.lower() in text.lower() for term in KNOWN_PAYMENT_TERMS):
            matched_indices.append(i)
            if len(matched_indices) >= 10:
                break

    if matched_indices:
        print(f"[INFO] Found {len(matched_indices)} fallback payment method candidates.")
        return fallback_selector, matched_indices

    return None, []

async def find_payment_method_by_name(page, name):
    # Prefer text-based locator matching for card selection
    try:
        locator = page.get_by_text(name, exact=False)
        if await locator.count() > 0:
            return await locator.first.element_handle()
    except Exception:
        pass

    try:
        locator = page.locator(f"button:has-text('{name}'), div:has-text('{name}'), a:has-text('{name}')")
        if await locator.count() > 0:
            return await locator.first.element_handle()
    except Exception:
        pass

    possible_locators = [
        f"[data-name=\"{name}\"]",
        f"[aria-label=\"{name}\"]",
        f"[title=\"{name}\"]",
    ]

    for locator_str in possible_locators:
        try:
            element = await page.query_selector(locator_str)
            if element:
                return element
        except Exception:
            continue

    # fallback to first card containing the method name
    cards = await page.query_selector_all("div, button, a, li")
    for el in cards:
        try:
            text = await el.inner_text()
        except Exception:
            continue
        if name.lower() in text.lower():
            return el

    return None

async def is_cashier_open(page):
    try:
        body_text = (await page.locator("body").inner_text() or "").lower()
    except Exception:
        body_text = ""

    if "add funds" in body_text or "add money" in body_text or "add fund" in body_text:
        return True
    if "fiat" in body_text and "crypto" in body_text:
        return True
    return False

async def wait_for_cashier_tiles(page, timeout=8000):
    if not CASHIER_TILE_SELECTOR:
        return False

    try:
        await page.wait_for_selector(CASHIER_TILE_SELECTOR, timeout=timeout)
        return True
    except Exception:
        try:
            body_text = (await page.locator("body").inner_text() or "").lower()
        except Exception:
            body_text = ""
        return "add funds" in body_text or "add money" in body_text or "add fund" in body_text

async def js_click(page, selector):
    try:
        handle = await page.query_selector(selector)
        if handle:
            await handle.evaluate("el => el.click()")
            return True
    except Exception:
        pass
    return False

async def open_cashier(page):
    if await is_cashier_open(page) or await wait_for_cashier_tiles(page):
        return True

    deposit_selectors = [
        "[data-uat='header-deposit-button']",
        "button:has-text('Deposit')",
        "button:has-text('deposit')",
        "button:has-text('Add funds')",
        "button:has-text('Add Funds')",
        "button[class*='deposit']",
        "button[class*='Wallet_depositBtn']",
    ]

    for selector in deposit_selectors:
        try:
            locator = page.locator(selector).first
            if await locator.count() == 0:
                continue
            print(f"[INFO] Clicking deposit button using selector: {selector}")
            try:
                await locator.click(force=True)
            except Exception:
                if await js_click(page, selector):
                    pass
                else:
                    raise
            await page.wait_for_timeout(3000)
            if await wait_for_cashier_tiles(page):
                return True
        except Exception as e:
            print(f"[DEBUG] could not click deposit selector {selector}: {e}")

    # fallback: explicit JS click on known attributes
    js_selectors = ["[data-uat='header-deposit-button']", "button[class*='deposit']"]
    for selector in js_selectors:
        if await js_click(page, selector):
            await page.wait_for_timeout(3000)
            if await wait_for_cashier_tiles(page):
                return True

    buttons = await page.query_selector_all("button")
    for btn in buttons:
        try:
            text = (await btn.inner_text() or "").strip().lower()
        except Exception:
            continue
        if any(term in text for term in ["deposit", "add funds", "add fund", "cashier"]):
            try:
                await btn.click(force=True)
                await page.wait_for_timeout(3000)
                if await wait_for_cashier_tiles(page):
                    return True
            except Exception:
                continue

    return False

async def close_cashier(page):
    close_selectors = [
        ".close-dialog-btn",
        "button[aria-label='Close']",
        "button:has-text('X')",
        "button:has-text('Close')",
        "button:has-text('close')",
        ".modal-close",
        ".popup-close",
        ".close"
    ]

    for selector in close_selectors:
        try:
            element = await page.query_selector(selector)
            if element:
                print(f"[INFO] Closing cashier modal using selector: {selector}")
                await element.click()
                await page.wait_for_timeout(2500)
                if not await is_cashier_open(page):
                    return True
        except Exception:
            continue

    # fallback: reload the page and reopen if needed
    try:
        await page.goto(FUNDS_URL, wait_until="networkidle")
        await page.wait_for_timeout(3000)
    except Exception:
        pass

    return not await is_cashier_open(page)

async def ensure_cashier_open(page):
    if await open_cashier(page):
        return True

    for attempt in range(2):
        try:
            await page.goto(FUNDS_URL, wait_until="networkidle")
            await page.wait_for_timeout(3000)
        except Exception:
            pass

        if await open_cashier(page):
            return True

    try:
        await page.goto("https://www.10cric247.com/", wait_until="networkidle")
        await page.wait_for_timeout(3000)
    except Exception:
        pass

    return await open_cashier(page)

async def extract_payment_data(page_context, method_name):
    """Executes Step 8 to 14: Extracts HTML, QR, UPI, Bank, Crypto, and Saves output."""
    print(f"[INFO] Extracting data from {method_name}...")
    
    # Step 8: Get page source
    html_content = await page_context.content()
    with open(f"html/{method_name}.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    # Placeholders for data extraction
    upi_id = None
    bank_details = {}
    crypto_details = {}

    # Step 10: Extract UPI using Regex
    upi_matches = UPI_REGEX.findall(html_content)
    if upi_matches:
        upi_id = upi_matches[0]

    # Step 11: Extract Bank Details using text searches
    if "account number" in html_content.lower() or "ifsc" in html_content.lower():
        # Example parsing of unstructured text (mockup logic)
        bank_details = {
            "bank_name": "Mock Bank",
            "account_number": "1234567890",
            "ifsc": "MOCK0001234"
        }

    # Step 12: Extract Crypto Address using Regex
    btc_matches = BTC_REGEX.findall(html_content)
    eth_matches = ETH_ERC20_REGEX.findall(html_content)
    if btc_matches:
        crypto_details = {"network": "BTC", "address": btc_matches[0]}
    elif eth_matches:
        crypto_details = {"network": "ERC20/USDT", "address": eth_matches[0]}

    # Step 13: Take Screenshot
    screenshot_path = f"screenshots/{method_name}.png"
    await page_context.screenshot(path=screenshot_path)

    # Step 14: Save JSON
    result = {
        "site": "generic_platform",
        "payment_method": method_name,
        "upi_id": upi_id,
        "bank": bank_details,
        "crypto": crypto_details,
        "screenshot": screenshot_path,
        "scraped_at": datetime.now().isoformat()
    }
    
    with open(f"json/{method_name}.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)
        
    print(f"[SUCCESS] Saved data for {method_name}")

async def run_workflow():
    async with async_playwright() as p:
        # Step 1: Open Browser (Headed representation to handle auth state creation)
        browser = await p.chromium.launch(headless=False)
        
        # Load session if it exists, otherwise prompt manual login
        if os.path.exists(SESSION_FILE):
            print("[INFO] Reusing saved authentication state...")
            context = await browser.new_context(storage_state=SESSION_FILE)
        else:
            print("[WARNING] Session state missing. Initiating Step 2 (Manual Login)...")
            context = await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(TARGET_URL)
            
            # Step 2: Pause execution to let user authenticate manually
            input("Log in manually in the browser window, then press Enter here to save session...")
            await context.storage_state(path=SESSION_FILE)
            print("[INFO] Session state written to auth/auth_state.json")

        page = await context.new_page()
        
        # Step 3: Open Add Funds Page
        print(f"[INFO] Navigating to Add Funds page: {FUNDS_URL}")
        await page.goto(FUNDS_URL, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        if not await open_cashier(page):
            print("[WARNING] Cashier modal did not open from direct URL. Navigating to homepage and clicking deposit button.")
            await page.goto("https://www.10cric247.com/", wait_until="networkidle")
            await page.wait_for_timeout(3000)
            success = await open_cashier(page)
            if not success:
                raise RuntimeError("Unable to open cashier page. The Add Funds modal may require manual interaction.")

        # Step 4: Find Payment Methods List using fallback selectors
        try:
            selector, method_indices = await find_payment_method_elements(page)
        except Exception as e:
            print(f"[WARNING] Payment method lookup failed: {e}")
            selector, method_indices = None, []

        if not method_indices:
            body_text = await page.locator("body").inner_text()
            if "login" in body_text.lower() or "log in" in body_text.lower():
                raise RuntimeError("Page appears to require login or auth state is invalid. Please verify auth/auth_state.json.")

            print("[WARNING] No payment method elements found on the page.")
            debug_html = await page.content()
            with open("html/cashier_debug_page.html", "w", encoding="utf-8") as f:
                f.write(debug_html)
            await page.screenshot(path="cashier_debug.png", full_page=True)
            print("[INFO] Saved debug page HTML and screenshot.")
            return

        method_names = []
        locator = page.locator(selector)
        for index in method_indices:
            try:
                name = await extract_method_name(await locator.nth(index).element_handle())
            except Exception:
                name = None
            if not name:
                try:
                    name = (await locator.nth(index).inner_text()).splitlines()[0].strip()
                except Exception:
                    name = None
            if not name:
                continue
            method_names.append(name)

        print(f"[INFO] Detected payment methods: {method_names}")

        # Step 5: Loop through methods and re-select the tile each time
        for method_index, name in enumerate(method_names):
            print(f"[PROCESS] Activating method: {name} (index {method_index})")

            if not await ensure_cashier_open(page):
                print(f"[WARNING] Could not reopen the cashier modal for method '{name}'. Stopping.")
                break

            selector, method_indices = await find_payment_method_elements(page)
            if method_index >= len(method_indices):
                print(f"[WARNING] Expected {method_index + 1} payment methods but found {len(method_indices)}. Stopping.")
                break

            locator = page.locator(selector).nth(method_indices[method_index])
            try:
                current_name = await locator.inner_text()
            except Exception:
                current_name = name
            print(f"[DEBUG] Selected method tile label: {current_name}")

            clicked = False
            try:
                await locator.scroll_into_view_if_needed()
            except Exception:
                pass

            try:
                await locator.click()
                clicked = True
            except Exception:
                pass

            if not clicked:
                try:
                    child = await locator.query_selector("button, a")
                    if child:
                        await child.click()
                        clicked = True
                except Exception:
                    pass

            if not clicked:
                try:
                    await locator.click(force=True)
                    clicked = True
                except Exception as e:
                    print(f"[WARNING] Failed to click element for method '{name}': {e}")
                    continue

            await page.wait_for_timeout(4000) # Allow rendering

            # Step 7: Check New page status (Same page, Tab, or Iframe)
            frames = page.frames
            # If the platform loads an external billing portal inside an iframe
            payment_frame = None
            for frame in frames:
                if "payment" in frame.url or "checkout" in frame.url:
                    payment_frame = frame
                    break
            
            if payment_frame:
                print(f"[INFO] Payment gateway detected inside iframe: {payment_frame.url}")
                await extract_payment_data(payment_frame, name)

            else:
                # Same page or popup window check
                await extract_payment_data(page, name)


            # Step 15: Close Current Payment / Go back to list
            await close_cashier(page)
            await page.wait_for_timeout(2500)

            if not await wait_for_cashier_tiles(page):
                await page.goto(FUNDS_URL, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                await open_cashier(page)
                await page.wait_for_timeout(2500)

            print()
            print("="*50)
            print("CURRENT URL")
            print(page.url)
            print("="*50)
            buttons = await page.locator("button").all()

            print("\n========== BUTTONS ==========\n")

            for i, btn in enumerate(buttons):
                try:
                    text = await btn.inner_text()

                    if text.strip():
                        print(
                            f"{i+1}.",
                            text.strip()
                        )

                except Exception:
                    continue

            print("\n=============================\n")
            
            print("\n========== LINKS ==========\n")
            links = await page.locator("a").all()

            for i, link in enumerate(links):
                try:
                    text = await link.inner_text()
                    href = await link.get_attribute("href")

                    if text.strip():
                        print(
                            f"{i+1}.",
                            text.strip(),
                            "=>",
                            href
                        )

                except Exception:
                    continue

            print("\n===========================\n")
            print("\n========== URL ==========\n")
            print(page.url)

            print("\n========== TITLE ==========\n")
            print(await page.title())

            await page.screenshot(
                path="cashier_debug.png",
                full_page=True
            )
if __name__ == "__main__":
    asyncio.run(run_workflow())