import os
import sys
import re
import time
import json
import base64
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
from PIL import Image
from pyzbar.pyzbar import decode

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
    BASE_URL = "https://www.10cric247.com/"


class AutomatedPaymentScraper:
    def __init__(self, headless=True, wait_timeout=15):
        self.wait_timeout = wait_timeout
        self.output_dir = "OUTPUT_10"
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
        chrome_options.add_argument("--incognito")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

        stealth(self.driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL",
                fix_hairline=True)

        self.wait = WebDriverWait(self.driver, self.wait_timeout)

    def perform_login(self):
        """Automated login utilizing credentials from environment variables or manual fallback"""
        email = os.getenv("10CRIC_EMAIL") or os.getenv("10CRIC_USERNAME")
        password = os.getenv("10CRIC_PASSWORD")

        if not email or not password:
            print("⚠️ WARNING: 10CRIC_EMAIL/10CRIC_USERNAME and 10CRIC_PASSWORD are not set in .env!")
            print("Falling back to manual login mode...")
            
            self.driver.get(self.base_url)
            print("\nSTEP 1: Login manually")
            print("STEP 2: Open Deposit/Cashier page manually")
            print("STEP 3: Make sure payment methods are visible")
            print("STEP 4: Then come back to terminal")
            input("\nPress ENTER only after payment methods are visible...")
            return True

        print(f"🚀 Automating login using username/email: {email}")
        self.driver.get(self.base_url)
        self.wait_for_page_load()

        try:
            # 1. Click "Log in" button in the header
            login_btn = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'Log in')]")
            ))
            login_btn.click()
            time.sleep(2)  # Allow modal to transition

            # 2. Enter email
            email_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, "//input[@placeholder='Email' or @type='text']")
            ))
            email_field.clear()
            email_field.send_keys(email)

            # 3. Enter password
            password_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, "//input[@placeholder='********' or @type='password']")
            ))
            password_field.clear()
            password_field.send_keys(password)

            # 4. Click Submit Log in
            submit_btn = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[@type='submit' and contains(text(), 'Log in')]")
            ))
            submit_btn.click()
            print("✓ Login form submitted. Waiting for page redirection...")

            # Wait for login completion by checking if the Log in button goes away, or we see a Deposit button / user element
            self.wait.until(EC.invisibility_of_element_located(
                (By.XPATH, "//button[contains(text(), 'Log in')]")
            ))
            print("✓ Logged in successfully!")
            
            # Navigate to Cashier / Deposit page
            return self.navigate_to_deposit()

        except Exception as e:
            print(f"❌ Automated login/navigation failed: {e}")
            print("Falling back to manual setup. Please log in and navigate to the Deposit page now.")
            input("\nPress ENTER once you have logged in and payment methods are visible...")
            return True

    def navigate_to_deposit(self):
        """Locate and click the Deposit button to bring up payment cashier"""
        print("Opening Deposit/Cashier page...")
        try:
            # Look for Deposit button in header
            deposit_selectors = [
                "//button[contains(translate(text(), 'DEPOSIT', 'deposit'), 'deposit')]",
                "//a[contains(translate(text(), 'DEPOSIT', 'deposit'), 'deposit')]",
                "//a[contains(@href, '/deposit')]",
                "//button[contains(@class, 'deposit')]"
            ]

            deposit_btn = None
            for selector in deposit_selectors:
                try:
                    deposit_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    if deposit_btn:
                        break
                except TimeoutException:
                    continue

            if deposit_btn:
                deposit_btn.click()
                print("✓ Clicked Deposit button.")
                time.sleep(5)
                return True
            else:
                # Direct URL fallback
                deposit_url = urllib.parse.urljoin(self.base_url, "/deposit/")
                print(f"No deposit button found, attempting direct navigation to: {deposit_url}")
                self.driver.get(deposit_url)
                self.wait_for_page_load()
                return True
        except Exception as e:
            print(f"Error navigating to cashier: {e}")
            return False

    def wait_for_page_load(self):
        """Wait for page to be completely loaded"""
        try:
            self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            time.sleep(2)
        except TimeoutException:
            print("Page load timeout - continuing anyway")

    def switch_to_payment_iframe(self):
        """Find and switch to payment iframe if needed, or stay in default context if cashier is visible"""
        self.driver.switch_to.default_content()
        
        # Check if cashier cards are already visible in default context
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, "div[class*='PaymentRouteCardBase_root'], div[class*='PaymentRouteCard']")
            if len(elements) > 0:
                print("✓ Cashier cards visible in default context. No iframe switch needed.")
                return True
        except:
            pass
        
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
                # Use a short timeout of 2 seconds to avoid hanging on non-existent iframes
                short_wait = WebDriverWait(self.driver, 2)
                iframe = short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                self.driver.switch_to.frame(iframe)
                print(f"Switched to payment iframe: {selector}")
                self.wait_for_page_load()
                return True
            except:
                continue

        print("No payment iframe found")
        return False

    def extract_payment_methods(self):
        try:
            payment_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                "[class*='PaymentRouteCardBase_root'], [class*='PaymentRouteCard']"
            )

            print(f"Found {len(payment_elements)} payment methods")

            return payment_elements

        except Exception as e:
            print(f"Error extracting payment methods: {e}")
            return []

    def extract_payment_name(self, element):
        try:
            name_element = element.find_element(
                By.CSS_SELECTOR,
                "[class*='PaymentRouteCard_name']"
            )

            return name_element.text.strip()

        except Exception:
            try:
                return element.text.split("\n")[0].strip()
            except:
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

    def extract_qr_details(self, qr_file="qr.png"):
        try:
            img = Image.open(qr_file)
            results = decode(img)
            print("DECODE RESULTS:", results)

            if not results:
                print("QR NOT DECODED")
                return {}

            qr_data = results[0].data.decode("utf-8")
            print("RAW QR DATA:", qr_data)

            if not qr_data.startswith("upi://"):
                return {
                    "crypto_token": qr_data
                }

            parsed = urllib.parse.urlparse(qr_data)
            params = urllib.parse.parse_qs(parsed.query)

            return {
                "upi_id": params.get("pa", [""])[0],
                "upi_name": params.get("pn", [""])[0],
                "amount": params.get("am", [""])[0],
                "transaction_reference": params.get("tr", [""])[0],
                "currency": params.get("cu", [""])[0],
                "note": params.get("tn", [""])[0]
            }

        except Exception as e:
            print(f"QR decode error: {e}")
            return {}

    def find_any_clickable_button(self):
        """Find specific clickable buttons inside the payment iframe"""
        button_selectors = [
            'button.alerts-ok[onclick="closeForm()"]',
            'button.alerts-ok',
            'div.payment_modal_btn[id="deposit_button"]',
            'div.payment_modal_btn',
            'button[onclick*="closeForm"]',
            'button[onclick*="getForm"]',
            'button.payment_modal_btn[onclick*="getForm"]',
            'button.payment_modal_btn',
            '//button[contains(@class, "alerts-ok")]',
            '//div[contains(@class, "payment_modal_btn")]',
            '//button[contains(@onclick, "closeForm")]',
            '//button[contains(@onclick, "getForm")]',
            '//button[contains(translate(text(), "CONFIRM", "confirm"), "confirm")]',
            '//div[contains(translate(text(), "CONFIRM", "confirm"), "confirm")]',
            '//button[contains(translate(text(), "OK", "ok"), "ok")]',
            '//div[contains(translate(text(), "OK", "ok"), "ok")]',
            '//button[contains(translate(text(), "CONTINUE", "continue"), "continue")]',
            '//div[contains(translate(text(), "CONTINUE", "continue"), "continue")]',
            '//button[contains(translate(text(), "PROCEED", "proceed"), "proceed")]',
            '//div[contains(translate(text(), "PROCEED", "proceed"), "proceed")]',
            '//button[contains(translate(text(), "SUBMIT", "submit"), "submit")]',
            '//div[contains(translate(text(), "SUBMIT", "submit"), "submit")]',
            '//button[contains(translate(text(), "PAY", "pay"), "pay")]',
            '//div[contains(translate(text(), "PAY", "pay"), "pay")]',
            '//button[contains(translate(text(), "DEPOSIT", "deposit"), "deposit")]',
            '//div[contains(translate(text(), "DEPOSIT", "deposit"), "deposit")]',
            '//button[not(contains(translate(text(), "CANCEL", "cancel"), "cancel")) and not(contains(translate(text(), "CLOSE", "close"), "close")) and not(contains(translate(text(), "BACK", "back"), "back")) and not(contains(translate(text(), "EXIT", "exit"), "exit")) and not(contains(@class, "cancel")) and not(contains(@class, "close")) and not(contains(@class, "back"))]',
            '//div[not(contains(translate(text(), "CANCEL", "cancel"), "cancel")) and not(contains(translate(text(), "CLOSE", "close"), "close")) and not(contains(translate(text(), "BACK", "back"), "back")) and not(contains(translate(text(), "EXIT", "exit"), "exit")) and not(contains(@class, "cancel")) and not(contains(@class, "close")) and not(contains(@class, "back")) and (@onclick or contains(@class, "btn") or contains(@class, "button"))]',
        ]
        
        for selector in button_selectors:
            try:
                if selector.startswith("//"):
                    elements = self.driver.find_elements(By.XPATH, selector)
                else:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for el in elements:
                    try:
                        if el.is_displayed() and el.is_enabled():
                            text = el.text.strip() or el.get_attribute('value') or el.get_attribute('onclick') or 'No text'
                            class_name = el.get_attribute('class') or ''
                            tag_name = el.tag_name
                            print(f"Found clickable button: '{text}' | Class: '{class_name}' | Tag: {tag_name} | Selector: {selector}")
                            return el, text
                    except Exception:
                        continue
            except Exception:
                continue
        
        print("No specific payment buttons found in iframe")
        return None, None

    def navigate_with_max_depth(self, max_depth=2):
        """Navigate through pages by clicking buttons with maximum depth limit"""
        current_depth = 0
        clicked_buttons = []
        
        print(f"Starting navigation with max depth: {max_depth}")
        
        while current_depth < max_depth:
            print(f"\n--- Navigation Depth: {current_depth + 1}/{max_depth} ---")
            time.sleep(5)
            
            button, button_text = self.find_any_clickable_button()
            if not button:
                print(f"No more payment buttons found at depth {current_depth + 1} - stopping navigation")
                break
            
            if button_text in clicked_buttons:
                print(f"Button '{button_text}' already clicked - looking for different button")
                try:
                    self.driver.execute_script("arguments[0].style.display = 'none';", button)
                    alt_button, alt_button_text = self.find_any_clickable_button()
                    self.driver.execute_script("arguments[0].style.display = '';", button)
                    
                    if alt_button and alt_button_text != button_text:
                        button, button_text = alt_button, alt_button_text
                    else:
                        print("No alternative button found - stopping navigation")
                        break
                except Exception as e:
                    print(f"Error looking for alternative button: {e}")
                    break
            
            print(f"Attempting to click button: '{button_text}'")
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                time.sleep(2)
                
                clicked = False
                try:
                    button.click()
                    clicked = True
                    print("✓ Clicked button with standard click")
                except Exception:
                    try:
                        self.driver.execute_script("arguments[0].click();", button)
                        clicked = True
                        print("✓ Clicked button with JavaScript click")
                    except Exception:
                        try:
                            ActionChains(self.driver).move_to_element(button).click().perform()
                            clicked = True
                            print("✓ Clicked button with ActionChains")
                        except Exception as e:
                            print(f"⚠️ Failed to click button: {e}")
                
                if not clicked:
                    print("Failed to click button - stopping navigation")
                    break
                
                clicked_buttons.append(button_text)
                current_depth += 1
                
                current_url = self.driver.current_url
                if any(exit_indicator in current_url.lower() for exit_indicator in ['success', 'complete', 'error', 'failed', 'redirect']):
                    print(f"Detected completion page in URL: {current_url}")
                    break
                    
            except Exception as e:
                print(f"❌ Error clicking button at depth {current_depth + 1}: {e}")
                break
        
        print(f"Navigation completed at depth: {current_depth}")
        print(f"Buttons clicked: {clicked_buttons}")
        return current_depth

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
        crypto_token = transaction_details.get('crypto_token', '').strip()

        valid_upi = bool(upi_id)
        valid_bank = any([bank_holder_name, bank_ifsc_code])
        valid_crypto = bool(crypto_token or (crypto_id and crypto_value))
        
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
            
            # Save screenshot directly without minimizing/maximizing window, preventing file corruption
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
        # Remove script, style, head, meta, link, noscript tags to prevent false matches on build IDs/JS variables
        for tag in soup(["script", "style", "head", "meta", "link", "noscript"]):
            tag.decompose()
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

    def wait_for_gateway_load(self, timeout=8):
        """Automatically wait for cashier payment gateway/QR details to render"""
        print("⏳ Waiting automatically for payment gateway / cashier fields to load...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 1. Check if a new tab or window was opened
            if len(self.driver.window_handles) > 1:
                print(f"✓ Detected new tab/window. Switching context...")
                self.driver.switch_to.window(self.driver.window_handles[-1])
                time.sleep(1)
                
            # 2. Check if there are canvas/image QR indicators or target UPI/crypto text
            try:
                # Search default context
                html = self.driver.page_source
                if self.has_payment_details_loaded(html):
                    print("✓ Payment elements detected in default context.")
                    time.sleep(1.0) # Wait for final draw
                    return True
                
                # Check inside iframes
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for idx, frame in enumerate(iframes):
                    try:
                        self.driver.switch_to.default_content()
                        self.driver.switch_to.frame(frame)
                        frame_html = self.driver.page_source
                        if self.has_payment_details_loaded(frame_html):
                            print(f"✓ Payment elements detected in iframe {idx}.")
                            time.sleep(1.0)
                            return True
                    except Exception:
                        continue
                
                # Return context to top window/frame if nested
                self.driver.switch_to.default_content()
            except Exception as e:
                print(f"Warning during loading check: {e}")

            time.sleep(0.5)
            
        print("⚠️ Reached loading limit - continuing with extraction on current state.")
        return False

    def has_payment_details_loaded(self, html):
        """Check if HTML contains typical payment details, inputs, forms, or indicators that the gateway has loaded"""
        soup = BeautifulSoup(html, "html.parser")
        
        # Check if there are active input fields or select dropdowns (indicates form loaded)
        inputs = soup.find_all("input")
        visible_inputs = [inp for inp in inputs if inp.get("type") != "hidden"]
        if len(visible_inputs) > 0 or len(soup.find_all("select")) > 0 or len(soup.find_all("form")) > 0:
            return True
            
        # Check canvases or SVG elements (often used for QR rendering)
        if len(soup.find_all("canvas")) > 0 or len(soup.find_all("svg")) > 0:
            return True
            
        # Check images with base64 data src (typical dynamically generated QR)
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src.startswith("data:image") or "qr" in src.lower():
                return True
                
        # Check plain text for UPI VPA addresses
        plain_text = self.extract_plain_text(html)
        upi_matches = re.findall(r'[A-Za-z0-9._-]+@[A-Za-z0-9._-]+', plain_text)
        upi_matches = [x for x in upi_matches if not x.lower().endswith(".com")]
        if len(upi_matches) > 0:
            return True
            
        # Check for common banking/cashier keywords
        if any(term in plain_text.upper() for term in ["BANK", "ACCOUNT", "PAYEE", "HOLDER", "AMOUNT", "DEPOSIT", "SUBMIT"]):
            return True
            
        # Check for Crypto keywords
        if any(coin in plain_text for coin in ["BTC", "ETH", "LTC", "USDT"]):
            return True
            
        return False

    def submit_deposit_amount_if_needed(self):
        """Enter a default amount and submit the deposit form if we are on the amount selection screen"""
        amount = os.getenv("10CRIC_DEPOSIT_AMOUNT", "500")
        print(f"💰 Checking for deposit amount entry screen (entering: {amount})...")
        time.sleep(2) # Wait a bit for the card to expand / load inputs
        
        try:
            # Check for amount input field
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
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            amount_input = el
                            break
                    if amount_input:
                        break
                except:
                    continue
            
            if amount_input:
                print("✓ Found amount input field. Clearing and typing...")
                amount_input.clear()
                amount_input.send_keys(amount)
                time.sleep(1)
            else:
                # Let's check if there are amount preset buttons (e.g. 500, 1000, 2000 INR)
                preset_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), '500') or contains(text(), '1000') or contains(text(), '2000')]")
                for btn in preset_buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        print(f"✓ Found preset amount button: '{btn.text}'. Clicking it...")
                        btn.click()
                        time.sleep(1)
                        break

            # Now find and click the Proceed/Deposit/Next submit button
            submit_btn = None
            submit_selectors = [
                "button[type='submit']",
                "button.alerts-ok",
                "div.payment_modal_btn[id='deposit_button']",
                "div.payment_modal_btn",
                "button.payment_modal_btn",
                "//button[contains(translate(text(), 'DEPOSIT', 'deposit'), 'deposit')]",
                "//button[contains(translate(text(), 'PAY', 'pay'), 'pay')]",
                "//button[contains(translate(text(), 'PROCEED', 'proceed'), 'proceed')]",
                "//button[contains(translate(text(), 'CONFIRM', 'confirm'), 'confirm')]",
                "//div[contains(translate(text(), 'DEPOSIT', 'deposit'), 'deposit')]",
                "//div[contains(translate(text(), 'PAY', 'pay'), 'pay')]",
                "//div[contains(translate(text(), 'PROCEED', 'proceed'), 'proceed')]",
                "//div[contains(translate(text(), 'CONFIRM', 'confirm'), 'confirm')]"
            ]
            
            for selector in submit_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            submit_btn = el
                            break
                    if submit_btn:
                        break
                except:
                    continue
            
            if submit_btn:
                text = submit_btn.text.strip() or submit_btn.get_attribute("value") or "Submit"
                print(f"✓ Found submit button: '{text}'. Clicking it...")
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", submit_btn)
                time.sleep(1)
                try:
                    submit_btn.click()
                except:
                    self.driver.execute_script("arguments[0].click();", submit_btn)
                time.sleep(3)
                return True
            else:
                print("⚠️ No submit button found for amount. It might be direct redirection.")
                return False
        except Exception as e:
            print(f"Error handling amount submission: {e}")
            return False

    def extract_context_data(self, i):
        """Extract html, plain text, and transaction details from the current driver context"""
        html = self.driver.page_source
        plain = self.extract_plain_text(html)
        details = {}
        
        # Check for image QR
        soup = BeautifulSoup(html, "html.parser")
        imgs = soup.find_all("img")
        for img_idx, img in enumerate(imgs):
            src = img.get("src", "")
            if src.startswith("data:image"):
                try:
                    _, encoded = src.split(",", 1)
                    temp_file = f"qr_method_{i}_{img_idx}.png"
                    with open(temp_file, "wb") as f:
                        f.write(base64.b64decode(encoded))
                    qr_details = self.extract_qr_details(temp_file)
                    if qr_details:
                        details = qr_details
                        break
                except Exception as e:
                    print(f"Error decoding base64 image: {e}")
        
        # Check for canvas QR
        canvas_elements = self.driver.find_elements(By.TAG_NAME, "canvas")
        if canvas_elements and not details:
            try:
                canvas = canvas_elements[0]
                canvas_base64 = self.driver.execute_script(
                    "return arguments[0].toDataURL('image/png');", canvas
                )
                _, encoded = canvas_base64.split(",", 1)
                temp_canvas_file = f"canvas_qr_method_{i}.png"
                with open(temp_canvas_file, "wb") as f:
                    f.write(base64.b64decode(encoded))
                qr_details = self.extract_qr_details(temp_canvas_file)
                if qr_details:
                    details = qr_details
            except Exception as e:
                print(f"Error checking canvas QR: {e}")
        
        # Check for UPI matches in text
        upi_matches = re.findall(r'[A-Za-z0-9._-]+@[A-Za-z0-9._-]+', plain)
        upi_matches = [x for x in upi_matches if not x.lower().endswith(".com")]
        if upi_matches and not details:
            details = {"upi_id": upi_matches[0]}
            
        return html, plain, details

    def find_best_context_and_extract(self, i):
        """
        Check if there are any payment/cashier iframes. 
        If found, switch to and scrape them, otherwise scrape the current page.
        """
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        iframe_found = len(iframes) > 0
        
        # Look for payment iframe specifically or default to first iframe if present
        payment_iframe = None
        for frame in iframes:
            try:
                if not frame.is_displayed():
                    continue
                size = frame.size
                if size["width"] < 100 or size["height"] < 100:
                    continue
                
                src = frame.get_attribute("src") or ""
                id_attr = frame.get_attribute("id") or ""
                name = frame.get_attribute("name") or ""
                if any(term in src.lower() or term in id_attr.lower() or term in name.lower() for term in ["payment", "deposit", "paysystem", "cashier", "checkout", "gateway"]):
                    payment_iframe = frame
                    break
            except:
                continue
                
        # If no specific payment iframe is identified, use a large visible frame as fallback
        if not payment_iframe:
            for frame in iframes:
                try:
                    if frame.is_displayed():
                        size = frame.size
                        if size["width"] > 300 and size["height"] > 300:
                            payment_iframe = frame
                            print(f" -> Found large visible fallback iframe: size={size['width']}x{size['height']}")
                            break
                except:
                    continue
            
        if iframe_found and payment_iframe:
            print("✓ Payment iframe found. Scraping iframe...")
            try:
                self.driver.switch_to.frame(payment_iframe)
                # Check for nested iframes inside this iframe
                nested = self.driver.find_elements(By.TAG_NAME, "iframe")
                if nested:
                    try:
                        self.driver.switch_to.frame(nested[0])
                        print(" -> Scraping nested payment iframe...")
                    except:
                        pass
                html_content, plain_text, transaction_details = self.extract_context_data(i)
            except Exception as e:
                print(f"Error scraping iframe: {e}")
                self.driver.switch_to.default_content()
                html_content, plain_text, transaction_details = self.extract_context_data(i)
        else:
            print("No payment iframe found. Scraping current page context...")
            html_content, plain_text, transaction_details = self.extract_context_data(i)
            
        self.driver.switch_to.default_content()
        return html_content, plain_text, transaction_details, None, None

    def return_to_cashier(self):
        """Return to the payment methods list page without reloading the entire site"""
        try:
            print("🔙 Returning to cashier list...")
            if len(self.driver.window_handles) > 1:
                # Close the gateway tab and switch back to cashier tab
                print("Closing payment gateway tab/window...")
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
                time.sleep(2)
            else:
                self.driver.switch_to.default_content()
                
                # Check if cashier cards are already visible in default context
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, "div[class*='PaymentRouteCardBase_root'], div[class*='PaymentRouteCard']")
                    if len(elements) > 0:
                        print("✓ Cashier cards visible in default context. No reopen needed.")
                        return True
                except:
                    pass
                
                # Close cashier modal to reset state
                close_selectors = [
                    "button[aria-label='Close']",
                    "button.close",
                    ".modal-close",
                    ".close-dialog-btn",
                    "//button[text()='X']"
                ]
                for sel in close_selectors:
                    try:
                        if sel.startswith("//"):
                            btn = self.driver.find_element(By.XPATH, sel)
                        else:
                            btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                        if btn.is_displayed():
                            btn.click()
                            print(f"Closed cashier modal using selector: {sel}")
                            time.sleep(2)
                            break
                    except:
                        continue
                
                # Reopen cashier modal
                self.navigate_to_deposit()
                time.sleep(3)
                
            self.switch_to_payment_iframe()
            return True
        except Exception as e:
            print(f"Error returning to cashier: {e}")
            return False

    def run_scraper_enhanced(self, range_start=1, range_end=None):
        """Main scraper orchestration block outputting directly to JSON storage files"""
        try:
            print("🚀 Starting Automated Payment Scraper with Local JSON File Storage")
            print(f"Output directory: {self.output_dir}")
            print(f"Multimedia directory: {self.multimedia_dir}")
            print(f"Target URL: {self.base_url}")
            
            processed_count = 0
            valid_count = 0
            
            print("Starting automated login...")
            self.perform_login()
            self.wait_for_page_load()

            print("Current URL:", self.driver.current_url)

            # Switch to payment iframe to extract payment options
            self.switch_to_payment_iframe()
            payment_elements = self.extract_payment_methods()
            print(f"Found {len(payment_elements)} payment methods")

            if not payment_elements:
                print("\n❌ DEBUG INFO: No payment methods found!")
                print(f"Current URL: {self.driver.current_url}")
                print(f"Page Source length: {len(self.driver.page_source)}")
                
                # Check all visible iframes
                self.driver.switch_to.default_content()
                all_iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                print(f"Total iframes on page: {len(all_iframes)}")
                for idx, frame in enumerate(all_iframes):
                    name = frame.get_attribute("name") or "No name"
                    id_attr = frame.get_attribute("id") or "No id"
                    src = frame.get_attribute("src") or "No src"
                    print(f" -> Iframe {idx}: ID='{id_attr}', Name='{name}', Src='{src[:150]}'")
                
                # Take screenshot for diagnostic purposes
                diag_screenshot = os.path.join(self.multimedia_dir, "diagnostic_empty_methods.png")
                self.driver.save_screenshot(diag_screenshot)
                print(f"Saved diagnostic screenshot to: {diag_screenshot}")
                return

            max_methods_to_process = len(payment_elements)
            r_start = max(1, range_start)
            r_end = min(max_methods_to_process, range_end) if range_end else max_methods_to_process

            print(f"⚠️ RUN TIMELINE: Processing routes from indices {r_start} to {r_end}.")
            
            for i in range(r_start - 1, r_end):
                try:
                    processed_count += 1
                    
                    # If navigating multiple options, return to base/cashier setup
                    if processed_count > 1:
                        if not self.return_to_cashier():
                            print(f"Failed to return to cashier for method {i+1}. Attempting fallback base navigation...")
                            self.driver.switch_to.default_content()
                            if not self.navigate_back_to_base() or not self.navigate_to_deposit() or not self.switch_to_payment_iframe():
                                print(f"Fallback navigation failed for method {i+1}")
                                continue
                        
                    try:
                        payment_elements = self.extract_payment_methods()
                        element = payment_elements[i]
                    except:
                        print("⚠️ Element load failed. Refreshing page...")
                        self.driver.refresh()
                        time.sleep(5)
                        self.navigate_to_deposit()
                        self.switch_to_payment_iframe()
                        payment_elements = self.extract_payment_methods()
                        try:
                            element = payment_elements[i]
                        except Exception as e:
                            print(f"Error re-fetching element after refresh: {e}")
                            continue

                    payment_name = self.extract_payment_name(element)
                    
                    print(f"\n{'='*60}")
                    print(f"Processing method {i+1}/{max_methods_to_process}: {payment_name}")
                    print(f"{'='*60}")
                    
                    old_tabs = len(self.driver.window_handles)

                    if not self.click_payment_method(element):
                        print(f"Failed to click payment method: {payment_name}")
                        continue

                    # Enter deposit amount and submit if an input field is shown
                    self.submit_deposit_amount_if_needed()

                    time.sleep(3)

                    new_tabs = len(self.driver.window_handles)

                    if new_tabs > old_tabs:
                        self.driver.switch_to.window(
                            self.driver.window_handles[-1]
                        )
                    else:
                        print("No new tab opened")

                    # AUTOMATED WAIT FOR THE PAYMENT GATEWAY / QR DETAILS TO LOAD
                    self.wait_for_gateway_load()

                    print("CURRENT URL:", self.driver.current_url)

                    # Automatically find the best iframe/context and extract details
                    html_content, plain_text, transaction_details, canvas_qr, image_qr = self.find_best_context_and_extract(i+1)

                    # Capture screenshot from the current active context
                    final_screenshot = self.take_screenshot_enhanced(payment_name, "_final", self.multimedia_dir)

                    print("\nTRANSACTION DETAILS:", transaction_details)
                    
                    reference_urls = self.extract_reference_urls(html_content)
                    
                    method_data = {
                        "site_name": "10Cric",
                        "payment_method": payment_name,
                        "html": html_content,
                        "plain_text": plain_text,
                        "transaction_details": transaction_details,
                        "reference_urls": reference_urls,
                        "fetchtime": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                        "navigation_depth": 0,
                        "screenshots": {
                            "final": final_screenshot
                        }
                    }
                    
                    if self.should_save_method_data(method_data):
                        valid_count += 1
                        
                    # Always save the scraped method data to disk to guarantee files are created
                    self.save_method_data(method_data)
                            
                except Exception as loop_error:
                    print(f"❌ Internal iteration handling error on position index {i}: {loop_error}")
                    continue
                    
            print(f"\n{'-'*60}\n🛑 ARCHITECTURE SCRAPING CYCLE FINISHED")
            print(f"Processed: {processed_count} | Valid Targets Saved: {valid_count}\n{'-'*60}")
            
        except Exception as global_err:
            print(f"💥 Global system runtime fatal fault occurred inside Scraper context: {global_err}")
        finally:
            if hasattr(self, 'driver') and self.driver:
                print("Shutting down headless webdriver context safely...")
                self.driver.quit()


if __name__ == "__main__":
    # Example usage: Run scraper. By default it runs with headless=False to facilitate login confirmation
    # or manual troubleshooting if credentials are not configured.
    scraper = AutomatedPaymentScraper(headless=False)
    
    # Run the scraper for all payment methods automatically
    scraper.run_scraper_enhanced()
