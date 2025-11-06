from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class APISpecEntry(Base):
    __tablename__ = "api_specs"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    owner = Column(String)
    spec_json = Column(Text)
    score = Column(Integer)
    potential_score = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    improvements = relationship("ImprovementEntry", back_populates="api", cascade="all, delete-orphan")


class ImprovementEntry(Base):
    __tablename__ = "improvement_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    api_id = Column(String, ForeignKey("api_specs.id"))
    endpoint = Column(String)
    field = Column(String)
    before = Column(Text)
    after = Column(Text)
    reason = Column(Text)
    priority = Column(String)

    api = relationship("APISpecEntry", back_populates="improvements")
