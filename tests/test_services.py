from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import Base, FollowUp, Lead, LeadActivity, LeadSource, User
from app.schemas import FollowUpCreate, LeadCreate, Reassign, StatusUpdate
from app.services import add_follow_up, change_status, create_lead, dashboard, reassign


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    session.add_all(
        [
            User(id=1, name="Manager", role="manager", is_active=True),
            User(id=2, name="Active", role="counsellor", is_active=True),
            User(id=3, name="Inactive", role="counsellor", is_active=False),
            LeadSource(id=1, name="Website"),
        ]
    )
    session.commit()
    yield session
    session.close()
    engine.dispose()


def lead_payload(phone: str = "+91 98765 43210") -> LeadCreate:
    return LeadCreate(name="Test Lead", phone=phone, source_id=1)


def test_duplicate_phone_formats_return_same_lead(db):
    first, duplicate = create_lead(db, lead_payload())
    second, is_duplicate = create_lead(db, lead_payload("09876543210"))
    assert duplicate is False
    assert is_duplicate is True
    assert first.id == second.id
    assert db.scalar(select(LeadActivity).where(LeadActivity.action == "duplicate_detected"))


def test_invalid_status_jump_is_rejected(db):
    lead, _ = create_lead(db, lead_payload())
    with pytest.raises(ValueError, match="Cannot change status"):
        change_status(db, lead.id, StatusUpdate(status="converted"))


def test_lost_requires_reason(db):
    with pytest.raises(ValueError, match="lost_reason"):
        StatusUpdate(status="lost")


def test_inactive_reassignment_is_rejected(db):
    lead, _ = create_lead(db, lead_payload())
    with pytest.raises(ValueError, match="active counsellor"):
        reassign(db, lead.id, Reassign(counsellor_id=3))


def test_converted_lead_cannot_change_status(db):
    lead, _ = create_lead(db, lead_payload())
    lead.status = "converted"
    db.commit()
    with pytest.raises(ValueError, match="Cannot change status"):
        change_status(db, lead.id, StatusUpdate(status="contacted"))


def test_overdue_follow_up_is_reported(db):
    lead, _ = create_lead(db, lead_payload())
    add_follow_up(
        db,
        lead.id,
        FollowUpCreate(
            due_at=datetime.now(timezone.utc) - timedelta(days=1),
            type="call",
        ),
    )
    report = dashboard(db)
    assert len(report["overdue_follow_ups"]) == 1