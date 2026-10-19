# Project agreement and evidence

**Publication status: unfinished portfolio beta.** See [ROADMAP](../ROADMAP.md) for all remaining work. If the repository receives enough stars and community interest, its author will return, publish updates and complete the remaining functionality; no completion date is announced.

## Source and scope

Independent portfolio build based on a trading-company enquiry-to-quotation brief. There is no real client engagement, existing prototype access, production deployment restriction document or real acceptance dataset. Fictional inputs must be labeled as such.

## Required stages

1. Document upload → structured line extraction → review of every line and supplier selection → per-category Gmail RFQ drafts with BCC suppliers and an Excel reply template. Preserve RFQ references, source line numbers, permanent supplier IDs and header-based sheet columns.
2. Gmail intake, request classification, revisions/duplicate handling and permitted portal intake. Manual portal upload is an explicit feature of the brief; unsupported portal automation must not be invented.
3. Supplier reply intake, RFQ/line matching, reminders, currencies/units/validity/MOQ/lead-time normalization, landed cost and supplier comparisons. WhatsApp is optional and requires a separately agreed integration.
4. Accounting/email backfill and semantic price/quotation history. Genuine embeddings/vector search, not an exact-code lookup presented as semantic matching.
5. Margin policies, minimum floors, exception approvals, partial quotes and PDF quotations held as Gmail drafts for user approval.
6. Won/lost/no-response outcomes, customer PO matching, operational reports, handover and acceptance evidence.

## Acceptance targets

- At least 20 real requirements for stages 1–2 and 20 real supplier replies for stage 3, supplied by a real client with permission to process them.
- At least 90% correct line extraction on typed PDFs and spreadsheets, under an agreed field-level scoring definition.
- At least 85% correct historical matches within the top three suggestions on a client-supplied test set.
- No customer names, customer references or selling prices in supplier emails. Supplier-facing exports must use an explicit field allowlist and privacy checks before draft creation.
- Every uncertain extraction requires review. JSON validity is not evidence of correct interpretation.
- Documentation and recorded walkthrough per stage. A real delivery would include the specified 30-day bug-fix period after final acceptance; this portfolio exercise does not claim such a client acceptance has occurred.

## Development environment verified

Verification used a local GPU-capable development environment and the Ollama API with `qwen3.5:9b`. Hardware and model files are not included. No paid provider was connected.

The first real structured-output experiment returned all four line records, but omitted the three supplied units and assigned the PVC elbow to Fasteners. Its observed duration was 108.9 seconds. This failed semantic quality despite valid JSON. Prompt design, category definitions and verification therefore precede the user interface.

## Initial architecture direction

- Separate document readers, model provider, schema validation, business rules, persistence and Gmail/Sheets adapters.
- Start with local inference for evaluation. Keep model calls in one provider module; do not connect a paid provider now or create placeholder providers.
- A proper persistent database is required for workflow and audit records. Exact production database/deployment selection remains pending validation of the processing workload and data volume. Do not present an in-memory or spreadsheet-only prototype as the final history database.
- A public Cloudflare interface cannot directly depend on an unexposed localhost model as an always-on service. The local evaluation mode must be labeled honestly. Production hosting/LLM costs must be measured and funded by a real client before enabling them.
- Gmail drafts and reminders require authorization in a test mailbox. Do not send messages or create external artifacts merely to make a screenshot.

## Status

Current deliverable: a working local document-to-reviewed-record application plus the extraction benchmark. Actual TXT, typed PDF, DOCX and XLSX readers, persistent SQLite records, original model output, stable line IDs, source quotations, human corrections, manual missing-line addition, approval checks, stale-write protection, internal JSON downloads and record deletion are implemented and tested. The loopback server includes Host/Origin checks, per-session request tokens and restrictive browser security headers; this is a single-user local application, not a public service.

The local RFQ checkpoint adds a supplier registry with stable IDs and revision checks, per-category BCC selection, reasoned line exclusions and saved requirement revision history. Privacy confirmation plus explicit field allowlists and a separate final ZIP/Office XML scan precede local preview approval and download. Genuine Excel templates preserve RFQ and line identifiers. Stale packages are blocked after requirement/supplier edits. The dispatch ZIP is internal; only the reviewed body and its Excel attachment are intended for supplier correspondence.

The local OCR checkpoint adds genuine local vision transcription for PNG/JPEG/WebP, scanned PDFs and mixed PDFs, with a durable background queue, real interruption recovery, stored review previews and an explicit source-verification gate. Manual image transcriptions carry page provenance and do not overwrite the original OCR. Embedded Office images are explicitly rejected rather than silently dropped.

Long-document processing now partitions complete source sections without overlap, uses supplied source-record IDs for multipart provenance, retains raw part responses, verifies simple literal quantity/unit values and preserves repeated original numbers using stable line IDs/offsets. A full-source coverage confirmation is required for multipart review. Limits remain explicit: 1 MiB extracted text, 1,000 products, 12,000 bytes per continuous record/paragraph, and separate dense-page OCR limits.

The first milestone remains open. Embedded Office image OCR, Gmail/Sheets integration, the representative acceptance dataset and the recorded milestone walkthrough are outstanding. Complex layouts and the documented long-document limits remain acceptance boundaries. Privacy tests establish rejection of declared/suggested confidential markers, not automatic recognition of every unknown secret. See the checkpoint evidence, including `LONG-DOCUMENT-RESULTS.md`.
