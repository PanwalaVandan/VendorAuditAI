"""Organization settings endpoints."""

import json
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db import get_db
from app.models import User
from app.models.organization import Organization
from app.schemas.organization import (
    ExternalParserConfig,
    OrganizationSettingsResponse,
    OrganizationSettingsUpdate,
    DocumentProcessingSettings,
)

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_org(db: AsyncSession, org_id: str) -> Organization:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


def _parse_org_settings(org: Organization) -> dict:
    if org.settings:
        try:
            return json.loads(org.settings)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


@router.get("/settings", response_model=OrganizationSettingsResponse)
async def get_organization_settings(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationSettingsResponse:
    """Return the current organization's settings."""
    org = await _get_org(db, current_user.organization_id)
    raw = _parse_org_settings(org)

    dp_raw = raw.get("document_processing", {})
    ext_raw = dp_raw.get("external_parser")
    ext = ExternalParserConfig(**ext_raw) if ext_raw else None

    return OrganizationSettingsResponse(
        document_processing=DocumentProcessingSettings(
            provider=dp_raw.get("provider", "docling"),
            external_parser=ext,
        )
    )


@router.patch("/settings", response_model=OrganizationSettingsResponse)
async def update_organization_settings(
    body: OrganizationSettingsUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationSettingsResponse:
    """Merge new values into the organization's settings."""
    org = await _get_org(db, current_user.organization_id)
    raw = _parse_org_settings(org)

    if body.document_processing is not None:
        dp = body.document_processing
        raw["document_processing"] = {
            "provider": dp.provider,
            "external_parser": dp.external_parser.model_dump() if dp.external_parser else None,
        }

    org.settings = json.dumps(raw)
    await db.commit()
    await db.refresh(org)

    dp_raw = raw.get("document_processing", {})
    ext_raw = dp_raw.get("external_parser")
    ext = ExternalParserConfig(**ext_raw) if ext_raw else None

    return OrganizationSettingsResponse(
        document_processing=DocumentProcessingSettings(
            provider=dp_raw.get("provider", "docling"),
            external_parser=ext,
        )
    )


@router.post("/settings/parser/test")
async def test_external_parser(
    body: ExternalParserConfig,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """Test connectivity to an external parser service by calling its /health endpoint."""
    base_url = body.url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{base_url}/health",
                headers={"Authorization": f"Bearer {body.api_key}"},
            )
        if resp.status_code == 200:
            return {"ok": True}
        return {"ok": False, "error": f"Health check returned HTTP {resp.status_code}"}
    except httpx.TimeoutException:
        return {"ok": False, "error": "Connection timed out (10s)"}
    except httpx.ConnectError as exc:
        return {"ok": False, "error": f"Could not connect: {exc}"}
    except Exception as exc:
        logger.warning("External parser test failed: %s", exc)
        return {"ok": False, "error": str(exc)}
