# Lessons learned: working with System One models

What building these demos taught us about Jev, TypeSafe's System One model. The `demo/` and
`jevex/` figures come from small synthetic sets on `jev-1.13.0`, and the `rm-rjev/` figures
from its own 422-case report. They're not benchmarks, so treat them as hints.
The wording experiments are written up in full in
[demo/docs/lessons-learned.md](demo/docs/lessons-learned.md).

## Where it fits

- **Use it inside code, not instead of it.** Code settles what it can decide exactly, such
  as format checks, exact IDs, type filters and checksums. The model judges only the rows left over.
- **Let code find candidates and the model pick one.** It can pick the wrong one, but it never
  invents a value.
- **Put a threshold behind every probability.** The threshold turns it into accept, review or
  reject. A rule can't give you the review band. Set thresholds on your own labelled data.
- **Not every judgment fits.** As a permission judge in `rm-rjev/`, Jev let through 6.0% of the
  calls it should have stopped, and Haiku and Luna let through none. A gate at 0.95 cut that
  to 2.2% but dropped accuracy from 96.8% to 81.3%.

## Asking good questions

- **Put context in state and the requirement in `instructions`.** One sentence about the
  source system took schema mapping from 19 to 20 of 25 columns.
- **Describe the property the labels encode.** "One specific building, its own house
  number" beat "can a parcel be delivered here?", which would pass `Postbus 1200`.
- **Describe the category, never the rows you'll judge.** Options that name values from the
  data make the model overfitted on exactly those values, and useless on others.
- **Leave out detail the code already handles.** Removing a redundant `(type)` suffix sent the
  one wrong schema pre-fill to review.
- **Gate a Choice on the chosen option's own probability.** A Choice can be sure that
  something fits, with `other` near 0, while it splits 0.56/0.44 between two options.
- **Splitting a Choice into yes/no Nouls isn't a free win** when the options exclude each other.

## Reading the answers

- **Compare margins and review counts, not just accuracy.** Every DQ variant decided its
  auto-decided rows correctly, so only the margin told them apart.
- **Expect answers to move between repeats.** Trust a difference only when it is bigger than
  the repeat noise.
- **Change one wording at a time** and compare it with the old one on the same data.

## Running it

- **Pin the model.** A new model or a new wording gives new answers.
- **It is cheap and fast enough to call per row.** A call takes about 215 ms at p50 and a
  million questions cost about $13. Throughput grows with threads, from 4.3 rows/s
  sequential to 65 rows/s at 16.
- **Ask about distinct values, not rows.** Deduplication cut 90 cells to 73 calls.
- **A Choice takes at most 255 options.**
