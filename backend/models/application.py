from sqlalchemy import Boolean, Column, Date, DateTime, Integer, Numeric, String
from sqlalchemy.sql import func

from db.database import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, nullable=False)
    title = Column(String, nullable=False)
    location = Column(String)
    salary_min = Column(Numeric)
    salary_max = Column(Numeric)
    work_type = Column(String)        # remote / hybrid / onsite
    platform = Column(String)         # LinkedIn / Greenhouse / company site / etc.
    source_url = Column(String)
    applied_date = Column(Date)
    status = Column(String, default="Applied")
    pinned = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
