"""Self-contained HTML reports. No external assets."""

from __future__ import annotations

import html


def render_report(run: dict) -> str:
    mean = run["mean"]
    rows = sorted(run["trajectories"], key=lambda row: (row["score"], row["id"]))
    failed = [row for row in rows if row["score"] < 1]
    body = [
        _header(run),
        _summary(run),
        _scorer_table(run.get("by_scorer", {})),
    ]
    if not failed:
        body.append("<p class='note'>Every trajectory in this run scored 1.0000.</p>")
    body.append(_trajectory_table(rows, failures_first=True))
    if failed:
        body.append("<h2>Failures</h2>")
        body.extend(_failure_block(row) for row in failed)
    return _page(f"Trajectory eval — {run.get('agent', 'run')}", "\n".join(body))


def render_diff_report(diff: dict, *, baseline_label: str = "baseline", current_label: str = "current") -> str:
    drop = diff["mean_drop"]
    parts = [
        "<header>",
        "<p class='kicker'>trajectory-eval-harness · synthetic data · run diff</p>",
        f"<h1>{html.escape(baseline_label)} → {html.escape(current_label)}</h1>",
        f"<p class='mean'>{drop:+.4f}</p>",
        (
            f"<p class='sub'>Suite mean {diff['baseline_mean']:.4f} → {diff['current_mean']:.4f}. "
            f"{diff['n_regressed']} regressed, {diff['n_improved']} improved, "
            f"{diff['n_unchanged']} unchanged. "
            "Negative drop is an improvement. The sign on the figure above is baseline minus current.</p>"
        ),
        "</header>",
    ]
    if diff.get("warnings"):
        items = "".join(f"<li>{html.escape(item)}</li>" for item in diff["warnings"])
        parts.append(f"<ul class='warn'>{items}</ul>")
    parts.append("<h2>Scorer movement</h2>")
    parts.append(_kv_table(diff.get("by_scorer_drop", {}), "Scorer", "Drop (baseline − current)"))
    parts.append("<h2>Regressed</h2>")
    parts.append(_diff_table(diff.get("regressed", [])))
    if diff.get("improved"):
        parts.append("<h2>Improved</h2>")
        parts.append(_diff_table(diff["improved"]))
    if diff.get("missing_ids"):
        parts.append("<h2>Missing from current</h2><ul>")
        parts.extend(f"<li><code>{html.escape(ident)}</code></li>" for ident in diff["missing_ids"])
        parts.append("</ul>")
    return _page("Trajectory eval diff", "\n".join(parts))


