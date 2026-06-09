# Demand Triangle Model

Demand becomes actionable when three conditions are present at the same time:

1. `lack`: the user feels a gap, loss, unfinished job, anxiety, identity pressure, time scarcity, risk, or self-improvement desire.
2. `target_object`: the user understands a concrete product, service, workflow, content, brand promise, community, or mechanism as the solution.
3. `consumer_ability`: the user can afford, trust, learn, access, approve, and continue using the solution.

The model behaves like multiplication. A high score on one side cannot fully compensate for a collapsed side.

## Dimension 1: Lack

| Subscore | Weight | Diagnostic Question | High Signal | Low Signal |
|---|---:|---|---|---|
| `intensity` | 0.25 | How much loss, pressure, emotion, or opportunity cost does the problem create? | Clear loss, stress, failure cost, or strong aspiration. | Mild annoyance or nice-to-have. |
| `frequency` | 0.15 | How often does it occur? | Daily, weekly, recurring workflow, or repeated trigger. | Rare, seasonal, one-off. |
| `urgency` | 0.15 | Does the user need to solve it now? | Deadline, compliance, interruption, health/safety, opportunity window. | Long-term desire with weak action trigger. |
| `awareness` | 0.15 | Is the user conscious of the gap? | Search, complaints, questions, existing workarounds. | Product team must invent the problem framing. |
| `trend` | 0.10 | Is the lack strengthening? | Policy, technology, culture, channel, or workflow change increases pain. | Stable or shrinking issue. |
| `willingness_to_pay` | 0.20 | Does the user already pay, switch, spend time, or accept costs? | Paid substitutes, high manual effort, budget owner pain. | No budget, no switching, no sacrifice. |

Common lack types: functional, emotional, identity, relationship, time, safety/risk, self-actualization.

## Dimension 2: Target Object

| Subscore | Weight | Diagnostic Question | High Signal | Low Signal |
|---|---:|---|---|---|
| `job_fit` | 0.25 | Does the product match the real JTBD? | Clear progress in the user's context. | Feature list detached from user job. |
| `clarity` | 0.15 | Can value be understood in one sentence or 10 seconds? | Sharp first-screen promise, clear category. | Vague, jargon-heavy, overbroad. |
| `differentiation` | 0.20 | Why this instead of competitors or substitutes? | Distinct advantage against real alternatives. | Same claims, feature parity, weak moat. |
| `proof` | 0.15 | Does the product prove it can fill the gap? | Demo, case, trial, metric, customer, certification, credible review. | Claims without evidence. |
| `category_fit` | 0.15 | Does the user know this kind of thing solves the problem? | Mature category or well-bridged new category. | Requires heavy category education. |
| `time_to_value` | 0.10 | How quickly can the user experience progress? | Immediate or low-friction proof of value. | Long setup before benefit. |

The target object is not only the product. It can include service workflow, pricing mechanism, evidence, brand trust, community, refund promise, or delivery process.

## Dimension 3: Consumer Ability

| Subscore | Weight | Diagnostic Question | High Signal | Low Signal |
|---|---:|---|---|---|
| `money_cost` | 0.18 | Does price match value, budget, and payment ability? | Trial, ROI, tiered pricing, affordable entry. | High price, unclear ROI, budget mismatch. |
| `action_cost` | 0.16 | How many steps, approvals, integrations, or waiting points? | Short path, default setup, automation, simple purchase. | Long onboarding, migration, manual steps. |
| `learning_cost` | 0.16 | Does the user need new concepts or skills? | Templates, examples, guided path, progressive disclosure. | Complex docs, new workflow, high error fear. |
| `trust_cost` | 0.20 | Why should the user believe and rely on it? | Reviews, credentials, transparency, third-party proof, guarantees. | Privacy concerns, opaque claims, weak support. |
| `risk_cost` | 0.14 | Are there safety, privacy, compliance, financial, or operational risks? | Clear safeguards, compliance, refund, fallback. | High downside or unclear responsibility. |
| `image_cost` | 0.08 | Does adoption threaten identity, status, politics, or social perception? | Respectful framing, privacy, positive identity symbol. | Shame, awkwardness, organizational politics. |
| `availability` | 0.08 | Can the user actually access it in the channel, region, platform, or workflow? | Available where and when needed. | Geography, platform, procurement, supply constraints. |

## Score Formula

```text
lack_score = weighted_sum([
  intensity * 0.25,
  frequency * 0.15,
  urgency * 0.15,
  awareness * 0.15,
  trend * 0.10,
  willingness_to_pay * 0.20
])

target_score = weighted_sum([
  job_fit * 0.25,
  clarity * 0.15,
  differentiation * 0.20,
  proof * 0.15,
  category_fit * 0.15,
  time_to_value * 0.10
])

ability_score = weighted_sum([
  money_cost * 0.18,
  action_cost * 0.16,
  learning_cost * 0.16,
  trust_cost * 0.20,
  risk_cost * 0.14,
  image_cost * 0.08,
  availability * 0.08
])

base_total = lack_score ** 0.35 * target_score ** 0.35 * ability_score ** 0.30
final_total = clamp(base_total * evidence_confidence + context_adjustment, 0, 10)
```

## Score Interpretation

| Score | Meaning | Action |
|---|---|---|
| `9.0-10.0` | Very strong, multi-source evidence. | Expand validation, optimize secondary constraints. |
| `7.0-8.9` | Strong, with local uncertainty. | Run experiments around weak spots. |
| `5.0-6.9` | Opportunity exists, but evidence is narrow or weak. | Add interviews, competitor proof, and user feedback. |
| `3.0-4.9` | Dimension is weak enough to block demand. | Redefine segment, scenario, target object, or ability design. |
| `0.0-2.9` | Dimension is nearly absent or contradicted by evidence. | Stop scale-up and return to problem discovery. |

Total score bands:

| Total | Meaning | Suggested Decision |
|---|---|---|
| `8.2-10.0` | Demand appears strong and triangle is complete. | Validate channels and unit economics. |
| `6.8-8.1` | Demand likely exists, with a fixable short board. | Fix weakest dimension before scaling. |
| `5.5-6.7` | Demand is plausible but under-evidenced. | Run focused discovery and small experiments. |
| `4.0-5.4` | Demand is fragile or mismatch is unclear. | Rework positioning, segment, or product promise. |
| `0.0-3.9` | Demand foundation is weak. | Pause large investment; revisit problem definition. |

## Red Flags

- Lack red flag: no search, complaint, paid substitute, switching effort, or clear trigger.
- Target red flag: product cannot explain its value in 10 seconds or compares only feature lists.
- Ability red flag: migration, learning, price, privacy, approval, safety, or trust cost blocks adoption.
- Evidence red flag: conclusion rests on a single source, outdated data, soft articles, or unverifiable claims.
- Ethics red flag: the growth path depends on fear, shame, addiction, hidden risk, or exploiting vulnerable users.
