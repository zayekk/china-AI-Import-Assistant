"""
Modèle User : utilisateurs de la plateforme.
"""
import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserRole(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.FREE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Quota d'analyses (pour différencier free / pro plus tard)
    analyses_used_this_month = Column(String(20), default="0")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
