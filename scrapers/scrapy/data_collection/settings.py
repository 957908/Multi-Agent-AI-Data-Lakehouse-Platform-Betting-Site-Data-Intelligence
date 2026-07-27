BOT_NAME = "data_collection"

SPIDER_MODULES = ["data_collection.spiders"]
NEWSPIDER_MODULE = "data_collection.spiders"

# Obey robots.txt rules (set false for betting site research sandbox)
ROBOTSTXT_OBEY = False

# Playwright Download Handler integration
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

# Asyncio Twisted Reactor configuration required by Scrapy Playwright
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 8

# Configure a delay for requests (Rate Limiting)
DOWNLOAD_DELAY = 1.5

# Enable cookies middleware
COOKIES_ENABLED = True

# Disable Telnet Console
TELNETCONSOLE_ENABLED = False

# Enable or disable spider middlewares
SPIDER_MIDDLEWARES = {
    "data_collection.middlewares.DataCollectionSpiderMiddleware": 543,
}

# Enable or disable downloader middlewares (Proxy and UA Rotation)
DOWNLOADER_MIDDLEWARES = {
    "data_collection.middlewares.ProxyRotationMiddleware": 400,
    "data_collection.middlewares.UserAgentRotationMiddleware": 410,
}

# Configure item pipelines
ITEM_PIPELINES = {
    "data_collection.pipelines.DataValidationPipeline": 100,
    "data_collection.pipelines.JsonExportPipeline": 200,
    "data_collection.pipelines.KafkaPublisherPipeline": 300,
    "data_collection.pipelines.PostgresExportPipeline": 400,
}

# Configure Playwright Browser settings
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "timeout": 20000,  # 20 seconds launch limit
}
