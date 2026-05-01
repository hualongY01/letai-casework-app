# Letai Local Factbase

This repository contains a local NotebookLM-like replacement for handling Letai case materials.

It is not intended to clone the NotebookLM product, and it is not a general chat or writing app. Its purpose is to turn source materials into traceable, citable, reviewable, human-confirmed factual context so that downstream LLMs and subagents work from grounded evidence instead of hallucinated summaries caused by large files, scanned PDFs, or context-window limits.

Core flow:

```text
File import
-> chunk / evidence
-> FactCandidate
-> item-by-item human confirmation
-> confirmed FC
-> read-only Vault export
-> Fact Gateway mock
```

## Positioning

- Local NotebookLM-like fact-material processing layer.
- Fact-entry control layer for downstream LLMs and subagents.
- SQLite is the sole source of truth.
- Vault Markdown is a read-only projection and must not be manually edited.
- Imported originals are copied into the evidence archive and hashed.
- Confirmed FC records cannot be overwritten in place; later changes must create new versions.
- v0.1 does not formally integrate downstream subagents. It only validates fact-pack format and boundaries through the Fact Gateway mock.

## v0.1 Scope

Supported:

- PDF, including text PDFs and scanned PDFs
- PNG / JPG / JPEG / TIFF
- DOCX
- XLSX
- TXT / Markdown
- Local OCR
- OCR page snapshots and bbox highlight review
- LLM-generated FactCandidate records, using chunks only, never full files
- Local redaction before LLM calls for ID numbers, phone numbers, bank accounts, and addresses
- LLM call logging with source, chunk, prompt version, model, and output
- Item-by-item human confirmation for candidate facts
- Read-only Vault export for confirmed FC records

Out of scope for v0.1:

- Multi-user permissions
- Cloud deployment
- NotebookLM upload
- Gmail automation
- Full subagent workflow integration
- Automatic final reports

## Repository Boundary

This repository may contain only application code, schemas, documentation, and redacted examples.

Do not commit:

- Real case source materials
- Office / PDF / archive originals
- `.env`
- API keys or tokens
- Full unredacted fact-card datasets
- Unredacted email bodies

## Directory Layout

```text
backend/      Python + FastAPI backend
frontend/     React + TypeScript local review UI
schemas/      JSON schemas
docs/         Product, architecture, and decision documents
```

## Next Steps

1. Implement confirmed FC versioning.
2. Backtest import, parsing, rendering, OCR, and candidate confirmation with controlled real materials.
3. Add import/review UI controls so routine use does not depend on manual API calls.
4. Revisit the React/Vite build chain after Node/Vite compatibility is resolved.

## LLM Candidate Extraction

If no API key is configured, the system can still import, parse, OCR, index, display evidence, and let users create candidates manually. It cannot automatically extract candidates.

Configuration example:

```bash
LETAI_LLM_PROVIDER=openai
LETAI_LLM_API_KEY=...
LETAI_LLM_MODEL=...
```

Endpoints:

```text
POST /api/chunks/{chunk_uid}/extract-candidates
GET  /api/llm-call-logs
```

Rules:

- The LLM receives only redacted text from a single chunk.
- Original files are not uploaded.
- OCR page images are not uploaded.
- The LLM may create only `FactCandidate` records, never confirmed FC records.
- Every call is recorded in `LLMCallLog`.

## Local Backend Commands

```bash
cd /Users/controller/Documents/Codex/letai-casework-app/backend
python3 -m venv .venv
.venv/bin/python -m pip install .
PYTHONPATH=src .venv/bin/python -c "from letai_factbase.db.session import init_db; init_db()"
PYTHONPATH=src .venv/bin/python -m pytest
PYTHONPATH=src .venv/bin/uvicorn letai_factbase.main:app --reload
```

The frontend currently has two entry points:

- `frontend/src/`: React + TypeScript source, validated by `tsc`.
- `frontend/static/index.html`: no-build OCR review page, currently used as the runnable v0.1 UI.

```bash
cd /Users/controller/Documents/Codex/letai-casework-app/frontend/static
python3 -m http.server 5173 --bind 127.0.0.1
```

Open after startup:

```text
http://127.0.0.1:5173/
```
