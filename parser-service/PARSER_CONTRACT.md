# VendorAuditAI External Parser Contract

This document defines the HTTP interface that any external GPU parser service must implement
to integrate with VendorAuditAI's configurable parser provider system.

Once your service implements this contract, users can connect it via:
**Organization Settings → Document Processing → External GPU Parser**

---

## Endpoints

### `GET /health`

Health check. No authentication required.

**Response 200**
```json
{"status": "ok"}
```

VendorAuditAI calls this endpoint when the user clicks **Test Connection** in Settings.
Any non-200 response is treated as a failure.

---

### `POST /parse`

Parse a PDF document and return structured chunks.

**Request headers**
```
Authorization: Bearer <api_key>
Content-Type: application/json
```

**Request body**
```json
{
  "pdf_b64": "<base64-encoded PDF bytes>",
  "filename": "vendor-soc2-report.pdf",
  "document_type": "soc2"
}
```

| Field | Type | Description |
|---|---|---|
| `pdf_b64` | string | Base64-encoded PDF file bytes |
| `filename` | string | Original filename (use as hint for document type detection) |
| `document_type` | string | See document type values below |

**`document_type` values**

| Value | Document |
|---|---|
| `soc2` | SOC 2 Type I or Type II report |
| `iso27001` | ISO 27001 certification or audit report |
| `sig_lite` | SIG Lite questionnaire |
| `sig_core` | SIG Core questionnaire |
| `hecvat` | HECVAT (Higher Education Community Vendor Assessment Tool) |
| `caiq` | CSA CAIQ (Consensus Assessments Initiative Questionnaire) |
| `pentest` | Penetration test report |
| `other` | Any other document type |

**Response 200**
```json
{
  "chunks": [
    {
      "content": "CC6.1 — Logical and Physical Access Controls\n\nThe organization restricts logical access...",
      "page": 14,
      "section_header": "CC6.1",
      "token_count": 142
    }
  ],
  "page_count": 54,
  "filename": "vendor-soc2-report.pdf"
}
```

| Field | Type | Description |
|---|---|---|
| `chunks` | array | List of text chunks (see below) |
| `page_count` | integer | Total pages in the document |
| `filename` | string | Echo of the input filename |

**Chunk object**

| Field | Type | Required | Description |
|---|---|---|---|
| `content` | string | yes | Text content of the chunk |
| `page` | integer \| null | no | Page number where this chunk appears (1-indexed) |
| `section_header` | string \| null | no | Section or control ID heading (e.g. `"CC6.1"`, `"A.9.1"`) |
| `token_count` | integer | no | Approximate token count (word-split estimate is fine) |

**Error responses**

| Status | Meaning |
|---|---|
| 401 | Invalid or missing Bearer token |
| 422 | Malformed request body |
| 500 | Internal parser error |

On 4xx/5xx, VendorAuditAI logs the error and falls back to the built-in docling parser.
The document will still be processed — no upload failure is surfaced to the end user.

---

## Timeout

VendorAuditAI waits up to **600 seconds** for a `/parse` response. This accommodates cold
starts on serverless GPU platforms (e.g. Modal, RunPod) and large documents (150+ pages).

If your service cannot respond within 600 seconds, return a partial result rather than timing out.

---

## Chunking recommendations

For compliance documents (SOC 2, ISO 27001, etc.), chunk boundaries should ideally align with:
- Control IDs (`CC6.1`, `SI-7`, `A.9.1.2`)
- Section headings
- Table boundaries (keep tables intact within a single chunk)

VendorAuditAI uses `section_header` values to group findings during analysis. Returning
control IDs as `section_header` values significantly improves analysis quality.

---

## Reference implementation

`modal_app.py` in this directory is the reference implementation. It wraps RAGFlow's DeepDoc
PDF parser (YOLOv10 layout detection + PaddleOCR) and deploys as a serverless GPU function
on Modal.com.

To deploy your own instance:
1. Install Modal: `pip install modal`
2. Authenticate: `modal token new`
3. Create a secret: `modal secret create vendorauditai-parser-secret PARSER_SERVICE_SECRET=<your-token>`
4. Run the model downloader: `modal run download_models.py`
5. Deploy: `modal deploy modal_app.py`
6. Copy the deployment URL and your secret value into VendorAuditAI Settings

---

## Testing

Use `test_parse.py` to verify your deployment against the contract:

```bash
cd parser-service
pip install -r requirements-dev.txt

python test_parse.py \
  --url https://your-service.example.com \
  --key your-api-key \
  --pdf path/to/test.pdf
```

Expected output:
```
[+] Health check: ok
[+] Parse complete: 54 pages, 1467 chunks
[+] Avg tokens/chunk: 68
[+] Sample chunk:
    page=14  header="CC6.1"
    "CC6.1 - Logical and Physical Access Controls..."
```
