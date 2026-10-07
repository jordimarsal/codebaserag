#!/usr/bin/env python3
"""Render the SonarQube scan report into the published quality assets.

Reads the report produced by the homelab scanner (default: ../codebaserag-report.json
relative to the repo root, the path `analyze.sh -r` writes to) and regenerates:

  docs/quality/index.html          self-contained quality page (GitHub Pages)
  docs/quality/codebaserag-report.json  the raw report, published for inspection
  docs/images/badge-*.svg          static README badges

Static output is deliberate: the Sonar server lives on a LAN-only domain, so
dynamic badges would be unreachable for anyone browsing the repo. Re-run this
script after every scan and commit the result. Stdlib only.

Module rows are aggregated from the coverage.py XML written by the default
pytest run (grouped by package: coderag subpackages, core modules, evals).
"""

from __future__ import annotations

import html
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = REPO_ROOT.parent / "codebaserag-report.json"

BRIGHT_GREEN, GREEN, YELLOW, ORANGE, RED, GRAY = (
    "#4c1",
    "#97ca00",
    "#dfb317",
    "#fe7d37",
    "#e05d44",
    "#9f9f9f",
)


def rating_letter(value: float | None) -> str:
    if value is None:
        return "?"
    return {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}[max(1, min(5, round(value)))]


def rating_color(letter: str) -> str:
    return {"A": BRIGHT_GREEN, "B": GREEN, "C": YELLOW, "D": ORANGE, "E": RED, "?": GRAY}[letter]


def coverage_color(pct: float) -> str:
    if pct >= 80:
        return BRIGHT_GREEN
    if pct >= 60:
        return GREEN
    if pct >= 40:
        return YELLOW
    return RED


def badge(label: str, value: str, color: str) -> str:
    label_w = round(len(label) * 6.6) + 12
    value_w = round(len(value) * 6.6) + 12
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{label_w + value_w}" height="20" role="img" aria-label="{html.escape(f"{label}: {value}")}">
  <title>{html.escape(label)}: {html.escape(value)}</title>
  <defs>
    <linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>
    <clipPath id="r"><rect width="{label_w + value_w}" height="20" rx="3" fill="#fff"/></clipPath>
  </defs>
  <g clip-path="url(#r)">
    <rect width="{label_w}" height="20" fill="#555"/>
    <rect x="{label_w}" width="{value_w}" height="20" fill="{color}"/>
    <rect width="{label_w + value_w}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{label_w / 2:.0f}" y="14">{html.escape(label)}</text>
    <text x="{label_w + value_w / 2:.0f}" y="14">{html.escape(value)}</text>
  </g>
