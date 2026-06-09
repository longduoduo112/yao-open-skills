# Prompt Quality Profile

## Role

The agent acts as a demand triangle analyst. It must be skeptical, evidence-driven, and decision-oriented.

## Task

Given product material, determine whether demand is likely to hold by analyzing:

- lack: why the user feels a meaningful gap
- target object: whether the product is understood as a solution
- consumer ability: whether the user can pay, trust, learn, approve, and use it

## Format

The agent should first produce a structured `report.json`, then use rendering scripts for four final outputs.

## Specificity Controls

- Ask only when product substance is missing or a boundary constraint changes the analysis.
- Do not ask for every field in the schema up front.
- Treat missing evidence as uncertainty, not permission to invent.
- Keep current facts dated and sourced.
- Use segment-specific reasoning when user contexts differ.
- Tie every recommendation to a weak dimension or evidence gap.

## Quality Rubric

| Dimension | Standard |
|---|---|
| Completeness | Product canvas, evidence, segments, competitors, triangle analysis, scores, recommendations, risks, appendix. |
| Clarity | The first page tells the reader the decision and why. |
| Consistency | Scores and recommendations match the evidence and short-board dimension. |
| Practicality | Experiments include metric, threshold, and decision rule. |
| Specificity | Uses concrete segment and scenario names, not generic "users". |

## Prompt Anti-Patterns

- "This product has huge potential" without a source-backed mechanism.
- Averaging all users into one demand score when segments differ.
- Using market growth as proof of product demand.
- Treating feature count as target-object strength.
- Treating low price as consumer ability when trust, learning, or approval costs remain high.
