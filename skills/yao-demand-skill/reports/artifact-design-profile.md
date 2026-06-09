# Artifact Design Profile

## Artifact Family

High-trust product demand assessment report.

The artifact should read like a decision memo with evidence and model-backed reasoning, not like a marketing landing page or a BI dashboard.

## Visual System

- background: pure white `#ffffff`
- accent: ink-blue `#1B365D`
- text: warm near-black and warm graphite
- typography: serif-led Chinese document hierarchy
- layout: centered long document, bounded width, quiet section rhythm
- navigation: HTML-only sticky top menu
- diagrams: inline SVG for workflow and demand triangle
- tables: restrained borders, horizontal overflow on screen, compact print styling

## Density Strategy

- Open with decision, score, opportunity, and risk.
- Use short fact cards for product overview only.
- Use tables when comparing segments, competitors, sources, risks, or experiments.
- Use prose for score reasoning.
- Move dense source metadata to appendix or method section.

## Diagram Strategy

Two visual modules are part of the artifact contract:

1. Process flow: input -> parse -> research -> analyze -> score -> output.
2. Demand triangle: lack, target object, consumer ability, center demand statement, score values.

HTML and PDF render diagrams. Markdown gets Mermaid equivalents. Word gets text/table equivalents unless a future version adds PNG insertion.

## QA Focus

- white background in HTML and PDF
- sticky top menu visible in HTML and hidden in PDF
- no nested cards or decorative visual noise
- no clipped diagram text
- no long URL or evidence overflow
- citations readable without cluttering core paragraphs
