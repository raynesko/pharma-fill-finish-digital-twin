"""Five-slide summary (T7.2.1), built from the results files only.

Figures are regenerated from ``reports/results_baseline.json`` and ``reports/results_final.json``
on every build; every number on a slide is read from those files. Output:
``docs/portfolio/slides.html`` (source) and ``docs/portfolio/slides.pdf`` (printed by headless
Chrome or Edge, whichever is installed).

    python -m ffdt.experiments.slides
"""

from __future__ import annotations

import html
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import plotly.graph_objects as go

from ffdt import api, viz

ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "reports"
FIGS = REPORTS / "figures"
OUT = ROOT / "docs" / "portfolio"
HTML, PDF = OUT / "slides.html", OUT / "slides.pdf"
BLUE, MUTED, INK, SURFACE, GRID = "#2a78d6", "#52514e", "#1f1e1c", "#fcfcfb", "#e6e4df"
NOT_DETECTED = "#a3a19b"  # muted ink for effects whose CI includes zero, always with a label
FONT = "Segoe UI, Helvetica, Arial, sans-serif"


def load() -> tuple[dict, dict]:
    b = json.loads((REPORTS / "results_baseline.json").read_text(encoding="utf-8"))
    d = json.loads((REPORTS / "results_final.json").read_text(encoding="utf-8"))
    return b, d


def _style(fig: go.Figure, title: str, height: int) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=17, color=INK)),
        height=height,
        width=600,
        margin=dict(l=8, r=24, t=48, b=48),
        font=dict(family=FONT, size=13, color=MUTED),
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        showlegend=False,
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    fig.update_yaxes(showgrid=False, automargin=True, tickfont=dict(color=INK))
    return fig


def pareto_fig(b: dict, top: int = 6) -> go.Figure:
    """Largest losses of the filler's scheduled time (single series: one hue, no legend)."""
    rows = sorted(b["loss_pareto"], key=lambda r: r["mean"], reverse=True)[:top][::-1]
    x = [100 * r["mean"] for r in rows]
    fig = go.Figure(
        go.Bar(
            x=x,
            y=[viz.LOSS_LABELS.get(r["category"], r["category"]) for r in rows],
            orientation="h",
            marker=dict(color=BLUE, line=dict(width=2, color=SURFACE)),
            error_x=dict(
                type="data",
                symmetric=False,
                array=[100 * (r["ci_high"] - r["mean"]) for r in rows],
                arrayminus=[100 * (r["mean"] - r["ci_low"]) for r in rows],
                color=MUTED,
                thickness=1.5,
                width=3,
            ),
        )
    )
    for r, v in zip(rows, x, strict=True):
        fig.add_annotation(
            x=100 * r["ci_high"],
            y=viz.LOSS_LABELS.get(r["category"], r["category"]),
            text=f"{v:.1f}%",
            showarrow=False,
            xanchor="left",
            xshift=6,
            font=dict(color=INK, size=13),
        )
    _style(fig, "Losses, % of the filler's scheduled time (95% CI)", 320)
    fig.update_layout(bargap=0.35)
    fig.update_xaxes(ticksuffix="%", range=[0, max(x) * 1.3])
    return fig


def forest_fig(d: dict) -> go.Figure:
    """Main-set scenario effects with paired 95% CIs; grey = CI includes zero (labeled)."""
    rows = sorted((s for s in d["scenarios"] if s["set"] == "main"), key=lambda s: s["pct_diff"])
    det = [s["pct_ci_low"] > 0 or s["pct_ci_high"] < 0 for s in rows]
    names = [s["plain_name"].replace(" (SMED, ASSUMPTION)", "") for s in rows]
    names = [n if ok else f"{n} (no detectable change)" for n, ok in zip(names, det, strict=True)]
    fig = go.Figure(
        go.Scatter(
            x=[100 * s["pct_diff"] for s in rows],
            y=names,
            mode="markers",
            marker=dict(
                size=10,
                color=[BLUE if ok else NOT_DETECTED for ok in det],
                line=dict(width=2, color=SURFACE),
            ),
            error_x=dict(
                type="data",
                symmetric=False,
                array=[100 * (s["pct_ci_high"] - s["pct_diff"]) for s in rows],
                arrayminus=[100 * (s["pct_diff"] - s["pct_ci_low"]) for s in rows],
                color=MUTED,
                thickness=2,
                width=0,
            ),
        )
    )
    _style(fig, "Change in good vials per scheduled hour vs baseline", 440)
    fig.update_layout(margin=dict(t=72))
    fig.add_vline(x=0, line=dict(color=MUTED, width=1))
    fig.add_vline(x=3, line=dict(color=MUTED, width=1, dash="dash"))
    fig.add_annotation(
        x=3,
        y=1,
        yref="paper",
        yanchor="bottom",
        text="+3% practical threshold (TARGET)",
        showarrow=False,
        xanchor="left",
        font=dict(size=11, color=MUTED),
    )
    fig.update_xaxes(ticksuffix="%", title="paired 95% CI, 30 replications")
    return fig


def figures(b: dict, d: dict) -> dict[str, Path]:
    FIGS.mkdir(parents=True, exist_ok=True)
    out = {"pareto": FIGS / "slide_loss_pareto.png", "forest": FIGS / "slide_scenario_forest.png"}
    pareto_fig(b).write_image(out["pareto"], scale=2)
    forest_fig(d).write_image(out["forest"], scale=2)
    return out


def _pct(x: float, signed: bool = True) -> str:
    return f"{100 * x:+.1f}%" if signed else f"{100 * x:.1f}%"


def _err(x: float) -> str:
    s = f"{100 * x:+.1f}%"
    return "0.0%" if s in ("-0.0%", "+0.0%") else s


def flow_svg() -> str:
    """Line flow diagram: stations from the frozen baseline config."""
    names = {
        "washer": ("Washer",),
        "tunnel": ("Depyrogenation", "tunnel"),
        "filler": ("Filler /", "stopperer"),
        "capper": ("Capper",),
        "avi": ("Automated", "inspection (AVI)"),
        "labeler": ("Labeler",),
        "cartoner": ("Cartoner",),
    }
    sts = api.baseline().stations
    w, gap, x0, y = 132, 26, 6, 40
    parts = []
    for i, s in enumerate(sts):
        x = x0 + i * (w + gap)
        hot = s.name == "filler"
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="64" rx="8" '
            f'fill="{"#e8f0fb" if hot else "#ffffff"}" stroke="{BLUE if hot else MUTED}" '
            f'stroke-width="{2 if hot else 1}"/>'
        )
        lines = names[s.name]
        top = y + (24 if len(lines) == 1 else 18)
        for j, ln in enumerate(lines):
            parts.append(
                f'<text x="{x + w / 2}" y="{top + 15 * j}" class="st">{html.escape(ln)}</text>'
            )
        parts.append(
            f'<text x="{x + w / 2}" y="{y + 54}" class="rt">{s.rate_vpm:.0f} vials/min</text>'
        )
        if i:
            parts.append(
                f'<line x1="{x - gap + 2}" y1="{y + 32}" x2="{x - 4}" y2="{y + 32}" '
                f'stroke="{MUTED}" stroke-width="1.5" marker-end="url(#a)"/>'
            )
    avi_x = x0 + 4 * (w + gap) + w / 2
    parts.append(
        f'<line x1="{avi_x}" y1="{y + 66}" x2="{avi_x}" y2="{y + 104}" stroke="{MUTED}" '
        f'stroke-width="1.5" stroke-dasharray="4 3" marker-end="url(#a)"/>'
        f'<text x="{avi_x}" y="{y + 122}" class="rt">rejects to manual re-inspection</text>'
        f'<text x="{x0 + 6 * (w + gap) + w / 2}" y="{y + 92}" class="rt">then QA batch release</text>'
    )
    width = x0 + len(sts) * (w + gap)
    return (
        f'<svg viewBox="0 0 {width} 175" width="100%" role="img" aria-label="Line flow">'
        '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker>'
        "</defs>" + "".join(parts) + "</svg>"
    )


