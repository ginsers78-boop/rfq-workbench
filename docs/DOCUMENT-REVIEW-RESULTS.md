# Document review checkpoint — 2026-10-19

## Verified behavior

All 31 Python automated checks passed, including a mixed text/scanned PDF that is rejected without accepting a partial extraction. JavaScript syntax checks also passed.

The browser automation runs against a real loopback HTTP server, real SQLite and the installed local `qwen3.5:9b`. There are no intercepted model/API responses.

- Real TXT, text-layer PDF, DOCX and XLSX each produced four positions from the fictional requirement. Quantities, units, categories and original line numbers were checked for every returned position. Model times in the first passing browser run were 10.94 / 6.50 / 6.57 / 6.66 seconds respectively. These are one small fixture in different formats, not four independent quality benchmarks.
- The missing quantity/unit stayed null. Approval failed until human corrections were supplied. A corrected quantity of 25 was used only as a fictional review test, not inferred from the source.
- Save, page reload, reopen and saved-JSON download preserved the corrected record. A missed line could be added with a source quotation. The unapproved addition returned the record to NEEDS REVIEW.
- An actual image-only PDF and a corrupted PDF produced readable errors. PDF page count, encryption, empty documents, size limits, malformed Office files, UTF-8 text limits and spreadsheet formulas are covered by automated reader tests.
- Persistence is checked by reopening the SQLite database through a new Store instance. Concurrent stale writes, permanent IDs, immutable original source metadata, invalid approval data and deletion have automated checks.
- Browser scripts reported no page errors and no horizontal overflow at 390 px. Desktop and mobile screenshots were inspected.
- Cross-origin/token failures are rejected; HTTP tests cover Host checks, invalid requests, upload size headers, unknown records, security headers and blocked filesystem paths.

Detailed local reports, exported JSON, generated test documents and screenshots are in ignored `data/`. Browser-created test records are deleted after a successful run.

## Limits of this evidence

This is a local document review checkpoint, not a finished client delivery. It does not establish 90% production extraction accuracy, semantic matching quality, 30–50 enquiries/day throughput, supplier privacy, Gmail drafts, OCR, quotation generation or an always-on public deployment. Internal JSON explicitly contains customer/source information and must not be shared with suppliers.

The original model response and latest reviewed version are retained separately; a complete edit-by-edit audit log and reviewed exclusion of false-positive rows remain open work. Uploaded binaries are not retained. Extracted text is intentionally persisted locally, and deletion does not remove external backups/exports.
