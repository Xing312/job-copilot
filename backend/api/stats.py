from collections import Counter
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from models.application import Application

router = APIRouter()

STATUS_ORDER = ["Applied", "OA", "Phone Screen", "Interview", "Offer", "Rejected", "Ghosted"]


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    apps = db.query(Application).all()
    total = len(apps)

    status_counts = Counter(a.status for a in apps)

    # Status breakdown in canonical order
    by_status = [
        {"name": s, "value": status_counts[s]}
        for s in STATUS_ORDER
        if status_counts.get(s, 0) > 0
    ]

    # Weekly trend — last 12 weeks
    week_counts: Counter = Counter()
    for a in apps:
        d = a.applied_date or (a.created_at.date() if a.created_at else None)
        if d:
            week_counts[_week_start(d)] += 1

    today = date.today()
    by_week = [
        {
            "week": (_week_start(today) - timedelta(weeks=i)).strftime("%m/%d"),
            "count": week_counts.get(_week_start(today) - timedelta(weeks=i), 0),
        }
        for i in range(11, -1, -1)
    ]

    # Platform breakdown (top 6)
    platform_counts = Counter(a.platform for a in apps if a.platform)
    by_platform = [{"name": k, "value": v} for k, v in platform_counts.most_common(6)]

    # Work type breakdown
    work_type_counts = Counter(a.work_type for a in apps if a.work_type)
    by_work_type = [{"name": k, "value": v} for k, v in work_type_counts.most_common()]

    responded = sum(1 for a in apps if a.status not in ("Applied", "Ghosted"))

    return {
        "total": total,
        "offers": status_counts.get("Offer", 0),
        "interviews": status_counts.get("Interview", 0),
        "response_rate": round(responded / total * 100, 1) if total else 0,
        "by_status": by_status,
        "by_week": by_week,
        "by_platform": by_platform,
        "by_work_type": by_work_type,
    }
