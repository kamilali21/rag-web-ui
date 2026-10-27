"""Bounded owner-private history. Unavailable sources reveal no saved content."""
from fastapi import HTTPException
from sqlalchemy.orm import load_only
from app.models import AnalysisRun, AnalysisEvidence
from app.services.authorization import require_active_user
from app.services import comparison
from app.services.insights_catalog import selection

TYPES = ("summary", "compare", "analyze", "contradictions", "candidate_gaps")


def history(db, actor, *, before_id=None, limit=20, analysis_type=None, status=None, scope=None):
    require_active_user(actor)
    db.rollback()
    query = db.query(AnalysisRun).options(load_only(AnalysisRun.id, AnalysisRun.analysis_type,
        AnalysisRun.status, AnalysisRun.scope, AnalysisRun.created_at, AnalysisRun.completed_at,
        AnalysisRun.request_json)).filter(AnalysisRun.user_id == actor.id, AnalysisRun.analysis_type.in_(TYPES))
    if before_id is not None: query = query.filter(AnalysisRun.id < before_id)
    if analysis_type: query = query.filter(AnalysisRun.analysis_type == analysis_type)
    if status: query = query.filter(AnalysisRun.status == status)
    if scope: query = query.filter(AnalysisRun.scope == scope)
    rows = query.order_by(AnalysisRun.id.desc()).limit(limit + 1).all()
    items = []
    for run in rows[:limit]:
        available, documents, question = True, [], None
        try:
            comparison.validate_run_sources(db, actor, run)
            documents = [{"id": doc["id"], "title": doc["title"] or doc["file_name"]}
                         for doc in selection(db, actor, run.scope, run.request_json["document_ids"])]
            question = run.request_json.get("question") or None
        except HTTPException as error:
            if error.status_code != 404: raise
            available = False
        items.append({"id": run.id, "analysis_type": run.analysis_type, "status": run.status,
            "scope": run.scope, "created_at": run.created_at, "completed_at": run.completed_at,
            "available": available, "documents": documents, "question": question})
    return {"items": items, "has_more": len(rows) > limit,
            "next_before_id": rows[limit - 1].id if len(rows) > limit else None}


def read(db, actor, run_id):
    result = comparison.read_run(db, actor, run_id, TYPES)
    run = db.get(AnalysisRun, run_id)
    evidence = db.query(AnalysisEvidence).filter_by(analysis_id=run_id).order_by(AnalysisEvidence.id).all()
    return {**result, "analysis_type": run.analysis_type, "scope": run.scope,
            "evidence": [{"evidence_id": row.evidence_id, "document_id": row.source_document_id,
                "page": row.page, "excerpt": row.excerpt, "evidence_hash": row.evidence_hash}
                for row in evidence]}
