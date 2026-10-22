# Lessons learned: question wording

We checked every Jev question in the demo against four prompt anti-patterns, tried a fix
for each one we found, and measured each fix against the old wording on the same data.
`notebooks/05_lessons.ipynb` recomputes every comparison from the recordings.
Every number below is from one run on the small synthetic sets (30 DQ rows, 25 source
columns). A difference of one column or two rows is a hint, not proof.

## The checklist

1. **Jev doesn't know your world.** Put context it needs in state.
2. **A question ID carries no meaning.** The requirement belongs in `instructions`.
3. **Score items one at a time** instead of one Choice over a blob.
4. **Describe the property, not the surface.** Option text that says what an answer looks
   like gets matched on looks.

Rule 2 was already met everywhere: every question, including the ones with opaque IDs
(`passes`, `code`, `target`, `same`), carries its full requirement in `instructions`.

## What we changed and what it did

| Change | Rule | Before | After | Adopted |
|---|---|---|---|---|
| Schema: leave the `(type)` suffix out of option descriptions | 4 | 60% pre-filled, 1 wrong pre-fill | 64%, none wrong | yes |
| Schema: the source system in state (`source_system`) | 1 | 76% top-1, 60% pre-filled | 80% top-1, 60% pre-filled | yes |
| Schema: both | 1, 4 | 76% top-1, 60% pre-filled, 1 wrong | 80%, 64%, none wrong | yes |
| DQ address: "one specific building, its own house number" instead of "street + number, optionally postcode/city" | 4 | lowest true row 0.68, 5 rows in review | 0.87, 3 rows | yes |
| DQ cancel reason: a pass/fail Noul plus a code Choice instead of `1 - p(other)` | 3 | lowest true row 0.94, 1 row in review | 0.67, 7 rows | no |

The rejected wordings stay recorded and runnable: `checks_variants.yaml` for DQ,
`schema.VARIANTS` for schema mapping. Both notebooks show them side by side with the
defaults.

## What we learned

**The labels define the property, not the rule of thumb.** The obvious fix for the address
check was to ask what we actually care about: can a parcel be delivered here? But the
labels mark `Postbus 1200` and `Molenweg, naast nummer 4` as failing, and a deliverability
question would pass both. Before rewording a check, walk every labelled row against the new
sentence. What helped was being precise about the property the labels encode: one building,
identified by its own house number. The street and number are still named; the wording just
says what they have to do.

**Redundant surface detail costs confidence in the wrong place.** The shortlist already
filters targets on type, so the `(type)` suffix told Jev nothing new. Removing it took the
one wrong pre-fill (`ORD_BTW_BDR → none`) from 0.86 to 0.73, below the 0.80 pre-fill
cutoff, so it went to review instead.

**Context in state moved top-1, not pre-fill.** One sentence about the source system
("a Dutch legacy ERP, abbreviated Dutch names") added a correct top answer (76% → 80%,
19 → 20 of 25), and `ORD_LVR_DT` is now mapped right. Pre-fill stayed at 60% on its own;
only together with the suffix change did it reach 64%. An earlier attempt that put generic
context in the question wording, not in state, gave 64% pre-filled; it also said other
things (cents versus euros), so the two aren't a clean comparison.

**Splitting a Choice into separate scores isn't a free win.** The checklist's rule 3 comes
from scoring separate blocks of one input. Our cancel check is different: it picks one of a
few mutually exclusive codes, and the Choice's `other` probability already separated
pass from fail sharply. The separate Noul was less sure of plain reasons
(`wachttijd te lang` 0.67, `bezorger kwam niet opdagen` 0.76).

**Measure the margin, not just accuracy.** Every DQ variant decided all auto-decided rows
correctly, so accuracy couldn't tell them apart. The gap between the lowest true row and
the highest false row, and the number of rows left in review, could.

## How to run the next experiment

- Add the new wording next to the old one; never edit the old request in place. Its
  recordings are keyed by the exact request body, so the old wording only stays
  replayable if its body doesn't change.
- Before calling the API, list which requests lack a recording. That list must be exactly
  the new variants; anything else means the change touched a baseline request.
- DQ answers are cached by `(check_id, value)`, and variants keep the same ids so the labels
  apply. Give each variant its own `Cache`, or it silently replays the other one's answers.
- Record with `scripts/record.py`, then compare in the notebook from recordings, so the
  comparison costs nothing to rerun.
