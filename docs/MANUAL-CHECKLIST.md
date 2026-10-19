# Manual acceptance — local document review stage

Use fictional data only. Start Ollama and `python -m rfq_workbench serve`, then open `http://127.0.0.1:8765`.

- [ ] Select `demo/requirement.txt`; extract four product lines and compare every description/specification/quantity/unit/category against the source.
- [ ] Check the last line: no quantity or unit should be invented. Approving it without correcting the missing information must fail.
- [ ] Save an unfinished review; reopen it from Recent requirements.
- [ ] Supply a human-confirmed quantity/unit, approve all lines and save. Check REVIEWED status.
- [ ] Stop the application, start it again, reopen the saved record and verify the correction and permanent line IDs.
- [ ] In two tabs open the same revision. Save the first, then try to save the second. The stale update must fail without overwriting the first.
- [ ] Add a missed line with its original number and a quotation copied exactly from the source. Invented quotations and duplicate permanent IDs must fail. Original numbers may repeat on different sheets/pages; the saved IDs and source positions must remain distinct.
- [ ] Download saved JSON; verify metadata, original model response, reviewed lines and source text. Do not send this internal export to a supplier.
- [ ] Try a real text-based PDF, DOCX with paragraphs/tables and XLSX with values. Compare complete source text with the file, not just the number of extracted lines.
- [ ] Try an empty TXT, renamed non-PDF, corrupted PDF and encrypted PDF. Expect readable errors and no stack traces. A scanned/mixed PDF without enabled page processing must ask for local OCR; no partial text-only record may be saved.
- [ ] Try XLSX formulas, files larger than 10 MB, PDFs over 50 pages and extracted text over 1 MiB UTF-8 bytes. Expect explicit limits and no silent truncation.
- [ ] Stop Ollama and try an extraction: expect a readable error and no successful record. Restart Ollama afterwards.
- [ ] Enter text resembling HTML in a description, save and reopen. It must display as text and execute nothing.
- [ ] At 390 px width, check all controls are usable and there is no horizontal overflow.
- [ ] Delete a record and verify it is absent after restarting the server. Exported files and backups are separate copies.

## Local RFQ checks

- [ ] Add two suppliers for one category and one for each other category; edit a supplier and verify its permanent ID is preserved. Duplicate email, invalid email and stale updates must fail.
- [ ] Exclude an incorrect row with a reason. Saving an exclusion without a reason or simultaneously approving it must fail. The row must remain in saved history but be absent from the RFQ.
- [ ] Confirm the full confidential-data checklist. Add an extra secret that is not recognised from headers. Unsaved checklist edits must block RFQ preparation.
- [ ] Intentionally include a declared customer name/reference/selling price in a product field. RFQ generation must fail; source quotations and customer headers must never be copied automatically to supplier content.
- [ ] Select active suppliers for every included category. Missing categories, duplicates, inactive suppliers and category mismatches must fail.
- [ ] Inspect each preview, BCC list and Excel attachment. Download must require explicit preview approval. The ZIP/manifest are internal and must never be forwarded to suppliers.
- [ ] Read the downloaded Excel and compare RFQ/line identifiers and all requested product fields with the preview. Offer columns must be blank and editable; strings starting with `=` must remain literal text.
- [ ] Change a requirement or supplier after generating a package. Approving/downloading the old in-app package must fail. Repeating preparation without changes should retain the existing RFQ IDs.
- [ ] Restart the app and verify supplier records, requirement history and saved RFQs remain. Delete a requirement and check that its history and RFQ packages are gone.

## Local OCR and queue checks

- [ ] Upload PNG/JPEG/WebP and scanned/mixed PDFs with page processing enabled. Compare every quantity/unit/specification and customer header with the original, not only the recognized text.
- [ ] Verify explicit storage consent is required and resets after reload. The original upload is temporary; resized source previews persist locally for review.
- [ ] Inspect progress per page. Close/reopen the tab and verify the queue/result remain available. Stop/restart the app during processing and confirm genuine recovery without duplicate requirements.
- [ ] A blank image must fail without invented positions or a partial saved record. Blurred, handwritten and small-print examples need separate evaluation; model silence about uncertainty is not a pass.
- [ ] Open source images after page reload. Approve all product lines without confirming image comparison: the record must remain NEEDS REVIEW and RFQ preparation must fail.
- [ ] Correct product fields against the image. For a line missing from OCR, add a manual transcription and a saved OCR page number. Verify the explicit image-transcription label, immutable page citation and unchanged raw OCR in history.
- [ ] Cancel a queued/running task; its raw upload must be cleared and no later model reply may create a completed requirement. The current model call may take time to finish.
- [ ] Delete a processed requirement and verify its preview/history/RFQ rows are removed. Starting a second app on the same database must fail; a separate QA database must work.
- [ ] Embedded images in DOCX/XLSX must cause an explicit rejection rather than a text-only partial result.

## Long-document checks

- [ ] Generate fictional inputs with `python tests/make_long_inputs.py`. Enable background processing and upload each long TXT/PDF/DOCX/XLSX. Check all 24 positions, multiline technical details, quantities/units and original order against the source.
- [ ] In `table-order.xlsx`, check all 12 products across both sheets, the restarted original numbers, reversed column ordering and unspecified quantities. No header or sheet title should become a product.
- [ ] Use View source on products with identical original numbers. Each highlight must refer to the correct source occurrence; permanent IDs must be distinct.
- [ ] Save approved/corrected rows without confirming complete-source comparison: a multipart document must remain NEEDS REVIEW. Confirm after actual comparison and save again. Editing a product must clear that confirmation.
- [ ] Reload and export the record. Source text, part provenance, literal quantity evidence, reviewed changes and stable IDs must persist.
- [ ] Submit one continuous product/paragraph over 12,000 UTF-8 bytes. Expect an explicit safe-boundary error and no partial requirement. The whole-document limit does not imply every layout can be partitioned.

These checks do not accept Gmail/Sheets, embedded Office image OCR, historical matching, quotation pricing, portal intake or production deployment. Known-marker checks plus human review are implemented; universal automatic recognition of all unknown confidential data is not claimed. Fictional long-file checks do not establish the client's real-data accuracy targets.
