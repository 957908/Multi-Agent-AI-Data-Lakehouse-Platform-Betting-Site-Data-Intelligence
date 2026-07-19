from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.models import Platform
from backend.app.repositories.base import BaseRepository

class PlatformRepository(BaseRepository[Platform]):
    def get_by_name(self, db: Session, name: str) -> Optional[Platform]:
        """Fetch betting platform by name."""
        return db.query(self.model).filter(self.model.name == name).first()

platform_repository = PlatformRepository(Platform)
