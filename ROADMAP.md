# Project status and unfinished work

RFQ Workbench is an **unfinished portfolio beta**, not a completed freelance delivery. It currently runs as a local, single-user application. There is no public hosted version, production acceptance or connected customer account.

## Working and tested locally

- TXT, text PDF, text/table Word and Excel reading; local vision OCR for images and scanned/mixed PDFs.
- Bounded multipart processing for long sources, source excerpts and persistent processing queue.
- SQLite records, permanent identifiers, corrections, review confirmations, history and internal JSON export.
- Supplier directory and category selection; reviewed RFQ message bodies and genuine Excel reply templates in a local ZIP.
- Declared confidential-data checks and explicit human review before local export. Automatic detection of every possible secret is not claimed.

See `docs/*RESULTS.md` for the scope and limitations of each test checkpoint. Fictional tests do not establish real-customer accuracy.

## Still to be completed

1. **Finish document-to-RFQ:** OCR for images embedded in DOCX/XLSX; broader complex-layout evaluation; authorized Gmail draft creation with BCC and attachments; Google Sheets integration; final walkthrough and representative acceptance testing.
2. **Enquiry intake:** Gmail ingestion, classification, revision tracking, duplicate handling and agreed portal intake.
3. **Supplier replies:** real reply ingestion, RFQ/line matching, reminders, validity/MOQ/lead-time handling, unit/currency normalization, landed cost and supplier comparison.
4. **Quotation history:** authorized accounting/email imports, genuine embeddings and semantic historical matching, measured top-three match quality.
5. **Customer quotations:** margin policies, price floors, exception approvals, partial offers, PDF quotation generation and approved Gmail drafts.
6. **Operations and delivery:** outcomes, customer purchase-order matching, reports, maintenance guidance, deployment architecture, production security/privacy checks and handover.

Acceptance needs a permitted, representative dataset: at least 20 real requirements and 20 real supplier replies, agreed field-level scoring and historical-match labels. The original brief's 90% extraction and 85% top-three history targets have not been demonstrated on such data.

## Current operating limits

The computer and Ollama must remain on. Inference is local; no paid API is connected. Files are limited to 10 MB, PDFs to 50 pages and extracted text to 1 MiB. The partitioner supports bounded source blocks; a continuous block above 12,000 UTF-8 bytes fails explicitly. OCR requires source comparison and has a separate per-page output limit. Embedded Office images and spreadsheet formulas are rejected rather than silently ignored. This server is bound to localhost; do not expose it as a public multi-user service.

## Stars and future development

If this repository receives enough stars and community interest, I will return to it, publish updates and complete the remaining functionality myself. There is no announced star threshold or completion date. Stars indicate interest; they do not mean that unfinished features are already available or create a support/service commitment.

Until then, use the documented working features and treat all items above as unfinished. No paid service will be silently enabled.
