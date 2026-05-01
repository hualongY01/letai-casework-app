# Decision Log

## 2026-04-30

1. The application is positioned as a local factbase, not a NotebookLM clone.
2. The v0.1 flow is: file import -> chunk/evidence -> FactCandidate -> item-by-item human confirmation -> confirmed FC -> read-only Vault export.
3. Scanned PDF and image OCR are included in v0.1.
4. OCR must run locally.
5. OCR output must preserve page snapshots and bbox coordinates.
6. v0.1 must provide a basic OCR highlight review UI.
7. v0.1 uses a local web application shape.
8. Original files are copied into the evidence archive.
9. Archived files are not physically deleted by default.
10. A new source version creates a new source version and does not overwrite the old one.
11. Human confirmation may edit candidate fact text.
12. Confirmed FC records cannot be overwritten in place and may only be superseded by new versions.
13. Factual conflicts are not auto-resolved.
14. Source authority levels use built-in defaults first and may become project-configurable later.
15. The fact schema uses generic categories plus Letai-specific tags.
16. v0.1 provides only a Fact Gateway mock before full subagent integration.
17. The LLM processes only chunks, and sensitive information is redacted by default.
