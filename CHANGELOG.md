# CHANGELOG

## v1.0.0 — 2026-11-08
首个可复用版本，从「数字媒体设计学习平台」沉淀而来：

- 通用构建器 `scripts/build_platform.py`：视频课 / 图文课 / B 站课 / 外链课，多根目录合并去重，字幕自动转 VTT，知识点/题库/章节考核/知识图谱/封面。
- 配置驱动 `course-config.json`：换专业/学科只改配置。
- `bot.py`：new / scan / build / check / serve / agents / template。
- 5 个 Agent 提示词：
  - `ui-adjuster`（界面与 UI 调整）
  - `content-optimizer`（课程内容体系优化）
  - `course-scanner` / `lesson-writer` / `subtitle-translator`
- 模板：站点骨架 zip（UI 引擎）+ 本地启动器（学生登录/教师端接口/视频 Range/访问控制）+ 启动 bat。
- 云端分发：`scripts/publish_repo.py`（GitHub API，凭证不落盘）。
- 验证：用 2 门示例课（视频 + 图文）跑通 new → scan → build → check → serve。
