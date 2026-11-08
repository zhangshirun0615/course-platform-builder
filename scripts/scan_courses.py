#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""扫描课程资源根目录，生成 course-config.json 草稿。"""
import argparse
import json
import re
import os
from pathlib import Path

VIDEO = {".mp4", ".mov", ".mkv", ".avi", ".flv", ".wmv", ".m4v", ".webm"}
IMAGE = {".jpg", ".jpeg", ".png", ".webp", ".jfif", ".bmp"}
DOC = {".pdf"}
SUB = {".srt", ".vtt"}


def slug(name, idx):
    s = re.sub(r"[^0-9a-zA-Z]+", "-", name).strip("-").lower()
    s = re.sub(r"-+", "-", s)
    return s or f"course-{idx}"


def scan_dir(root):
    stat = {"video": 0, "pdf": 0, "image": 0, "sub": 0, "size": 0, "subdirs": []}
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        if len(rel.parts) == 1:
            stat["subdirs"].append(rel.name)
        for fn in filenames:
            ext = Path(fn).suffix.lower()
            stat["size"] += (Path(dirpath) / fn).stat().st_size
            if ext in VIDEO:
                stat["video"] += 1
            elif ext in DOC:
                stat["pdf"] += 1
            elif ext in IMAGE:
                stat["image"] += 1
            elif ext in SUB:
                stat["sub"] += 1
    return stat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", required=True)
    ap.add_argument("--resources", default="")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    platform = Path(args.platform).resolve()
    cfg_path = platform / "course-config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    res_root = Path(args.resources or cfg.get("resourcesRoot") or "").resolve()
    if not res_root.exists():
        raise SystemExit(f"课程资源目录不存在：{res_root}")

    top = [p for p in sorted(res_root.iterdir()) if p.is_dir() and not p.name.startswith(".")]
    print(f"扫描：{res_root}（{len(top)} 个一级目录）\n")
    rows = []
    courses = []
    for i, d in enumerate(top, 1):
        st = scan_dir(d)
        if st["video"] == 0 and st["pdf"] == 0 and st["image"] == 0:
            print(f"  - 跳过（没有可用内容）：{d.name}")
            continue
        kind = "video" if st["video"] else "gallery"
        cid = slug(d.name, i)
        rows.append((cid, kind, d.name, st["video"], st["pdf"], st["image"], st["sub"],
                     round(st["size"] / 1024 / 1024 / 1024, 2)))
        courses.append({
            "id": cid,
            "type": kind,
            "category": "专业核心",
            "title": d.name,
            "subtitle": "",
            "description": "",
            "accent": "#ff8a3d",
            "tags": [],
            "roots": [{"root": d.name, "modules": "stage"}],
        })

    print(f"{'id':<22}{'类型':<10}{'标题':<34}{'视频':>6}{'PDF':>5}{'图片':>6}{'字幕':>5}{'GB':>7}")
    for r in rows:
        print(f"{r[0]:<22}{r[1]:<10}{r[2][:30]:<34}{r[3]:>6}{r[4]:>5}{r[5]:>6}{r[6]:>5}{r[7]:>7}")

    existing = cfg.get("courses") or []
    if existing and not args.force:
        print("\n⚠ course-config.json 里已有课程，未自动覆盖；如需重建请加 --force。")
    else:
        cfg.setdefault("platform", {
            "title": platform.name,
            "subtitle": "课程学习 · 知识图谱 · 闯关练习",
            "intro": "请补充平台简介。",
            "categories": [
                {"id": "all", "name": "全部"},
                {"id": "专业核心", "name": "专业核心"},
                {"id": "基础课程", "name": "基础课程"},
            ],
        })
        cfg["resourcesRoot"] = str(res_root)
        cfg["courses"] = courses
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n✔ 已写入 {cfg_path}")
        print("下一步：编辑该文件（标题/分类/描述/modules 模式），然后运行 bot.py build")


if __name__ == "__main__":
    main()
