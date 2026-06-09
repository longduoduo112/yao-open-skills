# Evals

Run from the skill root:

```bash
python3 evals/resource_boundary_check.py
python3 evals/trigger_eval.py
python3 scripts/validate_report.py reports/sample-ai-meeting-tool.report.json
python3 scripts/render_report.py reports/sample-ai-meeting-tool.report.json --outdir reports/rendered-sample --basename sample-ai-meeting-tool
```

These are lightweight first-release gates. They check route clarity, package boundaries, and report rendering.
