#!/usr/bin/env python3
"""Calculate demand triangle scores for Yao Demand Skill reports."""

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Mapping


LACK_WEIGHTS = {
    "intensity": 0.25,
    "frequency": 0.15,
    "urgency": 0.15,
    "awareness": 0.15,
    "trend": 0.10,
    "willingness_to_pay": 0.20,
}

TARGET_WEIGHTS = {
    "job_fit": 0.25,
    "clarity": 0.15,
    "differentiation": 0.20,
    "proof": 0.15,
    "category_fit": 0.15,
    "time_to_value": 0.10,
}

ABILITY_WEIGHTS = {
    "money_cost": 0.18,
    "action_cost": 0.16,
    "learning_cost": 0.16,
    "trust_cost": 0.20,
    "risk_cost": 0.14,
    "image_cost": 0.08,
    "availability": 0.08,
}


def clamp(value: float, low: float = 0.0, high: float = 10.0) -> float:
    return max(low, min(high, value))


def weighted_sum(subscores: Mapping[str, Any], weights: Mapping[str, float]) -> float:
    total = 0.0
    missing = []
    for key, weight in weights.items():
        if key not in subscores:
            missing.append(key)
            continue
        total += clamp(float(subscores[key])) * weight
    if missing:
        raise ValueError(f"Missing subscore(s): {', '.join(missing)}")
    return round(total, 2)


def calculate_scores(
    lack_subscores: Mapping[str, Any],
    target_subscores: Mapping[str, Any],
    ability_subscores: Mapping[str, Any],
    evidence_confidence: float = 0.8,
    context_adjustment: float = 0.0,
) -> Dict[str, float]:
    evidence_confidence = max(0.7, min(1.0, float(evidence_confidence)))
    context_adjustment = max(-1.0, min(1.0, float(context_adjustment)))
    lack_score = weighted_sum(lack_subscores, LACK_WEIGHTS)
    target_score = weighted_sum(target_subscores, TARGET_WEIGHTS)
    ability_score = weighted_sum(ability_subscores, ABILITY_WEIGHTS)
    if min(lack_score, target_score, ability_score) <= 0:
        base_total = 0.0
    else:
        base_total = (
            math.pow(lack_score, 0.35)
            * math.pow(target_score, 0.35)
            * math.pow(ability_score, 0.30)
        )
    total_score = clamp(base_total * evidence_confidence + context_adjustment)
    return {
        "lack_score": round(lack_score, 2),
        "target_object_score": round(target_score, 2),
        "consumer_ability_score": round(ability_score, 2),
        "evidence_confidence": round(evidence_confidence, 2),
        "context_adjustment": round(context_adjustment, 2),
        "total_score": round(total_score, 2),
    }


def update_report_scores(report: Dict[str, Any]) -> Dict[str, Any]:
    triangle = report.get("triangle_analysis", {})
    summary = report.setdefault("executive_summary", {})
    confidence = summary.get("evidence_confidence", 0.8)
    adjustment = summary.get("context_adjustment", 0.0)
    scores = calculate_scores(
        triangle.get("lack", {}).get("subscores", {}),
        triangle.get("target_object", {}).get("subscores", {}),
        triangle.get("consumer_ability", {}).get("subscores", {}),
        evidence_confidence=confidence,
        context_adjustment=adjustment,
    )
    triangle.setdefault("lack", {})["score"] = scores["lack_score"]
    triangle.setdefault("target_object", {})["score"] = scores["target_object_score"]
    triangle.setdefault("consumer_ability", {})["score"] = scores["consumer_ability_score"]
    summary.update(scores)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate demand triangle scores.")
    parser.add_argument("report_json", help="Path to report JSON with dimension subscores")
    parser.add_argument("--write", action="store_true", help="Write calculated scores back to the report JSON")
    args = parser.parse_args()

    path = Path(args.report_json).resolve()
    report = json.loads(path.read_text(encoding="utf-8"))
    report = update_report_scores(report)
    scores = report["executive_summary"]

    if args.write:
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "scores": {
                    "lack_score": scores.get("lack_score"),
                    "target_object_score": scores.get("target_object_score"),
                    "consumer_ability_score": scores.get("consumer_ability_score"),
                    "evidence_confidence": scores.get("evidence_confidence"),
                    "context_adjustment": scores.get("context_adjustment", 0.0),
                    "total_score": scores.get("total_score"),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
