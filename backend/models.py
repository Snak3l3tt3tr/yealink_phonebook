"""
SQLAlchemy models for the phonebook database.
"""
from sqlalchemy import Column, ForeignKey, Integer, String
from database import Base


class Contact(Base):
    """Contact model with name and up to 3 phone numbers."""

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    phone1 = Column(String, nullable=True)
    phone2 = Column(String, nullable=True)
    phone3 = Column(String, nullable=True)

    def __repr__(self):
        return f"<Contact(name={self.name}, phone1={self.phone1})>"


class AdminUser(Base):
    """Single administrator account stored in the application database."""

    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)


class AuthSession(Base):
    """Server-side login session; only a hash of the cookie is stored."""

    __tablename__ = "auth_sessions"

    token_hash = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("admin_users.id"), nullable=False)
    expires_at = Column(Integer, nullable=False)
