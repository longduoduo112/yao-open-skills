# Yao Doctor Skill

`yao-doctor-skill` 是一个面向本地 Skill 库和 AI 工作台配置面的安全审计 Skill。它把 `能力风险` 和 `不安全行为` 分开评分，帮助你在安装、启用或执行 Skill 前识别隐私读取、凭据读取、静默外发、下载后执行、隐蔽控制链和持久化风险。

它默认生成中英双语 HTML 报告，同时保留结构化 JSON 和 Markdown 摘要。公开版本只包含源码、检测规则、示例报告和 eval fixture，不发布真实本地扫描输出。

## 适合什么时候用

- 扫描本地 `SKILL.md` 目录或一组 Skill 根目录。
- 审查 Codex、Claude、OpenClaw 等工作台配置面和项目级 agent surface。
- 在安装第三方 Skill、公开发布 Skill 或团队启用 Skill 前做安全体检。
- 批量区分“权限面大但没有恶意证据”和“已经出现不安全行为证据”的 Skill。

## 主流程

1. 运行 `scripts/run_yao_doctor_skill.py`，传入一个或多个根目录，或使用默认自动发现范围。
2. 扫描包含 `SKILL.md` 的 Skill 目录，以及支持的工作台配置面。
3. 对每个目标分别计算 `capability risk` 和 `unsafe behavior`。
4. 记录路径、行号、证据类型、置信度、严重级别和建议动作。
5. 生成 `_yao_doctor_skill_reports/<timestamp>/report.html`、`report.json` 和 `report.md`。
6. 更新稳定入口：`full-library-latest` 或 `changed-only-latest`。

## 输出物

默认命令：

```bash
python3 scripts/run_yao_doctor_skill.py --full-scan
```

常见输出：

- `report.html`：中英双语安全报告，包含概览、数据分析、定义、模块说明和 Skill 模块。
- `report.json`：完整结构化审计结果。
- `report.md`：适合放进复核记录的 Markdown 摘要。
- `_yao_doctor_skill_reports/full-library-latest/report.html`：全量扫描的稳定入口。
- `_yao_doctor_skill_reports/changed-only-latest/report.html`：增量扫描的稳定入口。

校验报告 UI 合约：

```bash
python3 scripts/validate_report_ui_contract.py _yao_doctor_skill_reports/full-library-latest/report.html
```

## 安全边界

- 默认只读扫描，不执行被审计 Skill 的脚本。
- 不把权限大直接判定为恶意，必须结合行为证据和证据置信度。
- 对隐私源、凭据源、外部 sink、下载执行、混淆执行和持久化入口做重点提级。
- 公开仓库不提交真实扫描报告、缓存、eval 输出、`__pycache__` 或本地运行产物。
- 对 `unsafe` 和 `critical` 结论，仍建议回到具体代码、用途和安装环境人工复核。

## 公开示例

公开仓库包含一份完全虚构的示例报告，用于展示报告结构、UI 和交互，不来自真实本地环境：

- [示例说明](../../skills/yao-doctor-skill/docs/example-report/README.md)
- [示例 HTML 报告](../../skills/yao-doctor-skill/docs/example-report/report.html)
- [示例 JSON](../../skills/yao-doctor-skill/docs/example-report/report.json)
- [示例 Markdown](../../skills/yao-doctor-skill/docs/example-report/report.md)

## 入口文件

- [Skill 入口](../../skills/yao-doctor-skill/SKILL.md)
- [目录说明](../../skills/yao-doctor-skill/README.md)
- [中文说明](../../skills/yao-doctor-skill/docs/中文说明.md)
- [安全原则](../../skills/yao-doctor-skill/references/security-principles.md)
- [检测分类](../../skills/yao-doctor-skill/references/detection-taxonomy.md)
- [报告蓝图](../../skills/yao-doctor-skill/references/report-blueprint.md)
- [报告 UI 契约](../../skills/yao-doctor-skill/references/report-ui-contract.md)
- [主运行脚本](../../skills/yao-doctor-skill/scripts/run_yao_doctor_skill.py)
