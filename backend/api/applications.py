from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from models.application import Application

router = APIRouter()

VALID_STATUSES = {"Applied", "OA", "Phone Screen", "Interview", "Offer", "Rejected", "Ghosted"}


class ApplicationCreate(BaseModel):
    company: str
    title: str
    location: str | None = None
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    work_type: str | None = None
    platform: str | None = None
    source_url: str | None = None
    applied_date: date | None = None
    status: str | None = "Applied"


class ApplicationOut(BaseModel):
    id: int
    company: str
    title: str
    location: str | None
    salary_min: Decimal | None
    salary_max: Decimal | None
    work_type: str | None
    platform: str | None
    source_url: str | None
    applied_date: date | None
    status: str
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class StatusUpdate(BaseModel):
    status: str


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)):
    return db.query(Application).order_by(Application.created_at.desc()).all()


@router.post("/applications", response_model=ApplicationOut, status_code=201)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    app = Application(**payload.model_dump())
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.get("/applications/{app_id}", response_model=ApplicationOut)
def get_application(app_id: int, db: Session = Depends(get_db)):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.patch("/applications/{app_id}/status", response_model=ApplicationOut)
def update_status(app_id: int, payload: StatusUpdate, db: Session = Depends(get_db)):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status: {payload.status}")
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    app.status = payload.status
    db.commit()
    db.refresh(app)
    return app


@router.put("/applications/{app_id}", response_model=ApplicationOut)
def update_application(app_id: int, payload: ApplicationCreate, db: Session = Depends(get_db)):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    for field, value in payload.model_dump().items():
        setattr(app, field, value)
    db.commit()
    db.refresh(app)
    return app


@router.delete("/applications/{app_id}", status_code=204)
def delete_application(app_id: int, db: Session = Depends(get_db)):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    db.delete(app)
    db.commit()
