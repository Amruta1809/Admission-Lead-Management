from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from .database import SessionLocal, init_db
from .models import Course, Lead, LeadSource, User
from .schemas import CoursePreference, LeadCreate
from .services import create_lead


def seed() -> None:
    init_db()
    with SessionLocal() as db:
        if not db.scalar(select(User).limit(1)):
            db.add_all(
                [
                    User(name="Meera Kulkarni", role="manager"),
                    User(name="Rohan Patil", role="counsellor"),
                    User(name="Sneha Joshi", role="counsellor"),
                    User(name="Aditya More", role="counsellor"),
                ]
            )
        if not db.scalar(select(LeadSource).limit(1)):
            db.add_all(LeadSource(name=name) for name in ["Website", "Walk-in", "Phone call", "WhatsApp", "Education fair", "Campaign"])
        if not db.scalar(select(Course).limit(1)):
            db.add_all(Course(name=name) for name in ["B.Tech Computer Science", "B.Tech Mechanical", "BBA", "MBA", "B.Com"])
        db.commit()

        if db.scalar(select(Lead).limit(1)):
            print("Seed skipped: leads already exist.")
            return

        sources = list(db.scalars(select(LeadSource).order_by(LeadSource.id)))
        courses = list(db.scalars(select(Course).order_by(Course.id)))
        for index in range(30):
            lead, _ = create_lead(
                db,
                LeadCreate(
                    name=f"Demo Lead {index + 1}",
                    phone=f"+91 90000 {index:05d}",
                    email=f"lead{index + 1}@example.com",
                    source_id=sources[index % len(sources)].id,
                    courses=[CoursePreference(course_id=courses[index % len(courses)].id)],
                ),
            )
            if index % 7 == 0:
                lead.created_at = datetime.now(timezone.utc) - timedelta(days=15)
                db.commit()
        print("Seeded 30 demo leads.")


if __name__ == "__main__":
    seed()