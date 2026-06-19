# Reference Scan

Date: 2026-06-03

## User Materials

- User-provided expert-skill design note
- User-provided industry-learning deep research report

Extracted patterns:

- Skill should act as a domain/industry cognition accelerator, not a generic report writer.
- Default flow: brief, boundary, classification, evidence, current state, lifecycle, actors, keywords, Feynman test, final report.
- Expert learning is judged by structure, evidence, uncertainty handling, and ability to explain to outsiders.
- Keyword method must become a concept system with relationships and decision value.
- Final artifacts must include Markdown, Word, PDF, and HTML; HTML needs fixed left numbered navigation.
- Word/PDF layout risks are first-class: table borders, wrapping, overflow, and export validation must be explicit.

## Local Skill Benchmarks

- `yao-tutorial-skill`: borrowed tutorial/package validation and multi-format export expectations.
- `yao-business-skill`: borrowed evidence labels, market context, JSON/HTML artifact discipline, and source confidence framing.

## What Not To Borrow

- Do not make this a pure business model skill; business model is one section, not the whole job.
- Do not make this a generic beginner tutorial; expert structure and judgment are required.
- Do not require extensive intake before starting when the user only provides a topic; use default assumptions and proceed.
- Do not add a heavy app or UI dependency in v0.1; scripts and templates are enough.

## Package Decision

Mode: Production.

Reason: the skill is reusable, route-confusable with tutorial/business/research skills, and produces user-facing multi-format artifacts where layout failure is common.
