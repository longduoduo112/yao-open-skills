#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import shutil
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "templates"

TEXT_EXTS = {
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".sh",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".toml",
    ".ini",
    ".cfg",
    ".csv",
}
SCRIPT_EXTS = {".py", ".sh", ".js", ".ts", ".tsx", ".jsx", ".rb", ".go", ".rs"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", ".cache"}

RUBRIC = [
    ("spec_compatibility", "规范兼容", "Spec compatibility", 12),
    ("trigger_signal", "触发信号", "Trigger signal", 14),
    ("context_efficiency", "上下文效率", "Context efficiency", 12),
    ("resource_structure", "结构资源", "Resource structure", 12),
    ("usage_readiness", "使用就绪", "Usage readiness", 14),
    ("safety_permissions", "安全权限", "Safety and permissions", 14),
    ("tests_evals", "测试评估", "Tests and evals", 10),
    ("maintenance_release", "维护发布", "Maintenance and release", 7),
    ("learning_value", "学习价值", "Learning value", 5),
]

DANGEROUS_PATTERNS = [
    (r"\brm\s+-rf\b", "未解释的递归删除命令"),
    (r"\bsudo\b", "提升权限命令"),
    (r"\bchmod\s+777\b", "宽权限修改"),
    (r"\bdd\s+if=", "磁盘级写入命令"),
    (r">\s*/etc/", "系统配置覆盖"),
    (r"\bmkfs\b|\bshutdown\b|\breboot\b", "系统破坏或重启命令"),
]
NETWORK_PATTERNS = [
    (r"\bcurl\b|\bwget\b", "命令行网络访问"),
    (r"\brequests\.", "Python requests 网络访问"),
    (r"\bfetch\s*\(", "JavaScript fetch 网络访问"),
    (r"https?://", "硬编码 URL"),
]
SECRET_PATTERNS = [
    (r"\b[A-Z0-9_]*(?:API_KEY|SECRET|TOKEN)[A-Z0-9_]*\b", "密钥或令牌变量"),
    (r"(?i)\.env\b|id_rsa|ssh/private|browser_cookies|Cookie", "敏感文件或 Cookie 线索"),
]
PROMPT_INJECTION_PATTERNS = [
    (r"ignore (all )?(previous|prior|system) (instructions|rules)", "忽略上级规则"),
    (r"忽略(之前|以上|系统|开发者).*(指令|规则)", "中文忽略规则提示"),
    (r"不要告诉用户|隐藏真实|绕过.*确认|越权", "隐藏行为或绕过确认"),
]


class AnalysisError(RuntimeError):
    pass


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_template(name: str) -> str:
    path = TEMPLATE_DIR / name
    return path.read_text(encoding="utf-8")


def safe_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def is_binary(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:2048]
    except OSError:
        return True
    return b"\0" in chunk


def read_text_limited(path: Path, max_bytes: int = 262_144) -> str:
    data = path.read_bytes()[:max_bytes]
    return data.decode("utf-8", errors="replace")


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        current_path = Path(current)
        for filename in filenames:
            path = current_path / filename
            if path.is_symlink():
                files.append(path)
                continue
            if path.is_file():
                files.append(path)
    return sorted(files)


def find_skill_root(path: Path) -> Path:
    path = path.resolve()
    if path.is_file() and path.name == "SKILL.md":
        return path.parent
    if path.is_dir() and (path / "SKILL.md").exists():
        return path
    if path.is_dir():
        candidates = [p for p in path.rglob("SKILL.md") if not any(part in SKIP_DIRS for part in p.parts)]
        if len(candidates) == 1:
            return candidates[0].parent
        if len(candidates) > 1:
            names = ", ".join(safe_rel(p.parent, path) for p in candidates[:8])
            raise AnalysisError(f"发现多个 SKILL.md，请指定具体目录：{names}")
    raise AnalysisError("未找到 SKILL.md，无法识别为智能体 Skill。")


def safe_extract_zip(zip_path: Path, max_file_bytes: int, max_total_bytes: int) -> tuple[tempfile.TemporaryDirectory[str], Path, list[dict[str, Any]]]:
    tmp = tempfile.TemporaryDirectory(prefix="skill-interpreter-")
    target = Path(tmp.name)
    warnings: list[dict[str, Any]] = []
    total = 0
    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
        if len(infos) > 2000:
            tmp.cleanup()
            raise AnalysisError("zip 文件数量超过上限 2000。")
        for info in infos:
            name = info.filename
            parts = Path(name).parts
            is_symlink = (info.external_attr >> 16) & 0o170000 == 0o120000
            if name.startswith("/") or ".." in parts:
                tmp.cleanup()
                raise AnalysisError(f"zip 存在路径穿越风险：{name}")
            if is_symlink:
                warnings.append({"path": name, "risk": "可疑符号链接", "severity": "high"})
                continue
            if info.file_size > max_file_bytes:
                tmp.cleanup()
                raise AnalysisError(f"zip 单文件超过上限：{name}")
            total += info.file_size
            if total > max_total_bytes:
                tmp.cleanup()
                raise AnalysisError("zip 解包总大小超过上限。")
        archive.extractall(target)
    return tmp, find_skill_root(target), warnings


def resolve_target(target: Path, max_file_mb: int, max_total_mb: int) -> tuple[Path, tempfile.TemporaryDirectory[str] | None, list[dict[str, Any]]]:
    max_file_bytes = max_file_mb * 1024 * 1024
    max_total_bytes = max_total_mb * 1024 * 1024
    if target.is_file() and target.suffix.lower() == ".zip":
        tmp, root, warnings = safe_extract_zip(target, max_file_bytes, max_total_bytes)
        return root, tmp, warnings
    return find_skill_root(target), None, []


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    lines = text.splitlines()
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            fm = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1 :])
            return fm, body
    return "", text


