# -*- coding: utf-8 -*-
"""生成《课程平台 Bot · 使用与管理说明》Word 文档。"""
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

PKG = Path(__file__).resolve().parent.parent
OUT = PKG / "docs" / "课程平台Bot_使用与管理说明.docx"
ICON = PKG / "launcher" / "bot.png"

ACCENT = RGBColor(0xC4, 0x5A, 0x1E)
INK = RGBColor(0x22, 0x22, 0x22)
MUTED = RGBColor(0x66, 0x66, 0x66)
TEAL = RGBColor(0x1E, 0x6F, 0x5C)
BODY, HEAD, MONO = "宋体", "微软雅黑", "Consolas"

doc = Document()


def set_font(run, name, size=None, bold=None, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def para(text="", size=10.5, bold=False, color=INK, align=None, before=0, after=4, indent=None):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    if indent:
        p.paragraph_format.first_line_indent = Cm(indent)
    if text:
        r = p.add_run(text)
        set_font(r, BODY, size, bold, color)
    return p


def h1(text):
    p = doc.add_heading(level=1)
    r = p.add_run(text)
    set_font(r, HEAD, 16, True, ACCENT)
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(8)
    return p


def h2(text):
    p = doc.add_heading(level=2)
    r = p.add_run(text)
    set_font(r, HEAD, 13, True, INK)
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(5)
    return p


def h3(text):
    p = doc.add_heading(level=3)
    r = p.add_run(text)
    set_font(r, HEAD, 11.5, True, TEAL)
    p.paragraph_format.space_before = Pt(9)
    p.paragraph_format.space_after = Pt(4)
    return p


def bullets(items, size=10.5):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.left_indent = Cm(0.7)
        r = p.add_run(it)
        set_font(r, BODY, size)


def shade_cell(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def shade_para(p, fill):
    pPr = p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    pPr.append(shd)


def code(lines):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(6)
    shade_para(p._p, "F4F1EC")
    for i, ln in enumerate(lines):
        r = p.add_run(ln)
        set_font(r, MONO, 8.5, False, RGBColor(0x33, 0x33, 0x33))
        if i < len(lines) - 1:
            r.add_break()
    return p


def table(headers, rows, widths=None, size=9.5):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = True
    for i, htext in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = ""
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(htext)
        set_font(r, HEAD, size, True, RGBColor(0xFF, 0xFF, 0xFF))
        shade_cell(c, "C45A1E")
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            r = p.add_run(str(val))
            set_font(r, BODY, size, False, INK)
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Cm(w)
    return t


def caption(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run(text)
    set_font(r, BODY, 9, False, MUTED)


def note_box(title, body, fill="FFF6EC"):
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    cell = t.rows[0].cells[0]
    cell.text = ""
    shade_cell(cell, fill)
    p = cell.paragraphs[0]
    r = p.add_run(title + "  ")
    set_font(r, HEAD, 9.5, True, ACCENT)
    r2 = p.add_run(body)
    set_font(r2, BODY, 9.5, False, INK)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def page_number_footer(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("第 ")
    set_font(r, BODY, 8.5, False, MUTED)
    for instr, placeholder in ((" PAGE ", "1"), (" NUMPAGES ", "1")):
        rr = p.add_run()
        fld = OxmlElement("w:fldChar")
        fld.set(qn("w:fldCharType"), "begin")
        rr._r.append(fld)
        rr = p.add_run()
        it = OxmlElement("w:instrText")
        it.set(qn("xml:space"), "preserve")
        it.text = instr
        rr._r.append(it)
        rr = p.add_run()
        sep = OxmlElement("w:fldChar")
        sep.set(qn("w:fldCharType"), "separate")
        rr._r.append(sep)
        rr = p.add_run(placeholder)
        rr = p.add_run()
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        rr._r.append(end)
        r = p.add_run(" 页 / 共 " if instr == " PAGE " else " 页")
        set_font(r, BODY, 8.5, False, MUTED)


# 页面
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.top_margin, sec.bottom_margin = Cm(2.2), Cm(2.0)
sec.left_margin, sec.right_margin = Cm(2.3), Cm(2.3)
sec.different_first_page_header_footer = True
page_number_footer(sec)
hp = sec.header.paragraphs[0]
hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = hp.add_run("课程平台 Bot · 使用与管理说明")
set_font(r, HEAD, 8.5, False, MUTED)

style = doc.styles["Normal"]
style.font.name = BODY
style.font.size = Pt(10.5)
style.element.rPr.rFonts.set(qn("w:eastAsia"), BODY)

# ============ 封面 ============
for _ in range(1):
    doc.add_paragraph()
if ICON.exists():
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(ICON), width=Cm(3.2))
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(14)
r = p.add_run("课程平台 Bot")
set_font(r, HEAD, 32, True, INK)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("使用与管理说明")
set_font(r, HEAD, 24, True, ACCENT)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(10)
r = p.add_run("任意课程资源 → 学习平台 ｜ 桌面启动器 · 命令行 · Agent · 维护与拓展")
set_font(r, HEAD, 11, False, MUTED)

doc.add_paragraph()
t = doc.add_table(rows=4, cols=2)
t.style = "Table Grid"
t.alignment = WD_TABLE_ALIGNMENT.CENTER
info = [
    ("版本", "v1.0（2026-11-08）"),
    ("本地技能目录", str(PKG)),
    ("桌面入口", "桌面 / 开始菜单 →「课程平台 Bot」"),
    ("云端仓库", "https://github.com/zhangshirun0615/course-platform-builder"),
]
for i, (k, v) in enumerate(info):
    c0, c1 = t.rows[i].cells
    for c, text, bold, font in ((c0, k, True, HEAD), (c1, v, False, MONO)):
        c.text = ""
        p = c.paragraphs[0]
        r = p.add_run(text)
        set_font(r, font, 9.5 if font == MONO else 10, bold, INK if bold else RGBColor(0x33, 0x33, 0x33))
    c0.width = Cm(3.6)
    c1.width = Cm(11.6)

doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("面向：任课教师 / 平台管理员 / 后续接手维护的同事")
set_font(r, BODY, 9.5, False, MUTED)
doc.add_page_break()

# ============ 目录 ============
h1("目录")
para("本说明共十章：第 1~3 章介绍是什么、怎么装、桌面启动器；第 4~7 章是配置与内容生产；第 8~9 章是维护与安全；第 10 章为速查与 FAQ。", size=9.5, color=MUTED)
table(
    ["章节", "内容"],
    [
        ("一、Bot 是什么", "定位、与学习平台的关系、能力清单、内置 Agent"),
        ("二、安装与环境", "环境要求、获取方式、首次安装、目录结构"),
        ("三、桌面启动器", "入口、按钮说明、典型流程、启动器常见问题"),
        ("四、命令行使用", "命令速查、完整示例、输出说明"),
        ("五、课程配置", "course-config 字段、modules 三种模式、多根目录与去重"),
        ("六、内容生产与 Agent", "推荐顺序、两个核心 Agent、数据契约、质量校验"),
        ("七、数据与文件结构", "Skill 目录、生成平台目录、关键文件"),
        ("八、管理与维护", "版本更新、模板升级、备份迁移、清理缓存、故障排查"),
        ("九、安全与规范", "密钥与数据边界、公开仓库、课程资源版权"),
        ("十、附录与 FAQ", "按钮速查、命令速查、Agent 清单、常见问题、版本记录"),
    ],
    widths=[4.6, 11.2],
    size=9.5,
)
doc.add_page_break()

# ============ 一、Bot 是什么 ============
h1("一、Bot 是什么")
para("课程平台 Bot 是一个「课程资源 → 学习平台」的自动化工具包。它由三部分组成：命令行编排器 bot.py、"
     "一套可复用的站点模板与本地服务器、以及给 AI Agent 使用的技能说明和提示词。")
para("它不替你做教学设计，而是把你已有的课程视频、PDF、图片、B 站链接整理成：课程目录、课时知识点、"
     "闯关题库、图文课章节考核、知识图谱，并生成一个能双击启动的本地学习平台。")

h2("1.1 与学习平台的关系")
bullets([
    "Bot 是「生产线」：负责建平台、扫课程、生成数据、检查、启动。",
    "平台是「产品」：生成后的网站可以独立运行、独立备份、独立部署镜像。",
    "每个专业/学科生成一套平台；Bot 本身只有约 0.6 MB，放云端仓库，本机保留工作副本即可。",
])
h2("1.2 能力清单")
table(
    ["能力", "说明"],
    [
        ("课程扫描", "自动识别视频课 / 图文课 / B 站课，生成课程配置草稿"),
        ("目录生成", "多目录合并、按文件名+大小去重、模块重命名、课时中文命名"),
        ("内容增强", "每课知识点、每模块题库、图文课章节考核、课程大纲、知识图谱、字幕"),
        ("本地服务", "静态站点 + 视频 Range + 学生登录 + 教师端接口 + 访问控制"),
        ("模板复用", "换学科只改 course-config.json，前端与功能全部复用"),
        ("云端分发", "GitHub 仓库一键发布，换机器 clone 即用"),
    ],
    widths=[3.4, 12.4],
)
h2("1.3 内置 Agent")
table(
    ["Agent", "文件", "职责"],
    [
        ("界面与 UI 调整", "agents/ui-adjuster.md", "设计令牌、布局、响应式、可访问性、截图回归"),
        ("课程内容体系优化", "agents/content-optimizer.md", "章节逻辑、大纲、知识点、题库、章节考核、翻译"),
        ("课程扫描", "agents/course-scanner.md", "资源目录 → course-config 草稿"),
        ("课时/题库 Writer", "agents/lesson-writer.md", "批量生成知识点与题库 JSON"),
        ("字幕匹配翻译", "agents/subtitle-translator.md", "SRT 匹配、翻译、自动转 VTT"),
    ],
    widths=[4.2, 5.6, 6.0],
)
note_box("怎么让 AI 干活", "把整个 skill 目录交给任意支持文件操作的 AI Agent，让它先读 SKILL.md，"
         "再按 SKILL.md 的流程调用 bot.py，并把 agents/ 下对应提示词派给子 Agent。")

# ============ 二、安装与环境 ============
doc.add_page_break()
h1("二、安装与环境")
h2("2.1 环境要求")
table(
    ["项目", "要求", "说明"],
    [
        ("操作系统", "Windows 10/11（启动器）；Bot 本身跨平台", "桌面快捷方式仅 Windows"),
        ("Python", "3.10+", "bot.py / 构建器 / 启动器均使用 Python"),
        ("ffmpeg", "可选", "读取视频时长、生成封面；不装也能运行"),
        ("磁盘", "技能包约 0.6 MB", "课程视频不复制、不转码，不额外占空间"),
    ],
    widths=[2.6, 6.4, 7.0],
)
h2("2.2 获取方式")
para("方式一（推荐）：从云端克隆。")
code(["git clone https://github.com/zhangshirun0615/course-platform-builder.git"])
para("方式二：从已有电脑复制整个 course-platform-builder 文件夹。")
h2("2.3 首次安装桌面入口")
para("进入 launcher 目录，运行一次快捷方式安装脚本：")
code(["powershell -ExecutionPolicy Bypass -File launcher\\install_shortcuts.ps1"])
bullets([
    "会在桌面和开始菜单创建「课程平台 Bot」快捷方式（橙色「课」图标）。",
    "快捷方式通过 wscript + VBS 启动 GUI，不会弹出黑色命令行窗口。",
    "移动技能目录后需要重新运行一次该脚本。",
])
h2("2.4 目录结构")
code([
    "course-platform-builder/",
    "├─ bot.py                 命令行编排器（new/scan/build/check/serve/agents/template）",
    "├─ SKILL.md               技能说明（给 AI Agent 读）",
    "├─ BOT.md                 给人看的 Bot 说明",
    "├─ README.md              快速开始与配置说明",
    "├─ agents/                5 个 Agent 提示词",
    "├─ scripts/               扫描、构建、检查、发布脚本",
    "├─ template/              站点模板 zip + 通用启动器 + 启动 bat",
    "├─ launcher/              桌面启动器（GUI、VBS、bat、图标、快捷方式脚本）",
    "└─ docs/                  本说明文档与生成脚本",
])

# ============ 三、桌面启动器 ============
h1("三、桌面启动器")
h2("3.1 入口")
bullets([
    "桌面快捷方式：双击「课程平台 Bot」。",
    "开始菜单：所有程序 →「课程平台 Bot」。",
    "直接运行：launcher\\launch.vbs（无控制台）或 launcher\\启动Bot.bat（有控制台，便于排错）。",
])
h2("3.2 按钮说明")
table(
    ["按钮", "作用", "会弹出什么"],
    [
        ("① 新建平台", "从模板创建一套新平台", "选择存放位置 → 输入平台名 → 选择课程资源目录"),
        ("② 扫描课程", "生成 course-config.json 草稿", "选择平台目录、资源目录"),
        ("③ 生成平台", "生成课程目录/课时/题库/图谱/封面", "选择平台目录"),
        ("④ 检查内容", "检查知识点、题库、章节覆盖", "选择平台目录，输出缺失项"),
        ("⑤ 启动平台", "启动本地服务并打开浏览器", "选择平台目录，自动开 8899 页面"),
        ("打开 Agent 目录", "查看 5 个 Agent 提示词", "资源管理器"),
        ("打开云端仓库", "访问 GitHub 仓库", "浏览器"),
        ("清空日志", "清空下方输出", "—"),
    ],
    widths=[3.2, 7.0, 6.0],
)
h2("3.3 典型流程")
para("新建平台 → 扫描课程 → 编辑平台目录下 course-config.json → 生成平台 → 检查内容 → 启动平台。")
bullets([
    "第 1 次：点「① 新建平台」，选择空目录，输入平台名称，选择课程资源根目录。",
    "第 2 次：点「② 扫描课程」，选择刚建好的平台目录；生成配置草稿。",
    "手工编辑 course-config.json：课程标题、分类、模块模式（stage / flat / gallery）。",
    "点「③ 生成平台」，再点「④ 检查内容」；有缺失时按提示补内容或跑内容 Agent。",
    "点「⑤ 启动平台」，浏览器自动打开 http://127.0.0.1:8899/。",
    "教师端：http://127.0.0.1:8899/#/teacher（仅本机）；学生端：/#/student。",
])
h2("3.4 启动器常见问题")
table(
    ["现象", "原因", "处理"],
    [
        ("提示未找到 Python", "python 不在 PATH", "安装 Python 3.10+ 并勾选 Add to PATH；或使用 DSH 自带 Python"),
        ("双击没反应", "快捷方式指向旧路径", "重新运行 launcher\\install_shortcuts.ps1"),
        ("窗口一闪而过", "脚本报错", "用 launcher\\启动Bot.bat 运行，查看控制台报错"),
        ("按钮点击后无输出", "命令执行中或输出过长", "等待；或改用命令行执行同一条命令"),
        ("启动平台后页面打不开", "端口被占用 / 启动器窗口已关闭", "看服务窗口提示的端口；不要关闭服务窗口"),
    ],
    widths=[4.0, 5.4, 6.8],
    size=9,
)

# ============ 四、命令行使用 ============
doc.add_page_break()
h1("四、命令行使用")
h2("4.1 命令速查")
table(
    ["命令", "作用"],
    [
        ("python bot.py new --dest <目录> --title \"平台名\" --resources <资源目录>", "从模板创建平台"),
        ("python bot.py scan --platform <平台目录> [--resources <资源目录>]", "扫描课程，生成配置草稿"),
        ("python bot.py build --platform <平台目录>", "生成 catalog / courses / quizzes / 封面 / 图谱"),
        ("python bot.py check --platform <平台目录> [--strict]", "检查内容覆盖，--strict 有缺失即失败"),
        ("python bot.py serve --platform <平台目录>", "启动本地服务器"),
        ("python bot.py agents [名称]", "列出 / 打印 Agent 提示词"),
        ("python bot.py template --from-site <站点目录>", "从现有站点重新打包 UI 模板"),
        ("python scripts\\publish_repo.py --repo <owner/repo> --dir .", "把技能包发布到 GitHub"),
    ],
    widths=[9.2, 7.0],
    size=8.8,
)
h2("4.2 完整示例")
code([
    "cd /d D:\\course-platform-builder",
    "python bot.py new --dest D:\\护理学平台 --title \"护理学学习平台\" --resources \"D:\\护理课程\"",
    "python bot.py scan --platform D:\\护理学平台",
    "rem 编辑 D:\\护理学平台\\course-config.json",
    "python bot.py build --platform D:\\护理学平台",
    "python bot.py check --platform D:\\护理学平台 --strict",
    "python bot.py serve --platform D:\\护理学平台",
])
h2("4.3 输出说明")
bullets([
    "build 结束会打印：课程数、课时数、总时长、每门课题库有无。",
    "check 会打印每门课的课时/知识点/字幕/题库板块/题数/章节数，并列出缺失项。",
    "首次 build 通常没有知识点与题库（显示「题库:无」），需要内容 Agent 补齐后再 build。",
])

# ============ 五、课程配置 ============
h1("五、课程配置（course-config.json）")
h2("5.1 字段说明")
table(
    ["字段", "必填", "说明"],
    [
        ("platform.title", "是", "平台名称，页面顶部与浏览器标题使用"),
        ("platform.subtitle / intro", "否", "副标题与首页介绍"),
        ("platform.categories", "否", "分类列表，首页筛选使用"),
        ("resourcesRoot", "是", "课程资源根目录，支持任意盘符"),
        ("courses[].id", "是", "英文短 id，用于 URL 与文件名"),
        ("courses[].type", "是", "video / gallery / bilibili / external"),
        ("courses[].title / subtitle / description", "是/否", "课程标题、副标题、简介"),
        ("courses[].category / tags / accent", "否", "分类、标签、主题色"),
        ("courses[].roots", "video/gallery 必填", "一个或多个课程目录配置"),
        ("courses[].pan", "否", "网盘链接 {url, pwd}"),
        ("courses[].bilibili.bv", "bilibili 必填", "B 站 BV 号"),
        ("courses[].url", "external 必填", "外部课程链接"),
    ],
    widths=[6.0, 3.0, 7.2],
    size=9,
)
h2("5.2 modules 三种模式")
table(
    ["模式", "含义", "适用"],
    [
        ("stage", "第一层子目录作为模块", "按章节/阶段整理的课程"),
        ("flat", "全部课时归入一个模块", "按书名/单套视频的课程"),
        ("gallery", "图文资料型（PDF/图片）", "教材、画册、扫描资料"),
    ],
    widths=[2.8, 7.0, 6.4],
)
h2("5.3 多根目录与去重")
para("一个课程可以配置多个 roots（例如把两套书合成一门课）。构建时按「文件名 + 大小」自动去重，"
     "重复的赠送视频、同名 PDF 只保留一份。roots 还支持 renames（模块改名）与 skip（跳过某目录）。")
h2("5.4 最小示例")
code([
    '{',
    '  "platform": {"title": "护理学学习平台", "subtitle": "基础护理 · 临床实训"},',
    '  "resourcesRoot": "D:\\\\护理课程",',
    '  "courses": [',
    '    {"id": "nursing-basic", "type": "video", "category": "专业核心",',
    '     "title": "基础护理学", "description": "……",',
    '     "roots": [{"root": "基础护理", "modules": "stage"}]}',
    '  ]',
    '}',
])

# ============ 六、内容生产与 Agent ============
doc.add_page_break()
h1("六、内容生产与 Agent")
h2("6.1 推荐顺序")
table(
    ["步骤", "执行者", "产出"],
    [
        ("1. 扫描", "course-scanner 或 bot.py scan", "course-config.json"),
        ("2. 内容体系", "content-optimizer", "data/outlines.json、data/generated/kp-*.json、quiz-*.json、gallery-chapters.json"),
        ("3. 合并校验", "merge_generated.py + bot.py build", "site/data 下的课程数据与题库"),
        ("4. 界面", "ui-adjuster", "CSS / 页面调整与截图回归"),
        ("5. 交付", "bot.py check / serve", "可访问的平台与检查报告"),
    ],
    widths=[3.0, 5.2, 8.0],
)
h2("6.2 两个核心 Agent")
h3("界面与 UI 调整（ui-adjuster）")
bullets([
    "输入：平台目录、目标页面、品牌与设计约束。",
    "工作：先截图看现状 → 改设计令牌（颜色/字号/间距/圆角）→ 逐页调整 → 响应式 1440/1024/768/390 → 可访问性 → 回归截图。",
    "输出：修改清单、改前后截图、UI_CHANGELOG.md。",
    "禁止：改课程数据、引入构建工具、删除教师端/学生端入口。",
])
h3("课程内容体系优化（content-optimizer）")
bullets([
    "输入：平台目录、专业背景、课程资源目录。",
    "工作：重排章节逻辑 → 写课程大纲（目标/知识点/考核/理论实操）→ 每课知识点 → 每模块题库 → 图文课章节考核 → 翻译/命名 → 图谱质量。",
    "输出：outlines.json、generated/*.json，并通过 check --strict。",
    "禁止：编造参数、删除原课时、破坏播放路径。",
])
h2("6.3 数据契约（关键 JSON）")
code([
    "data/outlines.json        课程大纲",
    "data/generated/kp-<id>.json    每课知识点  lessons[{no, keypoints[]}]",
    "data/generated/quiz-<id>.json  模块题库    modules[{title, questions[]}]",
    "data/generated/gallery-chapters.json  图文课章节考核",
    "data/generated.json        以上文件的合并结果（merge_generated.py 生成）",
])
h2("6.4 质量校验")
para("运行 python bot.py check --platform <目录>：输出每门课的课时/知识点/字幕/题库/章节统计；"
     "加 --strict 时有缺失会返回非 0，适合放进自动流程。通过标准：每课有知识点、每模块有题、图文课有章节考核。")

# ============ 七、数据与文件结构 ============
h1("七、数据与文件结构")
h2("7.1 生成后的平台目录")
code([
    "<platform>/",
    "├─ 启动学习平台.bat        双击启动",
    "├─ course-config.json       课程配置（人工维护）",
    "├─ site/                    静态站点（可直接部署镜像）",
    "│  ├─ data/catalog.json     课程目录",
    "│  ├─ data/courses/*.json   每门课数据",
    "│  ├─ data/quizzes/*.json   题库",
    "│  └─ assets/courses/*.jpg  课程封面",
    "├─ data/outlines.json       课程大纲（可选输入）",
    "├─ data/generated/          知识点/题库/章节源文件",
    "├─ data/course_roots.json   课程 → 磁盘目录映射",
    "├─ scripts/launcher.py      本地服务器",
    "└─ media/                   转码视频（如使用）",
])
h2("7.2 关键文件")
table(
    ["文件", "作用", "维护方式"],
    [
        ("course-config.json", "课程配置唯一人工入口", "手工编辑或扫描生成"),
        ("data/outlines.json", "课程大纲", "content-optimizer 生成"),
        ("data/generated/*.json", "知识点/题库/章节", "Agent 生成后 merge"),
        ("site/data/*", "构建产物", "只由 bot.py build 生成，勿手改"),
        ("data/course_roots.json", "资源路径映射", "build 自动生成"),
        ("data/server/", "学生名单/成绩/密钥", "教师端发布与备份"),
    ],
    widths=[5.0, 6.4, 5.0],
    size=9,
)

# ============ 八、管理与维护 ============
doc.add_page_break()
h1("八、管理与维护")
h2("8.1 更新技能与云端发布")
bullets([
    "改完本地 skill 文件后，运行 python scripts\\publish_repo.py --repo course-platform-builder --dir . 把新版推到云端。",
    "云端仓库是主副本；本机只是工作副本。换机器直接 clone。",
    "发布使用本机 Git 凭证（git credential），token 不落盘；公开仓库不含任何课程视频与密钥。",
])
h2("8.2 模板升级（UI 调整后）")
para("如果直接改了某个平台的 site/（CSS/页面），想让以后新建的平台也用新 UI：")
code(["python bot.py template --from-site <平台目录>\\site"])
para("会重新打包 template/site-template.zip；再发布一次仓库即可。")
h2("8.3 备份与迁移")
table(
    ["对象", "位置", "策略"],
    [
        ("技能包", "course-platform-builder/", "云端仓库 + 本机工作副本"),
        ("平台数据", "<platform>/", "整目录复制；课程视频可保留原路径不复制"),
        ("课程资源", "resourcesRoot 目录", "单独备份（视频/PDF/图片/字幕）"),
        ("教师数据", "教师端导出备份", "每次大改前导出加密备份"),
        ("服务器数据", "data/server/", "名单、成绩、密钥、已发布目录"),
    ],
    widths=[3.2, 6.0, 7.2],
    size=9,
)
h2("8.4 清理缓存与瘦身")
bullets([
    "技能包本身约 0.6 MB；主要空间在课程视频，不要复制进平台目录。",
    "定期清理：pip 缓存（python -m pip cache purge）、系统临时文件、旧截图/渲染临时目录。",
    "平台目录里 _shots、.dsh-office-*、__pycache__ 可以安全删除。",
])
h2("8.5 故障排查")
table(
    ["现象", "原因", "处理"],
    [
        ("扫描不到课程", "资源目录层级不对", "一级目录=一门课；确认 resourcesRoot"),
        ("视频打不开", "课程目录移动/改名", "恢复路径或改配置后重新 build"),
        ("封面是黑的", "ffmpeg 缺失或视频编码特殊", "装 ffmpeg 或手动放 assets/courses/<id>.jpg"),
        ("没有知识点/题库", "未跑内容 Agent", "按第六章生成 generated 后 build"),
        ("发布仓库报 409", "空仓库需初始化", "发布脚本会自动初始化；重跑即可"),
        ("网页样式不更新", "浏览器缓存", "Ctrl+F5；或确认部署完成"),
    ],
    widths=[4.2, 5.4, 6.6],
    size=9,
)

# ============ 九、安全与规范 ============
h1("九、安全与规范")
bullets([
    "教师端仅本机可访问，依赖启动器；不要尝试用局域网 IP 打开教师端。",
    "teacher_key.txt 是服务器接口密钥，不要发给学生、不要提交到公开仓库。",
    "公开仓库只放通用技能代码与模板，不要放课程视频、学生名单、成绩、密钥。",
    "课程资源用于教学时注意版权：不要公开分发商业课程视频。",
    "镜像站点只放目录与页面；视频/图片留在本地服务器或对象存储。",
])

# ============ 十、附录与 FAQ ============
doc.add_page_break()
h1("十、附录与 FAQ")
h2("10.1 按钮速查")
table(
    ["按钮", "对应命令"],
    [
        ("① 新建平台", "bot.py new --dest ... --title ... --resources ..."),
        ("② 扫描课程", "bot.py scan --platform ..."),
        ("③ 生成平台", "bot.py build --platform ..."),
        ("④ 检查内容", "bot.py check --platform ..."),
        ("⑤ 启动平台", "bot.py serve --platform ..."),
    ],
    widths=[4.4, 11.4],
)
h2("10.2 常见问题 FAQ")
table(
    ["问题", "回答"],
    [
        ("Bot 是聊天机器人吗？", "不是。它是本地工具包 + 图形启动器，由人或 AI Agent 操作。"),
        ("换专业要重做前端吗？", "不用。只改 course-config.json；UI 由 ui-adjuster 微调即可。"),
        ("课程视频要复制吗？", "不用。启动器按原路径直连；只有需要在线镜像时才考虑对象存储。"),
        ("能放进 DSH 技能目录吗？", "DSH 应用目录只读；以「读取 SKILL.md」的方式使用，或复制到可写的 agent skills 目录。"),
        ("为什么首次 build 没有题？", "题库需要内容 Agent 生成，build 只负责收集。"),
        ("多人使用怎么部署？", "把平台放到固定服务器（Nginx/HTTPS），学生端接口沿用现有 /api；或用镜像 + 网盘。"),
        ("怎么升级 UI？", "改平台 site/ → bot.py template --from-site → 重新发布仓库。"),
        ("怎么备份？", "技能包在云端；平台整目录 + 课程资源目录；教师数据用导出备份。"),
    ],
    widths=[4.6, 11.2],
    size=9,
)
h2("10.3 Agent 提示词清单")
code([
    "agents/ui-adjuster.md          界面与 UI 调整",
    "agents/content-optimizer.md    课程内容体系优化",
    "agents/course-scanner.md       课程扫描",
    "agents/lesson-writer.md        课时知识点/题库写作",
    "agents/subtitle-translator.md  字幕匹配与翻译",
])
h2("10.4 版本记录")
table(
    ["版本", "日期", "说明"],
    [
        ("v1.0", "2026-11-08", "首版：安装、桌面启动器、命令行、配置、Agent、维护与安全"),
    ],
    widths=[2.4, 3.0, 10.6],
)

doc.core_properties.title = "课程平台 Bot 使用与管理说明"
doc.core_properties.author = "课程平台 Bot"
doc.core_properties.subject = "使用、配置、Agent、维护与拓展"
OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print("saved:", OUT)
print("paragraphs:", len(doc.paragraphs), "tables:", len(doc.tables), "images:", len(doc.inline_shapes))
