# Invoice Intake

Reads Japanese supplier invoices, extracts them into structured data, verifies the numbers
arithmetically, and registers them into the accounting system through its API — with a human
review screen in front of the irreversible step.

## Run it

You need **Python 3.10 or newer. Nothing else.** No Node.js, no `pip install`, no Docker.

```
python run.py
```

Then open <http://localhost:8000>.

That single command does everything:

1. Creates a virtual environment in `.venv` and installs the dependencies (first run only, a few
   minutes).
2. Starts the client's accounting system on port **8080**.
3. Starts this application on port **8000** and serves the review screen.

> On Windows use `python`. The `python3` command is a Microsoft Store alias and will not run the file.

If something is already listening on port 8080, the accounting system is left alone and this app
just talks to it.

## Before the first run: your LLM key

Extraction needs a model. Create a file named `.env` next to `run.py`:

```
OPENROUTER_API_KEY=your-openrouter-key
GEMINI_API_KEY=your-gemini-key
ACCOUNTING_API_KEY=demo-key-1234
```

- `OPENROUTER_API_KEY` is the reader. Free models are used, so a free account is enough.
- `GEMINI_API_KEY` is optional. It is the last fallback when every OpenRouter model is rate-limited.
- `ACCOUNTING_API_KEY` is the key the assignment publishes for the mock accounting system.

**The app still starts without a key.** PDFs that carry a real text layer are read locally with no
API call at all. Scans and photographs need a model, and without one they are held for a human with
that reason stated on screen.

## Adding invoices

Upload them on the Upload screen. It takes `.pdf`, `.jpg`, `.jpeg` and `.png`.

Each file is copied into `public/storage/`, given a process id, and read in the background. A
text-layer PDF is done in well under a second; a scanned page takes roughly half a minute.

## What happens to an invoice

1. Each file is routed by what it actually is. A PDF with a real text layer is parsed directly, at
   no cost and in a fraction of a second. Scans and photographs are rendered to a lossless image and
   sent to a vision model.
2. If the page is upside down or on its side it is turned upright first, by an exact 90° rotation
   that changes no pixel values. If that cannot be done the original page is used unchanged.
3. The supplier is matched against the accounting system's partner master — by registration number
   (登録番号), then by partner code, then by the master's own company name and aliases.
4. Every extraction is checked arithmetically: the line amounts must sum to the subtotal, the tax
   must match a per-tax-code recomputation rounded down exactly as the accounting system does it,
   the subtotal plus tax must equal the total, and that total must equal the total printed on the
   page. The same invoice from the same supplier twice is flagged as a duplicate.
5. Anything that fails a check, or is missing a field the accounting system requires, waits in the
   queue for a human. An invoice that passes every check is registered automatically.
6. Registration cannot be undone — the accounting system has no update and no single-record delete —
   so a registered invoice can no longer be edited or re-read.

## Optional: straightening rotated scans

Page orientation uses Tesseract if it is installed. It is entirely optional: without it, pages are
passed through untouched and everything else works normally. It is found automatically on `PATH` or
in the usual install locations, or you can point at it with `TESSERACT_PATH` in `.env`. Set
`ORIENTATION_ENABLED=false` to turn it off.

## Layout

```
backend/
  app.py            builds the application
  controllers/      the HTTP endpoints
  core/             models, prompts, and the domain knowledge the extraction agent uses
  repositories/     persistence
  services/         extraction, validation, accounting client
frontend/           review screen (React); dist/ is the built output the backend serves
public/
  storage/          the invoice files
  database/         the SQLite database
run.py              the single entry point
accounting_api.py   the client's accounting system, verbatim from the assignment; not our code
```

`accounting_api.py` is the block from section 8 of the assignment, copied in byte for byte. Nothing
here modifies it. This app is a client of it over HTTP, exactly as it would be if that system ran on
another server.

`frontend/dist/` is committed on purpose so the project runs without a Node toolchain. To rebuild
it: `cd frontend && npm install && npm run build`.
