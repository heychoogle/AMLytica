from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

class Job(Base):
    __tablename__ = "jobs"
    
    job_id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, index=True)
    filename = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    current_status = Column(String, default="PENDING")
    events = relationship("JobEvent", back_populates="job", cascade="all, delete-orphan")

class JobEvent(Base):
    __tablename__ = "job_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.job_id"))
    status = Column(String) 
    message = Column(Text, nullable=True)
    worker_name = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="events")

class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(Text, nullable=True)