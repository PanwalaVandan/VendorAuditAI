"""
VendorAuditAI — DeepDoc Parser Service
=======================================
Deploys RAGFlow's DeepDoc PDF pipeline as a serverless GPU function on Modal.com.

Accepts a PDF (as base64), runs DeepDoc layout recognition + OCR + table extraction,
and returns structured chunks ready for AI compliance analysis.

Commands
--------
  # One-time: download model weights into the persistent volume
  modal run download_models.py

  # Local dev with live reload
  modal serve modal_app.py

  # Production deploy
  modal deploy modal_app.py

Environment (Modal Secret: "vendorauditai-parser-secret")
----------------------------------------------------------
  PARSER_SERVICE_SECRET   Shared secret the VendorAuditAI backend sends as Bearer token
"""

import base64
import re
import sys
from io import BytesIO
from pathlib import Path

import modal

# ---------------------------------------------------------------------------
# Modal app + persistent volume
# ---------------------------------------------------------------------------

app = modal.App("vendorauditai-parser")

# Persistent volume — survives pod restarts and scales across containers.
# Stores the ~1 GB of DeepDoc model weights so they are never re-downloaded
# during a live request.
models_volume = modal.Volume.from_name("vendorauditai-models", create_if_missing=True)

VOLUME_PATH    = Path("/vol")
MODELS_PATH    = VOLUME_PATH / "rag" / "res" / "deepdoc"   # matches RAG_PROJECT_BASE=/vol
RAGFLOW_SRC    = Path("/opt/ragflow")

# ---------------------------------------------------------------------------
# Stubs injected into the image at build time
# ---------------------------------------------------------------------------
# RAGFlow's common/settings.py tries to connect to MySQL/ES/Redis on import.
# We replace it with a minimal stub that only exposes what DeepDoc reads.

_SETTINGS_STUB = """\
# Modal stub — no database/storage connections needed for parsing only.
DOC_ENGINE            = "elasticsearch"
DOC_ENGINE_INFINITY   = False
PARALLEL_DEVICES      = [0]          # GPU device IDs available
THREAD_POOL_MAX_WORKERS = 8
TIKA_SERVER_JAR       = None

class _Stub:
    \"\"\"Silent no-op for any attribute DeepDoc doesn't actually use.\"\"\"
    def __getattr__(self, name):
        return None

es           = _Stub()
docStoreConn = _Stub()
storage      = _Stub()
"""

# infinity.rag_tokenizer is from InfiniFlow's infinity-sdk (dev build).
# We provide a pure-Python stub that covers the interface DeepDoc's pdf_parser
# uses: tokenize() and fine_grained_tokenize().  Chunking quality is not
# affected because we implement our own compliance chunker below.

_INFINITY_STUB = """\
import re as _re

class RagTokenizer:
    def tokenize(self, text: str) -> str:
        if not text:
            return ""
        text = _re.sub(r'[^\\w\\s]', ' ', text.lower())
        return " ".join(text.split())

    def fine_grained_tokenize(self, tks):
        if isinstance(tks, str):
            return tks.split()
        return tks if tks else []

    def is_chinese(self, text: str) -> bool:
        return False

tokenizer = RagTokenizer()

def tokenize(text: str) -> str:
    return tokenizer.tokenize(text)

def fine_grained_tokenize(tks):
    return tokenizer.fine_grained_tokenize(tks)
"""


