import config
import re
from playwright.async_api import Page
from config import logger

def parse_float(raw_val: str) -> float:
    """Helper to parse a float value from a string, returns 0.0 on failure."""
    try:
        cleaned = re.sub(r'[^\d\.,\-]', '', raw_val)
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
        return 0.0

async def scrape_bets(page: Page) -> list[dict]:
    """Scrapes bet history records from the bet history tab."""
    bets = []
    bet_sel = config.SELECTORS["bets"]
    
    try:
        logger.info("Navigating to Bet History page...")
        tab_visible = await page.is_visible(bet_sel["history_tab"])
        if tab_visible:
            await page.click(bet_sel["history_tab"])
            await page.wait_for_timeout(2000)
            
            rows = await page.query_selector_all(bet_sel["row"])
            logger.info(f"Found {len(rows)} bet rows in bet history.")
            
            for row in rows:
                try:
                    bet_id_el = await row.query_selector(bet_sel["bet_id"])
                    event_el = await row.query_selector(bet_sel["event_name"])
                    stake_el = await row.query_selector(bet_sel["stake"])
                    odds_el = await row.query_selector(bet_sel["odds"])
                    status_el = await row.query_selector(bet_sel["status"])
                    pnl_el = await row.query_selector(bet_sel["profit_loss"])
                    time_el = await row.query_selector(bet_sel["settlement_time"])
                    
                    bet_id_val = (await bet_id_el.inner_text()).strip() if bet_id_el else "N/A"
                    # Extract numeric ID if prefixed (e.g. "Bet ID: 9283749")
                    id_match = re.search(r'\d+', bet_id_val)
                    if id_match:
                        bet_id_val = id_match.group(0)
                        
                    event_val = (await event_el.inner_text()).strip() if event_el else "Unknown Event"
                    stake_val = parse_float(await stake_el.inner_text()) if stake_el else 0.0
                    odds_val = parse_float(await odds_el.inner_text()) if odds_el else 1.00
                    status_val = (await status_el.inner_text()).strip().upper() if status_el else "UNSETTLED"
                    pnl_val = parse_float(await pnl_el.inner_text()) if pnl_el else 0.0
                    time_val = (await time_el.inner_text()).strip() if time_el else "N/A"
                    
                    # Normalize Status
                    if any(x in status_val for x in ["WIN", "WON", "SUCCESS", "PAID"]):
                        status_val = "WIN"
                    elif any(x in status_val for x in ["LOSE", "LOST", "DEFEAT"]):
                        status_val = "LOSS"
                        # For a loss, profit_loss is negative stake
                        if pnl_val == 0.0:
                            pnl_val = -stake_val
                    elif any(x in status_val for x in ["RETURN", "REFUND", "VOID", "CANCEL"]):
                        status_val = "VOID"
                        pnl_val = 0.0
                    else:
                        status_val = "PENDING"
                        pnl_val = 0.0
                        
                    if bet_id_val != "N/A":
                        bets.append({
                            "bet_id": bet_id_val,
                            "event_name": event_val,
                            "stake": stake_val,
                            "odds": odds_val,
                            "status": status_val,
                            "profit_loss": pnl_val,
                            "settlement_time": time_val
                        })
                except Exception as row_err:
                    logger.warning(f"Error parsing bet history row: {row_err}")
        else:
            logger.info("Bet History tab not found on current page.")
            
    except Exception as e:
        logger.error(f"Error scraping bet history: {e}")
        try:
            await page.screenshot(path="screenshots/bets_scraping_error.png")
        except Exception:
            pass
            
    return bets
