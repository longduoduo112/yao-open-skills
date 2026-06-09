#!/usr/bin/env python3
"""Check package boundaries for yao-demand-skill."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "SKILL.md",
    "agents/interface.yaml",
    "manifest.json",
    "references/workflow.md",
    "references/evidence-policy.md",
    "references/triangle-model.md",
    "references/report-contract.md",
    "references/kami-white-report-layout.md",
    "scripts/score_triangle.py",
    "scripts/validate_report.py",
    "scripts/render_report.py",
    "templates/report.schema.json",
]


def main() -> None:
    failures = []
    forbidden_inline_image = "data:" + "image"
    for rel in REQUIRED:
        if not (ROOT / rel).exists():
            failures.append(f"missing {rel}")
    skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if len(skill_text) > 7000:
        failures.append("SKILL.md exceeds lean entrypoint budget")
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".py", ".html", ".json", ".yaml"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if forbidden_inline_image in text:
                failures.append(f"base64 image found in {path.relative_to(ROOT)}")
    result = {"ok": not failures, "failures": failures}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
