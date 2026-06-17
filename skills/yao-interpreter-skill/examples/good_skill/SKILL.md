---
name: example-good-skill
description: "Use when the user needs to turn a recurring release checklist into a structured Markdown runbook with inputs, outputs, review gates, and handoff notes. Do not use for live deployment or credential handling."
metadata:
  author: "Example"
  version: "0.1.0"
---

# Example Good Skill

把重复发布检查整理成可复用 runbook。

## 输入

- 发布目标和版本号。
- 已知风险和负责人。
- 需要保留的检查项。

## 输出

- `release-runbook.md`
- `release-checklist.json`

## 工作流

1. 读取用户提供的发布材料。
2. 提取发布前、发布中、发布后的检查项。
3. 标注负责人、风险、回滚条件和验收标准。
4. 生成 Markdown runbook 和 JSON checklist。
5. 让用户复核高风险操作。

## 边界

- 不执行部署命令。
- 不读取密钥。
- 不替代人工发布负责人。

## 验收

- 每个高风险步骤都有负责人和回滚条件。
- 输出文件没有占位符。
