from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import Lead, LeadStatus, User
from .schemas import LeadCreate, LeadCreateResult, LeadOut, Reassign, StatusUpdate
from .services import change_status, create_lead, reassign
from .services import change_status, create_lead, delete_lead, reassign

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=list[LeadOut])
def list_leads(status_filter: LeadStatus | None = Query(default=None, alias="status"), source_id: int | None = None, assigned_to: int | None = None, db: Session = Depends(get_db)) -> list[Lead]:
    query = select(Lead).order_by(Lead.created_at.desc())
    if status_filter is not None:
        query = query.where(Lead.status == status_filter.value)
    if source_id is not None:
        query = query.where(Lead.source_id == source_id)
    if assigned_to is not None:
        query = query.where(Lead.assigned_to == assigned_to)
    return list(db.scalars(query))


@router.post("", response_model=LeadCreateResult, status_code=status.HTTP_201_CREATED)
def create(payload: LeadCreate, db: Session = Depends(get_db)) -> LeadCreateResult:
    try:
        lead, duplicate = create_lead(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LeadCreateResult(lead=lead, duplicate=duplicate)


@router.patch("/{lead_id}/status", response_model=LeadOut)
def update_status(lead_id: int, payload: StatusUpdate, db: Session = Depends(get_db)) -> Lead:
    try:
        return change_status(db, lead_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/{lead_id}/reassign", response_model=LeadOut)
def reassign_lead(lead_id: int, payload: Reassign, db: Session = Depends(get_db)) -> Lead:
    try:
        return reassign(db, lead_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_lead(lead_id: int, db: Session = Depends(get_db)) -> None:
    try:
        delete_lead(db, lead_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{lead_id}/activities")
def activities(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return list(lead.activities)


@router.get("/counsellors")
def counsellors(db: Session = Depends(get_db)):
    return list(db.scalars(select(User).where(User.role == "counsellor")))