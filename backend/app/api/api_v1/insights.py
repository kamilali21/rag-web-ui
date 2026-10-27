"""Authenticated catalog-backed Insights; analysis generation has separate phase gates."""
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import User, AnalysisRun
from app.services import insights_catalog
from app.services import comparison
from app.services import research_analysis
from app.services import analysis_history
from app.schemas.research_analysis import AnalysisRequest
from app.schemas.comparison import ComparisonRequest

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(get_current_user)]
Scope = Literal["public", "private", "both"]


@router.get("/history")
def history(db: Database, actor: Actor, response: Response,
            before_id: int | None = Query(None, gt=0), limit: int = Query(20, ge=1, le=50),
            analysis_type: Literal["summary", "compare", "analyze", "contradictions", "candidate_gaps"] | None = None,
            status: Literal["processing", "complete", "failed", "insufficient_evidence"] | None = None,
            scope: Scope | None = None):
    response.headers["Cache-Control"] = "no-store"
    return analysis_history.history(db, actor, before_id=before_id, limit=limit,
        analysis_type=analysis_type, status=status, scope=scope)


@router.get("/history/{run_id}")
def history_result(run_id: int, db: Database, actor: Actor, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return analysis_history.read(db, actor, run_id)


class SelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: Scope
    mode: Literal["compare", "analyse"]
    document_ids: list[Annotated[StrictInt, Field(gt=0)]] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def check_selection(self):
        if len(set(self.document_ids)) != len(self.document_ids):
            raise ValueError("Select distinct documents")
        if self.mode == "compare" and len(self.document_ids) < 2:
            raise ValueError("Comparison requires at least two documents")
        return self


@router.get("/documents")
def documents(db: Database, actor: Actor, scope: Scope = "public",
              search: str = Query("", max_length=200), author: str = Query("", max_length=200),
              department_id: int | None = Query(None, gt=0),
              document_type: Literal["paper", "thesis", "report", "other"] | None = None,
              year_from: int | None = Query(None, ge=1000, le=9999), year_to: int | None = Query(None, ge=1000, le=9999),
              before_id: int | None = Query(None, gt=0), limit: int = Query(20, ge=1, le=50)):
    return insights_catalog.catalog(db, actor, scope=scope, search=search, author=author,
        department_id=department_id, document_type=document_type, year_from=year_from,
        year_to=year_to, before_id=before_id, limit=limit)


@router.get("/documents/{document_id}")
def document(document_id: int, db: Database, actor: Actor, scope: Scope = "public"):
    return insights_catalog.selection(db, actor, scope, [document_id])[0]


@router.post("/selection")
def validate_selection(payload: SelectionRequest, db: Database, actor: Actor):
    return {"scope": payload.scope, "mode": payload.mode,
            "documents": insights_catalog.selection(db, actor, payload.scope, payload.document_ids)}


@router.post("/comparisons")
def create_comparison(payload: ComparisonRequest, db: Database, actor: Actor):
    return comparison.compare(db, actor, payload)


@router.get("/comparisons/{run_id}")
def read_comparison(run_id: int, db: Database, actor: Actor):
    return comparison.read_run(db, actor, run_id)


@router.post("/analyses")
def create_analysis(payload: AnalysisRequest, db: Database, actor: Actor):
    return research_analysis.analyze(db, actor, payload)


@router.get("/analyses/{run_id}")
def read_analysis(run_id: int, db: Database, actor: Actor):
    return comparison.read_run(db, actor, run_id, ("analyze", "contradictions", "candidate_gaps"))


@router.get("/analyses/requests/{request_id}")
def recover_analysis(request_id: UUID, db: Database, actor: Actor):
    # Recover a disconnected POST without generating another result. Never expose
    # another user's request, even when its UUID is known on a shared browser.
    run = db.query(AnalysisRun).filter_by(user_id=actor.id, request_id=str(request_id)).filter(AnalysisRun.analysis_type.in_(("analyze", "contradictions", "candidate_gaps"))).one_or_none()
    if run is None:
        raise HTTPException(404, "Analysis unavailable")
    return comparison.read_run(db, actor, run.id, ("analyze", "contradictions", "candidate_gaps"))
