"""Pydantic models for raw findings and classification output."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RawFinding(BaseModel):
    """Payload deserialized from the Go scanner."""

    id: str
    source: str
    module_name: str
    raw_content: str
    content_hash: str
    url: str
    affected_entity: str
    metadata: dict[str, str] = Field(default_factory=dict)
    discovered_at: datetime
    scan_session_id: str


class LeakType(str, Enum):
    CREDENTIAL = "credential"
    PII = "pii"
    AI_TRAINING_DATA = "ai_training_data"
    SYSTEM_PROMPT = "system_prompt"
    API_KEY = "api_key"
    PRIVATE_KEY = "private_key"
    INTERNAL_CONFIG = "internal_config"
    MCP_EXPOSURE = "mcp_exposure"
    OTHER = "other"


class RecommendedAction(str, Enum):
    NOTIFY_CERT = "notify_cert"
    NOTIFY_COMPANY = "notify_company"
    NOTIFY_RESEARCHER = "notify_researcher"
    ESCALATE = "escalate"
    FALSE_POSITIVE = "false_positive"


class ClassificationResult(BaseModel):
    """Structured LLM / rules output."""

    finding_id: str
    is_real_leak: bool
    confidence: float
    leak_type: LeakType
    severity_score: float
    severity_reasoning: str
    affected_entity: str
    affected_entity_confidence: float
    recommended_action: RecommendedAction
    pii_detected: bool
    pii_types: list[str]
    ai_content_detected: bool
    classified_at: datetime
    model_used: str
    tokens_used: int
