import scrapy


class PlatformItem(scrapy.Item):
    name = scrapy.Field()
    url = scrapy.Field()
    description = scrapy.Field()
    trust_score = scrapy.Field()
    risk_score = scrapy.Field()


class ReviewItem(scrapy.Item):
    platform_name = scrapy.Field()
    author = scrapy.Field()
    rating = scrapy.Field()
    content = scrapy.Field()
    source_url = scrapy.Field()
    scrape_timestamp = scrapy.Field()
    collection_agent = scrapy.Field()
    data_quality = scrapy.Field()     # REAL | NOT_SCRAPED | SCRAPE_FAILED
    _pushed_to_kafka = scrapy.Field()


class ComplaintItem(scrapy.Item):
    platform_name = scrapy.Field()
    title = scrapy.Field()
    description = scrapy.Field()
    status = scrapy.Field()           # UNRESOLVED | RESOLVED | IN_PROGRESS
    source_url = scrapy.Field()
    scrape_timestamp = scrapy.Field()
    collection_agent = scrapy.Field()
    data_quality = scrapy.Field()
    _pushed_to_kafka = scrapy.Field()


class NewsItem(scrapy.Item):
    platform_name = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()
    url = scrapy.Field()
    source = scrapy.Field()
    scrape_timestamp = scrapy.Field()
    collection_agent = scrapy.Field()
    data_quality = scrapy.Field()
    _pushed_to_kafka = scrapy.Field()


class TransactionItem(scrapy.Item):
    platform_name = scrapy.Field()
    ref_number = scrapy.Field()
    user_id = scrapy.Field()
    amount = scrapy.Field()
    method = scrapy.Field()
    type = scrapy.Field()             # DEPOSIT | WITHDRAWAL
    status = scrapy.Field()           # SUCCESS | FAILED | PENDING
    timestamp = scrapy.Field()        # ISO-8601 datetime string
    source_url = scrapy.Field()
    scrape_timestamp = scrapy.Field()
    collection_agent = scrapy.Field()
    data_quality = scrapy.Field()
    _pushed_to_kafka = scrapy.Field()


class PaymentMethodItem(scrapy.Item):
    """
    Scraped from public deposit pages only.
    Fields that require authentication are set to "Not Yet Collected".
    Every field has a traceable source.
    """
    platform_name = scrapy.Field()
    method_name = scrapy.Field()
    method_type = scrapy.Field()      # UPI | CRYPTO | BANK | WALLET | CARD | UNKNOWN

    # Availability — True if visible on public deposit page; None if not determinable
    deposit_supported = scrapy.Field()
    withdrawal_supported = scrapy.Field()

    # Limits & fees — "Not Yet Collected" if requires authentication
    min_deposit = scrapy.Field()
    max_deposit = scrapy.Field()
    min_withdrawal = scrapy.Field()
    max_withdrawal = scrapy.Field()
    fee = scrapy.Field()
    processing_time = scrapy.Field()

    # Provenance — required on every record
    source_url = scrapy.Field()
    scrape_timestamp = scrapy.Field()
    collection_agent = scrapy.Field()
    data_quality = scrapy.Field()     # REAL | NOT_SCRAPED | SCRAPE_FAILED | AUTH_REQUIRED
    scrape_error = scrapy.Field()     # Error message if scrape failed; None on success

    _pushed_to_kafka = scrapy.Field()
