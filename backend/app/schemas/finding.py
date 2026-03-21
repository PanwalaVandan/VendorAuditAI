"""Pydantic schemas for findings and analysis."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Severity and status literals
SeverityType = Literal["critical", "high", "medium", "low", "info"]
FindingStatusType = Literal["open", "acknowledged", "remediated", "accepted", "false_positive"]
FrameworkType = Literal["nist_800_53", "soc2_tsc", "iso_27001", "cis_controls", "hipaa", "pci_dss", "caiq", "nist_ai_rmf", "ai_risk"]


class AnalysisRequest(BaseModel):
    """Request to trigger document analysis.

    Supply either `framework` (a built-in framework key) OR `custom_framework_id`
    (the UUID of a custom framework).  Exactly one must be provided.
    """

    framework: FrameworkType | None = Field(
        None, description="Built-in compliance framework key"
    )
    custom_framework_id: str | None = Field(
        None, description="UUID of a custom framework to analyze against"
    )
    chunk_limit: int = Field(50, ge=1, le=200, description="Maximum chunks to analyze")


class AnalysisRunResponse(BaseModel):
    """Response model for an analysis run."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    organization_id: str
    framework: str
    model_used: str
    status: str
    error_message: str | None = None
    chunks_analyzed: int
    findings_count: int
    input_tokens: int
    output_tokens: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    summary: str | None = None
    created_at: datetime
    updated_at: datetime


class AnalysisRunListResponse(BaseModel):
    """Paginated list of analysis runs."""

    data: list[AnalysisRunResponse]
    total: int
    page: int
    limit: int


class FindingBase(BaseModel):
    """Base finding fields."""

    title: str = Field(..., min_length=1, max_length=500)
    severity: SeverityType = "medium"
    description: str
    framework_control: str | None = None
    evidence: str | None = None
    remediation: str | None = None
    impact: str | None = None


class FindingCreate(FindingBase):
    """Schema for creating a finding manually."""

    document_id: str
    chunk_id: str | None = None
    page_number: int | None = None
    section_header: str | None = None


class FindingUpdate(BaseModel):
    """Schema for updating a finding."""

    title: str | None = Field(None, min_length=1, max_length=500)
    severity: SeverityType | None = None
    status: FindingStatusType | None = None
    description: str | None = None
    remediation: str | None = None
    user_notes: str | None = None


class FindingResponse(BaseModel):
    """Response model for a finding."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    analysis_run_id: str
    document_id: str
    organization_id: str
    title: str
    severity: str
    status: str
    framework: str
    framework_control: str | None = None
    description: str
    evidence: str | None = None
    remediation: str | None = None
    impact: str | None = None
    chunk_id: str | None = None
    page_number: int | None = None
    section_header: str | None = None
    confidence_score: float | None = None
    user_notes: str | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    created_at: datetime
    updated_at: datetime


class FindingListResponse(BaseModel):
    """Paginated list of findings."""

    data: list[FindingResponse]
    total: int
    page: int
    limit: int


class FindingSummary(BaseModel):
    """Summary of findings by severity."""

    total: int
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    open: int = 0
    resolved: int = 0


class AnalysisStatusResponse(BaseModel):
    """Response for analysis status check."""

    analysis_run_id: str
    status: str
    progress: float = Field(ge=0.0, le=1.0)
    message: str | None = None
    findings_count: int = 0