CSS = f"""
@page {{ size: 1280px 720px; margin: 0; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: {FONT}; color: {INK}; background: {SURFACE}; }}
.slide {{ width: 1280px; height: 720px; padding: 48px 64px 40px; position: relative;
  page-break-after: always; break-after: page; overflow: hidden; background: {SURFACE}; }}
.kicker {{ font-size: 14px; letter-spacing: .08em; text-transform: uppercase; color: {BLUE};
  font-weight: 600; margin-bottom: 8px; }}
h1 {{ font-size: 32px; line-height: 1.2; margin: 0 0 24px; font-weight: 650; max-width: 1120px; }}
p, li {{ font-size: 19px; line-height: 1.45; color: #3b3a37; }}
ul {{ padding-left: 22px; margin: 0; }} li {{ margin-bottom: 8px; }}
.cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 40px; }}
.cols3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }}
.tile {{ border: 1px solid {GRID}; border-radius: 10px; padding: 18px 20px; background: #fff; }}
.big {{ font-size: 40px; font-weight: 650; color: {INK}; line-height: 1.1; }}
.lab {{ font-size: 15px; color: {MUTED}; margin-top: 6px; line-height: 1.35; }}
.foot {{ position: absolute; left: 64px; right: 64px; bottom: 18px; font-size: 12px;
  color: {MUTED}; display: flex; justify-content: space-between; }}
img {{ width: 100%; display: block; }}
table {{ border-collapse: collapse; width: 100%; font-size: 15px; }}
td, th {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid {GRID}; }}
th {{ color: {MUTED}; font-weight: 600; }}
svg .st {{ font: 600 13px {FONT}; fill: {INK}; text-anchor: middle; }}
svg .rt {{ font: 12px {FONT}; fill: {MUTED}; text-anchor: middle; }}
"""


def _slide(n: int, kicker: str, title: str, body: str) -> str:
    return (
        f'<section class="slide"><div class="kicker">{kicker}</div><h1>{title}</h1>{body}'
        f'<div class="foot"><span>{viz.SIM_TAG} Numbers from reports/results_final.json.</span>'
        f"<span>{n} / 5</span></div></section>"
    )


