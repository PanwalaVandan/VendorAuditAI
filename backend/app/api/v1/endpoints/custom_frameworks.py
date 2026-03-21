"""Custom compliance framework CRUD endpoints.

Provides endpoints for:
- POST   /custom-frameworks              - create a framework
- GET    /custom-frameworks              - list frameworks for the org
- GET    /custom-frameworks/{id}         - get a framework with all controls
- PATCH  /custom-frameworks/{id}         - update framework metadata
- DELETE /custom-frameworks/{id}         - delete a framework
- POST   /custom-frameworks/{id}/controls              - add a control
- PATCH  /custom-frameworks/{id}/controls/{control_id} - update a control
- DELETE /custom-frameworks/{id}/controls/{control_id} - remove a control
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user
from app.db import get_db
from app.models import User
from app.models.custom_framework import CustomControl, CustomFramework
from app.schemas.custom_framework import (
    CustomControlCreate,
    CustomControlResponse,
    CustomControlUpdate,
    CustomFrameworkCreate,
    CustomFrameworkListResponse,
    CustomFrameworkResponse,
    CustomFrameworkSummary,
    CustomFrameworkUpdate,
)

router = APIRouter(tags=["Custom Frameworks"])


async def _get_framework_or_404(
    framework_id: str,
    org_id: str,
    db: AsyncSession,
    load_controls: bool = False,
) -> CustomFramework:
    """Fetch a framework by ID scoped to the org, or raise 404."""
    query = select(CustomFramework).where(
        CustomFramework.id == framework_id,
        CustomFramework.organization_id == org_id,
    )
    if load_controls:
        query = query.options(selectinload(CustomFramework.controls))
    result = await db.execute(query)
    fw = result.scalar_one_or_none()
    if not fw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Framework not found")
    return fw


# ── Framework CRUD ───────────────────────────────────────────────────────────

@router.post("", response_model=CustomFrameworkResponse, status_code=status.HTTP_201_CREATED)
async def create_framework(
    payload: CustomFrameworkCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CustomFrameworkResponse:
    """Create a new custom compliance framework."""
    fw = CustomFramework(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        name=payload.name,
        version=payload.version,
        description=payload.description,
    )
    db.add(fw)
    await db.commit()
    await db.refresh(fw)
    # Reload with controls relationship (empty at creation)
    result = await db.execute(
        select(CustomFramework)
        .where(CustomFramework.id == fw.id)
        .options(selectinload(CustomFramework.controls))
    )
    return CustomFrameworkResponse.model_validate(result.scalar_one())


@router.get("", response_model=CustomFrameworkListResponse)
async def list_frameworks(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
) -> CustomFrameworkListResponse:
    """List all custom frameworks for the current organisation."""
    skip = (page - 1) * limit

    total_result = await db.execute(
        select(func.count(CustomFramework.id)).where(
            CustomFramework.organization_id == current_user.organization_id,
            CustomFramework.is_active == True,  # noqa: E712
        )
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(CustomFramework)
        .where(
            CustomFramework.organization_id == current_user.organization_id,
            CustomFramework.is_active == True,  # noqa: E712
        )
        .options(selectinload(CustomFramework.controls))
        .order_by(CustomFramework.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    frameworks = result.scalars().all()

    summaries = [
        CustomFrameworkSummary(
            id=fw.id,
            name=fw.name,
            version=fw.version,
            description=fw.description,
            is_active=fw.is_active,
            control_count=len(fw.controls),
            created_at=fw.created_at,
            updated_at=fw.updated_at,
        )
        for fw in frameworks
    ]

    return CustomFrameworkListResponse(data=summaries, total=total, page=page, limit=limit)


@router.get("/{framework_id}", response_model=CustomFrameworkResponse)
async def get_framework(
    framework_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CustomFrameworkResponse:
    """Get a framework with all its controls."""
    fw = await _get_framework_or_404(
        framework_id, current_user.organization_id, db, load_controls=True
    )
    return CustomFrameworkResponse.model_validate(fw)


@router.patch("/{framework_id}", response_model=CustomFrameworkResponse)
async def update_framework(
    framework_id: str,
    payload: CustomFrameworkUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CustomFrameworkResponse:
    """Update framework metadata (name, version, description, is_active)."""
    fw = await _get_framework_or_404(
        framework_id, current_user.organization_id, db, load_controls=True
    )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(fw, field, value)
    await db.commit()
    await db.refresh(fw)
    result = await db.execute(
        select(CustomFramework)
        .where(CustomFramework.id == fw.id)
        .options(selectinload(CustomFramework.controls))
    )
    return CustomFrameworkResponse.model_validate(result.scalar_one())


@router.delete("/{framework_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_framework(
    framework_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a custom framework and all its controls (cascade)."""
    fw = await _get_framework_or_404(framework_id, current_user.organization_id, db)
    await db.delete(fw)
    await db.commit()


# ── Control CRUD ─────────────────────────────────────────────────────────────

@router.post(
    "/{framework_id}/controls",
    response_model=CustomControlResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_control(
    framework_id: str,
    payload: CustomControlCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CustomControlResponse:
    """Add a control to a framework."""
    await _get_framework_or_404(framework_id, current_user.organization_id, db)

    control = CustomControl(
        framework_id=framework_id,
        control_id=payload.control_id,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        guidance=payload.guidance,
        order_index=payload.order_index,
    )
    db.add(control)
    await db.commit()
    await db.refresh(control)
    return CustomControlResponse.model_validate(control)


@router.patch(
    "/{framework_id}/controls/{control_id}",
    response_model=CustomControlResponse,
)
async def update_control(
    framework_id: str,
    control_id: str,
    payload: CustomControlUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CustomControlResponse:
    """Update a control."""
    await _get_framework_or_404(framework_id, current_user.organization_id, db)

    result = await db.execute(
        select(CustomControl).where(
            CustomControl.id == control_id,
            CustomControl.framework_id == framework_id,
        )
    )
    control = result.scalar_one_or_none()
    if not control:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(control, field, value)
    await db.commit()
    await db.refresh(control)
    return CustomControlResponse.model_validate(control)


@router.delete(
    "/{framework_id}/controls/{control_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_control(
    framework_id: str,
    control_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Remove a control from a framework."""
    await _get_framework_or_404(framework_id, current_user.organization_id, db)

    result = await db.execute(
        select(CustomControl).where(
            CustomControl.id == control_id,
            CustomControl.framework_id == framework_id,
        )
    )
    control = result.scalar_one_or_none()
    if not control:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control not found")

    await db.delete(control)
    await db.commit()
