# =====================================================================
# Python Web Scraping Tutorial & Template
# =====================================================================
# This script is a step-by-step tutorial designed to teach you how to write
# modern, robust web scrapers for dynamic websites (like sports, betting, or
# dashboard portals) using Python, Playwright, and BeautifulSoup.
#
# Prerequisite libraries (run in your terminal to install):
#   pip install playwright beautifulsoup4
#   playwright install
# =====================================================================

import asyncio  # Used to run code asynchronously (non-blocking wait operations)
import os       # Used for interacting with the operating system (creating folders, check file paths)
import re       # Regular Expressions library, used to find patterns (like UPI IDs, crypto keys)
import json     # JSON library, used to format and save extracted data as .json files
from datetime import datetime  # Used to mark timestamps of when we scraped the data
from bs4 import BeautifulSoup  # Used to parse HTML and extract text easily
from playwright.async_api import async_playwright  # Modern browser automation library

# ---------------------------------------------------------------------
# 1. SETUP LOGGING DIRECTORIES
# ---------------------------------------------------------------------
# We create folders to store our results so they are organized automatically.
# 'screenshots' stores visual images, 'html' stores raw code, 'json' stores data.
OUTPUT_DIR = "OUTPUT_TUTORIAL"
os.makedirs(f"{OUTPUT_DIR}/screenshots", exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/html", exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/json", exist_ok=True)

# ---------------------------------------------------------------------
# 2. PATTERN MATCHING / REGULAR EXPRESSIONS (REGEX)
# ---------------------------------------------------------------------
# Regex is used to scan unstructured text and extract specific targets:
# - UPI_PATTERN: Matches standard virtual payment addresses (e.g., example@upi, user@ybl).
# - crypto_pattern: Matches bitcoin (bc1/1/3) or ethereum (0x) blockchain wallet addresses.
# - ifsc_pattern: Matches standard Indian Bank IFSC codes (4 capital letters + 0 + 6 alphanumeric).
UPI_PATTERN = re.compile(r"[a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+")
CRYPTO_PATTERN = re.compile(r"\b(0x[a-fA-F0-9]{40}|[13][a-km-zA-HJ-NP-Z1-9]{26,33}|bc1[a-z0-9]{39,59})\b")
IFSC_PATTERN = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")


# ---------------------------------------------------------------------
# 3. HELPER FUNCTIONS FOR DATA EXTRACTION
# ---------------------------------------------------------------------

def extract_upi_id(text: str) -> str:
    """
    Scans the given raw text and extracts the first matching UPI ID.
    If no match is found, returns an empty string.
    """
    match = UPI_PATTERN.search(text)
    return match.group().strip() if match else ""


def extract_crypto_address(text: str) -> str:
    """
    Scans raw text to detect Ethereum or Bitcoin public wallet addresses.
    Returns the address if found, otherwise returns an empty string.
    """
    match = CRYPTO_PATTERN.search(text)
    return match.group().strip() if match else ""


def extract_bank_details(text: str, soup: BeautifulSoup) -> dict:
    """
    Extracts bank account details by searching for IFSC code and common banking terms.
    We look for numbers representing bank accounts, and labels indicating Holder names.
    """
    details = {
        "ifsc_code": "",
        "account_number": "",
        "holder_name": ""
    }
    
    # 1. Search for IFSC Code using our regex pattern
    ifsc_match = IFSC_PATTERN.search(text)
    if ifsc_match:
        details["ifsc_code"] = ifsc_match.group()

    # 2. Search for bank account number (usually 9 to 18 digits in sequence)
    account_number_match = re.search(r"\b\d{9,18}\b", text)
    if account_number_match:
        details["account_number"] = account_number_match.group()

    # 3. Search for beneficiary or holder name by scanning labels in the HTML
    # We find tags containing words like "holder", "beneficiary", or "name"
    for element in soup.find_all(["span", "div", "td", "label", "p"]):
        el_text = element.get_text().strip()
        # If the label contains holder/beneficiary keywords, the next element might contain the actual name
        if re.search(r"(holder|beneficiary|payee|name)\b", el_text, re.IGNORECASE):
            # Attempt to extract next sibling or child text
            sibling = element.find_next()
            if sibling:
                details["holder_name"] = sibling.get_text().strip()
                break # Stop searching after finding the first candidate name

    return details


# ---------------------------------------------------------------------
# 4. CORE SCRA-PER CLASS
# ---------------------------------------------------------------------

