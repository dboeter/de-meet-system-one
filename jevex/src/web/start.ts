/** What a screen opens on: a named preset, its first preset, or an empty email to type into. */
export type ViewStart = { readonly kind: "preset"; readonly presetId: string } | { readonly kind: "first" } | { readonly kind: "blank" };

export type ViewProps = { readonly start: ViewStart };

/** The preset a screen opens on; `undefined` for a blank start. Unknown ids fall back to the first. */
export function startPreset<P extends { readonly id: string }>(presets: readonly [P, ...P[]], start: ViewStart): P | undefined {
  switch (start.kind) {
    case "blank":
      return undefined;
    case "first":
      return presets[0];
    case "preset":
      return presets.find((p) => p.id === start.presetId) ?? presets[0];
    default: {
      const _exhaustive: never = start;
      return _exhaustive;
    }
  }
}
