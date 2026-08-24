# Submission

- Name: Soumit
- Submission date (YYYY-MM-DD): 2026-08-25
- Hours actually spent: 8
- Repository / how to run it: https://github.com/soumit1803063/InvoiceExtractionAssignment. One command, `python run.py`. Setup is in `README.md`. A demo recording, annotated screenshots, and a rendered walkthrough of the whole workflow are attached with this submission.

## 1. Understanding the request

The email asks for AI that reads invoices so staff stop typing them by hand. That is the stated problem, and taken literally it is an extraction problem.

I do not think extraction is the problem worth solving. The sentence that matters most is the one about nearly paying the same invoice twice. Manual entry is slow, but it has a human looking at every number. Automating extraction without replacing that judgement removes the only control the process currently has, and it removes it in front of a system that cannot be corrected. The accounting API has no update call and no per-record delete, so a wrong registration is effectively permanent.

So the problem I set out to solve is: **get invoices into the accounting system without ever putting a wrong one in.** Extraction is a component of that, not the goal. The centre of the build is the verification layer that decides which invoices a human ever has to look at. Speed is what is left over once correctness is guaranteed.

## 2. What you would have asked the client

| What you wanted to ask | The assumption you made | Why |
|---|---|---|
| When an invoice's printed total disagrees with its own line items by a yen, do you pay the printed total or the computed one? | Neither. Stop and ask a human. | One sample invoice has exactly this defect. Guessing either way silently changes what a supplier is paid. |
| What should happen when a supplier is not in the partner master? | Hold it for a human. Do not attempt registration. | The API rejects it and offers no way to onboard a supplier. This is an operational gap, not an extraction failure. |
| Who may approve a registration, and is one approval enough? | Anyone using the review screen, and one approval. | No role information exists in the brief. Flagged as the first thing to fix before real use. |
| Is a handwritten correction on an invoice authoritative? | No. Extract the printed values. Show the handwriting to the reviewer and let them decide. | One sample carries a handwritten bank-account change. Treating handwriting as data would let anyone with a pen redirect a payment. |
| How current must the accounting system be, same day or is a queue acceptable? | A queue is acceptable, and an invoice that passes every check may file itself. | Month-end close is the stated pain, which is a batch process. Holding a provably correct invoice for a signature adds delay without adding safety. The checks are the gate, not the click. |
| If something is registered by mistake, how do you expect to undo it? | Build an undo on top of the only removal the API offers, and refuse it when it is not safe. | The API can only clear everything at once. Doing nothing leaves an operator with no recovery path at all. |

## 3. Scoping decisions

**What you built**

Ingestion for all three input shapes in the sample set, routed by what each file actually is rather than by its extension. Extraction into a fixed schema. A deterministic verification suite that runs on every invoice and on every correction. Partner matching against the live master. A local duplicate check that runs before anything is sent. Full integration with the accounting API including its error codes. A review screen where a person corrects fields and revalidates. A dashboard showing exactly what the accounting system will accept, so a reviewer can see why something was blocked. A guarded unregister that rebuilds the ledger when a registration has to be taken back. A single command that starts all of it.

**What you left out, and why**

I cut anything that did not reduce the chance of a wrong registration.

No correction that changes a number. Page orientation is corrected, because turning a sideways scan upright is a lossless 90 degree transpose that alters no pixel and no figure. Supplier matching does fall back to the master's own registered names and aliases when the registration number is misread, but only to an unambiguous single match. Two candidates means no match and a human decides. What I refused is anything that silently rewrites an amount. No re-scanning at higher resolution to improve a total, no guessing a missing line. A guess in front of a ledger that is hard to correct is the failure mode I am trying to remove.

No multi-invoice PDF splitting, no batch-scanner support, no handling for documents beyond a few pages. The sample set tops out at two pages, so anything built for larger batches would be untested code shipped on speculation.

No user accounts, no approval roles, no audit trail beyond the local record. Real deployment needs all three. None of them make the extraction more correct, and I would rather ship a narrow thing that works than a broad thing I cannot verify in the time.

No automated test suite. Verification of the model output ships as product code and runs on every invoice, which is what actually protects the ledger.

## 4. Design and technology choices

The flow: a file is classified by inspecting it, extracted by the reader appropriate to its class, normalised, verified arithmetically, and then either held for a human or filed. An invoice that passes every check files itself. An invoice that fails even one is held, and the person who fixes it presses the button. The gate is the checks, not the click. A human rubber-stamping a screen of numbers they cannot recompute is theatre, and the accounting system re-derives those numbers anyway.

**Routing before extraction.** A PDF is checked for a real text layer. If it has one, the text is pulled out locally and only that text goes to a model. Three of the twelve invoices are in this class. No image is rendered and none is uploaded, so the reading is cheaper and there is no chance of an OCR-style misread of a digit that was already machine-readable.

**Vision for the rest.** The remaining nine are photographs, or a PDF that contains only a scan. Each page is rendered to an image and sent to a vision model with a fixed output schema, so the model returns typed structured data rather than prose that has to be parsed.

**Which model, and why.** Two ordered chains, each ending in free models. Text-layer documents go to `deepseek/deepseek-v3.2`, then `google/gemini-2.5-flash-lite`, then four free OpenRouter models. Images go to `google/gemini-2.5-flash-lite`, then four free vision models led by `google/gemma-4-31b-it:free` and `nvidia/nemotron-3-nano-omni:free`. Google's own `gemini-3.7-flash` is tried ahead of both chains when a Gemini key is present.

I started free-only and moved the head of each chain to small paid models after measuring. Free tiers fail constantly and specifically: one model I picked returns 403 because it is only served to agentic harnesses, another returns prose instead of structured output, and daily quota runs out mid-run. All three happened during testing. A cheap paid model at the head raises the straight-through rate, and the free tail still catches it when the paid call is rate-limited or slow. Twelve invoices cost almost nothing either way, so the choice is about reliability, not price.

The chain is not theoretical. In the run recorded in section 6, the paid vision model answered one image and timed out on the rest, and a free model finished those documents. On one image every model in the chain failed, and the document was held with the whole failure list shown on screen.

**What I decided against.** OCR followed by a language model, because the vision model reads Japanese layout directly and an OCR stage adds a failure mode without adding information. Redacting personal data before sending it to the model, because the tax registration number is the field used to identify the supplier, and redacting it would break the matching the system exists to do.

**Orientation, and the rule it had to obey.** None of the twelve samples is rotated, but a copier feeds pages in sideways and that is the case this has to survive. Tesseract detects the angle when it is installed, and the page is turned by an exact 90 degree transpose, a pixel permutation rather than a resample, because degrading the image degrades the extraction that depends on it. An upright page is returned as the original bytes, untouched. If Tesseract is absent or errors, the original page is used and nothing else changes. My first version of this was worse than useless. It borrowed a brute-force search that rotated an already-upright invoice by 180 degrees on a 0.57 confidence reading. Measuring all twelve showed a clean separation: upright pages always report 0, genuine rotations report the right angle at confidence above 3.8, and everything unreliable sits below 1.0. So the search came out and a single confidence threshold went in.

**Frontend.** React, built to static files and served by the same process on the same port, so the whole system starts with one command and needs no Node toolchain to run.

**A guardrail on model input.** An invoice is a document supplied by someone outside the company, and its text can be written to address the model rather than the reader. Because a clean invoice files itself, a successful instruction injection would not meet a human at all. Input is screened, and anything rejected is routed to a human rather than skipped.

## 5. How you used AI, and how you checked it

**What you delegated to AI**

Only the reading of a page into fields. Every downstream decision, whether the numbers are self-consistent, whether the supplier is real, whether this invoice has been seen before, whether it may be registered, is ordinary deterministic code. The model is a reader, never a decision-maker.

**How you verified the output**

Ten checks run on every invoice, none of which consult the model. Seven are scored on the review screen. Three of them (tax code present, tax code known, date order) exist to explain a failure rather than to be counted twice.

