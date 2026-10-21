# Labelling rubric: Intent, Flags and Triage

## Intent

Frozen before any gold label in `data/corpus.jsonl` was written. A rule added later means
relabelling every case, or reporting the cases by rubric version.

The question is the Intent station's, word for word (`src/core/stations/intent.ts`):
"What does the customer want from this email?"

| Label | Meaning |
|---|---|
| `refund` | Wants money back now, for a purchase |
| `exchange` | Wants a replacement or a different item, not money back |
| `cancel` | Wants to stop a subscription, order or account |
| `complaint` | Reports a problem or is unhappy, without asking for a specific remedy |
| `question` | Asks for information; no problem and no remedy requested |
| `praise` | Thanks or compliments; no action needed |
| `other` | None of the above |

### Rules, applied in order

1. **Label the action the writer asks for now**, not the words they use. A keyword that is
   negated ("I don't want a refund"), quoted, or about the past does not count.
2. **A requested remedy beats the complaint around it.** "It broke, I want my money back" is
   `refund`; "It broke, send a new one" is `exchange`. `complaint` is only for problems with
   no specific remedy asked.
3. **Asking about a policy is a `question`, not a request.** "Can I get a refund if…?",
   "How do I cancel?" are `question` unless the writer also says they want it done.
   "Can you refund order 123?" is a request phrased as a question: `refund`.
4. **Resolved and thankful is `praise`.** A past refund or fix mentioned with thanks and no new
   ask is `praise`.
5. **Sarcasm is read for meaning.** "Great, thanks for losing my parcel" is `complaint`.
6. **Several asks: the strongest action wins**, in this order: `cancel` > `refund` >
   `exchange` > `question`. Praise or complaint next to an ask never wins.
7. **Store credit, discount or partial compensation** count as `refund` (money back in some
   form). Repair counts as `exchange` (getting a working item).
8. **`other`** is for messages with no customer intent from this list: changing an address,
   a partnership pitch, spam, an empty or unrelated message.
9. **Ambiguous** cases (a careful reader could defend two labels under these rules) keep their
   best label and get the `ambiguous` tag, so they can be excluded from accuracy.

### Tags

- `easy`: the regex ladder in the Intent station gets it right. Every easy case must pass the
  regex; this keeps the scoreboard honest.
- `hard`: the regex gets it wrong, plus one reason tag: `negation`, `sarcasm`, `past-tense`,
  `typo`, `synonym`, `policy-question`, `multi-intent`, `no-keyword`, `polite-request`,
  `misleading-keyword` (a keyword appears in another sense).
- The regex verdict `none` counts as `other` when scoring the regex.
- `preset`: one of the seven presets in `docs/spec.md`.
- `ambiguous`: see rule 9.

## Flags

Written before any Flags gold label. The questions are the Flags station's, word for word
(`src/core/stations/flags.ts`). Each flag is labelled on its own: `true` when the question's
answer is yes for this email.

| Flag | True when |
|---|---|
| `asks_refund_now` | The customer asks, in this email, to get money back for a purchase: a refund, reversed charge or credit. |
| `wants_human` | The customer asks to deal with a human person at the company instead of a bot or automated reply. |
| `repeat_contact` | The customer says they already contacted support about this same issue. |
| `legal_or_chargeback_threat` | The customer threatens legal action, a complaint to a regulator, or a chargeback / payment dispute with their bank. |
| `cancellation_risk` | The customer says they will cancel, stop buying, or move to a competitor. |

### Rules

1. **What the writer does, not the words.** A negated ("I'm not going to sue"), quoted or
   unrelated use of a keyword does not count. "My manager asked me…" is a colleague, not an
   escalation.
2. **`asks_refund_now`:** a refund that already happened, or a question about refund policy,
   is false. "Reverse the charge", "credit it back", "put the money back on my card" are true.
3. **`wants_human`:** an explicit ask for a person, manager or someone at the company is true.
   Asking whether they are talking to a bot, or objecting to template replies, also counts as
   true: the writer is asking to get past the automation. Praising a named agent is false.
4. **`repeat_contact`:** earlier emails, calls or chats about this issue count ("third time
   writing", "we spoke yesterday", "still no reply to my email"). "Again" about buying again or
   a product failing again, with no earlier contact said, is false.
5. **`legal_or_chargeback_threat`:** conditional threats count ("or I'll dispute it with my
   bank"). A regulator or ombudsman counts. An action already taken ("I've filed a dispute")
   counts as true but is tagged `ambiguous`, since the question says "threaten".
6. **`cancellation_risk`:** a cancel request or a stated plan to cancel, stop buying or go
   elsewhere is true, including conditional ("one more mistake and you've lost a customer").
   A cancellation that already happened, "don't cancel", or switching plans with the same
   company is false.
7. **Ambiguous:** a case where a careful reader could defend the other value for at least one
   flag gets the `ambiguous` tag.

### Tags

- `easy`: the per-flag regex gets all five flags right (a match means true).
- `hard`: at least one flag is wrong by the regex, plus a reason tag as for Intent.
- `preset`, `ambiguous`: as for Intent.

## Triage

Written before any Triage gold label. The questions are the Triage station's
(`src/core/stations/triage.ts`): "Which team should handle this email?" and "How soon does
this email need a response?".

| Department | Handles |
|---|---|
| `returns` | Exchanges, returns, wrong or damaged items |
| `shipping` | Delivery status, delays, lost or misdelivered packages |
| `billing` | Charges, invoices, refunds of payments, payment problems |
| `account` | Logging in, passwords, account settings |
| `other` | Anything else, including feedback that needs no team |

### Department rules

1. **The team that has to act to fix it.** A double charge for a lost package is `billing`
   (the money is the fix); the package itself is a copy for `shipping`.
2. **Wrong or damaged item that did arrive → `returns`**, even when the damage happened in
   transit. A package that never came or went to the wrong place → `shipping`.
3. **Money for a return not yet received → `billing`** (a refund of a payment).
4. **Thanks or feedback with nothing to do → `other`**, whatever it mentions.
5. **Changing the delivery address of an order in progress → `shipping`.** Changing details
   stored on the account → `account`.

### Urgency rule

`urgent` is true when the situation is "Today" on the urgency scale: a deadline or event
within the next day or two, or harm that gets worse with every hour of waiting (money still
being taken, a business that cannot operate). A problem that has already happened and is not
growing, such as a past double charge or one person locked out, is not urgent. It is read
from the situation, not the tone:
capitals, `!!!` or "ASAP" with no deadline or harm are not urgent; a calm email with a
deadline is. The regex counts as urgent when its urgency pattern matches.

### Tags

- `easy`: the regex gets both the department (no match counts as `other`) and urgency right.
- `hard`: the regex gets at least one wrong, plus a reason tag as for Intent, or `tone` when
  urgency words and real urgency disagree.
- `preset`, `ambiguous`: as for Intent.
