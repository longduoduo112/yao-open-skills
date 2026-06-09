#!/usr/bin/env python3
"""Validate a Yao Demand Skill report JSON before rendering."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set


REQUIRED_TOP_LEVEL = [
    "meta",
    "executive_summary",
    "product_canvas",
    "segments",
    "triangle_analysis",
    "recommendations",
    "risks",
    "evidence",
]

REQUIRED_DIMENSIONS = ["lack", "target_object", "consumer_ability"]
SOURCE_ID_RE = re.compile(r"\bS\d+\b")


def walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from walk_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from walk_strings(item)


def score_in_range(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return 0 <= number <= 10


def validate_report(report: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    for key in REQUIRED_TOP_LEVEL:
        if key not in report:
            errors.append(f"missing top-level key: {key}")

    meta = report.get("meta", {})
    for key in ["title", "product_name", "generated_at", "language"]:
        if not meta.get(key):
            errors.append(f"meta.{key} is required")

    summary = report.get("executive_summary", {})
    for key in ["total_score", "lack_score", "target_object_score", "consumer_ability_score"]:
        if key in summary and not score_in_range(summary.get(key)):
            errors.append(f"executive_summary.{key} must be 0-10")
    confidence = summary.get("evidence_confidence", 0.0)
    try:
        confidence_value = float(confidence)
        if not 0.7 <= confidence_value <= 1.0:
            errors.append("executive_summary.evidence_confidence must be 0.70-1.00")
    except (TypeError, ValueError):
        errors.append("executive_summary.evidence_confidence must be numeric")

    triangle = report.get("triangle_analysis", {})
    counter_count = 0
    for dimension in REQUIRED_DIMENSIONS:
        payload = triangle.get(dimension)
        if not isinstance(payload, dict):
            errors.append(f"triangle_analysis.{dimension} is required")
            continue
        if not score_in_range(payload.get("score")):
            errors.append(f"triangle_analysis.{dimension}.score must be 0-10")
        if not payload.get("subscores"):
            warnings.append(f"triangle_analysis.{dimension}.subscores is empty")
        if not payload.get("reasoning"):
            errors.append(f"triangle_analysis.{dimension}.reasoning is required")
        if not payload.get("improvement_path"):
            errors.append(f"triangle_analysis.{dimension}.improvement_path is required")
        counter_count += len(payload.get("counter_evidence", []) or [])

    if counter_count < 3:
        warnings.append("fewer than 3 counter-evidence items across the triangle analysis")

    evidence = report.get("evidence", [])
    evidence_ids: Set[str] = set()
    if not evidence:
        warnings.append("evidence list is empty")
    for item in evidence:
        if not isinstance(item, dict):
            errors.append("evidence entries must be objects")
            continue
        source_id = item.get("id")
        if not source_id:
            errors.append("evidence entry missing id")
        else:
            evidence_ids.add(str(source_id))
        if not item.get("title"):
            errors.append(f"evidence {source_id or '<unknown>'} missing title")
        if item.get("quality") not in {"A", "B", "C"}:
            errors.append(f"evidence {source_id or '<unknown>'} quality must be A, B, or C")

    mentioned_ids: Set[str] = set()
    for text in walk_strings(report):
        mentioned_ids.update(SOURCE_ID_RE.findall(text))
    missing_ids = sorted(mentioned_ids - evidence_ids)
    if missing_ids:
        warnings.append(f"mentioned source IDs not found in evidence list: {', '.join(missing_ids)}")

    if len(report.get("recommendations", []) or []) == 0:
        errors.append("at least one recommendation is required")
    if len(report.get("risks", []) or []) == 0:
        warnings.append("risk register is empty")
    if len(report.get("segments", []) or []) == 0:
        errors.append("at least one user segment is required")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a Yao Demand Skill report JSON.")
    parser.add_argument("report_json", help="Path to report JSON")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    args = parser.parse_args()

    path = Path(args.report_json).resolve()
    report = json.loads(path.read_text(encoding="utf-8"))
    result = validate_report(report)
    if args.strict and result["warnings"]:
        result["ok"] = False
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