def _patch_ragflow_for_modal():
    """
    Run inside the container at IMAGE BUILD TIME (via .run_function()).
    1. Replaces common/settings.py with a no-op stub.
    2. Creates an infinity/rag_tokenizer.py stub package.
    """
    base = Path("/opt/ragflow")

    # 1. Settings stub
    settings_file = base / "common" / "settings.py"
    if settings_file.exists():
        settings_file.write_text(
            "# Modal stub — no database/storage connections needed for parsing only.\n"
            "DOC_ENGINE              = 'elasticsearch'\n"
            "DOC_ENGINE_INFINITY     = False\n"
            "THREAD_POOL_MAX_WORKERS = 8\n"
            "TIKA_SERVER_JAR         = None\n"
            "\n"
            "# PARALLEL_DEVICES is an integer count of GPU devices.\n"
            "# OCR uses: range(PARALLEL_DEVICES) to init detectors,\n"
            "# and PARALLEL_DEVICES > 0 to check GPU mode.\n"
            "PARALLEL_DEVICES = 1\n"
            "\n"
            "class _Stub:\n"
            "    def __getattr__(self, name):\n"
            "        return None\n"
            "\n"
            "es           = _Stub()\n"
            "docStoreConn = _Stub()\n"
            "storage      = _Stub()\n"
        )
        print(f"[patch] Replaced {settings_file}")

    # 2. infinity stub
    inf_dir = base / "infinity"
    inf_dir.mkdir(exist_ok=True)
    (inf_dir / "__init__.py").write_text("")
    (inf_dir / "rag_tokenizer.py").write_text(
        "import re as _re\n"
        "\n"
        "class RagTokenizer:\n"
        "    def tokenize(self, text):\n"
        "        if not text: return ''\n"
        "        text = _re.sub(r'[^\\w\\s]', ' ', text.lower())\n"
        "        return ' '.join(text.split())\n"
        "    def fine_grained_tokenize(self, tks):\n"
        "        if isinstance(tks, str): return tks.split()\n"
        "        return tks if tks else []\n"
        "    def is_chinese(self, text): return False\n"
        "    def tag(self, token):\n"
        "        # POS tag stub — return 'n' (noun) for all tokens.\n"
        "        # table_structure_recognizer.blockType checks for 'nr' (proper noun).\n"
        "        # Returning 'n' means no token is classified as a proper noun, which is\n"
        "        # safe for English compliance documents.\n"
        "        return 'n'\n"
        "\n"
        "tokenizer = RagTokenizer()\n"
        "def tokenize(text): return tokenizer.tokenize(text)\n"
        "def fine_grained_tokenize(tks): return tokenizer.fine_grained_tokenize(tks)\n"
        "def tag(token): return tokenizer.tag(token)\n"
    )
    print(f"[patch] Created infinity stub at {inf_dir}")

    # 3. Patch deepdoc/parser/__init__.py to only import the PDF parser.
    #    The default __init__ eagerly imports DocxParser, HtmlParser, ExcelParser,
    #    etc., which pull in pandas, python-pptx, mammoth, and other heavy deps
    #    we don't need for PDF-only processing.
    parser_init = base / "deepdoc" / "parser" / "__init__.py"
    if parser_init.exists():
        parser_init.write_text(
            "# Patched for Modal: PDF parser only — other parsers omitted.\n"
            "from deepdoc.parser.pdf_parser import RAGFlowPdfParser\n"
        )
        print(f"[patch] Replaced {parser_init}")

    # 4. Patch deepdoc/__init__.py similarly to avoid pulling in unused parsers
    deepdoc_init = base / "deepdoc" / "__init__.py"
    if deepdoc_init.exists():
        original = deepdoc_init.read_text()
        # Only keep the line that imports RAGFlowPdfParser; comment out the rest
        lines = original.splitlines()
        patched = []
        for line in lines:
            # Keep imports that are essential; skip imports of non-PDF parsers
            if any(x in line for x in ["DocxParser", "HtmlParser", "ExcelParser",
                                        "PlaintextParser", "PptParser", "AudioParser",
                                        "EmailParser", "EmlParser"]):
                patched.append(f"# [modal-skip] {line}")
            else:
                patched.append(line)
        deepdoc_init.write_text("\n".join(patched))
        print(f"[patch] Patched {deepdoc_init}")

    # 5. Patch rag/nlp/__init__.py — pdf_parser.py only needs rag_tokenizer from
    #    this module. The full __init__ imports tiktoken, rank_bm25, datrie, jieba,
    #    and other heavy NLP packages we don't need for PDF layout parsing.
    rag_nlp_init = base / "rag" / "nlp" / "__init__.py"
    if rag_nlp_init.exists():
        original = rag_nlp_init.read_text()
        # Write a minimal stub that exposes rag_tokenizer plus no-op stubs for
        # any other symbol that pdf_parser might reference from rag.nlp
        rag_nlp_init.write_text(
            "# Patched for Modal: minimal rag.nlp — only what deepdoc actually uses.\n"
            "from infinity import rag_tokenizer  # our stub\n"
            "\n"
            "import chardet as _chardet\n"
            "\n"
            "def find_codec(blob):\n"
            "    \"\"\"Detect character encoding of a byte string.\"\"\"\n"
            "    if isinstance(blob, str):\n"
            "        return 'utf-8'\n"
            "    result = _chardet.detect(blob[:4096])\n"
            "    return result.get('encoding') or 'utf-8'\n"
            "\n"
            "def tokenize_table(table, *a, **kw): return str(table)\n"
            "def tokenize_chunks(sections, doc, *a, **kw): return sections\n"
            "def num_tokens_from_string(s, *a, **kw): return max(1, len(s) // 4)\n"
            "\n"
            "class Node:\n"
            "    pass\n"
        )
        print(f"[patch] Replaced {rag_nlp_init}")

    # 6. Patch rag/utils/lazy_image.py — operators.py imports ensure_pil_image
    #    from here. Replace the module with a real implementation that doesn't
    #    pull in rag.nlp.
    lazy_image = base / "rag" / "utils" / "lazy_image.py"
    if lazy_image.exists():
        lazy_image.write_text(
            "# Patched for Modal: real ensure_pil_image without rag.nlp dependency.\n"
            "import numpy as np\n"
            "from PIL import Image\n"
            "\n"
            "def ensure_pil_image(img):\n"
            "    \"\"\"\n"
            "    Convert bytes / path to PIL Image.\n"
            "    Numpy arrays are returned as-is so callers (NormalizeImage,\n"
            "    ToCHWImage) preserve the array dtype (e.g. float32 after\n"
            "    normalisation).  The callers only reassign 'img' when the\n"
            "    return value isinstance(pil, Image.Image), so returning the\n"
            "    ndarray directly skips the PIL round-trip and keeps float32.\n"
            "    \"\"\"\n"
            "    if isinstance(img, Image.Image):\n"
            "        return img\n"
            "    if isinstance(img, np.ndarray):\n"
            "        # Return the array directly — preserves float32 dtype.\n"
            "        return img\n"
            "    if isinstance(img, (bytes, bytearray)):\n"
            "        import io\n"
            "        return Image.open(io.BytesIO(img))\n"
            "    if isinstance(img, str):\n"
            "        return Image.open(img)\n"
            "    raise TypeError(f'Cannot convert {type(img)} to PIL Image')\n"
            "\n"
            "class LazyImage:\n"
            "    def __init__(self, path):\n"
            "        self._path = path\n"
            "        self._img = None\n"
            "    def __call__(self):\n"
            "        if self._img is None:\n"
            "            self._img = Image.open(self._path)\n"
            "        return self._img\n"
        )
        print(f"[patch] Replaced {lazy_image}")

    # 7. Stub rag/prompts/ — pdf_parser imports vision_llm_describe_prompt from
    #    here but only calls it when need_image=True (which we never use).
    #    The real generator.py pulls in json_repair, anthropic, openai, etc.
    prompts_dir = base / "rag" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "__init__.py").write_text("# Patched for Modal.\n")
    (prompts_dir / "generator.py").write_text(
        "# Patched for Modal: stub prompts — LLM calls not needed for parsing.\n"
        "def vision_llm_describe_prompt(*a, **kw): return ''\n"
        "def get_prompt(*a, **kw): return ''\n"
    )
    print(f"[patch] Stubbed {prompts_dir}")

    # 8. Verify critical files exist after sparse checkout
    critical = [
        base / "deepdoc" / "parser" / "pdf_parser.py",
        base / "deepdoc" / "vision" / "ocr.py",
        base / "deepdoc" / "vision" / "layout_recognizer.py",
        base / "common" / "file_utils.py",
    ]
    for f in critical:
        status = "OK" if f.exists() else "MISSING"
        print(f"[patch] {f.relative_to(base)}: {status}")


