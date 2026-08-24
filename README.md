# Invoice Intake

Reads Japanese supplier invoices, turns them into structured data, checks the numbers, and registers
them into the accounting system through its API — with a human review screen in front of the
irreversible step.

The rule is simple: **an invoice registers itself only when every check passes. Anything else waits
for a person.**

---

## 1. Run it

You need **Python 3.10 or newer. Nothing else.** No Node.js, no `pip install`, no Docker.

```
python run.py
```

Then open <http://localhost:8000>.

That one command does everything:

1. Creates a virtual environment in `.venv` and installs the dependencies (first run only, a few
   minutes).
2. Starts the client's accounting system on port **8080**.
3. Starts this application on port **8000** and serves the review screen.

> On Windows use `python`. The `python3` command is a Microsoft Store alias and will not run the file.

If something is already listening on port 8080, the accounting system is left alone and this app just
talks to it.

### Your LLM key

Extraction needs a model. Create a file named `.env` next to `run.py`:

```
OPENROUTER_API_KEY=your-openrouter-key
GEMINI_API_KEY=your-gemini-key
ACCOUNTING_API_KEY=demo-key-1234
```

| Key | What it is for |
|---|---|
| `OPENROUTER_API_KEY` | The reader. Free models are used, so a free account is enough. |
| `GEMINI_API_KEY` | Optional. Tried first, and it is also the last resort when OpenRouter is rate-limited. |
| `ACCOUNTING_API_KEY` | The key the assignment publishes for the mock accounting system. |

**The app still starts without a key.** PDFs that carry a real text layer are read locally with no API
call at all. Scans and photographs need a model, and without one they are held for a human with that
reason stated on screen.

---

## 2. Connection to the accounting system

The header shows, at all times, whether the accounting system is answering. If it is not, nothing is
registered — invoices simply queue up and wait.

