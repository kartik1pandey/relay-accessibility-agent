import { useState, useEffect, useRef } from "react";

// Relay — the end-user runtime UI for the accessibility agent.
// Seven states from CLAUDE.md's design brief: idle/listening, transcribing,
// deciding, confirming, acting, blocked, error/not-found. Deliberately a
// different visual identity from build_checklist.jsx (that one is a
// developer build-tracker; this one is the end-user-facing product).
//
// Copy in CONFIRMING/BLOCKED/ERROR reuses the exact strings agent.py's
// Agent._say() produces, so this preview stays honest about what the
// backend actually says, not an invented tone.

const STATES = {
  listening: {
    tone: "calm", corner: "round", icon: "mic", live: true, app: "Mail",
    title: "Listening",
    caption: "Say what you'd like me to do.",
  },
  transcribing: {
    tone: "calm", corner: "round", icon: "wave", live: true, app: "Mail",
    title: "Understanding what you said",
    caption: "“Read me the new ones” — got it.",
  },
  deciding: {
    tone: "calm", corner: "round", icon: "search", live: true, app: "Mail",
    title: "Working out the next step",
    caption: "Looking at what's on screen in Mail.",
  },
  confirming: {
    tone: "confirm", corner: "sharp", icon: "bang", live: false, app: "Mail",
    title: "Confirm before I do this",
    caption: "Say yes to confirm: Send.",
    readout: 'control: "Send" · Button · Mail',
  },
  acting: {
    tone: "calm", corner: "round", icon: "check", live: true, app: "Mail",
    title: "Doing it now",
    caption: "Sending it now.",
    readout: 'control: "Send" · Button · Mail',
  },
  blocked: {
    tone: "block", corner: "sharp", icon: "slash", live: false, app: "Microsoft Edge",
    title: "I can't do that",
    caption: "I can't do that — Disable firewall is blocked.",
    readout: 'control: "Disable firewall" · MenuItem · Microsoft Edge',
  },
  error: {
    tone: "error", corner: "round", icon: "findx", live: false, app: "Media Player",
    title: "I couldn't find that",
    caption: "I couldn't find “Shuffle” on screen anymore.",
    readout: 'control: "Shuffle" · Button · Media Player',
  },
};

const ORDER = ["listening", "transcribing", "deciding", "confirming", "acting", "blocked", "error"];
const WALKTHROUGH = ["listening", "transcribing", "deciding", "confirming", "acting"];
const WALKTHROUGH_TIMINGS = { listening: 1600, transcribing: 1800, deciding: 1700, confirming: 3200, acting: 1800 };

// "calm" uses --accent-text, not --accent — verified 2026-09-10 via a real
// WCAG contrast check (check_contrast.mjs): plain --accent on --surface-2
// (the acting-state readout background) measured 5.34:1 in light mode,
// under the 7:1 AAA floor. --accent-text is the darkened text-safe variant;
// --accent itself stays reserved for icon strokes/borders, which only need
// the more lenient 3:1 non-text contrast.
const TONE_COLOR = {
  calm: "var(--accent-text)",
  confirm: "var(--confirm-text)",
  block: "var(--block-text)",
  error: "var(--error-text)",
};

