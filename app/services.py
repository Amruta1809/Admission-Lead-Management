from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    ALLOWED_TRANSITIONS,
    FollowUp,
    Lead,
    LeadActivity,
    LeadCourse,
    LeadSource,
    LeadStatus,
    User,
    can_transition,
    normalize_phone,
)
from .schemas import FollowUpCreate, FollowUpUpdate, LeadCreate, Reassign, StatusUpdate

OPEN_STATUSES = {
    LeadStatus.NEW.value,
    LeadStatus.CONTACTED.value,
    LeadStatus.INTERESTED.value,
    LeadStatus.FOLLOW_UP.value,
    LeadStatus.APPLIED.value,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _active_counsellor(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None or user.role != "counsellor" or not user.is_active:
        raise ValueError("Target must be an active counsellor")
    return user


def _least_loaded_counsellor(db: Session) -> User | None:
    counsellors = list(
        db.scalars(
            select(User)
            .where(User.role == "counsellor", User.is_active.is_(True))
            .order_by(User.id)
        )
    )
    if not counsellors:
        return None
    counts = {
        user.id: db.scalar(
            select(func.count(Lead.id)).where(
                Lead.assigned_to == user.id,
                Lead.status.in_(OPEN_STATUSES),
            )
        )
        or 0
        for user in counsellors
    }
    return min(counsellors, key=lambda user: (counts[user.id], user.id))


def create_lead(db: Session, payload: LeadCreate) -> tuple[Lead, bool]:
    phone_normalized = normalize_phone(payload.phone)
    existing = db.scalar(select(Lead).where(Lead.phone_normalized == phone_normalized))
    if existing is not None:
        db.add(
            LeadActivity(
                lead_id=existing.id,
                action="duplicate_detected",
                new_value=payload.phone,
            )
        )
        db.commit()
        db.refresh(existing)
        return existing, True

    assigned_to = payload.assigned_to
    if assigned_to is not None:
        _active_counsellor(db, assigned_to)
    else:
        counsellor = _least_loaded_counsellor(db)
        assigned_to = counsellor.id if counsellor else None

    lead = Lead(
        name=payload.name,
        phone=payload.phone,
        phone_normalized=phone_normalized,
        email=payload.email,
        source_id=payload.source_id,
        assigned_to=assigned_to,
    )
    lead.courses = [
        LeadCourse(course_id=course.course_id, priority=course.priority)
        for course in payload.courses
    ]
    db.add(lead)
    db.flush()
    db.add(LeadActivity(lead_id=lead.id, action="created"))
    db.commit()
    db.refresh(lead)
    return lead, False


def change_status(db: Session, lead_id: int, payload: StatusUpdate) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise LookupError("Lead not found")
    old_status = LeadStatus(lead.status)
    if not can_transition(old_status, payload.status):
        allowed = sorted(status.value for status in ALLOWED_TRANSITIONS[old_status])
        raise ValueError(f"Cannot change status from {old_status.value}; allowed: {allowed}")
    lead.status = payload.status.value
    lead.lost_reason = payload.lost_reason if payload.status == LeadStatus.LOST else None
    lead.last_activity_at = _now()
    db.add(
        LeadActivity(
            lead_id=lead.id,
            actor_id=payload.actor_id,
            action="status_changed",
            old_value=old_status.value,
            new_value=payload.status.value,
        )
    )
    db.commit()
    db.refresh(lead)
    return lead


def reassign(db: Session, lead_id: int, payload: Reassign) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise LookupError("Lead not found")
    _active_counsellor(db, payload.counsellor_id)
    old_assignee = str(lead.assigned_to) if lead.assigned_to else None
    lead.assigned_to = payload.counsellor_id
    lead.last_activity_at = _now()
    db.add(
        LeadActivity(
            lead_id=lead.id,
            actor_id=payload.actor_id,
            action="reassigned",
            old_value=old_assignee,
            new_value=str(payload.counsellor_id),
        )
    )
    db.commit()
    db.refresh(lead)
    return lead


def delete_lead(db: Session, lead_id: int) -> None:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise LookupError("Lead not found")
    db.delete(lead)
    db.commit()


def add_follow_up(db: Session, lead_id: int, payload: FollowUpCreate) -> FollowUp:
    if db.get(Lead, lead_id) is None:
        raise LookupError("Lead not found")
    follow_up = FollowUp(lead_id=lead_id, **payload.model_dump())
    db.add(follow_up)
    db.flush()
    db.add(
        LeadActivity(
            lead_id=lead_id,
            actor_id=payload.created_by,
            action="follow_up_added",
            new_value=payload.type,
        )
    )
    db.commit()
    db.refresh(follow_up)
    return follow_up


def update_follow_up(db: Session, follow_up_id: int, payload: FollowUpUpdate) -> FollowUp:
    follow_up = db.get(FollowUp, follow_up_id)
    if follow_up is None:
        raise LookupError("Follow-up not found")
    if follow_up.status != "pending":
        raise ValueError("Follow-up is already closed")
    follow_up.status = payload.status
    follow_up.note = payload.note or follow_up.note
    follow_up.completed_at = _now() if payload.status == "done" else None
    db.add(
        LeadActivity(
            lead_id=follow_up.lead_id,
            action="follow_up_updated",
            old_value="pending",
            new_value=payload.status,
        )
    )
    db.commit()
    db.refresh(follow_up)
    return follow_up


def dashboard(db: Session, stale_days: int = 7) -> dict:
    leads = list(db.scalars(select(Lead)))
    users = {user.id: user for user in db.scalars(select(User))}
    sources = {source.id: source.name for source in db.scalars(select(LeadSource))}
    now = _now()

    status_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    counsellor_counts: dict[str, int] = {}
    ageing = {"0-2": 0, "3-7": 0, "8-14": 0, "15+": 0}
    for lead in leads:
        status_counts[lead.status] = status_counts.get(lead.status, 0) + 1
        source_name = sources.get(lead.source_id, str(lead.source_id))
        source_counts[source_name] = source_counts.get(source_name, 0) + 1
        counsellor = users.get(lead.assigned_to)
        counsellor_name = counsellor.name if counsellor else "Unassigned"
        counsellor_counts[counsellor_name] = counsellor_counts.get(counsellor_name, 0) + 1
        created_at = _utc(lead.created_at)
        age = max(0, (now - created_at).days) if created_at else 0
        bucket = "0-2" if age <= 2 else "3-7" if age <= 7 else "8-14" if age <= 14 else "15+"
        ageing[bucket] += 1

    overdue = list(
        db.scalars(
            select(FollowUp).where(
                FollowUp.status == "pending", FollowUp.due_at < now
            )
        )
    )
    stale_cutoff = now - timedelta(days=stale_days)
    stale = [
        lead
        for lead in leads
        if _utc(lead.last_activity_at) and _utc(lead.last_activity_at) < stale_cutoff
    ]
    conversion = {}
    for user in users.values():
        if user.role != "counsellor":
            continue
        assigned = [lead for lead in leads if lead.assigned_to == user.id]
        converted = sum(lead.status == LeadStatus.CONVERTED.value for lead in assigned)
        conversion[user.name] = round(converted / len(assigned) * 100, 1) if assigned else 0

    return {
        "total_leads": len(leads),
        "by_status": status_counts,
        "by_source": source_counts,
        "by_counsellor": counsellor_counts,
        "conversion_rate_by_counsellor": conversion,
        "ageing": ageing,
        "overdue_follow_ups": overdue,
        "stale_leads": stale,
    }