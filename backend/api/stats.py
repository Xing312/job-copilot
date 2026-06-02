from collections import Counter
from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from models.application import Application

router = APIRouter()

STATUS_ORDER = ["Applied", "OA", "Phone Screen", "Interview", "Offer", "Rejected", "Ghosted"]


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _subtract_months(d: date, n: int) -> date:
    month = d.month - n
    year = d.year
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


@router.get("/stats")
def get_stats(
    period: Literal["day", "week", "month"] = "day",
    db: Session = Depends(get_db),
):
    apps = db.query(Application).all()
    total = len(apps)

    status_counts = Counter(a.status for a in apps)

    by_status = [
        {"name": s, "value": status_counts[s]}
        for s in STATUS_ORDER
        if status_counts.get(s, 0) > 0
    ]

    today = date.today()

    date_counts: Counter = Counter()
    for a in apps:
        d = a.applied_date or (a.created_at.date() if a.created_at else None)
        if d:
            if period == "day":
                date_counts[d] += 1
            elif period == "week":
                date_counts[_week_start(d)] += 1
            else:
                date_counts[_month_start(d)] += 1

    if period == "day":
        by_period = [
            {
                "period": (today - timedelta(days=i)).strftime("%m/%d"),
                "count": date_counts.get(today - timedelta(days=i), 0),
            }
            for i in range(29, -1, -1)
        ]
    elif period == "week":
        by_period = [
            {
                "period": (_week_start(today) - timedelta(weeks=i)).strftime("%m/%d"),
                "count": date_counts.get(_week_start(today) - timedelta(weeks=i), 0),
            }
            for i in range(11, -1, -1)
        ]
    else:
        by_period = [
            {
                "period": _subtract_months(today, i).strftime("%b '%y"),
                "count": date_counts.get(_subtract_months(today, i), 0),
            }
            for i in range(11, -1, -1)
        ]

    platform_counts = Counter(a.platform for a in apps if a.platform)
    by_platform = [{"name": k, "value": v} for k, v in platform_counts.most_common(6)]

    work_type_counts = Counter(a.work_type for a in apps if a.work_type)
    by_work_type = [{"name": k, "value": v} for k, v in work_type_counts.most_common()]

    responded = sum(1 for a in apps if a.status not in ("Applied", "Ghosted"))

    return {
        "total": total,
        "offers": status_counts.get("Offer", 0),
        "interviews": status_counts.get("Interview", 0),
        "response_rate": round(responded / total * 100, 1) if total else 0,
        "by_status": by_status,
        "by_period": by_period,
        "by_platform": by_platform,
        "by_work_type": by_work_type,
    }
