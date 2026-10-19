# Local RFQ checkpoint — 2026-10-19

## Completed and verified

43 Python checks passed, including the existing document readers/review checks and 12 RFQ tests. The RFQ tests cover actual ZIP/Excel construction, stable supplier IDs, duplicate email rejection, stale updates, active/category rules, exact category coverage, line exclusions with reasons, confidential data in product fields, independent decoded Office XML scanning, literal spreadsheet formula-like text, equivalent monetary formatting, immutable version history, stale package blocking and cascading record deletion.

A real Playwright/Chromium scenario ran against a separate local SQLite database on port 8766. It created four fictional supplier records through the UI, uploaded the fictional TXT requirement, and made a genuine local Ollama extraction call. Three positions were approved; the fourth was excluded with a reason.

The scenario deliberately inserted `PRIVATE-CUSTOMER-442` into a product description. RFQ preparation was blocked. After the description was corrected, it generated three category RFQs with four BCC supplier selections. Download was blocked until human-preview approval. The actual ZIP was downloaded, the saved RFQ was reopened after page reload, and a supplier edit preserved its ID while blocking the old package download.

The database retained four saved requirement revisions, including the deliberately unsafe intermediate description, which remained internal. Deleting the test requirement removed its RFQ; the test suppliers were deactivated in the isolated QA database. The working database was not seeded with these contacts.

No browser page errors were recorded, and there was no horizontal overflow at 390 px. Desktop and mobile RFQ previews were visually inspected. The previous browser scenario for TXT/PDF/DOCX/XLSX, review/save/reload/internal JSON/manual line addition/delete also passed after the RFQ changes.

The **actual downloaded** ZIP was then separately opened. Each of its three Excel workbooks was read back and checked against the manifest: exact header names, RFQ reference, permanent line ID, original number, description, specification, quantity and unit matched. Supplier offer columns were blank and no formula cells existed. The final package passed declared confidential-marker scanning.

Local evidence (ignored by Git): `data/rfq-browser-report.json`, `data/rfq-browser-package.zip`, `data/rfq-preview-desktop.png`, `data/rfq-preview-mobile.png` and `data/browser-test-report.json`.

## What remains unaccepted

No Gmail account was connected, no Gmail draft created and no message sent. Local file preparation does not replace that integration. At this historical checkpoint, Google Sheets, OCR, long documents, supplier reply ingestion, pricing/history matching, quotations, reporting, production hosting and the client's representative real-data acceptance targets remained outstanding. Subsequent local OCR and long-document evidence is recorded in [OCR results](OCR-RESULTS.md) and [long-document results](LONG-DOCUMENT-RESULTS.md); this does not accept the external integrations or later workflow stages.

Known/suggested confidential values are checked conservatively, including case/punctuation normalisation and monetary formatting changes. Unknown secrets can still require identification by a human; the user must review the entire source, add all confidential markers and inspect the outbound preview. This evidence is not a claim of universal data-loss prevention.

The ZIP and dispatch manifest are internal because they include supplier BCC contacts. They must not be forwarded to suppliers. Only the reviewed body and corresponding `reply.xlsx` are supplier-facing. Already downloaded files cannot be revoked when a later revision invalidates their in-app download.
