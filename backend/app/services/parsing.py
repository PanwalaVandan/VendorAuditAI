"""Document parsing service for text extraction."""

import io
import logging
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from collections.abc import Callable
from typing import ClassVar

import fitz  # PyMuPDF
from docx import Document as DocxDocument

logger = logging.getLogger(__name__)


@dataclass
class ParsedPage:
    """Represents a parsed page from a document."""

    page_number: int
    text: str
    tables: list[list[list[str]]] = field(default_factory=list)


@dataclass
class ParsedDocument:
    """Represents a fully parsed document."""

    pages: list[ParsedPage]
    total_pages: int
    metadata: dict = field(default_factory=dict)
    markdown_text: str | None = None  # Set when parsed via docling; None for legacy path
    pre_chunks: list[dict] | None = None  # Set by external parser; skip re-chunking when set

    @property
    def full_text(self) -> str:
        """Get the full text of the document."""
        return "\n\n".join(page.text for page in self.pages if page.text)

    @property
    def has_tables(self) -> bool:
        """Check if document contains any tables."""
        return any(page.tables for page in self.pages)


class PDFParser:
    """Parser for PDF documents using PyMuPDF."""

    @staticmethod
    def parse(content: bytes) -> ParsedDocument:
        """Parse a PDF document and extract text and tables.

        Args:
            content: PDF file bytes

        Returns:
            ParsedDocument with extracted content

        Raises:
            ValueError: If PDF cannot be parsed
        """
        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as e:
            raise ValueError(f"Failed to open PDF: {e!s}") from e

        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]

            # Extract text
            text = page.get_text("text")

            # Extract tables (basic approach using blocks)
            tables = PDFParser._extract_tables(page)

            pages.append(ParsedPage(
                page_number=page_num + 1,
                text=text.strip(),
                tables=tables,
            ))

        # Extract metadata
        metadata = {
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "creator": doc.metadata.get("creator", ""),
            "producer": doc.metadata.get("producer", ""),
            "creation_date": PDFParser._parse_pdf_date(doc.metadata.get("creationDate", "")),
            "modification_date": PDFParser._parse_pdf_date(doc.metadata.get("modDate", "")),
        }

        doc.close()

        return ParsedDocument(
            pages=pages,
            total_pages=len(pages),
            metadata=metadata,
        )

    @staticmethod
    def _extract_tables(page: fitz.Page) -> list[list[list[str]]]:
        """Extract tables from a PDF page.

        This is a simplified table extraction. For production,
        consider using more sophisticated table detection.

        Args:
            page: PyMuPDF page object

        Returns:
            List of tables, each table is a list of rows
        """
        tables = []

        # Use PyMuPDF's table finder if available (v1.23+)
        try:
            page_tables = page.find_tables()
            for table in page_tables:
                extracted = table.extract()
                if extracted:
                    tables.append(extracted)
        except AttributeError:
            # Fallback for older PyMuPDF versions - no table extraction
            pass

        return tables

    @staticmethod
    def _parse_pdf_date(date_str: str) -> str | None:
        """Parse PDF date format (D:YYYYMMDDHHmmSS) to ISO format.

        Args:
            date_str: PDF date string

        Returns:
            ISO format date string or None
        """
        if not date_str:
            return None

        try:
            # Remove D: prefix if present
            if date_str.startswith("D:"):
                date_str = date_str[2:]

            # Parse basic format YYYYMMDDHHMMSS
            if len(date_str) >= 14:
                dt = datetime.strptime(date_str[:14], "%Y%m%d%H%M%S")
                return dt.isoformat()
            elif len(date_str) >= 8:
                dt = datetime.strptime(date_str[:8], "%Y%m%d")
                return dt.isoformat()
        except ValueError:
            pass

        return None


