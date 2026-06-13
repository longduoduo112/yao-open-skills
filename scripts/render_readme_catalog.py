#!/usr/bin/env python3

import json
from pathlib import Path

from catalog_common import visible_tag_labels


START_MARKER = "<!-- catalog:start -->"
END_MARKER = "<!-- catalog:end -->"


def escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def format_tags(tags):
    visible, has_more = visible_tag_labels(tags)
    if not visible:
        return "未标注"
    rendered = "、".join(f"`{label}`" for label in visible)
    return f"{rendered} 等" if has_more else rendered


def format_nav(skill):
    links = []
    if skill.get("guide_path"):
        links.append("[说明]({path})".format(path=skill["guide_path"]))
    links.append("[Skill]({path}/SKILL.md)".format(path=skill["collection_path"]))
    links.append("[目录]({path})".format(path=skill["collection_path"]))
    if skill.get("github_url"):
        links.append("[GitHub]({url})".format(url=skill["github_url"]))
    return " · ".join(links)


def render_table(skills):
    lines = [
        START_MARKER,
        "这个目录从 `registry/skills.json` 自动生成，优先帮助读者判断每个 Skill 解决什么问题，以及从哪里开始阅读。",
        "",
        "| Skill | 简体中文说明 | 主题标签 | 导航 |",
        "| --- | --- | --- | --- |",
    ]

    for skill in skills:
        summary = escape_table_cell(skill["summary"])
        lines.append(
            "| [{title}]({collection_path}/SKILL.md)<br><sub>`{slug}`</sub> | {summary} | {tags} | {nav} |".format(
                title=skill["title"],
                slug=skill["slug"],
                collection_path=skill["collection_path"],
                summary=summary,
                tags=format_tags(skill.get("tags", [])),
                nav=format_nav(skill),
            )
        )

    lines.append(END_MARKER)
    return "\n".join(lines)


def main():
    repo_root = Path(__file__).resolve().parents[1]
    registry_path = repo_root / "registry" / "skills.json"
    readme_path = repo_root / "README.md"

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    skills = sorted(registry.get("skills", []), key=lambda item: item["slug"])
    table = render_table(skills)

    readme = readme_path.read_text(encoding="utf-8")
    if START_MARKER not in readme or END_MARKER not in readme:
        raise SystemExit("README catalog markers not found.")

    start = readme.index(START_MARKER)
    end = readme.index(END_MARKER) + len(END_MARKER)
    updated = readme[:start] + table + readme[end:]
    readme_path.write_text(updated, encoding="utf-8")
    print(f"Rendered catalog for {len(skills)} skill(s).")


if __name__ == "__main__":
    main()
