"""ORM model for administrative_units table (created in migration 0003)."""

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class AdministrativeUnit(Base):
    __tablename__ = "administrative_units"

    code = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    administrative_level = Column(String(20), nullable=False)
    parent_code = Column(
        String(20),
        ForeignKey("administrative_units.code"),
        nullable=True,
    )

    # Self-referential relationship for hierarchy traversal
    children = relationship(
        "AdministrativeUnit",
        foreign_keys=[parent_code],
        backref="parent",
        lazy="select",
    )