![Accounting system reachable](https://raw.githubusercontent.com/soumit1803063/InvoiceExtractionAssignment/main/public/screenshots/01-accounting-reachable.png)

The app never imports or launches `accounting_api.py`. It is treated as a separate system on another
server and reached over HTTP only: `/health`, `/partners`, `/tax-codes`, `POST /invoices`.

---

## 3. Uploading invoices

Drop files on the Upload screen. It accepts `.pdf`, `.jpg`, `.jpeg` and `.png`, several at a time.

![Upload screen](https://raw.githubusercontent.com/soumit1803063/InvoiceExtractionAssignment/main/public/screenshots/02-upload.png)

Each file is copied into the invoices folder, given a process id, and read in the background. You do
not wait on the screen — the upload returns immediately.

---

## 4. Reading

Reading happens on a background worker, so the queue stays usable while models are working. Every
document carries its own process id, which is how you follow it end to end.

![Reading queue](https://raw.githubusercontent.com/soumit1803063/InvoiceExtractionAssignment/main/public/screenshots/03-reading.png)

How a file is read depends on what it actually is:

| Input | How it is read | Cost | Time |
|---|---|---|---|
| PDF with a text layer | Parsed locally, then a text model structures it | No vision call | Under a second |
| Scan, photo, or image-only PDF | Each page rendered to a lossless PNG, then a vision model reads it | One vision call per page | Roughly half a minute |

Two things happen before the model sees the page:

- **Orientation.** If a page is upside down or on its side it is turned upright by an exact 90°
  rotation, which changes no pixel values. This uses Tesseract if it is installed; without it, pages
  pass through untouched and everything else still works.
- **Model fallback.** Models are tried in order and the first usable answer wins. A rate limit, a
  timeout, or an empty answer moves on to the next model instead of failing the document. The model
  that actually answered is recorded, with its token counts.

---

## 5. Verification — where the automation stops

This is the heart of the app. **Seven checks** run on every extraction, and every one of them must
pass before anything is sent to the accounting system.

| # | Check | What it protects against |
|---|---|---|
| 1 | Line amounts add up to the subtotal | A misread digit in any line |
| 2 | Tax matches the per-tax-code recalculation | Getting tax wrong on a mixed 10% / 8% invoice |
| 3 | Subtotal plus tax equals the total | Arithmetic that does not hold internally |
| 4 | The total matches the total printed on the page | A total invented by the model |
| 5 | The supplier exists in the accounting supplier master | Registering to a partner that does not exist |
| 6 | This invoice is not a duplicate | Paying the same invoice twice — the CEO's actual complaint |
| 7 | All required fields are filled in | An outright rejection from the accounting system |

Checks 1–3 deliberately reproduce the accounting system's own arithmetic, **including its
round-down-per-tax-code rule**. If our numbers do not survive that calculation locally, the API would
reject them anyway — so we never send them.

Check 4 is the one that catches AI error specifically. Every other check can be satisfied by a set of
numbers that are internally consistent but simply not the ones on the paper. Comparing the computed
total against the total printed on the page ties the extraction back to the document.

The supplier master and the accepted tax codes are read live from the accounting system, and shown
next to the checks so a reviewer can see what was matched against:

![Reference data from the accounting system](https://raw.githubusercontent.com/soumit1803063/InvoiceExtractionAssignment/main/public/screenshots/06-accounting-reference.png)

---

## 6. When a check fails

A document that fails any check goes to **Blocked** and stops there. It is never sent onward.

![Blocked queue](https://raw.githubusercontent.com/soumit1803063/InvoiceExtractionAssignment/main/public/screenshots/04-blocked.png)

The queue tells you the score at a glance (`6/7`), and the detail screen tells you exactly which check
failed, in plain language, with the numbers it used:

![A failed check](https://raw.githubusercontent.com/soumit1803063/InvoiceExtractionAssignment/main/public/screenshots/07-check-failed.png)

Duplicates are caught before registration rather than after, by partner code plus invoice number, and
the screen names the earlier document:

![Duplicate blocked](https://raw.githubusercontent.com/soumit1803063/InvoiceExtractionAssignment/main/public/screenshots/08-duplicate-blocked.png)

---

## 7. Human review and correction

Every extracted field is editable, side by side with the source page. The reviewer reads the paper on
the left and fixes the data on the right — no switching windows.

![Review and edit](https://raw.githubusercontent.com/soumit1803063/InvoiceExtractionAssignment/main/public/screenshots/05-review-and-edit.png)

What is on this screen:

- **Source page** — the original PDF or image, zoomable, with an "open full size" link.
- **Invoice fields** — supplier, partner code, registration number, invoice number, dates, subtotal,
  tax, total, and the total printed on the page.
- **Line items** — description, quantity, unit, unit price, amount, and tax code per line. Lines can
  be edited or removed.
- **Tokens used** — which model answered and how many input and output tokens it spent, so cost is
  visible per document rather than estimated.
- **Save & Revalidate** — writes the correction and re-runs all seven checks on the server. **Revert**
  throws the edits away.

Correcting a field never re-reads the document and never spends another token. The same document id is
kept throughout, so history is not lost.

---

## 8. Registration

When all seven checks pass, the invoice is registered automatically — no button, no confirmation
step. The reviewer's job is only the exceptions.

![All checks passed](https://raw.githubusercontent.com/soumit1803063/InvoiceExtractionAssignment/main/public/screenshots/10-all-checks-passed.png)

Registered invoices move to **Registered** and stay there permanently, showing the accounting id the
accounting system gave back and the time it was accepted.

![Registered list](https://raw.githubusercontent.com/soumit1803063/InvoiceExtractionAssignment/main/public/screenshots/09-registered-list.png)

Registration is one-way. The accounting system has no update and no single-record delete, so once an
invoice is registered this app will not edit it, will not re-read it, and will not send it again. A
lock around the registration step makes sure two workers cannot register the same document twice.

If the accounting system refuses a record anyway, its error code and message are stored and shown on
the document, and the document returns to the queue rather than disappearing.

---

## 9. Two languages

The whole interface is English and Japanese, switchable in the header and remembered between visits.
Every visible string comes from a single dictionary — there is no hard-coded text in any component.
The invoices, the supplier names and the field labels stay in Japanese, because that is what is
printed on the paper.

---

## 10. Layout

```
backend/
  app.py               builds the application
  settings.py          every path, url, model name and threshold
  controllers/         the HTTP endpoints
  core/                models, prompts, and the domain knowledge the agent uses
  repositories/        persistence (SQLite)
  services/
    document_service.py     upload, background reading, registration
    validation/             the seven checks
    accounting_service.py   HTTP client for the accounting system
    extraction/             orientation, transcription, model chain
frontend/              review screen (React); dist/ is the built output the backend serves
public/
  storage/             the invoice files
  database/            the SQLite database
run.py                 the single entry point
accounting_api.py      the client's accounting system, verbatim from the assignment; not our code
```

`accounting_api.py` is the block from section 8 of the assignment, copied in byte for byte. Nothing
here modifies it.

`frontend/dist/` is committed on purpose so the project runs without a Node toolchain. To rebuild it:
`cd frontend && npm install && npm run build`.

---

## 11. Notes and limits

- **Restart is safe.** Documents left mid-read when the process stopped are picked up again at
  startup.
- **Scanned invoices are the weak point.** Free vision models misread digits on some scans. The
  checks catch it, so nothing wrong reaches the accounting system, but those invoices need a human.
  A stronger vision model is a one-line change in `.env`.
- **Everything runs locally.** The only outbound calls are to the model provider you configured.