class EducationalWebScraper:
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.output_path = OUTPUT_DIR

    async def save_scraped_results(self, page, method_name: str, extracted_data: dict):
        """
        Saves three files for debugging and historical verification:
        1. PNG Screenshot of the page layout.
        2. Raw HTML source code of the scraped screen.
        3. Structured JSON file containing parsed details.
        """
        # Create a safe name by replacing slashes and spaces with underscores
        safe_filename = re.sub(r"[^\w\-.]", "_", method_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # A. Save Screenshot
        screenshot_path = f"{self.output_path}/screenshots/{safe_filename}_{timestamp}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"[SAVED] Screenshot: {screenshot_path}")

        # B. Save Raw HTML
        html_path = f"{self.output_path}/html/{safe_filename}_{timestamp}.html"
        page_html = await page.content()
        with open(html_path, "w", encoding="utf-8") as file:
            file.write(page_html)
        print(f"[SAVED] Raw HTML: {html_path}")

        # C. Save Structured JSON Data
        json_path = f"{self.output_path}/json/{safe_filename}_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as file:
            json.dump(extracted_data, file, indent=4, ensure_ascii=False)
        print(f"[SAVED] JSON Data: {json_path}")

    async def run_pipeline(self):
        """
        This is the main asynchronous execution sequence.
        It starts Playwright, launches Chrome, manages pages, performs manual login
        bypass, and extracts payment details from the target page.
        """
        # Step A: Launch Playwright engine
        async with async_playwright() as playwright_engine:
            
            print("[INFO] Launching Chromium browser (headless=False)...")
            # headless=False shows the browser GUI. This lets you see what the scraper is doing.
            browser = await playwright_engine.chromium.launch(headless=False)
            
            # Create an isolated browser context (like an incognito session)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800} # Set a fixed window resolution
            )
            
            # Open a new browser tab
            page = await context.new_page()
            
            print(f"[INFO] Navigating browser to: {self.target_url}")
            await page.goto(self.target_url)

            # -------------------------------------------------------------
            # STEP B: MANUAL LOGIN BYPASS / CAPTCHA SOLVER
            # -------------------------------------------------------------
            # Automating logins is highly fragile due to captchas, security questions, or changing layouts.
            # The most robust student approach is to let the script navigate, wait, and allow you
            # to log in manually, then press ENTER in your command line terminal to resume automation.
            print("\n" + "="*70)
            print("  MANUAL ACTION REQUIRED IN OPEN BROWSER:")
            print("  1. Please login manually if prompt is displayed.")
            print("  2. Complete any required security checks or CAPTCHAs.")
            print("  3. Navigate directly to the Deposit / Cashier screen.")
            print("  4. Ensure payment options or transaction data are displayed.")
            print("="*70 + "\n")
            
            # Wait for user confirmation in the console terminal
            input("Once you are ready and the screen is visible, press ENTER here to start scraping...")

            # -------------------------------------------------------------
            # STEP C: IFRAME RESOLUTION
            # -------------------------------------------------------------
            # Many betting portals load their cashier screens inside an <iframe> (an HTML document inside another).
            # If the scraper looks for buttons or text inside the outer page, it won't find them.
            # We must detect iframes and target them directly.
            
            print("[INFO] Searching for cashier or payment iframes on the current page...")
            active_frame = page  # By default, we search the main page
            
            # Query all frames currently active on the page
            all_frames = page.frames
            print(f"[INFO] Total frames found on page: {len(all_frames)}")
            
            # Look for frames containing words like 'payment', 'cashier', 'deposit', or 'paysystem' in their name/url
            for frame in all_frames:
                url_lower = frame.url.lower()
                name_lower = frame.name.lower() if frame.name else ""
                
                if "payment" in url_lower or "cashier" in url_lower or "deposit" in url_lower or "paysystem" in url_lower:
                    print(f"[SUCCESS] Switched context to payment iframe: {frame.url} (Name: {frame.name})")
                    active_frame = frame  # Change our extraction target to the matching iframe
                    break

            # -------------------------------------------------------------
            # STEP D: DYNAMIC ELEMENT SELECTION & WAIT STATE
            # -------------------------------------------------------------
            # Modern SPA (Single Page Applications) take time to load elements.
            # Instead of simple `time.sleep()`, we use `wait_for_selector()` to wait only
            # until our target elements are dynamically drawn in the DOM.
            
            # Below are common CSS class patterns used for payment method cards/buttons
            selector_patterns = [
                ".payment-cell", 
                ".payment_item", 
                "[data-method]", 
                "button.payment-method",
                ".payment-cell--recommended",
                "a.payment_item"
            ]
            
            selected_selector = None
            for pattern in selector_patterns:
                try:
                    # Wait up to 3 seconds for the selector to appear in the active frame
                    await active_frame.wait_for_selector(pattern, timeout=3000)
                    selected_selector = pattern
                    print(f"[SUCCESS] Found active target elements matching selector: '{pattern}'")
                    break
                except Exception:
                    # If this selector pattern is not found, loop and try the next one
                    continue

            if not selected_selector:
                print("[WARNING] Could not find any standard payment selectors. Scraping the base page instead...")
            
            # -------------------------------------------------------------
            # STEP E: EXTRACTION LOOP
            # -------------------------------------------------------------
            # If we found individual payment elements, we loop through them to read their contents.
            # If not, we fall back to reading the entire page's visible text.
            extracted_methods = []
            
            if selected_selector:
                # Find all elements matching the chosen selector
                elements = await active_frame.locator(selected_selector).all()
                total_elements = len(elements)
                print(f"[INFO] Discovered {total_elements} payment methods to analyze.")

                for index, element in enumerate(elements):
                    try:
                        # Extract the inner text of this payment card
                        element_text = await element.inner_text()
                        
                        # Replace line breaks with spaces for clean parsing
                        clean_text = " ".join(element_text.split())
                        
                        # Get a readable name (e.g. the first few words of the element)
                        method_name = clean_text[:30].strip() or f"Method_{index+1}"
                        
                        print(f"[{index+1}/{total_elements}] Extracting details for: {method_name}")
                        
                        # Get the complete outer HTML of this specific element
                        element_html = await element.inner_html()
                        soup = BeautifulSoup(element_html, "html.parser")
                        
                        # Parse out data properties using our helper functions
                        upi_id = extract_upi_id(clean_text)
                        crypto_address = extract_crypto_address(clean_text)
                        bank_info = extract_bank_details(clean_text, soup)
                        
                        method_data = {
                            "payment_method": method_name,
                            "raw_text": clean_text,
                            "extracted_upi": upi_id,
                            "extracted_crypto": crypto_address,
                            "extracted_bank": bank_info,
                            "scraped_at": datetime.now().isoformat()
                        }
                        
                        extracted_methods.append(method_data)
                        
                        # Optional: If you want to click the payment card to open a deposit modal
                        # (uncomment below to test on sites where detailed info requires clicking)
                        # await element.click()
                        # await page.wait_for_timeout(2000) # wait 2 seconds for modal
                        # ... do modal extraction here ...
                        
                    except Exception as element_error:
                        print(f"[ERROR] Failed to process method {index+1}: {element_error}")
            else:
                # Fallback: scrape the entire page's text if no individual elements were identified
                print("[INFO] Fallback: Scraping visible text from the entire active screen...")
                page_text = await active_frame.locator("body").inner_text()
                page_html = await active_frame.content()
                soup = BeautifulSoup(page_html, "html.parser")
                
                upi_id = extract_upi_id(page_text)
                crypto_address = extract_crypto_address(page_text)
                bank_info = extract_bank_details(page_text, soup)
                
                method_data = {
                    "payment_method": "Full_Page_Fallback",
                    "raw_text": " ".join(page_text.split())[:1000], # Save first 1000 chars of page text
                    "extracted_upi": upi_id,
                    "extracted_crypto": crypto_address,
                    "extracted_bank": bank_info,
                    "scraped_at": datetime.now().isoformat()
                }
                extracted_methods.append(method_data)

            # -------------------------------------------------------------
            # STEP F: WRITE OUTPUTS
            # -------------------------------------------------------------
            # Combine all results into a single dataset and save to file
            final_report = {
                "site_scraped": self.target_url,
                "timestamp": datetime.now().isoformat(),
                "extracted_count": len(extracted_methods),
                "methods": extracted_methods
            }
            
            # Save our report alongside screenshot and source code
            await self.save_scraped_results(page, "Scraping_Session_Summary", final_report)
            print("\n" + "="*70)
            print(f"[COMPLETED] Scraping session ended. Ingested {len(extracted_methods)} records.")
            print(f"            Results written to the directory: '{OUTPUT_DIR}/'")
            print("="*70 + "\n")

            # Clean close: Shut down browser and release system resources
            print("[INFO] Closing browser...")
            await browser.close()


# ---------------------------------------------------------------------
# 5. ENTRY POINT
# ---------------------------------------------------------------------
if __name__ == "__main__":
    # Choose a target URL to test.
    # Note: For educational purposes, you can replace this with a local page,
    # a sandboxed test site, or the URL of one of the project components.
    TEST_URL = "https://www.wikipedia.org"  # Replace with target URL when ready to scrape
    
    print(f"Starting Scraper pipeline targeting: {TEST_URL}")
    scraper_object = EducationalWebScraper(target_url=TEST_URL)
    
    # Run the main async routine using asyncio event loop
    asyncio.run(scraper_object.run_pipeline())
