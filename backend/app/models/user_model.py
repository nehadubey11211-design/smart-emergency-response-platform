"""
FILE: backend/app/models/user_model.py
============================================
SQLAlchemy ORM Model — Users Table
============================================

A SQLAlchemy model is a Python class that maps to a database table.
Each class attribute decorated with Column() maps to a table column.

WHY SEPARATE MODELS FROM SCHEMAS?
  Models (here) represent the database structure.
  Schemas (schemas/user_schema.py) represent what the API accepts/returns.
  Keeping them separate lets you:
    - Expose only safe fields in the API (e.g. never return 'password')
    - Have different validation rules for DB vs API
    - Evolve DB structure independently of the API contract

INTERVIEW TALKING POINT:
  "I followed the repository pattern — models are responsible for DB shape,
  schemas handle API validation, and services contain business logic.
  This separation makes each layer independently testable."
"""

from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func

from app.database.db import Base


class User(Base):
    """
    Represents a system operator or administrator.

    Table name: users
    Columns:
      id         — Auto-incrementing primary key
      name       — Display name
      email      — Unique login identifier
      password   — bcrypt hash of the password (NEVER store plaintext!)
      role       — "admin" can manage users; "operator" manages incidents
      is_active  — Soft delete flag (deactivate without deleting records)
      created_at — Auto-set on INSERT by the database server
      updated_at — Auto-set on UPDATE by the database server
    """

    __tablename__ = "users"

    # Primary key: auto-incremented by PostgreSQL SERIAL
    id = Column(Integer, primary_key=True, index=True)

    # VARCHAR(100) — max 100 chars; nullable=False enforces NOT NULL at DB level
    name = Column(String(100), nullable=False)

    # unique=True creates a UNIQUE INDEX — fast lookup and prevents duplicates
    # index=True adds a secondary index to speed up WHERE email = '...' queries
    email = Column(String(150), unique=True, index=True, nullable=False)

    # Store only the bcrypt hash — 60-char string for bcrypt output
    # bcrypt is preferred over MD5/SHA1 because it's intentionally slow,
    # making brute-force attacks computationally expensive.
    password = Column(String(255), nullable=False)

    # Role-based access control (RBAC): simple string-based roles.
    # In a larger system you'd use a separate roles/permissions table.
    class UserRole(str, enum.Enum):
      admin = "admin"
      operator = "operator"

    role = Column(Enum(UserRole, name="user_role"), default=UserRole.operator, nullable=False)

    # Soft delete: set is_active=False instead of DELETE-ing the row.
    # This preserves audit history and avoids foreign key issues.
    is_active = Column(Boolean, default=True, nullable=False)

    # server_default=func.now() sets the default AT THE DATABASE LEVEL,
    # not in Python. This is more reliable for distributed systems.
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # onupdate=func.now() tells SQLAlchemy to set this on every UPDATE.
    updated_at = Column(
        DateTime(timezone=True),
      onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

    # Tracks when the user last successfully authenticated
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        """String representation useful for debugging in logs."""
        return f"<User id={self.id} email={self.email!r} role={self.role!r}>"
    