class DOCXParser:
    """Parser for DOCX documents using python-docx."""

    @staticmethod
    def parse(content: bytes) -> ParsedDocument:
        """Parse a DOCX document and extract text and tables.

        Args:
            content: DOCX file bytes

        Returns:
            ParsedDocument with extracted content

        Raises:
            ValueError: If DOCX cannot be parsed
        """
        try:
            doc = DocxDocument(io.BytesIO(content))
        except Exception as e:
            raise ValueError(f"Failed to open DOCX: {e!s}") from e

        # DOCX doesn't have pages in the same way as PDF
        # We'll treat the whole document as one "page" with sections
        text_parts = []
        tables = []

        # Extract paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)

        # Extract tables
        for table in doc.tables:
            table_data = []
            for row in table.rows:
                row_data = [cell.text.strip() for cell in row.cells]
                table_data.append(row_data)
            if table_data:
                tables.append(table_data)

        # Extract metadata from core properties
        core_props = doc.core_properties
        metadata = {
            "title": core_props.title or "",
            "author": core_props.author or "",
            "subject": core_props.subject or "",
            "creator": core_props.author or "",
            "creation_date": core_props.created.isoformat() if core_props.created else None,
            "modification_date": core_props.modified.isoformat() if core_props.modified else None,
        }

        # Create single page with all content
        page = ParsedPage(
            page_number=1,
            text="\n\n".join(text_parts),
            tables=tables,
        )

        return ParsedDocument(
            pages=[page],
            total_pages=1,  # DOCX doesn't have physical pages until rendered
            metadata=metadata,
        )


class DoclingParser:
    """Document parser using docling for structure-aware extraction.

    Handles PDF, DOCX, DOC, XLSX, and XLS files. Extracts markdown with
    preserved tables, heading hierarchy, and reading order. Falls back
    gracefully so the caller can use the legacy parser on failure.
    """

    SUPPORTED_MIME_TYPES: ClassVar[set[str]] = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    }

    # Map MIME type to a file extension docling can recognise
    _EXTENSIONS: ClassVar[dict[str, str]] = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.ms-excel": ".xls",
    }

    @classmethod
    def _build_converter(cls) -> "DocumentConverter":
        """Build a DocumentConverter using docling-parse C++ backend only.

        force_backend_text=True skips all ML models (no image rendering, no OOM,
        fast on CPU). Still produces structured markdown with headings and tables
        extracted from the PDF text layer.

        Set env var DOCLING_ML_PIPELINE=1 to enable TableFormer + layout models —
        only viable on a GPU server (CPU inference is ~16s/page, impractical).
        """
        import os
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions

        use_ml = os.getenv("DOCLING_ML_PIPELINE", "0") == "1"

        pdf_opts = PdfPipelineOptions()
        pdf_opts.force_backend_text = not use_ml
        pdf_opts.do_table_structure = use_ml
        pdf_opts.do_ocr = False
        pdf_opts.generate_page_images = False
        pdf_opts.generate_picture_images = False

        return DocumentConverter(
            format_options={"pdf": PdfFormatOption(pipeline_options=pdf_opts)}
        )

    _BATCH_SIZE: ClassVar[int] = 5  # pages per docling batch for PDFs

    @classmethod
    def parse(
        cls,
        content: bytes,
        mime_type: str,
        filename: str = "",
        on_progress: "Callable[[int, int], None] | None" = None,
    ) -> ParsedDocument:
        """Parse a document using docling.

        PDFs are processed in batches of _BATCH_SIZE pages so memory stays
        bounded regardless of document length. on_progress(pages_done, total)
        is called after each batch completes.

        Args:
            content: File bytes
            mime_type: MIME type of the document
            filename: Original filename (used for extension hint only)
            on_progress: Optional callback(pages_done, total_pages)

        Returns:
            ParsedDocument with markdown_text populated

        Raises:
            Exception: Propagated so caller can fall back to legacy parser
        """
        if mime_type == "application/pdf":
            return cls._parse_pdf_batched(content, on_progress)

        ext = cls._EXTENSIONS.get(mime_type, Path(filename).suffix or ".pdf")
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        try:
            return cls._convert_and_build(tmp_path, on_progress=None)
        finally:
            tmp_path.unlink(missing_ok=True)

    @classmethod
    def _parse_pdf_batched(
        cls,
        content: bytes,
        on_progress: "Callable[[int, int], None] | None",
    ) -> ParsedDocument:
        """Process a PDF in page batches to bound peak memory usage."""
        src = fitz.open(stream=content, filetype="pdf")
        total_pages = len(src)
        converter = cls._build_converter()
        markdown_parts: list[str] = []
        all_pages: list[ParsedPage] = []
        page_offset = 0

        for batch_start in range(0, total_pages, cls._BATCH_SIZE):
            batch_end = min(batch_start + cls._BATCH_SIZE, total_pages)

            # Carve out a sub-PDF for this batch
            sub = fitz.open()
            sub.insert_pdf(src, from_page=batch_start, to_page=batch_end - 1)
            sub_bytes = sub.tobytes()
            sub.close()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(sub_bytes)
                tmp_path = Path(tmp.name)
            try:
                result = converter.convert(str(tmp_path))
                batch_doc = result.document
                markdown_parts.append(batch_doc.export_to_markdown())

                if hasattr(batch_doc, "pages") and batch_doc.pages:
                    for i in range(len(batch_doc.pages)):
                        all_pages.append(ParsedPage(page_number=page_offset + i + 1, text=""))
                else:
                    for i in range(batch_end - batch_start):
                        all_pages.append(ParsedPage(page_number=page_offset + i + 1, text=""))
            finally:
                tmp_path.unlink(missing_ok=True)

            page_offset += batch_end - batch_start
            if on_progress:
                on_progress(batch_end, total_pages)

        src.close()

        markdown_text = "\n\n".join(markdown_parts)
        if all_pages:
            all_pages[0].text = markdown_text
        else:
            all_pages = [ParsedPage(page_number=1, text=markdown_text)]

        return ParsedDocument(
            pages=all_pages,
            total_pages=total_pages,
            metadata={},
            markdown_text=markdown_text,
        )

    @classmethod
    def _convert_and_build(
        cls,
        tmp_path: Path,
        on_progress: "Callable[[int, int], None] | None",
    ) -> ParsedDocument:
        """Run docling on a single temp file and build a ParsedDocument."""
        converter = cls._build_converter()
        result = converter.convert(str(tmp_path))
        doc = result.document
        markdown_text = doc.export_to_markdown()

        pages: list[ParsedPage] = []
        if hasattr(doc, "pages") and doc.pages:
            for page_no, _ in enumerate(doc.pages, start=1):
                pages.append(ParsedPage(page_number=page_no, text=""))
        else:
            pages = [ParsedPage(page_number=1, text=markdown_text)]

        if pages and all(p.text == "" for p in pages):
            pages[0].text = markdown_text

        metadata: dict = {}
        if hasattr(doc, "metadata") and doc.metadata:
            raw = doc.metadata
            metadata = {
                "title": getattr(raw, "title", "") or "",
                "author": getattr(raw, "authors", "") or "",
            }

        total = len(pages)
        if on_progress:
            on_progress(total, total)

        return ParsedDocument(
            pages=pages,
            total_pages=total,
            metadata=metadata,
            markdown_text=markdown_text,
        )


