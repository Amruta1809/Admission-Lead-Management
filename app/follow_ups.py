from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import FollowUp, Lead
from .schemas import FollowUpCreate, FollowUpOut, FollowUpUpdate
from .services import add_follow_up, update_follow_up

router = APIRouter(tags=["follow-ups"])


@router.get("/leads/{lead_id}/follow-ups", response_model=list[FollowUpOut])
def list_follow_ups(lead_id: int, db: Session = Depends(get_db)) -> list[FollowUp]:
    if db.get(Lead, lead_id) is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return list(db.scalars(select(FollowUp).where(FollowUp.lead_id == lead_id).order_by(FollowUp.due_at)))


@router.post("/leads/{lead_id}/follow-ups", response_model=FollowUpOut, status_code=status.HTTP_201_CREATED)
def create_follow_up(lead_id: int, payload: FollowUpCreate, db: Session = Depends(get_db)) -> FollowUp:
    try:
        return add_follow_up(db, lead_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/follow-ups/{follow_up_id}", response_model=FollowUpOut)
def update_follow_up(follow_up_id: int, payload: FollowUpUpdate, db: Session = Depends(get_db)) -> FollowUp:
    try:
        return update_follow_up(db, follow_up_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc