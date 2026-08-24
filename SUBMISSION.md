# Submission

- Name: Soumit
- Submission date (YYYY-MM-DD): 2026-08-25
- Hours actually spent: 8
- Repository / how to run it: https://github.com/soumit1803063/InvoiceExtractionAssignment. One command, `python run.py`. Setup is in `README.md`. A demo recording, annotated screenshots, and a rendered walkthrough of the workflow are attached.

## 1. Understanding the request

**The problem the client described.** Staff type invoices by hand. It is slow. Month-end close turns into overtime. Read them with AI instead.

**Why I did not stop there.** The line that matters most is the one about nearly paying the same invoice twice.

- Manual entry is slow, but a human sees every number.
- Automating extraction removes that human.
- It removes them in front of a system that cannot be corrected.
- The accounting API has no update call and no per-record delete.
- So a wrong registration is effectively permanent.

**The problem I actually solved.** Get invoices into the accounting system **without ever putting a wrong one in**.

- Extraction is a component, not the goal.
- The centre of the build is the verification layer.
- It decides which invoices a human ever has to look at.
- Speed is what is left over once correctness is guaranteed.

**What the samples and the API reference told me.** Every part of the build exists because of one of these.

| The problem I found | What it produced |
|---|---|
| The duplicate trap is in the sample set, not just the email. invoice_07 is a photograph of the same invoice as invoice_01, under a different name and file type | A duplicate check against invoices already registered. Run before anything is sent. Repeated inside the registration lock. Backed by registering one document at a time, because the API's own duplicate check is not atomic |
| A wrong registration cannot be taken back. No update call, no per-record delete | Nothing is sent until all seven checks pass. An undo rebuilt from a full read, a full delete and a full replay, which refuses outright if any live record cannot be matched |
| A model can return an invoice that is internally consistent and still wrong, by dropping a line or omitting a tax code | The cross-foot is tied to the total **printed on the page**, not to the model's own arithmetic. It is the only check that can see a row that was never extracted |
| Some invoices cannot be registered however well they are read. invoice_10's supplier is absent from the partner master | Supplier matching against the live master, and a failure that names the real cause. The dashboard shows which suppliers are registerable |
| Some source documents are defective. invoice_09's printed total is one yen above its own lines | The system refuses to pick a side. It holds the document and shows both numbers |
| The twelve files are not one kind of document. Three carry a text layer, eight are photographs, one is a PDF holding only a scan | Routing by inspecting the file, not by trusting its extension. A machine-readable invoice is never rendered to an image |
| Model endpoints fail often, and differently each time: quota, timeouts, prose instead of schema | Ordered model chains that fall through on failure. A document that exhausts every model is held, with each failure reason on screen |

## 2. What you would have asked the client

| What you wanted to ask | The assumption you made | Why |
|---|---|---|
| An invoice's printed total disagrees with its own lines by one yen. Do you pay the printed total or the computed one? | Neither. Stop and ask a human. | invoice_09 has exactly this defect. Guessing either way silently changes what a supplier is paid. |
| What happens when a supplier is not in the partner master? | Hold it for a human. Do not attempt registration. | The API rejects it and offers no way to onboard a supplier. An operational gap, not an extraction failure. |
| Who may approve a registration? Is one approval enough? | Anyone using the review screen. One approval. | No role information in the brief. Flagged as the first thing to fix before real use. |
| Is a handwritten correction authoritative? | No. Extract the printed values. Show the handwriting to the reviewer and let them decide. | invoice_08 carries a handwritten bank-account change. Treating handwriting as data lets anyone with a pen redirect a payment. |
| Must the accounting system be current the same day, or is a queue acceptable? | A queue is acceptable. An invoice that passes every check may file itself. | Month-end close is a batch process. Holding a provably correct invoice for a signature adds delay, not safety. The checks are the gate, not the click. |
| Is there a way to remove one invoice, or to ask whether one invoice is registered? | No. There is `GET /invoices`, `POST /invoices` and `DELETE /invoices`, and nothing else. An undo has to be read, delete, replay. "Is this registered" has to be answered from this app's own record. | Doing nothing leaves an operator with no recovery path. Building the replay, and making it refuse when a live record cannot be matched, is the only safe use of the primitives that exist. |
| How badly written is the handwriting? | Handwriting is annotation. Never the only source of a required field. Printed values are always machine-legible. | If a required amount existed only in poor handwriting, no arithmetic check could recover it and the document would be held anyway. The assumption costs nothing if it is wrong. |
| Do pages arrive skewed by a few degrees, or only rotated in quarter turns? | Only 0, 90, 180 or 270 degrees. No deskewing. | Tesseract reports exactly those four angles. A quarter turn is a lossless pixel permutation. A deskew is a resample, which degrades the image the extraction depends on. Better to hold a skewed page than blur it. |
| How poor can the scan quality get? | Images are legible without guessing. Anything the models cannot read is held, never inferred. | The one assumption the system does not need to be right about. On invoice_05 every model failed and the document was held with all six reasons on screen. An unreadable page and a failed check are handled identically. |
| Will model prices and availability stay where they are? | Roughly. Not reliably enough to hard-code a model. | Every model id is a settings field with an environment alias. Switching one, or reaching for a stronger frontier model on the rare hard document, is an environment change, not a code change. Two of the ten configured ids have already vanished from the catalogue. See section 7. |
| One company, or several sharing an installation? | One. Single tenant throughout. | One database, one invoice folder, one API key, one partner master. Nothing separates data by tenant. Retrofitting that is a schema change, so it is worth stating rather than implying. |

## 3. Scoping decisions

**What you built**

- **Ingestion** for all three input shapes in the sample set, routed by what each file actually is, not by its extension.
- **Extraction** into a fixed schema.
- **Verification**, deterministic, on every invoice and on every correction.
- **Partner matching** against the live master.
- **A duplicate check** that runs locally before anything is sent.
- **Full API integration**, including its error codes.
- **A review screen** where a person corrects fields and revalidates.
- **A dashboard** showing exactly what the accounting system will accept, so a reviewer can see why something was blocked.
- **A guarded unregister** that rebuilds the ledger when a registration has to come back.
- **One command** that starts all of it.

**What you left out, and why**

The rule I cut by: anything that did not reduce the chance of a wrong registration.

- **No correction that changes a number.**
  - Orientation is corrected, because a quarter turn alters no pixel and no figure.
  - Supplier matching falls back to the master's own names and aliases when the registration number is misread, but only to a single unambiguous match. Two candidates means no match, and a human decides.
  - Refused: re-scanning at higher resolution to "improve" a total. Refused: guessing a missing line.
  - A guess in front of a ledger that is hard to correct is the exact failure mode I am removing.
- **No multi-invoice PDF splitting, no batch-scanner support, no long documents.** The sample set tops out at two pages. Anything built for larger batches would be untested code shipped on speculation.
- **No user accounts, no approval roles, no audit trail** beyond the local record. Real deployment needs all three. None of them make an extraction more correct.
- **No automated test suite.** Verification of the model output ships as product code and runs on every invoice. That is what actually protects the ledger.

## 4. Design and technology choices

**The flow, end to end**

1. A file is classified by inspecting it.
2. It is read by the reader for its class.
3. The fields are normalised.
4. Seven checks run.
5. All seven pass, and it files itself. One fails, and it is held.

The gate is the checks, not the click. A human rubber-stamping numbers they cannot recompute is theatre, and the accounting system re-derives those numbers anyway.

**Routing before extraction**

- A PDF is tested for a real text layer.
- If it has one, the text is pulled out locally and only that text goes to a model.
- Three of the twelve invoices are in this class.
- No image is rendered. None is uploaded.
- So there is no chance of an OCR-style misread of a digit that was already machine-readable.

**Vision for the rest**

- The remaining nine are photographs, or a PDF containing only a scan.
- Each page is rendered to an image and sent to a vision model.
- The model is bound to a fixed output schema, so it returns typed data rather than prose that has to be parsed.

**Which model, and why**

