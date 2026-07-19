import asyncio
import os
import re
import json
from datetime import datetime, timezone
from pathlib import Path

import nodriver as uc
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=True)

BASE_URL = os.getenv("BASE_URL", "https://22play8.com/")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")


class NodriverPaymentScraper:
    def __init__(self, headless=False, wait_timeout=15):
        self.headless = headless
        self.wait_timeout = wait_timeout
        self.base_url = BASE_URL
        self.output_dir = ROOT / "OUTPUT"
        self.multimedia_dir = self.output_dir / "multimedia"
        self.browser = None
        self.page = None
        self.context_selector = None
        self.iframe_url = None

        self.output_dir.mkdir(exist_ok=True)
        self.multimedia_dir.mkdir(exist_ok=True)

    async def start_browser(self):
        print("Starting nodriver browser...")
        self.browser = await uc.start(headless=self.headless)
        self.page = await self.browser.get(self.base_url)
        await asyncio.sleep(5)
        print("Website opened")

    async def js(self, expression):
        return await self.page.evaluate(expression)

    async def wait_for_page_load(self, seconds=3):
        await asyncio.sleep(seconds)

    # ========================================================
    # MANUAL LOGIN - SAME FLOW AS OLD WORKING CODE
    # ========================================================

    async def perform_login(self):
        print("\nStarting manual login flow...")
        self.page = await self.browser.get(self.base_url)
        await self.wait_for_page_load(4)

        print("1. Login manually in the browser.")
        print("2. Complete CAPTCHA manually if shown.")
        print("3. Open Deposit / Wallet page.")
        print("4. Make sure payment methods are visible.")
        input("\nWhen payment methods are visible, press ENTER here... ")

        print("Continuing scraper with nodriver...")
        return True

    # ========================================================
    # DOM CONTEXT / IFRAME
    # ========================================================

    async def switch_to_payment_iframe(self):
        """
        nodriver does not use Selenium-style switch_to.frame().
        We locate a payment iframe and navigate a nodriver tab/page object
        to its src when possible. If no iframe exists, use the current page.
        """
        selectors = [
            "iframe[name*='payment']",
            "iframe[id*='payment']",
            "iframe[src*='paysystem']",
            "iframe[src*='deposit']",
            "iframe#payments_frame",
        ]

        for selector in selectors:
            try:
                src = await self.js(f"""
                (() => {{
                    const el = document.querySelector({json.dumps(selector)});
                    return el ? el.src : null;
                }})()
                """)
                if src:
                    print(f"Payment iframe found: {selector}")
                    self.iframe_url = src
                    self.page = await self.browser.get(src)
                    await self.wait_for_page_load(4)
                    self.context_selector = selector
                    print("Opened payment iframe URL in nodriver tab")
                    return True
            except Exception as e:
                print(f"Iframe check failed for {selector}: {e}")

        print("No payment iframe found; checking current page directly")
        self.context_selector = None
        return True

    # ========================================================
    # PAYMENT METHODS
    # ========================================================

    async def extract_payment_methods(self):
        selectors = [
            ".payment-cell",
            ".payment_item",
            "[data-method]",
            "[data-icon]",
            ".payment-cell--recommended",
        ]

        for selector in selectors:
            try:
                count = await self.js(f"""
                (() => document.querySelectorAll({json.dumps(selector)}).length)()
                """)
                if count and int(count) > 0:
                    print(f"Found {count} payment elements with selector: {selector}")
                    return selector, int(count)
            except Exception:
                pass

        return None, 0

    async def extract_payment_name(self, method_selector, index):
        name_selectors = [
            ".payment-cell-name__caption",
            ".payment_item__name",
            ".payment-cell__name",
            "[title]",
        ]

        result = await self.js(f"""
        (() => {{
            const methods = document.querySelectorAll({json.dumps(method_selector)});
            const root = methods[{index}];
            if (!root) return "Unknown";

            const nameSelectors = {json.dumps(name_selectors)};
            for (const s of nameSelectors) {{
                const el = root.querySelector(s);
                if (el) {{
                    const value = el.getAttribute("title") || el.innerText || el.textContent;
                    if (value && value.trim()) return value.trim();
                }}
            }}

            const fallback = root.getAttribute("title") || root.innerText || root.textContent;
            return fallback && fallback.trim() ? fallback.trim().slice(0, 150) : "Unknown";
        }})()
        """)
        return result or "Unknown"

    async def click_payment_method(self, method_selector, index):
        try:
            result = await self.js(f"""
            (() => {{
                const methods = document.querySelectorAll({json.dumps(method_selector)});
                const el = methods[{index}];
                if (!el) return false;
                el.scrollIntoView({{block: "center"}});
                el.click();
                return true;
            }})()
            """)
            await asyncio.sleep(4)
            return bool(result)
        except Exception as e:
            print("Payment click error:", e)
            return False

    # ========================================================
    # BUTTON NAVIGATION
    # ========================================================

    async def find_any_clickable_button(self, excluded_texts=None):
        excluded_texts = excluded_texts or []

        result = await self.js(f"""
        (() => {{
            const excluded = {json.dumps(excluded_texts)};
            const keywords = [
                "confirm", "ok", "continue", "proceed",
                "submit", "pay", "deposit"
            ];

            const candidates = Array.from(
                document.querySelectorAll(
                    'button, input[type="button"], input[type="submit"], [role="button"], .btn, .button, .payment_modal_btn'
                )
            );

            function visible(el) {{
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 &&
                       s.display !== "none" &&
                       s.visibility !== "hidden";
            }}

            const usable = candidates.filter(el => {{
                if (!visible(el)) return false;

                const text = (
                    el.innerText ||
                    el.value ||
                    el.getAttribute("aria-label") ||
                    el.getAttribute("onclick") ||
                    ""
                ).trim();

                const lower = text.toLowerCase();

                if (["cancel", "close", "back", "exit"].some(x => lower.includes(x)))
                    return false;

                if (excluded.includes(text))
                    return false;

                return keywords.some(x => lower.includes(x)) ||
                       el.classList.contains("alerts-ok") ||
                       el.classList.contains("payment_modal_btn");
            }});

            if (!usable.length) return null;

            const el = usable[0];
            const text = (
                el.innerText ||
                el.value ||
                el.getAttribute("aria-label") ||
                el.getAttribute("onclick") ||
                "No text"
            ).trim();

            el.setAttribute("data-nodriver-target", "1");

            return JSON.stringify({{
                text,
                tag: el.tagName,
                className: el.className || ""
            }});
        }})()
        """)

        if not result:
            return None
        return json.loads(result)

    async def click_marked_button(self):
        return await self.js("""
        (() => {
            const el = document.querySelector('[data-nodriver-target="1"]');
            if (!el) return false;
            el.scrollIntoView({block: "center"});
            el.click();
            el.removeAttribute("data-nodriver-target");
            return true;
        })()
        """)

    async def navigate_with_max_depth(self, max_depth=2):
        current_depth = 0
        clicked_buttons = []

        print(f"Starting navigation with max depth: {max_depth}")

        while current_depth < max_depth:
            print(f"\n--- Navigation Depth: {current_depth + 1}/{max_depth} ---")
            await asyncio.sleep(5)

            info = await self.find_any_clickable_button(clicked_buttons)

            if not info:
                print("No more payment buttons found")
                break

            button_text = info.get("text", "No text")
            print(
                f"Found clickable button: '{button_text}' | "
                f"Class: '{info.get('className', '')}' | "
                f"Tag: {info.get('tag', '')}"
            )

            clicked = await self.click_marked_button()
            if not clicked:
                print("Failed to click button")
                break

            print(f"Clicked: {button_text}")
            clicked_buttons.append(button_text)
            current_depth += 1
            await asyncio.sleep(3)

            current_url = str(self.page.url)
            if any(x in current_url.lower() for x in
                   ["success", "complete", "error", "failed", "redirect"]):
                print("Completion URL detected:", current_url)
                break

        print("Navigation completed at depth:", current_depth)
        print("Buttons clicked:", clicked_buttons)
        return current_depth

    # ========================================================
    # HTML / SCREENSHOT
    # ========================================================

    async def get_html(self):
        return await self.js("document.documentElement.outerHTML")

    async def take_screenshot(self, payment_name, suffix="_final"):
        clean_name = re.sub(r"[^\w\-.]", "_", payment_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.multimedia_dir / f"{clean_name}{suffix}_{timestamp}.png"

        try:
            await self.page.save_screenshot(str(path))
            print("Screenshot saved:", path)
            return str(path)
        except Exception as e:
            print("Screenshot error:", e)
            return None

    # ========================================================
    # EXTRACTION LOGIC - KEPT FROM OLD CODE
    # ========================================================

    def extract_plain_text(self, html):
        soup = BeautifulSoup(html, "html.parser")
        collected = []

        visible = soup.get_text(separator="\n", strip=True)
        if visible:
            collected.append(visible)

        for el in soup.find_all(True):
            for attr, val in el.attrs.items():
                if isinstance(val, (list, tuple)):
                    val = " ".join(val)

                if val and (
                    attr in ["value", "alt", "title", "aria-label", "placeholder"]
                    or attr.startswith("data-")
                ):
                    collected.append(str(val).strip())

        plain_text = "\n".join(collected)
        plain_text = re.sub(r"\n\s*\n+", "\n\n", plain_text)
        return "\n".join(x.strip() for x in plain_text.splitlines() if x.strip())

    def extract_upi_details(self, soup, plain_text):
        details = {"upi_id": "", "upi_name": ""}
        upi_pattern = re.compile(r"[a-zA-Z0-9.\-_]+@[a-zA-Z0-9]+")
        found = upi_pattern.findall(plain_text)

        if found:
            details["upi_id"] = found[0]

        for label in soup.find_all(string=re.compile(
            r"UPI ID|VPA|Payee Name|Name", re.IGNORECASE
        )):
            parent = label.parent
            next_text = parent.get_text() if parent else ""
            cleaned = next_text.replace(str(label), "").strip(": \n")

            if "ID" in str(label).upper() and not details["upi_id"]:
                details["upi_id"] = cleaned
            elif "NAME" in str(label).upper():
                details["upi_name"] = cleaned

        return details

    def extract_bank_details(self, soup, plain_text):
        details = {
            "bank_holder_name": "",
            "bank_account_number": "",
            "bank_ifsc_code": "",
            "bank_name": "",
        }

        ifsc_pattern = re.compile(r"[A-Z]{4}0[A-Z0-9]{6}")
        acc_pattern = re.compile(r"\b\d{9,18}\b")

        ifsc = ifsc_pattern.search(plain_text)
        if ifsc:
            details["bank_ifsc_code"] = ifsc.group(0)

        for match in acc_pattern.findall(plain_text):
            details["bank_account_number"] = match
            break

        for field in soup.find_all(["span", "div", "td", "label"]):
            text = field.get_text().strip()

            if re.search(r"Beneficiary|Holder|Account Name", text, re.I):
                sibling = field.find_next_sibling()
                if sibling:
                    details["bank_holder_name"] = sibling.get_text().strip()

            elif re.search(r"Bank Name", text, re.I):
                sibling = field.find_next_sibling()
                if sibling:
                    details["bank_name"] = sibling.get_text().strip()

        return details

    def extract_crypto_details(self, soup, plain_text):
        details = {"crypto_id": "", "crypto_value": ""}

        pattern = re.compile(
            r"\b(0x[a-fA-F0-9]{40}|[13][a-km-zA-HJ-NP-Z1-9]{26,33}|T[A-Za-z1-9]{33})\b"
        )

        match = pattern.search(plain_text)
        if match:
            details["crypto_id"] = match.group(0)

        for label in soup.find_all(
            string=re.compile(r"Address|Network|Crypto Address", re.I)
        ):
            val = label.find_next()
            if val:
                details["crypto_value"] = val.get_text().strip()

        return details

    def extract_transaction_details(self, html, plain_text, payment_name):
        soup = BeautifulSoup(html, "html.parser")
        details = {}

        upi = self.extract_upi_details(soup, plain_text)
        bank = self.extract_bank_details(soup, plain_text)
        crypto = self.extract_crypto_details(soup, plain_text)

        details.update(upi)
        details.update(bank)
        details.update(crypto)

        return details

    def extract_reference_urls(self, html):
        soup = BeautifulSoup(html, "html.parser")
        urls = []

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith(("http", "https", "//")):
                urls.append(href)

        return list(set(urls))

    def should_save_method_data(self, method_data):
        d = method_data.get("transaction_details", {})

        valid_upi = bool(d.get("upi_id", "").strip())
        valid_bank = any([
            d.get("bank_holder_name", "").strip(),
            d.get("bank_ifsc_code", "").strip(),
        ])
        valid_crypto = bool(
            d.get("crypto_id", "").strip()
            and d.get("crypto_value", "").strip()
        )

        return valid_upi or valid_bank or valid_crypto

    def save_method_data(self, method_data):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        method_name = re.sub(
            r"[^\w\-.]",
            "_",
            method_data.get("payment_method", "unknown")
        )

        path = self.output_dir / f"payment_{method_name}_{timestamp}.json"

        with open(path, "w", encoding="utf-8") as f:
            json.dump(method_data, f, indent=2, ensure_ascii=False)

        print("Data saved:", path)
        return str(path)

    # ========================================================
    # MAIN FLOW
    # ========================================================

    async def run(self):
        processed_count = 0
        valid_count = 0

        try:
            print("Starting nodriver payment scraper")
            print("Target URL:", self.base_url)

            await self.start_browser()
            await self.perform_login()

            # IMPORTANT:
            # The manual login flow leaves you on Deposit/Wallet page.
            # Do not reload BASE_URL here, because that would leave Deposit.
            await self.switch_to_payment_iframe()

            method_selector, count = await self.extract_payment_methods()

            if not method_selector or count == 0:
                print("No payment methods found")
                return

            methods_to_process = min(count, 103)
            print(f"Processing up to {methods_to_process} methods")

            # This conversion processes the current payment page safely.
            # For websites where each method changes URL/state differently,
            # the reset logic must be adapted after observing the real flow.
            for i in range(methods_to_process):
                processed_count += 1

                # Re-read methods on the current page.
                method_selector, current_count = await self.extract_payment_methods()

                if not method_selector or i >= current_count:
                    print(f"Method index {i} unavailable")
                    break

                try:
                    payment_name = await self.extract_payment_name(method_selector, i)

                    print("\n" + "=" * 60)
                    print(f"Processing {i + 1}/{methods_to_process}: {payment_name}")
                    print("=" * 60)

                    if not await self.click_payment_method(method_selector, i):
                        print("Could not click payment method")
                        continue

                    depth = await self.navigate_with_max_depth(max_depth=2)
                    await asyncio.sleep(5)

                    screenshot = await self.take_screenshot(payment_name)
                    html = await self.get_html()
                    plain_text = self.extract_plain_text(html)

                    transaction_details = self.extract_transaction_details(
                        html, plain_text, payment_name
                    )

                    method_data = {
                        "site_name": "22play",
                        "payment_method": payment_name,
                        "html": html,
                        "plain_text": plain_text,
                        "transaction_details": transaction_details,
                        "reference_urls": self.extract_reference_urls(html),
                        "fetchtime": datetime.now(timezone.utc).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "navigation_depth": depth,
                        "screenshots": {"final": screenshot},
                    }

                    if self.should_save_method_data(method_data):
                        valid_count += 1
                        self.save_method_data(method_data)
                    else:
                        print("No structured transaction data found")

                except Exception as e:
                    print(f"Method {i + 1} error:", repr(e))

                finally:
                    if hasattr(self, "iframe_url") and self.iframe_url:
                        print("Resetting: Navigating back to payment iframe URL...")
                        self.page = await self.browser.get(self.iframe_url)
                        await self.wait_for_page_load(4)
                    else:
                        print("Resetting: Reloading page...")
                        await self.page.reload()
                        await self.wait_for_page_load(4)

            print("\nFinished")
            print("Processed:", processed_count)
            print("Valid saved:", valid_count)

        finally:
            print("Browser left open for inspection.")
            input("Press ENTER to close browser... ")


async def main():
    scraper = NodriverPaymentScraper(headless=False)
    await scraper.run()


if __name__ == "__main__":
    uc.loop().run_until_complete(main())