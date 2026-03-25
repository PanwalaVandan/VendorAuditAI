"""Document management API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db import get_db
from app.models import User
from app.schemas.document import (
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
)
from app.services import document as document_service
from app.services import processing as processing_service

router = APIRouter(tags=["Documents"])

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
    file: UploadFile = File(..., description="Document file to upload"),
    vendor_id: str | None = Query(None, description="Associated vendor ID"),
    document_type: str = Query("other", description="Document type"),
) -> DocumentResponse:
    """
    Upload a new document.

    Accepts PDF and DOCX files up to 50MB.
    The document will be queued for processing after upload.
    """
    # Validate file type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed types: PDF, DOCX",
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Validate filename
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Create document metadata
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

        # Auto-process the document after upload
        try:
            processed_doc = await processing_service.process_document(db, document)
            await db.commit()
            await db.refresh(processed_doc)
            return DocumentResponse.model_validate(processed_doc)
        except Exception as process_error:
            # If processing fails, still return the uploaded document
            # User can manually retry via /documents/{id}/process
            await db.rollback()
            await db.refresh(document)
            # Update status to indicate processing attempt failed
            document.status = "pending"
            document.error_message = str(process_error)
            await db.commit()
            await db.refresh(document)
            return DocumentResponse.model_validate(document)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


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
