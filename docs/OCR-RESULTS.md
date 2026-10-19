# Local vision OCR checkpoint — 2026-10-19

Historical checkpoint: the whole-document text limit described below was subsequently replaced by bounded multipart processing. See [Long-document results](LONG-DOCUMENT-RESULTS.md) for current limits and additional evidence.

## Verified behavior

56 Python checks passed. New coverage includes genuine PDF-to-image rendering, bounded image preparation, transparency handling, invalid/animated images, missing-image provenance, durable queue state, upload-storage consent, cancellation/purging, interrupted-state recovery, one application owner per database, OCR source-verification gates, preview deletion and manual image transcription with immutable page provenance. Existing document review, supplier and RFQ checks remain included.

The first actual vision probe sent a fictional four-position image to the installed local `qwen3.5:9b`. All visible product lines, technical details, quantities/units and confidential customer headers were transcribed. A separate white image returned empty text and readable=false. The first printed-image call took 86.24 seconds; this is why page processing uses a background queue rather than relying on one long browser request.

A real Chromium scenario subsequently uploaded PNG, JPEG, WebP, a scanned PDF and a two-page mixed PDF. Calls went to the genuine local model; no inference/HTTP responses were replaced or intercepted. Four positions were checked for each of the first four files; the mixed PDF produced three positions. Quantities, units and categories matched their fictional labels, including null quantity/unit for the unspecified position. These are variants of two small fixtures, not 19 independent real requirements and not a production-accuracy benchmark.

The mixed PDF retained its first page's text layer and transcribed its second scanned page. Source previews were retrieved as real JPEGs after page reload. All OCR records remained unreviewed until human source verification was saved. A blank-image job failed with a readable error and no partial requirement. Desktop/mobile preview screenshots were inspected; no horizontal overflow at 390 px or browser page errors were recorded.

In this passing browser run OCR calls took 4.78–9.86 seconds/page and subsequent extraction 5.45–7.51 seconds/document, after model warm-up. These values are observations on the development hardware, not promised throughput.

## Real interruption and recovery

`tests/queue_restart.py` started its own local server, uploaded an actual mixed PDF, observed a running task, terminated that specific owned process and inspected the database. The exact uploaded bytes remained. A fresh process reopened the same database, genuinely reran OCR/extraction and completed the same task. Exactly one requirement was saved, and the temporary original-upload BLOB was cleared. The test requirement was then deleted. The script refuses an occupied test port and does not terminate unrelated processes.

## Failures diagnosed during development

- A browser test initially omitted storage consent after a page reload. Consent deliberately resets; the test now re-confirms it for the next upload.
- The test initially checked a source image before it had loaded. It now waits for successful decoding rather than treating a visible image element as a loaded image.
- Tab refreshes exposed disconnected HTTP responses being logged as backend errors. The server now handles a closed transport explicitly and does not attempt a second response on it.
- A PDF text header must not hide a scanned table on the same page. Images now require page-aware processing; unsupported embedded Office images cause an explicit whole-document rejection.

## Data and review semantics

The queue stores the original file locally until completion, failure or cancellation. OCR page previews are resized to a maximum edge of 2200 pixels and retained with the requirement. Original OCR text stays unchanged. Human-corrected product fields and manually transcribed missing lines are separate reviewed data; new image transcriptions carry an explicit source page/kind and are recorded in revision history. Deleting a requirement cascades to its previews/history/RFQ packages. Backups and previously exported files are separate copies.

Evidence is local and ignored by Git: `data/ocr-probe/vision-results.json`, `data/ocr-browser-report.json`, `data/ocr-review-desktop.png`, `data/ocr-review-mobile.png`, and `data/queue-restart-report.json`.

A separate selected-file browser run also passed the manual image-transcription UI path and checked that its explicit page/kind were saved while the raw OCR stayed unchanged (`data/ocr-selected-browser-report.json`). The previous TXT/PDF/DOCX/XLSX browser scenario and supplier/RFQ scenario passed after these changes, and their actual downloaded Excel package was read back successfully.

## Remaining acceptance limits

No claim is made for handwriting, blur, tiny print, complex tables, the client's 20 real requirements or 90% production accuracy. Model-reported uncertainty is not calibrated confidence: an empty list never removes the need for visual review. The 16,000 UTF-8-byte extraction limit remains explicit; long-document processing and OCR for images embedded in DOCX/XLSX are still open. Gmail/Sheets, later workflow stages and production deployment remain unaccepted.

The [Ollama vision API documentation](https://docs.ollama.com/capabilities/vision) describes the local REST image input used here. No external OCR/inference service, paid key, credits or subscription was connected.
