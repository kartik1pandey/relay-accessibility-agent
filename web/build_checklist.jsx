import { useState, useEffect } from "react";

const CATEGORIES = [
  {
    id: "eligibility",
    title: "Eligibility & compliance",
    items: [
      { id: "elig-1", text: "Confirm Indian residency and the 18+ age requirement" },
      { id: "elig-2", text: "Create a Qualcomm ID and confirm Qualcomm AI Hub access" },
      { id: "elig-3", text: "Register on the actual Unstop submission page, not just this checklist" },
      { id: "elig-4", text: "Confirm the whole build is solely your own work, with nothing confidential in it" },
    ],
  },
  {
    id: "environment",
    title: "Environment & access",
    items: [
      { id: "env-1", text: "Install 64-bit x64 Python if working on a real Snapdragon X Elite/X2 Elite Windows machine" },
      { id: "env-2", text: "Install qai_hub_models and configure your AI Hub API token" },
      { id: "env-3", text: "Install the GenieX CLI and confirm the real Python SDK API" },
      { id: "env-4", text: "Confirm you can submit a profiling job to Qualcomm's hosted Snapdragon device farm" },
      { id: "env-5", text: "Decide whether you need hands-on hardware time (Croma / Reliance Digital Snapdragon zones) or cloud profiling alone is enough" },
    ],
  },
  {
    id: "models",
    title: "Model selection & benchmarking",
    items: [
      { id: "mod-1", text: "Pick and benchmark the Whisper variant for speech-to-text" },
      { id: "mod-2", text: "Set up MeloTTS-EN for the spoken responses" },
      { id: "mod-3", text: "Pick the default text-only reasoning model (e.g. Phi-4-Mini-Instruct) and benchmark it" },
      { id: "mod-4", text: "Pick the vision-fallback model (e.g. Qwen3-VL-4B-Instruct) and benchmark it separately" },
      { id: "mod-5", text: "Record every model's on-device latency and memory numbers for the write-up" },
    ],
  },
  {
    id: "perception",
    title: "Perception layer",
    items: [
      { id: "perc-1", text: "Get a UI Automation tree reading live off a real running app" },
      { id: "perc-2", text: "Tune the \"is this tree usable\" heuristic against real windows" },
      { id: "perc-3", text: "Wire the vision-fallback path end to end: screenshot to VLM to structured description" },
      { id: "perc-4", text: "Test tree coverage against all three target apps, not just one" },
    ],
  },
  {
    id: "reasoning",
    title: "Reasoning layer",
    items: [
      { id: "reas-1", text: "Lock the prompt format: transcript plus screen context to one decided action" },
      { id: "reas-2", text: "Handle the \"no matching control found\" case explicitly" },
      { id: "reas-3", text: "Add short-term memory for follow-ups like \"read the next one\"" },
    ],
  },
  {
    id: "guardrails",
    title: "Guardrails & safety",
    items: [
      { id: "guard-1", text: "Finalize the always-confirm pattern list" },
      { id: "guard-2", text: "Finalize the small hard-block list" },
      { id: "guard-3", text: "Build the spoken confirm-before-acting flow" },
      { id: "guard-4", text: "Test the gate against real controls in all three target apps" },
      { id: "guard-5", text: "Log every action and every gate decision somewhere reviewable" },
    ],
  },
  {
    id: "action",
    title: "Action execution",
    items: [
      { id: "act-1", text: "Execute actions via UI Automation's invoke/set-value patterns, not simulated clicks" },
      { id: "act-2", text: "Re-check the target element still matches right before acting" },
      { id: "act-3", text: "Handle \"element not found\" and \"app not responding\" with a spoken fallback" },
    ],
  },
  {
    id: "voice",
    title: "Voice I/O",
    items: [
      { id: "voice-1", text: "Wire microphone capture into Whisper end to end" },
      { id: "voice-2", text: "Wire MeloTTS output for responses and confirmations" },
      { id: "voice-3", text: "Decide push-to-talk vs. always-listening, and think through the privacy tradeoff" },
    ],
  },
  {
    id: "testing",
    title: "Testing",
    items: [
      { id: "test-1", text: "Measure full voice-to-action latency on real or profiled Snapdragon hardware" },
      { id: "test-2", text: "Build a fixed task list per target app and track success rate against it" },
      { id: "test-3", text: "Deliberately try to trip the confirmation gate, both to fire it and to over-fire it" },
    ],
  },
  {
    id: "docs",
    title: "Documentation & demo",
    items: [
      { id: "doc-1", text: "Write the technical write-up: architecture, model choices, benchmark numbers" },
      { id: "doc-2", text: "Script and record the demo video across the three target-app scenarios" },
      { id: "doc-3", text: "Clean up the repo and README, since submissions are made public" },
    ],
  },
  {
    id: "submission",
    title: "Submission",
    items: [
      { id: "sub-1", text: "Confirm the exact intake-form fields (video length, file types) from the real registration page" },
      { id: "sub-2", text: "Have the video link, repo link, and write-up ready before opening the form" },
      { id: "sub-3", text: "Submit by Sep 28\u201329, with a buffer before the Sep 30 deadline" },
      { id: "sub-4", text: "Do one last read-through of the whole form before hitting submit \u2014 there's no editing after" },
    ],
  },
];

