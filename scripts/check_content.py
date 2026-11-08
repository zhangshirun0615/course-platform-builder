#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查平台内容覆盖：每课知识点、每模块题库、图文课章节、题库结构。"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", required=True)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    site = Path(args.platform).resolve() / "site" / "data"
    catalog = json.loads((site / "catalog.json").read_text(encoding="utf-8"))
    problems = []
    rows = []
    for c in catalog.get("courses", []):
        cid = c["id"]
        fp = site / "course.json" if c["type"] == "sp" else site / "courses" / (cid + ".json")
        if not fp.exists():
            continue
        course = json.loads(fp.read_text(encoding="utf-8"))
        lessons = [l for m in course.get("modules", []) for l in m.get("lessons", [])]
        kp = sum(1 for l in lessons if l.get("keypoints"))
        subs = sum(1 for l in lessons if l.get("subtitle"))
        qp = site / "quizzes" / (cid + ".json")
        qmods = 0
        qcount = 0
        if qp.exists():
            q = json.loads(qp.read_text(encoding="utf-8"))
            qmods = len(q.get("modules", {}))
            qcount = sum(len(m.get("questions", [])) for m in q["modules"].values())
            for mid, m in q["modules"].items():
                for qi, item in enumerate(m.get("questions", []), 1):
                    opts = item.get("options") or []
                    if len(opts) != 4 or not (0 <= item.get("answer", -1) < len(opts)):
                        problems.append(f"{cid}/{mid} 第{qi}题结构错误")
        chapters = len(course.get("chapters") or [])
        rows.append((cid, len(lessons), kp, subs, qmods, qcount, chapters))
        if lessons and kp < len(lessons):
            problems.append(f"{cid} 有 {len(lessons) - kp} 节课缺知识点")
        if lessons and qcount == 0:
            problems.append(f"{cid} 没有题库")
        if not lessons and chapters == 0:
            problems.append(f"{cid} 是图文课但没有章节考核")
        if course.get("graph") and len(course["graph"].get("nodes", [])) < 5:
            problems.append(f"{cid} 知识图谱节点过少")

    print(f"{'课程':<20}{'课时':>5}{'知识点':>7}{'字幕':>5}{'题库板块':>8}{'题数':>5}{'章节':>5}")
    for r in rows:
        print(f"{r[0]:<20}{r[1]:>5}{r[2]:>7}{r[3]:>5}{r[4]:>8}{r[5]:>5}{r[6]:>5}")
    print()
    if problems:
        print("⚠ 待完善：")
        for p in problems:
            print(" -", p)
        if args.strict:
            raise SystemExit(1)
    else:
        print("✔ 内容覆盖完整")


if __name__ == "__main__":
    main()
