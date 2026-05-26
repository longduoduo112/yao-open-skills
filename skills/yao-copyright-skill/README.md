<!--
Copyright © 2026 姚金刚. All rights reserved.
Project: yao-copyright-skill
Created by: 姚金刚
Date: 2026-05-16
X: https://x.com/yaojingang
-->

# Yao Copyright Skill

Adds Yao copyright comment headers to core files in an installed skill package.

Common usage:

```bash
python3 scripts/add_copyright_comments.py /path/to/target-skill --dry-run
python3 scripts/add_copyright_comments.py /path/to/target-skill
python3 scripts/add_copyright_comments.py /path/to/target-skill --scope all
```

The default pass covers core Markdown files. `--scope all` also covers scripts plus YAML and TOML configs. JSON, lock files, generated files, build outputs, caches, and `reports/` are skipped.
