import config
import re
from playwright.async_api import Page
from config import logger

def parse_amount(raw_amount: str) -> float:
    """Parses a float value from a raw amount string."""
    try:
        # Strip currency symbols and whitespace
        cleaned = re.sub(r'[^\d\.,\-]', '', raw_amount)
        # Normalize formatting (e.g., 1,200.00 -> 1200.0)
        if ',' in cleaned and '.' in cleaned:
            if cleaned.find('.') < cleaned.find(','):
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            parts = cleaned.split(',')
            if len(parts[-1]) == 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        return float(cleaned) if cleaned else 0.0
    except Exception:
        logger.warning(f"Could not parse amount from: {raw_amount}")
        return 0.0

async def scrape_transactions(page: Page) -> tuple[list[dict], list[dict]]:
    """Scrapes deposits and withdrawals history."""
    deposits = []
    withdrawals = []
    
    tx_sel = config.SELECTORS["transactions"]
    
    # --- 1. Scrape Deposits ---
    try:
        logger.info("Navigating to Deposit History page...")
        # Check if tab exists and click it, or navigate to a direct URL if known
        deposit_tab_visible = await page.is_visible(tx_sel["deposit_tab"])
        if deposit_tab_visible:
            await page.click(tx_sel["deposit_tab"])
            await page.wait_for_timeout(2000)
            
            rows = await page.query_selector_all(tx_sel["row"])
            logger.info(f"Found {len(rows)} deposit rows in transaction page.")
            
            for row in rows:
                try:
                    amount_el = await row.query_selector(tx_sel["amount"])
                    date_el = await row.query_selector(tx_sel["datetime"])
                    method_el = await row.query_selector(tx_sel["method"])
                    status_el = await row.query_selector(tx_sel["status"])
                    ref_el = await row.query_selector(tx_sel["ref_number"])
                    
                    amount_val = parse_amount(await amount_el.inner_text()) if amount_el else 0.0
                    date_val = (await date_el.inner_text()).strip() if date_el else "N/A"
                    method_val = (await method_el.inner_text()).strip() if method_el else "Unknown"
                    status_val = (await status_el.inner_text()).strip().upper() if status_el else "UNKNOWN"
                    ref_val = (await ref_el.inner_text()).strip() if ref_el else "N/A"
                    
                    # Normalize Status
                    if any(x in status_val for x in ["SUCCESS", "DONE", "COMPLETED", "APPROVED", "ACCEPTED"]):
                        status_val = "SUCCESS"
                    elif any(x in status_val for x in ["FAIL", "REJECT", "DECLINED", "CANCEL"]):
                        status_val = "FAILED"
                    else:
                        status_val = "PENDING"
                        
                    if ref_val != "N/A":
                        deposits.append({
                            "amount": amount_val,
                            "datetime": date_val,
                            "method": method_val,
                            "status": status_val,
                            "ref_number": ref_val
                        })
                except Exception as row_err:
                    logger.warning(f"Error parsing deposit row: {row_err}")
        else:
            logger.info("Deposit History tab not found on current page.")
            
    except Exception as e:
        logger.error(f"Error scraping deposits: {e}")
        try:
            await page.screenshot(path="screenshots/deposits_scraping_error.png")
        except Exception:
            pass

    # --- 2. Scrape Withdrawals ---
    try:
        logger.info("Navigating to Withdrawal History page...")
        withdrawal_tab_visible = await page.is_visible(tx_sel["withdrawal_tab"])
        if withdrawal_tab_visible:
            await page.click(tx_sel["withdrawal_tab"])
            await page.wait_for_timeout(2000)
            
            rows = await page.query_selector_all(tx_sel["row"])
            logger.info(f"Found {len(rows)} withdrawal rows in transaction page.")
            
            for row in rows:
                try:
                    amount_el = await row.query_selector(tx_sel["amount"])
                    date_el = await row.query_selector(tx_sel["datetime"])
                    status_el = await row.query_selector(tx_sel["status"])
                    ref_el = await row.query_selector(tx_sel["ref_number"])
                    
                    amount_val = parse_amount(await amount_el.inner_text()) if amount_el else 0.0
                    date_val = (await date_el.inner_text()).strip() if date_el else "N/A"
                    status_val = (await status_el.inner_text()).strip().upper() if status_el else "UNKNOWN"
                    ref_val = (await ref_el.inner_text()).strip() if ref_el else "N/A"
                    
                    # Normalize Status
                    if any(x in status_val for x in ["SUCCESS", "DONE", "COMPLETED", "APPROVED", "ACCEPTED"]):
                        status_val = "SUCCESS"
                    elif any(x in status_val for x in ["FAIL", "REJECT", "DECLINED", "CANCEL"]):
                        status_val = "FAILED"
                    else:
                        status_val = "PENDING"
                        
                    if ref_val != "N/A":
                        withdrawals.append({
                            "amount": amount_val,
                            "datetime": date_val,
                            "status": status_val,
                            "ref_number": ref_val
                        })
                except Exception as row_err:
                    logger.warning(f"Error parsing withdrawal row: {row_err}")
        else:
            logger.info("Withdrawal History tab not found on current page.")
            
    except Exception as e:
        logger.error(f"Error scraping withdrawals: {e}")
        try:
            await page.screenshot(path="screenshots/withdrawals_scraping_error.png")
        except Exception:
            pass

    return deposits, withdrawals
