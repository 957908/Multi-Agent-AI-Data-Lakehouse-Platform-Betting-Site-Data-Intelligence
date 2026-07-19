from typing import Optional, List
from sqlalchemy.orm import Session
from backend.app.models.models import Transaction
from backend.app.repositories.base import BaseRepository

class TransactionRepository(BaseRepository[Transaction]):
    def get_by_ref_number(self, db: Session, ref_number: str) -> Optional[Transaction]:
        """Fetch transaction by unique reference reference number."""
        return db.query(self.model).filter(self.model.ref_number == ref_number).first()

    def get_by_platform(self, db: Session, platform_id: int, skip: int = 0, limit: int = 100) -> List[Transaction]:
        """Fetch transactions for a specific betting platform."""
        return db.query(self.model).filter(self.model.platform_id == platform_id).offset(skip).limit(limit).all()

    def get_anomalies(self, db: Session, skip: int = 0, limit: int = 100) -> List[Transaction]:
        """Fetch all flagged anomalous transactions."""
        return db.query(self.model).filter(self.model.is_anomalous == True).offset(skip).limit(limit).all()

transaction_repository = TransactionRepository(Transaction)
