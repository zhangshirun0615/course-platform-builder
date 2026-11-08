# -*- coding: utf-8 -*-
"""
材质工坊 · 本地服务启动器（含教师发布接口 / 学生登录接口 / 访问控制）
- 双栈静态服务器（IPv4 + IPv6），视频通过 /media/ 提供，支持 Range
- 自动检测公网 IPv6 与局域网 IPv4，写入 site/data/endpoints.json
- 同时启动 localtunnel 备用隧道
- /api/* 提供：健康检查、教师密钥、访问控制、发布名单与成绩、学生登录
"""
import hashlib
import hmac
import http.server
import json
import mimetypes
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from base64 import urlsafe_b64decode, urlsafe_b64encode
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
MEDIA = ROOT / "media"
DATA = SITE / "data"
SERVER_DIR = ROOT / "data" / "server"
ACCESS_FILE = SERVER_DIR / "access.json"
KEY_FILE = SERVER_DIR / "teacher_key.txt"
ROSTER_FILE = SERVER_DIR / "roster.json"
TASKS_FILE = SERVER_DIR / "tasks.json"
GRADES_FILE = SERVER_DIR / "grades.json"
CATALOG_FILE = SERVER_DIR / "catalog.json"

NODE = ROOT / "tools" / "node" / "node.exe"
LT = ROOT / "tools" / "share" / "node_modules" / "localtunnel" / "bin" / "lt.js"
PORT_START = 8899

mimetypes.add_type("video/mp4", ".mp4")
mimetypes.add_type("video/quicktime", ".mov")
mimetypes.add_type("video/x-matroska", ".mkv")
mimetypes.add_type("image/jpeg", ".jpg")
mimetypes.add_type("image/png", ".png")
mimetypes.add_type("image/tiff", ".tif")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("application/pdf", ".pdf")
mimetypes.add_type("text/plain", ".txt")
mimetypes.add_type("text/plain", ".srt")
mimetypes.add_type("text/vtt", ".vtt")

COURSE_ROOTS_FILE = ROOT / "data" / "course_roots.json"
_course_roots = {"mtime": 0, "roots": {}}


def load_course_roots():
    try:
        stat = COURSE_ROOTS_FILE.stat()
        if stat.st_mtime != _course_roots["mtime"]:
            _course_roots["roots"] = json.loads(COURSE_ROOTS_FILE.read_text(encoding="utf-8"))
            _course_roots["mtime"] = stat.st_mtime
    except Exception:
        pass
    return _course_roots["roots"]

SERVER_DIR.mkdir(parents=True, exist_ok=True)

endpoints = {"ipv6": "", "lan": "", "tunnel": "", "port": 0, "updated": ""}

TEACHER_KEY = ""
STUDENT_SECRET = secrets.token_bytes(32)
LOGIN_ATTEMPTS = {}  # ip -> [timestamps]
ACCESS = {"mode": "all", "whitelist": [], "updatedAt": ""}


def log(msg=""):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("utf-8", "ignore").decode("utf-8", "ignore"), flush=True)