# ---------------------------------------------------------------------------
# Container image
# ---------------------------------------------------------------------------

image = (
    modal.Image.debian_slim(python_version="3.11")
    # ---- System libraries ----
    .apt_install(
        "git",
        "libgl1",               # OpenCV (headless) runtime
        "libglib2.0-0",         # OpenCV
        "libgomp1",             # XGBoost OpenMP
        "poppler-utils",        # pdfplumber page rendering
        "openjdk-17-jre-headless",  # Apache Tika (used by laws.py for .doc)
    )
    # ---- Python packages (DeepDoc subset only — NOT the RAGFlow web stack) ----
    .pip_install(
        # PDF / document parsing
        "pdfplumber==0.10.4",
        "pypdf>=6.8.0",
        "python-docx>=1.1.2",
        # Vision / ML inference
        "onnxruntime-gpu==1.23.2",      # must match RAGFlow's exact version requirement
        "opencv-python-headless==4.10.0.84",
        "numpy<2.0",
        "Pillow>=10.0.0",
        "xgboost==1.6.0",
        "scikit-learn>=1.3.0",
        # PyTorch — only needed for torch.cuda.is_available() check inside DeepDoc
        "torch==2.3.0",
        # HuggingFace model download
        "huggingface_hub>=0.24.0",
        # NLP utilities used by rag/nlp/
        "cn2an==0.5.22",
        "word2number==1.1",
        "chardet>=5.2.0",
        "xpinyin==0.7.6",
        "nltk>=3.8.0",
        "roman-numbers==1.0.2",
        "beartype>=0.18.0",
        "six>=1.16.0",              # deepdoc/vision/operators.py
        "pyclipper>=1.4.0",         # deepdoc vision OCR preprocessing
        "shapely>=2.0.0",           # deepdoc/vision/postprocess.py polygon ops
        "editdistance>=0.8.0",      # deepdoc pdf_parser text similarity
        "tabulate>=0.9.0",          # table-to-text rendering
        # Web endpoint
        "fastapi>=0.110.0",
        "python-multipart>=0.0.9",
    )
    # ---- Clone RAGFlow (sparse: only deepdoc/, rag/, common/) ----
    .run_commands(
        "git clone --filter=blob:none --sparse --depth=1 "
        "https://github.com/infiniflow/ragflow.git /opt/ragflow",
        "cd /opt/ragflow && git sparse-checkout set deepdoc rag common",
        # Ensure rag/res/deepdoc/ directory exists (models come from volume at runtime)
        "mkdir -p /opt/ragflow/rag/res/deepdoc",
    )
    # ---- Patch settings + create infinity stub ----
    .run_function(_patch_ragflow_for_modal)
)

