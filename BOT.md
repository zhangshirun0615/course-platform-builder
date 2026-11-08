# BOT 说明 · course-platform-bot

`bot.py` 是一个**命令行编排器**：它把「建平台、扫课程、生成数据、检查、启动」串起来。
真正的智能工作（内容体系、UI 调整）由调用它的 AI Agent 按 `SKILL.md` + `agents/*.md` 完成。

## 安装
1. 复制整个 `course-platform-builder/` 目录到本机（或从云端仓库 clone）。
2. 需要 Python 3.10+；视频封面/时长需要 ffmpeg（可放在 `<platform>/tools/ffmpeg.exe`，或用系统 ffmpeg）。
3. 无需 npm 构建；页面是纯静态 ES Modules。

## 命令
| 命令 | 作用 |
| --- | --- |
| `bot.py new --dest D:\my-platform --title "平台名" --resources D:\课程资源` | 从模板创建平台（站点、启动器、配置骨架） |
| `bot.py scan --platform <dir> --resources <dir>` | 扫描资源目录，生成 `course-config.json` 草稿 |
| `bot.py build --platform <dir>` | 生成 catalog/courses/quizzes/封面/图谱/字幕索引 |
| `bot.py check --platform <dir> [--strict]` | 检查知识点/题库/章节覆盖 |
| `bot.py serve --platform <dir>` | 启动本地服务器（默认 8899 端口） |
| `bot.py agents [name]` | 列出/打印内置 Agent 提示词 |
| `bot.py template --from-site <site>` | 从现有站点重新打包 UI 模板（升级 UI 后使用） |

## 目录
```
course-platform-builder/
├─ bot.py                  # 入口
├─ SKILL.md                # 能力说明（给 AI Agent 看）
├─ BOT.md                  # 本文件（给人看）
├─ agents/                 # 5 个内置 Agent 提示词
├─ scripts/
│  ├─ scan_courses.py      # 资源扫描 → 配置草稿
│  ├─ build_platform.py    # 通用构建器
│  ├─ check_content.py     # 覆盖率检查
│  └─ publish_repo.py      # 把本 skill 发布到 GitHub（云端备份/分发）
├─ template/
│  ├─ site-template.zip    # 站点骨架（UI/样式/脚本）
│  ├─ launcher.py          # 本地服务器
│  └─ 启动学习平台.bat
└─ examples/course-config.example.json
```

## 与 AI Agent 配合
1. AI 读 `SKILL.md`，执行 `bot.py new/scan`；
2. 把 `agents/content-optimizer.md` 作为提示词交给一个子 Agent，产出大纲/知识点/题库/章节；
3. 把 `agents/ui-adjuster.md` 交给另一个子 Agent 做界面调整；
4. 运行 `bot.py build / check / serve` 验证。

## 云端备份
```bat
python scripts\publish_repo.py --repo <owner>/<repo> --dir . --message "course-platform-builder v1.0"
```
使用本机 Git 凭证（`git credential fill`）调用 GitHub API 创建/更新仓库，不需要把 token 写进文件。