def build_html(b: dict, d: dict, figs: dict[str, Path]) -> str:
    base, bn, ver, sens = d["baseline"], d["bottleneck"], d["verification"], d["sensitivity"]
    sc = {s["scenario"]: s for s in d["scenarios"]}
    m50, m25, avi = sc["sc04_changeover_m50"], sc["sc04_changeover_m25"], sc["sc01_avi_plus1"]
    op, bx2 = sc["sc03_operator_plus1"], sc["sc02_batch_x2"]
    oee = base["line_oee"]
    rel = lambda p: os.path.relpath(p, OUT).replace(os.sep, "/")  # noqa: E731

    def ci(s: dict) -> str:
        return f"95% CI {_pct(s['pct_ci_low'])} to {_pct(s['pct_ci_high'])}"

    s1 = _slide(
        1,
        "Context and question",
        "Four common ideas compete to raise output on a sterile vial fill-finish line",
        '<div class="cols"><div><p>Aseptic fill-finish lines are capital-intensive and '
        "tightly scheduled, so plants look for more good vials from the same line. Typical "
        "proposals are judged with spreadsheet averages that ignore breakdowns, queues and "
        "blocking.</p><p><b>Decision:</b> which lever adds the most good vials per scheduled "
        "hour, and which station limits the line?</p></div>"
        '<div class="cols" style="gap:16px">'
        '<div class="tile"><div class="big" style="font-size:24px">Inspection</div>'
        '<div class="lab">add a second automated inspection (AVI) machine</div></div>'
        '<div class="tile"><div class="big" style="font-size:24px">Batch size</div>'
        '<div class="lab">halve batches, or merge identical neighbours</div></div>'
        '<div class="tile"><div class="big" style="font-size:24px">Staffing</div>'
        '<div class="lab">operators, mechanics, inspectors, each &plusmn;1</div></div>'
        '<div class="tile"><div class="big" style="font-size:24px">Changeover</div>'
        '<div class="lab">SMED: every changeover 25% or 50% shorter (ASSUMPTION)</div></div>'
        "</div></div>"
        f"<p style='margin-top:28px'>Scenarios and decision rules were <b>pre-registered</b> "
        f"before any run; a change counts as meaningful at {d['practical_threshold'][8:]}.</p>",
    )
    s2 = _slide(
        2,
        "Line and model",
        "A discrete-event model of one week on a 7-station line, with randomness where "
        "the plant has it",
        flow_svg() + '<div class="cols" style="margin-top:8px"><div><p><b>Random:</b> '
        "breakdowns (repair needs a mechanic), minor stops, defects and rejects, QA review "
        "time.</p><p><b>Planned:</b> 6 batches, 2 products &times; 2 vial formats, 2 shifts "
        "&times; 5 days; three changeover types that need line operators.</p></div><div>"
        "<p><b>GMP touchpoints modeled:</b> line clearance inside every changeover, "
        "manual re-inspection of AVI rejects, QA batch release (adds lead time, not an "
        "equipment loss).</p><p><b>Out of scope:</b> lyophilization, sterility-test holds, "
        "deviations, absenteeism. Parameters are public benchmarks or judgment, not plant "
        "data.</p></div></div>",
    )
    checks = "".join(
        f"<tr><td>{html.escape(c['name'])}</td><td>{c['theory']:.4g}</td>"
        f"<td>{c['simulated']:.4g}</td><td>{_err(c['rel_error'])}</td>"
        f"<td>{'yes' if c['theory_in_ci'] else 'no'}</td></tr>"
        for c in ver["analytic_checks"]
    )
    s3 = _slide(
        3,
        "Why trust it",
        "Verified against queueing theory; the constraint holds when each uncertain "
        "parameter is moved on its own",
        '<div class="cols"><div><div class="cols" style="gap:16px">'
        f'<div class="tile"><div class="big">{ver["automated_tests"]}</div>'
        '<div class="lab">automated tests: vial conservation, time accounting, '
        "determinism, random-stream isolation</div></div>"
        f'<div class="tile"><div class="big">{sens["n_perturbations"]}</div>'
        '<div class="lab">one-at-a-time perturbations: the constraint never moved, and '
        "changeover reduction beat a second AVI in every speed case</div></div></div>"
        "<p style='margin-top:20px'><b>Two model errors</b> were caught by these checks "
        "during the study, fixed, documented as dated errata, and every run repeated.</p>"
        "<p><b>Honest limit:</b> validation is face validity only. No plant data; "
        "a practitioner review is pending.</p></div>"
        "<div><table><tr><th>Analytic check</th><th>Theory</th><th>Simulated</th>"
        f"<th>Error</th><th>In 95% CI</th></tr>{checks}</table>"
        f"<p style='font-size:16px;margin-top:16px'>Common random numbers made the "
        f"scenario CIs {d['crn_ci_narrowing_x']['min']:.1f}&ndash;"
        f"{d['crn_ci_narrowing_x']['max']:.1f}&times; narrower than independent runs.</p>"
        "</div></div>",
    )
    co = next(r for r in b["loss_pareto"] if r["category"] == "CHANGEOVER")
    s4 = _slide(
        4,
        "Results",
        f"The filler is the constraint; halving changeovers adds {_pct(m50['pct_diff'])} "
        "output, a second inspection machine nothing detectable",
        '<div class="cols" style="gap:24px">'
        f'<div><img src="{rel(figs["pareto"])}" alt="Loss Pareto">'
        f"<p style='font-size:16px'>Baseline line OEE <b>{_pct(oee['mean'], False)}</b> "
        f"(95% CI {_pct(oee['ci_low'], False)}&ndash;{_pct(oee['ci_high'], False)}, "
        f"{base['n_reps']} replications). Changeover is the largest loss at "
        f"{_pct(co['mean'], False)} of scheduled time. The filler was named the constraint "
        f"by all {bn['methods_agreeing_of_4']} methods and was the sole bottleneck "
        f"{_pct(bn['constraint_sole_share'], False)} of the time.</p></div>"
        f'<div><img src="{rel(figs["forest"])}" alt="Scenario effects"></div></div>',
    )
    s5 = _slide(
        5,
        "Recommendation and next steps",
        "Start with SMED on the whole line; skip the second inspection machine; "
        "calibrate before investing",
        '<div class="cols3">'
        f'<div class="tile"><div class="big">{_pct(m50["pct_diff"])}</div><div class="lab">'
        f"<b>1. Changeovers &minus;50%</b> (SMED, all stations). {ci(m50)}. Even &minus;25% "
        f"gives {_pct(m25['pct_diff'])}.</div></div>"
        f'<div class="tile"><div class="big">{_pct(op["pct_diff"])}</div><div class="lab">'
        f"<b>2. One more line operator.</b> {ci(op)}. Staff waits were at the cartoner, "
        "not the filler.</div></div>"
        f'<div class="tile"><div class="big">{_pct(avi["pct_diff"])}</div><div class="lab">'
        f"<b>Not: a second AVI.</b> {ci(avi)}. Capacity at a non-constraint buys no "
        "output.</div></div></div>"
        '<div class="cols" style="margin-top:28px"><div><p><b>What would change the '
        "answer:</b> a different product mix or schedule; filler speed outside the &plusmn;20% "
        "tested; SMED savings well below 25% (the reduction levels are assumptions, not measured). "
        f"Merging identical batches also helps ({_pct(bx2['pct_diff'])}) where the "
        "schedule allows.</p></div><div><p><b>With real data:</b> fit failure and repair "
        "times per station from the historian or MES, time a real changeover to size "
        "SMED, calibrate to measured OEE and check a holdout week. A what-if app lets a "
        "plant team try their own levers.</p></div></div>",
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        "<title>Fill-Finish Digital Twin</title>"
        f"<style>{CSS}</style></head><body>{s1}{s2}{s3}{s4}{s5}</body></html>"
    )


