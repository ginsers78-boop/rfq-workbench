# Long-document checkpoint — 2026-10-19

## Implemented behavior

The document reader accepts up to 1 MiB of extracted UTF-8 text. A partitioner preserves every source character in non-overlapping parts of at most 12,000 UTF-8 bytes and eight recognised numbered product blocks. A single continuous block above that budget fails explicitly instead of losing its continuation. The product review limit remains 1,000 positions; file/PDF limits remain 10 MB and 50 pages.

Background processing now accepts typed TXT/PDF/DOCX/XLSX and pasted text as well as scans. All parts must finish successfully before a requirement is saved. Existing queue persistence, cancellation and storage consent still apply. No external model or paid service is connected.

For multipart requests, actual model output references supplied source-record IDs. Code obtains original numbers and exact excerpts directly from the corresponding source record. Repeated original numbers are permitted; immutable source offsets and permanent line UUIDs distinguish occurrences. Raw part responses are preserved separately. Simple explicit quantity/unit literals are read independently from source text or named table columns, with model disagreements recorded. Ambiguous values are not guessed.

Sheet titles and table headers have separate source boundaries. Literal column headers accompany records in subsequent model parts, including when column order changes between sheets. The reviewer can highlight a line's precise source excerpt. Multipart results require saved confirmation that the complete source was compared before REVIEWED status or RFQ preparation.

## Actual inference evidence

`tests/long-browser.cjs` uploaded four genuine fictional files through Chromium, the real local API, durable queue and installed `qwen3.5:9b`. There were no intercepted inference responses. Each format contained 24 positions, multiline technical details and restarted original numbering. Checks covered original order, all quantities/units/categories, retained technical ending markers, exact source excerpts, distinct source offsets and UUIDs.

The initial passing run processed TXT (18,595 UTF-8 bytes), six-page PDF (18,515 bytes), DOCX (18,497 bytes) and XLSX (18,492 bytes) in three model parts each. Observed extraction times were 69.13, 66.11, 71.00 and 62.81 seconds respectively. These are hardware-specific measurements, not throughput promises. Save/reload/internal JSON export, complete-source confirmation, correct highlighting, 390-pixel layout and absence of browser page errors also passed. Evidence: ignored `data/long-browser-report.json`, `data/long-review-export.json` and `data/long-coverage-desktop.png`.

`tests/long_probe.py` separately exercised real TXT/PDF readers and inference. Both returned all 24 labeled positions with matching checked fields and technical markers. These are format variants of fictional fixtures, not independent real customer orders or proof of a 90% production extraction target.

`tests/table_probe.py` uses a genuine two-sheet Excel file with reordered Description/Specification/Quantity/Unit columns and restarted source numbers. A failed initial run returned only nine of twelve products. Inspection exposed sheet/header text attached to the preceding product and insufficiently explicit handling of blank quantity cells. After separating those boundaries and clarifying record instructions, the same file returned all twelve products, preserving missing quantities rather than inventing them. The probe compares descriptions, specifications, numbers, quantities, units and categories. Evidence: ignored `data/long-inputs/table-order-report.json`.

Earlier probes also exposed unreliable model-copied quotations and missed explicit quantities. The implemented source-ID provenance and independent literal reading address those causes; no expected product values are inserted into runtime inference.

## Verification and remaining scope

All 73 Python tests passed in the final suite run. They cover lossless UTF-8 partition coverage, record/header boundaries, oversized-document/atomic-record rejection, distinct repeated-number anchors, immutable offsets, full-source review gates, literal quantity parsing and repeated original numbers in genuine Excel RFQ exports. Browser regression checks passed for short typed documents, review/export, local RFQ preparation and one image OCR case against the real application and model.

The final long-file browser rerun also passed on the corrected version: TXT/PDF/DOCX/XLSX each returned 24 positions in three parts, with observed durations of 63.24/47.38/47.06/47.88 seconds. The final two-sheet table probe passed all checked fields for twelve positions in 22.93 seconds.

The partitioner recognises common numbered rows and paragraph boundaries; arbitrary nested or unnumbered layouts still need representative evaluation and human comparison. Model omissions are possible: missing anchored numbered sections are flagged, not silently filled with fabricated products. One large continuous paragraph over the part budget is unsupported. Per-page OCR retains its separate 16,000-character response bound. Adaptive subdivision on a model output-length failure is implemented but was not forced in these live checks.

Milestone 1 is still open: embedded DOCX/XLSX image OCR, authorized Gmail/Sheets integration, representative client acceptance data and the final walkthrough remain outstanding. Later supplier-response, pricing, history and quotation workflows are not accepted by this checkpoint. No Gmail draft was created and no supplier message was sent.