class ModalParserClient:
    """HTTP client for an external GPU parser service.

    The external service must implement the VendorAuditAI Parser Contract:
      GET  /health                    -> {"status": "ok"}
      POST /parse  (Bearer auth)      -> {chunks, page_count, filename}

    See parser-service/PARSER_CONTRACT.md for the full specification.
    """

    @staticmethod
    def parse_pdf(
        content: bytes,
        filename: str,
        document_type: str,
        url: str,
        api_key: str,
    ) -> "ParsedDocument":
        """Send a PDF to the external parser and return a ParsedDocument.

        Runs synchronously — call inside asyncio.to_thread when needed.
        Raises on HTTP errors or connection failures (caller logs and falls back).
        """
        import base64

        import httpx

        base = url.rstrip("/")
        payload = {
            "pdf_b64": base64.b64encode(content).decode(),
            "filename": filename,
            "document_type": document_type,
        }
        with httpx.Client(timeout=600.0, follow_redirects=True) as client:
            resp = client.post(
                f"{base}/parse",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()

        data = resp.json()
        chunks: list[dict] = data.get("chunks", [])
        page_count: int = data.get("page_count", 1)

        pages = [ParsedPage(page_number=i + 1, text="") for i in range(max(page_count, 1))]
        if pages:
            pages[0].text = "\n\n".join(c["content"] for c in chunks if c.get("content"))

        return ParsedDocument(
            pages=pages,
            total_pages=page_count,
            metadata={"filename": filename, "parser": "external_gpu"},
            pre_chunks=chunks,
        )


class DocumentParser:
    """Main document parser that delegates to specific parsers.

    Routing is controlled by the org-level parser_config dict:
      provider="external"  -> ModalParserClient (PDF only), falls back to docling on error
      provider="legacy"    -> PDFParser / DOCXParser directly
      provider="docling"   -> DoclingParser, falls back to legacy on error (default)

    When parser_config is None or provider is missing, defaults to docling.
    """

    PARSERS: ClassVar[dict[str, type[PDFParser] | type[DOCXParser]]] = {
        "application/pdf": PDFParser,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DOCXParser,
        "application/msword": DOCXParser,
    }

    @classmethod
    def parse(
        cls,
        content: bytes,
        mime_type: str,
        filename: str = "",
        on_progress: "Callable[[int, int], None] | None" = None,
        parser_config: dict | None = None,
    ) -> ParsedDocument:
        """Parse a document based on its MIME type and org parser config.

        Routing (controlled by parser_config["provider"]):
          "external" -> ModalParserClient (PDF only), fallback to docling on error
          "legacy"   -> PDFParser / DOCXParser directly, no further fallback
          "docling"  -> DoclingParser, fallback to legacy on error (default)

        on_progress(pages_done, total_pages) is forwarded to DoclingParser only.

        Args:
            content: File bytes
            mime_type: MIME type of the document
            filename: Original filename (optional, used as extension hint)
            on_progress: Optional callback(pages_done, total_pages)
            parser_config: Org-level config dict with "provider" and "external_parser" keys

        Returns:
            ParsedDocument with extracted content

        Raises:
            ValueError: If MIME type is not supported or all parsers fail
        """
        cfg = parser_config or {}
        provider = cfg.get("provider", "docling")

        # External GPU parser path (PDF only)
        if provider == "external" and mime_type == "application/pdf":
            ext = cfg.get("external_parser") or {}
            ext_url = ext.get("url", "")
            ext_key = ext.get("api_key", "")
            if ext_url and ext_key:
                try:
                    doc_type = cls._infer_doc_type(filename)
                    return ModalParserClient.parse_pdf(
                        content, filename, doc_type, url=ext_url, api_key=ext_key
                    )
                except Exception as exc:
                    logger.warning(
                        "External parser failed for %s, falling back to docling: %s",
                        filename,
                        exc,
                    )
            else:
                logger.warning(
                    "External parser selected but url/api_key not configured; falling back to docling"
                )

        # Legacy parser path (direct, no fallback beyond this)
        if provider == "legacy":
            parser_class = cls.PARSERS.get(mime_type)
            if not parser_class:
                raise ValueError(f"Unsupported document type for legacy parser: {mime_type}")
            return parser_class.parse(content)

        # Docling path (default) with legacy fallback
        if mime_type in DoclingParser.SUPPORTED_MIME_TYPES:
            try:
                return DoclingParser.parse(content, mime_type, filename, on_progress)
            except Exception as exc:
                logger.warning(
                    "Docling parsing failed for mime_type=%s, falling back to legacy parser: %s",
                    mime_type,
                    exc,
                )

        # Legacy fallback
        parser_class = cls.PARSERS.get(mime_type)
        if not parser_class:
            raise ValueError(f"Unsupported document type: {mime_type}")
        return parser_class.parse(content)

    @classmethod
    def supported_types(cls) -> list[str]:
        """Get list of supported MIME types (union of docling + legacy)."""
        return list(DoclingParser.SUPPORTED_MIME_TYPES | set(cls.PARSERS.keys()))

    @staticmethod
    def _infer_doc_type(filename: str) -> str:
        """Map a filename to a document_type hint for the external parser."""
        name = filename.lower()
        if "soc2" in name or "soc_2" in name or "soc 2" in name:
            return "soc2"
        if "iso27001" in name or "iso_27001" in name or "iso 27001" in name:
            return "iso27001"
        if "sig_lite" in name or "sig lite" in name:
            return "sig_lite"
        if "sig_core" in name or "sig core" in name:
            return "sig_core"
        if "hecvat" in name:
            return "hecvat"
        if "caiq" in name:
            return "caiq"
        if "pentest" in name or "penetration" in name:
            return "pentest"
        return "other"
