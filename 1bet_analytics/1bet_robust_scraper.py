import os
import sys
import re
import time
import json
from datetime import datetime, timezone
import urllib.parse
from dotenv import load_dotenv

# Ensure console output uses UTF-8 to prevent UnicodeEncodeError on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from bs4 import BeautifulSoup

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

# Load environment variables
load_dotenv()

# Import configuration fallback
try:
    from config import BASE_URL
except ImportError:
    BASE_URL = os.getenv("BASE_URL", "https://indi.1xbet.com")


class SimplifiedPaymentScraper:
    def __init__(self, headless=True, wait_timeout=15):
        self.wait_timeout = wait_timeout
        self.output_dir = "OUTPUT"
        self.base_url = BASE_URL
        self.all_payment_methods = []

        self.setup_output_directory()
        self.multimedia_dir = self.setup_multimedia_directory()
        self.setup_driver(headless)
        self.scraped_data = {}

    def setup_output_directory(self):
        """Create OUTPUT directory if it doesn't exist"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"Created OUTPUT directory: {self.output_dir}")
        else:
            print(f"Using existing OUTPUT directory: {self.output_dir}")

    def setup_multimedia_directory(self):
        """Create and return specialized multimedia folder within output path"""
        media_path = os.path.join(self.output_dir, "multimedia")
        if not os.path.exists(media_path):
            os.makedirs(media_path)
            print(f"Created multimedia directory: {media_path}")
        return media_path

    def setup_driver(self, headless=True):
        """Setup Chrome driver with appropriate options and stealth configuration"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")

        # Selenium Manager automatically resolves a ChromeDriver version
        # compatible with the installed Chrome browser.
        self.driver = webdriver.Chrome(options=chrome_options)

        stealth(self.driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL",
                fix_hairline=True)

        self.wait = WebDriverWait(self.driver, self.wait_timeout)

    def perform_login(self):
        print("Manual login mode enabled")

        self.driver.get(self.base_url)

        print("\nSTEP 1: Login manually")
        print("STEP 2: Open Deposit/Cashier page manually")
        print("STEP 3: Make sure payment methods are visible")
        print("STEP 4: Then come back to terminal")

        input("\nPress ENTER only after payment methods are visible...")

        return True

            

    def wait_for_page_load(self):
        """Wait for page to be completely loaded"""
        try:
            self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            time.sleep(2)
        except TimeoutException:
            print("Page load timeout - continuing anyway")

    def switch_to_payment_iframe(self):
        """Find and switch to payment iframe"""
        self.driver.switch_to.default_content()
        
        iframe_selectors = [
            "iframe[name*='payment']",
            "iframe[id*='payment']",
            "iframe[src*='paysystem']",
            "iframe[src*='deposit']",
            "iframe#payments_frame",
            "iframe[name*='17564400901360660812']"
        ]

        for selector in iframe_selectors:
            try:
                iframe = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                self.driver.switch_to.frame(iframe)
                print(f"Switched to payment iframe: {selector}")
                self.wait_for_page_load()
                return True
            except (TimeoutException, NoSuchElementException):
                continue

        print("No payment iframe found")
        return False

    def extract_payment_methods(self):
        """Extract 1xBet payment method buttons from the main Deposit page."""
        self.driver.switch_to.default_content()

        selectors = [
            "button.payment-method.payment-list-methods__button",
            "button.payment-list-methods__button",
            "li.payment-list-methods__item button.payment-method"
        ]

        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                visible = [el for el in elements if el.is_displayed()]
                print(f"Selector {selector} -> {len(elements)} elements ({len(visible)} visible)")

                if visible:
                    return visible
            except Exception as e:
                print(f"Error with selector {selector}: {e}")

        return []

    def extract_payment_name(self, element):
        """Extract the visible 1xBet payment method name."""
        try:
            name_element = element.find_element(By.CSS_SELECTOR, ".payment-method__name")
            name = name_element.text.strip()
            if name:
                return name
        except Exception:
            pass

        try:
            name = element.text.strip()
            return name if name else "Unknown"
        except Exception:
            return "Unknown"

    def click_payment_method(self, element):
        """Click on a payment method"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(2)
            
            try:
                element.click()
                return True
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception:
                    try:
                        ActionChains(self.driver).move_to_element(element).click().perform()
                        return True
                    except Exception:
                        return False
        except Exception as e:
            print(f"Error clicking payment method: {e}")
            return False

    def find_any_clickable_button(self):
        """Find only payment-flow action buttons inside the Deposit area.

        This deliberately ignores header/navigation buttons such as refresh and MORE.
        """
        self.driver.switch_to.default_content()

        scopes = self.driver.find_elements(
            By.CSS_SELECTOR,
            ".deposit-page, .deposit-page__main, .deposit__content, .payment"
        )
        if not scopes:
            return None, None

        allowed_words = (
            "confirm", "continue", "next", "proceed", "submit",
            "pay", "deposit", "get details", "show details"
        )
        blocked_words = (
            "more", "log out", "refresh", "cancel", "close", "back", "exit"
        )

        candidates = []
        for scope in scopes:
            try:
                candidates.extend(scope.find_elements(
                    By.CSS_SELECTOR,
                    "button, input[type='submit'], input[type='button'], a.ui-button"
                ))
            except Exception:
                pass

        seen = set()
        for el in candidates:
            try:
                key = el.id
                if key in seen:
                    continue
                seen.add(key)

                if not el.is_displayed() or not el.is_enabled():
                    continue

                text = (
                    el.text.strip()
                    or (el.get_attribute("value") or "").strip()
                    or (el.get_attribute("aria-label") or "").strip()
                    or (el.get_attribute("title") or "").strip()
                )
                normalized = text.lower().strip()

                if not normalized:
                    continue
                if any(word in normalized for word in blocked_words):
                    continue
                if any(word in normalized for word in allowed_words):
                    print(
                        f"Found payment-flow button: {text!r} | "
                        f"Class: {el.get_attribute('class') or ''}"
                    )
                    return el, text
            except Exception:
                continue

        print("No safe payment-flow action button found")
        return None, None

    def navigate_with_max_depth(self, max_depth=2):
        """Advance only through clearly named payment-flow actions."""
        clicked_buttons = []

        for depth in range(max_depth):
            print(f"\n--- Payment flow depth: {depth + 1}/{max_depth} ---")
            time.sleep(3)

            button, button_text = self.find_any_clickable_button()
            if not button:
                break

            normalized = button_text.lower().strip()
            if normalized in [x.lower() for x in clicked_buttons]:
                print(f"Already clicked {button_text!r}; stopping to avoid a loop")
                break

            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", button
                )
                time.sleep(1)
                try:
                    button.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", button)

                clicked_buttons.append(button_text)
                print(f"Clicked payment-flow button: {button_text!r}")
                time.sleep(4)
            except Exception as e:
                print(f"Payment-flow click failed: {e}")
                break

        print(f"Payment-flow buttons clicked: {clicked_buttons}")
        return len(clicked_buttons)

    def wait_for_payment_list(self, timeout=30):
        """Wait until the 1xBet Deposit payment-method list is visible."""
        self.driver.switch_to.default_content()
        selector = "button.payment-method.payment-list-methods__button"
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
            )
            return True
        except TimeoutException:
            return False

    def reset_to_deposit_page(self):
        """Return to the captured Deposit URL and wait for its SPA content."""
        print("Returning to Deposit page...")
        self.driver.switch_to.default_content()

        try:
            self.driver.get(self.deposit_url)
        except Exception as e:
            print(f"Deposit navigation error: {e}")
            return False

        self.wait_for_page_load()

        if self.wait_for_payment_list(timeout=30):
            return True

        print("Payment list did not appear; refreshing once...")
        try:
            self.driver.refresh()
            self.wait_for_page_load()
            return self.wait_for_payment_list(timeout=30)
        except Exception as e:
            print(f"Deposit refresh error: {e}")
            return False

    # --- Data Extraction Algorithms ---

    def extract_upi_details(self, soup, plain_text):
        """Extract typical VPA or UPI ID identifiers found inside gateways"""
        details = {"upi_id": "", "upi_name": ""}
        upi_pattern = re.compile(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9]+')
        found_upis = upi_pattern.findall(plain_text)
        
        if found_upis:
            details["upi_id"] = found_upis[0]

        for label in soup.find_all(string=re.compile(r'UPI ID|VPA|Payee Name|Name', re.IGNORECASE)):
            parent = label.parent
            next_text = parent.get_text() if parent else ""
            cleaned = next_text.replace(label, "").strip(": \n")
            if "ID" in label.upper() and not details["upi_id"]:
                details["upi_id"] = cleaned
            elif "NAME" in label.upper():
                details["upi_name"] = cleaned
        return details

    def validate_upi_details(self, details):
        """Sanitize structural outputs for UPI"""
        return {
            "upi_id": details.get("upi_id", "").strip(),
            "upi_name": details.get("upi_name", "").strip()
        }

    def extract_bank_details(self, soup, plain_text):
        """Parse structured layout elements looking for bank processing credentials"""
        details = {"bank_holder_name": "", "bank_account_number": "", "bank_ifsc_code": "", "bank_name": ""}
        
        ifsc_pattern = re.compile(r'[A-Z]{4}0[A-Z0-9]{6}')
        acc_pattern = re.compile(r'\b\d{9,18}\b')
        
        ifsc_match = ifsc_pattern.search(plain_text)
        if ifsc_match:
            details["bank_ifsc_code"] = ifsc_match.group(0)
            
        acc_matches = acc_pattern.findall(plain_text)
        for match in acc_matches:
            if details["bank_ifsc_code"] and match in details["bank_ifsc_code"]:
                continue
            details["bank_account_number"] = match
            break

        for field in soup.find_all(["span", "div", "td", "label"]):
            text = field.get_text().strip()
            if re.search(r'Beneficiary|Holder|Account Name', text, re.IGNORECASE):
                sibling = field.find_next_sibling()
                if sibling: details["bank_holder_name"] = sibling.get_text().strip()
            elif re.search(r'Bank Name', text, re.IGNORECASE):
                sibling = field.find_next_sibling()
                if sibling: details["bank_name"] = sibling.get_text().strip()

        return details

    def validate_bank_details(self, details):
        """Sanitize bank output details"""
        return {
            "bank_holder_name": details.get("bank_holder_name", "").strip(),
            "bank_account_number": details.get("bank_account_number", "").strip(),
            "bank_ifsc_code": details.get("bank_ifsc_code", "").strip(),
            "bank_name": details.get("bank_name", "").strip()
        }

    def extract_crypto_details(self, soup, plain_text):
        """Extract target chain IDs and transaction addresses"""
        details = {"crypto_id": "", "crypto_value": ""}
        crypto_address_pattern = re.compile(r'\b(0x[a-fA-F0-9]{40}|[13][a-km-zA-HJ-NP-Z1-9]{26,33}|T[A-Za-z1-9]{33})\b')
        match = crypto_address_pattern.search(plain_text)
        if match:
            details["crypto_id"] = match.group(0)

        for label in soup.find_all(text=re.compile(r'Address|Network|Crypto Address', re.IGNORECASE)):
            val = label.find_next()
            if val:
                details["crypto_value"] = val.get_text().strip()
        return details

    def validate_crypto_details(self, details):
        """Enforce strict field checks for Crypto data arrays"""
        return {
            "crypto_id": details.get("crypto_id", "").strip(),
            "crypto_value": details.get("crypto_value", "").strip()
        }

    def extract_reference_urls(self, html_content):
        """Collect deep hyperlinks present within current transaction state"""
        soup = BeautifulSoup(html_content, 'html.parser')
        urls = []
        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            if href.startswith(('http', 'https', '//')):
                urls.append(href)
        return list(set(urls))

    def extract_transaction_details(self, html_content, plain_text, payment_name):
        """Enhanced extraction with validation before saving"""
        transaction_details = {}
        soup = BeautifulSoup(html_content, 'html.parser')
        
        upi_details = self.extract_upi_details(soup, plain_text)
        transaction_details.update(self.validate_upi_details(upi_details))
        
        bank_details = self.extract_bank_details(soup, plain_text)
        transaction_details.update(self.validate_bank_details(bank_details))
        
        crypto_details = self.extract_crypto_details(soup, plain_text)
        transaction_details.update(self.validate_crypto_details(crypto_details))
        
        return transaction_details
        
    def should_save_method_data(self, method_data):
        """Determine if method data has valid transaction details worth saving"""
        transaction_details = method_data.get('transaction_details', {})
        
        upi_id = transaction_details.get('upi_id', '').strip()
        bank_holder_name = transaction_details.get('bank_holder_name', '').strip()
        bank_ifsc_code = transaction_details.get('bank_ifsc_code', '').strip()
        crypto_id = transaction_details.get('crypto_id', '').strip()
        crypto_value = transaction_details.get('crypto_value', '').strip()
        
        valid_upi = bool(upi_id)
        valid_bank = any([bank_holder_name, bank_ifsc_code])
        valid_crypto = bool(crypto_id and crypto_value)
        
        has_valid_data = valid_upi or valid_bank or valid_crypto
        
        if has_valid_data:
            print(f"✅ Method '{method_data.get('payment_method', 'Unknown')}' contains active extraction objects.")
        else:
            print(f"⚠️ Method '{method_data.get('payment_method', 'Unknown')}' has no structured gateway values parsed.")
        
        return has_valid_data

    def take_screenshot_enhanced(self, payment_name, suffix="", multimedia_dir=None):
        """Enhanced version of take_screenshot with multimedia directory support"""
        try:
            if not multimedia_dir:
                multimedia_dir = self.multimedia_dir
            
            clean_name = re.sub(r'[^\w\-_\.]', '_', payment_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_filename = f"{clean_name}{suffix}_{timestamp}.png"
            screenshot_path = os.path.join(multimedia_dir, screenshot_filename)
            
            try:
                self.driver.minimize_window()
                print(" Browser window minimized")
                time.sleep(1)
                self.driver.maximize_window()
            except Exception as e:
                print(f"⚠️ State manipulation window notice: {e}")
            
            success = self.driver.save_screenshot(screenshot_path)
            if success:
                print(f"✓ Screenshot saved: {screenshot_path}")
                return screenshot_path
            else:
                print(f"✗ Failed to save screenshot for {payment_name}")
                return None
        except Exception as e:
            print(f"Error taking screenshot for {payment_name}: {e}")
            return None

    def extract_plain_text(self, html):
        """Extract plain text + useful attribute values, with all tags removed"""
        soup = BeautifulSoup(html, "html.parser")
        collected_texts = []

        visible_text = soup.get_text(separator="\n", strip=True)
        if visible_text:
            collected_texts.append(visible_text)

        for el in soup.find_all(True):
            for attr, val in el.attrs.items():
                if isinstance(val, (list, tuple)):
                    val = " ".join(val)
                if val and (attr in ["value", "alt", "title", "aria-label", "placeholder"] or attr.startswith("data-")):
                    collected_texts.append(str(val).strip())

        plain_text = "\n".join(collected_texts)
        plain_text = re.sub(r"\n\s*\n+", "\n\n", plain_text)
        return "\n".join(line.strip() for line in plain_text.splitlines() if line.strip())

    def save_method_data(self, method_data):
        """Save individual method data to JSON file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            method_name = re.sub(r'[^\w\-_\.]', '_', method_data.get('payment_method', 'unknown'))
            json_filename = f"payment_{method_name}_{timestamp}.json"
            json_path = os.path.join(self.output_dir, json_filename)

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(method_data, f, indent=2, ensure_ascii=False)

            print(f"✅ Data saved to local file: {json_filename}")
            return json_path
        except Exception as e:
            print(f"❌ Error saving to JSON: {e}")
            return None

    def navigate_back_to_base(self):
        """Navigate back to base URL and re-login if needed"""
        try:
            print(f"🔙 Navigating back to: {self.base_url}")
            self.driver.get(self.base_url)
            self.wait_for_page_load()

            current_url = self.driver.current_url
            if "login" in current_url.lower():
                print("Re-login required...")
                if not self.perform_login():
                    return False
                self.driver.get(self.base_url)
                self.wait_for_page_load()
            return True
        except Exception as e:
            print(f"Error navigating back: {e}")
            return False

    def run_scraper_enhanced(self):
        """Main scraper orchestration block outputting directly to JSON storage files"""
        try:
            print("🚀 Starting Enhanced Payment Scraper with Local JSON File Storage")
            print(f"Output directory: {self.output_dir}")
            print(f"Multimedia directory: {self.multimedia_dir}")
            print(f"Target URL: {self.base_url}")
            
            processed_count = 0
            valid_count = 0
            
            print("Starting manual login...")
            self.perform_login()

            self.wait_for_page_load()

            print("Current URL:", self.driver.current_url)
            self.deposit_url = self.driver.current_url

            # Save the actual Selenium DOM of the Deposit page
            debug_html = self.driver.page_source
            debug_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "1xbet_deposit_selenium.html")

            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(debug_html)

            print(f"Saved actual Deposit DOM: {debug_path}")

            # Print useful clickable/card-like elements for selector discovery
            debug_selectors = [
                "button",
                "a",
                "[role='button']",
                "[class*='payment']",
                "[class*='deposit']",
                "[class*='method']",
                "[class*='cashier']",
                "[class*='recharge']"
            ]

            for selector in debug_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"DEBUG {selector} -> {len(elements)}")

                    for el in elements[:10]:
                        try:
                            print(
                                "TAG:", el.tag_name,
                                "| CLASS:", el.get_attribute("class"),
                                "| TEXT:", repr(el.text[:100])
                            )
                        except Exception:
                            pass
                except Exception as e:
                    print(f"DEBUG selector error {selector}: {e}")

            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            print("Total iframes found:", len(iframes))

            for i, frame in enumerate(iframes):
                print(
                f"Iframe {i}: "
                f"id={frame.get_attribute('id')} "
                f"name={frame.get_attribute('name')} "
                f"src={frame.get_attribute('src')}"
            )

            print("Using main Deposit page for payment methods")
            self.driver.switch_to.default_content()
            payment_elements = self.extract_payment_methods()

            print(f"Found {len(payment_elements)} payment methods")

            if not payment_elements:
                print("No payment methods found!")

                selectors = [
                ".payment-cell",
                ".payment_item",
                "[data-method]",
                "[data-icon]",
                ".payment-cell--recommended"
                ]

                for selector in selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        print(f"{selector} -> {len(elements)} elements")
                    except Exception as e:
                        print(f"{selector} -> ERROR: {e}")

                return

            max_methods_to_process = 103
            method_names = [self.extract_payment_name(el) for el in payment_elements]
            method_names = method_names[:max_methods_to_process]

            print(f"Processing {len(method_names)} payment methods:")
            print(method_names)

            for i, target_name in enumerate(method_names, start=1):
                try:
                    processed_count += 1

                    if i > 1:
                        if not self.reset_to_deposit_page():
                            print(f"Could not restore Deposit page for method {i}: {target_name}")
                            continue

                    payment_elements = self.extract_payment_methods()

                    # Find the method again by name after each SPA reload.
                    element = None
                    for candidate in payment_elements:
                        if self.extract_payment_name(candidate) == target_name:
                            element = candidate
                            break

                    if element is None:
                        print(f"Payment method not found after reload: {target_name}")
                        continue

                    payment_name = target_name

                    print(f"\n{'='*60}")
                    print(f"Processing method {i}/{len(method_names)}: {payment_name}")
                    print(f"{'='*60}")

                    before_url = self.driver.current_url
                    before_handles = set(self.driver.window_handles)

                    if not self.click_payment_method(element):
                        print(f"Failed to click payment method: {payment_name}")
                        continue

                    time.sleep(5)

                    # If the method opened a new tab, inspect that tab.
                    after_handles = set(self.driver.window_handles)
                    new_handles = list(after_handles - before_handles)
                    if new_handles:
                        self.driver.switch_to.window(new_handles[-1])
                        print("Switched to newly opened payment tab")

                    navigation_depth = self.navigate_with_max_depth(max_depth=2)

                    print("Waiting for final payment state...")
                    time.sleep(5)

                    final_screenshot = self.take_screenshot_enhanced(
                        payment_name, "_final", self.multimedia_dir
                    )
                    html_content = self.driver.page_source
                    plain_text = self.extract_plain_text(html_content)

                    transaction_details = self.extract_transaction_details(
                        html_content, plain_text, payment_name
                    )
                    reference_urls = self.extract_reference_urls(html_content)

                    method_data = {
                        "site_name": "1xBet",
                        "payment_method": payment_name,
                        "start_url": before_url,
                        "final_url": self.driver.current_url,
                        "html": html_content,
                        "plain_text": plain_text,
                        "transaction_details": transaction_details,
                        "reference_urls": reference_urls,
                        "fetchtime": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                        "navigation_depth": navigation_depth,
                        "screenshots": {"final": final_screenshot}
                    }

                    if self.should_save_method_data(method_data):
                        valid_count += 1
                        self.save_method_data(method_data)
                    else:
                        # Save a diagnostic JSON even when structured values are absent.
                        diagnostic = dict(method_data)
                        diagnostic["diagnostic_only"] = True
                        self.save_method_data(diagnostic)

                    # Close payment tab if one was opened and return to original tab.
                    if new_handles:
                        self.driver.close()
                        remaining = self.driver.window_handles
                        if remaining:
                            self.driver.switch_to.window(remaining[0])

                except Exception as loop_error:
                    print(f"Iteration error on method {i} ({target_name}): {loop_error}")
                    try:
                        remaining = self.driver.window_handles
                        if remaining:
                            self.driver.switch_to.window(remaining[0])
                    except Exception:
                        pass
                    continue

            print(f"\n{'-'*60}\n🛑 ARCHITECTURE SCRAPING CYCLE FINISHED")
            print(f"Processed: {processed_count} | Valid Targets Saved: {valid_count}\n{'-'*60}")
            
        except Exception as global_err:
            print(f"💥 Global system runtime fatal fault occurred inside Scraper context: {global_err}")
        finally:
            if hasattr(self, 'driver') and self.driver:
                print("Closing webdriver safely...")
                try:
                    self.driver.quit()
                except Exception as e:
                    print(f"Browser session was already closed or disconnected: {e}")


if __name__ == "__main__":
    scraper = SimplifiedPaymentScraper(headless=False)
    scraper.run_scraper_enhanced()




    