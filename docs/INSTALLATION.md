# Installation and operation

This is an unfinished, local-only portfolio beta. Read [the roadmap](../ROADMAP.md) before installing. Gmail/Sheets, pricing and the complete quotation workflow are not implemented.

## Requirements

- Python 3.11 or newer, with pip and venv.
- Ollama installed and running on this computer, with the `qwen3.5:9b` model. A compatible GPU and sufficient RAM are recommended; CPU inference can be slow. Model files are several gigabytes and are not included in this repository.
- A modern browser. Node.js is needed only for optional browser development tests.

No API key, paid inference account, database subscription, Docker or hosted server is needed for local use. Hardware, storage, bandwidth and electricity remain your responsibility.

## Windows: first launch

1. Download this repository using GitHub's **Code → Download ZIP**. Extract the ZIP and open the extracted project folder.
2. Install Python from its official distribution and enable **Add python.exe to PATH**. Install and start Ollama from its official distribution.
3. In the project folder's File Explorer address bar, type `powershell` and press Enter.
4. Run these commands in that terminal:

```powershell
ollama pull qwen3.5:9b
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m rfq_workbench serve
```

The first command downloads the model; omit it if that exact model is already installed. Keep the terminal and Ollama running. Open **http://127.0.0.1:8765** in your browser.

If `py` is unavailable but Python is installed, use `python -m venv .venv`. Using the environment's Python directly avoids PowerShell activation-policy changes.

## macOS / Linux

With Python and Ollama installed and running, open a terminal in the extracted repository folder:

```sh
ollama pull qwen3.5:9b
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m rfq_workbench serve
```

Open **http://127.0.0.1:8765**. The documented verification was performed on Windows; other operating systems need their own validation, particularly OCR rendering and font-dependent test fixture generators.

## Try the workflow

1. Upload `demo/requirement.txt` and click **Extract product lines**.
2. Compare every field with the source. The fictional final position intentionally has no quantity/unit: leave it unresolved, or exclude it with a reason. Do not invent an order quantity.
3. Save corrections and approvals. Long files and scans require explicit background-storage consent; OCR and multipart results also require source-comparison confirmations.
4. Add your authorized suppliers, select their categories and save the privacy checklist.
5. Prepare RFQ previews and inspect recipients and every outbound field before approving local download.
6. The ZIP and manifest are internal and contain supplier contacts. Only the reviewed message body and corresponding Excel file are intended for supplier correspondence. The application does not create Gmail drafts or send email.

## Stop, restart and local data

Stop the server with **Ctrl+C** in its terminal. Restart using the same `python -m rfq_workbench serve` command and environment. Records are stored in `data/workbench.sqlite3`, created automatically on first use. Uploaded source files used by the queue are temporary; recognized text, model output, reviews and OCR previews can persist with records. Deleting a requirement removes its associated stored history/previews/RFQs, but not separately exported copies or backups.

Closing the browser does not stop inference. Interrupted queued tasks resume after server restart. Back up the `data` directory only after stopping the server. Keep backups and internal exports private. Never commit `data`, credentials, real customer documents or exported RFQ packages to GitHub.

This is a localhost server with no multi-user authentication. Do not expose its port to the internet, use a public tunnel or claim it is a hosted production service.

## Common problems

- **Ollama unavailable:** start Ollama, run `ollama list`, and check that `qwen3.5:9b` is installed. The application uses the fixed local endpoint `127.0.0.1:11434`.
- **Processing is slow:** model calls can take several minutes. Enable background processing for scans/long files and keep both processes running. Speed depends on local hardware.
- **Port already in use:** close the earlier instance. Alternatively run `python -m rfq_workbench serve --port 8767` and open `http://127.0.0.1:8767`. A second instance must not share the same database.
- **Unsupported document:** read the visible error. Embedded Office images, spreadsheet formulas and continuous source sections above the documented budget are explicitly unsupported; changing a filename will not fix them.
- **Reset local data:** stop the server and move the `data` directory to a private backup location, then restart. A fresh empty database is created. This removes previous records from the active workspace.

## Development checks

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The documented suite has 73 passing checks. Real-model browser and benchmark instructions are in [README](../README.md), with evidence scope in `docs/*RESULTS.md` and a [manual checklist](MANUAL-CHECKLIST.md). Browser tests need Node.js/Playwright plus running Ollama and an isolated local test database. Passing fictional checks is not real-client acceptance.
