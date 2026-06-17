#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "scripts" / "cli.py"
TMP = ROOT / "reports" / "smoke"


def run_case(name: str, target: Path) -> dict:
    out = TMP / name
    shutil.rmtree(out, ignore_errors=True)
    proc = subprocess.run(
        [sys.executable, str(CLI), "analyze", str(target), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    analysis = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    html = (out / "report.zh-CN.html").read_text(encoding="utf-8")
    qa = json.loads((out / "qa_report.json").read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert qa["score_sum_matches"] is True
    assert "position: sticky" in html
    assert "评分雷达" in html
    assert (out / "findings.json").exists()
    assert (out / "summary.md").exists()
    return analysis


def main() -> None:
    shutil.rmtree(TMP, ignore_errors=True)
    good = run_case("good", ROOT / "examples" / "good_skill")
    risky = run_case("risky", ROOT / "examples" / "risky_skill")
    assert good["scorecard"]["total"] >= 70, good["scorecard"]
    assert risky["scorecard"]["risk_level"] in {"high", "critical"}, risky["scorecard"]
    assert any(item["severity"] == "critical" for item in risky["findings"]), risky["findings"]
    print(json.dumps({"ok": True, "good_score": good["scorecard"]["total"], "risky_score": risky["scorecard"]["total"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