function Icon({ name }) {
  const common = { fill: "none", stroke: "currentColor", strokeWidth: 6, strokeLinecap: "round", strokeLinejoin: "round" };
  switch (name) {
    case "mic":
      return (
        <svg viewBox="0 0 100 100" {...common}>
          <rect x="38" y="14" width="24" height="42" rx="12" />
          <path d="M26 46a24 24 0 0 0 48 0" />
          <line x1="50" y1="70" x2="50" y2="84" />
          <line x1="36" y1="84" x2="64" y2="84" />
        </svg>
      );
    case "wave":
      return (
        <svg viewBox="0 0 100 100" {...common} strokeWidth={7}>
          {[22, 38, 50, 62, 78].map((x, i) => (
            <line key={x} className="wave-bar" style={{ transformOrigin: `${x}px 50px`, animationDelay: `${i * 0.1}s` }}
              x1={x} y1={50 - (10 + i % 2 * 20)} x2={x} y2={50 + (10 + i % 2 * 20)} />
          ))}
        </svg>
      );
    case "search":
      return (
        <svg viewBox="0 0 100 100" {...common}>
          <circle cx="44" cy="44" r="26" />
          <line x1="63" y1="63" x2="86" y2="86" />
        </svg>
      );
    case "bang":
      return (
        <svg viewBox="0 0 100 100" {...common} strokeWidth={7}>
          <path d="M50 12 L90 78 A6 6 0 0 1 84.8 88 H15.2 A6 6 0 0 1 10 78 Z" />
          <line x1="50" y1="38" x2="50" y2="60" />
          <circle cx="50" cy="72" r="1.5" fill="currentColor" stroke="none" />
        </svg>
      );
    case "check":
      return (
        <svg viewBox="0 0 100 100" {...common} strokeWidth={7}>
          <circle cx="50" cy="50" r="38" />
          <path d="M33 51 L45 64 L69 36" />
        </svg>
      );
    case "slash":
      return (
        <svg viewBox="0 0 100 100" {...common} strokeWidth={7}>
          <circle cx="50" cy="50" r="38" />
          <line x1="24" y1="76" x2="76" y2="24" />
        </svg>
      );
    case "findx":
      return (
        <svg viewBox="0 0 100 100" {...common}>
          <circle cx="44" cy="44" r="26" strokeDasharray="7 7" />
          <line x1="63" y1="63" x2="86" y2="86" />
          <line x1="36" y1="36" x2="52" y2="52" />
          <line x1="52" y1="36" x2="36" y2="52" />
        </svg>
      );
    default:
      return null;
  }
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export default function RelayRuntimeUI() {
  const [stateKey, setStateKey] = useState("listening");
  const [muted, setMuted] = useState(false);
  const [reduceMotion, setReduceMotion] = useState(false);
  const [countdown, setCountdown] = useState(6);
  const [toast, setToast] = useState({ text: "", visible: false });
  const [walkthroughRunning, setWalkthroughRunning] = useState(false);

  const mutedRef = useRef(muted);
  const toastTimerRef = useRef(null);

  useEffect(() => { mutedRef.current = muted; }, [muted]);

  function speak(text) {
    if (mutedRef.current || !("speechSynthesis" in window)) return;
    try {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.rate = 1;
      window.speechSynthesis.speak(utter);
    } catch (e) {
      // speechSynthesis unavailable in this browser/context — visual channel still carries the state
    }
  }

  function goTo(key, opts = {}) {
    setStateKey(key);
    if (!opts.silent) speak(STATES[key].caption);
  }

  function showToast(text, after) {
    setToast({ text, visible: true });
    speak(text);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => {
      setToast((t) => ({ ...t, visible: false }));
      if (after) after();
    }, 2200);
  }

  // The confirming state's countdown is a visual echo of the same window
  // agent.py's _await_yes is implicitly listening in — not a real timer in
  // the backend today, but shown honestly as illustrative, matching the
  // "waiting to hear you" framing rather than inventing a hard deadline.
  useEffect(() => {
    if (stateKey !== "confirming") return;
    setCountdown(6);
    const id = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) {
          clearInterval(id);
          showToast("Okay, cancelled.", () => goTo("listening", { silent: true }));
          return 0;
        }
        return c - 1;
      });
    }, 1000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stateKey]);

  async function playWalkthrough() {
    if (walkthroughRunning) return;
    setWalkthroughRunning(true);
    for (const key of WALKTHROUGH) {
      goTo(key);
      await sleep(WALKTHROUGH_TIMINGS[key]);
    }
    goTo("listening", { silent: true });
    showToast("Walkthrough complete.");
    setWalkthroughRunning(false);
  }

  const s = STATES[stateKey];
  const toneColor = TONE_COLOR[s.tone];

  return (
    <div style={css.app} className={reduceMotion ? "relay reduce-motion" : "relay"}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&family=JetBrains+Mono:wght@500;600&display=swap');

        .relay :focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
        .relay .ghost-btn:hover, .relay .btn:hover { border-color: var(--ink-soft); }

        @media (prefers-reduced-motion: no-preference) {
          .relay:not(.reduce-motion) .wave-bar { animation: bar-bounce 1.1s ease-in-out infinite; }
          .relay:not(.reduce-motion) .icon-live { animation: icon-breathe 2.4s ease-in-out infinite; }
        }
        @keyframes bar-bounce { 0%, 100% { transform: scaleY(0.4); } 50% { transform: scaleY(1); } }
        @keyframes icon-breathe { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.06); } }
      `}</style>

      <header style={css.topbar}>
        <div style={css.contextChip}>
          <span style={css.contextDot} aria-hidden="true" />
          <span>Active app: <strong style={{ color: "var(--ink)" }}>{s.app}</strong></span>
        </div>
        <div style={css.modeControls}>
          <button
            className="ghost-btn"
            style={{ ...css.ghostBtn, ...(muted ? css.ghostBtnActive : {}) }}
            type="button"
            aria-pressed={muted}
            onClick={() => {
              setMuted((m) => !m);
              if (!muted && "speechSynthesis" in window) {
                try { window.speechSynthesis.cancel(); } catch (e) {}
              }
            }}
          >
            {muted ? "Voice replies: off" : "Voice replies: on"}
          </button>
          <button
            className="ghost-btn"
            style={{ ...css.ghostBtn, ...(reduceMotion ? css.ghostBtnActive : {}) }}
            type="button"
            aria-pressed={reduceMotion}
            onClick={() => setReduceMotion((r) => !r)}
          >
            Reduce motion
          </button>
        </div>
      </header>

      <main style={css.stage}>
        <div
          style={{
            ...css.stagePanel,
            ...(s.tone === "confirm" ? css.panelConfirm : {}),
            ...(s.tone === "block" ? css.panelBlock : {}),
            ...(s.tone === "error" ? css.panelError : {}),
            ...(s.tone === "calm" ? css.panelCalm : {}),
          }}
        >
          <div
            className={s.live ? "icon-live" : ""}
            style={{
              ...css.iconFrame,
              color: toneColor,
              borderColor: toneColor,
              borderRadius: s.corner === "sharp" ? 8 : 30,
            }}
          >
            <div style={{ width: 72, height: 72 }}><Icon name={s.icon} /></div>
          </div>

          <h1 style={{ ...css.stageTitle, color: s.tone === "calm" ? "var(--ink)" : toneColor }}>{s.title}</h1>

          <p style={css.stageCaption} aria-live={s.tone === "calm" ? "polite" : "assertive"}>{s.caption}</p>

          {s.readout && (
            <div style={{ ...css.stageReadout, color: toneColor, borderColor: s.tone !== "calm" ? toneColor : "var(--line)" }}>
              {s.readout}
            </div>
          )}

          {stateKey === "confirming" && (
            <div style={css.countdown}>
              <span>Waiting to hear you</span>
              <strong style={css.countdownNum}>{countdown}</strong>
              <span>s</span>
            </div>
          )}
        </div>
      </main>

      <div style={{ ...css.toast, ...(toast.visible ? css.toastShow : {}) }} role="status">
        {toast.text}
      </div>

      <footer style={css.demoDock}>
        <p style={css.demoHeading}>Demo controls</p>
        <p style={css.demoSub}>
          These buttons preview every state Relay can be in. They are not part of the product —
          the real Relay only ever responds to a voice command and, where needed, a spoken "yes."
        </p>
        <div style={css.demoRow}>
          <button
            className="btn"
            style={{ ...css.btn, ...css.btnPrimary, ...(walkthroughRunning ? css.btnDisabled : {}) }}
            type="button"
            disabled={walkthroughRunning}
            onClick={playWalkthrough}
          >
            {walkthroughRunning ? "Playing walkthrough…" : 'Play the "send an email" walkthrough'}
          </button>
        </div>
        <div style={{ ...css.demoRow, marginTop: 12 }}>
          {ORDER.map((key) => (
            <button
              key={key}
              className="btn"
              style={{ ...css.btn, ...(stateKey === key ? css.btnActive : {}) }}
              type="button"
              aria-pressed={stateKey === key}
              disabled={walkthroughRunning}
              onClick={() => goTo(key)}
            >
              {STATES[key].title}
            </button>
          ))}
        </div>
        {stateKey === "confirming" && (
          <div style={{ ...css.demoRow, marginTop: 12 }}>
            <button
              className="btn"
              style={{ ...css.btn, ...css.btnConfirmSim }}
              type="button"
              onClick={() => goTo("acting")}
            >
              Simulate: heard "yes"
            </button>
            <button
              className="btn"
              style={{ ...css.btn, ...css.btnConfirmSim }}
              type="button"
              onClick={() => showToast("Okay, cancelled.", () => goTo("listening", { silent: true }))}
            >
              Simulate: no response, cancel
            </button>
          </div>
        )}
      </footer>
    </div>
  );
}

const css = {
  app: {
    "--bg": "#F5F7F4",
    "--surface": "#FFFFFF",
    "--surface-2": "#EAEFE9",
    "--ink": "#10151A",
    "--ink-soft": "#3F4A47",
    "--line": "#D3DAD2",
    "--accent": "#1B6B6E",
    "--accent-text": "#0B4547",
    "--accent-on": "#FFFFFF",
    "--confirm": "#B8402C",
    "--confirm-text": "#7A2416",
    "--confirm-surface": "#FBEAE5",
    "--block": "#4B5560",
    "--block-text": "#2C333A",
    "--block-surface": "#E7EAEC",
    "--error": "#8A5A17",
    "--error-text": "#5E3C0E",
    "--error-surface": "#F5ECDD",
    "--focus": "#0B4547",
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column",
    background: "var(--bg)",
    color: "var(--ink)",
    fontFamily: "'Atkinson Hyperlegible', system-ui, 'Segoe UI', sans-serif",
    fontSize: 18,
    lineHeight: 1.5,
  },
  topbar: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    padding: "18px 28px",
    borderBottom: "1px solid var(--line)",
  },
  contextChip: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    fontSize: 18,
    color: "var(--ink-soft)",
  },
  contextDot: {
    width: 12,
    height: 12,
    borderRadius: "50%",
    background: "var(--accent)",
    flexShrink: 0,
    display: "inline-block",
  },
  modeControls: { display: "flex", gap: 10, flexWrap: "wrap" },
  ghostBtn: {
    minHeight: 48,
    padding: "0 18px",
    borderRadius: 10,
    border: "1.5px solid var(--line)",
    background: "var(--surface)",
    color: "var(--ink-soft)",
    font: "inherit",
    fontSize: 18,
    cursor: "pointer",
  },
  ghostBtnActive: {
    borderColor: "var(--accent)",
    color: "var(--accent-text)",
    background: "var(--surface-2)",
  },
  stage: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center",
    padding: "48px 24px",
  },
  stagePanel: {
    display: "inline-flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 18,
    padding: "40px 44px",
    borderRadius: 26,
    border: "2px solid var(--line)",
    maxWidth: 640,
    background: "var(--surface)",
  },
  panelCalm: { background: "var(--surface)", borderColor: "var(--line)" },
  panelConfirm: { background: "var(--confirm-surface)", borderColor: "var(--confirm)", borderWidth: 5, borderRadius: 12 },
  panelBlock: { background: "var(--block-surface)", borderColor: "var(--block)", borderWidth: 3, borderRadius: 10 },
  panelError: { background: "var(--error-surface)", borderColor: "var(--error)" },
  iconFrame: {
    width: 132,
    height: 132,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 4,
    borderStyle: "solid",
    background: "var(--surface)",
  },
  stageTitle: {
    fontSize: "clamp(30px, 4.6vw, 52px)",
    fontWeight: 700,
    textWrap: "balance",
    margin: 0,
    maxWidth: "18ch",
  },
  stageCaption: {
    fontSize: 23,
    color: "var(--ink-soft)",
    maxWidth: "46ch",
    margin: 0,
  },
  stageReadout: {
    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
    fontSize: 18,
    background: "var(--surface-2)",
    border: "1px solid var(--line)",
    borderRadius: 8,
    padding: "10px 16px",
  },
  countdown: {
    display: "flex",
    alignItems: "baseline",
    gap: 10,
    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
    fontSize: 20,
    color: "var(--confirm-text)",
  },
  countdownNum: { fontSize: 34, fontVariantNumeric: "tabular-nums" },
  toast: {
    position: "fixed",
    left: "50%",
    bottom: 190,
    transform: "translateX(-50%)",
    background: "var(--ink)",
    color: "var(--bg)",
    padding: "14px 22px",
    borderRadius: 10,
    fontSize: 18,
    opacity: 0,
    pointerEvents: "none",
    transition: "opacity 220ms ease",
  },
  toastShow: { opacity: 1 },
  demoDock: {
    borderTop: "1px solid var(--line)",
    background: "var(--surface-2)",
    padding: "20px 28px 26px",
  },
  demoHeading: { fontSize: 18, fontWeight: 700, margin: "0 0 4px" },
  demoSub: { fontSize: 18, color: "var(--ink-soft)", margin: "0 0 16px", maxWidth: "62ch" },
  demoRow: { display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" },
  btn: {
    minHeight: 48,
    padding: "0 20px",
    borderRadius: 10,
    border: "1.5px solid var(--line)",
    background: "var(--surface)",
    color: "var(--ink)",
    font: "inherit",
    fontSize: 18,
    cursor: "pointer",
  },
  btnActive: { background: "var(--accent)", borderColor: "var(--accent)", color: "var(--accent-on)" },
  btnPrimary: { background: "var(--accent)", borderColor: "var(--accent)", color: "var(--accent-on)", fontWeight: 700 },
  btnDisabled: { opacity: 0.6, cursor: "not-allowed" },
  btnConfirmSim: { borderColor: "var(--confirm)", color: "var(--confirm-text)" },
};
