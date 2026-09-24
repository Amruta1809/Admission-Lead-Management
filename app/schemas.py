"""Pydantic v2 request/response schemas."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from .models import LeadStatus

FollowUpType = Literal["call", "whatsapp", "visit", "email"]


class CoursePreference(BaseModel):
    course_id: int
    priority: int = Field(default=1, ge=1)


class LeadCreate(BaseModel):
    name: str = Field(min_length=1)
    phone: str
    email: EmailStr | None = None
    source_id: int
    courses: list[CoursePreference] = Field(default_factory=list)
    assigned_to: int | None = None  # optional manual assignment; otherwise auto


class StatusUpdate(BaseModel):
    status: LeadStatus
    lost_reason: str | None = None
    actor_id: int | None = None

    @model_validator(mode="after")
    def lost_needs_reason(self):
        if self.status == LeadStatus.LOST and not self.lost_reason:
            raise ValueError("lost_reason is required when marking a lead as lost")
        return self


class Reassign(BaseModel):
    counsellor_id: int
    actor_id: int | None = None


class FollowUpCreate(BaseModel):
    due_at: datetime
    type: FollowUpType
    note: str | None = None
    created_by: int | None = None


class FollowUpUpdate(BaseModel):
    status: Literal["done", "cancelled"]
    note: str | None = None


class FollowUpOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    lead_id: int
    due_at: datetime
    type: str
    note: str | None
    status: str
    completed_at: datetime | None


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    action: str
    old_value: str | None
    new_value: str | None
    actor_id: int | None
    created_at: datetime


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    phone: str
    email: str | None
    source_id: int
    status: str
    lost_reason: str | None
    assigned_to: int | None
    created_at: datetime
    last_activity_at: datetime


class LeadCreateResult(BaseModel):
    lead: LeadOut
    duplicate: bool  # True if an existing lead with the same phone was returned
