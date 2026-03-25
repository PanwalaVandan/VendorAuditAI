"""Document processing pipeline orchestration."""

import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentStatus, ProcessingStage
from app.services.chunking import Chunk, DoclingChunker, TextChunker
from app.services.embedding import embedding_to_json, get_embedding_service
from app.services.parsing import DocumentParser, ParsedDocument
from app.services.storage import get_storage_backend


class DocumentProcessor:
    """Orchestrates the document processing pipeline.

    Pipeline stages:
    1. UPLOADED -> PARSING: Extract text from document
    2. PARSING -> CHUNKING: Split text into semantic chunks
    3. CHUNKING -> EMBEDDING: Generate embeddings (future)
    4. EMBEDDING -> COMPLETED: Ready for analysis
    """

    def __init__(
        self,
        chunker: TextChunker | None = None,
    ):
        """Initialize the document processor.

        Args:
            chunker: Text chunker instance (uses defaults if not provided)
        """
        self.storage = get_storage_backend()
        self.chunker = chunker or TextChunker()

    async def process_document(
        self,
        db: AsyncSession,
        document: Document,
    ) -> Document:
        """Process a document through the full pipeline.

        Args:
            db: Database session
            document: Document to process

        Returns:
            Updated document

        Raises:
            ValueError: If processing fails
        """
        try:
            # Update status to processing
            document.status = DocumentStatus.PROCESSING.value

            # Stage 1: Parse document
            document.processing_stage = ProcessingStage.PARSING.value
            await db.flush()

            parsed = await self._parse_document(document)

            # Update document metadata from parsing
            document.page_count = parsed.total_pages
            if parsed.metadata:
                document.metadata_ = json.dumps(parsed.metadata)

            # Stage 2: Chunk document
            document.processing_stage = ProcessingStage.CHUNKING.value
            await db.flush()

            chunks = self._chunk_document(parsed)

            # Save chunks to database
            db_chunks = await self._save_chunks(db, document, chunks)

            # Stage 3: Generate embeddings
            document.processing_stage = ProcessingStage.EMBEDDING.value
            await db.flush()

            await self._generate_embeddings(db, db_chunks)

            # Mark as completed
            document.status = DocumentStatus.PROCESSED.value
            document.processing_stage = ProcessingStage.COMPLETED.value
            document.processed_at = datetime.now(UTC)
            document.error_message = None

            await db.flush()
            return document

        except Exception as e:
            # Mark as failed
            document.status = DocumentStatus.FAILED.value
            document.processing_stage = ProcessingStage.ERROR.value
            document.error_message = str(e)
            await db.flush()
            raise ValueError(f"Processing failed: {e!s}") from e

    async def _parse_document(self, document: Document) -> ParsedDocument:
        """Parse a document to extract text.

        Args:
            document: Document to parse

        Returns:
            ParsedDocument with extracted content
        """
        # Load file from storage
        try:
            content = await self.storage.get(document.storage_path)
        except FileNotFoundError as e:
            raise ValueError(f"Document file not found: {document.storage_path}") from e

        # Parse based on MIME type
        try:
            parsed = DocumentParser.parse(content, document.mime_type)
        except ValueError as e:
            raise ValueError(f"Failed to parse document: {e!s}") from e

        return parsed

    def _chunk_document(self, parsed: ParsedDocument) -> list[Chunk]:
        """Split parsed document into chunks.

        Uses DoclingChunker when the document was parsed via docling
        (markdown_text is populated). Falls back to TextChunker otherwise.

        Args:
            parsed: ParsedDocument to chunk

        Returns:
            List of Chunk objects
        """
        if parsed.markdown_text:
            try:
                docling_chunker = DoclingChunker(target_chunk_size=self.chunker.target_chunk_size)
                chunks = docling_chunker.chunk_markdown(parsed.markdown_text)
                if chunks:
                    return chunks
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(
                    "DoclingChunker failed, falling back to TextChunker: %s", exc
                )

        full_text = parsed.full_text
        if not full_text.strip():
            return []

        return self.chunker.chunk_text(full_text)

    async def _save_chunks(
        self,
        db: AsyncSession,
        document: Document,
        chunks: list[Chunk],
    ) -> list[DocumentChunk]:
        """Save chunks to the database.

        Args:
            db: Database session
            document: Parent document
            chunks: List of chunks to save

        Returns:
            List of saved DocumentChunk objects
        """
        db_chunks = []
        for chunk in chunks:
            db_chunk = DocumentChunk(
                document_id=document.id,
                content=chunk.content,
                token_count=chunk.token_count,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                section_header=chunk.section_header,
                metadata_=json.dumps(chunk.metadata) if chunk.metadata else None,
            )
            db.add(db_chunk)
            db_chunks.append(db_chunk)

        await db.flush()
        return db_chunks

    async def _generate_embeddings(
        self,
        db: AsyncSession,
        chunks: list[DocumentChunk],
    ) -> None:
        """Generate embeddings for chunks.

        Args:
            db: Database session
            chunks: List of DocumentChunk objects to embed

        Note:
            If OpenAI API key is not configured, embeddings are skipped.
            Documents can still be processed and searched with keyword matching.
        """
        embedding_service = get_embedding_service()

        if not embedding_service.is_configured:
            # Skip embedding if API key not configured
            return

        # Extract texts for batch embedding
        texts = [chunk.content for chunk in chunks]

        try:
            embeddings = await embedding_service.embed_chunks_batch(texts)

            # Update chunks with embeddings
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                chunk.embedding = embedding_to_json(embedding)

            await db.flush()
        except ValueError:
            # Log but don't fail - documents can still work without embeddings
            pass


async def process_document(
    db: AsyncSession,
    document: Document,
) -> Document:
    """Convenience function to process a document.

    Args:
        db: Database session
        document: Document to process

    Returns:
        Updated document
    """
    processor = DocumentProcessor()
    return await processor.process_document(db, document)


async def process_document_by_id(
    db: AsyncSession,
    document_id: str,
    org_id: str,
) -> Document | None:
    """Process a document by ID.

    Args:
        db: Database session
        document_id: Document UUID
        org_id: Organization ID

    Returns:
        Processed document or None if not found
    """
    from app.services.document import get_document_by_id

    document = await get_document_by_id(db, document_id, org_id)
    if not document:
        return None

    processor = DocumentProcessor()
    return await processor.process_document(db, document)
