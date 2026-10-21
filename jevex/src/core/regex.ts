/** A labelled regex as written in the demo's editable baselines. */
export type RegexRule = {
  readonly label: string;
  readonly source: string;
  readonly flags: string;
  readonly pattern: RegExp;
};

export type Span = { readonly start: number; readonly end: number; readonly text: string };

export type ParsedRules =
  | { readonly kind: "ok"; readonly rules: readonly RegexRule[] }
  | { readonly kind: "error"; readonly line: number; readonly message: string };

const RULE_LINE = /^\s*([\w-]+)\s*:\s*\/(.*)\/([a-z]*)\s*$/;

/** Parse rules written one per line as `label: /source/flags`. Blank lines are ignored. */
export function parseRules(text: string): ParsedRules {
  const rules: RegexRule[] = [];
  const lines = text.split("\n");
  for (const [index, line] of lines.entries()) {
    if (line.trim() === "") continue;
    const m = RULE_LINE.exec(line);
    if (!m) return { kind: "error", line: index + 1, message: "Expected `label: /pattern/flags`" };
    const [, label = "", source = "", flags = ""] = m;
    try {
      rules.push({ label, source, flags, pattern: new RegExp(source, flags.replace("g", "")) });
    } catch (e) {
      return { kind: "error", line: index + 1, message: e instanceof Error ? e.message : String(e) };
    }
  }
  return { kind: "ok", rules };
}

/** Parse rules that ship with the app; a malformed default is a programming error. */
export function rulesOrThrow(text: string): readonly RegexRule[] {
  const parsed = parseRules(text);
  if (parsed.kind === "error") throw new Error(`Bad default rule on line ${parsed.line}: ${parsed.message}`);
  return parsed.rules;
}

export function formatRules(rules: readonly RegexRule[]): string {
  return rules.map((r) => `${r.label}: /${r.source}/${r.flags}`).join("\n");
}

export function firstSpan(pattern: RegExp, text: string): Span | null {
  return findAll(pattern, text)[0] ?? null;
}

/** First rule, in order, whose pattern matches. This is how keyword ladders route. */
export function firstMatch(
  rules: readonly RegexRule[],
  text: string,
): { readonly label: string; readonly span: Span } | null {
  for (const rule of rules) {
    const span = firstSpan(rule.pattern, text);
    if (span) return { label: rule.label, span };
  }
  return null;
}

export function findAll(pattern: RegExp, text: string): Span[] {
  const flags = pattern.flags.includes("g") ? pattern.flags : `${pattern.flags}g`;
  const global = new RegExp(pattern.source, flags);
  const spans: Span[] = [];
  for (const m of text.matchAll(global)) {
    if (m[0] === "") continue;
    spans.push({ start: m.index, end: m.index + m[0].length, text: m[0] });
  }
  return spans;
}