The one that does the real work is the cross-foot tied to the printed total. Line amounts are summed to a subtotal, tax is recomputed per tax code on that code's subtotal and rounded down, the two are added, and the result must equal the total **printed on the page**. I chose this check because it catches the failure that is otherwise invisible, a dropped line item. If a model misses a row, every remaining number is individually plausible and internally consistent. Only the tie to the printed grand total reveals that something is missing. Recomputing the total from the extracted lines alone would agree with itself and prove nothing.

The others: the supplier must match the master, by registration number, then partner code, then the master's own name and aliases; the invoice must not repeat one this app has already registered; the due date may not precede the issue date; every field the accounting system requires must be present, including a unit on every line; tax codes must be known; and amounts must be whole yen. An invoice failing any check is held for a human. Nothing is registered automatically unless all of them pass.

**A case where the AI got it wrong**

On invoice_11 the model returned a well-formed, entirely plausible invoice and left the tax code off two of its lines. Every amount was right and the JSON was valid. Tax cannot be recomputed without a code, so check 2 failed and the document was held rather than registered. Earlier in development the same invoice came back missing a whole line item, and the cross-foot caught that instead. Both are the same class of failure: output that looks correct and is not, caught by arithmetic rather than by reading.

Two more failures shaped the design.

The first is that the same document does not always read the same way. Reading invoice_01, a clean text-layer PDF, gave 7 of 7 on one pass and 6 of 7 on another, with the printed total misread the second time. Nothing about the input changed. This is the strongest argument I have for keeping a check that compares against the printed total rather than trusting a single read.

The second is a confabulation rather than an omission. Asked to transcribe the handwritten annotations on a page, the model sometimes returns a description of what such a note *would* look like rather than what is actually written. It is caught by a person rather than by arithmetic, which is precisely why that text is shown to the reviewer as something to check against the page and is never allowed into a structured field. Any handwritten annotation is treated as a prompt to look at the original, not as data.

Separately, model endpoints sometimes return nothing usable at all. That is not a subtle error, but it matters for the same reason: unusable output must fail closed. It does. Those invoices are held, never guessed at, with every model's failure reason shown on screen.

## 6. Integrating with the accounting system

The API's constraints shaped the design more than any other factor. Duplicates are checked locally before anything is sent, because discovering a duplicate from the API's own error means the request was already made. What counts as a duplicate is deliberately narrow: only an invoice this app has **already registered**. Two unread or held copies of the same invoice do not block each other, because neither has been sent anywhere, and blocking on them would strand a document behind a copy that may never be filed. Registrations are sent strictly one at a time, and the duplicate check is repeated inside that lock immediately before the request, because the API's own duplicate check is not atomic under concurrency and parallel submission can produce two records for the same invoice, which is precisely the outcome the client is afraid of. Tax is recomputed the way the API computes it, per code and rounded down, so a rejection means genuine disagreement rather than a rounding difference.

The hardest constraint is that a registration cannot be taken back one record at a time. `DELETE /invoices` clears everything or nothing. Rather than declare registration irreversible and leave an operator stuck, the app builds an undo on top of that endpoint: it reads back everything the accounting system holds, matches every record to a document it still has, deletes them all, and registers the survivors again. If even one record cannot be matched, something registered by another tool or by an earlier run, nothing is deleted and the reason names the invoice that could not be rebuilt. That refusal matters more than the feature. An undo that silently discards someone else's records would be worse than no undo at all.

The table below is a single clean pass over all twelve invoices, with the database and the accounting ledger emptied first.

| Invoice | Result | How you handled it |
|---|---|---|
| invoice_01 | Registered, 7/7 | Text layer read locally, then structured. 18s |
| invoice_02 | Registered, 7/7 | Text layer, two pages, full line table read. 75s |
| invoice_03 | Registered, 7/7 | Text layer read locally, then structured. 45s |
| invoice_04 | Registered, 7/7 | Scan read by the paid vision model on the first try. 12s |
| invoice_05 | Held for review, 1/7 | Every model in the chain failed on this scan. Held with all six failure reasons shown, nothing guessed |
| invoice_06 | Registered, 7/7 | Supplier printed under a trading name, matched through the master's aliases |
| invoice_07 | Held for review, 6/7 | Photograph of the same invoice as invoice_01. Caught locally by the duplicate check, never sent |
| invoice_08 | Registered, 7/7 | Two tax rates on one invoice, tax recomputed per code. Also carries a handwritten bank-account change shown to the reviewer |
| invoice_09 | Held for review, 6/7 | The document's own printed total is one yen above its line items. A defect in the source, not in the reading |
| invoice_10 | Held for review, 5/7 | Supplier genuinely absent from the partner master. Needs onboarding, not better extraction |
| invoice_11 | Held for review, 6/7 | Model omitted the tax code on two lines, so tax could not be recomputed |
| invoice_12 | Registered, 7/7 | Discount written in Japanese negative notation, converted to a negative amount |