SCRIPT = OUT / "slides_script.md"


def script(b: dict, d: dict) -> str:
    """Speaker notes for a 2-minute run-through; numbers from the results files."""
    sc = {s["scenario"]: s for s in d["scenarios"]}
    m50, avi, op = sc["sc04_changeover_m50"], sc["sc01_avi_plus1"], sc["sc03_operator_plus1"]
    oee, bn = d["baseline"]["line_oee"], d["bottleneck"]
    co = next(r for r in b["loss_pareto"] if r["category"] == "CHANGEOVER")
    parts = [
        "Sterile fill-finish lines are expensive, so plants want more good vials from the "
        "same line. I compared four common ideas: a second inspection machine, batch size, "
        "staffing, and faster changeovers, and asked which station really limits the line.",
        "I built a discrete-event simulation of a seven-station vial line for one week, "
        "with random breakdowns, minor stops, rejects, shared staff and QA release. The "
        "parameters come from public benchmarks, not plant data, and I wrote down the "
        "scenarios and decision rules before running anything.",
        f"To trust it, I checked it against queueing theory and availability formulas, and "
        f"the theory fell inside every confidence interval. I also moved each uncertain "
        f"parameter up and down on its own, {d['sensitivity']['n_perturbations']} runs, and "
        "the filler stayed the constraint every time. My tests caught two model bugs along "
        "the way, which I fixed and documented.",
        f"The baseline line OEE is {100 * oee['mean']:.0f} percent. Changeovers eat "
        f"{100 * co['mean']:.0f} percent of the filler's scheduled time, and the filler is the "
        f"constraint by all {bn['methods_agreeing_of_4']} methods. Cutting changeovers in half "
        f"adds about {100 * m50['pct_diff']:.0f} percent more good vials. A second inspection "
        f"machine adds {100 * avi['pct_diff']:.1f} percent, which is not statistically "
        "different from zero, because inspection is not the constraint.",
        f"So I would start with a SMED project across the whole line, then add one line "
        f"operator, about {100 * op['pct_diff']:.1f} percent more, and skip the inspection "
        "machine. With real data, I would fit breakdown and repair times from the historian "
        "and time a real changeover before committing money.",
    ]
    words = sum(len(t.split()) for t in parts)
    head = [
        "# Five-slide summary: speaking script (T7.2.1)",
        "",
        f"Generated by `python -m ffdt.experiments.slides`; do not edit by hand. {words} words, "
        f"about {words / 150 * 60:.0f} s at 150 words per minute (target: 2 minutes spoken). "
        "Simulated, benchmark-parameterized; not plant data. Slides: "
        "[`slides.pdf`](slides.pdf) (source [`slides.html`](slides.html)).",
        "",
    ]
    body = [f"**Slide {i}.** {t}\n" for i, t in enumerate(parts, 1)]
    return "\n".join(head + body)


def find_browser() -> str | None:
    cands = [
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    return next((c for c in cands if c and Path(c).exists()), None)


def print_pdf(src: Path, dst: Path) -> None:
    exe = find_browser()
    if exe is None:
        raise RuntimeError("No Chrome or Edge found to print the PDF.")
    with tempfile.TemporaryDirectory() as prof:
        subprocess.run(
            [
                exe,
                "--headless=new",
                "--disable-gpu",
                f"--user-data-dir={prof}",
                "--no-pdf-header-footer",
                f"--print-to-pdf={dst}",
                src.resolve().as_uri(),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )


def write(pdf: bool = True) -> Path:
    b, d = load()
    figs = figures(b, d)
    HTML.write_text(build_html(b, d, figs), encoding="utf-8")
    SCRIPT.write_text(script(b, d), encoding="utf-8")
    if pdf:
        print_pdf(HTML, PDF)
    return HTML


if __name__ == "__main__":
    write()
    print(f"wrote {HTML.relative_to(ROOT)} and {PDF.relative_to(ROOT)}")
