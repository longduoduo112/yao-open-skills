# Yao Copyright Skill

## 中文说明

`yao-copyright-skill` 用来给一个 Skill 包的核心文件批量添加姚金刚版权注释。

它重点解决的是“公开、迁移或复用 Skill 前，核心文件缺少统一版权头”的问题。它会根据文件类型选择合适的注释格式，并避免破坏 `SKILL.md` 的 YAML frontmatter、脚本 shebang、JSON 文件和 lock 文件。

### 适合什么时候用

- 给 `SKILL.md`、`README.md`、`references/*.md` 等核心 Markdown 文件加版权注释
- 给 `scripts/*.py`、`scripts/*.sh`、`scripts/*.js`、`scripts/*.ts` 加对应语言的注释头
- 给 `*.yml`、`*.yaml`、`*.toml` 这类支持注释的配置文件加版权头
- 检查目标 Skill 是否已经有姚金刚版权注释，避免重复添加
- 在把本地 Skill 发布到公开仓库前做版权头整理

不适合用来做法律许可选择、起草完整开源协议，或给 JSON、lock 文件、生成产物强行加注释。

### 核心行为

- Markdown 使用 `<!-- ... -->` 注释。
- Python、Shell、YAML、TOML 使用 `# ...` 注释。
- JavaScript 和 TypeScript 使用 `/** ... */` 注释。
- `SKILL.md` 会把版权注释放在 YAML frontmatter 后面，保持 frontmatter 仍在文件第一行。
- 脚本文件会保留 shebang；Python 文件会保留编码声明。
- 已存在版权注释的文件会跳过，避免重复插入。
- JSON、lock 文件、生成文件、缓存、构建产物和 `reports/` 默认跳过。

### 使用方法

先预览将要修改哪些文件：

```bash
python3 skills/yao-copyright-skill/scripts/add_copyright_comments.py /path/to/target-skill --dry-run
```

只处理核心 Markdown：

```bash
python3 skills/yao-copyright-skill/scripts/add_copyright_comments.py /path/to/target-skill
```

连脚本、YAML 和 TOML 一起处理：

```bash
python3 skills/yao-copyright-skill/scripts/add_copyright_comments.py /path/to/target-skill --scope all
```

指定项目名或日期：

```bash
python3 skills/yao-copyright-skill/scripts/add_copyright_comments.py /path/to/target-skill \
  --project yao-meta-skill \
  --date 2026-05-26
```

### 主要输出

脚本会在终端输出每个候选文件的处理状态：

- `[dry-run]`: 预览将写入但未实际修改
- `[write]`: 已写入版权注释
- `[skip] existing-notice`: 文件头部已经有版权注释
- `[skip] generated-or-binary`: 文件像生成文件或不可安全读取

### 目录入口

- [Skill 入口](../../skills/yao-copyright-skill/SKILL.md)
- [目录说明](../../skills/yao-copyright-skill/README.md)
- [版权注释策略](../../skills/yao-copyright-skill/references/copyright-comment-policy.md)
- [注释脚本](../../skills/yao-copyright-skill/scripts/add_copyright_comments.py)
- [脚本测试](../../skills/yao-copyright-skill/tests/test_add_copyright_comments.py)

### 公开发布边界

本 Skill 不包含私有账号、客户资料或生成报告。公开副本保留 Skill 入口、策略文档、执行脚本、接口文件和测试。运行时请先使用 `--dry-run` 检查目标目录，再实际写入。

## English Usage

`yao-copyright-skill` adds standardized Yao copyright comment headers to core files in a skill package.

Use it before publishing or migrating a skill when `SKILL.md`, `README.md`, references, prompts, templates, scripts, YAML, or TOML files need a consistent copyright notice.

### Command

```bash
python3 skills/yao-copyright-skill/scripts/add_copyright_comments.py /path/to/target-skill --dry-run
python3 skills/yao-copyright-skill/scripts/add_copyright_comments.py /path/to/target-skill
python3 skills/yao-copyright-skill/scripts/add_copyright_comments.py /path/to/target-skill --scope all
```

### Publishing boundary

The public copy contains only reusable source files, policy documentation, tests, and the command-line helper. Generated files, reports, caches, JSON files, and lock files are skipped by design.
