from .user import User
from .knowledge import KnowledgeBase, Document, DocumentChunk
from .chat import Chat, Message
from .api_key import APIKey
# Added by ChatGPT: register ResearchIQ tables with the existing SQLAlchemy metadata.
from .authorization import Role, AdminAllowlist, user_roles
from .authentication import EmailOTP, AuthSession, AuthRateLimit
from .research import Department, AcademicDocumentMetadata, Bookmark
from .researcher import ResearcherProfile, PublicationRequest, WithdrawalRequest
from .analysis import AnalysisRun, AnalysisDocument, AnalysisEvidence

__all__ = [
    "User",
    "KnowledgeBase",
    "Document",
    "DocumentChunk",
    "Chat",
    "Message",
    "APIKey",
    "Role", "AdminAllowlist", "user_roles", "EmailOTP", "AuthSession", "AuthRateLimit",
    "Department", "AcademicDocumentMetadata", "Bookmark",
    "ResearcherProfile", "PublicationRequest", "WithdrawalRequest",
    "AnalysisRun", "AnalysisDocument", "AnalysisEvidence",
]