const STORAGE_KEY = "snapdragon-a11y-checklist-state";

// Items genuinely completed and verified this session (see CLAUDE.md's
// "Resolved since the scaffold was written" for the full, dated evidence
// behind each one) — applied only as the STARTING state on a machine that's
// never saved progress before, never overriding whatever you've toggled
// yourself. Left unchecked on purpose: anything needing your own Qualcomm
// account/hardware, benchmarking, the demo recording itself, and the
// still-open design decisions (push-to-talk vs. always-listening) — none
// of those are code-completable, so marking them done here would be
// exactly the kind of overclaiming this whole project has tried to avoid.
const DEFAULT_CHECKED = {
  "env-1": true,
  "perc-1": true, "perc-2": true, "perc-4": true,
  "reas-1": true, "reas-2": true, "reas-3": true,
  "guard-1": true, "guard-2": true, "guard-3": true, "guard-4": true, "guard-5": true,
  "act-1": true, "act-2": true, "act-3": true,
  "voice-1": true, "voice-2": true,
  "test-2": true, "test-3": true,
  "doc-1": true, "doc-3": true,
};

function readLocalStorage(key) {
  try {
    return window.localStorage.getItem(key);
  } catch (e) {
    return null; // private browsing / storage disabled — degrade to session-only state
  }
}

function writeLocalStorage(key, value) {
  try {
    window.localStorage.setItem(key, value);
    return true;
  } catch (e) {
    return false;
  }
}

