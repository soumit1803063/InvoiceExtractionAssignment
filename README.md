# Invoice Intake

Reads Japanese supplier invoices, extracts them into structured data, verifies the numbers
arithmetically, and registers them into the accounting system through its API — with a human
review screen in front of the irreversible step.

## Requirements

- Python 3.10 or newer
- Node.js is **not** required to run this. The frontend is pre-built and committed.

## Setup

### 1. Start the accounting system API

`accounting_api.py` in this repository is the client's accounting system. It is not part of this
project and none of this code is ours: it is the block from section 8 of `TAKE_HOME.md`, copied in
byte for byte so you do not have to paste it yourself. Nothing here modifies it, and nothing here
starts or stops it. This app is a client of that system over HTTP, exactly as it would be if the
system ran on another server.

Run it in its own terminal and leave it running:

```
python accounting_api.py
```

Check it is up:

```
curl http://localhost:8080/health
```

> On Windows, use `python`. The `python3` command is a Microsoft Store alias and will not run the file.

The API keeps everything in memory. Restart it, or call `DELETE /invoices`, to start over.

### 2. Add the invoices

Put the invoice files in the `invoices/` folder at the root of this repository:

```
invoices/
  invoice_01.pdf
  invoice_02.pdf
  ...
```

Any `.pdf`, `.jpg`, `.jpeg` or `.png` file in that folder is picked up.

### 3. Configure credentials

Create a file named `.env` in the root of this repository:

```
OPENROUTER_API_KEY=your-openrouter-key
GEMINI_API_KEY=your-gemini-key
ACCOUNTING_API_BASE_URL=http://localhost:8080
ACCOUNTING_API_KEY=demo-key-1234
INVOICE_DIR=invoices
PORT=8000
```

`OPENROUTER_API_KEY` is the primary reader. `GEMINI_API_KEY` is the fallback used when the primary
is rate-limited or fails; the app runs without it, but loses that resilience.

### 4. Install dependencies

```
pip install -r requirements.txt
```

## Run it

```
python run.py
```

Then open <http://localhost:8000>.

That is the whole thing — one command, one process, one port. The REST API and the review screen are
served together. The accounting system stays where it was in step 1: a separate program on port 8080
that this one only ever talks to over HTTP.

## What happens

1. **Scan** reads every invoice in `invoices/`.
2. Each file is routed by what it actually is. PDFs with a real text layer are parsed directly, at
   no cost and in a fraction of a second. Scans and photographs go to a vision model.
3. Every extraction is then checked arithmetically — the line amounts must sum to the subtotal, tax
   must match a per-code recomputation rounded down, and the total must equal the total printed on
   the page.
4. Anything that fails a check, or is missing a field the accounting system requires, is held for a
   human in the review screen. Nothing is registered automatically unless every check passes.
5. **Register** posts the invoice. This step cannot be undone — the accounting system has no update
   and no single-record delete — so it is deliberately behind a human click.

## Layout

```
backend/           extraction, verification, accounting API client
  skills/          domain knowledge used by the extraction agent
frontend/          review screen (React); dist/ is the built output that the backend serves
run.py             the single entry point
accounting_api.py  the client's accounting system, verbatim from the assignment; not our code
```

`frontend/dist/` is committed on purpose, so the project runs without a Node toolchain. To rebuild
it: `cd frontend && npm install && npm run build`.
