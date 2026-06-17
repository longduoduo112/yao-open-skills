# Reports

This public copy intentionally does not include generated analysis reports.

Generated reports can contain absolute local paths, temporary review outputs, screenshots, or third-party Skill snapshots. Run the CLI locally to create fresh reports:

```bash
python3 scripts/cli.py analyze ./target-skill --out reports/generated
```

The generated `reports/generated/` directory should be reviewed before any public release.