- Two ordered chains, each ending in free models.
- Text: `deepseek/deepseek-v3.2`, then `google/gemini-2.5-flash-lite`, then four free OpenRouter models.
- Images: `google/gemini-2.5-flash-lite`, then four free vision models, led by `google/gemma-4-31b-it:free` and `nvidia/nemotron-3-nano-omni:free`.
- Google's own `gemini-3.7-flash` is tried ahead of both chains when a Gemini key is present.
- **No model id is written into the code.** Each is a settings field with an environment alias. The chain can be reordered, a model swapped, or a stronger paid model added, without touching a service. Deliberate: model names and free-tier terms change faster than this code will.

Why paid at the head:

- I started free-only and moved after measuring.
- Free tiers fail specifically, not vaguely. One model returns 403 because it is only served to agentic harnesses. Another returns prose instead of structured output. Daily quota runs out mid-run. All three happened during testing.
- A cheap paid model at the head raises the straight-through rate. The free tail still catches it when the paid call is rate-limited or slow.
- Twelve invoices cost almost nothing either way, so this is a reliability choice, not a price choice.

The chain is not theoretical. In the section 6 run the paid vision model answered one image and timed out on the rest, and a free model finished those documents. On one image every model failed, and the document was held with the whole failure list on screen.

**What I decided against**

- **OCR then a language model.** The vision model reads Japanese layout directly. An OCR stage adds a failure mode without adding information.
- **Redacting personal data before sending it.** The tax registration number is the field used to identify the supplier. Redacting it would break the matching the system exists to do.

**Orientation, and the rule it had to obey**

- None of the twelve samples is rotated. A copier feeds pages in sideways, so this has to survive it.
- Tesseract detects the angle when installed.
- The page is turned by an exact 90 degree transpose. A pixel permutation, not a resample, because degrading the image degrades the extraction that depends on it.
- An upright page is returned as the original bytes, untouched.
- If Tesseract is absent or errors, the original page is used and nothing else changes.
- My first version was worse than useless. It borrowed a brute-force search that rotated an already-upright invoice by 180 degrees on a 0.57 confidence reading.
- Measuring all twelve showed a clean separation. Upright pages report 0. Genuine rotations report the right angle above 3.8 confidence. Everything unreliable sits below 1.0.
- So the search came out and a single confidence threshold went in.

**Frontend.** React, built to static files, served by the same process on the same port. One command starts everything and no Node toolchain is needed to run it.

**A guardrail on model input.** An invoice comes from outside the company, and its text can be written to address the model rather than the reader. Because a clean invoice files itself, a successful injection would never meet a human. Input is screened, and anything rejected is routed to a human rather than skipped.

## 5. How you used AI, and how you checked it

**What you delegated to AI**

- Only the reading of a page into fields.
- Every downstream decision is ordinary deterministic code: are the numbers self-consistent, is the supplier real, has this invoice been seen, may it be registered.
- The model is a reader. Never a decision-maker.

**How you verified the output**

- Ten checks run on every invoice. None of them consult the model.
- Seven are scored on the review screen.
- Three (tax code present, tax code known, date order) exist to explain a failure rather than to be counted twice.

The one that does the real work is the cross-foot tied to the printed total.

1. Sum the line amounts into a subtotal.
2. Recompute tax per tax code, on that code's subtotal, rounded down.
3. Add the two.
4. The result must equal the total **printed on the page**.

Why that one:

- It catches the failure that is otherwise invisible: a dropped line item.
- If a model misses a row, every remaining number is individually plausible and internally consistent.
- Only the tie to the printed grand total reveals something is missing.
- Recomputing the total from the extracted lines alone would agree with itself and prove nothing.

The others:

- The supplier must match the master: registration number, then partner code, then the master's own names and aliases.
- The invoice must not repeat one this app has already registered.
- The due date may not precede the issue date.
- Every field the API requires must be present, including a unit on every line.
- Tax codes must be known.
- Amounts must be whole yen.

An invoice failing any check is held. Nothing registers automatically unless all of them pass.

**A case where the AI got it wrong**

- **invoice_11.** The model returned a well-formed, entirely plausible invoice and left the tax code off two lines. Every amount was right. The JSON was valid. Tax cannot be recomputed without a code, so check 2 failed and the document was held.
- Earlier in development the same invoice came back missing a whole line item, and the cross-foot caught that instead.
- Same class of failure both times: output that looks correct and is not, caught by arithmetic rather than by reading.

