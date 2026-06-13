# HTML 导航页维护说明

`index.html` 是 `yao-open-skills` 的 GitHub Pages 导航页，面向“先找能用的 Skill”的读者。

页面参考 `yao-geo-skills` 的静态导航结构，保留暖纸面、粘性顶部导航、分类筛选、搜索框和 Skill 卡片。它不是手工维护页面，而是从 `registry/skills.json` 自动生成。

## 生成命令

新增、刷新或发布 Skill 后，统一运行：

```bash
python3 scripts/render_collection_pages.py
```

这个命令会同时更新：

- `README.md` 里的 Skill 导航目录
- `index.html` 静态导航页

如果只想单独刷新 HTML 导航页，可以运行：

```bash
python3 scripts/render_site_nav.py
```

## 事实源

- `registry/skills.json`：Skill 名称、中文说明、标签、路径和 GitHub 地址。
- `scripts/catalog_common.py`：中文标签、首页分类和 Skill 到分类的映射。
- `assets/css/`：导航页设计系统和组件样式。
- `assets/js/navigation.js`：搜索、分类筛选和顶部菜单交互。

不要直接改 `index.html` 里的卡片内容。要改 Skill 文案、标签或链接，先改 `registry/skills.json` 或 `catalog_common.py`，再重新生成页面。

## 页面结构

```text
index.html
assets/
  css/
    tokens.css
    base.css
    layout.css
    components.css
  js/
    navigation.js
```

## 设计约束

- 保持“目录导航页”定位，不做营销型落地页。
- 保持暖纸面、墨色正文、蓝绿锈紫分类色和宋体标题。
- 卡片只展示读者选择 Skill 需要的信息：适合任务、摘要、标签、说明和 GitHub 入口。
- 新分类必须先写入 `catalog_common.py`，不要在 HTML 里临时加一套样式。
- 移动端必须保持中文按钮、筛选标签和 Skill 名称横向可读，不能变成单字竖排。
