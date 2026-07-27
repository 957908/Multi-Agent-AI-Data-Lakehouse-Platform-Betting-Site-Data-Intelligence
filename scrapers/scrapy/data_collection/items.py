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
    _pushed_to_kafka = scrapy.Field()

class ComplaintItem(scrapy.Item):
    platform_name = scrapy.Field()
    title = scrapy.Field()
    description = scrapy.Field()
    status = scrapy.Field()
    _pushed_to_kafka = scrapy.Field()

class NewsItem(scrapy.Item):
    platform_name = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()
    url = scrapy.Field()
    source = scrapy.Field()

class TransactionItem(scrapy.Item):
    platform_name = scrapy.Field()
    ref_number = scrapy.Field()
    user_id = scrapy.Field()
    amount = scrapy.Field()
    method = scrapy.Field()
    type = scrapy.Field() # DEPOSIT, WITHDRAWAL
    status = scrapy.Field() # SUCCESS, FAILED, PENDING
    _pushed_to_kafka = scrapy.Field()
