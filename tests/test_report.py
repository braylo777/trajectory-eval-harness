from trajeval.format import load_json, load_jsonl
from trajeval.report import render_diff_report, render_report
from tests.helpers import ROOT


def test_report_escapes_html_and_labels_the_mock_judge():
    run = {
        "mean": 0.2,
        "n": 1,
        "agent": "sample",
        "source": "synthetic",
        "judge": {"name": "mock", "is_mock": True},
        "by_scorer": {"exact": 0.2},
        "command": "python -m trajeval eval",
        "trajectories": [
            {
                "id": "x<script>",
                "task_id": "demo",
                "score": 0.2,
                "scorers": {},
                "notes": ["<script>alert(1)</script>"],
                "steps": [
                    {
                        "index": 0,
                        "exact": 0.0,
                        "tool_choice": 0.0,
                        "judge": 0.0,
                        "notes": ["<b>bold</b>"],
                    }
                ],
            }
        ],
    }
    page = render_report(run)
    assert "<script>" not in page
    assert "&lt;script&gt;" in page
    assert "synthetic" in page
    assert "mock judge" in page
    assert "0.2000" in page


def test_committed_sample_report_lists_every_golden_id():
    page = (ROOT / "results" / "sample-report.html").read_text(encoding="utf-8")
    assert "synthetic" in page
    assert "mock judge" in page
    assert "Every trajectory in this run scored 1.0000." in page
    for row in load_jsonl(ROOT / "data" / "golden.jsonl"):
        assert row["id"] in page


def test_diff_report_names_a_regressed_trajectory():
    diff = load_json(ROOT / "results" / "diff.json")
    page = (ROOT / "results" / "diff-report.html").read_text(encoding="utf-8")
    assert diff["n_regressed"] > 0
    assert diff["regressed"][0]["id"] in page
    assert "synthetic" in page
    rendered = render_diff_report(diff)
    assert diff["regressed"][0]["id"] in rendered
