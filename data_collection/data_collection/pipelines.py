import json
import os
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal
from backend.app.models.models import Platform, Review, Complaint, NewsItem, PaymentMethod, Transaction

class JsonExportPipeline:
    def open_spider(self, spider):
        self.output_dir = "scraped_data"
        os.makedirs(self.output_dir, exist_ok=True)
        self.file_path = os.path.join(self.output_dir, f"{spider.name}_data.json")
        self.file = open(self.file_path, "w", encoding="utf-8")
        self.file.write("[\n")
        self.first_item = True

    def close_spider(self, spider):
        self.file.write("\n]")
        self.file.close()
        spider.log(f"Exported scraped items to {self.file_path}")

    def process_item(self, item, spider):
        line = json.dumps(dict(item), ensure_ascii=False, indent=4)
        if not self.first_item:
            self.file.write(",\n")
        else:
            self.first_item = False
        self.file.write(line)
        return item

class PostgresExportPipeline:
    def open_spider(self, spider):
        self.db: Session = None
        try:
            self.db = SessionLocal()
            spider.log("[INFO] Connected to PostgreSQL Database for export.")
        except Exception as e:
            spider.log(f"[WARNING] Database connection failed for scraper export: {e}")

    def close_spider(self, spider):
        if self.db:
            self.db.close()
            spider.log("[INFO] Database connection closed.")

    def process_item(self, item, spider):
        if not self.db:
            return item

        try:
            platform_name = item.get("platform_name")
            if not platform_name:
                return item

            # 1. Ensure the platform exists in DB
            platform = self.db.query(Platform).filter(Platform.name == platform_name).first()
            if not platform:
                platform = Platform(
                    name=platform_name,
                    url=item.get("url", f"https://{platform_name.lower()}.com"),
                    description=f"Automated Scrapy profile ingest for {platform_name}"
                )
                self.db.add(platform)
                self.db.commit()
                self.db.refresh(platform)

            # 2. Match item type and persist
            item_class = item.__class__.__name__

            if item_class == "ReviewItem":
                review = Review(
                    platform_id=platform.id,
                    author=item.get("author", "Anonymous"),
                    rating=float(item.get("rating", 3.0)),
                    content=item.get("content", "")
                )
                self.db.add(review)
                self.db.commit()

            elif item_class == "ComplaintItem":
                complaint = Complaint(
                    platform_id=platform.id,
                    title=item.get("title", "No Subject"),
                    description=item.get("description", ""),
                    status=item.get("status", "UNRESOLVED")
                )
                self.db.add(complaint)
                self.db.commit()

            elif item_class == "NewsItem":
                news = NewsItem(
                    platform_id=platform.id,
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    url=item.get("url", ""),
                    source=item.get("source", "Web Scraper")
                )
                self.db.add(news)
                self.db.commit()

            elif item_class == "TransactionItem":
                # Ensure Payment Method exists
                method_name = item.get("method", "UPI")
                method = self.db.query(PaymentMethod).filter(PaymentMethod.name == method_name).first()
                if not method:
                    method = PaymentMethod(
                        name=method_name,
                        type="UPI" if "upi" in method_name.lower() else "CRYPTO" if "crypto" in method_name.lower() or "btc" in method_name.lower() else "BANK"
                    )
                    self.db.add(method)
                    self.db.commit()
                    self.db.refresh(method)

                # Check if transaction exists to prevent duplicates
                ref = item.get("ref_number")
                existing = self.db.query(Transaction).filter(Transaction.ref_number == ref).first()
                if not existing:
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

        except Exception as e:
            self.db.rollback()
            spider.log(f"[ERROR] Failed to save item to database: {e}")

        return item