Two more failures shaped the design.

- **The same document does not always read the same way.** invoice_01 is a clean text-layer PDF. It read 7 of 7 on one pass and 6 of 7 on another, with the printed total misread the second time. Nothing about the input changed. This is my strongest argument for comparing against the printed total instead of trusting a single read.
- **Confabulation, not omission.** Asked to transcribe handwritten annotations, the model sometimes describes what such a note *would* say rather than what is written. Arithmetic cannot catch that; a person can. So that text is shown to the reviewer as something to check against the page, and is never allowed into a structured field. A handwritten annotation is a prompt to look at the original, not data.

Separately, endpoints sometimes return nothing usable at all. Not subtle, but it matters for the same reason: unusable output must fail closed. It does. Those invoices are held, never guessed at, with every model's failure reason on screen.

## 6. Integrating with the accounting system

**How the API's constraints shaped the design**

- **Duplicates are checked locally, before anything is sent.** Learning about a duplicate from the API's own error means the request was already made.
- **What counts as a duplicate is deliberately narrow: only an invoice this app has already registered.** Two held or unread copies do not block each other. Neither has been sent anywhere, and blocking on them would strand a document behind a copy that may never be filed.
- **Registrations are sent strictly one at a time, and the duplicate check is repeated inside that lock, immediately before the request.** The API's own duplicate check is not atomic under concurrency. Parallel submission can produce two records for one invoice, which is exactly what the client is afraid of.
- **Tax is recomputed the way the API computes it**, per code and rounded down, so a rejection means real disagreement, not a rounding difference.

**The hardest constraint: a registration cannot be taken back one record at a time.**

`DELETE /invoices` clears everything or nothing. Rather than declare registration irreversible and leave an operator stuck, the app builds an undo on top of it:

1. Read back everything the accounting system holds.
2. Match every record to a document this app still has.
3. If even one cannot be matched, stop. Delete nothing. Name the invoice that could not be rebuilt.
4. Otherwise delete all records, then register the survivors again.

That refusal matters more than the feature. An undo that silently discards someone else's records would be worse than no undo at all.

**A single clean pass over all twelve, with the database and the ledger emptied first.**

| Invoice | Result | How you handled it |
|---|---|---|
| invoice_01 | Registered, 7/7 | Text layer read locally, then structured. 18s |
| invoice_02 | Registered, 7/7 | Text layer, two pages, full line table read. 75s |
| invoice_03 | Registered, 7/7 | Text layer read locally, then structured. 45s |
| invoice_04 | Registered, 7/7 | Scan read by the paid vision model on the first try. 12s |
| invoice_05 | Held, 1/7 | Every model in the chain failed. Held with all six failure reasons shown. Nothing guessed |
| invoice_06 | Registered, 7/7 | Supplier printed under a trading name, matched through the master's aliases |
| invoice_07 | Held, 6/7 | Photograph of the same invoice as invoice_01. Caught locally, never sent |
| invoice_08 | Registered, 7/7 | Two tax rates on one invoice, tax recomputed per code. Also carries a handwritten bank-account change, shown to the reviewer |
| invoice_09 | Held, 6/7 | Printed total is one yen above its own lines. A defect in the source, not in the reading |
| invoice_10 | Held, 5/7 | Supplier absent from the partner master. Needs onboarding, not better extraction |
| invoice_11 | Held, 6/7 | Tax code omitted on two lines, so tax could not be recomputed |
| invoice_12 | Registered, 7/7 | Discount in Japanese negative notation, converted to a negative amount |

- **7 of 12 registered with no human.**
- **5 held.** None was a case where guessing would have been safe: one unreadable, one duplicate, one defective source, one unknown supplier, one incomplete read.
- **Nothing was mis-registered.**

Throughput varies with what the endpoints are doing that day. On an exhausted free tier the same twelve produce **more held documents, not more wrong ones**. An unreadable invoice is held exactly like a failed check. The three text-layer invoices are least affected, because they never send an image.