export default function BuildChecklist() {
  const [checked, setChecked] = useState({});
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const saved = readLocalStorage(STORAGE_KEY);
    setChecked(saved ? JSON.parse(saved) : DEFAULT_CHECKED);
    setLoaded(true);
  }, []);

  const persist = (next) => {
    const ok = writeLocalStorage(STORAGE_KEY, JSON.stringify(next));
    setError(ok ? null : "Couldn't save your progress -- your browser may be blocking local storage.");
  };

  const toggle = (id) => {
    const next = { ...checked, [id]: !checked[id] };
    setChecked(next);
    persist(next);
  };

  const resetAll = () => {
    setChecked({});
    persist({});
  };

  const allItems = CATEGORIES.flatMap((c) => c.items);
  const doneCount = allItems.filter((i) => checked[i.id]).length;
  const totalCount = allItems.length;
  const pct = totalCount ? Math.round((doneCount / totalCount) * 100) : 0;

  return (
    <div style={s.page}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');
        .cl-row { transition: background 120ms ease; }
        .cl-row:hover { background: #1B222A; }
        .cl-check { transition: background 120ms ease, border-color 120ms ease, transform 100ms ease; }
        .cl-row:active .cl-check { transform: scale(0.9); }
        .cl-reset:hover { color: #D9A25C; border-color: #D9A25C; }
      `}</style>

      <div style={s.header}>
        <div style={s.kicker}>Snapdragon AI Lab</div>
        <h1 style={s.h1}>Accessibility agent checklist</h1>

        {!loaded ? (
          <div style={s.loadingText}>Loading your progress\u2026</div>
        ) : (
          <div style={s.heroRow}>
            <div style={s.heroPct}>{pct}%</div>
            <div style={s.heroSide}>
              <div style={s.heroFrac}>{doneCount} / {totalCount} steps</div>
              <div style={s.track}>
                <div style={{ ...s.fill, width: `${pct}%` }} />
              </div>
            </div>
          </div>
        )}
      </div>

      {loaded && (
        <div style={s.body}>
          {CATEGORIES.map((cat) => {
            const catDone = cat.items.filter((i) => checked[i.id]).length;
            return (
              <div key={cat.id} style={s.section}>
                <div style={s.sectionHeader}>
                  <h2 style={s.sectionTitle}>{cat.title}</h2>
                  <span style={s.sectionCount}>{catDone}/{cat.items.length}</span>
                </div>
                <div>
                  {cat.items.map((item) => {
                    const isDone = !!checked[item.id];
                    return (
                      <div
                        key={item.id}
                        className="cl-row"
                        style={s.row}
                        onClick={() => toggle(item.id)}
                      >
                        <span
                          className="cl-check"
                          style={{ ...s.check, ...(isDone ? s.checkDone : {}) }}
                        >
                          {isDone ? "\u2713" : ""}
                        </span>
                        <span style={{ ...s.itemText, ...(isDone ? s.itemTextDone : {}) }}>
                          {item.text}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}

          {error && <div style={s.errorBanner}>{error}</div>}

          <button className="cl-reset" style={s.resetBtn} onClick={resetAll}>
            Reset all progress
          </button>
        </div>
      )}
    </div>
  );
}

const s = {
  page: {
    fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
    background: "#0F1419",
    color: "#E7E9EC",
    minHeight: "100%",
    padding: "40px 28px 56px",
    boxSizing: "border-box",
  },
  header: {
    maxWidth: 640,
    margin: "0 auto",
    paddingBottom: 28,
    borderBottom: "1px solid #262E38",
  },
  kicker: {
    fontSize: 13,
    color: "#7C8792",
    marginBottom: 6,
  },
  h1: {
    fontSize: 26,
    fontWeight: 600,
    margin: "0 0 20px",
    letterSpacing: "-0.01em",
  },
  loadingText: {
    fontSize: 14,
    color: "#7C8792",
  },
  heroRow: {
    display: "flex",
    alignItems: "flex-end",
    gap: 20,
  },
  heroPct: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 48,
    fontWeight: 600,
    color: "#C9832E",
    lineHeight: 1,
  },
  heroSide: {
    flex: 1,
    paddingBottom: 6,
  },
  heroFrac: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 13,
    color: "#7C8792",
    marginBottom: 8,
  },
  track: {
    height: 6,
    borderRadius: 3,
    background: "#1E2530",
    overflow: "hidden",
  },
  fill: {
    height: "100%",
    background: "#C9832E",
    borderRadius: 3,
    transition: "width 200ms ease",
  },
  body: {
    maxWidth: 640,
    margin: "0 auto",
  },
  section: {
    marginTop: 28,
  },
  sectionHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "baseline",
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: 600,
    margin: 0,
    color: "#E7E9EC",
  },
  sectionCount: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 12,
    color: "#4A8B8C",
  },
  row: {
    display: "flex",
    alignItems: "flex-start",
    gap: 12,
    padding: "9px 8px",
    borderRadius: 6,
    cursor: "pointer",
  },
  check: {
    flexShrink: 0,
    width: 18,
    height: 18,
    marginTop: 1,
    borderRadius: 4,
    border: "1.5px solid #3A4552",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 12,
    color: "#0F1419",
  },
  checkDone: {
    background: "#C9832E",
    borderColor: "#C9832E",
  },
  itemText: {
    fontSize: 14.5,
    lineHeight: 1.45,
    color: "#D5D8DC",
  },
  itemTextDone: {
    color: "#5C6672",
  },
  errorBanner: {
    marginTop: 20,
    padding: "10px 12px",
    borderRadius: 6,
    background: "#2A1F1A",
    border: "1px solid #4A3423",
    color: "#D9A25C",
    fontSize: 13,
  },
  resetBtn: {
    marginTop: 32,
    marginBottom: 8,
    background: "transparent",
    border: "1px solid #3A4552",
    color: "#7C8792",
    fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
    fontSize: 13,
    padding: "8px 14px",
    borderRadius: 6,
    cursor: "pointer",
  },
};
