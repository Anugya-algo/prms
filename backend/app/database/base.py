"""
SQLAlchemy declarative base.

All ORM models must inherit from `Base` so that Alembic can discover them
via `Base.metadata` and auto-generate migration scripts.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Project-wide SQLAlchemy declarative base.

    Usage::

        from app.database.base import Base

        class MyModel(Base):
            __tablename__ = "my_table"
            ...
    """
