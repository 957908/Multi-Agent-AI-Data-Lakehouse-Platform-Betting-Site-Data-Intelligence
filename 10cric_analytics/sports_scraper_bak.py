import os
import re
import time
import json
from datetime import datetime, timezone
import urllib.parse
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from PIL import Image
from pyzbar.pyzbar import decode
import urllib.parse

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


class SimplifiedPaymentScraper:
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
        try:
            payment_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                "[class*='PaymentRouteCardBase_root']"
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

            qr_data = results[0].data.decode("utf-8")

            print("RAW QR DATA:", qr_data)

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
        
        valid_upi = bool(upi_id)
        valid_bank = any([bank_holder_name, bank_ifsc_code])
        crypto_token = transaction_details.get('crypto_token', '').strip()

        valid_crypto = bool(
        crypto_token or
        (crypto_id and crypto_value)
        )
        
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

            payment_elements = self.extract_payment_methods()

            print(f"Found {len(payment_elements)} payment methods")

            if not payment_elements:
                print("No payment methods found!")
                return

            max_methods_to_process = 103
            methods_to_process = min(len(payment_elements), max_methods_to_process)

            print(f"⚠️ RUN TIMELINE: Processing up to {methods_to_process} routes.")
            
            for i in range(6,7):
                try:
                    processed_count += 1
                    
                  #  if i > 1:
                   #     if not self.navigate_back_to_base():
                    #        print(f"Failed to navigate back for method {i}")
                     #       continue
                        #if not self.switch_to_payment_iframe():
                          #  print(f"Failed to switch to iframe for method {i}")
                           # continue
                        
                       # payment_elements = self.extract_payment_methods()
                       # if i > len(payment_elements):
                        #    print(f"Method {i} not available after list update")
                         #   continue
                    
                    element = payment_elements[i-1]
                    payment_name = self.extract_payment_name(element)
                    
                    print(f"\n{'='*60}")
                    print(f"Processing method {i}/{methods_to_process}: {payment_name}")
                    print(f"{'='*60}")
                    
                    if not self.click_payment_method(element):
                        print(f"Failed to click payment method: {payment_name}")
                        continue

                    print("PAUSED AFTER PAYMENT METHOD CLICK")
                    input("When QR page is visible, press ENTER...")

                    print("Tabs:", len(self.driver.window_handles))

                    print("Tabs:", len(self.driver.window_handles))

                    self.driver.switch_to.window(self.driver.window_handles[-1])

                    print("CURRENT URL:", self.driver.current_url)

                    iframes = self.driver.find_elements(By.TAG_NAME, "iframe")

                    print("IFRAMES FOUND:", len(iframes))



                    for idx, frame in enumerate(iframes):
                        try:
                            print(f"\n===== IFRAME {idx} =====")

                            self.driver.switch_to.default_content()
                            self.driver.switch_to.frame(frame)

                            print("FRAME URL:", self.driver.current_url)

                            frame_html = self.driver.page_source

                            print("FRAME HTML LENGTH:", len(frame_html))

                            if "BTC" in frame_html:
                                print("BTC FOUND")

                            if "ETH" in frame_html:
                                print("ETH FOUND")

                            if "LTC" in frame_html:
                                print("LTC FOUND")

                            if "USDT" in frame_html:
                                print("USDT FOUND")

                            elements = self.driver.find_elements(By.XPATH, "//*")

                           

                            for e in elements:
                                try:
                                    txt = e.text.strip()

                                    if txt in ["BTC", "ETH", "LTC", "USDT"]:
                                        print("COIN BUTTON:", txt)

                                except:
                                    pass

                                    with open(f"iframe_{idx}.html", "w", encoding="utf-8") as f:
                                        f.write(frame_html)

                                        print(frame_html[:500])

                        except Exception as e:
                            print("FRAME ERROR:", e)


                    html_content = self.driver.page_source

                    print("CURRENT URL:", self.driver.current_url)
                    print("HTML TYPE:", type(html_content))
                    print("HTML LENGTH:", len(html_content) if html_content else 0)

                    from bs4 import BeautifulSoup
                    import base64

                    soup = BeautifulSoup(html_content, "html.parser")


                    transaction_details = {}

                    imgs = soup.find_all("img")

                    print("TOTAL IMAGES:", len(imgs))

                    canvases = soup.find_all("canvas")
                    print("TOTAL CANVAS:", len(canvases))

                    svgs = soup.find_all("svg")
                    print("TOTAL SVG:", len(svgs))

                    for canvas in canvases:
                        print("CANVAS:", canvas)

                    for img in imgs:
                        src = img.get("src", "")

                        print("IMG SRC:", src[:200])

                        if src.startswith("data:image"):
                            _, encoded = src.split(",", 1)

                            qr_file = f"qr_method_{i}.png"

                            with open(qr_file, "wb") as f:
                                f.write(base64.b64decode(encoded))

                            print(f"✅ QR saved as {qr_file}")

                            qr_details = self.extract_qr_details(qr_file)

                            print("\nQR DETAILS:")
                            print(qr_details)

                            transaction_details = qr_details

                            break

                    #return

                    navigation_depth = 0

                    print("Waiting 5 seconds for final page to fully load...")
                    time.sleep(5)
                    
                    final_screenshot = self.take_screenshot_enhanced(payment_name, "_final", self.multimedia_dir)
                    html_content = self.driver.page_source
                    plain_text = self.extract_plain_text(html_content)


                    import re

                    upi_matches = re.findall(
                    r'[A-Za-z0-9._-]+@[A-Za-z0-9._-]+',
                    plain_text
                    )

                    print("UPI FOUND:", upi_matches)

                    upi_matches = [
                    x for x in upi_matches
                    if not x.lower().endswith(".com")
                    ]

                    print("FILTERED UPI:", upi_matches)

                    if upi_matches and not transaction_details:
                        transaction_details = {
                        "upi_id": upi_matches[0]
                    }

# Keep QR details
                    print("\nTRANSACTION DETAILS:")
                    print(transaction_details)
                    print("\nCURRENT URL:")
                    print(self.driver.current_url)
                    
                    canvas_elements = self.driver.find_elements(By.TAG_NAME, "canvas")

                    print("SELENIUM CANVAS COUNT:", len(canvas_elements))

                    if canvas_elements:

                        canvas = canvas_elements[0]

                        canvas_base64 = self.driver.execute_script("""
                        return arguments[0].toDataURL('image/png');
                        """, canvas)

                        _, encoded = canvas_base64.split(",", 1)

                        canvas_file = f"canvas_qr_method_{i}.png"

                        with open(canvas_file, "wb") as f:
                            f.write(base64.b64decode(encoded))

                        print(f"✅ Canvas QR saved: {canvas_file}")

                        qr_details = self.extract_qr_details(canvas_file)

                        print("CANVAS QR DETAILS:")
                        print(qr_details)

                        if qr_details:
                            transaction_details = qr_details

                    reference_urls = self.extract_reference_urls(html_content)
                    
                    # Target single data structure matching your local formatting schema
                    method_data = {
                        "site_name": "10Cric",
                        "payment_method": payment_name,
                        "html": html_content,
                        "plain_text": plain_text,
                        "transaction_details": transaction_details,
                        "reference_urls": reference_urls,
                        "fetchtime": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                        "navigation_depth": navigation_depth,
                        "screenshots": {
                            "final": final_screenshot
                        }
                    }
                    
                    # Validate targets strictly locally; write files directly out to disk
                    if self.should_save_method_data(method_data):
                        valid_count += 1
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
    scraper = SimplifiedPaymentScraper(headless=False)
    scraper.run_scraper_enhanced()