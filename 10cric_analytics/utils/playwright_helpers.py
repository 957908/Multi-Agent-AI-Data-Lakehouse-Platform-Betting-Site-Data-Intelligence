import asyncio
import random
import logging
from playwright.async_api import Page

logger = logging.getLogger("10cric_scraper.helpers")

async def apply_stealth(page: Page):
    """
    Applies common stealth patches to the page context to minimize bot detection.
    """
    # Override navigator.webdriver and other common automation detection indicators
    stealth_js = """
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };
    """
    await page.add_init_script(stealth_js)
    logger.debug("Applied stealth script patches to page context.")

async def human_scroll(page: Page, scroll_delay_range=(0.3, 0.8)):
    """
    Simulates human-like scrolling on the page to trigger dynamic content loading.
    """
    logger.info("Starting human-like page scroll simulation...")
    try:
        # Get total scrollable height
        last_height = await page.evaluate("document.body.scrollHeight")
        current_height = 0
        step = 400
        
        while current_height < last_height:
            # Scroll down by step
            current_height += step
            await page.evaluate(f"window.scrollTo(0, {current_height})")
            
            # Dynamic random delay
            await asyncio.sleep(random.uniform(*scroll_delay_range))
            
            # Recalculate height in case new content lazy loaded
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height > last_height:
                last_height = new_height
                
        # Scroll back to top
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)
        logger.info("Scroll simulation complete.")
    except Exception as e:
        logger.warning(f"Error during scroll simulation: {e}")
