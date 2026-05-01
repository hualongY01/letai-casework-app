# Letai Local Factbase Product Spec v0.1

## 1. Product Definition

This application is a local NotebookLM-like replacement for factual material processing. It converts source materials into traceable, verifiable factual assets that downstream LLMs and subagents can consume.

It is not a generic chat tool, a simple RAG Q&A app, a writing app, or a NotebookLM product clone. Its core responsibility is fact-entry control: source archiving, parsing/OCR, chunk/evidence creation, candidate facts, human confirmation, and Fact Gateway access. Downstream LLMs and subagents should consume only sourced, auditable, status-aware factual context.

## 2. Core Users

- The project owner
- Codex / LLM runtime
- Future downstream subagent workflows

v0.1 is not designed for direct use by outside counsel, financial advisors, commercial leasing teams, or creditors.

## 3. Inputs

### Source Materials

- PDF, including text PDFs and scanned PDFs
- Images: PNG, JPG, JPEG, TIFF
- DOCX
- XLSX
- TXT / Markdown

### Metadata

- Project name
- Source origin
- Submitter
- Received date
- Material type
- Confidentiality level
- Business line

### Human Actions

- Confirm candidate facts
- Edit candidate facts before confirmation
- Reject candidate facts
- Mark OCR errors
- Generate FR records
- Handle factual conflicts

## 4. Outputs

### Database Outputs

- Source
- DocumentChunk
- EvidenceSpan
- OCRPage / OCRBlock
- FactCandidate
- ConfirmedFact
- FactCard
- FactRequest
- ConflictRecord
- AuditLog

### File Outputs

- Read-only Vault Markdown
- Ingestion report
- OCR review record
- Conflict report
- Fact Gateway context pack

## 5. Main Flow

```text
File import
-> copy into evidence archive
-> calculate hash
-> parse text or run local OCR
-> create chunk / evidence
-> LLM extracts FactCandidate records
-> validate references and fields
-> item-by-item human confirmation
-> confirmed FC
-> read-only Vault export
-> Fact Gateway mock
```

## 6. Confirmed Rules

1. SQLite is the sole source of truth.
2. Vault Markdown is read-only and must not be manually edited.
3. Imported originals are copied into the evidence archive.
4. Archived files are not physically deleted by default; only logical status changes are allowed.
5. A new source version creates a new source record and does not overwrite the previous version.
6. Scanned PDFs and images must use local OCR.
7. OCR output must preserve page snapshots and bbox coordinates.
8. v0.1 must provide a basic OCR highlight review UI.
9. Candidate facts become confirmed FC records only after item-by-item human confirmation.
10. Human confirmation may edit candidate text, but the edit record must be preserved.
11. Confirmed FC records cannot be overwritten in place; new versions must be created.
12. Factual conflicts are not auto-resolved; humans choose the handling path.
13. Source authority levels use built-in defaults first and may become project-configurable later.
14. v0.1 uses generic fact categories plus Letai-specific tags.
15. v0.1 provides a Fact Gateway mock before full subagent integration.
16. The LLM processes only chunks and never full files.
17. Sensitive information is redacted locally before LLM calls.
18. OCR images are not sent to cloud multimodal models by default.

## 7. v0.1 Acceptance

Backtest with 3 to 5 controlled real materials, including at least:

- 1 scanned PDF
- 1 text PDF or DOCX
- 1 Excel file
- 1 material that can be compared against an existing FC
- Optional: 1 material with factual conflict or source-version relationships

Acceptance flow:

```text
Import -> OCR/parse -> chunk/evidence -> candidate -> human confirmation -> FC -> Vault export -> Fact Gateway mock
```
