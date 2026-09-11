// Computes real WCAG contrast ratios for every text/background pair actually
// rendered in relay_ui.jsx and relay_admin_ui.jsx, against the AAA 7:1 floor
// CLAUDE.md's design brief sets as "a concrete floor, not a suggestion."
// Run: node check_contrast.mjs

function luminance(hex) {
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i + 1, i + 3), 16) / 255);
  const lin = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

function contrast(fg, bg) {
  const l1 = luminance(fg), l2 = luminance(bg);
  const [lighter, darker] = l1 > l2 ? [l1, l2] : [l2, l1];
  return (lighter + 0.05) / (darker + 0.05);
}

function report(label, fg, bg, floor = 7.0) {
  const c = contrast(fg, bg);
  const status = c >= floor ? "PASS" : "FAIL";
  console.log(`[${status}] ${label}: ${fg} on ${bg} -> ${c.toFixed(2)}:1 (floor ${floor}:1)`);
  return c >= floor;
}

console.log("=== relay_ui.jsx — light theme ===");
let allPass = true;
const light = {
  ink: "#10151A", inkSoft: "#3F4A47", bg: "#F5F7F4", surface: "#FFFFFF", surface2: "#EAEFE9",
  accent: "#0B4547", accentText: "#0B4547",
  confirmText: "#7A2416", confirmSurface: "#FBEAE5",
  blockText: "#2C333A", blockSurface: "#E7EAEC",
  errorText: "#5E3C0E", errorSurface: "#F5ECDD",
};
allPass &= report("body text", light.ink, light.bg);
allPass &= report("context chip / ghost button", light.inkSoft, light.bg);
allPass &= report("ghost button active", light.accentText, light.surface2);
allPass &= report("stage title (calm)", light.ink, light.surface);
allPass &= report("stage caption (calm panel)", light.inkSoft, light.surface);
allPass &= report("stage caption (confirm panel)", light.inkSoft, light.confirmSurface);
allPass &= report("stage caption (block panel)", light.inkSoft, light.blockSurface);
allPass &= report("stage caption (error panel)", light.inkSoft, light.errorSurface);
allPass &= report("readout text, acting state (accent, not accent-text!)", light.accent, light.surface2);
allPass &= report("stage title/readout (confirm)", light.confirmText, light.confirmSurface);
allPass &= report("stage title/readout (block)", light.blockText, light.blockSurface);
allPass &= report("stage title/readout (error)", light.errorText, light.errorSurface);
allPass &= report("toast (inverted)", light.bg, light.ink);

console.log("\n=== relay_ui.jsx — dark theme ===");
const dark = {
  ink: "#EEF3EF", inkSoft: "#AFC0B8", bg: "#0B1613", surface: "#12201C", surface2: "#17281F",
  accent: "#8CDCD6", accentText: "#8CDCD6",
  confirmText: "#FF9E85", confirmSurface: "#2A1710",
  blockText: "#C9D0D5", blockSurface: "#1C2529",
  errorText: "#F0C67C", errorSurface: "#241D0F",
};
allPass &= report("body text", dark.ink, dark.bg);
allPass &= report("context chip / ghost button", dark.inkSoft, dark.bg);
allPass &= report("ghost button active", dark.accentText, dark.surface2);
allPass &= report("stage title (calm)", dark.ink, dark.surface);
allPass &= report("stage caption (calm panel)", dark.inkSoft, dark.surface);
allPass &= report("stage caption (confirm panel)", dark.inkSoft, dark.confirmSurface);
allPass &= report("stage caption (block panel)", dark.inkSoft, dark.blockSurface);
allPass &= report("stage caption (error panel)", dark.inkSoft, dark.errorSurface);
allPass &= report("readout text, acting state (accent, not accent-text!)", dark.accent, dark.surface2);
allPass &= report("stage title/readout (confirm)", dark.confirmText, dark.confirmSurface);
allPass &= report("stage title/readout (block)", dark.blockText, dark.blockSurface);
allPass &= report("stage title/readout (error)", dark.errorText, dark.errorSurface);
allPass &= report("toast (inverted)", dark.bg, dark.ink);

console.log("\n=== relay_admin_ui.jsx — light theme (single-theme design) ===");
const admin = {
  ink: "#131C24", inkSoft: "#47535E", bg: "#F1F4F7", surface: "#FFFFFF", surface2: "#E4E9EF",
  confirmText: "#1D4160", confirmSurface: "#E7EFF6",
  blockText: "#22262B", blockSurface: "#E7E9EB",
  allowText: "#274A31", allowSurface: "#E7F0E9",
  chipMonoText: "#3A434C",
};
allPass &= report("body text", admin.ink, admin.bg);
allPass &= report("kicker / subtitle text", admin.inkSoft, admin.bg);
allPass &= report("headings on surface", admin.ink, admin.surface);
allPass &= report("chip phrase (confirm chip)", admin.ink, admin.confirmSurface);
allPass &= report("chip phrase (block chip)", admin.ink, admin.blockSurface);
allPass &= report("chip pattern mono (confirm chip)", admin.chipMonoText, admin.confirmSurface);
allPass &= report("chip pattern mono (block chip)", admin.chipMonoText, admin.blockSurface);
allPass &= report("tester result (allow)", admin.allowText, admin.allowSurface);
allPass &= report("tester result (confirm)", admin.confirmText, admin.confirmSurface);
allPass &= report("tester result (block)", admin.blockText, admin.blockSurface);

console.log(`\n${allPass ? "ALL PAIRS MEET AAA 7:1" : "SOME PAIRS FAIL THE AAA 7:1 FLOOR — see FAIL lines above"}`);
