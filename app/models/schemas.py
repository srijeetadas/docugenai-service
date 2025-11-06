from pydantic import BaseModel
from typing import List
from datetime import datetime
from enum import Enum


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class APIStatus(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    NEEDS_IMPROVEMENT = "needs-improvement"
    CRITICAL = "critical"


class AnalyzeRequest(BaseModel):
    api_name: str
    owner: str
    spec_content: str


class AcceptImprovementRequest(BaseModel):
    api_id: str
    improvement_ids: List[int]


class DocScoreResponse(BaseModel):
    score: int
    potential_score: int
    missing_descriptions: int
    missing_examples: int
    vague_descriptions: int


class ImprovementItem(BaseModel):
    id: int
    endpoint: str
    field: str
    before: str
    after: str
    reason: str
    priority: Priority


class DuplicateItem(BaseModel):
    name: str
    api_id: str
    overlap: int
    endpoints: int
    recommendation: str
    details: List[str]


class ComplianceIssue(BaseModel):
    id: int
    field: str
    endpoint: str
    severity: Severity
    issue: str
    suggestion: str


class TimelinePoint(BaseModel):
    date: str
    score: int
    event: str
    projected: bool = False


class AnalysisResponse(BaseModel):
    api_id: str
    api_name: str
    doc_score: DocScoreResponse
    improvements: List[ImprovementItem]
    duplicates: List[DuplicateItem]
    compliance_issues: List[ComplianceIssue]
    timeline: List[TimelinePoint]