def _page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root {{
  --ink: #1c1914;
  --muted: #5c564c;
  --rule: #d4cdc2;
  --paper: #f6f1e8;
  --pass: #1d6b45;
  --fail: #9d2c2c;
  --amber: #8a5a12;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 16px/1.45 "Iowan Old Style", Palatino, "Palatino Linotype", Georgia, serif;
}}
main {{ max-width: 960px; margin: 0 auto; padding: 32px 20px 64px; }}
header {{ border-bottom: 1px solid var(--ink); padding-bottom: 16px; margin-bottom: 24px; }}
.kicker {{
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font: 12px/1.4 ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  color: var(--muted);
  margin: 0 0 8px;
}}
h1 {{ font-size: 32px; font-weight: 600; margin: 0; }}
h2 {{ font-size: 20px; margin: 28px 0 8px; }}
.mean {{ font: 56px/1 ui-monospace, Menlo, Consolas, monospace; margin: 12px 0 4px; }}
.sub, .note {{ color: var(--muted); }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--rule); vertical-align: top; }}
th {{ font: 12px/1.3 ui-monospace, Menlo, Consolas, monospace; font-weight: 600; }}
code, pre {{ font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace; font-size: 13px; }}
pre {{
  background: #fff;
  border: 1px solid var(--rule);
  padding: 10px;
  overflow: auto;
  white-space: pre-wrap;
}}
.pass {{ color: var(--pass); }}
.fail {{ color: var(--fail); }}
.amber {{ color: var(--amber); }}
.bars {{ display: grid; gap: 6px; margin: 12px 0 20px; }}
.bar-row {{ display: grid; grid-template-columns: 120px 1fr 64px; gap: 8px; align-items: center; }}
.track {{ background: #e4ddd2; height: 8px; }}
.fill {{ background: var(--ink); height: 8px; }}
details {{ border-top: 1px solid var(--rule); padding: 8px 0; }}
summary {{ cursor: pointer; }}
ul.warn {{ padding-left: 18px; }}
footer {{ margin-top: 36px; color: var(--muted); font-size: 13px; }}
@media (max-width: 640px) {{
  .mean {{ font-size: 40px; }}
  .bar-row {{ grid-template-columns: 1fr; }}
  main {{ padding: 20px 14px 48px; }}
}}
</style>
</head>
<body>
<main>
{body}
<footer>Synthetic trajectories. The mock judge is lexical overlap, not a language model. Scores are measurements of the agents in this repository against the committed golden file.</footer>
</main>
</body>
</html>
"""


def _header(run: dict) -> str:
    judge = run.get("judge", {})
    judge_label = "mock judge" if judge.get("is_mock") else html.escape(str(judge.get("name", "judge")))
    return (
        "<header>"
        f"<p class='kicker'>trajectory-eval-harness · synthetic data · {judge_label}</p>"
        f"<h1>{html.escape(str(run.get('agent', 'eval')))}</h1>"
        f"<p class='mean {_tone(run['mean'])}'>{run['mean']:.4f}</p>"
        f"<p class='sub'>Suite mean across {run['n']} trajectories. "
        f"Source label on the run: {html.escape(str(run.get('source', '')))}.</p>"
        "</header>"
    )


def _summary(run: dict) -> str:
    command = run.get("command") or ""
    if not command:
        return ""
    return f"<p><code>{html.escape(command)}</code></p>"


def _scorer_table(by_scorer: dict) -> str:
    if not by_scorer:
        return ""
    rows = ["<h2>Scorers</h2>", "<div class='bars'>"]
    for name, value in by_scorer.items():
        width = max(0.0, min(100.0, value * 100))
        rows.append(
            "<div class='bar-row'>"
            f"<span>{html.escape(name)}</span>"
            f"<div class='track'><div class='fill' style='width:{width:.2f}%'></div></div>"
            f"<span class='{_tone(value)}'>{value:.4f}</span>"
            "</div>"
        )
    rows.append("</div>")
    return "\n".join(rows)


def _trajectory_table(rows: list[dict], failures_first: bool) -> str:
    ordered = rows
    if not failures_first:
        ordered = sorted(rows, key=lambda row: row["id"])
    lines = ["<h2>Trajectories</h2>", "<table>", "<thead><tr><th>Id</th><th>Task</th><th>Score</th></tr></thead>", "<tbody>"]
    for row in ordered:
        lines.append(
            "<tr>"
            f"<td><code>{html.escape(row['id'])}</code></td>"
            f"<td>{html.escape(str(row.get('task_id', '')))}</td>"
            f"<td class='{_tone(row['score'])}'>{row['score']:.4f}</td>"
            "</tr>"
        )
    lines.append("</tbody></table>")
    return "\n".join(lines)


def _failure_block(row: dict) -> str:
    step_notes = {note for step in row.get("steps", []) for note in step.get("notes", [])}
    extra = [note for note in row.get("notes", []) if note not in step_notes]
    steps = []
    for step in row.get("steps", []):
        bits = f"step {step['index']}: tool {step['tool_choice']:.2f}, exact {step['exact']:.2f}, judge {step['judge']:.2f}"
        if "schema" in step:
            bits += f", schema {step['schema']:.2f}"
        steps.append("<li>" + html.escape(bits))
        if step.get("notes"):
            steps.append("<ul>" + "".join(f"<li>{html.escape(note)}</li>" for note in step["notes"]) + "</ul>")
        steps.append("</li>")
    extra_html = ""
    if extra:
        extra_html = "<ul>" + "".join(f"<li>{html.escape(note)}</li>" for note in extra) + "</ul>"
    return (
        f"<details><summary><code>{html.escape(row['id'])}</code> "
        f"<span class='fail'>{row['score']:.4f}</span></summary>"
        f"{extra_html}<ul>{''.join(steps)}</ul></details>"
    )


def _diff_table(rows: list[dict]) -> str:
    if not rows:
        return "<p class='note'>None.</p>"
    lines = [
        "<table><thead><tr><th>Id</th><th>Before</th><th>After</th><th>Drop</th><th>Scorer drop</th></tr></thead><tbody>"
    ]
    for row in rows:
        scorer = ", ".join(f"{key} {value:+.2f}" for key, value in row.get("scorer_drop", {}).items() if value)
        lines.append(
            "<tr>"
            f"<td><code>{html.escape(row['id'])}</code></td>"
            f"<td>{row['before']:.4f}</td>"
            f"<td>{row['after']:.4f}</td>"
            f"<td class='{_tone(1 - row['drop'])}'>{row['drop']:.4f}</td>"
            f"<td>{html.escape(scorer)}</td>"
            "</tr>"
        )
    lines.append("</tbody></table>")
    return "\n".join(lines)


def _kv_table(mapping: dict, left: str, right: str) -> str:
    lines = [f"<table><thead><tr><th>{html.escape(left)}</th><th>{html.escape(right)}</th></tr></thead><tbody>"]
    for key, value in mapping.items():
        lines.append(f"<tr><td>{html.escape(str(key))}</td><td>{value:.4f}</td></tr>")
    lines.append("</tbody></table>")
    return "\n".join(lines)


def _tone(score: float) -> str:
    if score >= 0.999:
        return "pass"
    if score >= 0.8:
        return "amber"
    return "fail"
