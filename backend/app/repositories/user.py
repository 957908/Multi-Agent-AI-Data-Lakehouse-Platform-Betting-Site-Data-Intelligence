from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.models import User
from backend.app.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Fetch user by email string."""
        return db.query(self.model).filter(self.model.email == email).first()

user_repository = UserRepository(User)
