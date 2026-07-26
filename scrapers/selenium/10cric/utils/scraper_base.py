import os
import json
import logging
from datetime import datetime
import asyncio
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Error as PlaywrightError
from utils.playwright_helpers import apply_stealth, human_scroll

class BaseScraper:
    """
    Base asynchronous scraper class containing core Playwright logic,
    retries, file saving, and default metadata extraction.
    """
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url
        self.timestamp = datetime.now().isoformat()
        self.timestamp_safe = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Setup directories
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.screenshots_dir = os.path.join(self.base_dir, "screenshots")
        self.html_dir = os.path.join(self.base_dir, "html")
        self.json_dir = os.path.join(self.base_dir, "json")
        self.logs_dir = os.path.join(self.base_dir, "logs")
        
        for d in [self.screenshots_dir, self.html_dir, self.json_dir, self.logs_dir]:
            os.makedirs(d, exist_ok=True)
            
        # Setup logging
        self._setup_logging()
        
        # Playwright placeholders
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def _setup_logging(self):
        """Initializes module-specific logger to console and file."""
        self.logger = logging.getLogger(f"10cric_scraper.{self.name}")
        self.logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            
            # File handler
            log_file = os.path.join(self.logs_dir, f"{self.name}.log")
            fh = logging.FileHandler(log_file, encoding='utf-8')
            fh.setLevel(logging.INFO)
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
            
            # Console handler
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

    async def init_browser(self):
        """Launches browser and creates a clean context with custom config."""
        self.logger.info("Initializing Playwright browser...")
        self.playwright = await async_playwright().start()
        
        # Launch Chromium with robust args
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        
        # Create a modern desktop browser context
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="Asia/Kolkata"
        )
        
        self.page = await self.context.new_page()
        await apply_stealth(self.page)

    async def close_browser(self):
        """Gracefully closes all browser resources."""
        self.logger.info("Closing browser resources...")
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.logger.info("Browser resources closed.")

    async def navigate_with_retry(self, retries: int = 3, initial_delay: float = 2.0) -> bool:
        """
        Navigates to the target URL with exponential backoff retry logic.
        """
        delay = initial_delay
        for attempt in range(1, retries + 1):
            try:
                self.logger.info(f"Navigating to {self.url} (Attempt {attempt}/{retries})...")
                # Navigate and wait for DOM content loaded
                response = await self.page.goto(self.url, wait_until="domcontentloaded", timeout=45000)
                
                # Check HTTP Status Code if available
                status = response.status if response else 0
                if status and status >= 400:
                    raise PlaywrightError(f"HTTP error status: {status}")
                
                # Wait for standard load state and some extra network idle
                await self.page.wait_for_load_state("load")
                await asyncio.sleep(2)  # Short pause to let static page load
                
                self.logger.info("Navigation successful.")
                return True
            except PlaywrightError as e:
                self.logger.warning(f"Attempt {attempt} failed: {e}")
                if attempt < retries:
                    self.logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    self.logger.error("All navigation attempts failed.")
                    return False
        return False

    async def capture_metadata(self) -> Dict[str, Any]:
        """
        Extracts title, URL, meta description, and page headings.
        """
        self.logger.info("Extracting standard page metadata...")
        
        page_title = await self.page.title()
        page_url = self.page.url
        
        # Meta description extraction
        meta_desc = ""
        try:
            meta_element = await self.page.query_selector('meta[name="description"]')
            if meta_element:
                meta_desc = await meta_element.get_attribute("content") or ""
        except Exception as e:
            self.logger.debug(f"Failed to extract meta description: {e}")

        # Heading extraction (H1-H6)
        headings = []
        try:
            for level in range(1, 7):
                elements = await self.page.query_selector_all(f"h{level}")
                for el in elements:
                    text = await el.inner_text()
                    text = text.strip()
                    if text:
                        headings.append({
                            "tag": f"H{level}",
                            "text": text
                        })
        except Exception as e:
            self.logger.error(f"Failed to extract headings: {e}")
            
        return {
            "page_title": page_title,
            "page_url": page_url,
            "meta_description": meta_desc,
            "headings": headings
        }

    async def take_screenshot(self) -> str:
        """Captures page screenshot and saves to disk."""
        filepath = os.path.join(self.screenshots_dir, f"{self.name}_{self.timestamp_safe}.png")
        self.logger.info(f"Capturing screenshot: {filepath}")
        await self.page.screenshot(path=filepath, full_page=True, timeout=15000)
        return filepath

    async def save_html(self) -> str:
        """Saves current raw HTML snapshot of the page."""
        filepath = os.path.join(self.html_dir, f"{self.name}_{self.timestamp_safe}.html")
        self.logger.info(f"Saving HTML snapshot: {filepath}")
        content = await self.page.content()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath

    def save_json(self, data: Dict[str, Any]) -> str:
        """Saves data structure as structured JSON file."""
        filepath = os.path.join(self.json_dir, f"{self.name}_{self.timestamp_safe}.json")
        self.logger.info(f"Saving JSON output: {filepath}")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return filepath

    async def scrape(self) -> Dict[str, Any]:
        """
        Template method that should be extended/customized in children.
        Performs setup -> navigate -> load details -> metadata -> extract content -> save artifacts.
        """
        raise NotImplementedError("Scraper classes must implement their own custom scrape method.")
