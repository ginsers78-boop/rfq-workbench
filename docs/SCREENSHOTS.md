# Screenshots

These images show the real local application, not interface mockups. All records and supplier contacts were created for the portfolio demonstration in a separate local database. Contacts use reserved `example.com` domains. No user database, account credentials, real customer documents or email inbox is included.

## Document workspace

![Document upload and empty local workspace](images/01-workspace.png)

The upload form supports the documented file formats, pasted text and explicit background-storage consent. The unfinished-beta notice remains visible.

## Human product review

![Extracted product lines and source-based review](images/02-product-review.png)

The source is the fictional `demo/requirement.txt`. The installed local Ollama model produced the actual extracted records. The final position has no supplied quantity/unit and requires clarification; in the RFQ demonstration it is excluded with a reason rather than assigned invented values.

## Local RFQ preview

![Category-specific RFQ preview](images/03-rfq-preview.png)

Three fictional suppliers represent the Fasteners, Electrical and Pipes and fittings categories. Product fields were reviewed, confidentiality markers confirmed and suppliers selected before preparing the preview. Only the actual implemented local-export workflow is shown. Gmail and Google Sheets are not connected.

## Reproduce locally

1. Follow [installation instructions](INSTALLATION.md).
2. Start an isolated demonstration database with `python -m rfq_workbench serve --port 8768 --database data/portfolio.sqlite3`, then open `http://127.0.0.1:8768`.
3. Extract `demo/requirement.txt` with local Ollama running. Compare the output with the file.
4. Approve the three complete positions; exclude the unresolved fourth position with a documented reason.
5. Add fictional suppliers using `example.com` addresses and the corresponding categories. Save the privacy checklist and select suppliers.
6. Prepare the RFQ preview. No email is sent. Take browser screenshots of the workspace, review and RFQ sections.

Source records, exports and the demonstration database stay under ignored `data/`; only the reviewed screenshots are committed. Images illustrate the current beta, not completion of the full roadmap or production acceptance.
