"""Custom compliance framework models."""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class CustomFramework(Base, UUIDMixin, TimestampMixin):
    """User-defined compliance framework.

    Organisations can create their own frameworks with custom controls
    and run AI analysis against them exactly like built-in frameworks.
    """

    __tablename__ = "custom_frameworks"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    controls: Mapped[list["CustomControl"]] = relationship(
        "CustomControl",
        back_populates="framework",
        cascade="all, delete-orphan",
        order_by="CustomControl.order_index",
    )

    def __repr__(self) -> str:
        return f"<CustomFramework(id={self.id}, name={self.name})>"


class CustomControl(Base, UUIDMixin, TimestampMixin):
    """A single control within a custom framework."""

    __tablename__ = "custom_controls"

    framework_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("custom_frameworks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    framework: Mapped["CustomFramework"] = relationship(
        "CustomFramework", back_populates="controls"
    )

    def __repr__(self) -> str:
        return f"<CustomControl(id={self.id}, control_id={self.control_id}, name={self.name})>"
