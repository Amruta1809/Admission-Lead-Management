from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .database import get_db
from .services import dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(stale_days: int = Query(default=7, ge=1), db: Session = Depends(get_db)):
    return dashboard(db, stale_days)