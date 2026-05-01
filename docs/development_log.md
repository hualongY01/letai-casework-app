# Development Log

## 2026-04-30

### Completed

- Created the backend Python virtual environment at `backend/.venv`.
- Installed backend dependencies: FastAPI, SQLModel, Pydantic, PyMuPDF, Pillow, and related packages.
- Installed test dependencies: pytest and httpx.
- Fixed SQLite initialization so `init_db()` imports model metadata before creating tables.
- Implemented `POST /api/sources/import`:
  - Accept uploaded files.
  - Copy files into `storage/evidence_archive/{source_uid}/original/`.
  - Calculate SHA-256 hashes.
  - Write `Source` records.
- Implemented `GET /api/sources`.
- Completed a local smoke test:
  - Uploaded a TXT sample.
  - API returned 200.
  - SQLite could query the source record.
  - The evidence archive contained the archived file.
- Added automated tests:
  - `tests/test_contracts.py`
  - `tests/test_source_import.py`
- Implemented the TXT/Markdown parser:
  - Added `POST /api/sources/{source_uid}/parse`.
  - Added `GET /api/chunks`.
  - Added `GET /api/evidence`.
  - Archived text can produce `DocumentChunk` and `EvidenceSpan` records.
- Added `tests/test_text_parse.py`.
- Implemented the extractable-text PDF parser:
  - Uses PyMuPDF to extract text page by page.
  - Preserves `page_start/page_end` on `DocumentChunk`.
  - Preserves page locators and parser metadata in `EvidenceSpan.locator_json`.
- Implemented the DOCX parser:
  - Extracts paragraphs.
  - Extracts table rows.
- Implemented the XLSX parser:
  - Uses `openpyxl` to read workbooks.
  - Creates chunks per sheet/row.
  - Preserves `sheet_name`, `row_start`, and `row_end`.
- Implemented page rendering:
  - Added `POST /api/sources/{source_uid}/render-pages`.
  - Added `GET /api/ocr-pages`.
  - Renders PDFs to `storage/evidence_archive/{source_uid}/pages/page-XXXX.png`.
  - Normalizes image files to `page-0001.png`.
  - Writes `OCRPage` records with `page_image_path`, `page_image_hash`, and `ocr_engine=pending`.
- Installed the local OCR engine:
  - Homebrew `tesseract`
  - Homebrew `tesseract-lang`
  - Python `pytesseract`
- Implemented the local OCR adapter:
  - Added `POST /api/ocr-pages/{ocr_page_uid}/run-ocr`.
  - Added `GET /api/ocr-blocks`.
  - Writes OCR results to `OCRBlock`.
  - Creates one `EvidenceSpan` per OCR block.
  - Preserves `bbox`, `ocr_engine`, `ocr_confidence`, and page number in `EvidenceSpan.locator_json`.
- Implemented the candidate fact creation API:
  - Added `POST /api/candidates`.
  - Creates `FactCandidate` records from stored evidence.
  - Validates that evidence and source match.
- Completed the minimal human confirmation loop through `POST /api/candidates/confirm`:
  - A `FactCandidate` can be confirmed into a `FactCard`.
  - Users may edit candidate text before confirmation.
  - `edited_from_candidate` and `edit_reason` are preserved.
- Added tests:
  - `tests/test_pdf_parse.py`
  - `tests/test_docx_parse.py`
  - `tests/test_xlsx_parse.py`
  - `tests/test_page_render.py`
  - `tests/test_ocr_run.py`
  - `tests/test_candidate_flow.py`

### Validation

```text
10 passed in 0.84s
```

### Not Completed

- Chunk/evidence/page render/OCR idempotency and rerun rules.
- LLM-based FactCandidate extraction.
- Confirmed FC versioning.
- Real case-material ingestion.

## 2026-05-01 · Idempotency and Force Reruns

### Completed

- Added idempotency to `POST /api/sources/{source_uid}/parse`:
  - Repeated calls return existing `DocumentChunk` records by default.
  - Existing chunk/evidence records are not duplicated.
  - Supports `force=true`.
  - If old evidence is already referenced by `FactCandidate` or `FactCard`, `force=true` returns 409.
