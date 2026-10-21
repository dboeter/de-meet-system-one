export type Band = "yes" | "review" | "no";

/** Two cut-offs on a Noul probability: at or above `yes` acts, between the two goes to a person. */
export type BandThresholds = { readonly no: number; readonly yes: number };

export function band(p: number, t: BandThresholds): Band {
  if (p >= t.yes) return "yes";
  return p > t.no ? "review" : "no";
}
