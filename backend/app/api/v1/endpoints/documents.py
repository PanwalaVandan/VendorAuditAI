"""Document management API endpoints."""

import logging
import time
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db import get_db
from app.db.session import async_session_factory
from app.models import User
from app.schemas.document import (
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
)
from app.services import document as document_service
from app.services import processing as processing_service
from app.services.processing import get_doc_progress

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Documents"])


async def _run_processing_background(document_id: str, org_id: str) -> None:
    """Background task: process a document using its own DB session."""
    async with async_session_factory() as db:
        try:
            document = await document_service.get_document_by_id(db, document_id, org_id)
            if document:
                await processing_service.process_document(db, document)
                await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error("Background processing failed for %s: %s", document_id, exc)

# Allowed MIME types for document upload
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/msword",  # .doc
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",        # .xlsx
    "application/vnd.ms-excel",                                                  # .xls
}

# Maximum file size (50 MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    vendor_id: str | None = Query(None, description="Filter by vendor"),
    document_type: str | None = Query(None, description="Filter by document type"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
) -> DocumentListResponse:
    """
    List documents for the current user's organization.

    Supports pagination and filtering by vendor, document type, and status.
    """
    skip = (page - 1) * limit
    documents, total = await document_service.get_documents(
        db=db,
        org_id=current_user.organization_id,
        skip=skip,
        limit=limit,
        vendor_id=vendor_id,
        document_type=document_type,
        status=status_filter,
    )
    return DocumentListResponse(
        data=[DocumentResponse.model_validate(d) for d in documents],
        total=total,
        page=page,
        limit=limit,
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document file to upload"),
    vendor_id: str | None = Query(None, description="Associated vendor ID"),
    document_type: str = Query("other", description="Document type"),
) -> DocumentResponse:
    """
    Upload a new document.

    Accepts PDF and DOCX files up to 50MB. Returns immediately with
    status=processing; parsing and chunking run as a background task.
    Poll GET /documents/{id}/progress for live progress.
    """
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed types: PDF, DOCX",
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    document_data = DocumentCreate(
        vendor_id=vendor_id,
        document_type=document_type,
    )

    try:
        document = await document_service.create_document(
            db=db,
            org_id=current_user.organization_id,
            filename=file.filename,
            file_content=content,
            mime_type=file.content_type,
            document_data=document_data,
        )
        await db.commit()
        await db.refresh(document)

        # Kick off processing in the background and return immediately
        background_tasks.add_task(
            _run_processing_background,
            str(document.id),
            str(current_user.organization_id),
        )
        return DocumentResponse.model_validate(document)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/{document_id}/progress")
async def get_document_progress(
    document_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Return live processing progress for a document.

    While parsing: returns pages_done, total_pages, percent, eta_seconds.
    After completion: returns stage=processed or stage=failed.
    """
    progress = get_doc_progress(document_id)

    if progress:
        pages_done = progress["pages_done"]
        total_pages = progress["total_pages"]
        elapsed = time.monotonic() - progress["started_at"]

        if pages_done > 0 and total_pages > 0:
            secs_per_page = elapsed / pages_done
            eta_seconds = max(0, int((total_pages - pages_done) * secs_per_page))
            percent = int((pages_done / total_pages) * 100)
        else:
            eta_seconds = 0
            percent = 0

        return {
            "stage": progress["stage"],
            "pages_done": pages_done,
            "total_pages": total_pages,
            "percent": percent,
            "eta_seconds": eta_seconds,
        }

    # Not in memory — check DB for final status
    document = await document_service.get_document_by_id(
        db, document_id, current_user.organization_id
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "stage": document.processing_stage,
        "pages_done": document.page_count or 0,
        "total_pages": document.page_count or 0,
        "percent": 100 if document.status == "processed" else 0,
        "eta_seconds": 0,
    }


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentResponse:
    """
    Get a specific document by ID.
    """
    document = await document_service.get_document_by_id(
        db=db,
        document_id=document_id,
        org_id=current_user.organization_id,
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return DocumentResponse.model_validate(document)


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """
    Download a document file.
    """
    result = await document_service.get_document_content(
        db=db,
        document_id=document_id,
        org_id=current_user.organization_id,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    document, content = result
    return Response(
        content=content,
        media_type=document.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{document.filename}"',
            "Content-Length": str(document.file_size),
        },
    )


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    document_data: DocumentUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentResponse:
    """
    Update a document's metadata.

    Only vendor association and document type can be updated.
    """
    document = await document_service.update_document(
        db=db,
        document_id=document_id,
        org_id=current_user.organization_id,
        document_data=document_data,
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    await db.commit()
    await db.refresh(document)
    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a document.

    This will also delete the file from storage.
    """
    deleted = await document_service.delete_document(
        db=db,
        document_id=document_id,
        org_id=current_user.organization_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    await db.commit()


@router.post("/{document_id}/process", response_model=DocumentResponse)
async def process_document(
    document_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentResponse:
    """
    Trigger processing for a document.

    This will parse the document, extract text, and create chunks.
    The document must be in PENDING status.
    """
    # Get the document first
    document = await document_service.get_document_by_id(
        db=db,
        document_id=document_id,
        org_id=current_user.organization_id,
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check if document is already processed or processing
    if document.status not in ("pending", "failed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document cannot be processed (status: {document.status})",
        )

    try:
        processed = await processing_service.process_document(db, document)
        await db.commit()
        await db.refresh(processed)
        return DocumentResponse.model_validate(processed)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
