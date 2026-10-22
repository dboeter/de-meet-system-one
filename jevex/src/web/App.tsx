import { useCallback, useEffect, useState } from "react";
import { MODEL } from "../core/config.ts";
import { DemoContext, type LiveBlock, type Mode } from "./demo.tsx";
import { GUIDED } from "./guided.ts";
import type { ViewStart } from "./start.ts";
import { VIEWS, viewById, type ViewDef } from "./views.ts";

type Route =
  | { readonly kind: "free"; readonly view: ViewDef; readonly start: ViewStart }
  | { readonly kind: "guided"; readonly step: number }
  /** The speaker-notes window the presenter keeps on their own screen. */
  | { readonly kind: "notes" };

/** Main window → notes window: the guided step on screen, or null outside guided mode. */
const NOTES_CHANNEL = "jevex-notes";
const NOTES_STEP_ITEM = "jevex-notes-step";

const ZOOMS = [0.8, 0.9, 1, 1.15, 1.3, 1.5, 1.75] as const;

/** `#/guided/3` is step 3 of the script (1-based); `#/<view>` is free play, `#/<view>/blank` its empty email; `#/notes` the notes window. */
function routeFromHash(): Route {
  const path = window.location.hash.replace(/^#\/?/, "");
  if (path === "notes") return { kind: "notes" };
  const guided = /^guided(?:\/(\d+))?$/.exec(path);
  if (guided) {
    const n = Number(guided[1] ?? 1);
    return { kind: "guided", step: Math.min(Math.max(n, 1), GUIDED.length) - 1 };
  }
  const [id = "", suffix] = path.split("/");
  return { kind: "free", view: viewById(id) ?? VIEWS[0], start: suffix === "blank" ? { kind: "blank" } : { kind: "first" } };
}

function hashFor(route: Route): string {
  switch (route.kind) {
    case "guided":
      return `#/guided/${route.step + 1}`;
    case "notes":
      return "#/notes";
    case "free":
      return route.start.kind === "blank" ? `#/${route.view.id}/blank` : `#/${route.view.id}`;
    default: {
      const _exhaustive: never = route;
      return _exhaustive;
    }
  }
}

type Health = { readonly live: boolean; readonly blocked: LiveBlock | null };

function useHealth(): Health & { readonly refresh: () => void } {
  const [health, setHealth] = useState<Health>({ live: false, blocked: null });
  const refresh = useCallback(() => {
    // A static (recorded-only) deploy has no /api; any failure means live is unavailable.
    fetch("api/health")
      .then((r) => (r.ok ? r.json() : null))
      .then((body: unknown) => {
        if (typeof body !== "object" || body === null) return setHealth({ live: false, blocked: null });
        const live = "live" in body && body.live === true;
        const b = "blocked" in body ? body.blocked : null;
        setHealth({ live, blocked: b === "request_cap" || b === "token_cap" ? b : null });
      })
      .catch(() => setHealth({ live: false, blocked: null }));
  }, []);
  useEffect(refresh, [refresh]);
  return { ...health, refresh };
}

function asStep(v: unknown): number | null {
  return typeof v === "number" && Number.isInteger(v) && v >= 0 && v < GUIDED.length ? v : null;
}

function readStoredStep(): number | null {
  const stored = window.localStorage.getItem(NOTES_STEP_ITEM);
  return stored === null ? null : asStep(Number(stored));
}

/** The pop-out notes window: follows the main window's guided step. */
function NotesWindow() {
  const [step, setStep] = useState<number | null>(readStoredStep);
  useEffect(() => {
    const channel = new BroadcastChannel(NOTES_CHANNEL);
    channel.onmessage = (e: MessageEvent<unknown>) => setStep(asStep(e.data));
    return () => channel.close();
  }, []);
  const s = step === null ? undefined : GUIDED[step];
  const next = step === null ? undefined : GUIDED[step + 1];
  return (
    <main className="notes-window" data-testid="notes-window">
      {s && step !== null ? (
        <>
          <p className="muted">
            Step {step + 1} / {GUIDED.length}: <strong>{s.title}</strong>
          </p>
          <p className="notes-text">{s.note}</p>
          {next && <p className="muted">Next: {next.title}</p>}
        </>
      ) : (
        <p className="muted">Speaker notes follow the guided script. Start guided mode in the main window.</p>
      )}
    </main>
  );
}

function isTyping(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
}

export function App() {
  const [route] = useState<Route>(routeFromHash);
  return route.kind === "notes" ? <NotesWindow /> : <Presenter />;
}

function Presenter() {
  const [route, setRoute] = useState<Route>(routeFromHash);
  const [mode, setMode] = useState<Mode>("recorded");
  const [zoom, setZoom] = useState(2);
  const [notes, setNotes] = useState(false);
  const health = useHealth();
  const liveAvailable = health.live;

  const go = useCallback((next: Route) => {
    window.location.hash = hashFor(next);
  }, []);

  useEffect(() => {
    const onHash = () => setRoute(routeFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  useEffect(() => {
    document.documentElement.style.setProperty("--zoom", String(ZOOMS[zoom] ?? 1));
  }, [zoom]);

  const step = route.kind === "guided" ? GUIDED[route.step] : undefined;
  const view = step ? (viewById(step.view) ?? VIEWS[0]) : route.kind === "free" ? route.view : VIEWS[0];
  const start: ViewStart = step ? (step.start ?? { kind: "first" }) : route.kind === "free" ? route.start : { kind: "first" };

  // Tell the notes window which step is on screen.
  const guidedStep = route.kind === "guided" ? route.step : null;
  useEffect(() => {
    if (guidedStep === null) window.localStorage.removeItem(NOTES_STEP_ITEM);
    else window.localStorage.setItem(NOTES_STEP_ITEM, String(guidedStep));
    const channel = new BroadcastChannel(NOTES_CHANNEL);
    channel.postMessage(guidedStep);
    channel.close();
  }, [guidedStep]);

  // Draw attention to the step's element once the view has rendered its answer.
  useEffect(() => {
    document.querySelectorAll(".spotlight").forEach((el) => el.classList.remove("spotlight"));
    if (!step?.highlight) return;
    const selector = step.highlight;
    const id = window.setTimeout(() => document.querySelector(selector)?.classList.add("spotlight"), 150);
    return () => window.clearTimeout(id);
  }, [step]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || isTyping(e.target)) return;
      if (route.kind === "guided" && e.key === "ArrowRight" && route.step < GUIDED.length - 1) go({ kind: "guided", step: route.step + 1 });
      else if (route.kind === "guided" && e.key === "ArrowLeft" && route.step > 0) go({ kind: "guided", step: route.step - 1 });
      else if (e.key === "n" || e.key === "N") setNotes((n) => !n);
      else if (e.key === "+" || e.key === "=") setZoom((z) => Math.min(z + 1, ZOOMS.length - 1));
      else if (e.key === "-") setZoom((z) => Math.max(z - 1, 0));
      else if (e.key === "l" || e.key === "L") {
        // The live box: an empty email, live if the server allows it. Free play stays in free play.
        if (liveAvailable) setMode("live");
        if (route.kind === "guided") go({ kind: "guided", step: GUIDED.length - 1 });
        else go({ kind: "free", view: view.takesEmail ? view : VIEWS[0], start: { kind: "blank" } });
        window.setTimeout(() => document.querySelector<HTMLTextAreaElement>("[data-testid=email-input]")?.focus(), 100);
      } else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [route, go, liveAvailable, view]);

  const groups = [...new Set(VIEWS.map((v) => v.group))];
  const View = view.View;

  return (
    <DemoContext.Provider value={{ mode, liveAvailable, liveBlocked: health.blocked, refreshHealth: health.refresh }}>
      <div className="app">
        <header className="topbar">
          <div className="brand">
            <span className="logo" aria-hidden>
              [/]
            </span>
            jevex <span className="muted">regex vs Jev</span>
          </div>
          <div className="topbar-actions">
            <button
              type="button"
              className={route.kind === "guided" ? "pill selected" : "pill"}
              data-testid="guided-toggle"
              onClick={() => go(route.kind === "guided" ? { kind: "free", view, start: { kind: "first" } } : { kind: "guided", step: 0 })}
            >
              {route.kind === "guided" ? "Free play" : "Guided"}
            </button>
            <button
              type="button"
              className={`pill mode-${mode}`}
              data-testid="mode-pill"
              disabled={!liveAvailable && mode === "recorded"}
              title={liveAvailable ? "Switch between recorded and live answers" : "Live mode needs the server with TYPESAFE_API_KEY"}
              onClick={() => setMode(mode === "live" ? "recorded" : "live")}
            >
              <span className="dot" aria-hidden /> {mode === "live" ? "Live" : "Recorded answers"}
              {!liveAvailable && <span className="muted"> · live unavailable</span>}
              {liveAvailable && health.blocked && (
                <span className="muted" data-testid="live-blocked">
                  {" "}
                  · {health.blocked === "request_cap" ? "request cap reached" : "token cap reached"}
                </span>
              )}
            </button>
            <span className="model" title="Pinned model">
              {MODEL}
            </span>
            <button type="button" className="icon-button" aria-label="Zoom out" onClick={() => setZoom((z) => Math.max(z - 1, 0))}>
              −
            </button>
            <button type="button" className="icon-button" aria-label="Zoom in" onClick={() => setZoom((z) => Math.min(z + 1, ZOOMS.length - 1))}>
              +
            </button>
          </div>
        </header>
        <nav className="sidenav" aria-label="Stations">
          {groups.map((g) => (
            <div key={g} className="nav-group">
              <div className="nav-group-title">{g}</div>
              {VIEWS.filter((v) => v.group === g).map((v) => (
                <a key={v.id} href={`#/${v.id}`} className={v.id === view.id ? "nav-item active" : "nav-item"}>
                  {v.title} <code>{v.code}</code>
                </a>
              ))}
            </div>
          ))}
        </nav>
        <main className="main">
          {route.kind === "guided" && step && (
            <div className="guided-bar" data-testid="guided-bar">
              <button type="button" className="icon-button" aria-label="Previous step" disabled={route.step === 0} onClick={() => go({ kind: "guided", step: route.step - 1 })}>
                ←
              </button>
              <span className="guided-step" data-testid="guided-step">
                {route.step + 1} / {GUIDED.length}
              </span>
              <strong className="guided-title">{step.title}</strong>
              <button
                type="button"
                className="icon-button"
                aria-label="Next step"
                disabled={route.step === GUIDED.length - 1}
                onClick={() => go({ kind: "guided", step: route.step + 1 })}
              >
                →
              </button>
              <span className="muted small">← → steps · N notes · L live box · +/− zoom</span>
            </div>
          )}
          <View key={`${route.kind === "guided" ? `g${route.step}` : `${view.id}-${start.kind}`}-${mode}`} start={start} />
        </main>
        {notes && (
          <aside className="speaker-notes" data-testid="speaker-notes" aria-label="Speaker notes">
            <span data-testid="speaker-note-text">{step ? step.note : "Speaker notes appear in guided mode."}</span>
            <button
              type="button"
              className="pill notes-popout"
              data-testid="notes-popout"
              onClick={() => window.open("#/notes", "jevex-notes", "popup,width=760,height=420")}
            >
              Open on another screen
            </button>
          </aside>
        )}
      </div>
    </DemoContext.Provider>
  );
}