</svg>
"""


def module_group(filename: str) -> str:
    """Bucket a coverage.py class filename into a display group."""
    parts = Path(filename).parts
    if parts[:1] == ("evals",):
        return "evals (eval harness)"
    if parts[:2] == ("src", "coderag"):
        rest = parts[2:]
        if len(rest) > 1:
            return f"coderag.{rest[0]}"
        return "coderag core"
    return "other"


def coverage_module_rows(path: Path) -> list[tuple[str, str, str]]:
    """Aggregate the coverage.py XML into per-package (lines, branch) rows."""
    if not path.exists():
        return []
    lines_total: dict[str, int] = defaultdict(int)
    lines_hit: dict[str, int] = defaultdict(int)
    cond_total: dict[str, int] = defaultdict(int)
    cond_hit: dict[str, int] = defaultdict(int)
    for klass in ET.parse(path).getroot().iter("class"):
        group = module_group(klass.get("filename", ""))
        for line in klass.iter("line"):
            lines_total[group] += 1
            if int(line.get("hits", "0")) > 0:
                lines_hit[group] += 1
            if line.get("branch") == "true":
                # condition-coverage="50% (1/2)" → covered=1, total=2
                counts = line.get("condition-coverage", "(0/0)").split("(")[-1].rstrip(")")
                covered, total = counts.split("/")
                cond_total[group] += int(total)
                cond_hit[group] += int(covered)
    rows = []
    for group in sorted(lines_total):
        pct = 100 * lines_hit[group] / lines_total[group]
        branch = f"{100 * cond_hit[group] / cond_total[group]:.1f}%" if cond_total[group] else "—"
        rows.append((group, f"{pct:.1f}%", branch))
    return rows


def render_page(report: dict, rows: list[tuple[str, str, str]]) -> str:
    m = report["measures"]
    gate = report["qualityGate"]
    pct = m.get("coverage")
    cards = [
        ("coverage", f"{pct:.1f}%" if pct is not None else "n/a"),
        (
            "duplication",
            f"{m['duplicated_lines_density']:.1f}%" if "duplicated_lines_density" in m else "n/a",
        ),
        ("issues", str(m.get("violations", "?"))),
        ("security hotspots", str(m.get("security_hotspots", "?"))),
        ("lines of code", str(m.get("ncloc", "?"))),
        ("files", str(m.get("files", "?"))),
    ]
    ratings = [
        ("reliability", rating_letter(m.get("reliability_rating"))),
        ("security", rating_letter(m.get("security_rating"))),
        ("maintainability", rating_letter(m.get("sqale_rating"))),
    ]
    card_html = "\n      ".join(
        f'<div class="card"><span class="value">{html.escape(value)}</span><span class="label">{label}</span></div>'
        for label, value in cards
    )
    rating_html = "\n      ".join(
        f'<div class="card"><span class="value" style="color:{rating_color(letter)}">{letter}</span>'
        f'<span class="label">{name}</span></div>'
        for name, letter in ratings
    )
    row_html = (
        "\n        ".join(
            f"<tr><td>{name}</td><td>{lines}</td><td>{branch}</td></tr>"
            for name, lines, branch in rows
        )
        or '<tr><td colspan="3">run <code>uv run pytest -q tests</code> first</td></tr>'
    )
    gate_ok = gate.get("status") == "OK"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>codebaserag — quality</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{
    margin: 0; min-height: 100vh; padding: 2rem;
    background: #05070a; color: #e6edf3;
    font: 14px/1.6 ui-monospace, "JetBrains Mono", Menlo, monospace;
    max-width: 880px; margin-inline: auto;
  }}
  h1 {{ font-size: 1rem; letter-spacing: .2em; text-transform: uppercase; color: #8b98ab; }}
  h2 {{ font-size: .8rem; letter-spacing: .15em; text-transform: uppercase; color: #8b98ab; margin: 2rem 0 .75rem; }}
  .gate {{ display: inline-block; padding: .5rem .9rem; border: 1px solid {'#3ddc97' if gate_ok else '#e05d44'}; border-radius: 8px; background: #0a0e14; }}
  .gate b {{ color: {'#3ddc97' if gate_ok else '#e05d44'}; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: .75rem; }}
  .card {{ display: grid; gap: .2rem; padding: .9rem; border: 1px solid #1c2530; border-radius: 8px; background: #0a0e14; }}
  .value {{ font-size: 1.4rem; color: #3ddc97; }}
  .label {{ font-size: .7rem; letter-spacing: .1em; text-transform: uppercase; color: #8b98ab; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ text-align: left; padding: .45rem .75rem; border-bottom: 1px solid #1c2530; }}
  th {{ color: #8b98ab; font-weight: normal; font-size: .75rem; text-transform: uppercase; letter-spacing: .1em; }}
  td:not(:first-child) {{ color: #3ddc97; }}
  a {{ color: #3ddc97; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  a.back {{ display: inline-block; margin-top: 2rem; padding: .5rem .9rem; border: 1px solid #1c2530; border-radius: 8px; background: #0a0e14; }}
  pre {{ background: #0a0e14; border: 1px solid #1c2530; border-radius: 8px; padding: .9rem; overflow-x: auto; }}
  code {{ color: #8b98ab; }}
  small {{ color: #4d5a6d; }}
</style>
</head>
<body>
  <h1>codebaserag — quality</h1>
  <p class="gate">quality gate <b>{html.escape(gate.get("name", ""))}</b> · {"passing" if gate_ok else "failing"}</p>

  <h2>Overall (SonarQube)</h2>
  <div class="grid">
      {card_html}
  </div>

  <h2>Ratings</h2>
  <div class="grid">
      {rating_html}
  </div>

  <h2>Coverage by module</h2>
  <table>
    <thead><tr><th>module</th><th>lines</th><th>branch</th></tr></thead>
    <tbody>
        {row_html}
    </tbody>
  </table>

  <h2>Raw data</h2>
  <p>The full scan report is published as <a href="codebaserag-report.json">codebaserag-report.json</a>.</p>
  <pre>~/homelab/sonarqube/analyze.sh -r codebaserag-report.json codebaserag
python3 scripts/sonar-quality.py</pre>

  <a class="back" href="https://github.com/jordimarsal/codebaserag/blob/main/README.md">README</a>
  <p><small>Rendered from the scan of {html.escape(report["generatedAt"])} by the internal SonarQube
  (LAN-only dashboard). Page, badges and JSON are regenerated after each scan.<br>
  The eval-gated core (ingest, retrieval, evals, stores-in-memory) carries the coverage number;
  the live-service adapters (pgvector, qdrant, ollama, litellm) sit low by design — they need a
  running backend and are exercised through contract tests, not unit tests.</small></p>
</body>
</html>
"""


def write_badges(out_dir: Path, report: dict) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    m = report["measures"]
    gate_ok = report["qualityGate"].get("status") == "OK"
    pct = m.get("coverage")
    specs = {
        "quality-gate": (
            "quality gate",
            "passing" if gate_ok else "failing",
            BRIGHT_GREEN if gate_ok else RED,
        ),
        "coverage": (
            "coverage",
            f"{pct:.1f}%" if pct is not None else "n/a",
            coverage_color(pct) if pct is not None else GRAY,
        ),
        "code-smells": (
            "code smells",
            str(m.get("code_smells", "n/a")),
            BRIGHT_GREEN if m.get("code_smells") == 0 else ORANGE,
        ),
    }
    written = []
    for name, (label, value, color) in specs.items():
        path = out_dir / f"badge-{name}.svg"
        path.write_text(badge(label, value, color))
        written.append(path)
    return written


def main() -> int:
    report_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_REPORT
    if not report_path.exists():
        print(f"report not found: {report_path} (run the scanner first)", file=sys.stderr)
        return 1
    report = json.loads(report_path.read_text())

    quality_dir = REPO_ROOT / "docs/quality"
    quality_dir.mkdir(parents=True, exist_ok=True)
    page = quality_dir / "index.html"
    page.write_text(render_page(report, coverage_module_rows(REPO_ROOT / "coverage.xml")))
    shutil.copy(report_path, quality_dir / "codebaserag-report.json")

    for path in write_badges(REPO_ROOT / "docs/images", report):
        print(f"  {path.relative_to(REPO_ROOT)}")
    print(f"  {page.relative_to(REPO_ROOT)}")
    print("  docs/quality/codebaserag-report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