# ---------------------------------------------------------------------------
# Compliance-aware chunker
# ---------------------------------------------------------------------------
# We implement our own chunker rather than using laws.py, which pulls in
# tika/JVM and the full rag.nlp stack.  This version is tuned specifically
# for SOC2, ISO 27001, NIST 800-53, and similar compliance documents.

# Regex that matches control IDs:  CC6.1  A.9.1.2  SI-7  PE-3(1)  3.1.1  etc.
_CONTROL_ID_RE = re.compile(
    r"^("
    r"[A-Z]{1,4}[-.]?\d[\d.]*(\(\d+\))?"   # CC6.1 / SI-7(1) / A.9.1.2
    r"|Control\s+\d[\d.]*"                   # Control 3.1
    r"|\d{1,2}\.\d{1,3}(\.\d{1,3})?"        # 3.1 / 3.1.1
    r")\b",
    re.IGNORECASE,
)

_MAX_CHUNK_TOKENS = 512     # ~2,048 characters
_MAX_CHUNK_CHARS  = _MAX_CHUNK_TOKENS * 4


def _looks_like_header(text: str) -> bool:
    """True if the text looks like a section / control header."""
    stripped = text.strip()
    if not stripped:
        return False
    # Short lines that start with a control ID or are ALL CAPS / Title Case headings
    first_line = stripped.splitlines()[0].strip()
    if _CONTROL_ID_RE.match(first_line):
        return True
    if len(first_line) < 120 and (first_line.isupper() or first_line.istitle()):
        return True
    return False


