"""Schemas for organization settings."""

from pydantic import BaseModel


class ExternalParserConfig(BaseModel):
    """Connection details for an external GPU parser service."""

    url: str
    api_key: str


class DocumentProcessingSettings(BaseModel):
    """Per-organization document processing configuration."""

    provider: str = "docling"  # "docling" | "legacy" | "external"
    external_parser: ExternalParserConfig | None = None


class OrganizationSettingsResponse(BaseModel):
    """Response schema for organization settings."""

    document_processing: DocumentProcessingSettings


class OrganizationSettingsUpdate(BaseModel):
    """Request body for updating organization settings (partial update)."""

    document_processing: DocumentProcessingSettings | None = None
