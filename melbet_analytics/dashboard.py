import config
import re
from playwright.async_api import Page
from config import TIMEOUT, logger

async def scrape_profile_info(page: Page) -> dict:
    """Scrapes user account info from the profile/dashboard page."""
    logger.info("Scraping user profile details...")
    
    profile_data = {
        "user_id": "UNKNOWN",
        "username": "N/A",
        "wallet_balance": 0.0,
        "currency": "INR", # Default
        "account_status": "Active" # Default
    }
    
    try:
        # Navigate to personal profile / account overview if necessary,
        # or read directly from header if elements are present.
        # Check if we are on dashboard; if not, click user menu or go to account link.
        login_sel = config.SELECTORS["login"]
        prof_sel = config.SELECTORS["profile"]
        
        # Ensure elements are present
        await page.wait_for_selector(login_sel["user_profile_trigger"], timeout=5000)
        
        # Click user profile menu to ensure dashboard elements or menu info is loaded
        try:
            await page.click(login_sel["user_profile_trigger"])
            await page.wait_for_timeout(1000)
        except Exception as e:
            logger.debug(f"Could not click user profile trigger (might be already open or direct routing): {e}")

        # Extract User ID
        user_id_el = await page.query_selector(prof_sel["user_id"])
        if user_id_el:
            raw_id = await user_id_el.inner_text()
            # Extract numbers if it contains 'ID: 123456'
            id_match = re.search(r'\d+', raw_id)
            if id_match:
                profile_data["user_id"] = id_match.group(0)
            else:
                profile_data["user_id"] = raw_id.strip()

        # Extract Username
        username_el = await page.query_selector(prof_sel["username"])
        if username_el:
            profile_data["username"] = (await username_el.inner_text()).strip()

        # Extract Balance and Currency
        balance_el = await page.query_selector(prof_sel["balance"])
        if balance_el:
            raw_balance = (await balance_el.inner_text()).strip()
            # Parse balance number (e.g., '12,500.50 ₹' or '₹ 12,500.50' or '12.500,50')
            # Extract currency if present (e.g., ₹, $, €, etc.)
            currency_match = re.search(r'[^\d\s\.,\-\+]+', raw_balance)
            if currency_match:
                profile_data["currency"] = currency_match.group(0)
            
            # Clean number string: keep digits, dots, commas, and minus sign
            num_str = re.sub(r'[^\d\.,\-]', '', raw_balance)
            
            # Normalize European formatting (e.g. 1.200,50 -> 1200.50) if comma is decimal
            if ',' in num_str and '.' in num_str:
                if num_str.find('.') < num_str.find(','):
                    num_str = num_str.replace('.', '').replace(',', '.')
                else:
                    num_str = num_str.replace(',', '')
            elif ',' in num_str:
                # If only comma is present, check if it's thousands separator or decimal
                parts = num_str.split(',')
                if len(parts[-1]) == 2:  # likely decimal, e.g., 1200,50
                    num_str = num_str.replace(',', '.')
                else:  # thousands separator, e.g., 12,500
                    num_str = num_str.replace(',', '')
                    
            try:
                profile_data["wallet_balance"] = float(num_str) if num_str else 0.0
            except ValueError:
                logger.warning(f"Could not parse wallet balance string: '{raw_balance}' -> '{num_str}'")
                profile_data["wallet_balance"] = 0.0

        # Extract Account Status
        status_el = await page.query_selector(prof_sel["status"])
        if status_el:
            profile_data["account_status"] = (await status_el.inner_text()).strip()

        logger.info(f"Scraped profile successfully: ID={profile_data['user_id']}, "
                    f"User={profile_data['username']}, Balance={profile_data['wallet_balance']} {profile_data['currency']}")
                    
    except Exception as e:
        logger.error(f"Error scraping profile details: {e}")
        # Capture debug screenshot
        try:
            await page.screenshot(path="screenshots/profile_scraping_error.png")
        except Exception:
            pass

    return profile_data
