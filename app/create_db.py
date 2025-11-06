from app.database.database import Base, engine
from app.models.entities import APISpecEntry, ImprovementEntry
Base.metadata.create_all(bind=engine)