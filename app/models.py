"""SQLAlchemy models + business rules that don't belong in the routes."""
import re
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    FOLLOW_UP = "follow_up"
    APPLIED = "applied"
    CONVERTED = "converted"
    LOST = "lost"


# Single source of truth for allowed status changes.
# 'lost' is reachable from any open state; a lost lead can be reopened as 'contacted'.
ALLOWED_TRANSITIONS: dict[LeadStatus, set[LeadStatus]] = {
    LeadStatus.NEW:        {LeadStatus.CONTACTED, LeadStatus.LOST},
    LeadStatus.CONTACTED:  {LeadStatus.INTERESTED, LeadStatus.FOLLOW_UP, LeadStatus.LOST},
    LeadStatus.INTERESTED: {LeadStatus.FOLLOW_UP, LeadStatus.APPLIED, LeadStatus.LOST},
    LeadStatus.FOLLOW_UP:  {LeadStatus.INTERESTED, LeadStatus.APPLIED, LeadStatus.LOST},
    LeadStatus.APPLIED:    {LeadStatus.CONVERTED, LeadStatus.LOST},
    LeadStatus.CONVERTED:  set(),  # final
    LeadStatus.LOST:       {LeadStatus.CONTACTED},
}


def can_transition(old: LeadStatus, new: LeadStatus) -> bool:
    return new in ALLOWED_TRANSITIONS[old]


def normalize_phone(raw: str) -> str:
    """Keep digits only, then the last 10 (drops +91 / leading 0). Used for duplicate detection."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) < 10:
        raise ValueError("Phone number must have at least 10 digits")
    return digits[-10:]


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String)  # 'counsellor' | 'manager'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class LeadSource(Base):
    __tablename__ = "lead_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)


class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    phone: Mapped[str] = mapped_column(Text)
    phone_normalized: Mapped[str] = mapped_column(Text, unique=True)
    email: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("lead_sources.id"))
    status: Mapped[str] = mapped_column(String, default=LeadStatus.NEW.value)
    lost_reason: Mapped[str | None] = mapped_column(Text)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source: Mapped[LeadSource] = relationship()
    counsellor: Mapped[User | None] = relationship()
    courses: Mapped[list["LeadCourse"]] = relationship(cascade="all, delete-orphan")
    follow_ups: Mapped[list["FollowUp"]] = relationship(cascade="all, delete-orphan")
    activities: Mapped[list["LeadActivity"]] = relationship(
        cascade="all, delete-orphan", order_by="LeadActivity.created_at"
    )


class LeadCourse(Base):
    __tablename__ = "lead_courses"
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), primary_key=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)


class FollowUp(Base):
    __tablename__ = "follow_ups"
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    type: Mapped[str] = mapped_column(String)  # call | whatsapp | visit | email
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending | done | cancelled
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LeadActivity(Base):
    __tablename__ = "lead_activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
