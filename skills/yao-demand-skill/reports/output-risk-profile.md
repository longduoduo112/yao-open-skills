# Output Risk Profile

## High-Risk Failure Modes

| Risk | Impact | Control |
|---|---|---|
| Unsupported demand claims | Report looks authoritative but cannot be reviewed. | Require source IDs or assumption labels for key facts. |
| Single-source overconfidence | Official product copy gets mistaken for market demand. | Evidence policy separates official, third-party, user feedback, and weak signals. |
| Score theater | Scores appear precise without reasoning. | Every dimension requires evidence, counter-evidence, reasoning, uncertainty, and improvement path. |
| Missing counter-signals | Report becomes a sales memo. | Validation warns when fewer than three counter-evidence items exist. |
| Four outputs diverge | HTML, PDF, Word, and Markdown disagree. | Render all formats from one canonical JSON. |
| Layout overflow | Tables, URLs, or diagrams clip in HTML/PDF. | White layout reference requires table wrappers, overflow wrapping, fixed SVG viewBox, and print checks. |
| Sticky nav prints into PDF | PDF looks like a webpage screenshot. | CSS hides `.top-nav` in print. |
| Ethical overreach | Recommendations amplify shame, fear, addiction, or hidden risk. | Evidence policy requires risk section for sensitive product categories. |

## Required Checks

- Run `scripts/validate_report.py <report.json>` before rendering.
- Run `scripts/score_triangle.py <report.json> --write` when subscores are present.
- Run `scripts/render_report.py <report.json>` and verify all four files exist.
- Inspect HTML/PDF for white background, sticky menu behavior, table overflow, and diagram legibility.

## Reviewer Notes

The report may still be weak if it has no independent user feedback. In that case, lower `evidence_confidence` and make the output a validation plan rather than a scale recommendation.