- Added idempotency to `POST /api/sources/{source_uid}/render-pages`:
  - Repeated calls return existing `OCRPage` records by default.
  - Pages are not re-rendered unless forced.
  - If old OCR evidence is referenced by a candidate or FC, rerun is rejected.
- Added idempotency to `POST /api/ocr-pages/{ocr_page_uid}/run-ocr`:
  - Repeated calls return existing `OCRBlock` records by default.
  - OCR block/evidence records are not duplicated.
  - Supports `force=true`.
  - If old OCR evidence is referenced by a candidate or FC, rerun is rejected.
- Added `tests/test_idempotency.py`:
  - Covers default idempotency for parse, render-pages, and run-ocr.
  - Covers forced parse rebuild.
  - Covers force rejection when evidence is already referenced by a candidate.

### Validation

```text
backend: 15 passed
frontend: tsc --noEmit passed
```

### Not Completed

- LLM-based FactCandidate extraction.
- Confirmed FC versioning.
- Real case-material ingestion.

## 2026-05-01 · LLM Candidate Fact Extraction

### Completed

- Added local sensitive-information redaction:
  - ID numbers -> `[REDACTED_ID_NUMBER]`
  - Phone numbers -> `[REDACTED_PHONE]`
  - 12-30 digit bank accounts / long numeric accounts -> `[REDACTED_BANK_ACCOUNT]`
  - Address fields -> `[REDACTED_ADDRESS]`
- Added the `LLMCallLog` table:
  - Records `source_uid`
  - Records `chunk_uid`
  - Records `prompt_version`
  - Records `model`
  - Records redacted input text
  - Records LLM output JSON
  - Records call status and errors
- Added LLM candidate extraction:
  - Processes one `DocumentChunk` at a time.
  - Does not upload full files.
  - Does not upload OCR images.
  - Uses prompt version `fact_candidate_extraction_v0.1`.
  - Creates only `FactCandidate` records, never confirmed FC records.
  - Skips duplicate candidates for the same evidence, proposed fact text, model, and prompt version.
- Added APIs:
  - `POST /api/chunks/{chunk_uid}/extract-candidates`
  - `GET /api/llm-call-logs`
- If `LETAI_LLM_API_KEY` or `LETAI_LLM_MODEL` is not configured, automatic extraction returns 409 while import, parsing, OCR, and manual review remain available.
- Updated the static frontend `frontend/static/index.html` with:
  - Chunk list
  - "Extract candidates with LLM" action
  - Candidate list
  - LLM call-log summary
- Added `tests/test_llm_extraction.py`:
  - Covers sensitive-information redaction.
  - Covers LLM candidate creation, call logs, and duplicate skipping.
  - Covers the 409 response when no API key is configured.

### Validation

```text
backend: 18 passed
frontend: tsc --noEmit passed
```

### Not Completed

- Confirmed FC versioning.
- Real case-material ingestion.
- Static frontend import and parse/render controls.

## 2026-05-01 · OCR Review UI (Earlier Stage)

### Completed

- Added backend page-image retrieval:
  - `GET /api/ocr-pages/{ocr_page_uid}/image`
  - Returns OCR page PNG files for frontend highlight review.
- Enabled local development CORS:
  - `http://localhost:5173`
  - `http://127.0.0.1:5173`
- Connected the React/TypeScript frontend source to real APIs:
  - `/api/ocr-pages`
  - `/api/ocr-blocks`
  - `/api/evidence`
  - `/api/ocr-pages/{ocr_page_uid}/image`
  - `/api/ocr-pages/{ocr_page_uid}/run-ocr`
  - `/api/candidates`
- Implemented real OCR page images, bbox overlay, block list, and candidate creation in the frontend.
- Added `frontend/static/index.html`:
  - No build step required.
  - Calls FastAPI directly.
  - Currently used as the runnable v0.1 frontend.
- Changed frontend `npm run build` to TypeScript type checking.

### Validation

```text
backend: 10 passed
frontend: tsc --noEmit passed
```

### Notes

- Vite build hangs under the current Node 25 environment, so it is temporarily outside the v0.1 runtime path.
- v0.1 currently uses `frontend/static/index.html` as the runnable frontend.

### Not Completed

- Confirmed FC versioning.
- Real case-material ingestion.