Seven of twelve registered without a human. Five were held, and none of the five was a case where guessing would have been safe: one unreadable, one duplicate, one defective source document, one unknown supplier, one incomplete read. Nothing was mis-registered.

Throughput varies with what the model endpoints are doing at the time, and that is worth being straight about. The same twelve invoices on an exhausted free tier produce more held documents, not more wrong ones. An unreadable invoice is held exactly like a failed check. The three text-layer invoices are the least affected, because they never send an image.

## 7. Cost, limits, and risk in production

Measured over the twelve-invoice run in section 6.

- **Cost per invoice** (and what makes it up): 94,000 input tokens and 36,500 output tokens across twelve invoices, so roughly 7,800 in and 3,000 out per invoice. The two classes differ sharply. A text-layer PDF sends about 18,000 input tokens of transcript and gets back about 1,400. An image sends about 5,000 input tokens, almost all of it image tokens, and gets back about 4,000, because the free vision models that answered most of them reason at length before returning the schema. At small-model rates this is fractions of a yen per invoice. The real cost is the human minute spent reviewing, which dominates by orders of magnitude. Any figure should be re-checked against the vendor's live rates on the day, as free-tier terms change often.
- **Monthly cost at 1,000 invoices per month**: Model spend stays small at these token counts. The cost that matters is review labour. Five of twelve reached a person in this run, so the monthly figure is set by how many minutes each of roughly 400 reviews takes, not by inference.
- **Processing time per invoice**: 46 seconds on average for a text-layer PDF, 18 to 75 seconds across the three. About 226 seconds on average for an image. That image figure is dominated by failover, not by reading: the primary vision model times out at 180 seconds and a free model then answers in under a minute. The one image the primary answered directly took 12 seconds. Lowering the timeout, or paying for capacity that does not time out, is the single biggest lever on wall-clock time.
- **Where this breaks first**: Model availability, and this is measured rather than predicted. In this run the paid vision model timed out on eight of nine images, and on one image every model in the chain failed. Neither caused a bad registration, because both fail closed into human review, but both cost throughput. Paid capacity that actually answers is the first thing to buy. The second constraint is the review queue itself. The system is only as fast as the person clearing it.
- **How you would find out if something was registered incorrectly**: Read the registered invoices back from the API and reconcile them against the local record of what was sent. The app already does this read on every unregister, and the same comparison run on a schedule would catch transmission and duplication problems. It does not catch everything, and it is worth being plain about why. An error that preserves the totals, two line amounts swapped, or a correct amount against the wrong description, is arithmetically consistent and indistinguishable from a correct entry using only the data the API stores. Reconciliation finds structural errors. The review screen has to catch the rest.

## 8. What you would do with another 8 hours

1. Buy vision capacity that answers inside the timeout, and add a second independent read of every image invoice. Failover is the measured bottleneck, and two independent reads that agree is a far stronger signal than one read that looks plausible. Given that the same document read twice already disagreed with itself once, this is the change that would most raise the straight-through rate without lowering the safety bar.
2. Show the reviewer the exact region of the page each extracted value came from, instead of the whole image beside the fields. Most review time is spent hunting for a number to confirm it. This is the highest-value change per hour in the review screen, and it turns the model's claim about where a value appeared into something checkable.
3. Add approval roles and a durable audit trail of who approved what, including who unregistered what. This does not make extraction more accurate, which is why it is third, but no finance team can run a payment path in production without it.
