import random
from scrapy import signals

# Complete list of modern user agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/115.0.1901.203",
]

# List of premium proxy placeholders (will be bypassed if mock mode is on)
PROXIES = [
    "http://127.0.0.1:8118", # Local proxy fallbacks
    "http://127.0.0.1:8119",
]

class UserAgentRotationMiddleware:
    def process_request(self, request, spider):
        user_agent = random.choice(USER_AGENTS)
        request.headers["User-Agent"] = user_agent
        # Log to debug output if needed
        # spider.log(f"Rotated User-Agent: {user_agent}")

class ProxyRotationMiddleware:
    def __init__(self):
        # We can toggle proxy routing via configuration to run locally without external proxy services
        self.enabled = False

    def process_request(self, request, spider):
        if not self.enabled:
            return
            
        proxy = random.choice(PROXIES)
        request.meta["proxy"] = proxy
        # spider.log(f"Routing request through proxy: {proxy}")

class DataCollectionSpiderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)
