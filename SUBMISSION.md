# Submission

- Name: Soumit
- Submission date (YYYY-MM-DD): 2026-08-22
- Hours actually spent: 8
- Repository / how to run it: https://github.com/soumit1803063/take-home — setup and the single start command are in `README.md`. Screenshots of it running are in `docs/`.

## 1. Understanding the request

The email asks for AI that reads invoices so staff stop typing them by hand. That is the stated problem, and taken literally it is an extraction problem.

I do not think extraction is the problem worth solving. The sentence that matters most is the one about nearly paying the same invoice twice. Manual entry is slow, but it has a human looking at every number. Automating extraction without replacing that judgement removes the only control the process currently has, and it removes it in front of a system that cannot be corrected: the accounting API has no update and no per-record delete, so a wrong registration is permanent.

So the problem I set out to solve is: **get invoices into the accounting system without ever putting a wrong one in.** Extraction is a component of that, not the goal. The centre of the build is the verification layer and the human gate in front of registration. Speed is what is left over once correctness is guaranteed, and on the machine-readable invoices it is a rounding error anyway.

## 2. What you would have asked the client

| What you wanted to ask | The assumption you made | Why |
|---|---|---|
| When an invoice's printed total disagrees with its own line items by a yen, do you pay the printed total or the computed one? | Neither. Stop and ask a human. | One sample invoice has exactly this defect. Guessing either way silently changes what a supplier is paid. |
| What should happen when a supplier is not in the partner master? | Hold it for a human; do not attempt registration. | The API rejects it and offers no way to onboard a supplier. This is an operational gap, not an extraction failure. |
| Who may approve a registration, and is one approval enough? | Anyone using the review screen; one approval. | No role information exists in the brief. Flagged as the first thing to fix before real use. |
| Is a handwritten correction on an invoice authoritative? | No. Extract the printed values; show the handwriting to the reviewer and let them decide. | One sample carries a handwritten bank-account change. Treating handwriting as data would let anyone with a pen redirect a payment. |
| How current must the accounting system be — same day, or is a queue acceptable? | A queue is acceptable; nothing auto-registers. | Month-end close is the stated pain, which is a batch process, not a real-time one. |

## 3. Scoping decisions

**What you built**

Ingestion for all three input shapes in the sample set, routed by what each file actually is rather than by its extension. Extraction into a fixed schema. A deterministic verification suite that runs on every invoice. Partner matching against the live master. A local duplicate check that runs before anything is sent. Full integration with the accounting API including its error codes. A review screen where a person corrects fields and approves registration. A single command that starts all of it.

**What you left out, and why**

I cut anything that did not reduce the chance of a wrong registration.

No automatic correction of anything — no skew or rotation correction, no re-processing of a poor scan at higher resolution, no fuzzy supplier-name matching. Each replaces a human decision with a guess, and a guess in front of an unfixable ledger is the failure mode I am trying to remove.

No multi-invoice PDF splitting, no batch-scanner support, no handling for documents beyond a few pages. The sample set tops out at two pages, so anything built for larger batches would be untested code shipped on speculation.

No user accounts, no approval roles, no audit trail beyond the local record. Real deployment needs all three; none of them make the extraction more correct, and I would rather ship a narrow thing that works than a broad thing I cannot verify in the time.

No automated test suite. Verification of the model output ships as product code and runs on every invoice, which is what actually protects the ledger.

## 4. Design and technology choices

The flow: a file is classified by inspecting it, extracted by the reader appropriate to its class, normalised, verified arithmetically, and then either held for a human or made available to register. Registration is always a deliberate human action.

**Routing before extraction.** A PDF is checked for a real text layer. If it has one, the text is parsed directly and no model is involved at all. Three of the twelve invoices are in this class, and they extract in under a tenth of a second at zero cost, with the unit column read straight out of the document. Sending a machine-readable document to a vision model would be slower, cost money, and introduce a misread where none previously existed.

**Vision for the rest.** The remaining nine are photographs or a scan with no text. These go to a vision model with a fixed output schema, so the model returns typed structured data rather than prose that has to be parsed.

