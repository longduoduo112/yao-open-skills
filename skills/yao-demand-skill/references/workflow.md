# Demand Assessment Workflow

This reference turns product material into a demand triangle report. The job is not to praise or dismiss a product quickly; the job is to show whether demand is likely to hold under evidence, competition, user ability, and adoption friction.

## 1. Intake

Accept any of these inputs:

| Field | Meaning |
|---|---|
| `product_url` | Official site, landing page, app-store page, GitHub repo, docs, product page, or media page. |
| `product_description` | User-provided product idea, value proposition, target user, pricing, or business model. |
| `product_docs` | PRD, PDF, Word, PPT, white paper, sales deck, screenshots, API docs, or product notes. |
| `target_market` | Region, industry, customer segment, language, channel, or buyer context. |
| `analysis_goal` | Investment review, growth diagnosis, positioning rebuild, competitor analysis, pricing review, or pre-launch review. |
| `constraints` | Sites not to use, required competitors, region limits, language, report length, privacy limits, or format preferences. |

If the user gives only a link, analyze from the link and sources. If the user gives only a product description, run a first-pass assessment and mark assumptions. Ask a question only when there is no product substance or a missing constraint changes the analysis boundary.

## 2. Product Canvas

Extract facts before inference:

- product name, category, value proposition, core promise
- target users, buyer, usage scenario, trigger moment
- main features and workflow
- pricing, commercial model, channel, support region
- claimed proof, customers, integrations, certifications, or limitations
- source IDs for every extracted fact
- unknowns and assumptions

Use the canvas to prevent later analysis from drifting into generic market commentary.

## 3. Evidence Plan

Write a short research plan before searching:

1. What product facts need confirmation?
2. What user problems or complaints would support lack?
3. What competitors, substitutes, manual workflows, or non-consumption options might users compare?
4. Which facts are time-sensitive: pricing, version, funding, market share, regulation, app ratings, reviews, or security claims?
5. What counter-evidence would weaken the demand thesis?

Do not collect sources as decoration. Every source should answer a diagnostic question.

## 4. Research Pass

Gather evidence in this order:

1. Official product, docs, pricing, help center, app-store listing, product demo, API docs.
2. User feedback: reviews, G2, Capterra, Trustpilot, App Store, Google Play, GitHub Issues, Reddit, Zhihu, forums.
3. Competitor and substitute evidence: direct competitors, adjacent tools, agencies, manual process, spreadsheets, old workflows, and "do nothing".
4. Market and environment evidence: industry reports, filings, regulator pages, technical constraints, distribution changes.
5. Counter-evidence: too expensive, too hard, untrusted, unnecessary, wrong timing, weak differentiation, privacy or safety risk.

For current or unstable facts, include source date or retrieval date.

## 5. Segmentation And JTBD

Create `2-5` user segments when the product has multiple demand contexts. For each segment:

- segment name and buyer/user role
- concrete scenario and trigger
- job to be done
- current alternative and switching path
- lack type and intensity
- target object interpretation
- consumer ability blockers
- adoption risk and evidence confidence

Do not average away segment differences. A product may have strong demand for one segment and weak demand for another.

## 6. Triangle Analysis

Analyze each segment through:

- `lack`: gap strength, frequency, urgency, awareness, trend, willingness to pay
- `target_object`: job fit, clarity, differentiation, proof, category fit, time to value
- `consumer_ability`: money, action, learning, trust, risk/safety, image, availability

For every dimension, include:

- evidence supporting the score
- counter-evidence or missing evidence
- reasoning for the score
- uncertainty and confidence
- improvement path

## 7. Score And Interpret

Use `references/triangle-model.md` and `scripts/score_triangle.py`.

Scoring rules:

- each subscore is `0-10`
- each dimension score is weighted
- total score uses geometric mean to preserve the short-board effect
- multiply by evidence confidence from `0.70-1.00`
- add context adjustment from `-1.00` to `+1.00`
- clamp final total to `0-10`
- any dimension below `5` is a red flag

## 8. Recommendations And Experiments

Recommendations must map to the weakest dimension:

| Weakest Area | Recommendation Types |
|---|---|
| Lack | redefine segment, sharpen trigger, prove problem frequency, expose hidden cost, run user interviews or search-signal tests |
| Target object | rewrite value proposition, narrow JTBD, improve demo, build proof, reposition against substitutes, reduce promise scope |
| Consumer ability | lower entry price, shorten onboarding, add templates, clarify ROI, add trust proof, reduce migration, improve compliance |

Experiments should be specific enough to run:

- hypothesis
- target segment
- metric
- minimum evidence threshold
- cost and time
- decision rule

## 9. Report Assembly

The final report should include:

1. Executive summary
2. Product overview
3. Research method and source boundary
4. Target users and JTBD scenarios
5. Competitor and substitute map
6. Demand triangle analysis
7. Scores and interpretation
8. Recommendations and validation experiments
9. Risk and ethics
10. Appendix: evidence, citations, unresolved questions

Build a structured JSON first, then render four formats.

## 10. QA Gate

Before rendering:

- each key fact has a source ID or is labeled assumption
- source dates exist for current facts
- at least two source classes appear when available
- at least three counter-signals or red flags are listed
- every score explains deduction and improvement path
- medical, financial, education, employment, minor, mental-health, or high-risk products have explicit risk review
- HTML, Markdown, Word, and PDF content comes from the same report JSON
