#!/usr/bin/env python3

from __future__ import annotations

import html
import json
from collections import Counter
from datetime import date
from pathlib import Path

from catalog_common import CATEGORIES, category_for_skill, tag_label, visible_tag_labels


GITHUB_REPO_URL = "https://github.com/yaojingang/yao-open-skills"


def text(value) -> str:
    return html.escape(str(value), quote=True)


def repo_blob(path: str) -> str:
    return f"{GITHUB_REPO_URL}/blob/main/{path}"


def repo_tree(path: str) -> str:
    return f"{GITHUB_REPO_URL}/tree/main/{path}"


def format_tags(tags) -> str:
    visible, has_more = visible_tag_labels(tags, limit=5)
    labels = [f'<span class="badge">{text(label)}</span>' for label in visible]
    if has_more:
        labels.append('<span class="badge muted">更多</span>')
    return "\n".join(labels)


def skill_search_text(skill, category) -> str:
    labels = [tag_label(tag) for tag in skill.get("tags", [])]
    parts = [
        skill["slug"],
        skill["title"],
        skill.get("summary", ""),
        category.title,
        category.short_title,
        " ".join(skill.get("tags", [])),
        " ".join(labels),
    ]
    return text(" ".join(parts).lower())


def render_card(skill) -> str:
    category = category_for_skill(skill)
    tags_html = format_tags(skill.get("tags", []))
    guide = skill.get("guide_path")
    guide_link = (
        f'<a href="{repo_blob(guide)}">使用说明</a>'
        if guide
        else '<span class="link-disabled">暂无说明</span>'
    )
    github = skill.get("github_url") or repo_tree(skill["collection_path"])
    return f"""          <article class="card" data-family="{category.slug}" data-search="{skill_search_text(skill, category)}">
            <div class="card-head">
              <p class="card-kicker">{text(category.title)}</p>
              <h4>{text(skill["title"])}</h4>
              <p class="slug"><code>{text(skill["slug"])}</code></p>
            </div>
            <div class="badge-row">
              <span class="badge strong">已发布</span>
              {tags_html}
            </div>
            <p class="desc">{text(skill.get("summary", ""))}</p>
            <div class="meta-list">
              <span><b>适合任务：</b>{text(category.description)}</span>
              <span><b>收录路径：</b><code>{text(skill["collection_path"])}</code></span>
            </div>
            <div class="links">
              <a href="{repo_blob(skill["collection_path"] + "/SKILL.md")}">查看 Skill</a>
              {guide_link}
              <a href="{text(github)}">GitHub 目录</a>
            </div>
          </article>"""


def render_category(category, skills) -> str:
    if not skills:
        return ""
    cards = "\n".join(render_card(skill) for skill in skills)
    return f"""      <div class="category" id="{category.slug}" data-category="{category.slug}">
        <h3>{text(category.title)} <span>{category.slug} · {len(skills)}</span></h3>
        <p class="category-desc">{text(category.description)}</p>
        <div class="cards">
{cards}
        </div>
      </div>"""


def render_nav_panel(counts: Counter) -> str:
    return "\n".join(
        f'            <a href="#{category.slug}" data-filter-link="{category.slug}">{text(category.title)} <span>{counts[category.slug]}</span></a>'
        for category in CATEGORIES
        if counts[category.slug]
    )


def render_filters(counts: Counter) -> str:
    buttons = ['          <button class="filter" type="button" data-filter="all" aria-pressed="true">全部</button>']
    buttons.extend(
        f'          <button class="filter" type="button" data-filter="{category.slug}" aria-pressed="false">{text(category.short_title)} <span>{counts[category.slug]}</span></button>'
        for category in CATEGORIES
        if counts[category.slug]
    )
    return "\n".join(buttons)


def render_index(registry) -> str:
    skills = sorted(registry.get("skills", []), key=lambda item: item["slug"])
    grouped = {category.slug: [] for category in CATEGORIES}
    for skill in skills:
        grouped[category_for_skill(skill).slug].append(skill)

    counts = Counter({category.slug: len(items) for category, items in ((category, grouped[category.slug]) for category in CATEGORIES)})
    published_count = sum(1 for skill in skills if skill.get("sync_status") == "published")
    guide_count = sum(1 for skill in skills if skill.get("guide_path"))
    updated_at = registry.get("updated_at") or date.today().isoformat()

    categories_html = "\n\n".join(render_category(category, grouped[category.slug]) for category in CATEGORIES if grouped[category.slug])

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Yao Open Skills 导航</title>
  <meta name="description" content="Yao Open Skills 的公开导航页，帮助用户按任务类型选择 Skill，并跳转到 GitHub 查看使用说明和源码入口。">
  <link rel="stylesheet" href="assets/css/tokens.css">
  <link rel="stylesheet" href="assets/css/base.css">
  <link rel="stylesheet" href="assets/css/layout.css">
  <link rel="stylesheet" href="assets/css/components.css">
