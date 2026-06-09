# Report Contract

The report must be comparable across products and traceable back to evidence. Write one canonical `report.json`, then render Markdown, HTML, Word, and PDF from it.

## Required Report Sections

| Section | Content | Presentation |
|---|---|---|
| Executive summary | One-sentence conclusion, total score, dimension scores, biggest opportunity, biggest risk, recommended decision | Dashboard strip plus short narrative |
| Product overview | Product definition, features, price, business model, target market, input sources | Product fact card |
| Method and sources | Search scope, evidence tiers, source limitations, time boundary | Source table |
| Target users and JTBD | Segments, scenarios, triggers, jobs, alternatives, buying roles | Segment table and narrative |
| Competitors and substitutes | Direct competitors, indirect competitors, manual workflows, non-consumption | Competitor matrix |
| Demand triangle analysis | Lack, target object, consumer ability, evidence, counter-evidence, short board | Three structured chapters |
| Scores and interpretation | Subscores, dimension scores, total, confidence, context adjustment | Score table and explanation |
| Recommendations and experiments | Positioning, product, pricing, onboarding, trust, channel, validation plan | Prioritized roadmap |
| Risks and ethics | Privacy, safety, compliance, overclaiming, user harm, evidence weakness | Risk register |
| Appendix | Evidence list, citations, unresolved questions, assumptions | Traceable appendix |

## Required Visual Blocks

The source materials include two visual models that should be preserved as report structure, not as fragile embedded base64 images.

| Visual | Purpose | Rendering Rule |
|---|---|---|
| Demand assessment process | Shows input -> parse -> research -> analyze -> score -> output | HTML/PDF should use inline SVG; Markdown should use Mermaid or text fallback; Word should include the same ordered flow as a table or short figure note. |
| Demand triangle | Shows lack, target object, and consumer ability as a multiplicative short-board model | HTML/PDF should use inline SVG with dimension scores; Markdown should include Mermaid/text; Word should include score table plus the model statement. |

Do not paste large base64 images into generated reports. Prefer inline SVG, small generated PNGs, or text equivalents so the four outputs stay portable and inspectable.

## Canonical JSON Shape

Use `templates/report.schema.json` as the target. The minimum useful shape:

```json
{
  "meta": {
    "title": "",
    "product_name": "",
    "generated_at": "2026-06-09",
    "language": "zh-CN",
    "analyst": "Yao Demand Skill",
    "analysis_goal": "",
    "target_market": "",
    "source_boundary": ""
  },
  "executive_summary": {
    "one_sentence": "",
    "decision": "scale|fix_short_board|validate|reposition|pause",
    "total_score": 0,
    "lack_score": 0,
    "target_object_score": 0,
    "consumer_ability_score": 0,
    "evidence_confidence": 0.8,
    "biggest_opportunity": "",
    "biggest_risk": ""
  },
  "product_canvas": {
    "definition": "",
    "value_proposition": "",
    "features": [],
    "pricing": [],
    "business_model": "",
    "target_users": [],
    "usage_scenarios": [],
    "assumptions": []
  },
  "segments": [
    {
      "name": "",
      "scenario": "",
      "job_to_be_done": "",
      "current_alternatives": [],
      "buying_role": "",
      "adoption_blockers": []
    }
  ],
  "competitors": [
    {
      "name": "",
      "type": "direct|indirect|substitute|manual|non_consumption",
      "positioning": "",
      "strengths": [],
      "weaknesses": [],
      "source_ids": []
    }
  ],
  "triangle_analysis": {
    "lack": {
      "score": 0,
      "subscores": {},
      "evidence": [],
      "counter_evidence": [],
      "reasoning": "",
      "improvement_path": ""
    },
    "target_object": {
      "score": 0,
      "subscores": {},
      "evidence": [],
      "counter_evidence": [],
      "reasoning": "",
      "improvement_path": ""
    },
    "consumer_ability": {
      "score": 0,
      "subscores": {},
      "evidence": [],
      "counter_evidence": [],
      "reasoning": "",
      "improvement_path": ""
    }
  },
  "recommendations": [
    {
      "priority": "P0",
      "area": "positioning|product|pricing|onboarding|trust|channel|research",
      "recommendation": "",
      "rationale": "",
      "expected_impact": "",
      "effort": "low|medium|high"
    }
  ],
  "experiments": [
    {
      "hypothesis": "",
      "segment": "",
      "method": "",
      "metric": "",
      "threshold": "",
      "decision_rule": ""
    }
  ],
  "risks": [
    {
      "type": "demand|evidence|privacy|safety|compliance|ethics|execution",
      "severity": "low|medium|high",
      "risk": "",
      "mitigation": "",
      "source_ids": []
    }
  ],
  "evidence": [],
  "open_questions": []
}
```

## Decision Labels

| Label | Meaning |
|---|---|
| `scale` | Demand triangle is strong; next work is channel and unit economics. |
| `fix_short_board` | Demand likely exists, but one dimension needs repair before scale. |
| `validate` | Demand is plausible but evidence is insufficient. |
| `reposition` | Product may work for a narrower or different segment/JTBD. |
| `pause` | Demand foundation is weak or contradicted by evidence. |

## Writing Standard

- Start with the decision, then explain.
- Use concrete segment names, not "users" everywhere.
- Show where evidence is strong, weak, missing, or contradictory.
- Tables are for comparison; prose is for reasoning.
- Recommendations must reference the weak dimension they improve.
- Avoid generic consultant phrases that do not change the decision.
- Keep citations readable; put dense source metadata in the appendix.

## Format Consistency

All four report outputs must render from the same JSON:

- Markdown: audit-friendly, easy to edit.
- HTML: white editorial report with sticky top menu.
- Word: editable team review and archive version.
- PDF: print/send version generated from the same HTML where possible.

If PDF or Word dependencies are unavailable, report the missing dependency and still produce Markdown and HTML. Do not claim four-format completion until all four files exist.
