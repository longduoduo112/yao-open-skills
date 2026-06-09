# Evidence Policy

Demand diagnosis must separate facts, interpretation, assumptions, and recommendations. A persuasive report with weak evidence is a failed report.

## Source Tiers

| Tier | Source Type | Use | Caution |
|---|---|---|---|
| A | Official site, product docs, pricing page, help center, API docs, app-store page | Product facts, features, regions, pricing, capability boundaries | Official sources are promotional; cross-check demand claims. |
| A | Public filings, SEC reports, prospectuses, regulator notices, audited disclosures | Scale, revenue, strategy, risk, compliance, market facts | Watch reporting period and metric definitions. |
| B | G2, Capterra, Trustpilot, app stores, GitHub Issues, Reddit, Zhihu, forums | User friction, alternatives, complaints, adoption blockers | Reviews are sampled and biased; cluster them, do not overgeneralize. |
| B | Industry reports, consulting reports, media deep dives, academic papers | Market context, trend, policy, technology constraints | Check date, sample, sponsorship, and regional fit. |
| C | Social posts, short videos, KOL commentary, community chatter | Emerging lack, user language, cultural signals | Use as signals, not as standalone proof. |
| C | Reposts, anonymous leaks, marketing content | Leads only | Do not support key conclusions independently. |

## Required Evidence Objects

Use this structure in report JSON where possible:

```json
{
  "id": "S1",
  "title": "Source title",
  "url": "https://example.com",
  "source_type": "official|filing|review|media|social|docs|user_material|assumption",
  "quality": "A|B|C",
  "retrieved_at": "2026-06-09",
  "published_at": "",
  "claims": ["Short claim supported by this source"],
  "confidence": 0.85
}
```

## Citation Rules

- Use source IDs such as `[S1]`, `[S2]` in the narrative.
- Do not cite a source unless the source directly supports the adjacent claim.
- Label inferred claims as assumptions when evidence is incomplete.
- If sources conflict, explain the conflict instead of silently choosing one.
- If a fact is current and likely to change, include retrieval date or publication date.
- Do not use a single review, anecdote, or promotional quote as broad demand proof.

## Time-Sensitive Facts

Verify or date these facts:

- pricing, packages, free trials, refund policies
- product versions, launch dates, app ratings, app-store rankings
- funding rounds, revenue, DAU/MAU, customer counts
- regulation, certification, compliance status
- competitive feature availability
- market growth, category share, macro indicators

When verification is unavailable, write "not verified from available sources" and lower evidence confidence.

## Evidence Confidence

Use `0.70-1.00` as the confidence multiplier in scoring.

| Confidence | Meaning |
|---|---|
| `0.95-1.00` | Multiple high-quality sources, current, consistent, and directly relevant. |
| `0.85-0.94` | Good evidence with minor gaps or limited user feedback. |
| `0.75-0.84` | Some evidence but narrow, dated, promotional, or weakly sampled. |
| `0.70-0.74` | Mostly assumptions or single-source evidence; report must emphasize uncertainty. |

Do not use confidence above `0.90` when the report lacks user feedback or independent validation.

## Counter-Evidence Requirement

Every report must list at least three possible demand weaknesses. Examples:

- users do not search, complain, pay, or switch
- product cannot explain value in 10 seconds
- competitor/substitute is cheaper, easier, or more trusted
- price, onboarding, migration, approval, privacy, safety, or reputation cost blocks action
- target market is too narrow or trigger frequency is low
- evidence is dominated by official copy or outdated material

## Ethics Boundary

Do not recommend manipulating users by shame, fear, fake scarcity, false authority, addiction loops, dark patterns, hidden risk, or exploitation of vulnerable groups.

Add a dedicated risk section when the product touches:

- healthcare, financial services, education, employment, insurance, housing, minors, mental health, identity, privacy, security, or high-risk decisions
- products that can encourage addiction, overconsumption, discrimination, harassment, deception, or unsafe behavior
