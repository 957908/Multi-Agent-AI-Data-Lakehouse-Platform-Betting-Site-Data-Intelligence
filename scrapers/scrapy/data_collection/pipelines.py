import json
import os
import sys
import logging
from datetime import datetime, timezone

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scrapy.exceptions import DropItem
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal
from backend.app.models.models import (
    Platform, Review, Complaint,
    NewsItem as DBNewsItem,   # ← renamed to avoid collision with Scrapy item class
    PaymentMethod, Transaction
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE 1 — Validation (priority 100)
# ─────────────────────────────────────────────────────────────────────────────
class DataValidationPipeline:
    """
    Validates required fields before any downstream pipeline runs.
    Only TransactionItem has strict validation (financial records must be clean).
    PaymentMethodItem with data_quality=NOT_SCRAPED or SCRAPE_FAILED passes through.
    """
    def process_item(self, item, spider):
        item_class = item.__class__.__name__

        if item_class == "TransactionItem":
            ref_number = item.get("ref_number")
            platform_name = item.get("platform_name")
            amount = item.get("amount")

            if not ref_number or not platform_name or amount is None:
                raise DropItem(
                    f"[VALIDATION FAILED] TransactionItem missing required fields: "
                    f"ref_number={ref_number}, platform_name={platform_name}, amount={amount}"
                )
            try:
                if float(amount) <= 0:
                    raise DropItem(f"[VALIDATION FAILED] Amount must be positive: {amount}")
            except (ValueError, TypeError):
                raise DropItem(f"[VALIDATION FAILED] Amount not a number: {amount}")

        elif item_class == "PaymentMethodItem":
            if not item.get("platform_name") or not item.get("method_name"):
                raise DropItem("[VALIDATION FAILED] PaymentMethodItem missing platform_name or method_name")

        return item


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE 2 — JSON Export (priority 200)
# ─────────────────────────────────────────────────────────────────────────────
class JsonExportPipeline:
    """
    Writes all scraped items to a JSON file in scraped_data/{spider_name}_data.json.
    Includes full provenance metadata on every record.
    """
    def open_spider(self, spider):
        self.output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scraped_data"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        self.file_path = os.path.join(self.output_dir, f"{spider.name}_data.json")
        self.file = open(self.file_path, "w", encoding="utf-8")
        self.file.write("[\n")
        self.first_item = True
        spider.log(f"[JSON EXPORT] Writing to: {self.file_path}")

    def close_spider(self, spider):
        self.file.write("\n]")
        self.file.close()
        spider.log(f"[JSON EXPORT] Completed: {self.file_path}")

    def process_item(self, item, spider):
        record = dict(item)
        # Ensure export_timestamp is on every record
        record["export_timestamp"] = datetime.now(timezone.utc).isoformat()
        line = json.dumps(record, ensure_ascii=False, indent=2, default=str)
        if not self.first_item:
            self.file.write(",\n")
        else:
            self.first_item = False
        self.file.write(line)
        return item


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE 3 — Kafka Publisher (priority 300)
# ─────────────────────────────────────────────────────────────────────────────
class KafkaPublisherPipeline:
    """
    Publishes validated items to Kafka topics.
    Falls back gracefully if Kafka broker is unavailable (Docker not running).
    Topic naming: sentinelx.raw.{item_type}
    """
    ITEM_TOPIC_MAP = {
        "PaymentMethodItem": "sentinelx.raw.payments",
        "TransactionItem":   "sentinelx.raw.transactions",
        "ReviewItem":        "sentinelx.raw.reviews",
        "ComplaintItem":     "sentinelx.raw.complaints",
        "NewsItem":          "sentinelx.raw.news",
    }

    def open_spider(self, spider):
        self.producer = None
        try:
            from data_pipelines.kafka.kafka_producer import SharedKafkaProducer
            self.producer = SharedKafkaProducer()
            spider.log(f"[KAFKA] Producer initialized. Enabled: {self.producer.enabled}")
        except Exception as e:
            spider.log(f"[KAFKA] Producer unavailable (Docker not running?): {e}", level=logging.WARNING)

    def close_spider(self, spider):
        if self.producer:
            try:
                self.producer.close()
            except Exception as e:
                spider.log(f"[KAFKA] Close error: {e}", level=logging.WARNING)

    def process_item(self, item, spider):
        item_class = item.__class__.__name__
        topic = self.ITEM_TOPIC_MAP.get(item_class, f"sentinelx.raw.{item_class.lower()}")

        payload = dict(item)
        if "timestamp" not in payload:
            payload["timestamp"] = datetime.now(timezone.utc).isoformat()

        if self.producer and self.producer.enabled:
            try:
                success = self.producer.publish_event(topic, payload)
                if success:
                    item["_pushed_to_kafka"] = True
                    spider.log(
                        f"[KAFKA ✓] Published {item_class} → {topic} | "
                        f"platform={payload.get('platform_name')} | "
                        f"method/ref={payload.get('method_name') or payload.get('ref_number')}"
                    )
                else:
                    spider.log(f"[KAFKA ✗] Publish failed → {topic}. DB fallback will handle.", level=logging.WARNING)
            except Exception as e:
                spider.log(f"[KAFKA ERROR] {e} → {topic}. DB fallback active.", level=logging.WARNING)
        else:
            spider.log(
                f"[KAFKA OFFLINE] {item_class} → will write directly to DB. Topic would be: {topic}",
                level=logging.WARNING
            )

        return item


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE 4 — Database Export (priority 400)
# ─────────────────────────────────────────────────────────────────────────────
class PostgresExportPipeline:
    """
    Writes items to SQLite (or PostgreSQL when Docker is running).
    Skips items already pushed to Kafka to avoid duplicates.
    PaymentMethodItem — stores to payment_methods table with data_quality field.
    """

    METHOD_TYPE_KEYWORDS = {
        "UPI":    ["upi", "gpay", "phonepe", "paytm", "bhim", "google pay", "qr", "imps"],
        "CRYPTO": ["crypto", "btc", "bitcoin", "eth", "ethereum", "usdt", "tether",
                   "solana", "dogecoin", "bnb", "xrp", "polygon", "usdc", "shiba"],
        "BANK":   ["netbanking", "bank transfer", "neft", "rtgs", "swift", "wire", "bank"],
        "WALLET": ["skrill", "neteller", "paypal", "astropay", "mifinity", "wallet", "webmoney", "jeton"],
        "CARD":   ["visa", "mastercard", "maestro", "amex", "credit card", "debit card"],
    }

    def classify_method_type(self, name: str) -> str:
        n = name.lower()
        for mtype, keywords in self.METHOD_TYPE_KEYWORDS.items():
            if any(k in n for k in keywords):
                return mtype
        return "WALLET"  # Most unknown payment methods are e-wallets

    def open_spider(self, spider):
        self.db: Session = None
        try:
            self.db = SessionLocal()
            spider.log("[DB] Connected to database for export.")
        except Exception as e:
            spider.log(f"[DB WARNING] Connection failed: {e}", level=logging.WARNING)

    def close_spider(self, spider):
        if self.db:
            self.db.close()
            spider.log("[DB] Connection closed.")

    def process_item(self, item, spider):
        if not self.db:
            return item

        # Skip if already pushed to Kafka (avoid double-write)
        if item.get("_pushed_to_kafka"):
            spider.log(
                f"[DB SKIP] Already in Kafka: {item.get('method_name') or item.get('ref_number', '')}",
                level=logging.DEBUG
            )
            return item

        try:
            platform_name = item.get("platform_name")
            if not platform_name:
                return item

            # Ensure platform exists
            platform = self.db.query(Platform).filter(Platform.name == platform_name).first()
            if not platform:
                platform = Platform(
                    name=platform_name,
                    url=item.get("source_url", f"https://{platform_name.lower().replace(' ', '')}.com"),
                    description=f"Auto-created by spider: {item.get('collection_agent', 'unknown')}"
                )
                self.db.add(platform)
                self.db.commit()
                self.db.refresh(platform)
                spider.log(f"[DB] Created new platform: {platform_name}")

            item_class = item.__class__.__name__

            if item_class == "PaymentMethodItem":
                method_name = item.get("method_name", "Unknown")
                method_type = item.get("method_type") or self.classify_method_type(method_name)

                # Skip NOT_SCRAPED / SCRAPE_FAILED entries — don't pollute DB with non-data
                if item.get("data_quality") in ("NOT_SCRAPED", "SCRAPE_FAILED"):
                    spider.log(f"[DB SKIP] PaymentMethodItem data_quality={item.get('data_quality')} — not storing.")
                    return item

                existing = self.db.query(PaymentMethod).filter(PaymentMethod.name == method_name).first()
                if not existing:
                    method = PaymentMethod(name=method_name, type=method_type)
                    self.db.add(method)
                    self.db.commit()
                    spider.log(f"[DB ✓] Saved payment method: {method_name} ({method_type})")
                else:
                    spider.log(f"[DB SKIP] PaymentMethod already exists: {method_name}")

            elif item_class == "ReviewItem":
                review = Review(
                    platform_id=platform.id,
                    author=item.get("author", "Anonymous"),
                    rating=float(item.get("rating", 0.0)),
                    content=item.get("content", "")
                )
                self.db.add(review)
                self.db.commit()
                spider.log(f"[DB ✓] Saved review for {platform_name}")

            elif item_class == "ComplaintItem":
                complaint = Complaint(
                    platform_id=platform.id,
                    title=item.get("title", "No Subject"),
                    description=item.get("description", ""),
                    status=item.get("status", "UNRESOLVED")
                )
                self.db.add(complaint)
                self.db.commit()
                spider.log(f"[DB ✓] Saved complaint for {platform_name}")

            elif item_class == "NewsItem":
                # FIX: use DBNewsItem (imported as alias) to avoid name collision with Scrapy's NewsItem
                news_record = DBNewsItem(
                    platform_id=platform.id,
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    url=item.get("url", ""),
                    source=item.get("source", "Web Scraper")
                )
                self.db.add(news_record)
                self.db.commit()
                spider.log(f"[DB ✓] Saved news item for {platform_name}")

            elif item_class == "TransactionItem":
                method_name = item.get("method", "Unknown")
                method = self.db.query(PaymentMethod).filter(PaymentMethod.name == method_name).first()
                if not method:
                    method = PaymentMethod(
                        name=method_name,
                        type=self.classify_method_type(method_name)
                    )
                    self.db.add(method)
                    self.db.commit()
                    self.db.refresh(method)

                ref = item.get("ref_number")
                if not self.db.query(Transaction).filter(Transaction.ref_number == ref).first():
                    tx = Transaction(
                        ref_number=ref,
                        user_id=item.get("user_id", "ANONYMOUS"),
                        platform_id=platform.id,
                        method_id=method.id,
                        amount=float(item.get("amount", 0.0)),
                        type=item.get("type", "DEPOSIT"),
                        status=item.get("status", "PENDING")
                    )
                    self.db.add(tx)
                    self.db.commit()
                    spider.log(f"[DB ✓] Saved transaction: {ref}")
                else:
                    spider.log(f"[DB SKIP] Transaction already exists: {ref}")

        except Exception as e:
            self.db.rollback()
            spider.log(f"[DB ERROR] Failed to save {item.__class__.__name__}: {e}", level=logging.ERROR)

        return item
