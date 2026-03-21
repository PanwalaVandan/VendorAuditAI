"""Analysis API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db import get_db
from app.middleware.rate_limit import limiter
from app.models import User
from app.schemas.finding import (
    AnalysisRequest,
    AnalysisRunListResponse,
    AnalysisRunResponse,
    FindingListResponse,
    FindingResponse,
    FindingSummary,
    FindingUpdate,
)
from app.services import analysis as analysis_service

router = APIRouter(tags=["Analysis"])


@router.post("/documents/{document_id}/analyze", response_model=AnalysisRunResponse)
@limiter.limit("10/hour")
async def analyze_document(
    request: Request,
    document_id: str,
    analysis_request: AnalysisRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalysisRunResponse:
    """
    Trigger compliance analysis on a document.

    The document must be processed before analysis.
    Analysis uses Claude to identify gaps against the specified framework.
    """
    if not analysis_request.framework and not analysis_request.custom_framework_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'framework' (built-in) or 'custom_framework_id'.",
        )
    try:
        analysis_run = await analysis_service.run_analysis(
            db=db,
            document_id=document_id,
            org_id=current_user.organization_id,
            framework=analysis_request.framework or "custom",
            chunk_limit=analysis_request.chunk_limit,
            custom_framework_id=analysis_request.custom_framework_id,
        )
        await db.commit()
        await db.refresh(analysis_run)
        return AnalysisRunResponse.model_validate(analysis_run)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/runs", response_model=AnalysisRunListResponse)
async def list_analysis_runs(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    document_id: str | None = Query(None, description="Filter by document"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> AnalysisRunListResponse:
    """List analysis runs for the organization."""
    skip = (page - 1) * limit
    runs, total = await analysis_service.get_analysis_runs(
        db=db,
        org_id=current_user.organization_id,
        document_id=document_id,
        skip=skip,
        limit=limit,
    )
    return AnalysisRunListResponse(
        data=[AnalysisRunResponse.model_validate(r) for r in runs],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/runs/{run_id}", response_model=AnalysisRunResponse)
async def get_analysis_run(
    run_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalysisRunResponse:
    """Get details of a specific analysis run."""
    run = await analysis_service.get_analysis_run_by_id(
        db=db,
        run_id=run_id,
        org_id=current_user.organization_id,
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis run not found",
        )
    return AnalysisRunResponse.model_validate(run)


@router.get("/findings", response_model=FindingListResponse)
async def list_findings(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    document_id: str | None = Query(None, description="Filter by document"),
    analysis_run_id: str | None = Query(None, description="Filter by analysis run"),
    severity: str | None = Query(None, description="Filter by severity"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> FindingListResponse:
    """
    List findings for the organization.

    Supports filtering by document, analysis run, severity, and status.
    Results are sorted by severity (critical first) then by date.
    """
    skip = (page - 1) * limit
    findings, total = await analysis_service.get_findings(
        db=db,
        org_id=current_user.organization_id,
        document_id=document_id,
        analysis_run_id=analysis_run_id,
        severity=severity,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return FindingListResponse(
        data=[FindingResponse.model_validate(f) for f in findings],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/findings/summary", response_model=FindingSummary)
async def get_findings_summary(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    document_id: str | None = Query(None, description="Filter by document"),
) -> FindingSummary:
    """Get summary of findings by severity and status."""
    summary = await analysis_service.get_finding_summary(
        db=db,
        org_id=current_user.organization_id,
        document_id=document_id,
    )
    return FindingSummary(**summary)


@router.get("/findings/{finding_id}", response_model=FindingResponse)
async def get_finding(
    finding_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FindingResponse:
    """Get details of a specific finding."""
    finding = await analysis_service.get_finding_by_id(
        db=db,
        finding_id=finding_id,
        org_id=current_user.organization_id,
    )
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )
    return FindingResponse.model_validate(finding)


@router.patch("/findings/{finding_id}", response_model=FindingResponse)
async def update_finding(
    finding_id: str,
    update_data: FindingUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FindingResponse:
    """
    Update a finding.

    Can update status, severity, notes, and remediation details.
    """
    finding = await analysis_service.update_finding(
        db=db,
        finding_id=finding_id,
        org_id=current_user.organization_id,
        update_data=update_data.model_dump(exclude_unset=True),
    )
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )
    await db.commit()
    await db.refresh(finding)
    return FindingResponse.model_validate(finding)