**Which model, and why.** I used `nvidia/nemotron-nano-12b-v2-vl` through OpenRouter's free tier as the primary reader, with Google's `gemini-3.7-flash` free tier as a fallback. The brief permits a free tier and there are only twelve invoices, so paid capacity buys nothing here. I tested the first model I considered before building on it and found it was text-only and physically incapable of reading an image, which would have failed nine of twelve invoices. Checking that before integration rather than after is the only reason it did not become a rewrite.

**What I decided against.** OCR followed by a language model, because the vision model reads Japanese layout directly and an OCR stage adds a failure mode without adding information. A dedicated orientation classifier, because it is a heavyweight dependency and no sample invoice is actually rotated. Redacting personal data before sending it to the model, because the tax registration number is the field used to identify the supplier — redacting it would break the matching the system exists to do.

**Frontend.** React, built to static files and served by the same process on the same port, so the whole system starts with one command and needs no Node toolchain to run.

**A guardrail on model input.** An invoice is a document supplied by someone outside the company, and its text can be written to address the model rather than the reader. Because the human gate reviews the model's output, a successful instruction injection would be reviewed rather than caught. Input is screened, and anything rejected is routed to a human rather than skipped.

## 5. How you used AI, and how you checked it

**What you delegated to AI**

Only the reading of a page into fields. Every downstream decision — whether the numbers are self-consistent, whether the supplier is real, whether this invoice has been seen before, whether it may be registered — is ordinary deterministic code. The model is a reader, never a decision-maker.

**How you verified the output**

Seven checks run on every invoice, none of which consult the model.

The one that does the real work is the cross-foot tied to the printed total: line amounts are summed to a subtotal, tax is recomputed per tax code on that code's subtotal and rounded down, the two are added, and the result must equal the total **printed on the page**. I chose this check because it catches the failure that is otherwise invisible — a dropped line item. If a model misses a row, every remaining number is individually plausible and internally consistent; only the tie to the printed grand total reveals something is missing. Recomputing the total from the extracted lines alone would agree with itself and prove nothing.

The others: the supplier must match the master by registration number; the invoice must not duplicate one already recorded locally; the due date may not precede the issue date; every field the accounting system requires must be present, including a unit on every line; tax codes must be known; and amounts must be whole yen. An invoice failing any check is held for a human. Nothing is registered automatically unless all of them pass.

**A case where the AI got it wrong**

On invoice_11 the model returned a well-formed, entirely plausible invoice that was missing one line item. Every field looked reasonable and the JSON was valid. The cross-foot caught it: the extracted lines summed to less than the total printed on the page, so the invoice was blocked and sent to review rather than registered. This is exactly the case the check was chosen for, and it is why the check compares against the printed total rather than against the model's own arithmetic.

A second failure, of a different kind, is worth recording because it shaped the design. Asked to transcribe the handwritten annotations on a page, the model sometimes returns a description of what such a note *would* look like rather than what is actually written — a confabulation rather than an omission. It is caught by a person rather than by arithmetic, which is precisely why that text is shown to the reviewer as something to check against the page and is never allowed into a structured field. Any handwritten annotation is treated as a prompt to look at the original, not as data.

Separately, the free-tier vision endpoint sometimes returned output truncated mid-JSON. That is not a subtle error, but it matters for the same reason: unusable output must fail closed. It does — those invoices are held, never guessed at.

## 6. Integrating with the accounting system

The API's constraints shaped the design more than any other factor. It cannot be corrected after the fact, so the system treats registration as irreversible and puts a person in front of it. Duplicates are checked locally before anything is sent, because discovering a duplicate from the API's own error means the request was already made. Registrations are sent strictly one at a time — the API's duplicate check is not atomic under concurrency, and parallel submission can produce two records for the same invoice, which is precisely the outcome the client is afraid of. Tax is recomputed the way the API computes it, per code and rounded down, so a rejection means genuine disagreement rather than a rounding difference.

