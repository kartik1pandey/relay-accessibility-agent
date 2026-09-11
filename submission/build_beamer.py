"""
build_beamer.py — generates a LaTeX Beamer deck (Relay_Pitch_Deck.tex)
from the same slides_content.py used by build_pptx.py, so the .tex, .pptx
and .pdf pitch decks can't drift out of sync with each other.

Run: python build_beamer.py
Then compile (from this directory): xelatex Relay_Pitch_Deck.tex
"""

import os
import re

from slides_content import SLIDES

OUT_PATH = os.path.join(os.path.dirname(__file__), "Relay_Pitch_Deck_LaTeX.tex")

_ESCAPE_MAP = {
    "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
    "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}
_ESCAPE_RE = re.compile("|".join(re.escape(k) for k in _ESCAPE_MAP))


def esc(text: str) -> str:
    # Escape LaTeX specials first, then reintroduce the typographic
    # replacements (smart quotes, en/em dash, arrow) as real LaTeX/unicode
    # output — done after escaping so none of these get mangled by it.
    text = _ESCAPE_RE.sub(lambda m: _ESCAPE_MAP[m.group(0)], text)
    text = text.replace("“", "``").replace("”", "''")
    text = text.replace("—", "---")
    text = text.replace("→", r"$\rightarrow$")
    return text


PREAMBLE = r"""
\PassOptionsToPackage{table}{xcolor}
\documentclass[aspectratio=169]{beamer}
\usepackage{fontspec}
\setmainfont{Segoe UI}
\usepackage{tabularx}
\usepackage{array}
\usepackage{tikz}
\newcolumntype{Y}{>{\raggedright\arraybackslash}X}

\definecolor{bg}{HTML}{F5F7F4}
\definecolor{ink}{HTML}{10151A}
\definecolor{inksoft}{HTML}{3F4A47}
\definecolor{accent}{HTML}{1B6B6E}
\definecolor{accenttext}{HTML}{0B4547}
\definecolor{linecol}{HTML}{D8DED8}
\definecolor{darkbg}{HTML}{10151A}
\definecolor{darkfg}{HTML}{F5F7F4}
\definecolor{darkmuted}{HTML}{9FB3AC}
\definecolor{tablehi}{HTML}{EAEFE9}

\setbeamertemplate{navigation symbols}{}
\setbeamertemplate{footline}{}
\setbeamercolor{background canvas}{bg=bg}
\setbeamercolor{normal text}{fg=ink, bg=bg}
\setbeamerfont{frametitle}{size=\LARGE, series=\bfseries}
\setbeamercolor{frametitle}{fg=ink, bg=bg}
\setbeamertemplate{frametitle}{
  \vspace{6pt}
  {\color{accenttext}\bfseries\small \MakeUppercase{\insertframetitle}}
}

\newcommand{\eyebrowtitle}[2]{
  \vspace{4pt}
  {\color{accenttext}\bfseries\small \MakeUppercase{#1}}\\[2pt]
  {\color{linecol}\rule{\textwidth}{0.6pt}}\\[10pt]
  {\color{ink}\LARGE\bfseries #2}\par\vspace{10pt}
}

% A tighter variant for content-heavy slides (the 7-step architecture
% diagram overflowed the frame with the standard spacing above — found by
% actually compiling and looking at the rendered page, not assumed).
\newcommand{\eyebrowtitlecompact}[2]{
  {\color{accenttext}\bfseries\small \MakeUppercase{#1}}\\[1pt]
  {\color{linecol}\rule{\textwidth}{0.6pt}}\\[6pt]
  {\color{ink}\Large\bfseries #2}\par\vspace{4pt}
}

% Beamer's background-canvas color must be set before \begin{frame} to
% affect that frame; setting it inside the frame body is too late (found
% by actually compiling: the title slide rendered with a light background
% and near-invisible light-on-light text). A full-page TikZ overlay
% painted first thing inside the frame is robust regardless of timing.
\newcommand{\darkbgrect}{%
\begin{tikzpicture}[remember picture, overlay]
\fill[darkbg] (current page.south west) rectangle (current page.north east);
\end{tikzpicture}%
}

\begin{document}
"""

POSTAMBLE = r"""
\end{document}
"""


def render_title(s: dict) -> str:
    return rf"""
\begin{{frame}}[plain]
\darkbgrect
\vspace{{2.2cm}}
{{\color{{darkfg}}\fontsize{{60}}{{60}}\selectfont\bfseries {esc(s['title'])}}}\\[14pt]
{{\color{{darkmuted}}\Large {esc(s['subtitle'])}}}
\vfill
{{\color{{accent}}\bfseries {esc(s['footer'])}}}
\end{{frame}}
"""


def render_content(s: dict) -> str:
    bullets = "\n".join(rf"\item {esc(b)}" for b in s["bullets"])
    return rf"""
\begin{{frame}}{{}}
\eyebrowtitle{{{esc(s['eyebrow'])}}}{{{esc(s['title'])}}}
\vspace{{6pt}}
{{\color{{inksoft}}
\begin{{itemize}}
\setlength{{\itemsep}}{{10pt}}
{bullets}
\end{{itemize}}
}}
\end{{frame}}
"""


def render_diagram(s: dict) -> str:
    lines = []
    for i, step in enumerate(s["steps"]):
        is_gate = "Guardrail" in step
        color = "accenttext" if is_gate else "ink"
        weight = r"\bfseries" if is_gate else ""
        lines.append(rf"\centerline{{\color{{{color}}}\footnotesize {weight} {esc(step)}}}")
        if i < len(s["steps"]) - 1:
            lines.append(r"\vspace{-2pt}\centerline{\color{linecol}\footnotesize$\downarrow$}\vspace{-2pt}")
    body = "\n".join(lines)
    return rf"""
\begin{{frame}}{{}}
\eyebrowtitlecompact{{{esc(s['eyebrow'])}}}{{{esc(s['title'])}}}
{body}
\end{{frame}}
"""


def render_table(s: dict) -> str:
    header = " & ".join(rf"\textbf{{\textcolor{{darkfg}}{{{esc(c)}}}}}" for c in s["columns"])
    rows_tex = []
    for row in s["rows"]:
        is_relay = row[0] == "Relay"
        if is_relay:
            cells = " & ".join(rf"\textbf{{{esc(v)}}}" for v in row)
            rows_tex.append(rf"\rowcolor{{tablehi}} {cells} \\")
        else:
            cells = " & ".join(esc(v) for v in row)
            rows_tex.append(rf"{cells} \\")
    rows_body = "\n".join(rows_tex)
    return rf"""
\begin{{frame}}{{}}
\eyebrowtitle{{{esc(s['eyebrow'])}}}{{{esc(s['title'])}}}
\footnotesize
\renewcommand{{\arraystretch}}{{1.15}}
\begin{{tabularx}}{{\textwidth}}{{@{{}} >{{\raggedright\arraybackslash}}p{{2.1cm}} Y >{{\raggedright\arraybackslash}}p{{3.2cm}} @{{}}}}
\rowcolor{{ink}} {header} \\
{rows_body}
\end{{tabularx}}
\renewcommand{{\arraystretch}}{{1}}
\vspace{{6pt}}
{{\tiny\color{{inksoft}} {esc(s.get('note', ''))}}}
\end{{frame}}
"""


def render_stats(s: dict) -> str:
    cols = " ".join(
        rf"\begin{{minipage}}[t]{{0.48\textwidth}}\centering "
        rf"{{\color{{accenttext}}\fontsize{{40}}{{40}}\selectfont\bfseries {esc(st['value'])}}}\\[10pt]"
        rf"{{\color{{inksoft}}\large {esc(st['label'])}}}"
        rf"\end{{minipage}}"
        for st in s["stats"]
    )
    return rf"""
\begin{{frame}}{{}}
\eyebrowtitle{{{esc(s['eyebrow'])}}}{{{esc(s['title'])}}}
\vspace{{18pt}}
\centerline{{{cols}}}
\vspace{{22pt}}
\centerline{{\begin{{minipage}}{{0.85\textwidth}}\centering\color{{inksoft}} {esc(s['note'])}\end{{minipage}}}}
\end{{frame}}
"""


def render_closing(s: dict) -> str:
    lines = "\n\\vspace{6pt}\n".join(
        rf"\centerline{{\color{{darkmuted}}\large {esc(l)}}}" for l in s["lines"]
    )
    return rf"""
\begin{{frame}}[plain]
\darkbgrect
\vspace{{2.6cm}}
\centerline{{\color{{darkfg}}\fontsize{{54}}{{54}}\selectfont\bfseries {esc(s['title'])}}}
\vspace{{22pt}}
{lines}
\end{{frame}}
"""


RENDERERS = {
    "title": render_title,
    "content": render_content,
    "diagram": render_diagram,
    "table": render_table,
    "stats": render_stats,
    "closing": render_closing,
}


def main():
    body = "".join(RENDERERS[s["kind"]](s) for s in SLIDES)
    tex = PREAMBLE + body + POSTAMBLE
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(tex)
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
