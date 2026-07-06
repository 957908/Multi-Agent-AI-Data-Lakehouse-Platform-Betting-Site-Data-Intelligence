import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
for directory in [DATA_DIR, REPORTS_DIR, SCREENSHOTS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Logger Setup
LOG_FILE = LOGS_DIR / "melbet_automation.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MelbetAnalytics")

# Configuration variables
MELBET_URL = os.getenv("MELBET_URL", "https://india.melbet.com/en")
MELBET_EMAIL = os.getenv("MELBET_EMAIL", "")
MELBET_PASSWORD = os.getenv("MELBET_PASSWORD", "")
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"
TIMEOUT = int(os.getenv("PLAYWRIGHT_TIMEOUT", "30000"))
DEBUG = os.getenv("DEBUG_MODE", "true").lower() == "true"

SESSION_FILE = DATA_DIR / "session_state.json"
DATABASE_FILE = DATA_DIR / "melbet_analytics.db"

# Selectors (Configurable for easy updates if Melbet layout changes)
SELECTORS = {
    "login": {
        "show_login_modal": ".login-btn, [data-testid='login-button'], button.login",
        "username_input": "input[name='email'], input[type='email'], input[placeholder*='Email'], #login-email",
        "password_input": "input[name='password'], input[type='password'], input[placeholder*='Password'], #login-password",
        "submit_button": "button[type='submit'], .submit-login-btn, button.login-submit, #credSection button.btn",
        "otp_input": "input[name='otp'], input[placeholder*='OTP'], input[placeholder*='code']",
        "otp_submit": ".otp-submit-btn, button.otp-submit",
        "user_profile_trigger": ".user-profile-menu, .account-button, .header-avatar, .user-id-selector",
    },
    "profile": {
        "user_id": ".user-id, .profile-id, [data-testid='user-id']",
        "username": ".user-name, .profile-name, [data-testid='user-name']",
        "balance": ".wallet-balance, .balance-value, .user-balance, [data-testid='balance']",
        "currency": ".wallet-currency, .currency-symbol, [data-testid='currency']",
        "status": ".account-status, .profile-status, [data-testid='status']",
    },
    "transactions": {
        "deposit_tab": ".deposit-history-tab, a[href*='deposit']",
        "withdrawal_tab": ".withdrawal-history-tab, a[href*='withdrawal']",
        "row": "tr.transaction-row, .transaction-item, tr.deposit-row, tr.withdrawal-row",
        "amount": ".amount, td.amount-col",
        "datetime": ".date, td.date-col",
        "method": ".method, td.method-col",
        "status": ".status, td.status-col",
        "ref_number": ".ref-id, .transaction-id, td.ref-col",
    },
    "bets": {
        "history_tab": ".bet-history-tab, a[href*='bet-history']",
        "row": "tr.bet-row, .bet-item, div.bet-history-row",
        "bet_id": ".bet-id, td.bet-id-col",
        "event_name": ".event-name, td.event-col, .bet-details-title",
        "stake": ".stake-amount, td.stake-col",
        "odds": ".odds-value, td.odds-col",
        "status": ".bet-status, td.status-col",
        "profit_loss": ".pnl-amount, td.pnl-col",
        "settlement_time": ".settlement-time, td.time-col",
    }
}
