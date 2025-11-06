from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from app.models.schemas import AcceptImprovementRequest, AnalyzeRequest
from app.services.parser import OpenAPIParser
from app.services.docscore import DocScoreEngine
from app.services.ai_improver import AIImprover
from app.services.duplicate_detector import DuplicateDetector
from app.services.compliance import ComplianceChecker
from app.services.timeline import TimelineTracker
from app.config import get_settings
import uuid
import json
import tempfile
import os
from datetime import datetime

router = APIRouter()
settings = get_settings()

# Initialize services
parser = OpenAPIParser()
docscore_engine = DocScoreEngine()
ai_improver = AIImprover(settings.OPENAI_API_KEY, settings.OPENAI_MODEL)
duplicate_detector = DuplicateDetector(settings.OPENAI_API_KEY, settings.EMBEDDING_MODEL)
compliance_checker = ComplianceChecker()
timeline_tracker = TimelineTracker()

# Temporary in-memory DB (replace with SQLAlchemy later)
api_database = {}

# =====================================================
#  📊 Analyze OpenAPI spec
# =====================================================
@router.post("/analyze")
async def analyze_api(
    file: UploadFile = File(...),
    api_name: str = None,
    owner: str = None
):
    try:
        content = await file.read()
        spec_text = content.decode("utf-8")
        spec = parser.parse(spec_text)

        if not parser.validate(spec):
            raise HTTPException(status_code=400, detail="Invalid OpenAPI spec")

        # 🧠 Reuse api_id if already analyzed before
        api_name = api_name or spec.get("info", {}).get("title", "Unnamed API")
        existing_api = next((v for v in api_database.values() if v["name"] == api_name), None)
        api_id = existing_api["id"] if existing_api else str(uuid.uuid4())

        # Calculate score
        doc_score = docscore_engine.calculate(spec, api_id=api_id)

        # Generate improvements only for not-already-improved fields
        improvements = ai_improver.generate_improvements(spec)

        duplicates = duplicate_detector.find_duplicates(spec, list(api_database.values()))
        compliance_issues = compliance_checker.check(spec)

        timeline = timeline_tracker.get_timeline(None, api_id)
        timeline = timeline_tracker.project_improvement(timeline, doc_score["potential_score"])

        api_database[api_id] = {
            "id": api_id,
            "name": api_name,
            "owner": owner or "Unknown",
            "spec": spec,
            "doc_score": doc_score,
            "improvements": improvements,
            "duplicates": duplicates,
            "compliance_issues": compliance_issues,
            "updated_at": datetime.now().isoformat(),
        }

        return {
            "api_id": api_id,
            "api_name": api_name,
            "doc_score": doc_score,
            "improvements": improvements,
            "duplicates": duplicates,
            "compliance_issues": compliance_issues,
            "timeline": timeline,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

# =====================================================
#  ✅ Accept Improvements
# =====================================================
@router.post("/analyze/accept-improvements")
async def accept_improvements(request: AcceptImprovementRequest):
    """Apply accepted AI improvements and re-evaluate."""
    try:
        api_id = request.api_id
        if api_id not in api_database:
            raise HTTPException(status_code=404, detail="API not found")

        api_data = api_database[api_id]
        spec = api_data["spec"]
        improvements = api_data["improvements"]
        accepted_count = 0

        for improvement in improvements:
            if improvement.get("id") in request.improvement_ids:
                endpoint_key = improvement["endpoint"].split(" ", 1)
                if len(endpoint_key) != 2:
                    continue

                method, path = endpoint_key
                method = method.lower()
                if path not in spec.get("paths", {}) or method not in spec["paths"][path]:
                    continue

                # Apply improvement
                if improvement["field"] == "description":
                    spec["paths"][path][method]["description"] = improvement["after"]
                elif improvement["field"] == "example":
                    spec["paths"][path][method].setdefault(
                        "requestBody", {"content": {"application/json": {}}}
                    )
                    spec["paths"][path][method]["requestBody"]["content"]["application/json"]["example"] = json.loads(
                        improvement["after"]
                    )

                accepted_count += 1

        # 💾 Save applied improvements so they don't appear again
        api_data["improvements"] = [
            imp for imp in improvements if imp["id"] not in request.improvement_ids
        ]

        # Recalculate doc score
        new_score = docscore_engine.calculate(spec, api_id=api_id)
        api_data["spec"] = spec
        api_data["doc_score"] = new_score
        api_data["updated_at"] = datetime.now().isoformat()

        # 💾 Persist improved JSON for download
        file_path = os.path.join(
            tempfile.gettempdir(), f"{api_data['name'].replace(' ', '_')}_improved.json"
        )
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2)

        return {
            "message": f"✅ {accepted_count} improvements applied.",
            "new_doc_score": new_score["score"],
            "potential_score": new_score["potential_score"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to accept improvements: {e}")

# =====================================================
#  ⬇️ Download Improved Spec
# =====================================================
@router.get("/analyze/{api_id}/download")
async def download_improved_spec(api_id: str):
    """Allow user to download the latest improved OpenAPI spec as JSON (with version + timestamp)."""
    if api_id not in api_database:
        raise HTTPException(status_code=404, detail="API not found")

    api_data = api_database[api_id]

    # Increment version number each time the user downloads
    version = api_data.get("version", 1.0)
    new_version = round(version + 0.1, 1)
    api_data["version"] = new_version

    spec = api_data["spec"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    tmp_dir = tempfile.gettempdir()
    file_name = f"{api_data['name'].replace(' ', '_')}_v{new_version}_improved_{timestamp}.json"
    file_path = os.path.join(tmp_dir, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)

    return FileResponse(
        path=file_path,
        media_type="application/json",
        filename=file_name,
    )
# =====================================================
#  📜 Get Timeline
# =====================================================
@router.get("/analyze/{api_id}/timeline")
async def get_api_timeline(api_id: str):
    """Return API documentation improvement timeline."""
    if api_id not in api_database:
        raise HTTPException(status_code=404, detail="API not found")

    api_data = api_database[api_id]
    timeline = api_data["doc_score"].get("history", [])
    return {"timeline": timeline}

# =====================================================
#  🧾 Analyze from raw text
# =====================================================
@router.post("/analyze/text")
async def analyze_text(request: AnalyzeRequest):
    """Analyze API documentation directly from raw OpenAPI text."""
    try:
        spec = parser.parse(request.spec_content)
        if not parser.validate(spec):
            raise HTTPException(status_code=400, detail="Invalid OpenAPI specification")

        api_id = str(uuid.uuid4())
        doc_score = docscore_engine.calculate(spec, api_id=api_id)
        improvements = ai_improver.generate_improvements(spec)
        duplicates = duplicate_detector.find_duplicates(spec, list(api_database.values()))
        compliance_issues = compliance_checker.check(spec)
        timeline = timeline_tracker.project_improvement([], doc_score["potential_score"])

        api_database[api_id] = {
            "id": api_id,
            "name": request.api_name,
            "owner": request.owner,
            "spec": spec,
            "doc_score": doc_score,
            "improvements": improvements,
            "duplicates": duplicates,
            "compliance_issues": compliance_issues,
        }

        return {
            "api_id": api_id,
            "api_name": request.api_name,
            "doc_score": doc_score,
            "improvements": improvements,
            "duplicates": duplicates,
            "compliance_issues": compliance_issues,
            "timeline": timeline
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
