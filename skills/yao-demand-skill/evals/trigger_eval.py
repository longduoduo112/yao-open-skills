#!/usr/bin/env python3
"""Lightweight trigger check for yao-demand-skill."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "evals" / "trigger_cases.json"
SKILL = ROOT / "SKILL.md"


POSITIVE_TERMS = [
    "需求",
    "需求三角",
    "缺乏感",
    "目标物",
    "消费者能力",
    "需求评估",
    "需求基础",
    "红旗项",
    "投前",
    "增长诊断",
    "上市前",
]

NEGATIVE_TERMS = [
    "广告文案",
    "TAM",
    "SAM",
    "SOM",
    "UI",
    "财务预测",
    "法律意见",
]


def score(text: str) -> int:
    value = 0
    for term in POSITIVE_TERMS:
        if term.lower() in text.lower():
            value += 1
    for term in NEGATIVE_TERMS:
        if term.lower() in text.lower():
            value -= 1
    return value


def main() -> None:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    description = re.search(r"description:\s*(.*)", SKILL.read_text(encoding="utf-8"))
    failures = []
    if not description:
        failures.append("missing description")
    for item in cases["positives"]:
        if score(item) <= 0:
            failures.append(f"positive missed: {item}")
    for item in cases["negatives"]:
        if score(item) > 0:
            failures.append(f"negative incorrectly matched: {item}")
    result = {"ok": not failures, "failures": failures}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
