#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把本 skill 目录发布到一个 GitHub 仓库（创建仓库 + 推送文件），用于云端备份/共享。
用法：
  python publish_repo.py --repo owner/course-platform-builder --dir . --message "v1.0"
凭证：优先环境变量 GITHUB_TOKEN；否则调用 git credential fill（与现有 Git 登录一致）。
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

API = "https://api.github.com"
SKIP = {".git", "__pycache__", ".pytest_cache", ".dsh-office"}


def token():
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        return tok
    for exe in ("git", r"D:\trae\git\cmd\git.exe"):
        try:
            out = subprocess.run([exe, "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                                 capture_output=True, text=True, timeout=20)
            for line in out.stdout.splitlines():
                if line.startswith("password="):
                    return line.split("=", 1)[1].strip()
        except Exception:
            continue
    return ""


TOK = token()
if not TOK:
    sys.exit("未找到 GitHub 凭证：请先 git 登录 github.com，或设置 GITHUB_TOKEN")


def api(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method,
                                 headers={"Authorization": "token " + TOK,
                                          "Accept": "application/vnd.github+json",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def files_of(root):
    out = []
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        if any(part in SKIP for part in f.parts):
            continue
        out.append(f)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--message", default="update skill")
    ap.add_argument("--private", action="store_true")
    ap.add_argument("--description", default="课程平台构建 Skill：任意课程资源 → 学习平台（含 UI/内容 Agent）")
    args = ap.parse_args()

    if "/" in args.repo:
        owner, repo = args.repo.split("/", 1)
    else:
        st, me = api("GET", "/user")
        if st != 200:
            sys.exit(f"无法获取 GitHub 用户：{st} {me}")
        owner, repo = me["login"], args.repo
        print("▶ 账号：", owner)
    root = Path(args.dir).resolve()
    status, info = api("GET", f"/repos/{owner}/{repo}")
    if status == 404:
        print("▶ 创建仓库 …")
        status, info = api("POST", "/user/repos", {"name": repo, "private": args.private,
                                                    "description": args.description, "auto_init": False})
        if status not in (200, 201):
            sys.exit(f"创建仓库失败：{status} {info}")
        print("✔ 已创建：", info.get("html_url"))
    else:
        print("▶ 使用已有仓库：", info.get("html_url"))

    # 默认分支
    branch = info.get("default_branch") or "main"

    # 空仓库需要先创建一次初始提交，否则无法创建 blob/tree
    st, _ = api("GET", f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
    if st != 200:
        print("▶ 初始化空仓库 …")
        st2, res2 = api("PUT", f"/repos/{owner}/{repo}/contents/README.md",
                        {"message": "init", "content": base64.b64encode(b"# repo\n").decode(),
                         "branch": branch})
        if st2 not in (200, 201):
            sys.exit(f"初始化仓库失败：{st2} {res2}")
        # 初始化后分支可能不是 main，重新读取默认分支
        st3, info3 = api("GET", f"/repos/{owner}/{repo}")
        if st3 == 200 and info3.get("default_branch"):
            branch = info3["default_branch"]
        print("▶ 初始化完成，分支：", branch)

    print("▶ 上传文件 …")
    blobs = []
    for f in files_of(root):
        rel = f.relative_to(root).as_posix()
        content = base64.b64encode(f.read_bytes()).decode()
        st, res = api("POST", f"/repos/{owner}/{repo}/git/blobs", {"content": content, "encoding": "base64"})
        if st not in (200, 201):
            sys.exit(f"上传失败 {rel}: {st} {res}")
        blobs.append({"path": rel, "mode": "100644", "type": "blob", "sha": res["sha"]})
        print("  +", rel)
    st, tree = api("POST", f"/repos/{owner}/{repo}/git/trees", {"tree": blobs})
    if st not in (200, 201):
        sys.exit(f"创建 tree 失败：{st} {tree}")

    parents = []
    st, ref = api("GET", f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
    if st == 200:
        parents = [ref["object"]["sha"]]

    payload = {"message": args.message, "tree": tree["sha"], "parents": parents}
    st, commit = api("POST", f"/repos/{owner}/{repo}/git/commits", payload)
    if st not in (200, 201):
        sys.exit(f"创建 commit 失败：{st} {commit}")

    if parents:
        st, _ = api("PATCH", f"/repos/{owner}/{repo}/git/refs/heads/{branch}", {"sha": commit["sha"], "force": False})
    else:
        st, _ = api("POST", f"/repos/{owner}/{repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": commit["sha"]})
    if st not in (200, 201):
        sys.exit(f"更新分支失败：{st}")
    print("✔ 已发布：", f"https://github.com/{owner}/{repo}")
    print("  clone：", f"https://github.com/{owner}/{repo}.git")


if __name__ == "__main__":
    main()