## 7. Cost, limits, and risk in production

Token counts are what the app records for the call that answered. Rates are OpenRouter's own, read from `GET https://openrouter.ai/api/v1/models` on 2026-08-25.

| Model | Input, USD per million | Output, USD per million |
|---|---|---|
| `deepseek/deepseek-v3.2` | 0.26 | 0.38 |
| `google/gemini-2.5-flash-lite` | 0.10 | 0.40 |
| the `:free` models in both chains | 0 | 0 |

- **Cost per invoice** (and what makes it up): only 4 of the 12 cost anything.

  | Invoice | Model that answered | Input | Output | Cost |
  |---|---|---|---|---|
  | invoice_01 | `deepseek-v3.2` | 16,296 | 589 | $0.00446 |
  | invoice_02 | `deepseek-v3.2` | 19,798 | 2,442 | $0.00608 |
  | invoice_03 | `deepseek-v3.2` | 17,890 | 1,289 | $0.00514 |
  | invoice_04 | `gemini-2.5-flash-lite` | 11,057 | 450 | $0.00129 |
  | seven scans | free models | 29,022 | 31,733 | $0 |
  | invoice_05 | none answered | 0 | 0 | $0 |

  - **Run total: $0.0170 for twelve invoices. $0.00141 each.**
  - Text-layer PDF: **$0.00523**, because the whole transcript goes into the prompt.
  - One image page on `flash-lite`: **$0.00129**.
  - An image on a free model: **$0**.
  - Text-layer documents cost four times an image page, and are still the best value in the system, because they never fail.
  - **These are a floor, not a total.** The app counts tokens only from the call that answered. Timed-out and refused calls are invisible to it, and a provider may still bill for tokens generated before a client-side timeout.
  - Eight of the nine images ran a full 180-second `flash-lite` call before falling through. Charging those at invoice_04's input size adds about 88,000 tokens and **$0.0088**. Realistic ceiling: **$0.026 for the run, $0.00215 per invoice**.

- **Monthly cost at 1,000 invoices per month**:

  | Scenario | Per invoice | Per month |
  |---|---|---|
  | As measured, free tail carrying 7 of 12 | $0.00141 | **$1.41** |
  | No free tier at all, at the sample mix of 25% text and 75% image | $0.00227 | **$2.27** |
  | Measured plus the timeout ceiling above | $0.00215 | **$2.15** |

  At 150 yen to the dollar: about **¥0.34 per invoice, ¥340 a month**.

  **Review labour is the number that matters, and it is not close.**

  - 5 of 12 held, so 1,000 invoices produces about **417 reviews**.
  - At three minutes each: **21 hours a month**.
  - At ¥2,000 an hour: **¥41,700 a month**, against ¥340 of model spend.
  - **A factor of about 120.**
  - The 417 is measured. The three minutes and the hourly rate are my assumptions.
  - So any change that removes a review is worth roughly 120 times the same proportional saving on inference. That is why section 8 spends two of three slots on the review path.

- **Processing time per invoice**:

  - Text-layer PDF: **46 seconds** mean, 18 to 75 across the three.
  - Image: **226 seconds** mean, 12 to 368.
  - Whole run: **2,171 seconds, 36.2 minutes for twelve**, 181 seconds each.
  - **Failover, not reading, is what that buys.** `MODEL_TIMEOUT_SECONDS` is 180. `flash-lite` timed out on eight of nine images. invoice_05 burned two full timeouts before every model had failed.
  - That is **1,620 of the 2,171 seconds, 75 percent of the wall clock, spent on calls that never returned**.
  - The one image `flash-lite` answered directly took **12.1 seconds**. The free model that picked up the other eight answered in roughly **45**.
  - Dropping the timeout to 60 seconds would cut about **20 minutes** off this run without changing a single result.

