# course-platform-builder

把**任意课程资源文件夹**（本地视频 / PDF / 图片 / B 站合集）变成一套可访问的学习平台：
课程目录、课时知识点、闯关题库、图文课章节考核、知识图谱、本地服务器（学生登录 + 教师端）。

内置两个关键 Agent：
- **界面与 UI 调整 Agent**（`agents/ui-adjuster.md`）
- **课程内容体系优化 Agent**（`agents/content-optimizer.md`）

## 云端仓库
- GitHub：https://github.com/zhangshirun0615/course-platform-builder
- 克隆：`git clone https://github.com/zhangshirun0615/course-platform-builder.git`
- 本机只保留工作副本，模板/脚本都有云端备份；如需私有化，可在 GitHub 设置改为 Private。

## 适用场景
- 换专业/换学科：只改 `course-config.json`，前端与功能全部复用；
- 课程资源散乱：自动扫描、合并去重、生成模块与课时；
- 需要练习与考核：按模块出题、图文课按章节考核；
- 需要教师端/学生端：本地启动器内置登录、名单、成绩接口。

## 环境要求
- Python 3.10+（Windows / macOS / Linux 均可）
- 可选：ffmpeg（读取视频时长、生成课程封面）；不装也能跑，只是时长/封面缺失

## 桌面启动器
双击桌面/开始菜单的「课程平台 Bot」即可打开图形界面（新建平台 / 扫描课程 / 生成平台 / 检查内容 / 启动平台）。
- 首次使用：launcher\install_shortcuts.ps1 创建快捷方式
- 直接运行：launcher\启动Bot.bat 或 launcher\launch.vbs
- 图标：launcher\bot.ico

## 快速开始
```bat
python bot.py new --dest D:\my-platform --title "XX专业学习平台" --resources "D:\课程资源"
python bot.py scan --platform D:\my-platform
rem 编辑 D:\my-platform\course-config.json（课程标题、分类、modules 模式）
python bot.py build --platform D:\my-platform
python bot.py check --platform D:\my-platform
python bot.py serve --platform D:\my-platform
```
浏览器打开 `http://127.0.0.1:8899/`；教师端 `#/teacher`，学生端 `#/student`。

## 让 AI Agent 使用
把本目录给任意支持文件操作的 AI Agent，并让它读 `SKILL.md`：
1. 先跑 `bot.py scan` 生成配置；
2. 把 `agents/content-optimizer.md` 作为提示词派给内容 Agent（生成大纲/知识点/题库/章节）；
3. 把 `agents/ui-adjuster.md` 派给 UI Agent（截图、改样式、回归）；
4. `bot.py build / check / serve` 验证。

## 配置说明（course-config.json）
| 字段 | 说明 |
| --- | --- |
| `platform.title/subtitle/intro/categories` | 平台品牌与分类 |
| `resourcesRoot` | 课程资源根目录（支持任意盘符） |
| `courses[].id` | 英文短 id（用于 URL 与文件） |
| `type` | `video` / `gallery` / `bilibili` / `external` |
| `roots[]` | 一个或多个课程目录：`root`（相对 resourcesRoot）、`modules`（stage/flat/gallery）、`label`、`renames`、`skip` |
| `pan` | 网盘链接 `{url,pwd}`，前端显示「网盘资源」 |
| `bilibili.bv` | B 站 BV 号（type=bilibili） |
| `url` | 外链地址（type=external） |

`modules` 规则：
- `stage`：第一层子目录作为模块（适合按章节/阶段整理的课程）；
- `flat`：全部课时归入一个模块（适合按书名/单套视频的课程）；
- `gallery`：图文资料型（PDF/图片），可配章节考核。

## 可选内容（提升质量）
- `data/outlines.json`：课程大纲（目标/知识点/考核/理论实操）
- `data/generated.json`：合并后的知识点、题库、章节考核（由 `merge_generated.py` 生成，或 Agent 直接写）
- 同名字幕：把 `.srt` 放视频旁，构建时自动转 VTT 并挂载
- 封面：构建时自动截取视频帧/第一张图；也可放 `site/assets/courses/<id>.jpg`

## 目录结构
```
course-platform-builder/
├─ bot.py / SKILL.md / BOT.md / README.md
├─ agents/        5 个 Agent 提示词
├─ scripts/       扫描、构建、检查、发布脚本
├─ template/      站点模板 zip + 启动器 + bat
└─ examples/      示例配置
```

## 云端备份与分发
```bat
python scripts\publish_repo.py --repo <owner>/<repo> --dir . --message "skill v1.0"
```
脚本用本机 Git 凭证（`git credential fill`）调 GitHub API 创建/更新仓库，token 不落盘。
建议：**云端仓库作为主副本**，本机只保留工作副本与生成后的平台，课程视频不必复制。

## 常见问题
| 问题 | 处理 |
| --- | --- |
| 扫描不到课程 | 确认 `resourcesRoot` 与子目录有视频/PDF；一级目录=一门课 |
| 视频打不开 | 启动器需运行；确认课程目录未移动；检查 `data/course_roots.json` |
| 没有知识点/题库 | 运行 content-optimizer 流程，写入 `data/generated` 后 `bot.py build` |
| 封面是黑图/没有 | 装 ffmpeg，或手动放 `site/assets/courses/<id>.jpg` |
| 想换 UI | 改 `template/site-template.zip` 的源站点，或直接改生成平台 `site/` 后 `bot.py template --from-site` |