| Invoice | Result | How you handled it |
|---|---|---|
| invoice_01 | Registered | Text layer parsed directly, all checks passed |
| invoice_02 | Registered | Text layer, two pages, full line table read |
| invoice_03 | Registered | Text layer parsed directly, all checks passed |
| invoice_04 | Registered | Read by vision model, all checks passed |
| invoice_05 | Held for review | Extraction incomplete on the free tier; held rather than guessed |
| invoice_06 | Held for review | Supplier printed under a trading name; matched by registration number |
| invoice_07 | Blocked, never sent | Photograph of the same invoice as invoice_01; caught locally before any request |
| invoice_08 | Held for review | Two tax rates on one invoice; also carries a handwritten bank-account change shown to the reviewer |
| invoice_09 | Held for review | The document's own printed total is one yen above its line items — a defect in the source |
| invoice_10 | Cannot be registered | Supplier genuinely absent from the partner master; needs onboarding, not better extraction |
| invoice_11 | Held for review | Model dropped a line item; the cross-foot caught the shortfall |
| invoice_12 | Held for review | Discount written in Japanese negative notation, converted to a negative amount |

This table describes how each invoice is handled once it has been read. It is worth being straight about what varies: on an exhausted free tier the vision reader returns nothing usable for some of the image invoices, and those are held at the extraction step rather than reaching the outcome above. Both providers hit their limits during testing. Nothing was mis-registered as a result — an unreadable invoice is held exactly like a failed check — but throughput on a free tier is not something I would promise. The three text-layer invoices are unaffected, because they never call a model.

## 7. Cost, limits, and risk in production

- **Cost per invoice** (and what makes it up): Zero in direct model spend on the free tiers used here. A quarter of the invoices never touch a model at all. For those that do, measured usage is roughly 3,400 tokens per invoice, almost entirely image tokens — the prompt is negligible and the structured answer is under a hundred tokens. On a paid tier the model cost stays in fractions of a yen; the real cost is the human minute spent reviewing, which dominates by orders of magnitude.
- **Monthly cost at 1,000 invoices per month**: Model spend stays small — the same few thousand tokens per document, with a quarter skipping the model entirely. The cost that matters is review labour. At the current straight-through rate most invoices still reach a person, so the monthly figure is set by how many minutes each review takes, not by inference. Any published price should be re-checked against the vendor's live rates on the day, as free-tier terms change often.
- **Processing time per invoice**: Under a tenth of a second for a text-layer PDF. Between roughly 45 seconds and several minutes for an image on the free tier — slow, but it runs unattended in a batch, and the text-layer invoices are effectively instant.
- **Where this breaks first**: Free-tier capacity, and this is measured rather than predicted. During testing the fallback provider returned a hard daily quota error and the primary returned truncated responses under load. Neither caused a bad registration — both fail closed into human review — but both reduce throughput. Paid capacity is the first thing to buy. The second constraint is the review queue itself: the system is only as fast as the person clearing it.
- **How you would find out if something was registered incorrectly**: Read the registered invoices back from the API and reconcile them against the local record of what was sent. That catches transmission and duplication problems. It does not catch everything, and it is worth being plain about why: an error that preserves the totals — two line amounts swapped, a correct amount against the wrong description — is arithmetically consistent and indistinguishable from a correct entry using only the data the API stores. Reconciliation finds structural errors; the review screen has to catch the rest.

## 8. What you would do with another 8 hours

1. Buy paid model capacity and add a second independent read of every image invoice. Free-tier limits are the measured bottleneck, and two independent reads that agree is a far stronger signal than one read that looks plausible. It is the single change that would most raise the straight-through rate without lowering the safety bar.
2. Show the reviewer the exact region of the page each extracted value came from, instead of the whole image beside the fields. Most review time is spent hunting for a number to confirm it. This is the highest-value change per hour in the review screen, and it turns the model's claim about where a value appeared into something checkable.
3. Add approval roles and a durable audit trail of who approved what. This does not make extraction more accurate, which is why it is third, but no finance team can run a payment path in production without it.
