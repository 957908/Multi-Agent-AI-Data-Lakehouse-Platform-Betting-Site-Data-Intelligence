import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Table
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user") # user, admin, analyst
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Platform(Base):
    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    url = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    trust_score = Column(Float, default=50.0)
    risk_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    reviews = relationship("Review", back_populates="platform", cascade="all, delete-orphan")
    complaints = relationship("Complaint", back_populates="platform", cascade="all, delete-orphan")
    news_items = relationship("NewsItem", back_populates="platform", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="platform", cascade="all, delete-orphan")

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    platform_id = Column(Integer, ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False)
    author = Column(String, default="Anonymous")
    rating = Column(Float, nullable=False)
    content = Column(Text, nullable=False)
    scraped_at = Column(DateTime, default=datetime.datetime.utcnow)

    platform = relationship("Platform", back_populates="reviews")

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    platform_id = Column(Integer, ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, default="UNRESOLVED") # UNRESOLVED, RESOLVED, IN_PROGRESS
    scraped_at = Column(DateTime, default=datetime.datetime.utcnow)

    platform = relationship("Platform", back_populates="complaints")

class NewsItem(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    platform_id = Column(Integer, ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    source = Column(String, default="Unknown")
    published_at = Column(DateTime, default=datetime.datetime.utcnow)

    platform = relationship("Platform", back_populates="news_items")

class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    type = Column(String, nullable=False) # UPI, CRYPTO, BANK, WALLET
    reliability_score = Column(Float, default=100.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    transactions = relationship("Transaction", back_populates="payment_method")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    ref_number = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, nullable=False)
    platform_id = Column(Integer, ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False)
    method_id = Column(Integer, ForeignKey("payment_methods.id"), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False) # DEPOSIT, WITHDRAWAL
    status = Column(String, default="PENDING") # SUCCESS, FAILED, PENDING
    is_anomalous = Column(Boolean, default=False)
    datetime = Column(DateTime, default=datetime.datetime.utcnow)

    platform = relationship("Platform", back_populates="transactions")
    payment_method = relationship("PaymentMethod", back_populates="transactions")

    @property
    def platform_name(self) -> str:
        return self.platform.name if self.platform else "Unknown Platform"

    @property
    def method_name(self) -> str:
        return self.payment_method.name if self.payment_method else "Unknown Method"

class EmbeddingRecord(Base):
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    source_table = Column(String, nullable=False) # e.g. news, reviews
    source_id = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    vector_id = Column(String, nullable=True) # ID referencing FAISS index row
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AgentRecord(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False)
    status = Column(String, default="IDLE") # RUNNING, IDLE, OFFLINE
    last_active = Column(DateTime, default=datetime.datetime.utcnow)

class LogRecord(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String, nullable=False)
    severity = Column(String, default="INFO") # INFO, WARN, CRITICAL
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class ReportRecord(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    format = Column(String, nullable=False) # PDF, CSV, EXCEL, JSON
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)
