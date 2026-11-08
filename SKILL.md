---
name: course-platform-builder
description: 把一个课程资源文件夹（视频/PDF/图片/B站链接）变成可访问的学习平台：自动扫描课程、生成课程目录、课时知识点、闯关题库、章节考核、知识图谱与本地服务器；内置「界面与 UI 调整 Agent」和「课程内容体系优化 Agent」。适用于任意专业/学科。
version: 1.0.0
author: 数字媒体设计学习平台
tags: [课程平台, 学习平台, 教育, 知识图谱, 题库, 静态站点, 多学科]
---

# course-platform-builder · 任意课程 → 学习平台

## 什么时候用
当用户有一批课程资源（本地视频、PDF、图片、B 站合集），希望：
- 有一个能浏览课程、看视频、看资料、做练习、看知识图谱的网站；
- 教师能管理课程/学生/成绩，学生能登录看成绩；
- 换专业、换学科时，不用重写前端，只换课程配置与内容。

## 产出
- 一套可直接双击启动的本地平台（`site/` 静态站点 + Python 启动器）；
- 课程目录、课程详情、课时知识点、模块题库、图文课章节考核、知识图谱；
- 可选的在线镜像（GitHub Pages 等静态托管）；
- 一份《使用与维护手册》Word 文档（可选）。

## 快速开始
```bat
python bot.py new --dest D:\my-platform --title "XX专业学习平台" --resources "D:\课程资源"
python bot.py scan --platform D:\my-platform
rem 编辑 D:\my-platform\course-config.json（课程标题/分类/模块模式）
python bot.py build --platform D:\my-platform
python bot.py check --platform D:\my-platform
python bot.py serve --platform D:\my-platform
```

## 工作流（Agent 视角）
1. **扫描**：`bot.py scan` 生成 `course-config.json`；检查类型/模块模式/分类。
2. **内容体系**（最重要）：派 `content-optimizer` Agent，按提示词完成
   - `data/outlines.json`（课程大纲、目标、考核、理论实操）
   - `data/generated/kp-*.json` / `quiz-*.json` / `gallery-chapters.json`
   - 课时命名、英文翻译、字幕匹配
   然后 `merge_generated.py` → `bot.py build` → `bot.py check --strict`。
3. **界面**：派 `ui-adjuster` Agent，按提示词检查 1440/1024/768/390 截图、导航、卡片、表格、图谱、教师端。
4. **启动与交付**：`bot.py serve`；需要外网时用静态镜像或隧道；需要手册时运行手册脚本。
5. **迭代**：新增课程 → 改 `course-config.json` → `bot.py build`；内容更新 → 回到第 2 步。

## 内置 Agent
| Agent | 文件 | 职责 |
| --- | --- | --- |
| 界面与 UI 调整 | `agents/ui-adjuster.md` | 设计令牌、页面布局、响应式、可访问性、截图回归 |
| 课程内容体系优化 | `agents/content-optimizer.md` | 章节逻辑、知识点、题库、章节考核、大纲、翻译、图谱质量 |
| 课程扫描 | `agents/course-scanner.md` | 资源 → course-config 草稿 |
| 课时/题库 Writer | `agents/lesson-writer.md` | 批量生成知识点与模块题库 JSON |
| 字幕匹配翻译 | `agents/subtitle-translator.md` | SRT 匹配、翻译、自动 VTT |

查看提示词：`python bot.py agents` 或 `python bot.py agents ui-adjuster`。

## 数据契约（不要改坏）
```
<platform>/
  course-config.json        # 课程配置（唯一需要人工编辑的入口）
  site/                     # 静态站点（模板复制）
    data/catalog.json       # 构建产物
    data/courses/<id>.json  # 构建产物
    data/quizzes/<id>.json  # 构建产物
    assets/courses/<id>.jpg # 构建产物（封面）
  data/outlines.json        # 课程大纲（可选输入）
  data/generated.json       # 知识点/题库/章节（可选输入，由 merge_generated 合并）
  data/course_roots.json    # 课程 → 磁盘目录映射（启动器用）
  scripts/launcher.py       # 本地服务器（学生登录/教师端接口/视频）
```
详细字段见 `README.md` 与 `examples/course-config.example.json`。

## 质量门槛
- `bot.py check --strict` 通过：每课有知识点、每模块有题、图文课有章节考核；
- 首页/课程页/课时页/题库页/图谱页 移动端无横向溢出；
- 视频可播放（本地直连或网盘回退），有字幕的视频显示字幕；
- 教师端/学生端在本地服务器可用，在线镜像不暴露 `/api`。

## 存储与分发
- 云端主副本：https://github.com/zhangshirun0615/course-platform-builder
- 本地工作副本：工作区 `skills/course-platform-builder/`（约 0.5 MB + 431 KB 模板 zip）
- 更新云端：`python scripts/publish_repo.py --repo course-platform-builder --dir . --message "update"`
- 换机器：clone 云端仓库即可；课程视频不复制、不转码（除特殊需要），由启动器按原路径直连，避免重复占用空间。
