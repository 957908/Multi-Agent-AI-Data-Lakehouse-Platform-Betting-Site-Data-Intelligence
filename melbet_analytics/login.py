import asyncio
import os
from pathlib import Path
import config
from playwright.async_api import BrowserContext, Page, async_playwright
from config import (
    SESSION_FILE, MELBET_EMAIL, MELBET_PASSWORD, 
    BROWSER_HEADLESS, TIMEOUT, logger
)


async def check_session_validity(page: Page) -> bool:
    """Checks if the loaded session is still valid by looking for user profile elements."""
    try:
        logger.info("Verifying session validity...")
        await page.goto(config.MELBET_URL, timeout=TIMEOUT, wait_until="domcontentloaded")
        
        # Wait a short moment for dynamic JS to load
        await asyncio.sleep(3)
        
        # If the user profile selector is visible, we are logged in.
        # If the login button is visible, we need to authenticate again.
        user_menu_selector = config.SELECTORS["login"]["user_profile_trigger"]
        login_btn_selector = config.SELECTORS["login"]["show_login_modal"]
        
        is_user_menu_visible = await page.is_visible(user_menu_selector)
        is_login_btn_visible = await page.is_visible(login_btn_selector)
        
        if is_user_menu_visible:
            logger.info("Existing session is valid.")
            return True
        elif is_login_btn_visible:
            logger.info("Session invalid or expired (login button visible).")
            return False
            
        # Fallback check
        logger.info("Unable to definitively determine session status. Re-authenticating to be safe.")
        return False
    except Exception as e:
        logger.warning(f"Error checking session validity: {e}")
        return False

async def get_otp_from_user() -> str:
    """Prompts the user via CLI for an OTP if required."""
    print("\n" + "=" * 50)
    print("ACTION REQUIRED: OTP (One-Time Password) / 2FA code is requested by Melbet.")
    print("Please check your email/phone and enter the code below.")
    print("=" * 50)
    # Use asyncio.to_thread to prevent blocking the async loop
    otp = await asyncio.to_thread(input, "Enter OTP / 2FA Code: ")
    return otp.strip()

async def perform_login(page: Page, max_retries: int = 3) -> bool:
    """Navigates to Melbet and performs the login sequence with retries and OTP support."""
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Login attempt {attempt}/{max_retries}...")
            await page.goto(config.MELBET_URL, timeout=TIMEOUT, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            login_sel = config.SELECTORS["login"]
            
            # Click login button to open modal
            if await page.is_visible(login_sel["show_login_modal"]):
                logger.info("Opening login modal...")
                await page.click(login_sel["show_login_modal"])
                await asyncio.sleep(1)
            
            # Fill Credentials
            logger.info(f"Filling credentials for {MELBET_EMAIL}...")
            await page.fill(login_sel["username_input"], MELBET_EMAIL)
            await page.fill(login_sel["password_input"], MELBET_PASSWORD)
            
            # Click submit
            logger.info("Submitting login form...")
            await page.click(login_sel["submit_button"])
            await asyncio.sleep(3)
            
            # Check for OTP field
            is_otp_required = await page.is_visible(login_sel["otp_input"])
            if is_otp_required:
                otp_code = await get_otp_from_user()
                logger.info("Entering OTP...")
                await page.fill(login_sel["otp_input"], otp_code)
                await page.click(login_sel["otp_submit"])
                await asyncio.sleep(4)
                
            # Verify if login succeeded
            is_logged_in = await page.is_visible(login_sel["user_profile_trigger"])
            if is_logged_in:
                logger.info("Successfully authenticated with Melbet.")
                # Save session state
                await page.context.storage_state(path=str(SESSION_FILE))
                logger.info(f"Session saved to {SESSION_FILE}")
                return True
                
            # Check for generic error message on page
            error_el = await page.query_selector(".error-msg, .login-error")
            if error_el:
                error_text = await error_el.inner_text()
                logger.warning(f"Login error displayed: {error_text.strip()}")
                
        except Exception as e:
            logger.error(f"Error during login attempt {attempt}: {e}")
            # Take a debug screenshot
            screenshot_path = Path(__file__).parent / "screenshots" / f"login_error_attempt_{attempt}.png"
            try:
                await page.screenshot(path=str(screenshot_path))
                logger.info(f"Saved error screenshot to {screenshot_path}")
            except Exception as se:
                logger.error(f"Failed to capture login screenshot: {se}")
            
            if attempt < max_retries:
                await asyncio.sleep(3)
                
    return False

async def get_authenticated_context(playwright) -> tuple[BrowserContext, Page, bool]:
    """
    Launches browser and provides an authenticated context and page.
    Returns: (BrowserContext, Page, is_new_login_performed)
    """
    browser = await playwright.chromium.launch(
        headless=BROWSER_HEADLESS,
        args=["--disable-blink-features=AutomationControlled"]
    )
    
    # Load session if exists
    if SESSION_FILE.exists():
        logger.info(f"Loading persistent session from {SESSION_FILE}...")
        context = await browser.new_context(
            storage_state=str(SESSION_FILE),
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Verify session
        if await check_session_validity(page):
            return context, page, False
            
        # If session is invalid, close context and create a fresh one
        logger.info("Loaded session was invalid. Re-authenticating...")
        await context.close()

    # Fresh login
    logger.info("Starting fresh browser session for authentication...")
    context = await browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    
    login_success = await perform_login(page)
    if not login_success:
        await context.close()
        await browser.close()
        raise RuntimeError("Authentication failed. Unable to obtain active session.")
        
    return context, page, True
