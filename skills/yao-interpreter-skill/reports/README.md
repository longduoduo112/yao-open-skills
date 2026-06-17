# Reports

This public copy normally does not include generated analysis reports.

Generated reports can contain absolute local paths, temporary review outputs, screenshots, or third-party Skill snapshots. Run the CLI locally to create fresh reports:

```bash
python3 scripts/cli.py analyze ./target-skill --out reports/generated
```

The generated `reports/generated/` directory should be reviewed before any public release.

Curated public examples may be published under `reports/examples/` after local paths, temporary clone paths, screenshots, and third-party snapshots have been reviewed and sanitized.
