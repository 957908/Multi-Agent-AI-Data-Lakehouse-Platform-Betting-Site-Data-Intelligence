import random
from scrapy import signals


# ─────────────────────────────────────────────────────────────────────────────
# User-Agent pool — modern browser strings
# ─────────────────────────────────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

# ─────────────────────────────────────────────────────────────────────────────
# Proxy pool — populated from env or settings PROXY_LIST
# Format: ["http://user:pass@host:port", ...]
# Set PROXY_ROTATION_ENABLED = True in settings.py to activate
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_PROXY_LIST = [
    # Add real proxy URLs here or configure via PROXY_LIST in settings.py
    # Example: "http://user:pass@proxy.example.com:8080"
]


class UserAgentRotationMiddleware:
    """
    Rotates User-Agent on every non-Playwright HTTP request.
    For Playwright requests, sets the UA at browser context level.
    """
    def process_request(self, request, spider):
        ua = random.choice(USER_AGENTS)
        request.headers["User-Agent"] = ua

        # Also inject UA into Playwright browser context if this is a Playwright request
        if request.meta.get("playwright"):
            request.meta.setdefault("playwright_context_kwargs", {})
            request.meta["playwright_context_kwargs"]["user_agent"] = ua


class ProxyRotationMiddleware:
    """
    Rotates proxies on each request.
    Enabled via PROXY_ROTATION_ENABLED = True in settings.py
    Proxy list configured via PROXY_LIST setting or DEFAULT_PROXY_LIST above.
    """

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
        instance.enabled = crawler.settings.getbool("PROXY_ROTATION_ENABLED", default=False)
        instance.proxy_list = crawler.settings.getlist("PROXY_LIST", default=DEFAULT_PROXY_LIST)

        if instance.enabled and not instance.proxy_list:
            crawler.spider.logger.warning(
                "[PROXY] PROXY_ROTATION_ENABLED=True but PROXY_LIST is empty. "
                "Add proxy URLs to settings.py PROXY_LIST or middlewares.py DEFAULT_PROXY_LIST."
            )
            instance.enabled = False

        if instance.enabled:
            crawler.spider.logger.info(
                f"[PROXY] Proxy rotation enabled with {len(instance.proxy_list)} proxies."
            )
        else:
            crawler.spider.logger.info("[PROXY] Proxy rotation disabled. Using direct connection.")

        return instance

    def process_request(self, request, spider):
        if not self.enabled or not self.proxy_list:
            return
        proxy = random.choice(self.proxy_list)
        request.meta["proxy"] = proxy


class DataCollectionSpiderMiddleware:
    """
    Core spider middleware — logs spider lifecycle events.
    """
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(s.spider_closed, signal=signals.spider_closed)
        return s

    def spider_opened(self, spider):
        spider.logger.info(
            f"[SPIDER OPENED] {spider.name} | "
            f"Platform: {getattr(spider, 'platform_name', 'N/A')} | "
            f"Target: {getattr(spider, 'deposit_page_url', 'N/A')}"
        )

    def spider_closed(self, spider):
        spider.logger.info(f"[SPIDER CLOSED] {spider.name} — scraping session ended.")

