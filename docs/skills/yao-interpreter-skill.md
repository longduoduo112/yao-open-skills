# Yao Interpreter Skill

`yao-interpreter-skill` 用来静态解读已有 Agent Skill。它读取本地 Skill 目录、单个 `SKILL.md` 或安全 zip 归档，把用途、触发边界、结构质量、脚本依赖、安全风险和改进路线整理成一份中文优先的双语 HTML 报告。

它适合做采用前评审、作者自检、团队 Skill 准入和学习拆解。目标 Skill 会被当作不可信输入处理，脚本、安装器、测试命令和远程调用都不会被执行。

## 适合什么时候用

- 安装或复用第三方 Skill 前，先判断它是否清楚、可用、安全。
- Skill 作者想知道自己的 `SKILL.md` 是否过重、边界是否清楚、证据链是否完整。
- 团队需要给 Skill 做 100 分质量评分、风险分级和改进路线。
- 想学习一个成熟 Skill 的结构设计、渐进披露、脚本分层和报告交付方式。

## 主流程

1. 把目标路径识别为 Skill 目录、单个 `SKILL.md` 或 zip 归档。
2. 按不可信输入处理目标内容，只做静态读取。
3. 解析 frontmatter、标题、目录、脚本、参考资料、输出契约和生成物。
4. 按 9 个维度生成 100 分评分，并把扣分项绑定到文件、行号和证据片段。
5. 输出默认中文 HTML 报告，同时保留右上角 `简体 / EN` 语言切换。
6. 生成结构化 JSON、发现项、QA 结果和 Markdown 摘要。

## 输出物

默认命令：

```bash
python3 scripts/cli.py analyze ./target-skill --out reports/generated
```

生成文件：

- `report.zh-CN.html`：中文主报告，内置中英切换。
- `analysis.json`：完整结构化分析结果。
- `findings.json`：风险、扣分项、证据、建议和验收标准。
- `qa_report.json`：报告生成后的质量检查结果。
- `summary.md`：适合放进评审记录的短摘要。

需要独立英文 HTML 时：

```bash
python3 scripts/cli.py analyze ./target-skill --out reports/generated --lang zh-CN,en
```

## 安全边界

- 不执行目标 Skill 的脚本、安装器、测试、Makefile 或模型提示。
- 不安装目标依赖，不访问目标声明的外部服务。
- 不修改目标 Skill，只在指定输出目录写报告。
- zip 输入会拒绝路径穿越、异常大文件和可疑符号链接。
- 静态安全结论只是采用前筛查，不替代人工安全审计。

## 公开版说明

公开仓库默认只保留源码、模板、参考资料、schema、eval 和最小示例。生成报告目录默认不随源码发布，因为报告里可能包含本地绝对路径、临时截图、第三方 Skill 快照或审查过程产物。

经过清洗的公开报告可以作为示例发布在 `reports/examples/` 下。目前可查看：

- [yao-meta-skill 解读报告](../../skills/yao-interpreter-skill/reports/examples/yaojingang-yao-meta-skill/report.zh-CN.html)

## 入口文件

- [Skill 入口](../../skills/yao-interpreter-skill/SKILL.md)
- [目录说明](../../skills/yao-interpreter-skill/README.md)
- [评分规则](../../skills/yao-interpreter-skill/references/rubric.zh-CN.md)
- [报告契约](../../skills/yao-interpreter-skill/references/report-contract.zh-CN.md)
- [安全边界](../../skills/yao-interpreter-skill/references/safety-boundary.zh-CN.md)
- [分析脚本](../../skills/yao-interpreter-skill/scripts/cli.py)
