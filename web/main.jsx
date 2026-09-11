import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import RelayRuntimeUI from "./relay_ui.jsx";
import RelayAdminUI from "./relay_admin_ui.jsx";
import BuildChecklist from "./build_checklist.jsx";

// Dev-only preview harness — lets both delivered UIs be viewed in a real
// browser during the build. Not part of either product surface.
function Preview() {
  const [tab, setTab] = useState("relay");
  const tabBtn = (key, label) => (
    <button
      onClick={() => setTab(key)}
      style={{
        font: "600 14px system-ui, sans-serif",
        padding: "8px 16px",
        border: "none",
        borderBottom: tab === key ? "3px solid #1B6B6E" : "3px solid transparent",
        background: "#1c1c1c",
        color: tab === key ? "#fff" : "#9aa0a6",
        cursor: "pointer",
      }}
    >
      {label}
    </button>
  );

  return (
    <div>
      <nav style={{ display: "flex", gap: 4, background: "#1c1c1c", position: "sticky", top: 0, zIndex: 10 }}>
        {tabBtn("relay", "Relay — end-user UI (Phase 4)")}
        {tabBtn("admin", "Guardrail admin (Phase 5)")}
        {tabBtn("checklist", "Build checklist (dev tracker)")}
      </nav>
      {tab === "relay" && <RelayRuntimeUI />}
      {tab === "admin" && <RelayAdminUI />}
      {tab === "checklist" && <BuildChecklist />}
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <Preview />
  </StrictMode>
);
