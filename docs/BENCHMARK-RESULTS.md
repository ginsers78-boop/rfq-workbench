# Initial extraction evidence — 2026-10-19

## What was actually run

- Nine Python unittest checks passed for category schemas, missing/extra/duplicate lines, quantity comparisons and visible evaluation errors.
- Two real inference calls were made to the locally installed `qwen3.5:9b` model after improving the extraction instructions and sampler schema.
- Final durations: 7.42 seconds for `FICTIONAL-REQ-001` and 7.16 seconds for `FICTIONAL-REQ-002`.
- Each source has four positions, with different numbering and presentation. Both contain deliberately missing information.
- Both final runs matched all labeled quantities, units and categories for all four positions. Missing values remained null. All returned source quotations were found exactly in the source.
- The final outputs were also inspected: technical specifications were separate from ordering quantities, and every line remained unreviewed, requiring approval.

Local JSON reports are written under `data/`, which is intentionally excluded from version control. Those reports preserve actual model output; they are not synthesized from expected answers.

## Failures found before the passing runs

1. The first real structured-output call produced JSON but omitted supplied units and misclassified a pipe fitting. JSON validity alone was therefore rejected as a success criterion.
2. The installed sampler rejected the generated Pydantic grammar with HTTP 400. An inline sampling schema using supported primitive types was introduced, while the full Pydantic bounds and business checks remain mandatory after inference. No schema failure is replaced with a successful response.
3. An intermediate model output repeated quantity/unit in the technical-specification field. The instructions now distinguish those fields, and validation flags this particular defect when it occurs.

## What this does not prove

This is an eight-position fictional benchmark, not the client's 20 real requirements. The automated score currently covers quantity, unit and category, plus missing/unexpected lines. It does not establish full description/specification accuracy, OCR quality, malicious-document resistance, PDF/Excel/Word parsing, production throughput or the client's 90% acceptance target.

The Gmail, RFQ, historical matching, pricing and reporting stages have not been built or accepted by this benchmark. No external email, paid inference, accounting import, hosted database or customer account was used.
