import asyncio
import os
import re
import json
import sys
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

# Ensure console output uses UTF-8 to prevent UnicodeEncodeError on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

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
    # Wait for cashier cards to load/render
    await page.wait_for_timeout(3000)
    # Prefer text-based locator matching for card selection
    try:
        locator = page.get_by_text(name, exact=False).first
        await locator.wait_for(state="attached", timeout=6000)
        return await locator.element_handle()
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
    if "modalId=cashier" in page.url:
        return True

    # Or check if payment cards are visible
    try:
        count = await page.locator("div[class*='PaymentRouteCard']").count()
        if count > 0:
            return True
    except Exception:
        pass

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
    if await wait_for_cashier_tiles(page, timeout=3000):
        return True

    if await is_cashier_open(page):
        if await wait_for_cashier_tiles(page, timeout=5000):
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
        await page.goto(FUNDS_URL, wait_until="load")
        await page.wait_for_timeout(3000)
    except Exception:
        pass

    return not await is_cashier_open(page)

async def ensure_cashier_open(page):
    if await open_cashier(page):
        return True

    for attempt in range(2):
        try:
            await page.goto(FUNDS_URL, wait_until="load")
            await page.wait_for_timeout(3000)
        except Exception:
            pass

        if await open_cashier(page):
            return True

    try:
        await page.goto("https://www.10cric247.com/", wait_until="load")
        await page.wait_for_timeout(3000)
    except Exception:
        pass

    return await open_cashier(page)

