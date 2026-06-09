#!/usr/bin/env python3
"""Render Yao Demand Skill report JSON to Markdown, HTML, DOCX, and PDF."""

import argparse
import html
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from validate_report import validate_report


SECTION_NAV = [
    ("summary", "摘要"),
    ("product", "产品"),
    ("method", "方法"),
    ("users", "用户"),
    ("competitors", "竞品"),
    ("triangle", "三角"),
    ("scores", "评分"),
    ("recommendations", "建议"),
    ("risks", "风险"),
    ("appendix", "附录"),
]


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def score(value: Any) -> str:
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "-"


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value.lower()).strip("-")
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned or "demand-report"


def md_escape(value: Any) -> str:
    return text(value).replace("|", "\\|").replace("\n", " ")


def h(value: Any) -> str:
    return html.escape(text(value), quote=True)


def md_list(items: Sequence[Any]) -> str:
    values = [text(item).strip() for item in items if text(item).strip()]
    if not values:
        return "- 未提供\n"
    return "\n".join(f"- {item}" for item in values) + "\n"


def md_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    if not rows:
        return ""
    header = "| " + " | ".join(md_escape(item) for item in headers) + " |"
    divider = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(md_escape(cell) for cell in row) + " |" for row in rows]
    return "\n".join([header, divider] + body) + "\n"


def html_list(items: Sequence[Any]) -> str:
    values = [h(item) for item in items if text(item).strip()]
    if not values:
        return "<p class=\"muted\">未提供</p>"
    return "<ul>" + "".join(f"<li>{item}</li>" for item in values) + "</ul>"