- **Where this breaks first**:

  1. **Model availability.** Measured, not predicted. `flash-lite` timed out on eight of nine images. Every model failed on one. Neither produced a wrong registration, because both fail closed, but both cost throughput. Availability is also less stable than a dependency list suggests: checking the **ten** OpenRouter model ids this app is configured with against the catalogue on 2026-08-25, **two are no longer listed at all**, `nvidia/nemotron-nano-12b-v2-vl:free` and `nvidia/nemotron-nano-9b-v2:free`. Both were valid when the chains were built.
  2. **The review queue.** 417 reviews and 21 hours of human time per 1,000 invoices.
  3. **Structure, not load.** Reading runs on a thread per document inside the web process. Sequentially, 1,000 invoices is **50 hours of model wait**. Concurrency helps, but the ceiling is one machine, a restart loses in-flight work, and there is no retry beyond restarting stranded rows at startup.
  4. **Tenancy.** One database, one invoice folder, one API key. Separating one company's invoices from another's is a schema change, not a configuration change.

- **How you would find out if something was registered incorrectly**:

  - Read the ledger back with `GET /invoices` and reconcile it against the local record of what was sent.
  - The app already performs exactly this read on every unregister. The comparison exists. It would only need a schedule.
  - **What it catches:** a record the app has no document for; a document the app believes registered that the ledger does not hold; a partner and invoice number registered twice.
  - **What it cannot catch, and why.** `GET /invoices` returns `partner_code`, `invoice_number`, both dates, subtotal, tax, total and a line count. **It does not return the lines.** So an error preserving those eight fields is invisible: two line amounts swapped between rows, or a correct amount filed against the wrong description. It still cross-foots and still matches.
  - Reconciliation finds structural errors. The printed-total check finds missing rows. Only the review screen finds the rest.

## 8. What you would do with another 8 hours

1. **Turn images into text locally, before any model call.**
   - *What:* benchmark PaddleOCR and EasyOCR against the twelve samples, and against a small local VLM. Goal: Markdown that keeps the table layout well enough to feed the existing text chain.
   - *Why now:* 3 of 12 already take a text path. They are the cheapest, fastest and most reliable in the set, precisely because no image is uploaded. The other 9 send about 5,000 image tokens each and average 226 seconds.
   - *If it works:* 9 of 12 move onto the path that already behaves best. Image token cost goes to zero. The vision chain becomes a fallback for pages OCR cannot handle, instead of the default.
   - *Why first:* it attacks cost, latency and the failover problem with one change.
   - *Honest caveat:* this is R&D, not a certainty. That is exactly why it needs the time rather than an afternoon.

2. **Give the reviewer a confidence signal and a second chance.**
   - *What, part one:* a confidence score per extracted field, with low-confidence fields highlighted in red. The reviewer checks the two or three doubtful fields instead of re-reading the whole document.
   - *What, part two:* a "reprocess with a different model" action. It re-runs one document from the extraction stage. The model is chosen per document, and there is a separate setting for the system-wide default.
   - *Why:* today, when a read is poor, the only recovery is retyping by hand. Section 6 shows why that matters. invoice_11 came back with two tax codes missing. invoice_05 came back with nothing at all. In both, a different model is far more likely to fix the document than a human transcribing it.
   - *Why second:* review labour is the dominant cost in section 7, at roughly 120 times model spend. This is the change that reduces it most directly.
   - *Bonus:* the same machinery makes an automatic second read cheap to add later. Two independent reads that agree is a much stronger signal than one read that looks plausible. Section 5 records a text-layer PDF that read 7 of 7 on one pass and 6 of 7 on the next, with nothing about the input changed.

3. **Move reading onto a real task queue.**
   - *What:* Celery, or any broker-backed equivalent, in place of a thread per document inside the web process.
   - *What it gives:* retries with backoff. Work that survives a restart. Visible failures. More workers instead of a bigger machine.
   - *Today:* the only failure handling is restarting stranded rows at startup.
   - *Why third:* it changes no answer the system produces. Nothing about it makes an extraction more correct, and a wrong registration is still what I am most afraid of.
   - *But:* it is the first thing that must exist before this runs on more than one machine, and it is where the current design is most obviously a prototype.

Just below these three: approval roles, and a durable audit trail of who approved and who unregistered what. No finance team can run a payment path without them. But they make nothing more accurate, and with three slots I would rather spend them on reducing wrong reads and human minutes.
