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

    # 9. Patch deepdoc/vision/ocr.py — increase ONNX BFC arena gpu_mem_limit.
    #
    #    Root cause of OOM: the default 2GB arena per ONNX session fragments under
    #    sustained load (56-page OCR run), leaving <1MB contiguous space.  When the
    #    table structure recognizer then tries to allocate a ~68MB tensor it fails.
    #
    #    Fix: raise gpu_mem_limit to 6GB (T4 has 16GB VRAM; OCR + layout + TSR
    #    running in parallel fit easily within 12GB total).
    #    Also switch arena_extend_strategy from kNextPowerOfTwo → kSameAsRequested
    #    so the arena grows in exact increments rather than doubling, which is the
    #    pattern that causes rapid fragmentation.
    import re as _re  # noqa: PLC0415 — needed inside the container function
    ocr_py = base / "deepdoc" / "vision" / "ocr.py"
    if ocr_py.exists():
        text = ocr_py.read_text()

        # Diagnostic: print the lines around 'gpu_mem_limit' so we can see the
        # exact source pattern if our replacement attempts below don't match.
        for i, ln in enumerate(text.splitlines()):
            if "gpu_mem_limit" in ln:
                print(f"[patch-diag] ocr.py:{i+1}: {ln!r}")

        original = text

        # Pattern A: 'gpu_mem_limit': 2 * 1024 * 1024 * 1024  (any spacing)
        text = _re.sub(
            r"(['\"])gpu_mem_limit\1\s*:\s*2\s*\*\s*1024\s*\*\s*1024\s*\*\s*1024",
            "'gpu_mem_limit': 6 * 1024 * 1024 * 1024",
            text,
        )
        # Pattern B: 2 * 1024 ** 3  or  2 * 1024**3  (exponent form)
        text = _re.sub(
            r"(['\"])gpu_mem_limit\1\s*:\s*2\s*\*\s*1024\s*\*\*\s*3",
            "'gpu_mem_limit': 6 * 1024 ** 3",
            text,
        )
        # Pattern C: hard-coded integer 2147483648  (= 2 * 1024^3)
        # Use a word-boundary so we don't corrupt other numbers.
        text = _re.sub(
            r"(['\"])gpu_mem_limit\1\s*:\s*2147483648\b",
            "'gpu_mem_limit': 6442450944",   # 6 * 1024^3
            text,
        )
        # Pattern D: int(os.environ.get(..., 2 * 1024 * 1024 * 1024)) style
        text = _re.sub(
            r"(['\"])gpu_mem_limit\1\s*:\s*int\s*\([^)]*\b2\s*\*\s*1024(?:\s*\*\s*1024){2}[^)]*\)",
            "'gpu_mem_limit': 6 * 1024 * 1024 * 1024",
            text,
        )

        # Pattern E: env-var style — os.environ.get("OCR_GPU_MEM_LIMIT_MB", "2048")
        # Confirmed from diagnostic output: this is the actual RAGFlow pattern.
        # Change the hard-coded default from "2048" MB (2GB) to "6144" MB (6GB).
        text = text.replace('"OCR_GPU_MEM_LIMIT_MB", "2048"', '"OCR_GPU_MEM_LIMIT_MB", "6144"')
        text = text.replace("'OCR_GPU_MEM_LIMIT_MB', '2048'", "'OCR_GPU_MEM_LIMIT_MB', '6144'")

        # Switch arena strategy to avoid doubling-induced fragmentation
        text = text.replace("'kNextPowerOfTwo'", "'kSameAsRequested'")
        text = text.replace('"kNextPowerOfTwo"', '"kSameAsRequested"')

        if text != original:
            ocr_py.write_text(text)
            print(f"[patch] Patched gpu_mem_limit + arena_extend_strategy in {ocr_py}")
        else:
            print(f"[patch] WARN: gpu_mem_limit pattern not matched in {ocr_py} — arena_extend_strategy only")
            ocr_py.write_text(text)  # still write back the arena_extend_strategy change
    else:
        print(f"[patch] WARN: {ocr_py} not found — skipping gpu_mem_limit patch")

    # 10. Patch deepdoc/vision/table_structure_recognizer.py — disable orientation
    #     detection.
    #
    #     Without this patch, RAGFlow calls OCR 4 times per table (at 0°, 90°, 180°,
    #     270°) to determine which orientation yields the best reading order.
    #     Each pass allocates large GPU tensors; after the initial 56-page OCR run the
    #     arena is fragmented and these allocations fail with OOM.
    #
    #     Compliance documents (SOC 2, ISO 27001, NIST 800-53, HIPAA …) are always
    #     printed in standard orientation — there is no such thing as a sideways
    #     table of controls.  Returning (0, None) immediately is safe and saves
    #     ~20 s × number-of-tables worth of wasted GPU time.
    tsr_py = base / "deepdoc" / "vision" / "table_structure_recognizer.py"
    if tsr_py.exists():
        text = tsr_py.read_text()
        # Replace the det_orient method body with an immediate early return.
        # The method signature varies across RAGFlow versions; match any variant.
        patched = _re.sub(
            r"(def\s+det_orient\s*\(self[^)]*\)\s*:)"
            r"((?:\s+(?!def\s)\S[^\n]*|\n(?=\s))*)",   # grab the full body
            lambda m: (
                m.group(1)
                + "\n        # Patched for Modal: skip 4-pass orientation detection.\n"
                  "        # Compliance PDFs always use 0-degree (standard) orientation.\n"
                  "        # This eliminates the GPU OOM caused by repeated large tensor\n"
                  "        # allocations after the main OCR run fragments the BFC arena.\n"
                  "        return 0, None"
            ),
            text,
            count=1,
            flags=_re.DOTALL,
        )
        if patched != text:
            tsr_py.write_text(patched)
            print(f"[patch] Disabled orientation detection in {tsr_py}")
        else:
            # Fallback: the regex didn't match (different RAGFlow version).
            # Try a simpler line-by-line replacement of just the first executable
            # line after the def, inserting an early return above it.
            lines = text.splitlines()
            new_lines = []
            in_det_orient = False
            inserted = False
            for line in lines:
                if _re.match(r"\s*def\s+det_orient\s*\(", line):
                    in_det_orient = True
                    inserted = False
                    new_lines.append(line)
                    continue
                if in_det_orient and not inserted:
                    # Insert early return as the first line of the method body
                    indent = len(line) - len(line.lstrip())
                    pad = " " * indent
                    new_lines.append(pad + "# Patched for Modal: skip orientation detection.")
                    new_lines.append(pad + "return 0, None")
                    inserted = True
                    in_det_orient = False
                new_lines.append(line)
            tsr_py.write_text("\n".join(new_lines))
            print(f"[patch] Disabled orientation detection (fallback path) in {tsr_py}")
    else:
        print(f"[patch] WARN: {tsr_py} not found — skipping orientation-detection patch")

    # 11. Diagnostic + patch: locate the orientation-detection function in pdf_parser.py
    #     and replace it with a no-op that immediately returns (0, original_img, {}).
    #     The "Best table orientation" log confirmed the function lives in pdf_parser.py,
    #     returns (best_angle, best_img, results), and iterates OCR at 4 angles.
    pdf_parser_py = base / "deepdoc" / "parser" / "pdf_parser.py"
    if pdf_parser_py.exists():
        _content = pdf_parser_py.read_text(errors="replace")
        _lines = _content.splitlines()

        # Find the def that owns the "Best table orientation" log line.
        _orient_log_lineno = None
        for _i, _ln in enumerate(_lines):
            if "Best table orientation" in _ln:
                _orient_log_lineno = _i
                break

        if _orient_log_lineno is not None:
            # Walk backwards from the log line to find the enclosing def statement.
            _def_lineno = None
            _def_indent = None
            for _i in range(_orient_log_lineno, -1, -1):
                stripped = _lines[_i].lstrip()
                if stripped.startswith("def ") or stripped.startswith("async def "):
                    _def_lineno = _i
                    _def_indent = len(_lines[_i]) - len(_lines[_i].lstrip())
                    break

            if _def_lineno is not None:
                _def_line = _lines[_def_lineno]
                print(f"[patch-diag] Orientation detection function at pdf_parser.py:{_def_lineno + 1}")
                # Print function signature + a few lines for confirmation
                for _j in range(_def_lineno, min(_def_lineno + 6, len(_lines))):
                    print(f"  {_j + 1:4d}: {_lines[_j]}")

                # Patch: replace the BODY of this function with an early return.
                # We keep the def line and its docstring (if any), then insert
                # `return 0, <first_img_param>, {}` as the first executable line.
                # The function signature ends at the line containing '):'
                # Find the first line of the body (non-def, non-blank after the def).
                _body_start = _def_lineno + 1
                # Skip multi-line signature (lines that are part of the def header)
                while _body_start < len(_lines):
                    ln = _lines[_body_start]
                    stripped = ln.strip()
                    if stripped and not stripped.startswith("#"):
                        break
                    _body_start += 1

                # Determine body indentation
                _body_indent = " " * (_def_indent + 4)

                # Find the end of this function (next def at same or lower indent,
                # or EOF).
                _func_end = len(_lines)
                for _i in range(_def_lineno + 1, len(_lines)):
                    ln = _lines[_i]
                    if not ln.strip():
                        continue
                    cur_indent = len(ln) - len(ln.lstrip())
                    if cur_indent <= _def_indent and (
                        ln.lstrip().startswith("def ")
                        or ln.lstrip().startswith("async def ")
                        or ln.lstrip().startswith("class ")
                    ):
                        _func_end = _i
                        break

                # Extract the first non-self parameter name from the def line.
                # e.g. "def _evaluate_table_orientation(self, table_img, ..."
                # → first_param = "table_img"
                import re as _re2
                _sig_match = _re2.search(r"\(\s*self\s*,\s*(\w+)", _lines[_def_lineno])
                _img_param = _sig_match.group(1) if _sig_match else "table_img"
                print(f"[patch] Using img param '{_img_param}' for orientation no-op return")

                # Rebuild: keep def line(s), replace body with immediate return.
                # Return (0, <img_param>, {}) — 0 = no rotation, original image, empty results.
                new_lines = (
                    _lines[:_body_start]
                    + [
                        _body_indent + "# Patched for Modal: skip 4-pass OCR orientation detection.",
                        _body_indent + "# Compliance PDFs are always 0-degree standard orientation.",
                        _body_indent + "# This eliminates ~12 s × n_tables of GPU BFC arena exhaustion.",
                        _body_indent + f"return 0, {_img_param}, {{}}",
                    ]
                    + _lines[_func_end:]
                )
                pdf_parser_py.write_text("\n".join(new_lines))
                print(f"[patch] Patched orientation function body in pdf_parser.py:{_def_lineno + 1}")
            else:
                print("[patch] WARN: Could not find enclosing def for 'Best table orientation'")
        else:
            print("[patch] INFO: 'Best table orientation' not found in pdf_parser.py")
    else:
        print(f"[patch] WARN: {pdf_parser_py} not found")

    # 8. Verify critical files exist after sparse checkout
    critical = [
        base / "deepdoc" / "parser" / "pdf_parser.py",
        base / "deepdoc" / "vision" / "ocr.py",
        base / "deepdoc" / "vision" / "layout_recognizer.py",
        base / "deepdoc" / "vision" / "table_structure_recognizer.py",
        base / "common" / "file_utils.py",
    ]
    for f in critical:
        status = "OK" if f.exists() else "MISSING"
        print(f"[patch] {f.relative_to(base)}: {status}")