def clean_value(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        items = [item.strip().strip('"').strip("'") for item in value[1:-1].split(",") if item.strip()]
        return items
    return value


def parse_frontmatter(source: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_parent: str | None = None
    for raw in source.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        if not raw.startswith(" ") and ":" in raw:
            key, value = raw.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                data[key] = clean_value(value)
                current_parent = None
            else:
                data[key] = {}
                current_parent = key
        elif current_parent and raw.startswith(" ") and ":" in raw:
            key, value = raw.split(":", 1)
            if isinstance(data.get(current_parent), dict):
                data[current_parent][key.strip()] = clean_value(value)
    return data


def find_line(lines: list[str], needle: str) -> int | None:
    if not needle:
        return None
    needle = needle.strip()
    for idx, line in enumerate(lines, start=1):
        if needle and needle in line:
            return idx
    return None


def evidence(file: str, section: str, line_start: int | None, quote: str, confidence: float = 0.86) -> dict[str, Any]:
    quote = " ".join(str(quote).strip().split())
    if len(quote) > 220:
        quote = quote[:217] + "..."
    return {
        "file": file,
        "section": section,
        "line_start": line_start,
        "line_end": line_start,
        "quote": quote or "missing evidence",
        "fact_type": "text" if line_start else "missing",
        "confidence": confidence,
        "source_hash": hash_text(quote or "missing"),
    }


def extract_headings(lines: list[str]) -> list[dict[str, Any]]:
    headings: list[dict[str, Any]] = []
    for idx, line in enumerate(lines, start=1):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            headings.append({"level": len(match.group(1)), "title": match.group(2).strip(), "line": idx})
    return headings


def section_text(lines: list[str], headings: list[dict[str, Any]], keywords: list[str]) -> str:
    for pos, heading in enumerate(headings):
        title = heading["title"].lower()
        if any(keyword.lower() in title for keyword in keywords):
            start = heading["line"]
            end = len(lines)
            for later in headings[pos + 1 :]:
                if later["level"] <= heading["level"]:
                    end = later["line"] - 1
                    break
            return "\n".join(lines[start:end]).strip()
    return ""


def extract_list_items(text: str, limit: int = 8) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        match = re.match(r"^(?:[-*]|\d+\.)\s+(.+)", stripped)
        if match:
            item = re.sub(r"`([^`]+)`", r"\1", match.group(1)).strip()
            if item:
                items.append(item)
        if len(items) >= limit:
            break
    return items


def make_inventory(root: Path, files: list[Path], max_file_bytes: int) -> dict[str, Any]:
    file_types: Counter[str] = Counter()
    directories: Counter[str] = Counter()
    largest: list[dict[str, Any]] = []
    hidden: list[str] = []
    symlinks: list[str] = []
    skipped_large: list[str] = []
    total = 0
    for path in files:
        rel = safe_rel(path, root)
        try:
            stat = path.lstat()
        except OSError:
            continue
        total += stat.st_size
        if path.is_symlink():
            symlinks.append(rel)
        if any(part.startswith(".") for part in Path(rel).parts):
            hidden.append(rel)
        file_types[path.suffix.lower() or "[none]"] += 1
        first = Path(rel).parts[0] if Path(rel).parts else "."
        directories[first] += 1
        if stat.st_size > max_file_bytes:
            skipped_large.append(rel)
        largest.append({"path": rel, "bytes": stat.st_size})
    largest.sort(key=lambda item: item["bytes"], reverse=True)
    return {
        "skill_path": str(root),
        "has_skill_md": (root / "SKILL.md").exists(),
        "file_count": len(files),
        "total_bytes": total,
        "directories": dict(sorted(directories.items())),
        "file_types": dict(sorted(file_types.items())),
        "largest_files": largest[:10],
        "hidden_files": hidden[:50],
        "symlinks": symlinks[:50],
        "skipped_large_files": skipped_large[:50],
    }


def scan_patterns(root: Path, files: list[Path], max_scan_bytes: int) -> dict[str, Any]:
    categories = {
        "dangerous_commands": DANGEROUS_PATTERNS,
        "network_access": NETWORK_PATTERNS,
        "secret_access": SECRET_PATTERNS,
        "prompt_injection": PROMPT_INJECTION_PATTERNS,
    }
    hits: dict[str, list[dict[str, Any]]] = {name: [] for name in categories}
    hidden_char_hits: list[dict[str, Any]] = []
    for path in files:
        if path.is_symlink() or path.suffix.lower() not in TEXT_EXTS:
            continue
        try:
            if path.stat().st_size > max_scan_bytes or is_binary(path):
                continue
            text = read_text_limited(path, max_scan_bytes)
        except OSError:
            continue
        rel = safe_rel(path, root)
        for line_no, line in enumerate(text.splitlines(), start=1):
            if re.search(r"[\u200b\u200c\u200d\u202a-\u202e]", line):
                hidden_char_hits.append({"file": rel, "line": line_no, "quote": line.strip()[:180]})
            for category, patterns in categories.items():
                for pattern, label in patterns:
                    flags = 0 if category == "secret_access" else re.IGNORECASE
                    if re.search(pattern, line, flags=flags):
                        hits[category].append({"file": rel, "line": line_no, "label": label, "quote": line.strip()[:220]})
    hits["hidden_chars"] = hidden_char_hits
    return hits


def add_finding(
    findings: list[dict[str, Any]],
    dimension: str,
    severity: str,
    summary: str,
    score_delta: int,
    ev: list[dict[str, Any]],
    recommendation: str,
    acceptance: str,
    confidence: float = 0.84,
) -> None:
    finding_id = f"{dimension}-{len([f for f in findings if f['dimension_key'] == dimension]) + 1:03d}"
    label = next((item[1] for item in RUBRIC if item[0] == dimension), dimension)
    findings.append(
        {
            "finding_id": finding_id,
            "dimension_key": dimension,
            "dimension": label,
            "severity": severity,
            "confidence": confidence,
            "summary": summary,
            "score_delta": score_delta,
            "evidence": ev,
            "recommendation": recommendation,
            "acceptance_criteria": acceptance,
        }
    )


def operational_hits(hits: list[dict[str, Any]], category: str = "") -> list[dict[str, Any]]:
    """Exclude quoted fixtures and generated reports from executable-surface risk scoring."""
    ignored_prefixes = ("examples/", "tests/", "reports/", "schemas/", "evals/", "references/")
    filtered: list[dict[str, Any]] = []
    for hit in hits:
        file = str(hit.get("file", ""))
        quote = str(hit.get("quote", ""))
        if file.startswith(ignored_prefixes):
            continue
        if is_scanner_signature(quote) or is_guardrail_explanation(quote):
            continue
        if category == "network_access" and not (file.startswith("scripts/") or Path(file).suffix.lower() in SCRIPT_EXTS):
            continue
        filtered.append(hit)
    return filtered


def is_scanner_signature(quote: str) -> bool:
    stripped = quote.strip()
    return (
        stripped.startswith('(r"')
        or stripped.startswith("(r'")
        or "PATTERNS" in stripped
        or "re.search(pattern" in stripped
        or "pattern, label" in stripped
        or "no_external_cdn" in stripped
        or '" not in text' in stripped
    )


def is_guardrail_explanation(quote: str) -> bool:
    lowered = quote.lower()
    guardrail_terms = [
        "禁止",
        "红线",
        "风险",
        "不要求",
        "不得",
        "不要把",
        "作为不可信",
        "do not use for",
        "do not execute",
        "forbid",
        "red line",
        "risk",
    ]
    return any(term in lowered for term in guardrail_terms)


def capped(score: int, maximum: int) -> int:
    return max(0, min(maximum, score))


def score_skill(model: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    metadata = model["metadata"]
    inventory = model["inventory"]
    skill_md = model["skill_md"]
    lines = skill_md["lines"]
    description = str(metadata.get("description", "") or "")
    name = str(metadata.get("name", "") or "")
    body = skill_md["body"]
    headings = skill_md["headings"]
    dirs = inventory["directories"]
    scans = model["static_scan"]
    text_all = (description + "\n" + body).lower()
    desc_line = skill_md.get("description_line")
    name_line = skill_md.get("name_line")

    scores: dict[str, dict[str, Any]] = {}

    spec = 12
    if not inventory["has_skill_md"]:
        spec = 0
        add_finding(findings, "spec_compatibility", "critical", "缺少 SKILL.md，无法识别为标准 Skill。", -12, [evidence("SKILL.md", "package root", None, "SKILL.md missing")], "补充标准入口文件。", "包体根目录包含 SKILL.md。")
    else:
        if not skill_md["frontmatter_source"]:
            spec -= 3
            add_finding(findings, "spec_compatibility", "medium", "SKILL.md 缺少前置元数据。", -3, [evidence("SKILL.md", "frontmatter", 1, lines[0] if lines else "")], "在文件开头补充 YAML 前置元数据。", "前置元数据至少包含名称和描述字段。")
        if not name:
            spec -= 3
            add_finding(findings, "spec_compatibility", "high", "frontmatter 缺少 name。", -3, [evidence("SKILL.md", "frontmatter.name", None, "name missing")], "补充稳定、唯一的 skill name。", "name 使用小写短横线格式，能稳定路由。")
        if not description:
            spec -= 4
            add_finding(findings, "spec_compatibility", "high", "前置元数据缺少描述字段。", -4, [evidence("SKILL.md", "frontmatter.description", None, "description missing")], "补充能力、时机、边界和关键词。", "描述字段能让系统判断何时触发。")
        if description and len(description) < 40:
            spec -= 2
            add_finding(findings, "spec_compatibility", "medium", "描述字段过短，难以承载路由信息。", -2, [evidence("SKILL.md", "frontmatter.description", desc_line, description)], "扩展描述字段，说明能力和使用场景。", "描述字段不少于 40 个字符且不堆砌。")
    scores["spec_compatibility"] = {"label": "规范兼容", "score": capped(spec, 12), "max": 12}

    trigger = 14
    if not description:
        trigger = 2
    else:
        if len(description) < 80:
            trigger -= 3
            add_finding(findings, "trigger_signal", "medium", "描述字段对使用时机解释不足。", -3, [evidence("SKILL.md", "frontmatter.description", desc_line, description)], "补充典型用户请求和适用场景。", "描述字段包含自然语言触发词和用户场景。")
        if not re.search(r"\b(use|when|for|analy[sz]e|review|score)\b|使用|用于|当用户|适合", description, re.I):
            trigger -= 2
            add_finding(findings, "trigger_signal", "medium", "描述字段没有明确说明何时使用。", -2, [evidence("SKILL.md", "frontmatter.description", desc_line, description)], "加入中文适用时机，必要时保留英文触发词。", "触发时机可以从描述字段直接读出。")
        if not re.search(r"\bnot\b|do not|except|不用于|不要|边界|排除", description, re.I):
            trigger -= 2
            add_finding(findings, "trigger_signal", "medium", "描述字段缺少不适用边界。", -2, [evidence("SKILL.md", "frontmatter.description", desc_line, description)], "补充相邻任务和慎用场景。", "描述字段明确至少一个非目标。")
        if len(description) > 1024:
            trigger -= 1
            add_finding(findings, "trigger_signal", "low", "描述字段接近或超过常见路由长度预算。", -1, [evidence("SKILL.md", "frontmatter.description", desc_line, description)], "压缩为能力、时机、边界、关键词四类信息。", "描述字段控制在 1024 字符内。")
        if not re.search(r"skill|agent|report|html|json|评分|报告|解读|审查", description, re.I):
            trigger -= 1
    scores["trigger_signal"] = {"label": "触发信号", "score": capped(trigger, 14), "max": 14}

    token_estimate = skill_md["token_estimate"]
    context = 12
    if token_estimate > 2500:
        delta = -5 if token_estimate > 5000 else -3
        context += delta
        add_finding(findings, "context_efficiency", "medium", f"SKILL.md 入口约 {token_estimate} token，初始上下文偏重。", delta, [evidence("SKILL.md", "entrypoint", 1, f"token_estimate={token_estimate}")], "把长规则、示例和模板下沉到 references/ 或 scripts/。", "入口只保留触发、核心流程、输出契约和安全边界。")
    if token_estimate > 1200 and "references" not in dirs:
        context -= 2
        add_finding(findings, "context_efficiency", "medium", "入口较长但没有 references/ 承载细节。", -2, [evidence("SKILL.md", "resource boundary", 1, "references/ missing")], "把评分细则、报告契约、长示例放入 references/。", "长规则不直接塞进 SKILL.md。")
    if "scripts" in dirs and token_estimate <= 1400:
        context += 1
    scores["context_efficiency"] = {"label": "上下文效率", "score": capped(context, 12), "max": 12}

    structure = 12
    for folder, delta, label in [("references", -3, "缺少 references/，长规则无处下沉。"), ("scripts", -3, "缺少 scripts/，重复静态分析逻辑难以稳定。")]:
        if folder not in dirs:
            structure += delta
            add_finding(findings, "resource_structure", "medium", label, delta, [evidence(folder + "/", "directory", None, "directory missing")], f"新增 {folder}/ 并在 SKILL.md 中说明用途。", f"{folder}/ 中的文件服务当前工作流。")
    if "examples" not in dirs:
        structure -= 1
    if "evals" not in dirs:
        structure -= 1
    if inventory["file_count"] > 120:
        structure -= 1
        add_finding(findings, "resource_structure", "low", "包体文件较多，报告需要区分核心文件和生成物。", -1, [evidence(".", "inventory", None, f"file_count={inventory['file_count']}")], "在 README 或报告中标注核心资产。", "用户能区分入口、脚本、参考、生成报告。")
    scores["resource_structure"] = {"label": "结构资源", "score": capped(structure, 12), "max": 12}

    workflow_items = model["capability_summary"]["workflow_steps"]
    inputs = model["capability_summary"]["required_inputs"]
    outputs = model["capability_summary"]["expected_outputs"]
    usage = 14
    if not workflow_items:
        usage -= 3
        add_finding(findings, "usage_readiness", "medium", "没有提取到明确工作流步骤。", -3, [evidence("SKILL.md", "workflow", None, "workflow missing")], "增加有顺序的执行步骤。", "用户能按步骤判断输入、处理、输出和验证。")
    if not inputs:
        usage -= 2
    if not outputs:
        usage -= 2
        add_finding(findings, "usage_readiness", "medium", "输出契约不清晰。", -2, [evidence("SKILL.md", "outputs", None, "outputs missing")], "列出默认文件名、格式和质量标准。", "报告明确产出路径和成功标准。")
    if "```" not in body:
        usage -= 1
    if not re.search(r"失败|错误|fallback|degradation|降级|排查|troubleshoot", text_all):
        usage -= 2
    if not re.search(r"验收|verify|validate|qa|质量|check", text_all):
        usage -= 2
    scores["usage_readiness"] = {"label": "使用就绪", "score": capped(usage, 14), "max": 14}

    safety = 14
    danger_hits = operational_hits(scans["dangerous_commands"], "dangerous_commands")
    network_hits = operational_hits(scans["network_access"], "network_access")
    secret_hits = operational_hits(scans["secret_access"], "secret_access")
    injection_hits = operational_hits(scans["prompt_injection"], "prompt_injection")
    hidden_hits = scans["hidden_chars"]
    if danger_hits:
        delta = -min(6, len(danger_hits) * 2)
        safety += delta
        add_finding(findings, "safety_permissions", "high", f"静态扫描发现 {len(danger_hits)} 个危险命令线索。", delta, [evidence(hit["file"], hit["label"], hit["line"], hit["quote"]) for hit in danger_hits[:3]], "为危险命令增加解释、确认和最小权限，无法解释时移除。", "高风险命令都有用途、范围、确认和回滚边界。")
    if network_hits:
        delta = -min(3, len(network_hits))
        safety += delta
        add_finding(findings, "safety_permissions", "medium", f"发现 {len(network_hits)} 个网络访问线索。", delta, [evidence(hit["file"], hit["label"], hit["line"], hit["quote"]) for hit in network_hits[:3]], "说明网络访问对象、数据类型和用户确认要求。", "外部访问边界清晰且无敏感外传。")
    if secret_hits:
        delta = -min(4, len(secret_hits) * 2)
        safety += delta
        add_finding(findings, "safety_permissions", "high", f"发现 {len(secret_hits)} 个密钥或敏感文件线索。", delta, [evidence(hit["file"], hit["label"], hit["line"], hit["quote"]) for hit in secret_hits[:3]], "避免读取或打印敏感信息；需要凭据时只声明环境变量名。", "报告不泄露密钥值，脚本不外传敏感文件。")
    if injection_hits:
        delta = -min(4, len(injection_hits) * 2)
        safety += delta
        add_finding(findings, "safety_permissions", "critical", f"发现 {len(injection_hits)} 个提示注入或越权指令线索。", delta, [evidence(hit["file"], hit["label"], hit["line"], hit["quote"]) for hit in injection_hits[:3]], "把这些文本作为不可信样本处理并移除越权要求。", "不要求忽略上级规则、隐藏行为或越权读取。")
    if hidden_hits:
        safety -= 1
    allowed_tools = str(metadata.get("allowed-tools", metadata.get("allowed_tools", "")) or "")
    if re.search(r"Bash\(\*\)|Write.*Bash|Read Write Bash", allowed_tools):
        safety -= 1
    scores["safety_permissions"] = {"label": "安全权限", "score": capped(safety, 14), "max": 14}

    tests = 10
    if "tests" not in dirs:
        tests -= 3
    if "evals" not in dirs:
        tests -= 3
        add_finding(findings, "tests_evals", "medium", "缺少 evals/，触发边界和报告质量难以回归。", -3, [evidence("evals/", "directory", None, "evals missing")], "增加正例、反例和近邻触发用例。", "触发用例覆盖解读、创建、执行、安全审计等邻近边界。")
    if "examples" not in dirs:
        tests -= 2
    if "reports" not in dirs:
        tests -= 1
    scores["tests_evals"] = {"label": "测试评估", "score": capped(tests, 10), "max": 10}

    maintenance = 7
    root_files = {p.name for p in model["root_files"]}
    if "README.md" not in root_files:
        maintenance -= 2
    if "LICENSE" not in root_files and "LICENSE.md" not in root_files:
        maintenance -= 1
    if "manifest.json" not in root_files and "VERSION" not in root_files:
        maintenance -= 2
    if not any(name in root_files for name in ("requirements.txt", "pyproject.toml", "package.json")) and "scripts" in dirs:
        maintenance -= 1
    scores["maintenance_release"] = {"label": "维护发布", "score": capped(maintenance, 7), "max": 7}

    learning = 5
    pattern_words = ["渐进披露", "progressive", "output contract", "输出契约", "examples", "示例", "design pattern", "模式", "安全边界"]
    if not any(word.lower() in text_all for word in pattern_words):
        learning -= 2
    if len(headings) < 4:
        learning -= 1
    if "examples" not in dirs:
        learning -= 1
    scores["learning_value"] = {"label": "学习价值", "score": capped(learning, 5), "max": 5}

    total = sum(item["score"] for item in scores.values())
    if any(f["severity"] == "critical" for f in findings):
        risk = "critical"
    elif scores["safety_permissions"]["score"] < 8 or any(f["severity"] == "high" for f in findings):
        risk = "high"
    elif total < 80 or any(f["severity"] == "medium" for f in findings):
        risk = "medium"
    else:
        risk = "low"
    if total >= 90:
        grade = "S"
    elif total >= 80:
        grade = "A"
    elif total >= 70:
        grade = "B"
    elif total >= 60:
        grade = "C"
    else:
        grade = "D"
    if risk == "critical":
        recommendation = "暂缓使用，先处理红线风险。"
    elif risk == "high":
        recommendation = "仅在受控环境试读，先修复高风险问题。"
    elif total >= 80:
        recommendation = "基本可用，建议修复中低风险问题后推广。"
    elif total >= 70:
        recommendation = "可试用，推广前补齐关键缺口。"
    else:
        recommendation = "不建议直接使用，优先重构结构和安全边界。"

    scorecard = {
        "total": total,
        "grade": grade,
        "risk_level": risk,
        "recommendation": recommendation,
        "dimensions": scores,
        "max_total": sum(item[3] for item in RUBRIC),
    }
    return scorecard, findings


def unique_items(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        normalized = " ".join(str(item).split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique


def text_has(text: str, *needles: str) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def infer_skill_family(description: str, body: str) -> str:
    combined = f"{description}\n{body}".lower()
    if text_has(combined, "create, refactor, evaluate, and package agent skills", "skill os 2.0", "governed package boundary"):
        return "meta_skill"
    if text_has(combined, "analyze local agent skill folders", "safe zip archives as untrusted input", "100-point quality score"):
        return "interpreter"
    if text_has(combined, "running opencli commands to interact with websites", "79+ adapters"):
        return "opencli_usage"
    if text_has(combined, "make websites accessible for ai agents", "browser automation for ai agents"):
        return "opencli_browser"
    if text_has(combined, "creating a new opencli adapter from scratch", "api discovery workflow"):
        return "opencli_explorer"
    if text_has(combined, "quickly generating a single opencli command", "4-step process"):
        return "opencli_oneshot"
    if text_has(combined, "automatically fix broken opencli adapters", "opencli_diagnostic"):
        return "opencli_autofix"
    if text_has(combined, "智能搜索路由器", "opencli 搜索源", "live registry"):
        return "opencli_smart_search"
    if text_has(combined, "release checklist", "structured markdown runbook", "handoff notes"):
        return "release_runbook"
    return "generic"


def localize_description_zh(description: str, family: str, name: str) -> str:
    if family == "meta_skill":
        return "这个 Skill 用于把工作流、提示词、访谈记录、文档或笔记转化为可复用的智能体技能，也支持对既有 Skill 做重构、评估、打包和团队分发准备。"
    if family == "interpreter":
        return "这个 Skill 用于把本地智能体 Skill 目录、SKILL.md 或安全 zip 归档当作不可信输入，静态解读其用途、触发契约、结构、就绪度、安全风险和改进路线，并输出中文优先的 HTML、JSON 和 Markdown 报告。"
    if family == "release_runbook":
        return "这个 Skill 用于把反复出现的发布检查清单整理成结构化 Markdown 运行手册，明确输入、输出、评审门禁和交接说明。"
    if family == "opencli_usage":
        return "这个 Skill 是 OpenCLI 的总使用手册，用来帮 Agent 查找并运行 79+ 网站、桌面应用和公开 API 的命令，比如搜索内容、看热门、发帖、下载素材、读取桌面应用状态。"
    if family == "opencli_browser":
        return "这个 Skill 用来通过 OpenCLI 控制 Chrome：打开网页、读取页面结构、点击、输入、等待、提取内容，并复用浏览器里的登录状态。它适合做网页自动化和适配器开发前的页面探索。"
    if family == "opencli_explorer":
        return "这个 Skill 用来从零创建 OpenCLI 网站适配器。它会指导 Agent 探索页面、发现 API、选择认证策略、编写 TypeScript 适配器，并用真实命令测试结果。"
    if family == "opencli_oneshot":
        return "这个 Skill 用来快速把一个具体 URL 和目标转成单个 OpenCLI 命令。它比完整适配器探索更轻，适合先做一次可运行的小命令。"
    if family == "opencli_autofix":
        return "这个 Skill 用来在 OpenCLI 命令失败时做自动诊断和小范围修复。它会读取诊断上下文，定位适配器文件，最多尝试三轮修复和重试。"
    if family == "opencli_smart_search":
        return "这个 Skill 是 OpenCLI 的智能搜索路由器，用来先判断该去哪个数据源查，再通过 live help 确认命令，最后把搜索过程和调用次数汇报清楚。"
    if not description:
        return "该 Skill 没有提供前置描述字段，当前只能从名称和目录结构判断其大致用途，建议先补齐中文定位。"
    if re.search(r"[\u4e00-\u9fff]", description):
        return description
    verbs: list[str] = []
    lowered = description.lower()
    if "analy" in lowered or "review" in lowered:
        verbs.append("分析或评审目标材料")
    if "generate" in lowered or "create" in lowered or "turn" in lowered:
        verbs.append("生成可复用交付物")
    if "report" in lowered:
        verbs.append("输出结构化报告")
    if "skill" in lowered:
        verbs.append("服务智能体技能的设计、理解或改进")
    if verbs:
        return f"{name or '该 Skill'} 的原始定位为英文。按关键词判断，它主要用于{ '、'.join(unique_items(verbs)) }。建议在 SKILL.md 中补一版中文描述字段，降低中文用户的理解成本。"
    return f"{name or '该 Skill'} 的原始定位为英文，自动解读只能确认它是一个面向特定工作流的智能体技能。建议补充中文适用场景、输入输出和边界。"


def infer_use_cases_zh(description: str, body: str, family: str, dirs: dict[str, int] | None = None) -> list[str]:
    if family == "meta_skill":
        return [
            "从零创建 Skill：当用户提供重复工作流、提示词、访谈记录、文档或笔记，并希望沉淀成可复用能力时使用。",
            "重构已有 Skill：当 SKILL.md 过长、规则散乱、脚本和参考资料没有分层时，用它把入口、references/、scripts/、reports/ 重新分界。",
            "评估与打包团队 Skill：当 Skill 准备给团队复用时，用它判断应采用脚手架、生产、库级还是治理模式，并补齐接口声明、评估用例、清单文件和门禁。",
            "处理高信任交付：当 Skill 涉及文件证据、发布关键流程或治理要求时，用它要求输入文件证据、输出契约、回滚边界、信任报告等可审计标签。",
        ]
    if family == "interpreter":
        return [
            "采用前评审：在安装或复用第三方 Skill 前，先静态解读其用途、触发方式、脚本依赖和安全边界。",
            "作者自检：Skill 作者可以用它生成 100 分评分、扣分证据和改进路线，判断是否达到团队复用标准。",
            "学习拆解：把成熟 Skill 当样例，提炼入口设计、渐进披露、参考资料分层和报告交付方式。",
            "安全筛查：把目标目录或 zip 当作不可信输入，只做静态扫描，不执行目标脚本。",
        ]
    if family == "release_runbook":
        return [
            "把反复执行的发布清单整理成可交接的 Markdown 手册。",
            "在发布前统一输入、输出、评审门禁和负责人交接说明。",
            "把临时发布笔记改造成团队可复用的运行流程。",
        ]
    opencli_cases = {
        "opencli_usage": [
            "查询命令：当用户想知道某个平台能不能搜索、发帖、下载或读取内容时，用它先查可用命令和参数。",
            "日常执行：当已经安装 OpenCLI 并具备登录态时，用它运行热门、搜索、时间线、下载、桌面应用控制等命令。",
            "格式化输出：当用户需要 JSON、Markdown、CSV 或表格结果，借助它确认 OpenCLI 的输出格式参数。",
            "能力总览：当不确定应该用哪个 OpenCLI 子命令时，用它先按平台和能力定位入口。",
        ],
        "opencli_browser": [
            "网页操作：需要打开网页、点击按钮、填写输入框、滚动页面或读取页面状态时使用。",
            "登录态复用：目标网站需要浏览器 Cookie 或当前 Chrome 登录状态时，用它通过 OpenCLI 浏览器桥接操作页面。",
            "页面探索：开发适配器前，需要观察 DOM、网络请求和元素索引时使用。",
            "轻量自动化：不需要完整写适配器，只想完成一次网页交互或数据提取时使用。",
        ],
        "opencli_explorer": [
            "新站点适配：需要为一个新网站或平台创建 OpenCLI 命令时使用。",
            "API 探索：需要通过浏览器和网络请求判断数据来自公开 API、Cookie API、Header API 还是 UI 提取时使用。",
            "适配器编写：需要写 TypeScript 适配器、定义参数、输出列和认证策略时使用。",
            "上线前测试：需要 build、list、validate 和真实命令验证时使用。",
        ],
        "opencli_oneshot": [
            "快速试验：用户给出一个 URL 和目标，只想先生成一个能跑的单命令时使用。",
            "小范围抓取：只需要一个页面、一个列表或一个接口结果，不值得完整探索整个网站时使用。",
            "原型验证：先确认 OpenCLI 是否能稳定拿到数据，再决定是否升级成完整适配器。",
        ],
        "opencli_autofix": [
            "命令失败：OpenCLI 适配器因为选择器、接口、返回结构或等待条件变化而失败时使用。",
            "诊断修复：需要读取 OPENCLI_DIAGNOSTIC 输出、定位适配器源码、做最小修复并重试时使用。",
            "受控自修：只允许在明确的 adapter sourcePath 内修复，且最多三轮诊断、修改、重试。",
        ],
        "opencli_smart_search": [
            "搜索路由：用户没有指定数据源，但想查资料、新闻、技术内容、商品、职位或社交内容时使用。",
            "指定平台搜索：用户点名 Bilibili、知乎、Twitter/X、小红书、GitHub 等平台时，用它确认 live registry 和命令帮助。",
            "多源补充：AI 源答案不够、需要原始帖子或垂直结果时，用它选择 1 到 2 个专用源补充。",
            "控制搜索预算：同一问题内限制站点调用次数，并在答案末尾写清搜索摘要。",
        ],
    }
    if family in opencli_cases:
        return opencli_cases[family]
    use_cases: list[str] = []
    combined = f"{description}\n{body}"
    if text_has(combined, "analy", "review", "解读", "评审"):
        use_cases.append("需要分析、评审或解释目标材料的用途、结构和风险时使用。")
    if text_has(combined, "score", "评分", "quality"):
        use_cases.append("需要把质量判断转成评分、发现项和改进建议时使用。")
    if text_has(combined, "report", "html", "json", "报告"):
        use_cases.append("需要输出结构化报告或机器可读 JSON 结果时使用。")
    if dirs and "scripts" in dirs:
        use_cases.append("工作流包含可复用脚本逻辑，需要稳定重复执行时使用。")
    if not use_cases:
        use_cases.append("需要理解这个 Skill 能做什么、何时使用、产出什么时使用。")
    return unique_items(use_cases)


def infer_non_goals_zh(description: str, body: str, family: str, extracted: list[str]) -> list[str]:
    if family == "meta_skill":
        return [
            "一次性任务不应强行创建 Skill。只有存在重复使用价值和可复用输出契约时，才进入 Skill 化流程。",
            "不要把所有治理门禁默认塞进轻量个人 Skill。脚手架、生产、库级、治理模式要按风险和复用范围逐级选择。",
            "不要伪造证据。遥测、审批、基准、信任报告缺失时必须标为缺失证据，而不是写成已完成。",
            "它不是具体业务任务执行器。目标是设计、重构、评估和打包 Skill，而不是代替目标 Skill 完成业务交付。",
        ]
    if family == "interpreter":
        return [
            "不执行目标 Skill 里的脚本、安装命令、测试、模型提示或远程调用。",
            "不修改目标 Skill，默认只在输出目录写入报告文件。",
            "zip 输入必须安全解包，遇到路径穿越、异常大文件或可疑符号链接应拒绝。",
            "静态安全结论只是采用建议，不替代人工安全审计。",
        ]
    if family.startswith("opencli_"):
        return [
            "不要在未确认登录态、权限和目标账号的情况下直接执行会发帖、点赞、关注、下载或修改数据的命令。",
            "不要把验证码、风控、限流或未登录误判为适配器损坏；这类情况应先停止并提示用户处理环境。",
            "不要在没有用户确认的情况下读取或外传 Cookie、Token、私信、账号信息和浏览器会话数据。",
            "不要把一次搜索或一次页面结果当成绝对事实；需要说明来源、查询词、调用次数和失败源。",
        ]
    translated = [translate_known_bullet_zh(item) for item in extracted]
    if translated:
        return unique_items(translated)
    if text_has(description + body, "do not", "not use", "不要", "不用于", "边界"):
        return ["目标 Skill 写有使用边界，但需要人工复核具体限制是否完整。"]
    return ["未提取到明确谨慎场景，建议在 SKILL.md 中补充非目标、权限边界和失败处理。"]


def infer_inputs_zh(family: str, extracted: list[str], body: str) -> list[str]:
    if family == "meta_skill":
        return [
            "原始材料：重复工作流、提示词、访谈记录、文档、笔记，或一个已有 Skill 包。",
            "目标模式：脚手架、生产、库级或治理模式，用于决定需要多少门禁和资产。",
            "输出契约：期望生成的 SKILL.md、接口声明、参考资料、脚本、报告、评估或发布包。",
            "约束信息：排除项、安全边界、团队复用范围、审查节奏和回滚边界。",
        ]
    if family == "interpreter":
        return [
            "本地 Skill 目录、单个 SKILL.md，或经过安全解包检查的 zip 归档。",
            "输出目录、语言选项、报告格式和扫描大小上限。",
            "人工复核目标：采用前评审、作者自检、学习拆解或安全筛查。",
        ]
    opencli_inputs = {
        "opencli_usage": [
            "用户要操作的平台或能力，比如搜索 B 站、读取 HackerNews、发推、下载小红书图片。",
            "本地 OpenCLI 安装状态，以及是否已经安装浏览器扩展。",
            "目标网站是否需要 Chrome 登录态，公开 API 命令则通常不需要。",
            "希望的输出格式，比如 JSON、Markdown、CSV 或表格。",
        ],
        "opencli_browser": [
            "目标 URL 或当前浏览器页面。",
            "OpenCLI Browser Bridge 扩展和 Chrome 运行状态。",
            "用户希望完成的动作，比如点击、输入、提取文本、保存截图或发现 API。",
            "涉及账号操作时的明确用户确认。",
        ],
        "opencli_explorer": [
            "要新增适配器的网站、页面 URL 和目标命令。",
            "希望抓取或操作的数据字段。",
            "认证方式判断：公开 API、Cookie、Header、拦截请求或 UI 自动化。",
            "本地适配器写入位置和测试命令。",
        ],
        "opencli_oneshot": [
            "一个具体 URL。",
            "这次只想完成的单一目标，比如抓列表、读详情、下载资源。",
            "期望输出列和参数，比如 limit、keyword、format。",
        ],
        "opencli_autofix": [
            "失败的 opencli 命令和完整错误输出。",
            "OPENCLI_DIAGNOSTIC=1 生成的 RepairContext。",
            "RepairContext.adapter.sourcePath 指向的适配器文件。",
            "用户确认可在该适配器文件内做最小修改。",
        ],
        "opencli_smart_search": [
            "用户的问题、关键词、语言和时间范围。",
            "是否指定网站或平台；未指定时再选择 AI 源或专用源。",
            "opencli list 和站点 help 的实时输出。",
            "搜索调用台账，用来记录网站、查询词、次数和状态。",
        ],
    }
    if family in opencli_inputs:
        return opencli_inputs[family]
    translated = [translate_known_bullet_zh(item) for item in extracted]
    return translated or ["目标 Skill 未清楚列出输入项，建议补充用户需要提供的文件、参数和上下文。"]


def infer_outputs_zh(family: str, extracted: list[str], body: str) -> list[str]:
    if family == "meta_skill":
        return [
            "SKILL.md：保持入口精简，只放触发、核心流程、输出契约和必要边界。",
            "agents/interface.yaml：当 Skill 需要被代理或工具系统稳定调用时，声明输入输出接口。",
            "references/：承载方法论、评分规则、治理说明和长文档，避免污染初始上下文。",
            "scripts/：承载稳定、可重复的机械逻辑，减少手工复制代码。",
            "reports/、evals/、manifest.json：在团队复用、治理或发布场景中补齐质量证据和分发信息。",
        ]
    if family == "interpreter":
        return [
            "report.zh-CN.html：默认中文简体 HTML 报告，包含目录、图表、评分、证据、安全审查和路线图。",
            "analysis.json：完整结构化分析结果，便于二次处理或回归比较。",
            "findings.json：扣分项、证据、建议和验收标准。",
            "qa_report.json：报告生成后的质量检查结果。",
            "summary.md：适合放入评审记录或提交说明的短摘要。",
            "report.en.html：可选英文版本，或通过页面右上角语言按钮切换查看英文内容。",
        ]
    if family.startswith("opencli_"):
        return [
            "可执行的 opencli 命令，包含站点、子命令、参数和输出格式。",
            "命令执行结果，优先使用结构化格式，方便 Agent 继续处理。",
            "必要的环境检查结论，比如是否需要 Chrome、扩展、登录态或 API Token。",
            "失败时的下一步建议，比如重新登录、运行 opencli doctor、调整查询词或进入自动修复流程。",
        ]
    paths = extracted or sorted(set(re.findall(r"[\w./-]+\.(?:html|json|md|pdf|docx|csv|yaml|yml)", body)))[:8]
    if not paths:
        return ["未提取到明确输出文件，建议补充默认文件名、格式和验收标准。"]
    return [describe_output_path_zh(path) for path in paths]


def infer_workflow_zh(family: str, extracted: list[str]) -> list[str]:
    if family == "meta_skill":
        return [
            "先判断是否真的需要创建 Skill。一次性任务、没有复用价值或没有稳定输出契约时，直接拒绝 Skill 化。",
            "明确任务、输出、排除项、约束、质量标准和最轻量的适用模式。",
            "按外部标杆、用户材料、本地相邻 Skill 的顺序扫描参考，只暴露不确定性或冲突。",
            "先写描述字段并测试路由质量，再按需要增加 references、scripts、reports 和门禁。",
            "只有在确有价值时，才补充输出风险、产物设计、提示词质量、系统模型和后续演进方向。",
        ]
    if family == "interpreter":
        return [
            "确认输入是本地 Skill 目录、单个 SKILL.md 或 zip 归档，并把目标内容视为不可信材料。",
            "静态读取 frontmatter、标题、目录、脚本、参考资料和生成物，不执行目标脚本。",
            "按 9 个维度计算 100 分评分，并把扣分项绑定到文件、行号和可复核证据。",
            "渲染默认中文报告，同时保留英文切换入口，便于双语审阅。",
            "生成 JSON、发现项、QA 结果和摘要，最后用浏览器检查首屏、目录、图表和移动端。",
        ]
    opencli_workflows = {
        "opencli_usage": [
            "先确认用户要操作的平台和动作，是搜索、热门、发布、下载、桌面应用控制，还是公开 API 查询。",
            "用 opencli list 或站点帮助确认命令是否存在，不凭记忆硬写参数。",
            "根据命令类型判断是否需要 Chrome、扩展、登录态或公开 API。",
            "运行命令时优先选择结构化输出格式，便于后续分析。",
            "如果命令失败，先区分环境问题、登录问题、限流问题和适配器问题。",
        ],
        "opencli_browser": [
            "先运行 opencli doctor，确认 Chrome、扩展和 daemon 连接正常。",
            "打开目标页面后先用 state 看结构化 DOM，不急着截图。",
            "用 state 返回的元素编号执行点击、输入、选择和读取。",
            "页面变化后重新 state，避免用旧编号继续操作。",
            "需要沉淀成适配器时，再用 init、编辑适配器、verify 测试。",
        ],
        "opencli_explorer": [
            "打开目标网站，先观察页面结构和用户目标对应的数据。",
            "优先用 network 发现 JSON API，只有没有稳定 API 时才考虑 DOM 提取。",
            "选择认证策略：公开、Cookie、Header、拦截请求或 UI。",
            "编写 TypeScript 适配器，定义参数、输出列和数据解析。",
            "用 build、list、真实命令和小 limit 结果验证适配器。",
        ],
        "opencli_oneshot": [
            "打开用户给的 URL，确认页面上到底有哪些数据。",
            "查看网络请求或 DOM，选择最快能拿到目标结果的方式。",
            "生成一个最小 TypeScript 命令，只覆盖这次目标。",
            "用 opencli verify 或真实命令跑一遍，确认输出可读。",
        ],
        "opencli_autofix": [
            "先确认失败不是登录、浏览器连接、验证码、限流或平台软封禁。",
            "用 OPENCLI_DIAGNOSTIC=1 重新运行失败命令，提取 RepairContext。",
            "读取诊断里的错误、页面快照、网络请求和 adapter sourcePath。",
            "只修改 sourcePath 指向的适配器文件，保持输出结构兼容。",
            "最多三轮诊断、修复、重试；仍失败就停止并报告尝试记录。",
        ],
        "opencli_smart_search": [
            "先运行 opencli list，确认当前环境里有哪些可用站点。",
            "如果用户指定平台，就直接查该平台 help；没有指定时只选一个 AI 源起步。",
            "执行真实搜索后立刻记录网站、查询词、次数和状态。",
            "信息不足时再补 1 到 2 个专用源，不无限扩搜。",
            "回答末尾写搜索摘要，让用户知道结果来自哪里。",
        ],
    }
    if family in opencli_workflows:
        return opencli_workflows[family]
    translated = [translate_known_bullet_zh(item) for item in extracted]
    if translated:
        return unique_items(translated)
    return ["未提取到明确工作流，建议在 SKILL.md 中按输入、处理、输出、验证、失败处理补齐步骤。"]


def translate_known_bullet_zh(item: str) -> str:
    lowered = item.lower()
    if "do not create a skill" in lowered or "one-off" in lowered:
        return "一次性任务或没有复用价值时，不创建 Skill；需要同时满足重复使用和可复用输出契约。"
    if "capture job" in lowered:
        return "捕捉任务、输出、排除项、约束、标准和最轻量的适用模式。"
    if "scan references" in lowered:
        return "按外部标杆、用户材料、本地相邻 Skill 的顺序扫描参考，只暴露不确定性或冲突。"
    if "write description early" in lowered:
        return "尽早写描述字段并测试路由质量，然后只增加确实需要的文件夹和门禁。"
    if "add output-risk" in lowered:
        return "只有在有实际价值时，才增加输出风险、产物设计、提示词质量、系统模型和后续方向。"
    if re.search(r"[\u4e00-\u9fff]", item):
        return item
    return f"原始条目需要中文化复核：{compact_english_label(item)}。"


def compact_english_label(item: str) -> str:
    item = re.sub(r"`([^`]+)`", r"\1", item)
    item = re.sub(r"\s+", " ", item).strip()
    if len(item) <= 48:
        return item
    return item[:45] + "..."


def describe_output_path_zh(path: str) -> str:
    clean = path.strip()
    lower = clean.lower()
    if clean == "SKILL.md":
        return "SKILL.md：Skill 入口文件，承载触发、流程和输出契约。"
    if clean.endswith("agents/interface.yaml"):
        return "agents/interface.yaml：结构化接口声明，便于代理和自动化系统调用。"
    if lower.endswith(".html"):
        return f"{clean}：HTML 报告或可视化页面。"
    if lower.endswith(".json"):
        return f"{clean}：结构化机器可读结果。"
    if lower.endswith((".yaml", ".yml")):
        return f"{clean}：配置、接口或清单文件。"
    if lower.endswith(".md"):
        return f"{clean}：Markdown 参考资料、说明或摘要。"
    return clean


def build_capability_summary(metadata: dict[str, Any], body: str, lines: list[str], headings: list[dict[str, Any]]) -> dict[str, Any]:
    description = str(metadata.get("description", "") or "").strip()
    name = str(metadata.get("name", "") or "").strip()
    raw_inputs = extract_list_items(section_text(lines, headings, ["input", "输入"]), 8)
    raw_outputs = extract_list_items(section_text(lines, headings, ["output", "输出", "产出"]), 8)
    raw_workflow = extract_list_items(section_text(lines, headings, ["workflow", "工作流", "流程", "步骤"]), 10)
    raw_boundaries = extract_list_items(section_text(lines, headings, ["boundary", "边界", "non-goal", "非目标", "安全"]), 8)
    family = infer_skill_family(description, body)
    return {
        "family": family,
        "one_sentence": localize_description_zh(description, family, name),
        "one_sentence_en": description or "The target Skill does not provide a frontmatter description.",
        "primary_use_cases": infer_use_cases_zh(description, body, family),
        "primary_use_cases_en": raw_use_cases_en(description, family),
        "non_goals": infer_non_goals_zh(description, body, family, raw_boundaries),
        "non_goals_en": raw_boundaries,
        "required_inputs": infer_inputs_zh(family, raw_inputs, body),
        "required_inputs_en": raw_inputs,
        "expected_outputs": infer_outputs_zh(family, raw_outputs, body),
        "expected_outputs_en": raw_outputs or sorted(set(re.findall(r"[\w./-]+\.(?:html|json|md|pdf|docx|csv|yaml|yml)", body)))[:8],
        "workflow_steps": infer_workflow_zh(family, raw_workflow),
        "workflow_steps_en": raw_workflow,
        "raw_description": description,
    }


def raw_use_cases_en(description: str, family: str) -> list[str]:
    if family == "meta_skill":
        return [
            "Create reusable agent skills from workflows, prompts, transcripts, docs, or notes.",
            "Refactor existing skills into lean entrypoints, references, scripts, reports, and gates.",
            "Evaluate and package team-ready skills with the lightest reliable operating mode.",
            "Handle governed skill packages with explicit evidence, rollback, and trust boundaries.",
        ]
    if family == "interpreter":
        return [
            "Review local Agent Skill folders before adoption.",
            "Generate evidence-backed quality reports for authors.",
            "Study mature Skill packages as reusable design examples.",
            "Perform static safety screening without executing target scripts.",
        ]
    return [description] if description else []


def analyze(root: Path, source_label: str, archive_warnings: list[dict[str, Any]], max_file_mb: int) -> dict[str, Any]:
    max_scan_bytes = max_file_mb * 1024 * 1024
    files = iter_files(root)
    inventory = make_inventory(root, files, max_scan_bytes)
    skill_path = root / "SKILL.md"
    if not skill_path.exists():
        raise AnalysisError("目标目录缺少 SKILL.md。")
    skill_text = read_text_limited(skill_path, max_scan_bytes)
    fm_source, body = split_frontmatter(skill_text)
    metadata = parse_frontmatter(fm_source)
    lines = skill_text.splitlines()
    headings = extract_headings(lines)
    description = str(metadata.get("description", "") or "")
    skill_md = {
        "path": "SKILL.md",
        "frontmatter_source": fm_source,
        "body": body,
        "lines": lines,
        "headings": headings,
        "description_line": find_line(lines, "description:"),
        "name_line": find_line(lines, "name:"),
        "token_estimate": max(1, len(skill_text) // 4),
        "char_count": len(skill_text),
        "line_count": len(lines),
    }
    root_files = [p for p in root.iterdir() if p.is_file()]
    model: dict[str, Any] = {
        "schema_version": "0.1.0",
        "generated_at": now_iso(),
        "source": {"input": source_label, "resolved_root": str(root), "archive_warnings": archive_warnings},
        "metadata": metadata,
        "skill_md": skill_md,
        "inventory": inventory,
        "root_files": root_files,
        "static_scan": scan_patterns(root, files, max_scan_bytes),
    }
    model["capability_summary"] = build_capability_summary(metadata, body, lines, headings)
    scorecard, findings = score_skill(model)
    model["scorecard"] = scorecard
    model["findings"] = findings
    model["metrics"] = {
        "script_count": sum(1 for path in files if path.suffix.lower() in SCRIPT_EXTS or safe_rel(path, root).startswith("scripts/")),
        "reference_count": sum(1 for path in files if safe_rel(path, root).startswith("references/")),
        "asset_count": sum(1 for path in files if safe_rel(path, root).startswith("assets/") or safe_rel(path, root).startswith("templates/")),
        "example_count": sum(1 for path in files if safe_rel(path, root).startswith("examples/")),
        "heading_count": len(headings),
        "todo_count": sum(count_text_hits(root, files, r"\bTODO\b|待办|TBD", max_scan_bytes).values()),
        "evidence_coverage": evidence_coverage(findings),
    }
    model["design_patterns"] = infer_design_patterns(model)
    model["roadmap"] = build_roadmap(findings, model)
    return make_jsonable(model)


def make_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): make_jsonable(v) for k, v in value.items() if k != "lines" and k != "body" and k != "frontmatter_source"}
    if isinstance(value, list):
        return [make_jsonable(item) for item in value]
    return value


def count_text_hits(root: Path, files: list[Path], pattern: str, max_bytes: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    regex = re.compile(pattern, flags=re.IGNORECASE)
    for path in files:
        if path.is_symlink() or path.suffix.lower() not in TEXT_EXTS:
            continue
        try:
            if path.stat().st_size > max_bytes or is_binary(path):
                continue
            text = read_text_limited(path, max_bytes)
        except OSError:
            continue
        count = len(regex.findall(text))
        if count:
            counts[safe_rel(path, root)] = count
    return counts


def evidence_coverage(findings: list[dict[str, Any]]) -> float:
    if not findings:
        return 1.0
    covered = 0
    for finding in findings:
        ev = finding.get("evidence", [])
        if ev and any(item.get("fact_type") != "missing" for item in ev):
            covered += 1
    return round(covered / len(findings), 3)


def infer_design_patterns(model: dict[str, Any]) -> dict[str, list[str]]:
    dirs = model["inventory"]["directories"]
    body = str(model.get("skill_md", {}).get("body", "")).lower()
    strengths: list[str] = []
    anti_patterns: list[str] = []
    if "references" in dirs and "scripts" in dirs:
        strengths.append("入口、参考资料和脚本分层，符合渐进披露思路。")
    if "evals" in dirs or "tests" in dirs:
        strengths.append("包体包含可复核的测试或触发样例。")
    if "output" in body or "输出" in body:
        strengths.append("入口中出现输出契约信号，便于用户判断成功结果。")
    if model["skill_md"]["token_estimate"] > 2500:
        anti_patterns.append("SKILL.md 入口偏长，可能把参考资料直接塞进初始上下文。")
    if "scripts" in dirs and not any("verify" in name.lower() or "test" in name.lower() for name in model["inventory"]["directories"]):
        anti_patterns.append("存在脚本资产，但测试或验证线索偏弱。")
    if not strengths:
        strengths.append("当前包体仍需更多结构证据，暂不提炼强模式。")
    if not anti_patterns:
        anti_patterns.append("未发现明显结构反例；仍建议人工复核高风险文件。")
    return {"strengths": strengths, "anti_patterns": anti_patterns}


def build_roadmap(findings: list[dict[str, Any]], model: dict[str, Any]) -> list[dict[str, str]]:
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    selected = sorted(findings, key=lambda item: (priority_order.get(item["severity"], 4), item["score_delta"]))[:5]
    roadmap: list[dict[str, str]] = []
    for finding in selected[:3]:
        roadmap.append(
            {
                "priority": {"critical": "P0", "high": "P1", "medium": "P2", "low": "P3"}.get(finding["severity"], "P3"),
                "title": finding["summary"],
                "action": finding["recommendation"],
                "acceptance": finding["acceptance_criteria"],
            }
        )
    if not roadmap:
        roadmap.append(
            {
                "priority": "P2",
                "title": "补充真实使用样例和回归用例。",
                "action": "为高频请求增加 examples/ 与 evals/trigger_cases.json。",
                "acceptance": "至少包含 3 个正例、3 个反例和 2 个近邻混淆用例。",
            }
        )
    return roadmap


def lang_pack(lang: str) -> dict[str, str]:
    if lang == "en":
        return {
            "html_lang": "en",
            "mark": "Yao Interpreter",
            "title": "Skill quality interpretation report",
            "lead": "A static, evidence-backed review of the target Agent Skill: purpose, trigger contract, structure, safety, score, and improvement path.",
            "score": "Score",
            "grade": "Grade",
            "risk": "Risk",
            "decision": "Recommendation",
            "sections": "Sections",
        }
    return {
        "html_lang": "zh-CN",
        "mark": "Yao Interpreter",
        "title": "Skill 质量解读报告",
        "lead": "基于静态读取、证据链和 100 分评分模型，解释目标 Skill 的用途、触发、结构、风险和改进路线。",
        "score": "总分",
        "grade": "等级",
        "risk": "风险",
        "decision": "建议",
        "sections": "目录",
    }


NAV_ZH = [
    ("overview", "封面总览"),
    ("position", "一句话定位"),
    ("use-cases", "适用场景"),
    ("caution", "谨慎场景"),
    ("quick-start", "快速使用"),
    ("outputs", "输出预期"),
    ("structure", "结构总览"),
    ("disclosure", "渐进披露"),
    ("workflow", "工作流"),
    ("scripts", "脚本依赖"),
    ("patterns", "设计模式"),
    ("score", "评分明细"),
    ("evidence", "证据链"),
    ("security", "安全审查"),
    ("prompts", "提示词库"),
    ("failures", "失败排查"),
    ("roadmap", "改进路线"),
    ("appendix", "附录"),
]
NAV_EN = [
    ("overview", "Overview"),
    ("position", "Positioning"),
    ("use-cases", "Use cases"),
    ("caution", "Cautions"),
    ("quick-start", "Quick start"),
    ("outputs", "Outputs"),
    ("structure", "Structure"),
    ("disclosure", "Disclosure"),
    ("workflow", "Workflow"),
    ("scripts", "Scripts"),
    ("patterns", "Patterns"),
    ("score", "Score"),
    ("evidence", "Evidence"),
    ("security", "Security"),
    ("prompts", "Prompts"),
    ("failures", "Failures"),
    ("roadmap", "Roadmap"),
    ("appendix", "Appendix"),
]


def bi(zh: Any, en: Any = None) -> str:
    zh_text = str(zh)
    en_text = str(en if en is not None else zh)
    return f'<span data-lang="zh-CN">{esc(zh_text)}</span><span data-lang="en">{esc(en_text)}</span>'


def render_nav(items: list[tuple[str, str]], class_name: str, en_items: list[tuple[str, str]] | None = None) -> str:
    en_lookup = dict(en_items or [])
    return f'<nav class="{class_name}" aria-label="report navigation">' + "".join(
        f'<a href="#{esc(anchor)}">{bi(label, en_lookup.get(anchor, label))}</a>' for anchor, label in items
    ) + "</nav>"


def render_kpis(model: dict[str, Any], labels: dict[str, str]) -> str:
    score = model["scorecard"]
    metrics = model["metrics"]
    cards = [
        (bi("总分", "Score"), str(score["total"])),
        (bi("等级", "Grade"), score["grade"]),
        (bi("风险", "Risk"), bi(zh_risk(score["risk_level"]), score["risk_level"])),
        (bi("证据覆盖", "Evidence"), f"{metrics['evidence_coverage'] * 100:.0f}%"),
    ]
    return '<div class="kpi-grid">' + "".join(
        f'<article class="kpi"><span>{label}</span><strong>{value if str(value).startswith("<span") else esc(value)}</strong></article>' for label, value in cards
    ) + "</div>"


def cover_lead_zh(model: dict[str, Any]) -> str:
    summary = model["capability_summary"]
    family = summary.get("family", "generic")
    score = model["scorecard"]
    if family == "opencli_usage":
        return (
            "这是 OpenCLI 能力入口型 Skill，背景是 Agent 需要访问网站、桌面应用和公开 API，却不应该靠临时记忆硬写命令。"
            "它解决的核心问题是先定位可用站点和子命令，再把搜索、热门、发布、下载、桌面应用控制等操作转成可执行的 opencli 调用。"
            "亮点是覆盖面广、输出格式明确；使用前要确认本地安装、浏览器扩展和登录态，涉及账号动作时不能自动越权。"
        )
    if family == "opencli_browser":
        return (
            "这是 OpenCLI 浏览器桥接型 Skill，面向需要让 Agent 操作真实网页的场景。"
            "它解决的问题是把打开页面、读取结构、点击、输入和提取内容这些浏览器动作变成可复用命令，同时复用 Chrome 里的登录状态。"
            "亮点是适合页面探索和轻量自动化；风险在于 Cookie、账号状态和验证码，需要把用户确认放在前面。"
        )
    if family == "opencli_explorer":
        return (
            "这是 OpenCLI 适配器创建型 Skill，背景是新网站接入时需要先搞清页面、接口和认证方式。"
            "它解决的核心问题是把探索网页、发现 API、选择认证策略、编写 TypeScript 适配器和真实命令验证串成一条工作流。"
            "亮点是从探索到测试都有路径；代价是步骤重，适合做长期可复用适配器，不适合只跑一次的小任务。"
        )
    if family == "opencli_oneshot":
        return (
            "这是 OpenCLI 单次命令原型型 Skill，适合用户给出一个 URL 和一个很具体的目标时使用。"
            "它解决的问题是先生成一个能跑的小命令，快速验证页面或接口是否能稳定拿到数据。"
            "亮点是轻、快、成本低；如果任务会反复出现，后续应升级成完整适配器。"
        )
    if family == "opencli_autofix":
        return (
            "这是 OpenCLI 适配器修复型 Skill，背景是网站结构、接口返回和等待条件经常变化。"
            "它解决的问题是读取诊断上下文，定位 adapter sourcePath，在受控范围内做最小修复并重试。"
            "亮点是有三轮上限和文件边界；如果失败来自登录、验证码、限流或平台风控，就不应该继续自动改代码。"
        )
    if family == "opencli_smart_search":
        return (
            "这是 OpenCLI 搜索路由型 Skill，适合用户只提出问题但没有指定搜索来源的情况。"
            "它解决的问题是先判断该用 AI 源、垂直平台还是指定站点，再用 live help 确认命令并记录调用过程。"
            "亮点是能控制搜索预算并说明来源；它适合补充原始结果，不适合把单次搜索当成最终事实。"
        )
    if family == "meta_skill":
        return (
            "这是 Skill 工程化设计 Skill，用来把重复工作流、提示词、访谈记录或文档沉淀成可复用的智能体能力。"
            "它解决的核心问题是先判断是否值得 Skill 化，再按最轻模式补齐入口、参考资料、脚本、评估和治理边界。"
            "亮点是重视路由质量和证据链；如果只是一次性任务，就不应该强行创建 Skill。"
        )
    if family == "interpreter":
        return (
            "这是 Skill 解读和质量评审 Skill，面向采用第三方 Skill、作者自检和团队复用前评审。"
            "它解决的问题是只通过静态读取判断用途、触发、结构、脚本依赖、安全风险和改进路线，并输出中文优先的可视化报告。"
            "亮点是证据链、评分和图表完整；它不会执行目标脚本，所以结论适合做采用前筛查。"
        )
    base = summary.get("one_sentence") or "这个 Skill 用于支持一个特定的智能体工作流。"
    use_cases = summary.get("primary_use_cases") or []
    first_case = str(use_cases[0]) if use_cases else "它适合在需要理解用途、触发方式、输入输出和风险边界时使用。"
    return (
        f"{base}"
        f"报告会重点解释它解决什么问题、什么时候触发、会产出什么，以及当前 {score['total']} 分背后的主要扣分原因。"
        f"{first_case}"
    )


def cover_lead_en(model: dict[str, Any]) -> str:
    summary = model["capability_summary"]
    family = summary.get("family", "generic")
    if family.startswith("opencli_"):
        return (
            "This report explains the OpenCLI Skill in practical terms: what problem it solves, when an agent should invoke it, and what local environment or account state must be checked first. "
            "It highlights the useful command workflow while calling out safety boundaries around login state, browser sessions, and source reliability."
        )
    if family == "meta_skill":
        return (
            "This report explains how the Skill turns repeated workflows, prompts, notes, or documents into reusable agent capabilities. "
            "It focuses on trigger quality, progressive disclosure, evidence, governance boundaries, and the lightest reliable packaging mode."
        )
    if family == "interpreter":
        return (
            "This report reviews a Skill package before adoption or reuse. "
            "It uses static reading, scoring, evidence, charts, and safety checks to explain purpose, trigger contract, structure, risk, and improvement priorities."
        )
    return str(summary.get("one_sentence_en") or "This report explains the target Skill's purpose, trigger contract, expected outputs, risk, and improvement priorities.")


def cover_badges(model: dict[str, Any]) -> list[tuple[str, str]]:
    family = model["capability_summary"].get("family", "generic")
    if family == "opencli_usage":
        return [("OpenCLI 总目录", "OpenCLI directory"), ("79+ 适配器", "79+ adapters"), ("需确认登录态", "Check login state")]
    if family == "opencli_browser":
        return [("浏览器桥接", "Browser bridge"), ("复用 Chrome 状态", "Chrome session"), ("账号操作需确认", "Confirm account actions")]
    if family == "opencli_explorer":
        return [("适配器创建", "Adapter creation"), ("API 探索", "API discovery"), ("真实命令验证", "Command verification")]
    if family == "opencli_oneshot":
        return [("单次命令", "One-shot command"), ("快速原型", "Fast prototype"), ("可升级适配器", "Adapter-ready")]
    if family == "opencli_autofix":
        return [("诊断修复", "Diagnostic repair"), ("三轮上限", "Three-attempt limit"), ("受控改动", "Scoped edits")]
    if family == "opencli_smart_search":
        return [("搜索路由", "Search routing"), ("live help 校验", "Live help check"), ("调用台账", "Search log")]
    if family == "meta_skill":
        return [("Skill 工程化", "Skill engineering"), ("渐进披露", "Progressive disclosure"), ("证据门禁", "Evidence gates")]
    if family == "interpreter":
        return [("中文优先", "Chinese first"), ("静态评审", "Static review"), ("证据链评分", "Evidence scoring")]
    return [("默认中文", "Chinese first"), ("静态分析", "Static review"), ("不执行目标脚本", "No target execution")]


def zh_risk(risk: str) -> str:
    return {"low": "低", "medium": "中", "high": "高", "critical": "严重"}.get(risk, risk)


def render_aside(model: dict[str, Any]) -> str:
    inventory = model["inventory"]
    metrics = model["metrics"]
    items = [
        (bi("文件数", "Files"), inventory["file_count"]),
        (bi("总大小", "Total size"), human_bytes(inventory["total_bytes"])),
        (bi("脚本数", "Scripts"), metrics["script_count"]),
        (bi("参考资料", "References"), metrics["reference_count"]),
        (bi("风险发现", "Findings"), len(model["findings"])),
        ("SKILL.md", f"{model['skill_md']['token_estimate']} Token"),
    ]
    return '<aside class="metrics-aside">' + "".join(
        f'<article class="aside-box"><span>{label}</span><strong>{esc(value)}</strong></article>' for label, value in items
    ) + "</aside>"


def human_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def section(anchor: str, number: int, title: str | tuple[str, str], body: str) -> str:
    title_html = bi(title[0], title[1]) if isinstance(title, tuple) else esc(title)
    return (
        f'<section class="report-section" id="{esc(anchor)}">'
        f'<div class="section-head"><span class="section-number">{number:02d}</span><h2>{title_html}</h2></div>'
        f"{body}</section>"
    )


def render_list(items: list[Any], empty: str = "暂无记录。") -> str:
    if not items:
        return f"<ul><li>{esc(empty)}</li></ul>"
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def render_bilingual_list(zh_items: list[Any], en_items: list[Any] | None = None, empty_zh: str = "暂无记录。", empty_en: str = "No records.") -> str:
    if not zh_items and not en_items:
        return f"<ul><li>{bi(empty_zh, empty_en)}</li></ul>"
    max_len = max(len(zh_items), len(en_items or []))
    items = []
    for index in range(max_len):
        zh = zh_items[index] if index < len(zh_items) else empty_zh
        en = (en_items or [])[index] if en_items and index < len(en_items) else zh
        items.append(f"<li>{bi(zh, en)}</li>")
    return "<ul>" + "".join(items) + "</ul>"


def render_analysis_panel(zh: str, en: str | None = None) -> str:
    return f'<article class="panel analysis-note"><p>{bi(zh, en or zh)}</p></article>'


def title_pair(index: int) -> tuple[str, str]:
    return NAV_ZH[index][1], NAV_EN[index][1]


def render_scores(model: dict[str, Any]) -> str:
    rows = []
    for key, zh, _en, maximum in RUBRIC:
        item = model["scorecard"]["dimensions"].get(key, {"score": 0, "max": maximum})
        pct = int(item["score"] / maximum * 100) if maximum else 0
        rows.append(
            f'<div class="score-row"><span>{bi(zh, _en)}</span><div class="bar"><i style="--score:{pct}%"></i></div><strong>{item["score"]}/{maximum}</strong></div>'
        )
    return '<div class="panel">' + "".join(rows) + "</div>"


def zh_severity(value: str) -> str:
    return {"low": "低", "medium": "中", "high": "高", "critical": "严重"}.get(value, value)


def evidence_quote_summary_zh(item: dict[str, Any]) -> str:
    quote = str(item.get("quote", "") or "")
    section_name = evidence_section_label_zh(str(item.get("section", "") or ""))
    if not quote:
        return "该发现缺少可引用原文，需要补充证据。"
    if re.search(r"[\u4e00-\u9fff]", quote):
        return quote if len(quote) <= 160 else quote[:157] + "..."
    lowered = quote.lower()
    if "description:" in lowered:
        return "该行定义前置描述字段，是判断触发范围、一句话定位和适用场景的主要来源。"
    if "name:" in lowered:
        return "该行定义 Skill 名称，用于识别包体和路由对象。"
    if "token_estimate" in lowered:
        return "该指标用于判断入口文件是否过重，以及是否需要把细节下沉到 references/。"
    if "directory missing" in lowered:
        return "该证据表示关键目录缺失，会影响渐进披露、脚本复用或评估能力。"
    if "missing" in lowered:
        return "该项缺失，说明目标 Skill 需要补齐对应契约或证据。"
    if section_name:
        return f"该片段来自 {section_name}，用于支撑上方发现；原文可在详情中查看。"
    return "该片段是原始证据，默认中文报告只显示释义；需要逐字核对时可展开查看原文。"


def evidence_section_label_zh(section: str) -> str:
    if not section:
        return ""
    lowered = section.lower()
    if "frontmatter.description" in lowered:
        return "前置描述字段"
    if "frontmatter.name" in lowered:
        return "前置名称字段"
    if "frontmatter" in lowered:
        return "前置元数据"
    if "inventory" in lowered:
        return "资产清单"
    if "directory" in lowered:
        return "目录结构"
    if "workflow" in lowered:
        return "工作流"
    if "output" in lowered:
        return "输出契约"
    if "entrypoint" in lowered:
        return "入口文件"
    return section


def render_findings(findings: list[dict[str, Any]], limit: int | None = None) -> str:
    selected = findings if limit is None else findings[:limit]
    if not selected:
        return '<article class="panel"><p>' + bi("没有发现需要扣分的关键问题。", "No key deduction findings were identified.") + "</p></article>"
    blocks = []
    for finding in selected:
        ev_html = "".join(
            '<div class="evidence">'
            f'<strong>{esc(item.get("file", ""))}:{esc(item.get("line_start", ""))}</strong>'
            f'<br>{bi("证据释义：" + evidence_quote_summary_zh(item), "Evidence: " + str(item.get("quote", "")))}'
            '<details class="evidence-raw"><summary>原始证据</summary>'
            f'<pre><code>{esc(item.get("quote", ""))}</code></pre>'
            "</details>"
            "</div>"
            for item in finding.get("evidence", [])[:2]
        )
        blocks.append(
            '<article class="finding">'
            '<div class="finding-head">'
            f'<h3>{esc(finding["summary"])}</h3>'
            f'<span class="severity {esc(finding["severity"])}">{bi(zh_severity(finding["severity"]), finding["severity"])}</span>'
            "</div>"
            f'<p><strong>{bi("建议：", "Recommendation:")}</strong>{esc(finding["recommendation"])}</p>'
            f'<p><strong>{bi("验收：", "Acceptance:")}</strong>{esc(finding["acceptance_criteria"])}</p>'
            f"{ev_html}</article>"
        )
    return "".join(blocks)


def render_chart_radar(model: dict[str, Any]) -> str:
    center = 170
    radius = 102
    dims = [(zh, model["scorecard"]["dimensions"][key]["score"], maximum) for key, zh, _en, maximum in RUBRIC]
    rings = []
    for pct in (0.25, 0.5, 0.75, 1.0):
        points = []
        for i in range(len(dims)):
            angle = -math.pi / 2 + 2 * math.pi * i / len(dims)
            points.append(f"{center + radius * pct * math.cos(angle):.1f},{center + radius * pct * math.sin(angle):.1f}")
        rings.append(f'<polygon points="{" ".join(points)}" fill="none" stroke="#e6e0d4" stroke-width="1"/>')
    data_points = []
    labels = []
    for i, (label, score, maximum) in enumerate(dims):
        angle = -math.pi / 2 + 2 * math.pi * i / len(dims)
        data_radius = radius * (score / maximum)
        data_points.append(f"{center + data_radius * math.cos(angle):.1f},{center + data_radius * math.sin(angle):.1f}")
        lx = center + (radius + 42) * math.cos(angle)
        ly = center + (radius + 42) * math.sin(angle)
        labels.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" dominant-baseline="middle" font-size="11" fill="#504e49">{esc(label[:5])}</text>')
    svg = (
        '<figure><svg viewBox="0 0 340 340" role="img" aria-label="评分雷达">'
        '<text class="chart-title" x="18" y="28">评分雷达</text>'
        + "".join(rings)
        + f'<polygon points="{" ".join(data_points)}" fill="#EEF3F8" stroke="#1B365D" stroke-width="2"/>'
        + "".join(labels)
        + "</svg><figcaption>雷达图展示 9 个评分维度的相对强弱。</figcaption></figure>"
    )
    return svg


def render_chart_assets(model: dict[str, Any]) -> str:
    dirs = sorted(model["inventory"]["directories"].items(), key=lambda item: item[1], reverse=True)[:5]
    total = sum(value for _label, value in dirs) or 1
    colors = ["#1B365D", "#315982", "#6b6a64", "#b8b7b0", "#EEF3F8"]
    offset = 0.0
    circles = []
    labels = []
    for index, (label, value) in enumerate(dirs):
        dash = value / total * 100
        circles.append(
            f'<circle cx="120" cy="130" r="68" fill="none" stroke="{colors[index]}" stroke-width="22" '
            f'stroke-dasharray="{dash:.2f} {100 - dash:.2f}" stroke-dashoffset="{-offset:.2f}" pathLength="100" transform="rotate(-90 120 130)"/>'
        )
        labels.append(f'<text x="220" y="{82 + index * 24}" font-size="12" fill="#504e49">{esc(label)} · {value}</text>')
        offset += dash
    return (
        '<figure><svg viewBox="0 0 420 280" role="img" aria-label="资产分布">'
        '<text class="chart-title" x="18" y="28">资产分布</text>'
        + "".join(circles)
        + f'<text x="120" y="136" text-anchor="middle" font-size="18" fill="#1B365D">{model["inventory"]["file_count"]}</text>'
        + "".join(labels)
        + "</svg><figcaption>目录分布显示包体重心和生成物比例。</figcaption></figure>"
    )


def render_chart_heatmap(model: dict[str, Any]) -> str:
    severity_weight = {"low": (1, 1), "medium": (2, 2), "high": (3, 2), "critical": (3, 3)}
    cells: dict[tuple[int, int], int] = defaultdict(int)
    for finding in model["findings"]:
        impact, probability = severity_weight.get(finding["severity"], (1, 1))
        cells[(impact, probability)] += 1
    rects = []
    for impact in range(1, 4):
        for probability in range(1, 4):
            count = cells[(impact, probability)]
            color = ["#ffffff", "#EEF3F8", "#d8e5f0", "#1B365D"][min(3, count)]
            text_color = "#ffffff" if count >= 3 else "#151515"
            x = 70 + (probability - 1) * 82
            y = 58 + (3 - impact) * 62
            rects.append(f'<rect x="{x}" y="{y}" width="74" height="54" rx="6" fill="{color}" stroke="#e6e0d4"/><text x="{x+37}" y="{y+33}" text-anchor="middle" fill="{text_color}" font-size="14">{count}</text>')
    return (
        '<figure><svg viewBox="0 0 340 280" role="img" aria-label="风险热力">'
        '<text class="chart-title" x="18" y="28">风险热力</text>'
        + "".join(rects)
        + '<text x="190" y="258" text-anchor="middle" font-size="12" fill="#68625a">发生概率</text>'
        + '<text x="22" y="152" text-anchor="middle" font-size="12" fill="#68625a" transform="rotate(-90 22 152)">影响程度</text>'
        + "</svg><figcaption>热力图按影响程度和发生概率聚合发现项。</figcaption></figure>"
    )


def render_chart_flow() -> str:
    labels = ["输入", "隔离", "解析", "评分", "报告", "QA"]
    nodes = []
    for idx, label in enumerate(labels):
        x = 34 + idx * 112
        nodes.append(f'<rect x="{x}" y="70" width="82" height="48" rx="8" fill="#ffffff" stroke="#e6e0d4"/><text x="{x+41}" y="100" text-anchor="middle" font-size="13" fill="#151515">{label}</text>')
    arrows = "".join(f'<path d="M{116 + idx * 112} 94 H{146 + idx * 112}" stroke="#1B365D" stroke-width="1.5"/>' for idx in range(5))
    return (
        '<figure><svg viewBox="0 0 680 180" role="img" aria-label="工作流图">'
        '<text class="chart-title" x="18" y="30">交付流程</text>'
        + arrows
        + "".join(nodes)
        + "</svg><figcaption>报告从不可信输入开始，经隔离、解析、评分和 QA 后输出。</figcaption></figure>"
    )


def render_charts(model: dict[str, Any]) -> str:
    return '<div class="chart-grid">' + render_chart_radar(model) + render_chart_assets(model) + render_chart_heatmap(model) + render_chart_flow() + "</div>"


def position_highlights_zh(model: dict[str, Any]) -> list[str]:
    family = model["capability_summary"].get("family")
    if family == "meta_skill":
        return [
            "它的核心不是生成一段提示词，而是把可重复的工作方式整理成可路由、可复用、可评估的 Skill 包。",
            "它强调先写描述字段并测试触发质量，说明这个 Skill 把“何时使用”看作 Skill 成败的第一入口。",
            "它把轻量脚手架模式和高信任治理模式分开，避免把所有流程都做成重治理工程。",
        ]
    if family == "interpreter":
        return [
            "它是采用前的静态评审工具，不是目标 Skill 的执行器。",
            "它把安全、评分、证据和 HTML 交付放在同一个闭环里，适合做团队 Skill 审阅入口。",
            "默认中文报告是主交付物，英文只作为双语审阅辅助。",
        ]
    if family == "opencli_usage":
        return [
            "它像 OpenCLI 的总目录，先帮 Agent 找到该用哪个站点和哪个子命令。",
            "它覆盖网站、公开 API、桌面应用和外部 CLI，能力广，但也更依赖本地环境。",
            "使用时要先区分公开查询和需要登录态的操作，后者必须更谨慎。",
        ]
    if family == "opencli_browser":
        return [
            "它把浏览器页面变成可操作的命令行界面，适合需要登录态的网站。",
            "核心方法是先看结构化 state，再按元素编号点击、输入和读取，不靠截图猜。",
            "它能做很多事，但也最容易碰到账号、Cookie、验证码和误操作风险。",
        ]
    if family == "opencli_explorer":
        return [
            "它面向适配器作者，目标是把一个网站沉淀成稳定的 OpenCLI 命令。",
            "它强调先找 API，再考虑 DOM 提取，能减少页面改版带来的脆弱性。",
            "它包含很多模板和策略，入口文件偏重，后续适合拆到参考资料里。",
        ]
    if family == "opencli_oneshot":
        return [
            "它适合先做一个小命令验证可行性，而不是一开始就建设完整站点适配器。",
            "它关注一个 URL、一个目标、一次输出，速度快但覆盖范围有限。",
            "如果这个命令会反复用，再升级到 explorer 的完整适配器流程。",
        ]
    if family == "opencli_autofix":
        return [
            "它不是通用修 bug 流程，而是专门修 OpenCLI adapter 因页面或接口变化导致的失败。",
            "它有明确停止条件：登录失效、浏览器连接失败、验证码、限流都不该改代码。",
            "它只允许改诊断上下文指定的适配器文件，避免把问题扩大到主项目。",
        ]
    if family == "opencli_smart_search":
        return [
            "它先选数据源，再执行搜索，避免一上来就乱查多个平台。",
            "它要求每次搜索后记录网站、查询词和次数，方便用户判断覆盖范围。",
            "它适合信息检索，不适合替代需要严格引用和人工复核的研究流程。",
        ]
    return [
        "定位判断来自前置描述字段、一级标题、目录结构和输出契约。",
        "如果描述字段仍是英文或过短，建议先补中文触发场景和非目标边界。",
    ]


def position_highlights_en(model: dict[str, Any]) -> list[str]:
    family = model["capability_summary"].get("family")
    if family == "meta_skill":
        return [
            "Its core job is packaging reusable ways of working into routeable, reusable, and evaluable Skill packages.",
            "It treats the frontmatter description and route quality as the first success condition.",
            "It separates lightweight Scaffold work from Governed high-trust packages.",
        ]
    if family == "interpreter":
        return [
            "It is a static pre-adoption review tool, not an executor for the target Skill.",
            "It combines safety, scoring, evidence, and HTML delivery into one review loop.",
            "The Simplified Chinese report is the primary artifact, with English as a review aid.",
        ]
    return []


def render_position(model: dict[str, Any]) -> str:
    summary = model["capability_summary"]
    return (
        '<article class="panel">'
        f'<p class="lead-in">{bi(summary["one_sentence"], summary.get("one_sentence_en", summary["one_sentence"]))}</p>'
        '<h3>' + bi("解读重点", "Interpretation focus") + "</h3>"
        + render_bilingual_list(position_highlights_zh(model), position_highlights_en(model))
        + "</article>"
    )


def render_use_cases_section(model: dict[str, Any]) -> str:
    summary = model["capability_summary"]
    return (
        '<article class="panel">'
        + render_bilingual_list(summary["primary_use_cases"], summary.get("primary_use_cases_en", []))
        + "</article>"
    )


def render_caution_section(model: dict[str, Any]) -> str:
    summary = model["capability_summary"]
    return (
        '<article class="panel">'
        + render_bilingual_list(summary["non_goals"], summary.get("non_goals_en", []), "未提取到明确谨慎场景，建议人工复核边界。", "No explicit caution cases were extracted.")
        + "</article>"
    )


def render_inputs_section(model: dict[str, Any]) -> str:
    summary = model["capability_summary"]
    return (
        '<article class="panel">'
        + render_bilingual_list(summary["required_inputs"], summary.get("required_inputs_en", []), "未提取到明确输入项。", "No explicit inputs were extracted.")
        + "</article>"
    )


def render_outputs_section(model: dict[str, Any]) -> str:
    summary = model["capability_summary"]
    return (
        '<article class="panel">'
        + render_bilingual_list(summary["expected_outputs"], summary.get("expected_outputs_en", []), "未提取到明确输出文件。", "No explicit output files were extracted.")
        + "</article>"
    )


def render_workflow_section(model: dict[str, Any]) -> str:
    summary = model["capability_summary"]
    return (
        '<article class="panel">'
        + render_bilingual_list(summary["workflow_steps"], summary.get("workflow_steps_en", []), "未提取到明确工作流。", "No explicit workflow was extracted.")
        + "</article>"
    )


def structure_summary_zh(model: dict[str, Any]) -> str:
    dirs = model["inventory"]["directories"]
    parts = [f"这个包一共有 {model['inventory']['file_count']} 个文件，分布在 {len(dirs)} 个顶层入口里。目录分层决定了入口是否轻、长规则是否下沉、脚本和生成物是否会污染初始上下文。"]
    if "references" in dirs:
        parts.append(f"references/ 有 {dirs['references']} 个文件，说明部分长规则已经从入口下沉。")
    if "scripts" in dirs:
        parts.append(f"scripts/ 有 {dirs['scripts']} 个文件，说明存在可重复执行的机械逻辑。")
    if "reports" in dirs:
        parts.append(f"reports/ 有 {dirs['reports']} 个文件，说明有生成物或评审材料；这类目录要和正式说明分清，避免以后反复扫描旧报告。")
    if "evals" in dirs:
        parts.append("evals/ 存在，说明作者已经开始把触发和输出质量做成可回归材料。")
    if not parts:
        parts.append("目录结构偏轻，需要人工确认是否足以承载复用、评估和维护。")
    return " ".join(parts)


def structure_summary_en(model: dict[str, Any]) -> str:
    dirs = model["inventory"]["directories"]
    return f"The package contains {model['inventory']['file_count']} files across {len(dirs)} top-level groups. The table below shows where the package weight sits."


def render_quick_start_section(model: dict[str, Any]) -> str:
    quick_cmd = f'python3 scripts/cli.py analyze "{model["source"]["input"]}" --out reports/generated'
    summary = model["capability_summary"]
    return (
        '<article class="panel"><h3>' + bi("调用前需要准备", "Required before use") + "</h3>"
        + render_bilingual_list(summary["required_inputs"], summary.get("required_inputs_en", []), "未提取到明确输入项。", "No explicit inputs were extracted.")
        + "</article>"
        + f'<article class="panel prompt"><button class="copy-button" data-copy-source="#quick-command" data-copied-label="已复制">复制命令</button><pre id="quick-command"><code>{esc(quick_cmd)}</code></pre></article>'
    )


def score_summary_zh(model: dict[str, Any]) -> str:
    score = model["scorecard"]
    return f"当前总分 {score['total']} / 100，等级 {score['grade']}，风险等级为{zh_risk(score['risk_level'])}。9 个维度里，低分项会直接影响采用建议；后续证据链会给出扣分来源、修复动作和验收标准。"


def score_summary_en(model: dict[str, Any]) -> str:
    score = model["scorecard"]
    return f"Total score is {score['total']} / 100, grade {score['grade']}, with {score['risk_level']} risk. The score is calculated across 9 dimensions."


def render_report(model: dict[str, Any], lang: str = "zh-CN") -> str:
    labels = lang_pack("en" if lang == "en" else "zh-CN")
    css = read_template("report.css")
    js = read_template("report.js")
    metadata = model["metadata"]
    name = metadata.get("name") or Path(model["source"]["resolved_root"]).name
    score = model["scorecard"]
    current_lang = labels["html_lang"]
    zh_pressed = "true" if current_lang == "zh-CN" else "false"
    en_pressed = "true" if current_lang == "en" else "false"
    cover_badge_html = "".join(f'<span class="badge">{bi(zh, en)}</span>' for zh, en in cover_badges(model))
    sections = []
    overview_intro_zh = f"当前建议为“{score['recommendation']}”总分 {score['total']} / 100，风险等级为{zh_risk(score['risk_level'])}。雷达图显示质量短板，资产分布显示包体重心，风险热力图显示问题集中位置。"
    overview_intro_en = "The overview starts with score, risk, charts, and asset distribution so the reader can judge whether the Skill is worth adopting or studying."
    sections.append(section("overview", 1, title_pair(0), render_analysis_panel(overview_intro_zh, overview_intro_en) + '<div class="panel">' + render_charts(model) + "</div>"))
    sections.append(section("position", 2, title_pair(1), render_position(model)))
    sections.append(section("use-cases", 3, title_pair(2), render_use_cases_section(model)))
    sections.append(section("caution", 4, title_pair(3), render_caution_section(model)))
    sections.append(section("quick-start", 5, title_pair(4), render_quick_start_section(model)))
    sections.append(section("outputs", 6, title_pair(5), render_outputs_section(model)))
    sections.append(section("structure", 7, title_pair(6), render_structure(model)))
    sections.append(section("disclosure", 8, title_pair(7), render_disclosure(model)))
    sections.append(section("workflow", 9, title_pair(8), render_workflow_section(model)))
    sections.append(section("scripts", 10, title_pair(9), render_script_review(model)))
    sections.append(section("patterns", 11, title_pair(10), render_patterns(model)))
    sections.append(section("score", 12, title_pair(11), render_analysis_panel(score_summary_zh(model), score_summary_en(model)) + render_scores(model)))
    evidence_intro_zh = "每个扣分项都绑定到文件、行号和原始片段。证据用于复核结论是否成立，验收标准用于判断修复后是否可以重新评分。"
    evidence_intro_en = "This section explains where each deduction comes from: file, line, source snippet, recommendation, and acceptance criteria."
    sections.append(section("evidence", 13, title_pair(12), render_analysis_panel(evidence_intro_zh, evidence_intro_en) + render_findings(model["findings"])))
    sections.append(section("security", 14, title_pair(13), render_security(model)))
    sections.append(section("prompts", 15, title_pair(14), render_prompts()))
    sections.append(section("failures", 16, title_pair(15), render_failures()))
    sections.append(section("roadmap", 17, title_pair(16), render_roadmap_html(model["roadmap"])))
    sections.append(section("appendix", 18, title_pair(17), render_appendix(model)))
    side_nav = render_nav(NAV_ZH, "side-toc", NAV_EN)
    html_doc = f"""<!doctype html>
<html lang="{esc(labels['html_lang'])}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="generator" content="Yao Interpreter">
  <title>{esc(name)} · {esc(labels['title'])}</title>
  <style>{css}</style>
</head>
<body>
  <a class="skip-link" href="#main">{bi("跳到正文", "Skip to content")}</a>
  <header class="topbar">
    <div class="progress-track"><span class="progress-bar"></span></div>
    <div class="topbar-inner">
      <div class="report-mark">{esc(labels['mark'])}</div>
      <div class="language-switch" aria-label="语言切换">
        <button type="button" data-set-lang="zh-CN" aria-pressed="{zh_pressed}">简体</button>
        <button type="button" data-set-lang="en" aria-pressed="{en_pressed}">EN</button>
      </div>
    </div>
  </header>
  <div class="wrap">
    <section class="hero">
      <div>
        <p class="eyebrow">{bi("Skill 质量解读报告", "Skill quality interpretation report")}</p>
        <h1>{esc(name)}</h1>
        <p class="lead">{bi(cover_lead_zh(model), cover_lead_en(model))}</p>
        <div class="badges">
          {cover_badge_html}
        </div>
      </div>
      <aside class="hero-card" aria-label="score summary">
        <div class="score-big"><strong>{score['total']}</strong><span>/ 100</span></div>
        <div class="decision"><strong>{bi("建议：", "Recommendation:")}</strong>{esc(score['recommendation'])}</div>
        {render_kpis(model, labels)}
      </aside>
    </section>
    <main id="main" class="layout">
      {side_nav}
      <article>{''.join(sections)}</article>
      {render_aside(model)}
    </main>
  </div>
  <script>{js}</script>
</body>
</html>
"""
    return html_doc


def render_structure(model: dict[str, Any]) -> str:
    dirs = model["inventory"]["directories"]
    rows = "".join(f"<tr><td>{esc(k)}</td><td class='num'>{v}</td></tr>" for k, v in dirs.items())
    return (
        render_analysis_panel(structure_summary_zh(model), structure_summary_en(model))
        + f'<article class="panel"><table><thead><tr><th>{bi("目录", "Directory")}</th><th class="num">{bi("文件数", "Files")}</th></tr></thead><tbody>{rows}</tbody></table></article>'
    )


def render_disclosure(model: dict[str, Any]) -> str:
    tokens = model["skill_md"]["token_estimate"]
    refs = model["metrics"]["reference_count"]
    scripts = model["metrics"]["script_count"]
    text = f"入口约 {tokens} Token，参考资料 {refs} 个，脚本 {scripts} 个。"
    if tokens <= 1400 and refs:
        text += " 入口相对克制，Agent 先读入口就能知道怎么触发；更长的解释可以继续放在 references/ 里。"
    elif tokens > 2500:
        text += " 入口偏重，第一次加载就会占掉不少上下文，建议把长示例、命令表和背景说明继续移入 references/。"
    else:
        text += " 如果后续还要加入更多示例，优先放到参考文件，不要继续堆在 SKILL.md 里。"
    en = f"The entrypoint is about {tokens} Token, with {refs} references and {scripts} scripts. Progressive disclosure is judged by how much detail is moved out of SKILL.md."
    return render_analysis_panel(text, en)


def render_script_review(model: dict[str, Any]) -> str:
    scans = model["static_scan"]
    rows = [
        ("危险命令", len(operational_hits(scans["dangerous_commands"], "dangerous_commands"))),
        ("网络访问", len(operational_hits(scans["network_access"], "network_access"))),
        ("密钥线索", len(operational_hits(scans["secret_access"], "secret_access"))),
        ("提示注入", len(operational_hits(scans["prompt_injection"], "prompt_injection"))),
        ("隐藏字符", len(scans["hidden_chars"])),
    ]
    html_rows = "".join(f"<tr><td>{label}</td><td class='num'>{value}</td></tr>" for label, value in rows)
    total_hits = sum(value for _label, value in rows)
    intro_zh = f"静态扫描不运行目标代码，只看危险命令、网络访问、密钥线索、提示注入和隐藏字符。本次在可执行面和文本面共发现 {total_hits} 个需要关注的扫描命中。"
    intro_en = f"The script section performs static scanning only. It found {total_hits} scan hits across executable and text surfaces."
    return (
        render_analysis_panel(intro_zh, intro_en)
        + f'<article class="panel"><table><thead><tr><th>{bi("静态扫描项", "Static scan item")}</th><th class="num">{bi("命中数", "Hits")}</th></tr></thead><tbody>{html_rows}</tbody></table></article>'
    )


def render_patterns(model: dict[str, Any]) -> str:
    patterns = model["design_patterns"]
    return (
        render_analysis_panel(
            "值得学习的部分可以作为同类 Skill 的写法参考；谨慎模仿的部分不一定错误，但复制前要确认场景、权限和维护成本是否匹配。",
            "The design pattern section separates reusable strengths from patterns that should be copied with caution.",
        )
        +
        '<div class="grid-2">'
        '<article class="panel"><h3>' + bi("值得学习", "Worth learning") + "</h3>" + render_list(patterns["strengths"]) + "</article>"
        '<article class="panel"><h3>' + bi("谨慎模仿", "Copy with caution") + "</h3>" + render_list(patterns["anti_patterns"]) + "</article>"
        "</div>"
    )


def render_security(model: dict[str, Any]) -> str:
    findings = [finding for finding in model["findings"] if finding["dimension_key"] == "safety_permissions"]
    if not findings:
        zh = "静态扫描没有发现高优先级安全问题，当前规则未命中危险命令、网络访问、密钥线索、提示注入或隐藏字符。这个结果适合作为采用前筛查，不能替代人工安全审计。"
        en = "Static scanning found no high-priority safety findings. This means no current rule hit was found, not that the Skill has passed a full security audit."
        return render_analysis_panel(zh, en)
    return render_findings(findings)


def render_prompts() -> str:
    prompts = [
        "请解读这个 Skill 的用途、适用场景、触发方式、输入输出要求和最佳使用方法，并生成中文 HTML 报告。",
        "请重点分析这个 Skill 的 SKILL.md 结构、脚本设计、渐进披露方式和安全风险，给出 100 分评分和改进路线图。",
        "请把这个 Skill 当作学习样例，提炼其中值得复用的设计模式，同时指出不建议模仿的写法。",
    ]
    blocks = []
    for idx, prompt in enumerate(prompts, start=1):
        blocks.append(f'<article class="panel prompt"><button class="copy-button" data-copy-source="#prompt-{idx}" data-copied-label="已复制">复制</button><pre id="prompt-{idx}"><code>{esc(prompt)}</code></pre></article>')
    return "".join(blocks)


def render_failures() -> str:
    rows = [
        ("没有识别到 Skill", "缺少 SKILL.md 或路径错误", "标记规范兼容失败"),
        ("分数较高但风险严重", "红线规则命中", "推荐动作降级为暂缓使用"),
        ("报告没有证据", "发现项未绑定来源", "降低置信度并补证据"),
        ("HTML 打印错位", "CSS 缺少打印规则", "使用打印媒体样式复核"),
    ]
    body = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in rows)
    return (
        render_analysis_panel("报告不可靠通常来自四类问题：目标路径错误、证据缺失、红线风险导致建议降级、HTML 打印样式异常。这些问题属于解释器失效模式，不等同于目标 Skill 的业务执行失败。", "Failure troubleshooting explains why the report may be incomplete, degraded, or untrusted.")
        + f'<article class="panel"><table><thead><tr><th>{bi("失败模式", "Failure mode")}</th><th>{bi("可能原因", "Likely cause")}</th><th>{bi("处理", "Handling")}</th></tr></thead><tbody>{body}</tbody></table></article>'
    )


def render_roadmap_html(items: list[dict[str, str]]) -> str:
    blocks = []
    for item in items:
        blocks.append(
            '<article class="panel">'
            f'<span class="tag">{esc(item["priority"])}</span>'
            f'<h3>{esc(item["title"])}</h3>'
            f'<p>{esc(item["action"])}</p>'
            f'<p><strong>验收：</strong>{esc(item["acceptance"])}</p>'
            "</article>"
        )
    return render_analysis_panel("优先处理最影响采用的缺口。每一项都包含动作和验收标准，修完后可以重新跑报告，确认分数、风险和建议是否变化。", "The roadmap focuses on the highest-priority issues and pairs each action with acceptance criteria.") + "".join(blocks)


def render_appendix(model: dict[str, Any]) -> str:
    tree = "\n".join(item["path"] for item in model["inventory"]["largest_files"])
    payload = json.dumps(
        {
            "source": model["source"],
            "scorecard": model["scorecard"],
            "metrics": model["metrics"],
        },
        ensure_ascii=False,
        indent=2,
    )
    return (
        render_analysis_panel(
            "附录放的是原始材料和机器可读指标，适合复查报告是否算错、是否漏扫、是否被大文件或生成物影响。一般读者不需要从这里开始，只有要复核证据或二次处理数据时才需要展开。",
            "The appendix keeps raw metrics and large-file details for audit or downstream processing.",
        )
        + '<details open><summary>最大文件</summary><pre class="file-tree"><code>'
        + esc(tree)
        + "</code></pre></details>"
        '<details><summary>原始指标</summary><pre><code>'
        + esc(payload)
        + "</code></pre></details>"
    )


def write_outputs(model: dict[str, Any], out_dir: Path, languages: list[str], formats: set[str]) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, str] = {}
    if "json" in formats:
        analysis_path = out_dir / "analysis.json"
        findings_path = out_dir / "findings.json"
        analysis_path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
        findings_path.write_text(json.dumps(model["findings"], ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts["analysis_json"] = str(analysis_path)
        artifacts["findings_json"] = str(findings_path)
    if "html" in formats:
        for lang in languages:
            suffix = "en" if lang == "en" else "zh-CN"
            path = out_dir / f"report.{suffix}.html"
            path.write_text(render_report(model, lang), encoding="utf-8")
            artifacts[f"report_{suffix}_html"] = str(path)
    if "markdown" in formats or "md" in formats:
        summary_path = out_dir / "summary.md"
        summary_path.write_text(render_summary(model), encoding="utf-8")
        artifacts["summary_md"] = str(summary_path)
    qa = build_qa(model, artifacts)
    qa_path = out_dir / "qa_report.json"
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    artifacts["qa_report_json"] = str(qa_path)
    return artifacts


def render_summary(model: dict[str, Any]) -> str:
    score = model["scorecard"]
    lines = [
        f"# {model['metadata'].get('name', 'Skill')} 解读摘要",
        "",
        f"- 总分：{score['total']} / 100，等级：{score['grade']}，风险：{zh_risk(score['risk_level'])}",
        f"- 推荐动作：{score['recommendation']}",
        f"- 文件数：{model['inventory']['file_count']}，脚本数：{model['metrics']['script_count']}，参考资料：{model['metrics']['reference_count']}",
        "",
        "## 最高优先级发现",
    ]
    for finding in model["findings"][:5]:
        lines.append(f"- [{finding['severity']}] {finding['summary']}：{finding['recommendation']}")
    lines.append("")
    lines.append("## 下一步")
    for item in model["roadmap"]:
        lines.append(f"- {item['priority']} {item['title']}：{item['action']}")
    lines.append("")
    return "\n".join(lines)


def build_qa(model: dict[str, Any], artifacts: dict[str, str]) -> dict[str, Any]:
    dims_total = sum(item["score"] for item in model["scorecard"]["dimensions"].values())
    html_checks = {}
    for key, path in artifacts.items():
        if path.endswith(".html"):
            text = Path(path).read_text(encoding="utf-8")
            html_checks[key] = {
                "has_sticky_topbar": "position: sticky" in text and "topbar" in text,
                "has_radar_chart": "评分雷达" in text or "Score" in text,
                "has_section_anchors": all(f'id="{anchor}"' in text for anchor, _label in NAV_ZH[:6]),
                "has_language_switch": 'data-set-lang="zh-CN"' in text and 'data-set-lang="en"' in text,
                "has_default_chinese": '<html lang="zh-CN">' in text or key.endswith("en_html"),
                "no_external_cdn": "https://cdn" not in text and "http://cdn" not in text,
            }
    return {
        "generated_at": now_iso(),
        "score_sum_matches": dims_total == model["scorecard"]["total"],
        "dimension_total": dims_total,
        "reported_total": model["scorecard"]["total"],
        "evidence_coverage": model["metrics"]["evidence_coverage"],
        "artifact_exists": {key: Path(path).exists() for key, path in artifacts.items()},
        "html_checks": html_checks,
    }


def parse_csv_arg(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def run_analyze(args: argparse.Namespace) -> int:
    tmp: tempfile.TemporaryDirectory[str] | None = None
    try:
        root, tmp, archive_warnings = resolve_target(Path(args.target), args.max_file_mb, args.max_total_mb)
        model = analyze(root, args.target, archive_warnings, args.max_file_mb)
        languages = parse_csv_arg(args.lang)
        languages = ["en" if item.lower() in {"en", "en-us"} else "zh-CN" for item in languages]
        formats = set(parse_csv_arg(args.format))
        artifacts = write_outputs(model, Path(args.out), languages, formats)
        print(json.dumps({"ok": True, "target": str(root), "artifacts": artifacts, "score": model["scorecard"]}, ensure_ascii=False, indent=2))
        return 0
    except AnalysisError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    finally:
        if tmp:
            tmp.cleanup()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Static Agent Skill interpreter and report generator.")
    sub = parser.add_subparsers(dest="command", required=True)
    analyze_parser = sub.add_parser("analyze", help="Analyze a local Skill directory, SKILL.md, or safe zip archive.")
    analyze_parser.add_argument("target")
    analyze_parser.add_argument("--out", default="reports/generated")
    analyze_parser.add_argument("--lang", default="zh-CN", help="Comma-separated languages: zh-CN,en")
    analyze_parser.add_argument("--format", default="html,json,markdown", help="Comma-separated formats: html,json,markdown")
    analyze_parser.add_argument("--max-file-mb", type=int, default=5)
    analyze_parser.add_argument("--max-total-mb", type=int, default=50)
    analyze_parser.set_defaults(func=run_analyze)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