def html_table(headers: Sequence[str], rows: Sequence[Sequence[Any]], compact: bool = False) -> str:
    if not rows:
        return "<p class=\"muted\">未提供</p>"
    cls = "compact" if compact else ""
    head = "".join(f"<th>{h(item)}</th>" for item in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{h(cell)}</td>" for cell in row) + "</tr>")
    return (
        f"<div class=\"table-wrap\"><table class=\"{cls}\"><thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def decision_label(value: str) -> str:
    labels = {
        "scale": "可以扩大验证",
        "fix_short_board": "先修短板",
        "validate": "先补验证",
        "reposition": "重做定位",
        "pause": "暂停规模投入",
    }
    return labels.get(value, value or "-")


def score_band(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if number >= 8.2:
        return "strong"
    if number >= 6.8:
        return "good"
    if number >= 5.5:
        return "uncertain"
    if number >= 4.0:
        return "fragile"
    return "weak"


def render_process_svg() -> str:
    steps = [
        ("输入", ["链接", "介绍", "文档"]),
        ("解析", ["产品画布", "用户假设", "价值主张"]),
        ("检索", ["权威资料", "竞品", "评价", "价格"]),
        ("分析", ["缺乏感", "目标物", "能力成本"]),
        ("评分", ["三维得分", "信心系数", "红旗项"]),
        ("输出", ["Markdown", "HTML", "Word", "PDF"]),
    ]
    card_w = 130
    card_h = 132
    gap = 36
    parts = [
        '<svg class="process-svg" viewBox="0 0 1030 230" role="img" aria-label="需求评估分析流程图">',
        '<rect x="0" y="0" width="1030" height="230" fill="#ffffff"/>',
    ]
    for index, (title, items) in enumerate(steps):
        x = 26 + index * (card_w + gap)
        parts.append(f'<rect x="{x}" y="32" width="{card_w}" height="{card_h}" rx="6" fill="#ffffff" stroke="#141413" stroke-width="2"/>')
        parts.append(f'<text x="{x + card_w / 2}" y="62" text-anchor="middle" class="svg-title">{h(title)}</text>')
        for item_index, item in enumerate(items):
            parts.append(f'<text x="{x + card_w / 2}" y="{90 + item_index * 18}" text-anchor="middle" class="svg-body">{h(item)}</text>')
        if index < len(steps) - 1:
            ax = x + card_w + 10
            ay = 98
            parts.append(f'<line x1="{ax}" y1="{ay}" x2="{ax + gap - 20}" y2="{ay}" stroke="#141413" stroke-width="2"/>')
            parts.append(f'<path d="M {ax + gap - 20} {ay} l -8 -5 v 10 z" fill="#141413"/>')
    parts.append('<text x="515" y="206" text-anchor="middle" class="svg-caption">核心原则：先把产品放进用户真实场景，再用证据校准三角各边。</text>')
    parts.append("</svg>")
    return "".join(parts)


def render_triangle_svg(report: Dict[str, Any]) -> str:
    summary = report.get("executive_summary", {})
    lack = score(summary.get("lack_score"))
    target = score(summary.get("target_object_score"))
    ability = score(summary.get("consumer_ability_score"))
    total = score(summary.get("total_score"))
    return f"""
<svg class="triangle-svg" viewBox="0 0 900 650" role="img" aria-label="需求三角模型分析结构">
  <rect x="0" y="0" width="900" height="650" fill="#ffffff"/>
  <polygon points="450,88 158,520 742,520" fill="#ffffff" stroke="#1B365D" stroke-width="5" stroke-linejoin="round"/>
  <circle cx="450" cy="394" r="156" fill="#ffffff" stroke="#141413" stroke-width="2.5"/>
  <line x1="374" y1="230" x2="272" y2="455" stroke="#141413" stroke-width="2.5"/>
  <path d="M 272 455 l 0 -12 l 10 6 z" fill="#141413"/>
  <line x1="526" y1="230" x2="628" y2="455" stroke="#141413" stroke-width="2.5"/>
  <path d="M 628 455 l -10 -6 l 10 -6 z" fill="#141413"/>
  <rect x="345" y="20" width="210" height="58" rx="9" fill="#ffffff" stroke="#141413" stroke-width="2"/>
  <text x="450" y="45" text-anchor="middle" class="svg-title">缺乏感</text>
  <text x="450" y="66" text-anchor="middle" class="svg-small">理想与现实的差距 | {lack}</text>
  <rect x="20" y="548" width="240" height="66" rx="9" fill="#ffffff" stroke="#141413" stroke-width="2"/>
  <text x="140" y="578" text-anchor="middle" class="svg-title">目标物</text>
  <text x="140" y="600" text-anchor="middle" class="svg-small">填补差距的具体方案 | {target}</text>
  <rect x="640" y="548" width="240" height="66" rx="9" fill="#ffffff" stroke="#141413" stroke-width="2"/>
  <text x="760" y="578" text-anchor="middle" class="svg-title">消费者能力</text>
  <text x="760" y="600" text-anchor="middle" class="svg-small">行动所需成本承受力 | {ability}</text>
  <text x="450" y="375" text-anchor="middle" class="svg-title">需求成立</text>
  <text x="450" y="403" text-anchor="middle" class="svg-body">动机清晰 + 成本可承受 + 场景触发</text>
  <text x="450" y="438" text-anchor="middle" class="svg-score">总分 {total}</text>
  <text x="450" y="636" text-anchor="middle" class="svg-caption">任一维度明显缺失，需求成立概率都会下降。</text>
</svg>
"""


def score_rows(report: Dict[str, Any]) -> List[List[Any]]:
    summary = report.get("executive_summary", {})
    return [
        ["缺乏感", score(summary.get("lack_score"))],
        ["目标物", score(summary.get("target_object_score"))],
        ["消费者能力", score(summary.get("consumer_ability_score"))],
        ["证据信心", text(summary.get("evidence_confidence", "-"))],
        ["总分", score(summary.get("total_score"))],
    ]


def competitor_rows(report: Dict[str, Any]) -> List[List[Any]]:
    rows = []
    for item in as_list(report.get("competitors")):
        rows.append(
            [
                item.get("name", ""),
                item.get("type", ""),
                item.get("positioning", ""),
                "；".join(as_list(item.get("strengths"))),
                "；".join(as_list(item.get("weaknesses"))),
                " ".join(as_list(item.get("source_ids"))),
            ]
        )
    return rows


def segment_rows(report: Dict[str, Any]) -> List[List[Any]]:
    rows = []
    for item in as_list(report.get("segments")):
        rows.append(
            [
                item.get("name", ""),
                item.get("scenario", ""),
                item.get("job_to_be_done", ""),
                "；".join(as_list(item.get("current_alternatives"))),
                "；".join(as_list(item.get("adoption_blockers"))),
            ]
        )
    return rows


def evidence_rows(report: Dict[str, Any]) -> List[List[Any]]:
    rows = []
    for item in as_list(report.get("evidence")):
        rows.append(
            [
                item.get("id", ""),
                item.get("quality", ""),
                item.get("source_type", ""),
                item.get("title", ""),
                item.get("url", ""),
                item.get("retrieved_at") or item.get("published_at", ""),
            ]
        )
    return rows


def risk_rows(report: Dict[str, Any]) -> List[List[Any]]:
    rows = []
    for item in as_list(report.get("risks")):
        rows.append(
            [
                item.get("severity", ""),
                item.get("type", ""),
                item.get("risk", ""),
                item.get("mitigation", ""),
                " ".join(as_list(item.get("source_ids"))),
            ]
        )
    return rows


def experiment_rows(report: Dict[str, Any]) -> List[List[Any]]:
    rows = []
    for item in as_list(report.get("experiments")):
        rows.append(
            [
                item.get("hypothesis", ""),
                item.get("segment", ""),
                item.get("method", ""),
                item.get("metric", ""),
                item.get("threshold", ""),
                item.get("decision_rule", ""),
            ]
        )
    return rows


def render_markdown(report: Dict[str, Any]) -> str:
    meta = report.get("meta", {})
    summary = report.get("executive_summary", {})
    canvas = report.get("product_canvas", {})
    triangle = report.get("triangle_analysis", {})
    lines: List[str] = []

    lines.append(f"# {text(meta.get('title') or meta.get('product_name') or '需求评估报告')}\n")
    lines.append(f"- 产品：{text(meta.get('product_name'))}")
    lines.append(f"- 日期：{text(meta.get('generated_at'))}")
    lines.append(f"- 目标市场：{text(meta.get('target_market', '未指定'))}")
    lines.append(f"- 分析目标：{text(meta.get('analysis_goal', '需求评估'))}")
    lines.append(f"- 来源边界：{text(meta.get('source_boundary', '未说明'))}\n")

    lines.append("## 执行摘要\n")
    lines.append(f"{text(summary.get('one_sentence'))}\n")
    lines.append(md_table(["项目", "结果"], [
        ["建议决策", decision_label(summary.get("decision", ""))],
        ["总分", score(summary.get("total_score"))],
        ["缺乏感", score(summary.get("lack_score"))],
        ["目标物", score(summary.get("target_object_score"))],
        ["消费者能力", score(summary.get("consumer_ability_score"))],
        ["证据信心", text(summary.get("evidence_confidence"))],
        ["最大机会", summary.get("biggest_opportunity", "")],
        ["最大风险", summary.get("biggest_risk", "")],
    ]))

    lines.append("## 产品概览\n")
    lines.append(f"**产品定义：** {text(canvas.get('definition'))}\n")
    lines.append(f"**价值主张：** {text(canvas.get('value_proposition'))}\n")
    lines.append("**核心功能：**\n")
    lines.append(md_list(as_list(canvas.get("features"))))
    lines.append("**定价与商业模式：**\n")
    lines.append(md_list(as_list(canvas.get("pricing")) + [canvas.get("business_model", "")]))
    lines.append("**假设：**\n")
    lines.append(md_list(as_list(canvas.get("assumptions"))))

    lines.append("## 研究方法与来源\n")
    lines.append(text(meta.get("source_boundary", "本报告区分事实、假设、证据和建议。")) + "\n")
    lines.append("```mermaid\nflowchart LR\n  A[输入\\n链接/介绍/文档] --> B[解析\\n产品画布/用户假设/价值主张]\n  B --> C[检索\\n权威资料/竞品/评价/价格]\n  C --> D[分析\\n缺乏感/目标物/能力成本]\n  D --> E[评分\\n三维得分/信心系数/红旗项]\n  E --> F[输出\\nMarkdown/HTML/Word/PDF]\n```\n")
    lines.append(md_table(["来源", "等级", "类型", "标题", "链接", "日期"], evidence_rows(report)))

    lines.append("## 目标用户与 JTBD\n")
    lines.append(md_table(["分群", "场景", "JTBD", "当前替代", "采用阻碍"], segment_rows(report)))

    lines.append("## 竞品与替代方案\n")
    lines.append(md_table(["名称", "类型", "定位", "优势", "弱点", "来源"], competitor_rows(report)))

    lines.append("## 需求三角分析\n")
    lines.append("```mermaid\nflowchart TB\n  L[缺乏感\\n理想与现实的差距] --> M[需求成立\\n动机清晰 + 成本可承受 + 场景触发]\n  T[目标物\\n填补差距的具体方案] --> M\n  A[消费者能力\\n行动所需成本承受力] --> M\n```\n")
    for key, label in [("lack", "缺乏感"), ("target_object", "目标物"), ("consumer_ability", "消费者能力")]:
        dim = triangle.get(key, {})
        lines.append(f"### {label}：{score(dim.get('score'))}\n")
        lines.append(f"**推理：** {text(dim.get('reasoning'))}\n")
        lines.append("**支持证据：**\n")
        lines.append(md_list(as_list(dim.get("evidence"))))
        lines.append("**反证或缺口：**\n")
        lines.append(md_list(as_list(dim.get("counter_evidence"))))
        lines.append(f"**改进路径：** {text(dim.get('improvement_path'))}\n")

    lines.append("## 评分与解释\n")
    lines.append(md_table(["维度", "分数"], score_rows(report)))

    lines.append("## 建议与实验\n")
    rec_rows = [
        [
            item.get("priority", ""),
            item.get("area", ""),
            item.get("recommendation", ""),
            item.get("rationale", ""),
            item.get("expected_impact", ""),
            item.get("effort", ""),
        ]
        for item in as_list(report.get("recommendations"))
    ]
    lines.append(md_table(["优先级", "领域", "建议", "理由", "预期影响", "成本"], rec_rows))
    lines.append(md_table(["假设", "分群", "方法", "指标", "阈值", "决策规则"], experiment_rows(report)))

    lines.append("## 风险与伦理\n")
    lines.append(md_table(["严重度", "类型", "风险", "缓释", "来源"], risk_rows(report)))

    lines.append("## 附录\n")
    lines.append("### 未解问题\n")
    lines.append(md_list(as_list(report.get("open_questions"))))
    return "\n".join(lines).rstrip() + "\n"


def render_html(report: Dict[str, Any]) -> str:
    meta = report.get("meta", {})
    summary = report.get("executive_summary", {})
    canvas = report.get("product_canvas", {})
    triangle = report.get("triangle_analysis", {})
    title = meta.get("title") or meta.get("product_name") or "需求评估报告"
    band = score_band(summary.get("total_score"))
    nav_links = "".join(f"<a href=\"#{anchor}\">{label}</a>" for anchor, label in SECTION_NAV)

    dimension_cards = []
    for key, label in [("lack", "缺乏感"), ("target_object", "目标物"), ("consumer_ability", "消费者能力")]:
        dim = triangle.get(key, {})
        dimension_cards.append(
            f"""
            <article class="dimension-card">
              <div class="dimension-head"><h3>{h(label)}</h3><span>{score(dim.get('score'))}</span></div>
              <p>{h(dim.get('reasoning'))}</p>
              <h4>支持证据</h4>
              {html_list(as_list(dim.get('evidence')))}
              <h4>反证或缺口</h4>
              {html_list(as_list(dim.get('counter_evidence')))}
              <div class="note"><strong>改进路径</strong><br>{h(dim.get('improvement_path'))}</div>
            </article>
            """
        )

    rec_rows = [
        [
            item.get("priority", ""),
            item.get("area", ""),
            item.get("recommendation", ""),
            item.get("rationale", ""),
            item.get("expected_impact", ""),
            item.get("effort", ""),
        ]
        for item in as_list(report.get("recommendations"))
    ]

    html_doc = f"""<!doctype html>
<html lang="{h(meta.get('language', 'zh-CN'))}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{h(title)}</title>
  <meta name="generator" content="Yao Demand Skill">
  <style>
    :root {{
      --paper: #ffffff;
      --near-black: #141413;
      --dark-warm: #3d3d3a;
      --olive: #504e49;
      --stone: #6b6a64;
      --border: #e8e6dc;
      --border-soft: #efeee8;
      --brand: #1B365D;
      --brand-soft: #EEF2F7;
      --green: #2f6f4e;
      --amber: #8a641f;
      --red: #9b3a32;
      --serif: "TsangerJinKai02", "Source Han Serif SC", "Noto Serif CJK SC", "Songti SC", "STSong", Georgia, serif;
      --mono: "JetBrains Mono", "SF Mono", Consolas, "TsangerJinKai02", "Source Han Serif SC", monospace;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; background: var(--paper); }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--near-black);
      font-family: var(--serif);
      font-size: 16px;
      line-height: 1.58;
      letter-spacing: 0;
    }}
    .top-nav {{
      position: sticky;
      top: 0;
      z-index: 30;
      background: var(--paper);
      border-bottom: 1px solid var(--border);
    }}
    .nav-inner {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 12px 28px;
      display: flex;
      align-items: center;
      gap: 24px;
    }}
    .nav-title {{
      min-width: 180px;
      max-width: 320px;
      color: var(--near-black);
      font-size: 15px;
      line-height: 1.25;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .nav-links {{
      display: flex;
      gap: 14px;
      overflow-x: auto;
      scrollbar-width: thin;
      white-space: nowrap;
    }}
    .nav-links a {{
      color: var(--brand);
      text-decoration: none;
      font-size: 14px;
      padding: 4px 0;
      border-bottom: 1px solid transparent;
    }}
    .nav-links a:hover {{ border-bottom-color: var(--brand); }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 48px 28px 72px;
    }}
    header.report-header {{
      border-bottom: 1px solid var(--border);
      padding-bottom: 28px;
      margin-bottom: 28px;
    }}
    .eyebrow {{
      color: var(--brand);
      font-size: 13px;
      letter-spacing: 0.5px;
      margin-bottom: 12px;
    }}
    h1 {{
      margin: 0 0 14px;
      font-size: clamp(32px, 5vw, 54px);
      line-height: 1.12;
      font-weight: 500;
    }}
    h2 {{
      margin: 0 0 16px;
      font-size: 26px;
      line-height: 1.25;
      font-weight: 500;
      border-left: 4px solid var(--brand);
      padding-left: 12px;
    }}
    h3 {{
      margin: 0 0 8px;
      font-size: 19px;
      line-height: 1.3;
      font-weight: 500;
    }}
    h4 {{
      margin: 18px 0 8px;
      font-size: 15px;
      line-height: 1.35;
      color: var(--dark-warm);
      font-weight: 500;
    }}
    section {{
      padding: 34px 0;
      border-top: 1px solid var(--border-soft);
      scroll-margin-top: 74px;
    }}
    .lede {{
      max-width: 820px;
      color: var(--dark-warm);
      font-size: 18px;
      line-height: 1.62;
    }}
    .meta-grid, .score-grid, .fact-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .meta-item, .score-card, .fact-box, .dimension-card, .note {{
      border: 1px solid var(--border);
      background: var(--paper);
      border-radius: 8px;
      padding: 16px;
    }}
    .meta-item span, .score-card span {{
      display: block;
      color: var(--stone);
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .score-card strong {{
      display: block;
      font-size: 28px;
      line-height: 1.1;
      font-weight: 500;
      color: var(--brand);
    }}
    .decision {{
      display: inline-block;
      color: var(--brand);
      background: var(--brand-soft);
      border-radius: 4px;
      padding: 2px 8px;
      font-size: 14px;
    }}
    .total-score {{
      border-top: 4px solid var(--brand);
    }}
    .band-strong strong, .band-good strong {{ color: var(--green); }}
    .band-uncertain strong {{ color: var(--amber); }}
    .band-fragile strong, .band-weak strong {{ color: var(--red); }}
    .dimension-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
    }}
    .diagram-block {{
      margin: 18px 0 26px;
      padding: 0;
      overflow-x: auto;
    }}
    .diagram-block svg {{
      width: 100%;
      min-width: 720px;
      height: auto;
      display: block;
    }}
    .figure-caption {{
      margin-top: 8px;
      color: var(--stone);
      font-size: 14px;
      line-height: 1.45;
    }}
    .svg-title {{
      font-family: var(--serif);
      font-size: 19px;
      font-weight: 500;
      fill: #141413;
    }}
    .svg-body {{
      font-family: var(--serif);
      font-size: 17px;
      fill: #141413;
    }}
    .svg-small {{
      font-family: var(--serif);
      font-size: 13px;
      fill: #3d3d3a;
    }}
    .svg-score {{
      font-family: var(--serif);
      font-size: 22px;
      font-weight: 500;
      fill: #1B365D;
    }}
    .svg-caption {{
      font-family: var(--serif);
      font-size: 15px;
      font-weight: 500;
      fill: #141413;
    }}
    .dimension-head {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
      border-bottom: 1px solid var(--border-soft);
      padding-bottom: 10px;
      margin-bottom: 12px;
    }}
    .dimension-head span {{
      color: var(--brand);
      font-size: 28px;
      line-height: 1;
    }}
    .table-wrap {{
      width: 100%;
      overflow-x: auto;
      margin: 14px 0 22px;
      border: 1px solid var(--border-soft);
      border-radius: 8px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 720px;
      font-size: 14px;
      line-height: 1.45;
    }}
    table.compact {{ font-size: 13px; }}
    th {{
      text-align: left;
      color: var(--dark-warm);
      font-weight: 500;
      background: #fbfbfa;
      border-bottom: 1px solid var(--border);
      padding: 10px 12px;
    }}
    td {{
      vertical-align: top;
      border-bottom: 1px solid var(--border-soft);
      padding: 9px 12px;
      overflow-wrap: anywhere;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    ul {{ margin: 8px 0 0 20px; padding: 0; }}
    li {{ margin: 4px 0; }}
    .muted {{ color: var(--stone); }}
    .note {{
      margin-top: 14px;
      background: #fbfbfa;
      overflow-wrap: anywhere;
    }}
    .two-col {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 16px;
    }}
    a {{ color: var(--brand); overflow-wrap: anywhere; }}
    @page {{
      size: A4;
      margin: 18mm 20mm 20mm 20mm;
      background: #ffffff;
    }}
    @media print {{
      body {{ font-size: 10pt; line-height: 1.52; }}
      .top-nav {{ display: none; }}
      main {{ max-width: none; padding: 0; }}
      section, .score-card, .fact-box, .risk-item {{ break-inside: avoid; }}
      .dimension-grid, .meta-grid, .score-grid, .fact-grid, .two-col {{
        display: block;
      }}
      .dimension-card, .score-card, .meta-item, .fact-box {{
        margin-bottom: 10pt;
      }}
      table {{ min-width: 0; font-size: 8.5pt; }}
      .table-wrap {{ overflow: visible; border: 0; }}
    }}
    @media (max-width: 820px) {{
      .nav-inner {{ padding: 10px 18px; display: block; }}
      .nav-title {{ max-width: none; margin-bottom: 8px; }}
      main {{ padding: 32px 18px 56px; }}
      .meta-grid, .score-grid, .fact-grid, .dimension-grid, .two-col {{
        grid-template-columns: 1fr;
      }}
      h1 {{ font-size: 34px; }}
      h2 {{ font-size: 23px; }}
    }}
  </style>
</head>
<body>
  <nav class="top-nav">
    <div class="nav-inner">
      <div class="nav-title">{h(meta.get('product_name') or title)}</div>
      <div class="nav-links">{nav_links}</div>
    </div>
  </nav>
  <main>
    <header class="report-header">
      <div class="eyebrow">需求三角评估报告</div>
      <h1>{h(title)}</h1>
      <p class="lede">{h(summary.get('one_sentence'))}</p>
      <div class="meta-grid">
        <div class="meta-item"><span>产品</span>{h(meta.get('product_name'))}</div>
        <div class="meta-item"><span>日期</span>{h(meta.get('generated_at'))}</div>
        <div class="meta-item"><span>目标市场</span>{h(meta.get('target_market', '未指定'))}</div>
        <div class="meta-item"><span>建议决策</span><span class="decision">{h(decision_label(summary.get('decision', '')))}</span></div>
      </div>
      <div class="score-grid">
        <div class="score-card total-score band-{band}"><span>总分</span><strong>{score(summary.get('total_score'))}</strong></div>
        <div class="score-card"><span>缺乏感</span><strong>{score(summary.get('lack_score'))}</strong></div>
        <div class="score-card"><span>目标物</span><strong>{score(summary.get('target_object_score'))}</strong></div>
        <div class="score-card"><span>消费者能力</span><strong>{score(summary.get('consumer_ability_score'))}</strong></div>
      </div>
    </header>

    <section id="summary">
      <h2>执行摘要</h2>
      <div class="two-col">
        <div class="fact-box"><h3>最大机会</h3><p>{h(summary.get('biggest_opportunity'))}</p></div>
        <div class="fact-box"><h3>最大风险</h3><p>{h(summary.get('biggest_risk'))}</p></div>
      </div>
    </section>

    <section id="product">
      <h2>产品概览</h2>
      <div class="fact-grid">
        <div class="fact-box"><h3>产品定义</h3><p>{h(canvas.get('definition'))}</p></div>
        <div class="fact-box"><h3>价值主张</h3><p>{h(canvas.get('value_proposition'))}</p></div>
        <div class="fact-box"><h3>商业模式</h3><p>{h(canvas.get('business_model'))}</p></div>
        <div class="fact-box"><h3>假设</h3>{html_list(as_list(canvas.get('assumptions')))}</div>
      </div>
      <h3>核心功能</h3>
      {html_list(as_list(canvas.get('features')))}
      <h3>定价信息</h3>
      {html_list(as_list(canvas.get('pricing')))}
    </section>

    <section id="method">
      <h2>研究方法与来源</h2>
      <p>{h(meta.get('source_boundary', '本报告区分事实、假设、证据和建议。'))}</p>
      <figure class="diagram-block">
        {render_process_svg()}
        <figcaption class="figure-caption">图 1：需求评估分析流程。检索只接受可追溯来源，不确定信息进入假设区。</figcaption>
      </figure>
      {html_table(['来源', '等级', '类型', '标题', '链接', '日期'], evidence_rows(report), compact=True)}
    </section>

    <section id="users">
      <h2>目标用户与 JTBD</h2>
      {html_table(['分群', '场景', 'JTBD', '当前替代', '采用阻碍'], segment_rows(report))}
    </section>

    <section id="competitors">
      <h2>竞品与替代方案</h2>
      {html_table(['名称', '类型', '定位', '优势', '弱点', '来源'], competitor_rows(report))}
    </section>

    <section id="triangle">
      <h2>需求三角分析</h2>
      <figure class="diagram-block">
        {render_triangle_svg(report)}
        <figcaption class="figure-caption">图 2：需求三角模型。缺乏感、目标物和消费者能力共同决定需求成立概率。</figcaption>
      </figure>
      <div class="dimension-grid">{''.join(dimension_cards)}</div>
    </section>

    <section id="scores">
      <h2>评分与解释</h2>
      {html_table(['维度', '分数'], score_rows(report), compact=True)}
    </section>

    <section id="recommendations">
      <h2>建议与实验</h2>
      {html_table(['优先级', '领域', '建议', '理由', '预期影响', '成本'], rec_rows)}
      <h3>验证实验</h3>
      {html_table(['假设', '分群', '方法', '指标', '阈值', '决策规则'], experiment_rows(report))}
    </section>

    <section id="risks">
      <h2>风险与伦理</h2>
      {html_table(['严重度', '类型', '风险', '缓释', '来源'], risk_rows(report))}
    </section>

    <section id="appendix">
      <h2>附录</h2>
      <h3>未解问题</h3>
      {html_list(as_list(report.get('open_questions')))}
    </section>
  </main>
</body>
</html>
"""
    return html_doc


def add_docx_table(document: Any, headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
    if not rows:
        document.add_paragraph("未提供")
        return
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    header_cells = table.rows[0].cells
    for index, header in enumerate(headers):
        header_cells[index].text = text(header)
    for row in rows:
        cells = table.add_row().cells
        for index, cell in enumerate(row):
            cells[index].text = text(cell)


def add_docx_bullets(document: Any, items: Sequence[Any]) -> None:
    values = [text(item).strip() for item in items if text(item).strip()]
    if not values:
        document.add_paragraph("未提供")
        return
    for item in values:
        document.add_paragraph(item, style="List Bullet")


def xml_text(value: Any) -> str:
    return html.escape(text(value), quote=False)


def ooxml_paragraph(value: Any, style: str | None = None) -> str:
    style_xml = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{style_xml}<w:r><w:t>{xml_text(value)}</w:t></w:r></w:p>"


def ooxml_bullets(items: Sequence[Any]) -> str:
    values = [text(item).strip() for item in items if text(item).strip()]
    if not values:
        return ooxml_paragraph("未提供")
    return "".join(ooxml_paragraph(f"- {item}") for item in values)


def ooxml_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    if not rows:
        return ooxml_paragraph("未提供")
    table_rows = []
    all_rows = [headers] + [list(row) for row in rows]
    for row in all_rows:
        cells = []
        for cell in row:
            cells.append(
                "<w:tc><w:tcPr><w:tcW w:w=\"2400\" w:type=\"dxa\"/></w:tcPr>"
                f"{ooxml_paragraph(cell)}</w:tc>"
            )
        table_rows.append(f"<w:tr>{''.join(cells)}</w:tr>")
    return (
        "<w:tbl><w:tblPr><w:tblStyle w:val=\"TableGrid\"/>"
        "<w:tblW w:w=\"0\" w:type=\"auto\"/></w:tblPr>"
        f"{''.join(table_rows)}</w:tbl>"
    )


def fallback_docx_parts(body_xml: str) -> Dict[str, str]:
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    {body_xml}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>"""
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:sz w:val="21"/><w:rFonts w:ascii="Times New Roman" w:eastAsia="Songti SC" w:hAnsi="Times New Roman"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="40"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="30"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="26"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="23"/></w:rPr></w:style>
  <w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4" w:color="E8E6DC"/><w:left w:val="single" w:sz="4" w:color="E8E6DC"/><w:bottom w:val="single" w:sz="4" w:color="E8E6DC"/><w:right w:val="single" w:sz="4" w:color="E8E6DC"/><w:insideH w:val="single" w:sz="4" w:color="E8E6DC"/><w:insideV w:val="single" w:sz="4" w:color="E8E6DC"/></w:tblBorders></w:tblPr></w:style>
</w:styles>"""
    return {
        "[Content_Types].xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>""",
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        "word/_rels/document.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>""",
        "word/document.xml": document_xml,
        "word/styles.xml": styles_xml,
    }


def render_docx_fallback(report: Dict[str, Any], output_path: Path) -> None:
    meta = report.get("meta", {})
    summary = report.get("executive_summary", {})
    canvas = report.get("product_canvas", {})
    triangle = report.get("triangle_analysis", {})
    body: List[str] = []

    body.append(ooxml_paragraph(meta.get("title") or meta.get("product_name") or "需求评估报告", "Title"))
    body.append(ooxml_paragraph(summary.get("one_sentence")))
    body.append(ooxml_table(["项目", "结果"], [
        ["产品", meta.get("product_name", "")],
        ["日期", meta.get("generated_at", "")],
        ["目标市场", meta.get("target_market", "")],
        ["建议决策", decision_label(summary.get("decision", ""))],
        ["总分", score(summary.get("total_score"))],
        ["缺乏感", score(summary.get("lack_score"))],
        ["目标物", score(summary.get("target_object_score"))],
        ["消费者能力", score(summary.get("consumer_ability_score"))],
        ["证据信心", summary.get("evidence_confidence", "")],
    ]))

    body.append(ooxml_paragraph("产品概览", "Heading1"))
    body.append(ooxml_paragraph(f"产品定义：{text(canvas.get('definition'))}"))
    body.append(ooxml_paragraph(f"价值主张：{text(canvas.get('value_proposition'))}"))
    body.append(ooxml_paragraph(f"商业模式：{text(canvas.get('business_model'))}"))
    body.append(ooxml_paragraph("核心功能", "Heading2"))
    body.append(ooxml_bullets(as_list(canvas.get("features"))))
    body.append(ooxml_paragraph("定价信息", "Heading2"))
    body.append(ooxml_bullets(as_list(canvas.get("pricing"))))
    body.append(ooxml_paragraph("假设", "Heading2"))
    body.append(ooxml_bullets(as_list(canvas.get("assumptions"))))

    body.append(ooxml_paragraph("研究方法与来源", "Heading1"))
    body.append(ooxml_paragraph(meta.get("source_boundary", "本报告区分事实、假设、证据和建议。")))
    body.append(ooxml_paragraph("图 1：输入 -> 解析 -> 检索 -> 分析 -> 评分 -> 输出。"))
    body.append(ooxml_table(["来源", "等级", "类型", "标题", "链接", "日期"], evidence_rows(report)))

    body.append(ooxml_paragraph("目标用户与 JTBD", "Heading1"))
    body.append(ooxml_table(["分群", "场景", "JTBD", "当前替代", "采用阻碍"], segment_rows(report)))

    body.append(ooxml_paragraph("竞品与替代方案", "Heading1"))
    body.append(ooxml_table(["名称", "类型", "定位", "优势", "弱点", "来源"], competitor_rows(report)))

    body.append(ooxml_paragraph("需求三角分析", "Heading1"))
    body.append(ooxml_paragraph("图 2：缺乏感、目标物和消费者能力共同决定需求成立概率；任一维度明显缺失，总分都会下降。"))
    for key, label in [("lack", "缺乏感"), ("target_object", "目标物"), ("consumer_ability", "消费者能力")]:
        dim = triangle.get(key, {})
        body.append(ooxml_paragraph(f"{label}：{score(dim.get('score'))}", "Heading2"))
        body.append(ooxml_paragraph(f"推理：{text(dim.get('reasoning'))}"))
        body.append(ooxml_paragraph("支持证据", "Heading3"))
        body.append(ooxml_bullets(as_list(dim.get("evidence"))))
        body.append(ooxml_paragraph("反证或缺口", "Heading3"))
        body.append(ooxml_bullets(as_list(dim.get("counter_evidence"))))
        body.append(ooxml_paragraph(f"改进路径：{text(dim.get('improvement_path'))}"))

    body.append(ooxml_paragraph("评分与解释", "Heading1"))
    body.append(ooxml_table(["维度", "分数"], score_rows(report)))

    body.append(ooxml_paragraph("建议与实验", "Heading1"))
    rec_rows = [
        [
            item.get("priority", ""),
            item.get("area", ""),
            item.get("recommendation", ""),
            item.get("rationale", ""),
            item.get("expected_impact", ""),
            item.get("effort", ""),
        ]
        for item in as_list(report.get("recommendations"))
    ]
    body.append(ooxml_table(["优先级", "领域", "建议", "理由", "预期影响", "成本"], rec_rows))
    body.append(ooxml_paragraph("验证实验", "Heading2"))
    body.append(ooxml_table(["假设", "分群", "方法", "指标", "阈值", "决策规则"], experiment_rows(report)))

    body.append(ooxml_paragraph("风险与伦理", "Heading1"))
    body.append(ooxml_table(["严重度", "类型", "风险", "缓释", "来源"], risk_rows(report)))
    body.append(ooxml_paragraph("附录", "Heading1"))
    body.append(ooxml_paragraph("未解问题", "Heading2"))
    body.append(ooxml_bullets(as_list(report.get("open_questions"))))

    parts = fallback_docx_parts("".join(body))
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as package:
        for name, content in parts.items():
            package.writestr(name, content)


def render_docx(report: Dict[str, Any], output_path: Path) -> None:
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError as exc:
        render_docx_fallback(report, output_path)
        return

    meta = report.get("meta", {})
    summary = report.get("executive_summary", {})
    canvas = report.get("product_canvas", {})
    triangle = report.get("triangle_analysis", {})
    document = Document()
    styles = document.styles
    styles["Normal"].font.name = "Songti SC"
    styles["Normal"].font.size = Pt(10.5)

    document.add_heading(text(meta.get("title") or meta.get("product_name") or "需求评估报告"), 0)
    document.add_paragraph(text(summary.get("one_sentence")))
    add_docx_table(document, ["项目", "结果"], [
        ["产品", meta.get("product_name", "")],
        ["日期", meta.get("generated_at", "")],
        ["目标市场", meta.get("target_market", "")],
        ["建议决策", decision_label(summary.get("decision", ""))],
        ["总分", score(summary.get("total_score"))],
        ["缺乏感", score(summary.get("lack_score"))],
        ["目标物", score(summary.get("target_object_score"))],
        ["消费者能力", score(summary.get("consumer_ability_score"))],
        ["证据信心", summary.get("evidence_confidence", "")],
    ])

    document.add_heading("产品概览", 1)
    document.add_paragraph(f"产品定义：{text(canvas.get('definition'))}")
    document.add_paragraph(f"价值主张：{text(canvas.get('value_proposition'))}")
    document.add_paragraph(f"商业模式：{text(canvas.get('business_model'))}")
    document.add_heading("核心功能", 2)
    add_docx_bullets(document, as_list(canvas.get("features")))
    document.add_heading("定价信息", 2)
    add_docx_bullets(document, as_list(canvas.get("pricing")))
    document.add_heading("假设", 2)
    add_docx_bullets(document, as_list(canvas.get("assumptions")))

    document.add_heading("研究方法与来源", 1)
    document.add_paragraph(text(meta.get("source_boundary", "本报告区分事实、假设、证据和建议。")))
    document.add_paragraph("图 1：输入 -> 解析 -> 检索 -> 分析 -> 评分 -> 输出。检索只接受可追溯来源，不确定信息进入假设区。")
    add_docx_table(document, ["来源", "等级", "类型", "标题", "链接", "日期"], evidence_rows(report))

    document.add_heading("目标用户与 JTBD", 1)
    add_docx_table(document, ["分群", "场景", "JTBD", "当前替代", "采用阻碍"], segment_rows(report))

    document.add_heading("竞品与替代方案", 1)
    add_docx_table(document, ["名称", "类型", "定位", "优势", "弱点", "来源"], competitor_rows(report))

    document.add_heading("需求三角分析", 1)
    document.add_paragraph("图 2：需求三角模型。缺乏感、目标物和消费者能力共同决定需求成立概率；任一维度明显缺失，总分都会下降。")
    for key, label in [("lack", "缺乏感"), ("target_object", "目标物"), ("consumer_ability", "消费者能力")]:
        dim = triangle.get(key, {})
        document.add_heading(f"{label}：{score(dim.get('score'))}", 2)
        document.add_paragraph(f"推理：{text(dim.get('reasoning'))}")
        document.add_heading("支持证据", 3)
        add_docx_bullets(document, as_list(dim.get("evidence")))
        document.add_heading("反证或缺口", 3)
        add_docx_bullets(document, as_list(dim.get("counter_evidence")))
        document.add_paragraph(f"改进路径：{text(dim.get('improvement_path'))}")

    document.add_heading("评分与解释", 1)
    add_docx_table(document, ["维度", "分数"], score_rows(report))

    document.add_heading("建议与实验", 1)
    rec_rows = [
        [
            item.get("priority", ""),
            item.get("area", ""),
            item.get("recommendation", ""),
            item.get("rationale", ""),
            item.get("expected_impact", ""),
            item.get("effort", ""),
        ]
        for item in as_list(report.get("recommendations"))
    ]
    add_docx_table(document, ["优先级", "领域", "建议", "理由", "预期影响", "成本"], rec_rows)
    document.add_heading("验证实验", 2)
    add_docx_table(document, ["假设", "分群", "方法", "指标", "阈值", "决策规则"], experiment_rows(report))

    document.add_heading("风险与伦理", 1)
    add_docx_table(document, ["严重度", "类型", "风险", "缓释", "来源"], risk_rows(report))

    document.add_heading("附录", 1)
    document.add_heading("未解问题", 2)
    add_docx_bullets(document, as_list(report.get("open_questions")))

    document.save(output_path)


def render_pdf(html_doc: str, output_path: Path, base_url: Path) -> None:
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError("WeasyPrint is required for PDF output") from exc
    HTML(string=html_doc, base_url=str(base_url)).write_pdf(str(output_path))


def write_outputs(report: Dict[str, Any], outdir: Path, basename: str, formats: Sequence[str]) -> Dict[str, str]:
    outputs: Dict[str, str] = {}
    outdir.mkdir(parents=True, exist_ok=True)
    markdown_doc = render_markdown(report)
    html_doc = render_html(report)

    if "md" in formats:
        md_path = outdir / f"{basename}.md"
        md_path.write_text(markdown_doc, encoding="utf-8")
        outputs["markdown"] = str(md_path)
    if "html" in formats:
        html_path = outdir / f"{basename}.html"
        html_path.write_text(html_doc, encoding="utf-8")
        outputs["html"] = str(html_path)
    if "docx" in formats:
        docx_path = outdir / f"{basename}.docx"
        render_docx(report, docx_path)
        outputs["word"] = str(docx_path)
    if "pdf" in formats:
        pdf_path = outdir / f"{basename}.pdf"
        render_pdf(html_doc, pdf_path, outdir)
        outputs["pdf"] = str(pdf_path)
    return outputs


def parse_formats(value: str) -> List[str]:
    if value == "all":
        return ["md", "html", "docx", "pdf"]
    formats = [item.strip().lower() for item in value.split(",") if item.strip()]
    allowed = {"md", "html", "docx", "pdf"}
    unknown = sorted(set(formats) - allowed)
    if unknown:
        raise ValueError(f"unknown format(s): {', '.join(unknown)}")
    return formats


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a Yao Demand Skill report to four output formats.")
    parser.add_argument("report_json", help="Path to canonical report JSON")
    parser.add_argument("--outdir", default=None, help="Output directory. Defaults to the report JSON directory.")
    parser.add_argument("--basename", default=None, help="Output basename. Defaults to slugified report title.")
    parser.add_argument("--formats", default="all", help="all, or comma list: md,html,docx,pdf")
    parser.add_argument("--skip-validate", action="store_true", help="Skip report validation before rendering")
    args = parser.parse_args()

    report_path = Path(args.report_json).resolve()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    validation = validate_report(report)
    if not args.skip_validate and not validation["ok"]:
        print(json.dumps(validation, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)

    formats = parse_formats(args.formats)
    outdir = Path(args.outdir).resolve() if args.outdir else report_path.parent
    title = report.get("meta", {}).get("title") or report.get("meta", {}).get("product_name") or report_path.stem
    basename = args.basename or slugify(title)
    outputs = write_outputs(report, outdir, basename, formats)
    print(
        json.dumps(
            {
                "ok": True,
                "outputs": outputs,
                "warnings": validation.get("warnings", []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
