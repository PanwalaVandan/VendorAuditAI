"""Pydantic schemas for custom compliance frameworks."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CustomControlCreate(BaseModel):
    """Schema for creating a control."""

    control_id: str = Field(..., min_length=1, max_length=50, description="Control identifier, e.g. CC-1")
    name: str = Field(..., min_length=1, max_length=255, description="Control name")
    description: str = Field(..., min_length=1, description="What must be true for this control to pass")
    category: str | None = Field(None, max_length=100, description="Control category")
    guidance: str | None = Field(None, description="Optional hints for the AI evaluator")
    order_index: int = Field(0, ge=0, description="Display order within the framework")


class CustomControlUpdate(BaseModel):
    """Schema for updating a control (all fields optional)."""

    control_id: str | None = Field(None, min_length=1, max_length=50)
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1)
    category: str | None = None
    guidance: str | None = None
    order_index: int | None = Field(None, ge=0)


class CustomControlResponse(BaseModel):
    """Schema for a control response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    framework_id: str
    control_id: str
    name: str
    description: str
    category: str | None
    guidance: str | None
    order_index: int
    created_at: datetime
    updated_at: datetime


class CustomFrameworkCreate(BaseModel):
    """Schema for creating a custom framework."""

    name: str = Field(..., min_length=1, max_length=255, description="Framework name")
    version: str = Field("1.0", max_length=50, description="Framework version")
    description: str | None = Field(None, description="Framework description")


class CustomFrameworkUpdate(BaseModel):
    """Schema for updating a framework (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    version: str | None = Field(None, max_length=50)
    description: str | None = None
    is_active: bool | None = None


class CustomFrameworkResponse(BaseModel):
    """Schema for a full framework response including controls."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    created_by: str
    name: str
    version: str
    description: str | None
    is_active: bool
    controls: list[CustomControlResponse] = []
    created_at: datetime
    updated_at: datetime


class CustomFrameworkSummary(BaseModel):
    """Lightweight framework summary for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    version: str
    description: str | None
    is_active: bool
    control_count: int = 0
    created_at: datetime
    updated_at: datetime


class CustomFrameworkListResponse(BaseModel):
    """Paginated list of custom frameworks."""

    data: list[CustomFrameworkSummary]
    total: int
    page: int
    limit: int
