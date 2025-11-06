from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import analysis

app = FastAPI(
    title="DocuGenAI+",
    description="AI-driven API Documentation Quality & Improvement Engine",
    version="1.0.0"
)

# Allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router, prefix="/api/v1", tags=["Analysis"])

@app.get("/")
def root():
    return {"message": "DocuGenAI+ backend running ✅"}
