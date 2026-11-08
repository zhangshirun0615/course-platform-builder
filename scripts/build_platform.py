#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通用课程平台构建器：读取 <platform>/course-config.json，扫描资源目录，
生成 site/data/catalog.json、courses/*.json、quizzes/*.json、course_roots.json。
支持：视频课 / 图文课 / B 站课 / 外链课；多根目录合并去重；字幕；知识点；题库；
课程大纲；图文章节考核；知识图谱；课程封面。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

VIDEO = {".mp4", ".mov", ".mkv", ".avi", ".flv", ".wmv", ".m4v", ".webm"}
IMAGE = {".jpg", ".jpeg", ".png", ".webp", ".jfif", ".bmp"}
DOC = {".pdf"}
SUB = {".srt", ".vtt"}
OTHER = {".psd", ".zip", ".rar", ".7z", ".txt", ".srt", ".doc", ".docx", ".ppt", ".pptx",
         ".xls", ".xlsx", ".abr", ".tpl", ".ai", ".eps"}

PHRASES = [
    (r"how to draw", "绘画基础"), (r"how to render", "渲染表现"),
    (r"draw & render", "绘画与渲染"), (r"framed perspective", "场景透视"),
    (r"framed ink", "分镜与构图"), (r"environment value block-in", "环境明度块面概括"),
    (r"block-in", "块面概括"), (r"block in", "块面概括"), (r"introduction", "入门"),
    (r"perspective", "透视"), (r"value", "明度"), (r"environment", "环境"),
    (r"composition", "构图"), (r"storyteller", "叙事"), (r"visual", "视觉"),
    (r"drawing", "绘制"), (r"render", "渲染"), (r"lighting", "光照"), (r"shadow", "阴影"),
    (r"volume", "体积"), (r"character", "角色"), (r"gesture", "动态"),
    (r"anatomy", "结构"), (r"material", "材质"), (r"reflection", "反射"),
    (r"texture", "纹理"), (r"vehicle", "载具"), (r"technique", "技法"),
    (r"practice", "练习"), (r"bonus", "赠送"), (r"demo", "示范"),
]
WORDS = {"draw": "绘制", "render": "渲染", "intro": "入门", "page": "第", "demo": "示范",
         "sketch": "草图", "line": "线条", "form": "形体", "light": "光", "color": "色彩",
         "final": "完成", "start": "开始", "part": "部分", "materials": "材质",
         "skills": "技法", "ellipses": "椭圆", "ellipse": "椭圆", "outdoor": "户外",
         "perspective": "透视", "values": "明度", "steps": "步骤"}
CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
PAGE_RE = re.compile(r"^(?:p|page[\s_\-]*)(\d+)$", re.I)


def tr(text):
    s = str(text).replace("_", " ").replace("-", " ")
    for pat, rep in PHRASES:
        s = re.sub(pat, rep, s, flags=re.I)
    s = re.sub(r"[A-Za-z][A-Za-z']+", lambda m: WORDS.get(m.group(0).lower(), m.group(0)), s)
    return re.sub(r"\s+", " ", s).strip()


def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(s))]


def cn_num(t):
    if t == "十":
        return 10
    m = re.match(r"^([一二三四五六七八九])?十([一二三四五六七八九])?$", t)
    if m:
        return (CN.get(m.group(1), 1) if m.group(1) else 1) * 10 + (CN.get(m.group(2), 0) if m.group(2) else 0)
    return CN.get(t, 0)


def module_key(name):
    m = re.search(r"第([一二三四五六七八九十]+)[章课节讲]", name)
    if m:
        return (0, cn_num(m.group(1)), natural_key(name))
    m = re.match(r"^(\d+)", name)
    if m:
        return (1, int(m.group(1)), natural_key(name))
    return (2, 0, natural_key(name))


def clean_title(stem):
    s = tr(Path(stem).stem)
    s = re.sub(r"^[\s\d]+[.、_\-—]?\s*", "", s)
    s = re.sub(r"[_\s]+", " ", s).strip()
    m = re.match(r"^(.*?)\s*(第[一二三四五六七八九十\d]+\s*课)\s*(\d{3,4})?\s*(\d{1,2})?\s*(.*)$", s)
    if m and " - " not in s:
        teacher, lesson, body = m.group(1).strip(), m.group(2).replace(" ", ""), m.group(5).strip()
        out = ("%s · %s" % (lesson, body)) if body else lesson
        if teacher and len(teacher) <= 8 and not re.search(r"[0-9]", teacher):
            out += "（%s）" % teacher
        return out
    return s or Path(stem).stem


def lesson_title(fname):
    stem = Path(fname).stem
    m = PAGE_RE.match(stem.strip())
    if m:
        return "第 %d 页 · 随书示范" % int(m.group(1))
    m = re.match(r"^page[\s_]*(\d+)[\s_]*(.*)$", stem, re.I)
    if m:
        rest = re.sub(r"\(?720p\)?|\(1\)", "", m.group(2), flags=re.I)
        rest = tr(rest).strip(" _-")
        rest = re.sub(r"\s+\d{1,2}$", "", rest)
        rest = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", rest)
        return ("第 %d 页 · %s" % (int(m.group(1)), rest)) if rest else ("第 %d 页 · 随书示范" % int(m.group(1)))
    s = clean_title(stem)
    s = re.sub(r"\s+\d{1,2}$", "", s)
    s = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", s)
    return s


def fmt_dur(path, ff):
    if not ff:
        return 0
    try:
        out = subprocess.run([str(ff), "-hide_banner", "-i", str(path)],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", out.stdout.decode("utf-8", "ignore"))
        if m:
            return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        pass
    return 0


def scan(root):
    out = {"videos": [], "pdfs": [], "images": [], "others": [], "subs": []}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort(key=natural_key)
        for fn in sorted(filenames, key=natural_key):
            p = Path(dirpath) / fn
            ext = p.suffix.lower()
            item = {"path": p.relative_to(root).as_posix(), "name": fn,
                    "size": p.stat().st_size,
                    "sizeMB": round(p.stat().st_size / 1048576, 2)}
            if ext in VIDEO:
                out["videos"].append(item)
            elif ext in DOC:
                out["pdfs"].append(item)
            elif ext in IMAGE:
                out["images"].append(item)
            elif ext in SUB:
                out["subs"].append(item)
            elif ext in OTHER or ext:
                out["others"].append(item)
    return out


def norm(name):
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", Path(name).stem.lower())


def srt_vtt(src, dst):
    try:
        raw = src.read_text(encoding="utf-8-sig", errors="ignore").replace("\r\n", "\n").replace("\r", "\n")
    except Exception:
        return False
    lines = [ln for ln in raw.split("\n") if not re.match(r"^\d+$", ln.strip())]
    body = re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", "\n".join(lines)).strip()
    dst.write_text("WEBVTT\n\n" + body + "\n", encoding="utf-8")
    return True


def attach_subs(course, roots, res_root):
    maps = {}
    for ri, r in enumerate(roots):
        root = res_root / r["root"]
        if not root.exists():
            continue
        m = {}
        for dirpath, _, files in os.walk(root):
            for fn in files:
                p = Path(dirpath) / fn
                if p.suffix.lower() in SUB:
                    m.setdefault(norm(fn), []).append((ri, p))
        maps[ri] = m
    for mod in course["modules"]:
        for l in mod["lessons"]:
            cand = (maps.get(l.get("rootIndex", 0)) or {}).get(norm(l["file"]))
            if not cand:
                continue
            sri, sp = cand[0]
            out = sp.with_suffix(".vtt")
            if sp.suffix.lower() == ".srt" and (not out.exists() or out.stat().st_mtime < sp.stat().st_mtime):
                if not srt_vtt(sp, out):
                    continue
            l["subtitle"] = {"path": out.relative_to(res_root / roots[sri]["root"]).as_posix(),
                             "rootIndex": sri, "label": "中文字幕"}


def graph_for(modules, chapters, course_kps):
    nodes = [{"id": "course", "label": "课程", "type": "course", "group": 0}]
    links = []
    if chapters:
        for i, ch in enumerate(chapters, 1):
            nid = "c%d" % i
            nodes.append({"id": nid, "label": ch["title"], "type": "chapter", "group": i})
            links.append({"source": "course", "target": nid})
            for j, k in enumerate((ch.get("lessons") or [])[:4]):
                kid = "%s-k%d" % (nid, j)
                nodes.append({"id": kid, "label": k, "type": "concept", "group": i})
                links.append({"source": nid, "target": kid})
                if j:
                    links.append({"source": "%s-k%d" % (nid, j - 1), "target": kid})
        return {"nodes": nodes, "links": links}
    for mod in modules:
        nid = "m%d" % mod["index"]
        nodes.append({"id": nid, "label": mod["title"], "type": "module", "group": mod["index"]})
        links.append({"source": "course", "target": nid})
        concepts = list(mod.get("keypoints") or [])
        for l in mod.get("lessons", []):
            for k in (l.get("keypoints") or []):
                if k not in concepts:
                    concepts.append(k)
        for j, k in enumerate(concepts[:14]):
            kid = "%s-k%d" % (nid, j)
            nodes.append({"id": kid, "label": k, "type": "concept", "group": mod["index"]})
            links.append({"source": nid, "target": kid})
            if j:
                links.append({"source": "%s-k%d" % (nid, j - 1), "target": kid})
    for j, k in enumerate((course_kps or [])[:8]):
        kid = "root-k%d" % j
        nodes.append({"id": kid, "label": k, "type": "concept", "group": 0})
        links.append({"source": "course", "target": kid})
    return {"nodes": nodes, "links": links}


def write_quiz(cid, title, modules, chapters, gen):
    quiz = {"courseId": cid, "title": title, "modules": {}}
    genq = ((gen.get("quizzes") or {}).get(cid) or {}).get("modules") or []
    by_title = {m.get("title"): m.get("questions", []) for m in genq}
    if chapters:
        for i, ch in enumerate(chapters, 1):
            if ch.get("questions"):
                quiz["modules"]["c%d" % i] = {"id": "c%d" % i, "title": ch["title"], "index": i,
                                              "questions": ch["questions"]}
    for mod in modules:
        qs = by_title.get(mod["title"]) or []
        if qs:
            quiz["modules"]["m%d" % mod["index"]] = {"id": "m%d" % mod["index"], "title": mod["title"],
                                                     "index": mod["index"], "questions": qs}
    return quiz if quiz["modules"] else None


def build_bilibili(spec, covers):
    bv = spec.get("bilibili", {}).get("bv") or spec.get("bv")
    if not bv:
        raise SystemExit("B 站课程缺少 bv：" + spec.get("id", ""))
    url = "https://api.bilibili.com/x/web-interface/view?bvid=" + bv
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    if data.get("code") != 0:
        raise SystemExit("B 站接口失败：" + str(data.get("message")))
    v = data["data"]
    groups = {}
    for p in v.get("pages") or []:
        t = p.get("part") or ("P%d" % p["page"])
        m = re.search(r"【([^】]+)】", t)
        g = (m.group(1).strip(" .、") if m else "全部课时")
        groups.setdefault(g, []).append({"page": p["page"], "title": re.sub(r"^【[^】]*】\s*", "", t),
                                         "cid": p["cid"], "durationSec": p.get("duration") or 0})
    modules = []
    no = 0
    for i, (g, items) in enumerate(groups.items(), 1):
        mod = {"id": "m%d" % i, "index": i, "title": g, "lessons": []}
        for it in items:
            no += 1
            mod["lessons"].append({"no": no, "id": "l%d" % no, "title": it["title"], "page": it["page"],
                                   "cid": it["cid"], "durationSec": it["durationSec"], "sizeMB": 0, "bvid": bv})
        modules.append(mod)
    cover = "assets/courses/%s.jpg" % spec["id"]
    try:
        pic = v.get("pic") or ""
        if pic:
            from PIL import Image
            import io
            req2 = urllib.request.Request(pic, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"})
            im = Image.open(io.BytesIO(urllib.request.urlopen(req2, timeout=30).read())).convert("RGB")
            im.thumbnail((960, 540))
            im.save(covers / (spec["id"] + ".jpg"), quality=86)
    except Exception:
        pass
    return {"modules": modules, "resources": [], "lessonCount": no,
            "durationSec": sum(l["durationSec"] for m in modules for l in m["lessons"]),
            "bilibili": {"bvid": bv, "title": v.get("title")}}


def make_cover(spec, data, roots, res_root, covers, ff):
    out = covers / (spec["id"] + ".jpg")
    if out.exists():
        return
    for mod in data["modules"]:
        for l in mod["lessons"]:
            if not l.get("file"):
                continue
            root = res_root / roots[l.get("rootIndex", 0)]["root"]
            src = root / l["file"]
            if not src.exists():
                continue
            if ff:
                for ss in (30, 5, 1):
                    subprocess.run([str(ff), "-y", "-hide_banner", "-loglevel", "error", "-ss", str(ss),
                                    "-i", str(src), "-frames:v", "1", "-vf", "scale=960:-2",
                                    "-q:v", "3", str(out)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
                    if out.exists() and out.stat().st_size > 2000:
                        return
            break
    for r in roots:
        root = res_root / r["root"]
        if not root.exists():
            continue
        for dirpath, _, files in os.walk(root):
            for fn in sorted(files, key=natural_key):
                if Path(fn).suffix.lower() in IMAGE:
                    try:
                        from PIL import Image
                        im = Image.open(Path(dirpath) / fn).convert("RGB")
                        w, h = im.size
                        sc = max(960 / w, 540 / h)
                        im = im.resize((int(w * sc), int(h * sc)))
                        im.crop(((im.width - 960) // 2, (im.height - 540) // 2,
                                 (im.width - 960) // 2 + 960, (im.height - 540) // 2 + 540)).save(out, quality=86)
                        return
                    except Exception:
                        continue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", required=True)
    ap.add_argument("--ffmpeg", default="")
    args = ap.parse_args()
    platform = Path(args.platform).resolve()
    cfg_path = platform / "course-config.json"
    if not cfg_path.exists():
        raise SystemExit("缺少 course-config.json，请先运行 bot.py new / scan")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    res_root = Path(cfg.get("resourcesRoot") or "").resolve()
    site = platform / "site"
    data_dir = site / "data"
    courses_dir = data_dir / "courses"
    quizzes_dir = data_dir / "quizzes"
    covers = site / "assets" / "courses"
    for d in (courses_dir, quizzes_dir, covers, platform / "data" / "generated"):
        d.mkdir(parents=True, exist_ok=True)
    ff = args.ffmpeg or cfg.get("ffmpeg") or str(platform / "tools" / "ffmpeg.exe")
    ff = ff if Path(ff).exists() or not ff else ""
    if args.ffmpeg:
        ff = args.ffmpeg
    if not ff or not Path(ff).exists():
        w = shutil_which("ffmpeg")
        ff = w or ""

    def load_json(p):
        return json.loads(Path(p).read_text(encoding="utf-8")) if Path(p).exists() else {}

    outlines = load_json(platform / "data" / "outlines.json")
    gen = load_json(platform / "data" / "generated.json")
    kp_all = gen.get("keypoints") or {}

    catalog = {
        "platform": cfg.get("platform") or {"title": "学习平台"},
        "updated": time.strftime("%Y-%m-%d %H:%M"),
        "categories": (cfg.get("platform") or {}).get("categories") or [{"id": "all", "name": "全部"}],
        "courses": [],
    }
    roots_map = {}

    for spec in cfg.get("courses", []):
        cid = spec["id"]
        ctype = spec.get("type", "video")
        print("== 构建:", cid, spec.get("title", ""))
        if ctype == "external":
            course = {"id": cid, "type": "external", "category": spec.get("category", "其他"),
                      "title": spec.get("title", cid), "subtitle": spec.get("subtitle", ""),
                      "description": spec.get("description", ""), "accent": spec.get("accent", "#ff8a3d"),
                      "tags": spec.get("tags", []), "cover": spec.get("cover", ""),
                      "dataFile": "data/courses/%s.json" % cid, "lessonCount": 0, "durationSec": 0,
                      "modules": 0, "resources": 0, "pan": spec.get("pan", {"url": "", "pwd": ""}),
                      "outline": outlines.get(cid), "hasQuiz": False, "url": spec.get("url", "")}
            json.dump({"id": cid, "title": course["title"], "type": "external", "modules": [],
                       "resources": [], "chapters": [], "outline": outlines.get(cid),
                       "graph": {"nodes": [], "links": []}},
                      open(courses_dir / (cid + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            catalog["courses"].append(course)
            continue

        if ctype == "bilibili":
            bdata = build_bilibili(spec, covers)
            kp_course = kp_all.get(cid) or {}
            for mod in bdata["modules"]:
                for l in mod["lessons"]:
                    kps = (kp_course.get(str(l["no"])) or {}).get("keypoints") or []
                    if kps:
                        l["keypoints"] = kps
            outline = outlines.get(cid)
            mod_out = (outline or {}).get("modules") or {}
            for mod in bdata["modules"]:
                mo = mod_out.get(mod["title"])
                if mo:
                    mod.update({k: mo.get(k) for k in ("goal", "keypoints", "theory", "practice") if k in mo})
            quiz = write_quiz(cid, spec["title"], bdata["modules"], None, gen)
            if quiz:
                json.dump(quiz, open(quizzes_dir / (cid + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
            graph = graph_for(bdata["modules"], None, (outline or {}).get("keypoints"))
            course = {"id": cid, "type": "bilibili", "category": spec.get("category", "其他"),
                      "title": spec["title"], "subtitle": spec.get("subtitle", ""),
                      "description": spec.get("description", ""), "accent": spec.get("accent", "#6bc5ff"),
                      "tags": spec.get("tags", []), "cover": "assets/courses/%s.jpg" % cid,
                      "dataFile": "data/courses/%s.json" % cid, "lessonCount": bdata["lessonCount"],
                      "durationSec": bdata["durationSec"], "modules": len(bdata["modules"]),
                      "resources": 0, "pan": spec.get("pan", {"url": "", "pwd": ""}),
                      "bilibili": bdata["bilibili"], "outline": outline, "hasQuiz": bool(quiz)}
            json.dump({"id": cid, "title": spec["title"], "type": "bilibili",
                       "modules": bdata["modules"], "resources": [], "chapters": [],
                       "outline": outline, "graph": graph},
                      open(courses_dir / (cid + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            catalog["courses"].append(course)
            continue

        # ---------- 本地视频 / 图文课 ----------
        roots = spec.get("roots") or []
        modules, resources, seen_v, seen_r = [], [], set(), set()
        pending = []
        for ri, r in enumerate(roots):
            root = res_root / r["root"]
            if not root.exists():
                print("  !! 目录不存在:", root)
                continue
            sc = scan(root)
            for v in sc["videos"]:
                v["rootIndex"] = ri
            label = r.get("label") or spec.get("title", "")
            mode = r.get("modules", "stage")
            renames = r.get("renames") or {}
            order = {k: i for i, k in enumerate(renames)}
            local = []
            if mode == "stage":
                groups = {}
                for v in sc["videos"]:
                    parts = v["path"].split("/")
                    mod = parts[0] if len(parts) > 1 else "正课"
                    if mod in (r.get("skip") or []):
                        continue
                    groups.setdefault(mod, []).append(v)
                for name in sorted(groups, key=lambda n: (order[n] if n in order else 100, module_key(n))):
                    local.append({"title": renames.get(name, tr(name)), "videos": groups[name]})
            elif mode == "flat":
                vids = [v for v in sc["videos"] if v["path"].split("/")[0] not in (r.get("skip") or [])]
                if vids:
                    local.append({"title": label, "videos": vids})
            for lm in local:
                items = []
                for v in sorted(lm["videos"], key=lambda x: natural_key(x["path"])):
                    key = (v["name"], v["size"])
                    if key in seen_v:
                        continue
                    seen_v.add(key)
                    items.append(v)
                if not items:
                    continue
                idx = len(modules) + 1
                mod = {"id": "m%d" % idx, "index": idx, "title": lm["title"], "lessons": []}
                modules.append(mod)
                pending.append((mod, items, root))
            # 资源
            section = label if mode == "gallery" else ""
            pool = (sc["pdfs"] + sc["others"] + sc["videos"]) if mode == "gallery" else (sc["pdfs"] + sc["others"])
            items = []
            for p in pool:
                key = (p["name"], p["size"])
                if key in seen_r:
                    continue
                seen_r.add(key)
                ext = p["name"].lower()
                kind = "pdf" if ext.endswith(".pdf") else ("video" if ext.endswith(tuple(VIDEO)) else "file")
                items.append({"kind": kind, "path": p["path"], "name": p["name"],
                              "label": tr(Path(p["name"]).stem) or p["name"],
                              "sizeMB": p["sizeMB"], "rootIndex": ri})
            img_dirs = {}
            for im in sc["images"]:
                img_dirs.setdefault(os.path.dirname(im["path"]) or "根目录", []).append(im)
            for d in sorted(img_dirs, key=natural_key):
                ims = img_dirs[d]
                items.append({"kind": "images", "dir": d, "count": len(ims), "name": d,
                              "label": tr(os.path.basename(d)) or d, "rootIndex": ri,
                              "totalMB": round(sum(x["sizeMB"] for x in ims), 1),
                              "files": [x["path"] for x in sorted(ims, key=lambda y: natural_key(y["path"]))]})
            if section:
                resources.append({"section": section, "items": items})
            else:
                resources.extend(items)

        flat = [(m, v, root) for m, items, root in pending for v in items]
        if flat:
            with ThreadPoolExecutor(max_workers=10) as ex:
                durs = list(ex.map(lambda mv: fmt_dur(mv[2] / mv[1]["path"], ff), flat))
            for (m, v, _), d in zip(flat, durs):
                v["durationSec"] = round(d, 1)
            no = 0
            for m, v, _ in flat:
                no += 1
                m["lessons"].append({"no": no, "id": "l%d" % no, "title": lesson_title(v["name"]),
                                     "file": v["path"], "rootIndex": v.get("rootIndex", 0),
                                     "durationSec": v.get("durationSec", 0), "sizeMB": v["sizeMB"]})
            for m in modules:
                m["lessons"].sort(key=lambda x: natural_key(x["file"]))
        else:
            no = 0
        outline = outlines.get(cid)
        mod_out = (outline or {}).get("modules") or {}
        for mod in modules:
            mo = mod_out.get(mod["title"])
            if mo:
                mod.update({k: mo.get(k) for k in ("goal", "keypoints", "theory", "practice") if k in mo})
        kp_course = kp_all.get(cid) or {}
        for mod in modules:
            for l in mod["lessons"]:
                kps = (kp_course.get(str(l["no"])) or {}).get("keypoints") or []
                if kps:
                    l["keypoints"] = kps
        data = {"modules": modules, "resources": resources}
        attach_subs(data, roots, res_root)
        chapters = ((gen.get("gallery") or {}).get(cid) or {}).get("chapters")
        graph = graph_for(modules, chapters, (outline or {}).get("keypoints"))
        quiz = write_quiz(cid, spec["title"], modules, chapters, gen)
        if quiz:
            json.dump(quiz, open(quizzes_dir / (cid + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
        make_cover(spec, data, roots, res_root, covers, ff)
        res_count = sum(len(s["items"]) if "items" in s else 1 for s in resources)
        course = {"id": cid, "type": ctype, "category": spec.get("category", "其他"),
                  "title": spec["title"], "subtitle": spec.get("subtitle", ""),
                  "description": spec.get("description", ""), "accent": spec.get("accent", "#ff8a3d"),
                  "tags": spec.get("tags", []), "cover": "assets/courses/%s.jpg" % cid,
                  "dataFile": "data/courses/%s.json" % cid,
                  "lessonCount": no, "durationSec": round(sum(
                      l.get("durationSec", 0) for m in modules for l in m["lessons"])),
                  "modules": len(modules), "resources": res_count,
                  "pan": spec.get("pan", {"url": "", "pwd": ""}),
                  "outline": outline, "hasQuiz": bool(quiz)}
        json.dump({"id": cid, "title": spec["title"], "type": ctype,
                   "roots": [r["root"] for r in roots], "modules": modules,
                   "resources": resources, "chapters": chapters or [],
                   "outline": outline, "graph": graph},
                  open(courses_dir / (cid + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        roots_map[cid] = [str(res_root / r["root"]) for r in roots]
        catalog["courses"].append(course)

    catalog["courseCount"] = len(catalog["courses"])
    catalog["lessonTotal"] = sum(c.get("lessonCount", 0) for c in catalog["courses"])
    catalog["durationTotal"] = sum(c.get("durationSec", 0) for c in catalog["courses"])
    json.dump(catalog, open(data_dir / "catalog.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(roots_map, open(platform / "data" / "course_roots.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # 题库索引
    idx = {"courses": []}
    for f in sorted(quizzes_dir.glob("*.json")):
        try:
            q = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        mods = list((q.get("modules") or {}).values())
        total = sum(len(m.get("questions") or []) for m in mods)
        c = next((x for x in catalog["courses"] if x["id"] == q.get("courseId")), None)
        if c and mods:
            idx["courses"].append({"id": c["id"], "title": c["title"], "modules": len(mods), "questions": total})
    json.dump(idx, open(quizzes_dir / "index.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n✔ 构建完成：%d 门课 / %d 课时 / %d 小时" % (
        catalog["courseCount"], catalog["lessonTotal"], round(catalog["durationTotal"] / 3600, 1)))
    for c in catalog["courses"]:
        print("  - %-18s %-34s %4d 节  题库:%s" % (c["id"], c["title"][:30], c["lessonCount"],
                                                    "有" if c.get("hasQuiz") else "无"))


def shutil_which(name):
    for p in os.environ.get("PATH", "").split(os.pathsep):
        f = Path(p) / (name + ".exe")
        if f.exists():
            return str(f)
    return ""


if __name__ == "__main__":
    main()