</head>
<body>
  <a class="skip-link" href="#catalog">跳到 Skill 目录</a>
  <nav class="site-nav" aria-label="Yao Open Skills 导航">
    <div class="nav-inner">
      <a class="nav-brand" href="#top">Yao Open Skills</a>
      <div class="nav-actions">
        <a class="nav-link" href="#catalog" data-show-all>查看全部</a>
        <details class="nav-menu">
          <summary>按任务选择</summary>
          <div class="nav-panel">
{render_nav_panel(counts)}
          </div>
        </details>
        <a class="nav-link" href="{GITHUB_REPO_URL}">GitHub</a>
        <a class="nav-link" href="{repo_blob("README.md")}">README</a>
        <a class="nav-link" href="{repo_blob("registry/skills.json")}">Skill 数据表</a>
      </div>
    </div>
  </nav>

  <main class="page" id="top">
    <header class="hero">
      <div>
        <p class="eyebrow">OpenYao · 公开 Skill 导航 · {text(updated_at)}</p>
        <h1>按任务找到合适的 AI Skill</h1>
        <p class="tagline">这里收录了 {len(skills)} 个公开 Skill。你可以按任务类型筛选，也可以直接搜索关键词，再进入 GitHub 查看使用说明、源码入口和维护边界。</p>
        <div class="hero-actions">
          <a class="button primary" href="#catalog">浏览 Skill</a>
          <a class="button" href="{repo_blob("README.md")}">查看 README</a>
          <a class="button" href="{repo_blob("docs/repository-design.md")}">仓库设计</a>
          <a class="button" href="{repo_blob("docs/publishing-rules.md")}">发布规则</a>
        </div>
      </div>

      <aside class="hero-panel" aria-label="仓库概览">
        <div class="stat-grid">
          <div class="stat"><strong>{len(skills)}</strong><span>公开 Skill</span></div>
          <div class="stat"><strong>{guide_count}</strong><span>说明文档</span></div>
          <div class="stat"><strong>{len([category for category in CATEGORIES if counts[category.slug]])}</strong><span>任务分类</span></div>
          <div class="stat"><strong>{published_count}</strong><span>已发布入口</span></div>
        </div>
        <p class="eyebrow">从判断到交付</p>
        <div class="flow" aria-hidden="true">
          <div class="flow-row"><div class="flow-label">先判断</div><div class="flow-bar"><div class="flow-dot blue"></div><div class="flow-dot teal"></div><div class="flow-dot rust"></div><div class="flow-dot green"></div></div></div>
          <div class="flow-row"><div class="flow-label">再生产</div><div class="flow-bar"><div class="flow-dot rust"></div><div class="flow-dot plum"></div><div class="flow-dot teal"></div><div class="flow-dot amber"></div></div></div>
          <div class="flow-row"><div class="flow-label">可治理</div><div class="flow-bar"><div class="flow-dot green"></div><div class="flow-dot blue"></div><div class="flow-dot plum"></div><div class="flow-dot rust"></div></div></div>
        </div>
      </aside>
    </header>

    <section class="section" id="catalog">
      <div class="section-head">
        <p class="section-num">01 · Choose</p>
        <div>
          <h2 class="section-title">按你的任务选择 Skill</h2>
          <p class="section-lede">默认展示全部 Skill。筛选按钮适合先按大类浏览，搜索框适合直接找“贝叶斯”“需求”“安全”“教程”“微信读书”等具体关键词。</p>
        </div>
      </div>

      <div class="toolbar" role="search">
        <input class="search" id="search" type="search" placeholder="搜索：需求、贝叶斯、商业模式、安全、教程、微信读书..." aria-label="搜索 Skill">
        <div class="filters" aria-label="按任务类型筛选">
{render_filters(counts)}
        </div>
      </div>

{categories_html}
    </section>

    <footer class="footer">
      <p>这个导航页由 <code>registry/skills.json</code> 自动生成。新增或更新 Skill 后，运行 <code>python3 scripts/render_collection_pages.py</code> 即可同步刷新 README 目录和 HTML 导航。</p>
    </footer>
  </main>

  <script src="assets/js/navigation.js"></script>
</body>
</html>
"""


def main():
    repo_root = Path(__file__).resolve().parents[1]
    registry_path = repo_root / "registry" / "skills.json"
    output_path = repo_root / "index.html"

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    output_path.write_text(render_index(registry), encoding="utf-8")
    print(f"Rendered HTML navigation: {output_path.relative_to(repo_root)}")


if __name__ == "__main__":
    main()