# ---------------------------------------------------------------------------
# Container image
# ---------------------------------------------------------------------------

image = (
    # CUDA 12.4 + cuDNN 9 runtime — required for onnxruntime-gpu 1.23.x
    # debian_slim has no CUDA libs so onnxruntime silently falls back to CPU
    modal.Image.from_registry(
        "nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04",
        add_python="3.11",
    )
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
    timeout=600,                    # 10 min max — covers 200-page PDFs on GPU
    scaledown_window=120,           # stay warm 2 min after last request
    volumes={str(VOLUME_PATH): models_volume},
    memory=16384,                   # 16 GB RAM
    secrets=[modal.Secret.from_name("vendorauditai-parser-secret")],
    # no retries — timeout failures are not transient; retrying just burns more GPU time
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
    # Raise ONNX BFC arena limit: RAGFlow reads this env var in ocr.py.
    # Default is "2048" MB (2GB) which fragments under 56-page OCR load.
    # T4 has 16GB VRAM; 6GB per arena gives OCR/layout/TSR plenty of room.
    os.environ.setdefault("OCR_GPU_MEM_LIMIT_MB", "6144")
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
    # 2a. Runtime monkey-patch: disable table orientation detection.
    #
    #     det_orient() runs OCR at 0°, 90°, 180°, 270° per table to find
    #     the best reading orientation.  After the main OCR pass the BFC
    #     arena is partially exhausted; each det_orient call then OOMs and
    #     retries 4× with 5 s delays — adding ~12 s per table × 27 tables
    #     = ~300 s of pure waste before timeout.
    #
    #     Compliance PDFs are always standard-orientation (0°).  Returning
    #     (0, None) immediately is safe and saves ~300 s.
    #
    #     IMPORTANT: det_orient is a MODULE-LEVEL function in
    #     table_structure_recognizer.py, not a class method.  Python resolves
    #     it via the module's __dict__ (global namespace), so we must patch
    #     the module object — patching the class attribute does nothing.
    # ------------------------------------------------------------------
    try:
        import inspect as _inspect
        import deepdoc.parser.pdf_parser as _pdf_parser_mod

        # The orientation-detection function lives in pdf_parser.py (confirmed by
        # build-time diagnostic at line 410).  It returns (best_angle, best_img, results).
        # Use inspect to find the exact method name so we don't hard-code it.
        _patched_orient = False
        for _attr_name in dir(_pdf_parser_mod.RAGFlowPdfParser):
            try:
                _method = getattr(_pdf_parser_mod.RAGFlowPdfParser, _attr_name)
                if not callable(_method):
                    continue
                _src = _inspect.getsource(_method)
                if "Best table orientation" in _src:
                    # Replace with a no-op that returns immediately.
                    # Signature: _evaluate_table_orientation(self, table_img, sample_ratio=0.3)
                    # → return (0, table_img, {}) meaning: no rotation, original image, no results.
                    def _noop_orient(self, table_img=None, *args, **kwargs):
                        return 0, table_img, {}
                    setattr(_pdf_parser_mod.RAGFlowPdfParser, _attr_name, _noop_orient)
                    log.info(
                        "Runtime patch applied: RAGFlowPdfParser.%s -> (0, img, {}) "
                        "[eliminates 4-pass OCR per table]",
                        _attr_name,
                    )
                    _patched_orient = True
                    break
            except Exception:
                continue

        if not _patched_orient:
            log.warning("Runtime patch: orientation method not found in RAGFlowPdfParser — "
                        "build-time patch in pdf_parser.py is the fallback")

    except Exception as _patch_exc:
        log.warning("Could not apply runtime orientation patch: %s — proceeding anyway", _patch_exc)

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
    timeout=700,                    # must exceed parse_document timeout (600s) + overhead
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

        result = await parse_document.remote.aio(pdf_bytes, filename, document_type)
        return result

    return web_app
