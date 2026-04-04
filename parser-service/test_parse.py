"""
VendorAuditAI Parser Service — local test client.

Sends a PDF to the running Modal service (modal serve OR modal deploy)
and prints the returned chunks.

Usage
-----
  # 1. Start the service locally (separate terminal):
  #    modal serve modal_app.py
  #
  # 2. Run this test against a real PDF:
  #    python test_parse.py path/to/soc2_report.pdf --type soc2
  #
  # 3. Against the deployed (production) endpoint:
  #    python test_parse.py path/to/soc2_report.pdf --url https://your-org--vendorauditai-parser-fastapi-app.modal.run
"""

import argparse
import base64
import json
import os
import sys
import httpx

DEFAULT_LOCAL_URL = "http://localhost:8000"   # modal serve default

def parse_args():
    p = argparse.ArgumentParser(description="Test the VendorAuditAI parser service.")
    p.add_argument("pdf", help="Path to a PDF file to parse")
    p.add_argument(
        "--type",
        default="soc2",
        choices=["soc2", "iso27001", "sig_lite", "sig_core", "hecvat", "caiq", "pentest", "other"],
        help="Document type (controls chunking strategy)",
    )
    p.add_argument(
        "--url",
        default=DEFAULT_LOCAL_URL,
        help="Base URL of the parser service",
    )
    p.add_argument(
        "--secret",
        default=os.environ.get("PARSER_SERVICE_SECRET", ""),
        help="Bearer token (or set PARSER_SERVICE_SECRET env var)",
    )
    p.add_argument(
        "--output",
        help="Optional: write full JSON response to this file",
    )
    return p.parse_args()


def main():
    args = parse_args()

    pdf_path = args.pdf
    if not os.path.isfile(pdf_path):
        print(f"ERROR: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    if not args.secret:
        print(
            "WARNING: no PARSER_SERVICE_SECRET set. "
            "Request will likely return 401.\n"
            "Set it with:  export PARSER_SERVICE_SECRET=your-secret",
            file=sys.stderr,
        )

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pdf_b64   = base64.b64encode(pdf_bytes).decode()
    filename  = os.path.basename(pdf_path)
    file_size = len(pdf_bytes) / (1024 * 1024)

    print(f"File    : {filename} ({file_size:.1f} MB, {len(pdf_bytes):,} bytes)")
    print(f"Type    : {args.type}")
    print(f"Endpoint: {args.url.rstrip('/')}/parse")
    print()

    payload = {
        "pdf_b64":       pdf_b64,
        "filename":      filename,
        "document_type": args.type,
    }

    headers = {}
    if args.secret:
        headers["Authorization"] = f"Bearer {args.secret}"

    print("Sending request… (this may take 30-120 s on first call / cold start)")

    try:
        resp = httpx.post(
            f"{args.url.rstrip('/')}/parse",
            json=payload,
            headers=headers,
            timeout=600.0,
        )
    except httpx.ConnectError as e:
        print(f"\nERROR: Could not connect to {args.url}\n{e}", file=sys.stderr)
        print("Is the service running?  Try:  modal serve modal_app.py", file=sys.stderr)
        sys.exit(1)

    print(f"HTTP status : {resp.status_code}")

    if resp.status_code != 200:
        print(f"Response    : {resp.text[:1000]}")
        sys.exit(1)

    data = resp.json()

    chunks     = data.get("chunks", [])
    page_count = data.get("page_count", 0)

    print(f"Pages       : {page_count}")
    print(f"Chunks      : {len(chunks)}")
    print()

    # Print first 5 chunks as a preview
    print("=" * 70)
    print(f"CHUNK PREVIEW (first {min(5, len(chunks))} of {len(chunks)})")
    print("=" * 70)
    for i, chunk in enumerate(chunks[:5]):
        page    = chunk.get("page")
        header  = chunk.get("section_header") or "(no header)"
        tokens  = chunk.get("token_count", 0)
        content = chunk.get("content", "")
        preview = content[:300].replace("\n", " ")
        if len(content) > 300:
            preview += "…"

        print(f"\n[Chunk {i+1}]  page={page}  tokens≈{tokens}")
        print(f"  Header : {header[:80]}")
        print(f"  Content: {preview}")

    print("\n" + "=" * 70)

    # Stats
    if chunks:
        token_counts = [c.get("token_count", 0) for c in chunks]
        avg_tokens   = sum(token_counts) / len(token_counts)
        max_tokens   = max(token_counts)
        min_tokens   = min(token_counts)
        print(f"\nChunk token stats:")
        print(f"  avg ≈ {avg_tokens:.0f}   min = {min_tokens}   max = {max_tokens}")

        with_header = sum(1 for c in chunks if c.get("section_header"))
        print(f"  Chunks with detected section header: {with_header}/{len(chunks)}")

    # Optional: save full response
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nFull response written to: {args.output}")


if __name__ == "__main__":
    main()
