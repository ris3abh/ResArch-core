# api/schemas/__init__.py
from api.schemas.auth import (
    SignupRequest, LoginRequest, RefreshTokenRequest,
    TokenResponse, UserResponse
)
from api.schemas.client import (
    ClientCreate, ClientUpdate, ClientResponse, ClientListResponse
)
from api.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
)
from api.schemas.document import (
    DocumentUploadRequest, DocumentUploadResponse,
    DocumentResponse, DocumentDownloadResponse, DocumentListResponse
)
from api.schemas.execution import (
    StartCrewRequest, ExecutionResponse, ExecutionStatusResponse
)
from api.schemas.webhook import (
    HITLWebhookPayload, WebhookEvent, WebhookEventsPayload,
    HITLApprovalRequest, HITLApprovalResponse,
    CheckpointResponse, PendingCheckpointsResponse
)

__all__ = [
    # Auth
    "SignupRequest", "LoginRequest", "RefreshTokenRequest",
    "TokenResponse", "UserResponse",
    # Client
    "ClientCreate", "ClientUpdate", "ClientResponse", "ClientListResponse",
    # Project
    "ProjectCreate", "ProjectUpdate", "ProjectResponse", "ProjectListResponse",
    # Document
    "DocumentUploadRequest", "DocumentUploadResponse",
    "DocumentResponse", "DocumentDownloadResponse", "DocumentListResponse",
    # Execution
    "StartCrewRequest", "ExecutionResponse", "ExecutionStatusResponse",
    # Webhook
    "HITLWebhookPayload", "WebhookEvent", "WebhookEventsPayload",
    "HITLApprovalRequest", "HITLApprovalResponse",
    "CheckpointResponse", "PendingCheckpointsResponse"
]