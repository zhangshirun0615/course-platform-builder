#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
course-platform-builder · Bot 入口
把一个课程资源文件夹变成一套可访问的学习平台：
    python bot.py new --dest D:\\my-platform --title "XX专业学习平台" --resources "D:\\课程资源"
    python bot.py scan --platform D:\\my-platform
    python bot.py build --platform D:\\my-platform
    python bot.py check --platform D:\\my-platform
    python bot.py serve --platform D:\\my-platform
    python bot.py agents            # 查看/打印内置 Agent 提示词
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PKG = Path(__file__).resolve().parent
TEMPLATE = PKG / "template"
AGENTS = PKG / "agents"
SCRIPTS = PKG / "scripts"


def run(cmd, cwd=None):
    print("▶", " ".join(str(c) for c in cmd))
    raise_code = subprocess.call([str(c) for c in cmd], cwd=cwd)
    if raise_code != 0:
        sys.exit(raise_code)


def py():
    return sys.executable


def write_config(platform, title, resources, courses=None):
    cfg = {
        "platform": {
            "title": title,
            "subtitle": "课程学习 · 知识图谱 · 闯关练习 · AI 辅助",
            "intro": "在这里填写平台简介：面向什么专业/学科、包含哪些课程、配套什么练习。",
            "categories": [
                {"id": "all", "name": "全部"},
                {"id": "专业核心", "name": "专业核心"},
                {"id": "基础课程", "name": "基础课程"},
                {"id": "拓展课程", "name": "拓展课程"},
            ],
        },
        "resourcesRoot": resources,
        "courses": courses or [],
    }
    (platform / "course-config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_new(args):
    dest = Path(args.dest).resolve()
    if dest.exists() and any(dest.iterdir()) and not args.force:
        sys.exit(f"目标目录已存在且非空：{dest}（加 --force 覆盖）")
    dest.mkdir(parents=True, exist_ok=True)
    site = dest / "site"
    if site.exists():
        shutil.rmtree(site)
    site.mkdir()
    zip_path = TEMPLATE / "site-template.zip"
    if not zip_path.exists():
        sys.exit(f"缺少模板：{zip_path}")
    print("▶ 解压站点模板 …")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(site)
    # 启动器与 bat
    (dest / "scripts").mkdir(exist_ok=True)
    shutil.copy2(TEMPLATE / "launcher.py", dest / "scripts" / "launcher.py")
    bat = (dest / "启动学习平台.bat")
    if (TEMPLATE / "no-launcher-bat.txt").exists() is False:
        shutil.copy2(TEMPLATE / "启动学习平台.bat", bat)
    for d in ("data/server", "media"):
        (dest / d).mkdir(parents=True, exist_ok=True)
    (dest / "data" / "generated").mkdir(parents=True, exist_ok=True)
    write_config(dest, args.title, args.resources or r"D:\课程资源")
    print(f"✔ 平台已创建：{dest}")
    print("下一步：python bot.py scan --platform", dest)
    print("        然后按扫描结果整理 course-config.json，再 build / serve")


def cmd_scan(args):
    platform = Path(args.platform).resolve()
    cmd = [py(), SCRIPTS / "scan_courses.py", "--platform", platform]
    if args.resources:
        cmd += ["--resources", args.resources]
    run(cmd)


def cmd_build(args):
    platform = Path(args.platform).resolve()
    run([py(), SCRIPTS / "build_platform.py", "--platform", platform])


def cmd_check(args):
    platform = Path(args.platform).resolve()
    cmd = [py(), SCRIPTS / "check_content.py", "--platform", platform]
    if args.strict:
        cmd.append("--strict")
    run(cmd)


def cmd_serve(args):
    platform = Path(args.platform).resolve()
    run([py(), platform / "scripts" / "launcher.py"], cwd=platform)


def cmd_agents(args):
    files = sorted(AGENTS.glob("*.md"))
    if not args.name:
        print("内置 Agent：")
        for f in files:
            print("  -", f.stem, "  (", f.name, ")")
        print("\n查看提示词：python bot.py agents --show ui-adjuster")
        return
    path = AGENTS / (args.name + ".md")
    if not path.exists():
        sys.exit(f"没有这个 Agent：{args.name}")
    print(path.read_text(encoding="utf-8"))


def cmd_template(args):
    """从现有平台重新生成站点模板（UI 升级后使用）。"""
    src = Path(args.from_site).resolve()
    if not src.exists():
        sys.exit(f"源站点不存在：{src}")
    out = TEMPLATE / "site-template.zip"
    skip_top = {"data"}
    skip_assets = {"posters", "courses"}
    print("▶ 打包模板：", src, "→", out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in src.rglob("*"):
            if not f.is_file():
                continue
            rel = f.relative_to(src)
            parts = rel.parts
            if ".git" in parts or (parts and parts[0] in skip_top):
                continue
            if len(parts) > 1 and parts[0] == "assets" and parts[1] in skip_assets:
                continue
            z.write(f, rel.as_posix())
        z.writestr("data/.gitkeep", "")
    print("✔ 模板已更新：", out, f"({out.stat().st_size // 1024} KB)")


def main():
    ap = argparse.ArgumentParser(prog="course-platform-bot")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new", help="从模板创建一个新平台")
    p.add_argument("--dest", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--resources", default="", help="课程资源根目录，如 D:\\课程资源")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("scan", help="扫描课程资源，生成 course-config 草稿")
    p.add_argument("--platform", default=".")
    p.add_argument("--resources", default="")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("build", help="生成课程目录、课时、题库、图谱")
    p.add_argument("--platform", default=".")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("check", help="检查知识点/题库覆盖率")
    p.add_argument("--platform", default=".")
    p.add_argument("--strict", action="store_true")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("serve", help="启动本地服务器（含学生登录/教师端接口）")
    p.add_argument("--platform", default=".")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("agents", help="列出或打印内置 Agent 提示词")
    p.add_argument("name", nargs="?")
    p.add_argument("--show", dest="name", help=argparse.SUPPRESS)
    p.set_defaults(func=cmd_agents)

    p = sub.add_parser("template", help="从现有站点打包新的 template/site-template.zip")
    p.add_argument("--from-site", required=True)
    p.set_defaults(func=cmd_template)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
