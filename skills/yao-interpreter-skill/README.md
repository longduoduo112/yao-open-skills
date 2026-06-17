# Yao Interpreter Skill

`yao-interpreter-skill` 用来静态解读已有 Agent Skill：读取本地目录、`SKILL.md` 或安全 zip 归档，生成证据化评分、风险审查、使用指导和中文优先的双语 HTML 报告。

## 快速使用

```bash
python3 scripts/cli.py analyze ./target-skill --out reports/generated
```

生成文件：

- `reports/generated/report.zh-CN.html`
- `reports/generated/analysis.json`
- `reports/generated/findings.json`
- `reports/generated/qa_report.json`
- `reports/generated/summary.md`

`report.zh-CN.html` 默认显示简体中文，右上角有 `简体 / EN` 语言切换。需要额外生成独立英文文件时：

```bash
python3 scripts/cli.py analyze ./target-skill --out reports/generated --lang zh-CN,en
```

## 安全边界

- 目标 Skill 只作为不可信输入。
- 不执行目标 Skill 的脚本、安装器、测试、Makefile 或模型提示。
- 不安装目标依赖，不访问目标声明的外部服务。
- 不修改目标 Skill，只在输出目录写报告。
- zip 输入会拒绝路径穿越、异常大文件和可疑符号链接。

## 报告重点

- 30 秒看懂：总分、等级、风险、推荐动作。
- 5 分钟学会使用：一句话定位、真实适用场景、谨慎场景、输入输出、示例提示词。
- 30 分钟深度学习：结构、渐进披露、脚本依赖、证据链、评分细则、安全审查、改进路线图。

## 包体地图

- `SKILL.md`：触发边界、工作流、安全边界和输出契约。
- `agents/interface.yaml`：跨平台接口元数据。
- `references/rubric.zh-CN.md`：100 分评分模型和红线规则。
- `references/safety-boundary.zh-CN.md`：不可信输入处理原则。
- `references/report-contract.zh-CN.md`：报告模块、输出文件和 QA 标准。
- `references/html-report-design.zh-CN.md`：白底、sticky 顶部状态栏、左侧目录和图表设计规则。
- `scripts/cli.py`：静态分析、评分、证据链、HTML 渲染和 QA。
- `scripts/smoke_test.py`：确定性 smoke test。
- `templates/report.css`：报告样式，渲染时内联。
- `templates/report.js`：滚动进度、目录高亮、语言切换和复制按钮。
- `schemas/`：`analysis.json` 和 `findings.json` 的 JSON Schema。
- `evals/trigger_cases.json`：触发正例、反例和近邻边界。
- `examples/`：好样例和风险样例。

## 验证

```bash
python3 -m py_compile scripts/cli.py scripts/smoke_test.py
python3 scripts/smoke_test.py
```