def load_access():
    global ACCESS
    if ACCESS_FILE.exists():
        try:
            ACCESS = json.loads(ACCESS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    ACCESS.setdefault("mode", "all")
    ACCESS.setdefault("whitelist", [])


def save_access():
    ACCESS["updatedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
    ACCESS_FILE.write_text(json.dumps(ACCESS, ensure_ascii=False, indent=1), encoding="utf-8")


def load_teacher_key():
    global TEACHER_KEY
    if KEY_FILE.exists():
        TEACHER_KEY = KEY_FILE.read_text(encoding="ascii").strip()
    if not TEACHER_KEY:
        TEACHER_KEY = secrets.token_hex(24)
        KEY_FILE.write_text(TEACHER_KEY, encoding="ascii")


def sha256_hex(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_loopback(ip):
    return ip.startswith("127.") or ip in ("::1",) or ip.startswith("::ffff:127.")


def is_private(ip):
    if is_loopback(ip):
        return True
    if ip.startswith("::ffff:"):
        ip = ip[7:]
    if ip.startswith("10.") or ip.startswith("192.168."):
        return True
    m = re.match(r"172\.(\d+)\.", ip)
    if m and 16 <= int(m.group(1)) <= 31:
        return True
    if ip.startswith(("fe80", "fd", "fc")) or ip == "::1":
        return True
    return False


def access_allowed(ip):
    mode = ACCESS.get("mode", "all")
    if mode == "all":
        return True
    if is_loopback(ip):
        return True
    if mode == "local":
        return False
    if mode == "lan":
        return is_private(ip)
    if mode == "whitelist":
        return ip in (ACCESS.get("whitelist") or [])
    return True


def issue_token(sid):
    exp = int(time.time()) + 12 * 3600
    payload = ("%s|%d" % (sid, exp)).encode("utf-8")
    sig = hmac.new(STUDENT_SECRET, payload, hashlib.sha256).digest()
    return urlsafe_b64encode(payload).decode("ascii").rstrip("=") + "." + urlsafe_b64encode(sig).decode("ascii").rstrip("=")


def verify_token(token):
    try:
        a, b = token.split(".")
        pad = lambda s: s + "=" * (-len(s) % 4)
        payload = urlsafe_b64decode(pad(a)).decode("utf-8")
        sig = urlsafe_b64decode(pad(b))
        if not hmac.compare_digest(sig, hmac.new(STUDENT_SECRET, payload.encode("utf-8"), hashlib.sha256).digest()):
            return None
        sid, exp = payload.split("|")
        if int(exp) < time.time():
            return None
        return sid
    except Exception:
        return None


def read_json(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


class DualStackServer(http.server.ThreadingHTTPServer):
    address_family = socket.AF_INET6
    daemon_threads = True
    allow_reuse_address = False

    def server_bind(self):
        try:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except Exception:
            pass
        super().server_bind()

    def handle_error(self, request, client_address):
        import sys as _sys
        exc = _sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # ---------- 基础 ----------
    def peer(self):
        return self.client_address[0]

    def json_response(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def deny_page(self):
        body = ("""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>访问受限</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0a0908;color:#f4f0ea;
font-family:"PingFang SC","Microsoft YaHei",sans-serif;text-align:center;padding:24px}
h1{font-size:26px;margin:0 0 12px}p{color:#8f8880;line-height:1.8;max-width:520px}
code{font-family:Consolas,monospace;color:#ffcf9e}</style></head><body><div>
<div style="font-size:12px;letter-spacing:.3em;color:#ff8a3d;margin-bottom:14px">ACCESS RESTRICTED</div>
<h1>老师已暂停对外访问</h1>
<p>当前学习平台只允许管理员本机使用。请联系任课教师，或稍后再试。</p>
<p style="font-size:12px">你的地址：<code>%s</code></p></div></body></html>""" % self.peer())
        data = body.encode("utf-8")
        self.send_response(403)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def require_teacher(self):
        """教师接口：仅本机 + 教师密钥"""
        if not is_loopback(self.peer()):
            self.json_response(403, {"error": "教师接口仅本机可用"})
            return False
        key = self.headers.get("X-Teacher-Key", "")
        if not hmac.compare_digest(key, TEACHER_KEY):
            self.json_response(403, {"error": "教师密钥无效"})
            return False
        return True

    def read_body_json(self, limit=2 * 1024 * 1024):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > limit:
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return None

    # ---------- API ----------
    def handle_api(self):
        path = urllib.parse.urlsplit(self.path).path
        method = self.command

        if path == "/api/health" and method in ("GET", "HEAD"):
            self.json_response(200, {
                "ok": True, "local": is_loopback(self.peer()),
                "mode": ACCESS.get("mode", "all"), "version": "1.1",
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            return True

        if path == "/api/teacher/key" and method == "GET":
            if not is_loopback(self.peer()):
                self.json_response(403, {"error": "仅本机可读取教师密钥"})
                return True
            self.json_response(200, {"key": TEACHER_KEY})
            return True

        if path == "/api/access" and method == "GET":
            if not self.require_teacher():
                return True
            self.json_response(200, dict(ACCESS))
            return True

        if path == "/api/access" and method == "POST":
            if not self.require_teacher():
                return True
            body = self.read_body_json()
            if not body:
                self.json_response(400, {"error": "请求体不正确"})
                return True
            mode = body.get("mode", "all")
            if mode not in ("all", "lan", "local", "whitelist"):
                self.json_response(400, {"error": "mode 不合法"})
                return True
            ACCESS["mode"] = mode
            ACCESS["whitelist"] = [str(x).strip() for x in (body.get("whitelist") or []) if str(x).strip()]
            save_access()
            self.json_response(200, {"ok": True, "access": dict(ACCESS), "ip": self.peer()})
            return True

        if path == "/api/catalog" and method == "GET":
            data = read_json(CATALOG_FILE, None)
            if data is None:
                self.json_response(404, {"error": "尚未发布课程目录"})
            else:
                self.json_response(200, data)
            return True

        if path == "/api/teacher/publish-catalog" and method == "POST":
            if not self.require_teacher():
                return True
            body = self.read_body_json(8 * 1024 * 1024)
            if not body or not isinstance(body.get("courses"), list):
                self.json_response(400, {"error": "课程目录格式不正确"})
                return True
            CATALOG_FILE.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
            self.json_response(200, {"ok": True, "courses": len(body.get("courses") or []),
                                     "time": time.strftime("%Y-%m-%d %H:%M:%S")})
            return True

        if path == "/api/teacher/publish" and method == "POST":
            if not self.require_teacher():
                return True
            body = self.read_body_json(4 * 1024 * 1024)
            if not body:
                self.json_response(400, {"error": "请求体不正确"})
                return True
            students = body.get("students") or []
            tasks = body.get("tasks") or []
            grades = body.get("grades") or []
            ROSTER_FILE.write_text(json.dumps(students, ensure_ascii=False, indent=1), encoding="utf-8")
            TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=1), encoding="utf-8")
            GRADES_FILE.write_text(json.dumps(grades, ensure_ascii=False, indent=1), encoding="utf-8")
            self.json_response(200, {
                "ok": True, "students": len(students), "tasks": len(tasks), "grades": len(grades),
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            return True

        if path == "/api/student/login" and method == "POST":
            ip = self.peer()
            now = time.time()
            attempts = [t for t in LOGIN_ATTEMPTS.get(ip, []) if now - t < 60]
            if len(attempts) >= 8:
                self.json_response(429, {"error": "尝试次数过多，请 1 分钟后再试"})
                return True
            body = self.read_body_json(64 * 1024)
            if not body:
                self.json_response(400, {"error": "请求体不正确"})
                return True
            sid = str(body.get("sid", "")).strip()
            password = str(body.get("password", ""))
            roster = read_json(ROSTER_FILE, [])
            student = next((s for s in roster if str(s.get("sid")) == sid), None)
            if not student or not student.get("enabled", True):
                attempts.append(now)
                LOGIN_ATTEMPTS[ip] = attempts
                self.json_response(401, {"error": "学号不存在或已被停用"})
                return True
            expected = student.get("passwordHash", "")
            actual = sha256_hex("%s:%s" % (sid, password))
            if not expected or not hmac.compare_digest(actual, expected):
                attempts.append(now)
                LOGIN_ATTEMPTS[ip] = attempts
                self.json_response(401, {"error": "口令不正确"})
                return True
            LOGIN_ATTEMPTS.pop(ip, None)
            self.json_response(200, {
                "ok": True, "token": issue_token(sid),
                "student": {
                    "sid": student.get("sid"), "name": student.get("name"),
                    "className": student.get("className"), "role": student.get("role", "student"),
                    "permissions": student.get("permissions", {"viewGrades": True})
                }
            })
            return True

        if path == "/api/student/me" and method == "GET":
            auth = self.headers.get("Authorization", "")
            token = auth[7:].strip() if auth.startswith("Bearer ") else ""
            sid = verify_token(token)
            if not sid:
                self.json_response(401, {"error": "登录已过期，请重新登录"})
                return True
            roster = read_json(ROSTER_FILE, [])
            student = next((s for s in roster if str(s.get("sid")) == str(sid)), None)
            if not student:
                self.json_response(401, {"error": "账号不存在"})
                return True
            tasks = read_json(TASKS_FILE, [])
            grades = read_json(GRADES_FILE, [])
            my_grades = [g for g in grades if str(g.get("sid")) == str(sid)]
            perms = student.get("permissions", {"viewGrades": True})
            if not perms.get("viewGrades", True):
                my_grades = []
            self.json_response(200, {
                "student": {"sid": student.get("sid"), "name": student.get("name"),
                            "className": student.get("className"), "role": student.get("role", "student"),
                            "permissions": perms},
                "tasks": tasks, "grades": my_grades,
                "updatedAt": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            return True

        if path.startswith("/api/"):
            self.json_response(404, {"error": "接口不存在"})
            return True
        return False

    # ---------- 静态文件 ----------
    def translate_path(self, path):
        clean = urllib.parse.urlsplit(path).path
        clean = urllib.parse.unquote(clean)
        if clean.startswith("/course-media/"):
            rest = clean[len("/course-media/"):]
            parts = rest.split("/")
            cid = parts[0] if parts else ""
            roots = load_course_roots().get(cid)
            if not roots:
                return str(SITE / "__invalid__")
            idx = 0
            rel_parts = parts[1:]
            if len(rel_parts) >= 2 and rel_parts[0].isdigit():
                idx = int(rel_parts[0])
                rel_parts = rel_parts[1:]
            rel = "/".join(rel_parts)
            if isinstance(roots, str):
                roots = [roots]
            if idx >= len(roots):
                return str(SITE / "__invalid__")
            base = Path(roots[idx])
            target = (base / rel).resolve()
            try:
                target.relative_to(base.resolve())
            except ValueError:
                return str(SITE / "__invalid__")
            return str(target)
        if clean.startswith("/media/"):
            base = MEDIA
            rel = clean[len("/media/"):]
        else:
            base = SITE
            rel = clean.lstrip("/")
        target = (base / rel).resolve()
        try:
            target.relative_to(base.resolve())
        except ValueError:
            return str(SITE / "__invalid__")
        if target.is_dir():
            target = target / "index.html"
        return str(target)

    def log_message(self, fmt, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def _send_file(self, send_body=True):
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            self.send_error(404, "Not Found")
            return
        size = os.path.getsize(path)
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        start, end = 0, size - 1
        range_header = self.headers.get("Range")
        if range_header:
            m = re.match(r"bytes=(\d*)-(\d*)", range_header)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                if m.group(2):
                    end = min(int(m.group(2)), size - 1)
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", "bytes */%d" % size)
                    self.end_headers()
                    return
                self.send_response(206)
                self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        else:
            self.send_response(200)
        length = end - start + 1
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if not send_body:
            return
        try:
            with open(path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(262144, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if not access_allowed(self.peer()):
            if self.path.startswith("/api/"):
                self.json_response(403, {"error": "当前访问模式下禁止访问"})
            else:
                self.deny_page()
            return
        if self.handle_api():
            return
        self._send_file(True)

    def do_HEAD(self):
        if not access_allowed(self.peer()):
            if self.path.startswith("/api/"):
                self.json_response(403, {"error": "当前访问模式下禁止访问"})
            else:
                self.send_response(403)
                self.end_headers()
            return
        self._send_file(False)

    def do_POST(self):
        if not access_allowed(self.peer()):
            self.json_response(403, {"error": "当前访问模式下禁止访问"})
            return
        if self.handle_api():
            return
        self.json_response(404, {"error": "接口不存在"})


# ---------- 启动流程 ----------
def write_endpoints():
    DATA.mkdir(parents=True, exist_ok=True)
    endpoints["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        (DATA / "endpoints.json").write_text(json.dumps(endpoints, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as e:
        log("写入 endpoints.json 失败：%s" % e)


def ps_json(cmd):
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=15,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def detect_ipv6():
    out = ps_json(
        "Get-NetIPAddress -AddressFamily IPv6 -PrefixOrigin RouterAdvertisement -ErrorAction SilentlyContinue | "
        "Where-Object { $_.PrefixLength -eq 64 -and $_.IPAddress -notlike 'fe80*' } | "
        "Select-Object -First 1 -ExpandProperty IPAddress"
    )
    if out:
        return out.splitlines()[-1].strip()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET6):
            addr = info[4][0].split("%")[0]
            if not addr.startswith(("fe80", "::1", "fd", "fc")):
                return addr
    except Exception:
        pass
    return ""


def detect_lan():
    out = ps_json(
        "Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.IPAddress -match '^(192\\.168|10\\.|172\\.(1[6-9]|2[0-9]|3[01])\\.)' } | "
        "Select-Object -First 1 -ExpandProperty IPAddress"
    )
    if out:
        return out.splitlines()[-1].strip()
    return ""


def start_tunnel(port):
    if not (NODE.exists() and LT.exists()):
        log("（未找到 localtunnel 组件，跳过备用隧道）")
        return None
    try:
        proc = subprocess.Popen(
            [str(NODE), str(LT), "--port", str(port)],
            cwd=str(LT.parent.parent.parent),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="ignore",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as e:
        log("隧道启动失败：%s" % e)
        return None

    def reader():
        for line in proc.stdout:
            line = line.strip()
            m = re.search(r"(https://[a-z0-9-]+\.loca\.lt)", line)
            if m and not endpoints["tunnel"]:
                endpoints["tunnel"] = m.group(1).rstrip("/") + "/"
                write_endpoints()
                log("")
                log("  备用隧道地址：%s" % endpoints["tunnel"])
                log("")

    threading.Thread(target=reader, daemon=True).start()
    return proc


def platform_title():
    try:
        cat = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
        return cat.get("platform", {}).get("title") or "学习平台"
    except Exception:
        return "学习平台"


def main():
    title = platform_title()
    log("")
    log("  ┌──────────────────────────────────────────────┐")
    log("  │  %s" % title)
    log("  │  正在启动本地服务，请稍候…")
    log("  └──────────────────────────────────────────────┘")
    log("")

    load_access()
    load_teacher_key()

    port = PORT_START
    server = None
    for p in range(PORT_START, PORT_START + 12):
        try:
            server = DualStackServer(("::", p), Handler)
            port = p
            break
        except OSError as e:
            if getattr(e, "winerror", 0) == 10048 or getattr(e, "errno", 0) == 98:
                continue
            raise

    if server is None:
        log("端口 8899-8910 都被占用了，请关闭占用程序后重试。")
        input("按回车退出…")
        return

    ipv6 = detect_ipv6()
    lan = detect_lan()
    endpoints["port"] = port
    endpoints["ipv6"] = "http://[%s]:%d/" % (ipv6, port) if ipv6 else ""
    endpoints["lan"] = "http://%s:%d/" % (lan, port) if lan else "http://127.0.0.1:%d/" % port
    write_endpoints()

    threading.Thread(target=server.serve_forever, daemon=True).start()

    log("  ✔ 本地服务已启动（端口 %d），视频目录已接通" % port)
    log("")
    log("  本机访问：  http://127.0.0.1:%d/" % port)
    if endpoints["lan"]:
        log("  局域网访问：%s" % endpoints["lan"])
    if ipv6:
        log("  公网 IPv6： %s" % endpoints["ipv6"])
    log("")
    log("  学生登录：  http://127.0.0.1:%d/#/student" % port)
    log("  教师端：    http://127.0.0.1:%d/#/teacher（仅本机可访问，需口令）" % port)
    log("  当前访问模式：%s（可在教师端「发布与访问」中修改）" % ACCESS.get("mode"))
    log("")
    log("  按 Ctrl+C 可停止服务。")
    log("")

    tunnel_proc = start_tunnel(port)
    time.sleep(1.2)
    try:
        webbrowser.open("http://127.0.0.1:%d/" % port)
    except Exception:
        pass

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("")
        log("正在关闭服务…")
        try:
            server.shutdown()
        except Exception:
            pass
        if tunnel_proc is not None:
            try:
                tunnel_proc.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        input("启动出错，按回车退出…")