async def extract_payment_data(page_context, method_name):
    """Executes Step 8 to 14: Extracts HTML, QR, UPI, Bank, Crypto, and Saves output."""
    print(f"[INFO] Extracting data from {method_name}...")
    
    # Step 8: Get page source
    html_content = await page_context.content()
    safe_method_name = re.sub(r"[^\w\-.]", "_", method_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    html_path = f"html/{safe_method_name}_{timestamp}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Use BeautifulSoup to parse HTML content
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove script, style, head, meta, link, noscript tags to prevent false matches on build IDs/JS variables
    for tag in soup(["script", "style", "head", "meta", "link", "noscript"]):
        tag.decompose()
    
    # Extract plain text
    collected = []
    visible = soup.get_text(separator="\n", strip=True)
    if visible:
        collected.append(visible)
    for el in soup.find_all(True):
        for attr, val in el.attrs.items():
            if isinstance(val, (list, tuple)):
                val = " ".join(val)
            if val and (attr in ["value", "alt", "title", "aria-label", "placeholder"] or attr.startswith("data-")):
                collected.append(str(val).strip())
    plain_text = "\n".join(collected)
    plain_text = re.sub(r"\n\s*\n+", "\n\n", plain_text)
    plain_text = "\n".join(x.strip() for x in plain_text.splitlines() if x.strip())

    # Extract details using BS4 and regex
    upi_details = {"upi_id": "", "upi_name": ""}
    # 1. Regex search for UPI IDs
    found_upis = UPI_REGEX.findall(plain_text)
    # Filter out common support emails or generic domains if matched
    filtered_upis = [u for u in found_upis if not any(x in u.lower() for x in ["support@", "info@", "help@", "youremail@", "domain.com", "10cric"])]
    if filtered_upis:
        upi_details["upi_id"] = filtered_upis[0]

    # 2. DOM-based search for labels
    for label in soup.find_all(string=re.compile(r"UPI ID|VPA|Payee Name|Name", re.IGNORECASE)):
        try:
            parent = label.parent
            next_text = parent.get_text() if parent else ""
            cleaned = next_text.replace(str(label), "").strip(": \n")
            if "ID" in str(label).upper() and not upi_details["upi_id"]:
                if not any(x in cleaned.lower() for x in ["support@", "info@", "help@", "youremail@", "domain.com", "10cric"]):
                    upi_details["upi_id"] = cleaned
            elif "NAME" in str(label).upper():
                upi_details["upi_name"] = cleaned
        except Exception:
            continue

    # Extract Bank Details
    bank_details = {}
    if "account number" in html_content.lower() or "ifsc" in html_content.lower():
        bank_details = {"bank_holder_name": "", "bank_account_number": "", "bank_ifsc_code": "", "bank_name": ""}
        ifsc_pattern = re.compile(r"[A-Z]{4}0[A-Z0-9]{6}")
        acc_pattern = re.compile(r"\b\d{9,18}\b")

        ifsc_match = ifsc_pattern.search(plain_text)
        if ifsc_match:
            bank_details["bank_ifsc_code"] = ifsc_match.group(0)
        acc_matches = acc_pattern.findall(plain_text)
        for match in acc_matches:
            if bank_details["bank_ifsc_code"] and match in bank_details["bank_ifsc_code"]:
                continue
            bank_details["bank_account_number"] = match
            break

        for field in soup.find_all(["span", "div", "td", "label", "p"]):
            try:
                text = field.get_text().strip()
                if re.search(r"Beneficiary|Holder|Account Name", text, re.IGNORECASE):
                    sibling = field.find_next_sibling()
                    if sibling:
                        bank_details["bank_holder_name"] = sibling.get_text().strip()
                elif re.search(r"Bank Name", text, re.IGNORECASE):
                    sibling = field.find_next_sibling()
                    if sibling:
                        bank_details["bank_name"] = sibling.get_text().strip()
            except Exception:
                continue

    # Extract Crypto Details
    crypto_details = {}
    crypto_address_pattern = re.compile(r"\b(0x[a-fA-F0-9]{40}|[13][a-km-zA-HJ-NP-Z1-9]{26,33}|T[A-Za-z1-9]{33})\b")
    crypto_match = crypto_address_pattern.search(plain_text)
    if crypto_match:
        crypto_details = {"network": "", "address": crypto_match.group(0)}
        # Try to infer network
        if crypto_match.group(0).startswith("0x"):
            crypto_details["network"] = "ERC20/USDT"
        elif crypto_match.group(0).startswith("T"):
            crypto_details["network"] = "TRC20/USDT"
        elif crypto_match.group(0).startswith(("1", "3", "bc1")):
            crypto_details["network"] = "BTC"
            
    for label in soup.find_all(string=re.compile(r"Address|Network|Crypto Address", re.IGNORECASE)):
        try:
            val = label.find_next()
            if val:
                crypto_details["network_label"] = val.get_text().strip()
        except Exception:
            continue

    # Step 13: Take Screenshot
    screenshot_path = f"screenshots/{safe_method_name}_{timestamp}.png"
    if hasattr(page_context, "screenshot"):
        await page_context.screenshot(path=screenshot_path)
    elif hasattr(page_context, "page") and page_context.page:
        await page_context.page.screenshot(path=screenshot_path)

    # Step 14: Save JSON
    result = {
        "site": "10cric",
        "payment_method": method_name,
        "upi_id": upi_details["upi_id"],
        "upi_name": upi_details["upi_name"],
        "bank": bank_details,
        "crypto": crypto_details,
        "screenshot": screenshot_path,
        "scraped_at": datetime.now().isoformat()
    }
    
    json_path = f"json/{safe_method_name}_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)
        
    print(f"[SUCCESS] Saved data for {method_name} to {json_path}")


async def submit_deposit_amount_if_needed(page_context, amount="1000"):
    """Enters the default amount and clicks proceed/deposit if the amount form is visible"""
    print(f"[INFO] Checking for deposit amount form...")
    try:
        # Wait a bit for the card to expand / load inputs
        await page_context.wait_for_timeout(2000)
        
        # 1. Look for amount input field
        amount_input = None
        amount_selectors = [
            "input[type='number']",
            "input[name*='amount' i]",
            "input[id*='amount' i]",
            "input[placeholder*='amount' i]",
            "input[class*='amount' i]"
        ]
        
        for selector in amount_selectors:
            try:
                locator = page_context.locator(selector)
                count = await locator.count()
                for i in range(count):
                    el = locator.nth(i)
                    if await el.is_visible() and await el.is_enabled():
                        amount_input = el
                        break
                if amount_input:
                    break
            except Exception:
                continue

        if amount_input:
            print(f"[INFO] Found amount input field. Clearing and typing '{amount}'...")
            await amount_input.fill("")
            await amount_input.fill(amount)
            await page_context.wait_for_timeout(1000)
        else:
            # Check for preset amount buttons (e.g. 1000, 2000)
            preset_buttons = page_context.locator("//button[contains(text(), '500') or contains(text(), '1000') or contains(text(), '2000') or contains(text(), '1,000')]")
            count = await preset_buttons.count()
            if count > 0:
                for i in range(count):
                    btn = preset_buttons.nth(i)
                    if await btn.is_visible() and await btn.is_enabled():
                        text = await btn.inner_text()
                        print(f"[INFO] Found preset button '{text}'. Clicking it...")
                        await btn.click()
                        await page_context.wait_for_timeout(1000)
                        break

        # 2. Look for the submit/deposit/proceed button
        submit_btn = None
        button_locators = page_context.locator(
            "button, input[type='button'], input[type='submit'], [role='button'], .btn, .button, .payment_modal_btn"
        )
        
        keywords = ["deposit", "pay", "proceed", "confirm", "continue", "submit"]
        count = await button_locators.count()
        for idx in range(count):
            btn = button_locators.nth(idx)
            if await btn.is_visible() and await btn.is_enabled():
                try:
                    text = (await btn.inner_text() or await btn.get_attribute("value") or "").strip()
                    if any(k in text.lower() for k in keywords):
                        submit_btn = btn
                        break
                except Exception:
                    continue

        if submit_btn:
            try:
                text = (await submit_btn.inner_text() or await submit_btn.get_attribute("value") or "Submit").strip()
            except Exception:
                text = "Submit"
            # Clean up text for logging
            text = " ".join(text.split()[:5])
            print(f"[INFO] Clicking submit button: '{text}'...")
            await submit_btn.scroll_into_view_if_needed()
            await page_context.wait_for_timeout(500)
            await submit_btn.click(force=True)
            await page_context.wait_for_timeout(5000) # Wait for gateway/iframe to load
            return True
        else:
            print("[INFO] No deposit submit button found (might be direct or already on gateway).")
            return False

    except Exception as e:
        print(f"[WARNING] Error checking/submitting deposit amount: {e}")
        return False

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
        await page.goto(FUNDS_URL, wait_until="load")
        await page.wait_for_timeout(3000)

        if not await open_cashier(page):
            print("[WARNING] Cashier modal did not open from direct URL. Navigating to homepage and clicking deposit button.")
            await page.goto("https://www.10cric247.com/", wait_until="load")
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

        unique_method_names = []
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
            if name:
                name = name.strip()
                if name and name not in unique_method_names:
                    unique_method_names.append(name)

        print(f"[INFO] Detected unique payment methods: {unique_method_names}")

        # Step 5: Loop through methods and re-select the tile each time
        for method_index, name in enumerate(unique_method_names):
            print(f"[PROCESS] Activating method: {name} (index {method_index})")

            if not await ensure_cashier_open(page):
                print(f"[WARNING] Could not reopen the cashier modal for method '{name}'. Stopping.")
                break

            element = await find_payment_method_by_name(page, name)
            if not element:
                print(f"[WARNING] Could not find payment method tile for '{name}'")
                continue

            print(f"[DEBUG] Selected method tile label: {name}")

            clicked = False
            try:
                await element.scroll_into_view_if_needed()
                await page.wait_for_timeout(500)
                await element.click()
                clicked = True
            except Exception:
                pass

            if not clicked:
                try:
                    await element.click(force=True)
                    clicked = True
                except Exception as e:
                    print(f"[WARNING] Failed to click element for method '{name}': {e}")
                    continue

            # Enter deposit amount and proceed
            await submit_deposit_amount_if_needed(page)

            # Step 7: Check New page status (Same page, Tab, or Iframe)
            await page.wait_for_timeout(4000) # Allow rendering
            frames = page.frames
            payment_frame = None
            for frame in frames:
                if frame == page.main_frame:
                    continue
                if any(x in frame.url.lower() for x in ["payment", "checkout", "paysystem", "deposit", "cashier", "wallet"]):
                    payment_frame = frame
                    break
            
            if payment_frame:
                print(f"[INFO] Payment gateway detected inside iframe: {payment_frame.url}")
                await extract_payment_data(payment_frame, name)
            else:
                await extract_payment_data(page, name)

            # Step 15: Close Current Payment / Go back to list
            await close_cashier(page)
            await page.wait_for_timeout(2500)

            if not await wait_for_cashier_tiles(page):
                try:
                    await page.goto(FUNDS_URL, wait_until="load", timeout=15000)
                except Exception as ne:
                    print(f"[WARNING] Navigation to cashier URL failed: {ne}")
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