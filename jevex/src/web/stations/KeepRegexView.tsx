import { StationHeader } from "../components.tsx";

const ROWS: readonly { readonly task: string; readonly use: "Regex / code" | "Jev" | "Both"; readonly why: string }[] = [
  { task: "Is this a valid email address, IBAN, postcode?", use: "Regex / code", why: "A question about shape. A pattern answers it exactly." },
  { task: "Find order IDs, amounts, dates, addresses", use: "Regex / code", why: "Over-collect candidates with a pattern; it never misses a well-formed one." },
  { task: "Totals, counts, date arithmetic", use: "Regex / code", why: "Counting and arithmetic belong in code." },
  { task: "Which of these amounts is the total charged?", use: "Both", why: "Regex proposes, Jev picks. The value is copied, never written." },
  { task: "What does the customer want?", use: "Jev", why: "Negation, sarcasm, tense and synonyms are about meaning." },
  { task: "Is this urgent? Should a person look first?", use: "Jev", why: "A probability lets code choose the threshold and the review band." },
];

export function KeepRegexView() {
  return (
    <>
      <StationHeader
        title="When to keep the regex"
        code="re vs jev"
        blurb="Jev is not a better regex for everything. Use each where it is exact, and combine them where one finds and the other judges."
      />
      <section className="card">
        <table className="score-table keep-table" data-testid="keep-table">
          <thead>
            <tr>
              <th>Task</th>
              <th>Use</th>
              <th>Why</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r) => (
              <tr key={r.task}>
                <td>{r.task}</td>
                <td>
                  <span className={`use use-${r.use === "Regex / code" ? "regex" : r.use.toLowerCase()}`}>{r.use}</span>
                </td>
                <td className="muted">{r.why}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