def chunk_sections(
    sections: list,
    tables: list,
    max_chars: int = _MAX_CHUNK_CHARS,
) -> list[dict]:
    """
    Group DeepDoc sections into semantically coherent chunks.

    Strategy:
    - When a new control ID / section header is encountered, start a new chunk.
    - Accumulate following paragraphs into the same chunk until max_chars is reached.
    - Tables are appended to the chunk they belong to (same page, following the header).

    Returns list of dicts: {content, page, section_header}
    """
    # Normalise: each item is (text, page_number_or_None)
    items: list[tuple[str, int | None]] = []
    for s in sections:
        if isinstance(s, tuple) and len(s) >= 2:
            items.append((str(s[0]).strip(), s[1]))
        elif isinstance(s, str):
            items.append((s.strip(), None))

    # Append tables as natural-language text (DeepDoc already converts them)
    for tbl in tables:
        text = tbl.text if hasattr(tbl, "text") else str(tbl)
        page = tbl.page_number if hasattr(tbl, "page_number") else None
        if text and text.strip():
            items.append((text.strip(), page))

    if not items:
        return []

    chunks: list[dict] = []
    current_texts: list[str] = []
    current_page: int | None = None
    current_header: str | None = None
    current_chars: int = 0

    def _flush():
        nonlocal current_texts, current_page, current_header, current_chars
        if current_texts:
            content = "\n\n".join(current_texts).strip()
            if content:
                chunks.append({
                    "content": content,
                    "page": current_page,
                    "section_header": current_header,
                    "token_count": max(1, len(content) // 4),
                })
        current_texts = []
        current_page = None
        current_header = None
        current_chars = 0

    for text, page in items:
        if not text:
            continue

        is_header = _looks_like_header(text)
        would_exceed = (current_chars + len(text)) > max_chars

        # Start a new chunk on: section header OR size overflow
        if current_texts and (is_header or would_exceed):
            _flush()

        if not current_texts:
            current_page = page
            if is_header:
                current_header = text.splitlines()[0].strip()

        current_texts.append(text)
        current_chars += len(text)

    _flush()
    return chunks


# ---------------------------------------------------------------------------
# Core GPU function
# ---------------------------------------------------------------------------

@app.function(
    image=image,
    gpu="T4",                       # cheapest Modal GPU ~$0.000164/s
    timeout=600,                    # 10 min max — covers 200-page PDFs
    scaledown_window=120,           # stay warm 2 min after last request
    volumes={str(VOLUME_PATH): models_volume},
    memory=16384,                   # 16 GB RAM
    secrets=[modal.Secret.from_name("vendorauditai-parser-secret")],
    retries=modal.Retries(max_retries=2, backoff_coefficient=2.0, initial_delay=5.0),
)
def parse_document(
    pdf_bytes: bytes,
    filename: str = "document.pdf",
    document_type: str = "other",
) -> dict:
    """
    Parse a PDF with DeepDoc and return compliance-ready chunks.

    Parameters
    ----------
    pdf_bytes     : raw PDF bytes
    filename      : original filename (for logging)
    document_type : one of soc2 | iso27001 | sig_lite | sig_core | hecvat |
                    caiq | pentest | other

    Returns
    -------
    {
        "chunks": [
            {"content": str, "page": int|null, "section_header": str|null, "token_count": int},
            ...
        ],
        "page_count": int,
        "filename":   str,
    }
    """
    import logging
    import os

    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("vendorauditai.parser")

    # ------------------------------------------------------------------
    # 1. Configure paths so DeepDoc finds its model weights in the volume
    # ------------------------------------------------------------------
    os.environ["RAG_PROJECT_BASE"] = str(VOLUME_PATH)
    sys.path.insert(0, str(RAGFLOW_SRC))

    # Symlink volume model directory into the path DeepDoc expects
    # (RAG_PROJECT_BASE)/rag/res/deepdoc  →  /vol/rag/res/deepdoc
    # The volume already has models here from download_models.py.
    # We just make sure the directory exists so DeepDoc doesn't re-download.
    MODELS_PATH.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 2. Import DeepDoc (after sys.path and env are set)
    # ------------------------------------------------------------------
    import pdfplumber
    from deepdoc.parser.pdf_parser import RAGFlowPdfParser

    # ------------------------------------------------------------------
    # 3. Get page count
    # ------------------------------------------------------------------
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        page_count = len(pdf.pages)

    log.info("Parsing '%s' — %d pages, type=%s", filename, page_count, document_type)

    # ------------------------------------------------------------------
    # 4. Run DeepDoc
    #    RAGFlowPdfParser.__call__(pdf_bytes, need_image=False)
    #    Returns (sections, tables)
    #      sections: list of (text: str, page_number: int) tuples
    #      tables  : list of table objects with .text attribute
    # ------------------------------------------------------------------
    parser = RAGFlowPdfParser()
    sections, tables = parser(pdf_bytes, need_image=False)

    log.info(
        "DeepDoc extracted %d sections and %d tables from '%s'",
        len(sections), len(tables), filename,
    )

    # ------------------------------------------------------------------
    # 5. Chunk into compliance-aware segments
    # ------------------------------------------------------------------
    chunks = chunk_sections(sections, tables)

    log.info("Produced %d chunks from '%s'", len(chunks), filename)

    return {
        "chunks":     chunks,
        "page_count": page_count,
        "filename":   filename,
    }


# ---------------------------------------------------------------------------
# FastAPI web endpoint
# ---------------------------------------------------------------------------
# All FastAPI imports are inside the function body so they only execute
# inside the container (where FastAPI is installed), not locally when
# Modal parses this file.

@app.function(
    image=image,
    volumes={str(VOLUME_PATH): models_volume},
    secrets=[modal.Secret.from_name("vendorauditai-parser-secret")],
)
@modal.asgi_app()
def fastapi_app():
    import os

    from fastapi import FastAPI, HTTPException, Request, Security
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

    web_app = FastAPI(
        title="VendorAuditAI Parser Service",
        description="Serverless DeepDoc PDF parser for compliance document analysis.",
        version="1.0.0",
    )

    bearer = HTTPBearer()

    def _check_token(
        credentials: HTTPAuthorizationCredentials = Security(bearer),
    ) -> None:
        expected = os.environ.get("PARSER_SERVICE_SECRET", "")
        if not expected:
            raise HTTPException(status_code=500, detail="PARSER_SERVICE_SECRET not configured")
        if credentials.credentials != expected:
            raise HTTPException(status_code=401, detail="Invalid or missing service token")

    @web_app.get("/health")
    async def health():
        """Liveness probe — no auth required."""
        return {"status": "ok", "service": "vendorauditai-parser"}

    @web_app.post("/parse")
    async def parse_endpoint(
        request: Request,
        credentials: HTTPAuthorizationCredentials = Security(bearer),
    ):
        """
        Parse a PDF with DeepDoc and return structured compliance chunks.

        Body: { pdf_b64, filename, document_type }
        Returns: { chunks, page_count, filename }
        """
        _check_token(credentials)

        body          = await request.json()
        pdf_b64       = body.get("pdf_b64", "")
        filename      = body.get("filename", "document.pdf")
        document_type = body.get("document_type", "other")

        if not pdf_b64:
            raise HTTPException(status_code=422, detail="pdf_b64 is required")

        try:
            pdf_bytes = base64.b64decode(pdf_b64)
        except Exception:
            raise HTTPException(status_code=422, detail="pdf_b64 is not valid base64")

        if not pdf_bytes.startswith(b"%PDF"):
            raise HTTPException(status_code=422, detail="Content does not appear to be a valid PDF")

        valid_types = {"soc2", "iso27001", "sig_lite", "sig_core", "hecvat", "caiq", "pentest", "other"}
        if document_type not in valid_types:
            document_type = "other"

        result = parse_document.remote(pdf_bytes, filename, document_type)
        return result

    return web_app
