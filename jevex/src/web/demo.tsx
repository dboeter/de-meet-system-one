import { createContext, useContext } from "react";

export type Mode = "recorded" | "live";

/** A server cap that refuses the next live request. */
export type LiveBlock = "request_cap" | "token_cap";

export type Demo = {
  readonly mode: Mode;
  /** Whether the server answered `/api/health` with live mode on. */
  readonly liveAvailable: boolean;
  /** The cap `/api/health` says is reached, if any. */
  readonly liveBlocked: LiveBlock | null;
  /** Re-read `/api/health`; called after every live answer. */
  readonly refreshHealth: () => void;
};

export const DemoContext = createContext<Demo>({ mode: "recorded", liveAvailable: false, liveBlocked: null, refreshHealth: () => {} });

export function useDemo(): Demo {
  return useContext(DemoContext);
}
