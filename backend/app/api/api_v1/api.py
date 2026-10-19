from fastapi import APIRouter
from app.api.api_v1 import auth, knowledge_base, chat, api_keys, corpus, departments, retrieval, researcher, insights

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(knowledge_base.router, prefix="/knowledge-base", tags=["knowledge-base"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])
# Added by ChatGPT: explicit corpus routes leave all existing private routes owner-only.
api_router.include_router(corpus.router, prefix="/corpus", tags=["corpus"])
# Added by ChatGPT: Phase 5 reference data uses the same session and admin policies.
api_router.include_router(departments.router, prefix="/departments", tags=["departments"])
api_router.include_router(retrieval.router, prefix="/retrieval", tags=["retrieval"])
api_router.include_router(researcher.router, prefix="/researcher", tags=["researcher"])
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
