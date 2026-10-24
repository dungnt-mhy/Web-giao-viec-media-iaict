"""Web App Giao Việc — HTTP API server (Giai đoạn 1 + 2 + 3).

Pure Python stdlib (``http.server.ThreadingHTTPServer``). All business
rules come from the bot project: ``storage.Store`` for data, ``roles``
for the 5-role permission matrix, ``stats`` for reporting. Every
endpoint re-checks permissions server-side against the session user's
role; nothing the client sends about roles is trusted.

GĐ2 adds: material uploads (multipart, stored under the bot's
``data/files/<task code>/``), the full per-channel output action set
mirroring the bot's channel-card buttons (same audit actions and
state transitions), review queue, scheduled list, statistics export,
a derived notifications inbox, password change, PWA static serving
and permission-checked material downloads (with HTTP Range support
so draft videos play in the browser).

GĐ3 adds: real Web Push notifications (VAPID/RFC 8291, see
``webapp/push.py``) fired from task creation and the output actions,
push subscription endpoints, a daily-summary endpoint + overview
card, and a background thread that at 20:00 Vietnam time each day
pushes the daily summary to Admins and drops it into every user's
in-app inbox (once per day, gated by a persisted date in web_meta).

Run:  python3 -m webapp.app     (port: $WEBAPP_PORT, default 8790)
"""

from __future__ import annotations

import contextlib
import json
import mimetypes
import os
import re
import shutil
import tempfile
import threading
import time
import warnings
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from . import VERSION
from .auth import hash_password, new_session_token, verify_password
from .db import WebDB, bot_dir, default_db_path, import_bot_modules
from .push import PushService, default_vapid_path

storage, roles, stats = import_bot_modules()

STATIC_DIR = Path(__file__).resolve().parent / "static"
SESSION_COOKIE = "webapp_session"
SESSION_TTL_DAYS = int(os.environ.get("WEBAPP_SESSION_TTL_DAYS", "7"))
MIN_PASSWORD_LENGTH = 8

#: Maximum size of one uploaded material file (GĐ2 decision: 200MB —
#: the web channel is not bound by Telegram's 20MB download cap).
MAX_UPLOAD_BYTES = 200 * 1024 * 1024
#: Sanity cap on a whole multipart request (several files per task).
MAX_REQUEST_BYTES = 1024 * 1024 * 1024

ICT = timezone(timedelta(hours=7), name="ICT")
FB_TARGETS = ("profile", "page")

#: Roles allowed to create tasks (mirrors handlers.CREATOR_ROLES of
#: the bot: every granted role; pending users with role NULL cannot).
CREATOR_ROLES = roles.ALL_ROLES

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/manifest.webmanifest": ("manifest.webmanifest",
                              "application/manifest+json; charset=utf-8"),
    "/sw.js": ("sw.js", "text/javascript; charset=utf-8"),
    "/icon.svg": ("icon.svg", "image/svg+xml; charset=utf-8"),
    "/icon-192.png": ("icon-192.png", "image/png"),
    "/icon-512.png": ("icon-512.png", "image/png"),
}

OUTPUT_ACTIONS = (
    "submit", "approve", "reject", "revise", "cancel", "publish",
    "publish-abort", "schedule", "schedule-abort", "unschedule",
    "retract",
)


def user_public(row) -> dict:
    """API view of a user row — never includes password_hash."""
    role = row["role"]
    return {
        "id": row["telegram_id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "email": row["email"] if "email" in row.keys() else None,
        "phone": row["phone"] if "phone" in row.keys() else None,
        "role": role,
        "role_title": roles.role_title(role),
        "can_publish": roles.can_publish(row),
        "can_review": roles.can_review(role),
        "can_manage_users": role in (roles.ROLE_ADMIN, roles.ROLE_DEPUTY),
        "can_create_task": role in CREATOR_ROLES,
        "created_at": row["created_at"],
    }


def _json_list(raw):
    try:
        value = json.loads(raw) if raw else []
    except (ValueError, TypeError):
        return []
    return value if isinstance(value, list) else []


def _row_get(row, key):
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return None


def task_public(row, creator_name=None) -> dict:
    return {
        "id": row["id"],
        "code": row["code"],
        "creator_id": row["creator_id"],
        "creator_name": creator_name or _row_get(row, "creator_name"),
        "creator_role": row["creator_role"],
        "hint": row["hint"],
        "file_ids": _json_list(row["file_ids"]),
        "destinations": _json_list(row["destinations"]),
        "draft_url": row["draft_url"],
        "public_url": row["public_url"],
        "status": row["status"],
        "reject_reason": row["reject_reason"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def output_public(row) -> dict:
    return {
        "id": row["id"],
        "task_code": row["task_code"],
        "channel": row["channel"],
        "channel_label": storage.channel_label(row["channel"]),
        "channel_kind": storage.channel_kind(row["channel"]),
        "status": row["status"],
        "draft_ref": row["draft_ref"],
        "draft_video_path": _row_get(row, "draft_video_path"),
        "draft_file_id": _row_get(row, "draft_file_id"),
        "public_url": row["public_url"],
        "reject_reason": row["reject_reason"],
        "scheduled_at": row["scheduled_at"],
        "publish_target": row["publish_target"],
        "pending_choice": bool(_row_get(row, "pending_choice")),
        "task_hint": _row_get(row, "task_hint"),
        "creator_id": _row_get(row, "task_creator_id"),
        "creator_name": _row_get(row, "creator_name"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def default_files_dir() -> Path:
    override = os.environ.get("WEBAPP_FILES_DIR")
    if override:
        return Path(override)
    return bot_dir() / "data" / "files"


def safe_filename(name: str) -> str:
    base = Path((name or "").replace("\\", "/")).name.strip()
    base = "".join(ch for ch in base if ch.isprintable() and ch not in '<>:"|?*')
    base = base.strip(". ")
    return base or "file"


def dedupe_filename(name: str, taken: set) -> str:
    if name not in taken:
        taken.add(name)
        return name
    stem, dot, ext = name.partition(".")
    suffix = f".{ext}" if dot and ext and " " not in ext and "/" not in ext else ""
    stem = name[: -len(suffix)] if suffix else name
    index = 2
    while True:
        candidate = f"{stem}-{index}{suffix}"
        if candidate not in taken:
            taken.add(candidate)
            return candidate
        index += 1


class App:
    """Holds the shared store + web db; one instance per server."""

    def __init__(self, db_path=None, files_dir=None):
        self.db_path = str(db_path or default_db_path())
        self.webdb = WebDB(self.db_path)
        self.store = storage.Store(self.db_path)
        self.files_dir = Path(files_dir or default_files_dir())
        # Web Push is best-effort infrastructure: if the VAPID keys
        # cannot be loaded/created the app still serves everything
        # else and the push endpoints answer 503.
        try:
            self.push = PushService(self.webdb,
                                    default_vapid_path(self.db_path))
        except Exception as err:  # noqa: BLE001 - degrade, never crash
            print(f"Web Push disabled: {type(err).__name__}: {err}")
            self.push = None

    def close(self) -> None:
        self.store.close()
        self.webdb.close()


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class Handler(BaseHTTPRequestHandler):
    server_version = f"WebAppGiaoViec/{VERSION}"
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------ helpers
    @property
    def app(self) -> App:
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, format, *args):  # noqa: A002 - stdlib name
        # Access log only (method + path + status); request bodies —
        # which may contain passwords — are never logged.
        super().log_message(format, *args)

    def _send_json(self, status: int, payload: dict, headers=None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_bytes(self, status: int, body: bytes, content_type: str,
                    headers=None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ApiError(HTTPStatus.BAD_REQUEST, "JSON không hợp lệ.")
        if not isinstance(data, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "Dữ liệu phải là object JSON.")
        return data

    def _is_multipart(self) -> bool:
        return (self.headers.get("Content-Type") or "").lower().startswith(
            "multipart/form-data")

    def _parse_multipart(self):
        """Parse a multipart/form-data body with stdlib ``cgi``.

        (cgi is deprecated in 3.12 but present and battle-tested; the
        project pins stdlib-only and Python 3.12.)"""
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_REQUEST_BYTES:
            raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                           "Tổng dung lượng tải lên vượt quá 1GB.")
        import cgi

        environ = {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": self.headers.get("Content-Type") or "",
            "CONTENT_LENGTH": str(length),
        }
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            return cgi.FieldStorage(fp=self.rfile, environ=environ,
                                    keep_blank_values=True)

    @staticmethod
    def _form_texts(form, name: str):
        values = []
        items = form.list or []
        for item in items:
            if item.name != name or item.filename is not None:
                continue
            value = item.value
            if isinstance(value, bytes):
                value = value.decode("utf-8", "replace")
            values.append(value)
        return values

    @staticmethod
    def _form_files(form):
        parts = []
        for item in form.list or []:
            if item.filename is None:
                continue
            if item.name not in ("files", "file", "materials", "uploads"):
                continue
            if item.filename == "":
                continue
            stream = item.file
            stream.seek(0, os.SEEK_END)
            size = stream.tell()
            stream.seek(0)
            parts.append({"filename": item.filename, "size": size,
                          "stream": stream})
        return parts

    def _session_token(self) -> str | None:
        auth = self.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            return auth[7:].strip() or None
        cookie = SimpleCookie(self.headers.get("Cookie") or "")
        morsel = cookie.get(SESSION_COOKIE)
        return morsel.value if morsel else None

    def _current_user(self, required: bool = True):
        token = self._session_token()
        user = self.app.webdb.get_session_user(token) if token else None
        if user is None and required:
            raise ApiError(HTTPStatus.UNAUTHORIZED,
                           "Chưa đăng nhập hoặc phiên đã hết hạn.")
        return user

    @staticmethod
    def _require_role(user, allowed, message="Bạn không có quyền này."):
        if user["role"] not in allowed:
            raise ApiError(HTTPStatus.FORBIDDEN, message)

    def _require_granted(self, user):
        self._require_role(user, CREATOR_ROLES,
                           "Tài khoản chưa được cấp quyền.")

    # ------------------------------------------------------------- routes
    def do_GET(self):
        self._dispatch("GET")

    def do_HEAD(self):
        self._dispatch("HEAD")

    def do_POST(self):
        self._dispatch("POST")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        try:
            if method in ("GET", "HEAD") and path in STATIC_FILES:
                return self._serve_static(path)
            if method == "GET" and path == "/api/health":
                return self._send_json(HTTPStatus.OK, {
                    "ok": True, "version": VERSION,
                    "db": Path(self.app.db_path).name,
                })
            if method == "POST" and path == "/api/auth/login":
                return self._login()
            if method == "POST" and path == "/api/auth/logout":
                return self._logout()
            if method == "GET" and path == "/api/auth/me":
                user = self._current_user()
                return self._send_json(HTTPStatus.OK,
                                       {"user": user_public(user)})
            if method == "POST" and path == "/api/auth/change-password":
                return self._change_password()
            if method == "GET" and path == "/api/tasks":
                return self._list_tasks(query)
            if method == "POST" and path == "/api/tasks":
                return self._create_task()
            if method == "POST" and path == "/api/uploads":
                return self._upload_to_task()
            task_files = re.fullmatch(r"/api/tasks/([^/]+)/files", path)
            if method == "POST" and task_files:
                return self._add_task_files(unquote(task_files.group(1)))
            if method == "GET" and path.startswith("/api/files/"):
                rest = path[len("/api/files/"):]
                code, _, filename = rest.partition("/")
                return self._serve_task_file(unquote(code),
                                             unquote(filename))
            if (method == "GET" and path.startswith("/api/tasks/")
                    and "/" not in path[len("/api/tasks/"):]):
                return self._task_detail(path[len("/api/tasks/"):])
            draft_video = re.fullmatch(r"/api/outputs/(\d+)/draft-video", path)
            if method in ("GET", "HEAD") and draft_video:
                return self._serve_draft_video(int(draft_video.group(1)))
            action = re.fullmatch(r"/api/outputs/(\d+)/([a-z-]+)", path)
            if method == "POST" and action:
                return self._output_action(int(action.group(1)),
                                           action.group(2))
            if method == "GET" and path == "/api/review-queue":
                return self._review_queue()
            if method == "GET" and path == "/api/scheduled":
                return self._scheduled()
            if method == "GET" and path == "/api/notifications":
                return self._notifications()
            if method == "POST" and path == "/api/notifications/read":
                return self._notifications_read()
            if method == "GET" and path == "/api/push/vapid-public-key":
                return self._push_vapid_key()
            if method == "POST" and path == "/api/push/subscribe":
                return self._push_subscribe()
            if method == "POST" and path == "/api/push/unsubscribe":
                return self._push_unsubscribe()
            if method == "POST" and path == "/api/push/test":
                return self._push_test()
            if method == "GET" and path == "/api/stats/daily-summary":
                return self._stats_daily_summary()
            if method == "GET" and path == "/api/stats/summary":
                return self._stats_summary(query)
            if method == "GET" and path == "/api/stats/export":
                return self._stats_export(query)
            if method == "GET" and path == "/api/users":
                return self._list_users()
            if method == "POST" and path == "/api/users":
                return self._create_user()
            user_role = re.fullmatch(r"/api/users/(\d+)/role", path)
            if method == "PATCH" and user_role:
                return self._set_user_role(int(user_role.group(1)))
            user_revoke = re.fullmatch(r"/api/users/(\d+)/revoke", path)
            if method == "POST" and user_revoke:
                return self._revoke_user(int(user_revoke.group(1)))
            raise ApiError(HTTPStatus.NOT_FOUND, "Không tìm thấy đường dẫn.")
        except ApiError as err:
            self._send_json(err.status, {"error": err.message})
        except BrokenPipeError:
            pass
        except Exception as err:  # never leak a stack trace to clients
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR,
                            {"error": f"Lỗi máy chủ: {err}"})

    # ------------------------------------------------------------ static
    def _serve_static(self, path: str) -> None:
        filename, content_type = STATIC_FILES[path]
        page = STATIC_DIR / filename
        if not page.exists():
            raise ApiError(HTTPStatus.NOT_FOUND, "Chưa có file tĩnh này.")
        body = page.read_bytes()
        headers = {}
        if filename == "index.html":
            headers["Cache-Control"] = "no-cache"
        elif filename == "sw.js":
            headers["Cache-Control"] = "no-cache"
            headers["Service-Worker-Allowed"] = "/"
        self._send_bytes(HTTPStatus.OK, body, content_type, headers)

    def _serve_index(self) -> None:  # kept for backwards compatibility
        self._serve_static("/")

    # --------------------------------------------------------------- auth
    def _login(self) -> None:
        body = self._read_json()
        login = (body.get("login") or body.get("email")
                 or body.get("phone") or "")
        password = body.get("password") or ""
        user = self.app.webdb.find_user_by_login(str(login))
        stored = (user["password_hash"]
                  if user is not None and "password_hash" in user.keys()
                  else None)
        if user is None or not verify_password(str(password), stored):
            raise ApiError(HTTPStatus.UNAUTHORIZED,
                           "Email/SĐT hoặc mật khẩu không đúng.")
        token = new_session_token()
        self.app.webdb.create_session(
            user["telegram_id"], token, ttl_days=SESSION_TTL_DAYS)
        cookie = (f"{SESSION_COOKIE}={token}; HttpOnly; Path=/; "
                  f"SameSite=Lax; Max-Age={SESSION_TTL_DAYS * 86400}")
        self._send_json(HTTPStatus.OK,
                        {"user": user_public(user), "token": token},
                        headers={"Set-Cookie": cookie})

    def _logout(self) -> None:
        token = self._session_token()
        if token:
            self.app.webdb.delete_session(token)
        cookie = f"{SESSION_COOKIE}=; HttpOnly; Path=/; SameSite=Lax; Max-Age=0"
        self._send_json(HTTPStatus.OK, {"ok": True},
                        headers={"Set-Cookie": cookie})

    def _change_password(self) -> None:
        user = self._current_user()
        body = self._read_json()
        old = str(body.get("old_password") or body.get("current_password")
                  or "")
        new = str(body.get("new_password") or "")
        stored = user["password_hash"] if "password_hash" in user.keys() \
            else None
        if not verify_password(old, stored):
            raise ApiError(HTTPStatus.UNAUTHORIZED,
                           "Mật khẩu hiện tại không đúng.")
        if len(new) < MIN_PASSWORD_LENGTH:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           f"Mật khẩu mới phải có ít nhất "
                           f"{MIN_PASSWORD_LENGTH} ký tự.")
        if verify_password(new, stored):
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           "Mật khẩu mới phải khác mật khẩu hiện tại.")
        self.app.webdb.set_password_hash(user["telegram_id"],
                                         hash_password(new))
        # Every other session of this user dies; this one survives.
        self.app.webdb.delete_user_sessions(
            user["telegram_id"], except_raw_token=self._session_token())
        self.app.store.audit(user["telegram_id"], "change_password",
                             "user", user["telegram_id"],
                             detail="via=webapp")
        self._send_json(HTTPStatus.OK, {"ok": True})

    # -------------------------------------------------------------- files
    def _task_files(self, task) -> list:
        code = task["code"]
        directory = self.app.files_dir / code
        physical = {}
        if directory.is_dir():
            for entry in directory.iterdir():
                if entry.is_file():
                    physical[entry.name] = entry
        ordered = []
        seen = set()
        for raw in _json_list(task["file_ids"]):
            name = Path(str(raw).replace("\\", "/")).name
            if name in physical and name not in seen:
                ordered.append(name)
                seen.add(name)
        for name in sorted(physical):
            if name not in seen:
                ordered.append(name)
                seen.add(name)
        files = []
        for name in ordered:
            entry = physical[name]
            files.append({
                "name": name,
                "relative_path": f"{code}/{name}",
                "size": entry.stat().st_size,
                "content_type": mimetypes.guess_type(name)[0]
                or "application/octet-stream",
                "url": f"/api/files/{quote(code)}/{quote(name)}",
            })
        return files

    def _validate_parts(self, parts):
        for part in parts:
            if part["size"] > MAX_UPLOAD_BYTES:
                raise ApiError(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                    f"File {part['filename']} vượt quá giới hạn 200MB.")

    def _plan_names(self, code: str, parts):
        directory = self.app.files_dir / code
        taken = set()
        if directory.is_dir():
            taken = {entry.name for entry in directory.iterdir()}
        planned = []
        for part in parts:
            name = dedupe_filename(safe_filename(part["filename"]), taken)
            planned.append((part, name))
        return planned

    def _save_parts(self, code: str, planned):
        directory = self.app.files_dir / code
        directory.mkdir(parents=True, exist_ok=True)
        saved = []
        for part, name in planned:
            dest = directory / name
            part["stream"].seek(0)
            with open(dest, "wb") as fh:
                shutil.copyfileobj(part["stream"], fh, length=1024 * 1024)
            saved.append(name)
        return saved

    def _add_task_files(self, code: str, form=None) -> None:
        user = self._current_user()
        self._require_granted(user)
        task = self.app.store.get_task(code)
        if task is None:
            raise ApiError(HTTPStatus.NOT_FOUND,
                           f"Không tìm thấy việc {code}.")
        if not (task["creator_id"] == user["telegram_id"]
                or user["role"] == roles.ROLE_ADMIN):
            raise ApiError(HTTPStatus.FORBIDDEN,
                           "Chỉ người tạo việc hoặc Admin mới thêm "
                           "tư liệu được.")
        if form is None:
            if not self._is_multipart():
                raise ApiError(HTTPStatus.BAD_REQUEST,
                               "Cần gửi multipart/form-data kèm file.")
            form = self._parse_multipart()
        parts = self._form_files(form)
        if not parts:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Chưa có file nào.")
        self._validate_parts(parts)
        saved = self._save_parts(code, self._plan_names(code, parts))
        file_ids = _json_list(task["file_ids"])
        for name in saved:
            if name not in file_ids:
                file_ids.append(name)
        self.app.webdb.set_task_file_ids(code, file_ids)
        self.app.store.audit(
            user["telegram_id"], "upload_files", "task", code,
            detail=f"files={len(saved)} via=webapp")
        task = self.app.store.get_task(code)
        self._send_json(HTTPStatus.CREATED,
                        {"files": self._task_files(task)})

    def _upload_to_task(self) -> None:
        if not self._is_multipart():
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           "Cần gửi multipart/form-data.")
        form = self._parse_multipart()
        codes = self._form_texts(form, "task_code")
        if not codes or not codes[0].strip():
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           "Thiếu task_code của việc cần gắn tư liệu.")
        self._add_task_files(codes[0].strip(), form=form)

    def _serve_task_file(self, code: str, filename: str) -> None:
        user = self._current_user()
        self._require_granted(user)
        task = self.app.store.get_task(code)
        if task is None:
            raise ApiError(HTTPStatus.NOT_FOUND,
                           f"Không tìm thấy việc {code}.")
        name = safe_filename(filename)
        directory = (self.app.files_dir / code).resolve()
        target = (directory / name).resolve()
        if target.parent != directory or not target.is_file():
            raise ApiError(HTTPStatus.NOT_FOUND, "Không tìm thấy file.")
        self._stream_file(target)

    def _serve_draft_video(self, output_id: int) -> None:
        user = self._current_user()
        self._require_granted(user)
        output = self.app.store.get_output(output_id)
        if output is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "Không tìm thấy thẻ kênh.")
        raw = output["draft_video_path"] if "draft_video_path" \
            in output.keys() else None
        if not raw:
            raise ApiError(HTTPStatus.NOT_FOUND,
                           "Thẻ kênh này chưa có video nháp.")
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = self.app.files_dir / candidate
            if not candidate.exists() and raw.startswith("data/files/"):
                candidate = self.app.files_dir / raw[len("data/files/"):]
        target = candidate.resolve()
        root = self.app.files_dir.resolve()
        if root not in target.parents or not target.is_file():
            raise ApiError(HTTPStatus.NOT_FOUND,
                           "Không tìm thấy file video nháp.")
        self._stream_file(target)

    def _stream_file(self, target: Path) -> None:
        size = target.stat().st_size
        content_type = mimetypes.guess_type(target.name)[0] \
            or "application/octet-stream"
        start, end, partial = 0, size - 1, False
        range_header = self.headers.get("Range") or ""
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
        if range_header and match:
            first, last = match.groups()
            if first == "" and last == "":
                return self._range_not_satisfiable(size)
            if first == "":
                count = int(last)
                if count <= 0:
                    return self._range_not_satisfiable(size)
                start = max(size - count, 0)
            else:
                start = int(first)
                if last:
                    end = min(int(last), size - 1)
            if start > end or start >= size:
                return self._range_not_satisfiable(size)
            partial = True
        length = max(end - start + 1, 0)
        self.send_response(HTTPStatus.PARTIAL_CONTENT if partial
                           else HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        if partial:
            self.send_header("Content-Range",
                             f"bytes {start}-{end}/{size}")
        self.send_header(
            "Content-Disposition",
            f"inline; filename*=UTF-8''{quote(target.name)}")
        self.end_headers()
        if self.command == "HEAD" or length == 0:
            return
        with open(target, "rb") as fh:
            fh.seek(start)
            remaining = length
            while remaining > 0:
                chunk = fh.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def _range_not_satisfiable(self, size: int) -> None:
        self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
        self.send_header("Content-Range", f"bytes */{size}")
        self.send_header("Content-Length", "0")
        self.end_headers()

    # -------------------------------------------------------------- tasks
    def _list_tasks(self, query: dict) -> None:
        user = self._current_user()
        self._require_granted(user)
        try:
            limit = min(max(int(query.get("limit", 50)), 1), 200)
            offset = max(int(query.get("offset", 0)), 0)
            creator = query.get("creator")
            creator_id = int(creator) if creator else None
        except ValueError:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           "Tham số phân trang không hợp lệ.")
        status = query.get("status") or None
        if status and status not in storage.ALL_STATUSES:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           f"Trạng thái không hợp lệ: {status}")
        channel = query.get("channel") or None
        if channel and channel not in storage.CHANNELS:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           f"Kênh không hợp lệ: {channel}")
        rows, total = self.app.webdb.list_tasks(
            status=status, channel=channel, creator_id=creator_id,
            q=query.get("q") or None, limit=limit, offset=offset)
        self._send_json(HTTPStatus.OK, {
            "items": [task_public(r) for r in rows],
            "total": total, "limit": limit, "offset": offset,
        })

    def _task_detail(self, code: str) -> None:
        user = self._current_user()
        self._require_granted(user)
        task = self.app.store.get_task(code)
        if task is None:
            raise ApiError(HTTPStatus.NOT_FOUND,
                           f"Không tìm thấy việc {code}.")
        outputs = self.app.store.list_outputs(code)
        output_ids = {str(o["id"]) for o in outputs}
        audit = [
            {
                "id": e["id"], "actor_id": e["actor_id"],
                "action": e["action"], "target_type": e["target_type"],
                "target_id": e["target_id"], "detail": e["detail"],
                "created_at": e["created_at"],
            }
            for e in self.app.store.audit_entries()
            if (e["target_type"] == "task" and e["target_id"] == code)
            or (e["target_type"] == "output" and e["target_id"] in output_ids)
        ]
        creator = self.app.store.get_user(task["creator_id"])
        creator_name = creator["display_name"] if creator else None
        self._send_json(HTTPStatus.OK, {
            "task": task_public(task, creator_name=creator_name),
            "outputs": [output_public(o) for o in outputs],
            "files": self._task_files(task),
            "audit": audit,
        })

    @staticmethod
    def _parse_destinations(raw_values) -> list:
        destinations = []
        for raw in raw_values:
            if isinstance(raw, list):
                candidates = raw
            elif isinstance(raw, str):
                text = raw.strip()
                if text.startswith("["):
                    try:
                        parsed = json.loads(text)
                    except ValueError:
                        parsed = None
                    candidates = parsed if isinstance(parsed, list) \
                        else [text]
                else:
                    candidates = [part.strip() for part in text.split(",")]
            else:
                candidates = [raw]
            for candidate in candidates:
                if candidate and candidate not in destinations:
                    destinations.append(candidate)
        return destinations

    def _create_task(self) -> None:
        user = self._current_user()
        self._require_role(
            user, CREATOR_ROLES,
            "Tài khoản chưa được cấp quyền tạo việc.")
        planned = []
        file_names = []
        if self._is_multipart():
            form = self._parse_multipart()
            hints = self._form_texts(form, "hint")
            hint = hints[0].strip() if hints else ""
            destinations = self._parse_destinations(
                self._form_texts(form, "destinations"))
            if not destinations:
                destinations = list(storage.DEFAULT_DESTINATIONS)
            parts = self._form_files(form)
            self._validate_parts(parts)
        else:
            body = self._read_json()
            hint = str(body.get("hint") or "").strip()
            destinations = body.get("destinations")
            if destinations is None:
                destinations = list(storage.DEFAULT_DESTINATIONS)
            parts = []
        if not isinstance(destinations, list) or not destinations:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           "destinations phải là danh sách kênh không rỗng.")
        unknown = [d for d in destinations if d not in storage.CHANNELS]
        if unknown:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           f"Kênh không hợp lệ: {', '.join(map(str, unknown))}")
        task = self.app.store.create_task(
            creator_id=user["telegram_id"], creator_role=user["role"],
            hint=hint, file_ids=[], destinations=list(destinations))
        if parts:
            planned = self._plan_names(task["code"], parts)
            file_names = self._save_parts(task["code"], planned)
            self.app.webdb.set_task_file_ids(task["code"], file_names)
        # Mirror the bot exactly: audit + one output per channel.
        self.app.store.audit(
            user["telegram_id"], "create_task", "task", task["code"],
            detail=f"role={user['role']} files={len(file_names)} via=webapp")
        if parts or self._is_multipart():
            # The web wizard's final button IS the confirmation, like
            # the bot wizard's "Chốt! Gửi Muse" step.
            self.app.store.audit(
                user["telegram_id"], "destinations_confirmed", "task",
                task["code"],
                detail=json.dumps(list(destinations), ensure_ascii=False))
        outputs = self.app.store.sync_outputs_for_task(task)
        task = self.app.store.get_task(task["code"])
        creator = self.app.store.get_user(task["creator_id"])
        # GĐ3: a new task means reviewers will have drafts to check.
        self._notify_async(
            self._reviewer_ids(exclude=user["telegram_id"]),
            f"🗂 Việc mới {task['code']}",
            hint or "(chưa có gợi ý)",
            f"/?task={task['code']}")
        self._send_json(HTTPStatus.CREATED, {
            "task": task_public(
                task,
                creator_name=creator["display_name"] if creator else None),
            "outputs": [output_public(o) for o in outputs],
            "files": self._task_files(task),
        })

    # ---------------------------------------------------- output actions
    def _output_action(self, output_id: int, action: str) -> None:
        if action not in OUTPUT_ACTIONS:
            raise ApiError(HTTPStatus.NOT_FOUND, "Thao tác không hợp lệ.")
        user = self._current_user()
        self._require_granted(user)
        output = self.app.store.get_output(output_id)
        if output is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "Không tìm thấy thẻ kênh.")
        task = self.app.store.get_task(output["task_code"])
        if task is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "Không tìm thấy việc gốc.")
        if output["pending_choice"] and action not in (
                "publish", "publish-abort", "schedule", "schedule-abort"):
            raise ApiError(HTTPStatus.CONFLICT,
                           "Thẻ kênh đang có một lựa chọn chưa hoàn tất.")
        body = self._read_json() if self.headers.get("Content-Length") \
            else {}
        handler = getattr(self, f"_act_{action.replace('-', '_')}")
        handler(user, output, task, body)

    def _done(self, output_id: int, message: str,
              status: int = HTTPStatus.OK, extra=None) -> None:
        payload = {"ok": True, "message": message,
                   "output": output_public(
                       self.app.store.get_output(output_id))}
        if extra:
            payload.update(extra)
        self._send_json(status, payload)

    def _bad_state(self, message="Thẻ kênh không ở trạng thái làm "
                                  "được thao tác này."):
        raise ApiError(HTTPStatus.CONFLICT, message)

    def _deny(self, user, output, task, audit_action: str,
              message: str):
        detail = f"role={user['role']}"
        if audit_action in ("denied_output_publish_attempt",
                            "denied_output_retract_attempt"):
            detail += f" can_publish={bool(user['can_publish'])}"
        self.app.store.audit(user["telegram_id"], audit_action, "output",
                             output["id"], detail=detail)
        raise ApiError(HTTPStatus.FORBIDDEN, message)

    def _require_creator(self, user, task):
        if task["creator_id"] != user["telegram_id"]:
            raise ApiError(HTTPStatus.FORBIDDEN,
                           "Chỉ người tạo việc mới làm được thao tác này.")

    def _auto_approve_admin_own(self, user, output, task):
        """Bot rule: an Admin acting on their OWN task's draft moves
        it straight to APPROVED_WAITING, audited auto=admin_own."""
        if (task["creator_id"] == user["telegram_id"]
                and user["role"] == roles.ROLE_ADMIN
                and output["draft_ref"]
                and output["status"] in (storage.STATUS_DRAFT,
                                         storage.STATUS_REJECTED,
                                         storage.STATUS_PENDING)):
            self.app.store.set_output_status(
                output["id"], storage.STATUS_APPROVED_WAITING)
            self.app.store.audit(
                user["telegram_id"], "approve_output", "output",
                output["id"],
                detail=f"task={task['code']} channel={output['channel']} "
                       "auto=admin_own")
            self.app.store.sync_task_status_from_outputs(task["code"])
            return self.app.store.get_output(output["id"])
        return None

    def _act_submit(self, user, output, task, body):
        self._require_creator(user, task)
        if output["status"] not in (storage.STATUS_DRAFT,
                                    storage.STATUS_REJECTED):
            self._bad_state("Thẻ kênh này không ở trạng thái gửi duyệt được.")
        if not output["draft_ref"]:
            raise ApiError(HTTPStatus.CONFLICT,
                           "Kênh này chưa có bản nháp — Muse đang viết.")
        self.app.store.set_output_status(output["id"], storage.STATUS_PENDING)
        self.app.store.audit(
            user["telegram_id"], "submit_output", "output", output["id"],
            detail=f"task={task['code']} channel={output['channel']}")
        self.app.store.sync_task_status_from_outputs(task["code"])
        self._notify_async(
            self._reviewer_ids(exclude=user["telegram_id"]),
            "⏳ Thẻ kênh chờ duyệt",
            f"{task['code']} · {storage.channel_label(output['channel'])}",
            f"/?task={task['code']}")
        self._done(output["id"], "Đã gửi duyệt.")

    def _act_approve(self, user, output, task, body):
        if not roles.can_review(user["role"]):
            self._deny(user, output, task, "denied_output_approve_attempt",
                       "Bạn không có quyền duyệt.")
        if output["status"] != storage.STATUS_PENDING:
            self._bad_state("Thẻ kênh này chưa được gửi duyệt.")
        self.app.store.set_output_status(
            output["id"], storage.STATUS_APPROVED_WAITING)
        self.app.store.audit(
            user["telegram_id"], "approve_output", "output", output["id"],
            detail=f"task={task['code']} channel={output['channel']}")
        self.app.store.sync_task_status_from_outputs(task["code"])
        if task["creator_id"] != user["telegram_id"]:
            self._notify_async(
                [task["creator_id"]], "✅ Thẻ kênh đã được duyệt",
                f"{task['code']} · "
                f"{storage.channel_label(output['channel'])}",
                f"/?task={task['code']}")
        self._done(output["id"], "Đã duyệt, thẻ kênh chuyển sang chờ đăng.")

    def _reason(self, body) -> str:
        reason = str(body.get("reason") or "").strip()
        if not reason:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           "Cần nhập nội dung/lý do.")
        return reason

    def _act_reject(self, user, output, task, body):
        if not roles.can_review(user["role"]):
            self._deny(user, output, task, "denied_output_reject_attempt",
                       "Bạn không có quyền trả lại.")
        if output["status"] not in (storage.STATUS_PENDING,
                                    storage.STATUS_DRAFT):
            self._bad_state("Thẻ kênh này không ở trạng thái trả lại được.")
        if output["status"] == storage.STATUS_DRAFT \
                and not output["draft_ref"]:
            raise ApiError(HTTPStatus.CONFLICT,
                           "Kênh này chưa có bản nháp để trả lại.")
        reason = self._reason(body)
        self.app.store.set_output_status(
            output["id"], storage.STATUS_REJECTED, reject_reason=reason)
        self.app.store.audit(
            user["telegram_id"], "reject_output", "output", output["id"],
            detail=f"task={task['code']} channel={output['channel']} "
                   f"reason={reason}")
        self.app.store.sync_task_status_from_outputs(task["code"])
        if task["creator_id"] != user["telegram_id"]:
            self._notify_async(
                [task["creator_id"]], "↩️ Thẻ kênh bị trả lại",
                f"{task['code']} · "
                f"{storage.channel_label(output['channel'])}: {reason}",
                f"/?task={task['code']}")
        self._done(output["id"], "Đã trả lại kèm yêu cầu chỉnh sửa.")

    def _act_revise(self, user, output, task, body):
        self._require_creator(user, task)
        if output["status"] not in (storage.STATUS_DRAFT,
                                    storage.STATUS_REJECTED):
            self._bad_state("Thẻ kênh này không ở trạng thái sửa lại được.")
        if not output["draft_ref"]:
            raise ApiError(HTTPStatus.CONFLICT,
                           "Kênh này chưa có bản nháp để sửa.")
        reason = self._reason(body)
        self.app.store.set_output_status(
            output["id"], storage.STATUS_REJECTED, reject_reason=reason)
        self.app.store.audit(
            user["telegram_id"], "revise_output", "output", output["id"],
            detail=f"task={task['code']} channel={output['channel']} "
                   f"reason={reason}")
        self.app.store.sync_task_status_from_outputs(task["code"])
        self._done(output["id"], "Đã ghi nhận yêu cầu sửa lại.")

    def _act_cancel(self, user, output, task, body):
        if not roles.can_review(user["role"]):
            self._deny(user, output, task, "denied_output_cancel_attempt",
                       "Bạn không có quyền hủy bài.")
        if output["status"] not in (storage.STATUS_DRAFT,
                                    storage.STATUS_PENDING,
                                    storage.STATUS_REJECTED):
            self._bad_state("Bài này không còn ở trạng thái hủy được.")
        self.app.store.set_output_status(output["id"],
                                         storage.STATUS_CANCELLED)
        self.app.store.audit(
            user["telegram_id"], "cancel_output", "output", output["id"],
            detail=f"task={task['code']} channel={output['channel']}")
        self.app.store.sync_task_status_from_outputs(task["code"])
        self._done(output["id"], "Đã hủy bài.")

    def _prepare_publishable(self, user, output, task):
        if output["status"] in (storage.STATUS_DRAFT,
                                storage.STATUS_REJECTED,
                                storage.STATUS_PENDING):
            approved = self._auto_approve_admin_own(user, output, task)
            if approved is None:
                self._bad_state("Thẻ kênh này chưa ở trạng thái chờ đăng.")
            output = approved
        if output["status"] != storage.STATUS_APPROVED_WAITING:
            self._bad_state("Thẻ kênh này chưa ở trạng thái chờ đăng.")
        return output

    def _act_publish(self, user, output, task, body):
        if not roles.can_publish(user):
            self._deny(user, output, task,
                       "denied_output_publish_attempt",
                       "Bạn không có quyền đăng.")
        output = self._prepare_publishable(user, output, task)
        if output["channel"] == "facebook":
            target = body.get("target")
            if target is None:
                # Mirror the bot: opening the target choice freezes
                # the card (pending_choice) until publish or abort.
                self.app.store.set_output_pending_choice(output["id"], True)
                return self._send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {
                    "error": "Cần chọn nơi đăng Facebook trước.",
                    "code": "target_required",
                    "targets": list(FB_TARGETS),
                    "output": output_public(
                        self.app.store.get_output(output["id"])),
                })
            if target not in FB_TARGETS:
                raise ApiError(HTTPStatus.BAD_REQUEST,
                               "Nơi đăng Facebook không hợp lệ.")
        else:
            target = None
            if output["pending_choice"]:
                raise ApiError(HTTPStatus.CONFLICT,
                               "Lệnh đăng đang được xử lý.")
        if output["scheduled_at"]:
            self.app.store.set_output_schedule(output["id"], None, None)
        self.app.store.set_output_pending_choice(output["id"], True)
        detail = f"task={task['code']} channel={output['channel']}"
        if target:
            detail += f" target={target}"
        self.app.store.audit(user["telegram_id"], "publish_requested",
                             "output", output["id"], detail=detail)
        body_text = (f"{task['code']} · "
                     f"{storage.channel_label(output['channel'])}")
        if target:
            body_text += f" · nơi đăng: {target}"
        self._notify_async(
            self._reviewer_ids(exclude=user["telegram_id"]),
            "🚀 Có lệnh đăng mới", body_text, f"/?task={task['code']}")
        self._done(output["id"],
                   "Đã nhận lệnh đăng — Muse sẽ đăng ngay và gửi "
                   "link bài khi xong.")

    def _act_publish_abort(self, user, output, task, body):
        if not roles.can_publish(user):
            raise ApiError(HTTPStatus.FORBIDDEN, "Bạn không có quyền đăng.")
        if output["channel"] != "facebook" \
                or output["status"] != storage.STATUS_APPROVED_WAITING:
            self._bad_state("Thao tác hủy đăng không hợp lệ lúc này.")
        self.app.store.audit(
            user["telegram_id"], "publish_aborted", "output", output["id"],
            detail=f"task={task['code']} channel=facebook "
                   "stage=target_choice via=webapp")
        self.app.store.set_output_pending_choice(output["id"], False)
        self._done(output["id"], "Đã hủy lệnh đăng.")

    @staticmethod
    def _parse_schedule_body(body):
        """Return an aware ICT datetime from {scheduled_at} (ISO or
        the bot's typed formats) or {preset}, else None."""
        preset = body.get("preset")
        now = datetime.now(ICT)
        if preset is not None:
            key = str(preset)
            if key in ("60", "120"):
                return now + timedelta(minutes=int(key))
            if key == "eve":
                when = now.replace(hour=20, minute=0, second=0,
                                   microsecond=0)
                return when if when > now else when + timedelta(days=1)
            if key == "mor":
                return (now + timedelta(days=1)).replace(
                    hour=8, minute=0, second=0, microsecond=0)
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           "preset đặt lịch không hợp lệ.")
        raw = body.get("scheduled_at")
        if raw is None or str(raw).strip() == "":
            return None
        text = str(raw).strip()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=ICT)
            when = parsed.astimezone(ICT)
            if when <= now:
                raise ApiError(HTTPStatus.BAD_REQUEST,
                               "Giờ đăng phải ở tương lai.")
            return when
        match = re.fullmatch(r"(\d{1,2}):(\d{2})", text)
        if match:
            try:
                when = now.replace(hour=int(match.group(1)),
                                   minute=int(match.group(2)),
                                   second=0, microsecond=0)
            except ValueError:
                when = None
            if when is None:
                raise ApiError(HTTPStatus.BAD_REQUEST,
                               "Giờ đăng không hợp lệ.")
            return when if when > now else when + timedelta(days=1)
        match = re.fullmatch(
            r"(?:(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\s+)?"
            r"(\d{1,2}):(\d{2})"
            r"(?:\s+(\d{1,2})/(\d{1,2})(?:/(\d{4}))?)?", text)
        if not match:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           "Chưa rõ giờ đăng. Dùng mẫu 16:30 hoặc "
                           "24/10 16:30 (giờ Việt Nam).")
        day = match.group(1) or match.group(6)
        month = match.group(2) or match.group(7)
        year = match.group(3) or match.group(8)
        if day is None:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           "Chưa rõ ngày đăng.")
        try:
            when = datetime(int(year) if year else now.year, int(month),
                            int(day), int(match.group(4)),
                            int(match.group(5)), tzinfo=ICT)
        except ValueError:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           "Ngày giờ đăng không hợp lệ.")
        if when <= now:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           "Giờ đăng phải ở tương lai.")
        return when

    def _schedule_warnings(self, output, when_utc: str):
        """The bot's warn-never-block rule for posts < 1h apart."""
        warnings = []
        label = storage.channel_label(output["channel"])
        for other in self.app.store.list_scheduled_outputs(
                output["channel"]):
            if other["id"] == output["id"]:
                continue
            delta = abs((datetime.fromisoformat(other["scheduled_at"])
                         - datetime.fromisoformat(when_utc)).total_seconds())
            if delta < 3600:
                warnings.append(
                    f"Kênh {label} đã có bài đặt lúc "
                    f"{other['scheduled_at']} (việc {other['task_code']})"
                    " — cách bài này chưa tới 1 giờ.")
        latest = self.app.store.latest_published_output(output["channel"])
        if latest is not None:
            gap = (datetime.fromisoformat(when_utc)
                   - datetime.fromisoformat(latest["updated_at"])
                   ).total_seconds()
            if 0 <= gap < 3600:
                warnings.append(
                    f"Kênh {label} mới đăng bài lúc {latest['updated_at']}"
                    f" (việc {latest['task_code']}) — bài này đăng tiếp"
                    " trong vòng 1 giờ.")
        return warnings

    def _act_schedule(self, user, output, task, body):
        if output["status"] in (storage.STATUS_DRAFT,
                                storage.STATUS_REJECTED,
                                storage.STATUS_PENDING):
            approved = self._auto_approve_admin_own(user, output, task)
            if approved is None:
                self._bad_state("Bài phải được duyệt trước khi đặt "
                                "lịch đăng.")
            output = approved
        if not roles.can_publish(user):
            raise ApiError(HTTPStatus.FORBIDDEN,
                           "Bạn không có quyền đăng.")
        if output["status"] != storage.STATUS_APPROVED_WAITING:
            self._bad_state("Thẻ kênh này chưa ở trạng thái đặt lịch được.")
        target = body.get("target")
        if output["channel"] == "facebook":
            if target is not None and target not in FB_TARGETS:
                raise ApiError(HTTPStatus.BAD_REQUEST,
                               "Nơi đăng Facebook không hợp lệ.")
            if target is None:
                self.app.store.set_output_pending_choice(output["id"], True)
                return self._send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {
                    "error": "Cần chọn nơi đăng Facebook trước khi "
                             "đặt lịch.",
                    "code": "target_required",
                    "targets": list(FB_TARGETS),
                    "output": output_public(
                        self.app.store.get_output(output["id"])),
                })
        elif target is not None:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           "Kênh này không có nơi đăng để chọn.")
        when = self._parse_schedule_body(body)
        if when is None:
            self.app.store.set_output_pending_choice(output["id"], True)
            return self._send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {
                "error": "Cần chọn giờ đăng.",
                "code": "time_required",
                "output": output_public(
                    self.app.store.get_output(output["id"])),
            })
        when_utc = when.astimezone(timezone.utc).isoformat(timespec="seconds")
        warnings = self._schedule_warnings(output, when_utc)
        self.app.store.set_output_pending_choice(output["id"], False)
        self.app.store.set_output_schedule(output["id"], when_utc, target)
        detail = (f"task={task['code']} channel={output['channel']} "
                  f"when={when.strftime('%H:%M %d/%m/%Y')}")
        if target:
            detail += f" target={target}"
        self.app.store.audit(user["telegram_id"], "schedule_set",
                             "output", output["id"], detail=detail)
        if task["creator_id"] != user["telegram_id"]:
            self._notify_async(
                [task["creator_id"]], "🕐 Đã đặt lịch đăng",
                f"{task['code']} · "
                f"{storage.channel_label(output['channel'])} · "
                f"{when.strftime('%H:%M %d/%m/%Y')}",
                f"/?task={task['code']}")
        self._done(output["id"], "Đã đặt lịch đăng.",
                   extra={"warnings": warnings, "scheduled_at": when_utc})

    def _act_schedule_abort(self, user, output, task, body):
        self.app.store.set_output_pending_choice(output["id"], False)
        self._done(output["id"], "Đã hủy đặt lịch.")

    def _act_unschedule(self, user, output, task, body):
        if not roles.can_publish(user):
            raise ApiError(HTTPStatus.FORBIDDEN,
                           "Bạn không có quyền đăng.")
        if output["status"] != storage.STATUS_APPROVED_WAITING \
                or not output["scheduled_at"]:
            self._bad_state("Thẻ kênh này chưa có lịch đăng.")
        self.app.store.set_output_schedule(output["id"], None, None)
        self.app.store.audit(
            user["telegram_id"], "schedule_cancelled", "output",
            output["id"],
            detail=f"task={task['code']} channel={output['channel']}")
        self._done(output["id"], "Đã hủy lịch đăng.")

    def _act_retract(self, user, output, task, body):
        if not roles.can_publish(user):
            self._deny(user, output, task,
                       "denied_output_retract_attempt",
                       "Bạn không có quyền thu hồi thẻ kênh đã đăng.")
        if output["status"] != storage.STATUS_PUBLISHED:
            self._bad_state("Thẻ kênh này chưa được đăng.")
        if output["channel"] == "facebook" and output["public_url"]:
            pending = self.app.store.latest_audit_id(
                output["id"], "retract_requested")
            done = self.app.store.latest_audit_id(
                output["id"], "retract_output")
            if pending is not None and (done is None or pending > done):
                raise ApiError(HTTPStatus.CONFLICT,
                               "Lệnh thu hồi đang được xử lý rồi.")
            self.app.store.audit(
                user["telegram_id"], "retract_requested", "output",
                output["id"],
                detail=f"task={task['code']} channel=facebook "
                       f"public_url={output['public_url']}")
            self._notify_async(
                self._reviewer_ids(exclude=user["telegram_id"]),
                "↩️ Yêu cầu thu hồi bài Facebook",
                f"{task['code']} · {output['public_url']}",
                f"/?task={task['code']}")
            return self._done(
                output["id"],
                "Đã nhận lệnh thu hồi — Muse sẽ xoá bài thật "
                "trên Facebook.")
        self.app.store.set_output_status(output["id"],
                                         storage.STATUS_RETRACTED)
        self.app.store.audit(
            user["telegram_id"], "retract_output", "output", output["id"],
            detail=f"task={task['code']} channel={output['channel']}")
        self.app.store.sync_task_status_from_outputs(task["code"])
        if task["creator_id"] != user["telegram_id"]:
            self._notify_async(
                [task["creator_id"]], "🗑 Bài đã bị thu hồi",
                f"{task['code']} · "
                f"{storage.channel_label(output['channel'])}",
                f"/?task={task['code']}")
        self._done(output["id"], "Đã thu hồi.")

    # ------------------------------------------- queues / notifications
    def _review_queue(self) -> None:
        user = self._current_user()
        if not roles.can_review(user["role"]):
            raise ApiError(HTTPStatus.FORBIDDEN,
                           "Chỉ người duyệt mới xem được hàng chờ duyệt.")
        rows = self.app.webdb.review_queue()
        self._send_json(HTTPStatus.OK,
                        {"items": [output_public(r) for r in rows]})

    def _scheduled(self) -> None:
        user = self._current_user()
        if not roles.can_review(user["role"]):
            raise ApiError(HTTPStatus.FORBIDDEN,
                           "Chỉ người duyệt mới xem được lịch đăng.")
        rows = self.app.webdb.scheduled_outputs()
        self._send_json(HTTPStatus.OK,
                        {"items": [output_public(r) for r in rows]})

    def _notifications(self) -> None:
        user = self._current_user()
        self._require_granted(user)
        items = self.app.webdb.notifications_for_user(user)
        self._send_json(HTTPStatus.OK, {
            "items": items,
            "unread": sum(1 for item in items if not item["read"]),
        })

    def _notifications_read(self) -> None:
        user = self._current_user()
        self._require_granted(user)
        body = self._read_json()
        if body.get("all"):
            items = self.app.webdb.notifications_for_user(user)
            keys = [item["key"] for item in items]
        else:
            keys = body.get("keys") or []
            if not isinstance(keys, list):
                raise ApiError(HTTPStatus.BAD_REQUEST,
                               "keys phải là danh sách.")
        marked = self.app.webdb.mark_notifications_read(
            user["telegram_id"], keys)
        self._send_json(HTTPStatus.OK, {"ok": True, "marked": marked})

    # ------------------------------------------- GĐ3: push plumbing
    def _reviewer_ids(self, exclude=None) -> list:
        return [u["telegram_id"] for u in self.app.store.list_users()
                if roles.can_review(u["role"])
                and u["telegram_id"] != exclude]

    def _admin_ids(self) -> list:
        return [u["telegram_id"] for u in self.app.store.list_users()
                if u["role"] == roles.ROLE_ADMIN]

    def _notify_async(self, user_ids, title: str, body: str,
                      url: str = "/") -> None:
        """Fire-and-forget Web Push from a background thread: a slow
        or failing push service must never delay or break the request
        that triggered the notification."""
        service = self.app.push
        ids = [u for u in dict.fromkeys(user_ids or [])]
        if service is None or not ids:
            return

        def _send():
            try:
                service.notify_users(ids, title, body, url)
            except Exception:  # notify_users already swallows; be safe
                pass

        threading.Thread(target=_send, daemon=True,
                         name="webapp-push").start()

    def _require_push(self) -> None:
        if self.app.push is None:
            raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE,
                           "Thông báo đẩy chưa khả dụng trên máy chủ.")

    def _push_vapid_key(self) -> None:
        self._current_user()
        self._require_push()
        self._send_json(HTTPStatus.OK,
                        {"public_key": self.app.push.public_key})

    @staticmethod
    def _validate_endpoint(endpoint) -> str:
        endpoint = str(endpoint or "").strip()
        parsed = urlparse(endpoint)
        host = (parsed.hostname or "").lower()
        if parsed.scheme == "https" and host:
            return endpoint
        if parsed.scheme == "http" and host in ("127.0.0.1", "localhost",
                                                "::1"):
            return endpoint  # loopback endpoints: tests/dev only
        raise ApiError(HTTPStatus.BAD_REQUEST,
                       "endpoint thông báo đẩy không hợp lệ.")

    def _push_subscribe(self) -> None:
        user = self._current_user()
        self._require_granted(user)
        self._require_push()
        from .push import b64url_decode

        body = self._read_json()
        endpoint = self._validate_endpoint(body.get("endpoint"))
        keys = body.get("keys") or {}
        p256dh = str(keys.get("p256dh") or "")
        auth = str(keys.get("auth") or "")
        try:
            point = b64url_decode(p256dh)
            auth_bytes = b64url_decode(auth)
        except Exception:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           "Khóa đăng ký thông báo đẩy không hợp lệ.")
        if len(point) != 65 or point[0] != 0x04 or len(auth_bytes) < 16:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           "Khóa đăng ký thông báo đẩy không hợp lệ.")
        row = self.app.webdb.upsert_push_subscription(
            user["telegram_id"], endpoint, p256dh, auth,
            user_agent=(self.headers.get("User-Agent") or "")[:300])
        self._send_json(HTTPStatus.OK, {
            "ok": True, "id": row["id"], "endpoint": row["endpoint"],
        })

    def _push_unsubscribe(self) -> None:
        user = self._current_user()
        self._require_granted(user)
        body = self._read_json()
        endpoint = str(body.get("endpoint") or "").strip()
        if not endpoint:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Thiếu endpoint.")
        removed = self.app.webdb.delete_push_subscription(
            endpoint, user_id=user["telegram_id"])
        self._send_json(HTTPStatus.OK, {"ok": True, "removed": removed})

    def _push_test(self) -> None:
        user = self._current_user()
        self._require_granted(user)
        self._require_push()
        results = self.app.push.notify_user_detailed(
            user["telegram_id"], "🔔 Thông báo thử",
            "Web App Giao Việc gửi thông báo đẩy thử — bạn đã bật "
            "thông báo thành công.", "/")
        self._send_json(HTTPStatus.OK, {
            "ok": True,
            "sent": sum(1 for r in results if r["ok"]),
            "results": [{
                "endpoint": r["endpoint"], "ok": r["ok"],
                "status": r["status"], "gone": r["gone"],
                "error": r["error"],
            } for r in results],
        })

    # -------------------------------------------------------------- stats
    def _stats_daily_summary(self) -> None:
        user = self._current_user()
        self._require_granted(user)
        self._send_json(HTTPStatus.OK,
                        daily_summary_data(self.app.store))

    def _stats_summary(self, query: dict) -> None:
        user = self._current_user()
        if not roles.can_review(user["role"]):
            raise ApiError(HTTPStatus.FORBIDDEN,
                           "Chỉ người duyệt mới xem được thống kê.")
        period = query.get("period", "all")
        if period not in stats.PERIODS:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           f"Kỳ không hợp lệ: {period}")
        data = stats.collect_stats(self.app.store, period)
        self._send_json(HTTPStatus.OK, {
            "period": data["period"],
            "label": data["label"],
            "tasks_total": len(data["tasks"]),
            "outputs_total": len(data["outputs"]),
            "published_total": len(data["published"]),
            "task_status_counts": data["task_status_counts"],
            "output_channel_status": data["output_channel_status"],
            "per_creator": data["per_creator"],
            "video": data["video"],
        })

    def _stats_export(self, query: dict) -> None:
        user = self._current_user()
        if not roles.can_review(user["role"]):
            raise ApiError(HTTPStatus.FORBIDDEN,
                           "Chỉ người duyệt mới xuất được thống kê.")
        fmt = (query.get("format") or "csv").lower()
        if fmt not in ("csv", "xlsx"):
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           "format phải là csv hoặc xlsx.")
        period = query.get("period", "all")
        if period not in stats.PERIODS:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           f"Kỳ không hợp lệ: {period}")
        data = stats.collect_stats(self.app.store, period)
        slug = {"today": "hom-nay", "week": "tuan-nay",
                "month": "thang-nay", "all": "tat-ca"}[period]
        with tempfile.TemporaryDirectory() as tmp:
            if fmt == "csv":
                path = Path(tmp) / f"thongke-{slug}.csv"
                stats.write_csv(data["export_rows"], path)
                content_type = "text/csv; charset=utf-8"
            else:
                path = Path(tmp) / f"thongke-{slug}.xlsx"
                try:
                    stats.write_xlsx(data["export_rows"], path)
                except ImportError:
                    raise ApiError(
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        "Máy chủ chưa có thư viện tạo Excel (openpyxl).")
                content_type = ("application/vnd.openxmlformats-"
                                "officedocument.spreadsheetml.sheet")
            body = path.read_bytes()
        self._send_bytes(HTTPStatus.OK, body, content_type, headers={
            "Content-Disposition":
                f"attachment; filename*=UTF-8''{quote(path.name)}",
        })

    # -------------------------------------------------------------- users
    def _list_users(self) -> None:
        user = self._current_user()
        self._require_role(user, (roles.ROLE_ADMIN, roles.ROLE_DEPUTY),
                           "Chỉ Admin/Phó Admin mới xem được danh sách "
                           "người dùng.")
        rows = self.app.store.list_users()
        self._send_json(HTTPStatus.OK,
                        {"items": [user_public(r) for r in rows]})

    def _create_user(self) -> None:
        actor = self._current_user()
        self._require_role(actor, (roles.ROLE_ADMIN, roles.ROLE_DEPUTY),
                           "Chỉ Admin/Phó Admin mới tạo được tài khoản.")
        body = self._read_json()
        role = body.get("role")
        if role not in roles.ALL_ROLES:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           f"Vai trò không hợp lệ: {role}")
        if not roles.can_grant(actor["role"], role):
            raise ApiError(HTTPStatus.FORBIDDEN,
                           "Bạn không được cấp vai trò này.")
        name = str(body.get("name") or body.get("display_name") or "").strip()
        email = str(body.get("email") or "").strip().lower() or None
        phone = str(body.get("phone") or "").strip() or None
        password = str(body.get("password") or "")
        if not name:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Thiếu tên hiển thị.")
        if not email and not phone:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           "Cần ít nhất email hoặc số điện thoại.")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           f"Mật khẩu tạm phải có ít nhất "
                           f"{MIN_PASSWORD_LENGTH} ký tự.")
        webdb = self.app.webdb
        if email and webdb.find_user_by_email(email):
            raise ApiError(HTTPStatus.CONFLICT,
                           "Email này đã có tài khoản.")
        if phone and webdb.find_user_by_phone(phone):
            raise ApiError(HTTPStatus.CONFLICT,
                           "Số điện thoại này đã có tài khoản.")
        user_id = webdb.create_web_user(
            display_name=name, email=email, phone=phone,
            password_hash=hash_password(password))
        can_publish = bool(body.get("can_publish")) or role == roles.ROLE_ADMIN
        self.app.store.set_role(user_id, role, can_publish=can_publish)
        self.app.store.audit(
            actor["telegram_id"], "create_web_user", "user", user_id,
            detail=f"role={role} via=webapp")
        created = webdb.get_user(user_id)
        self._send_json(HTTPStatus.CREATED, {"user": user_public(created)})

    def _set_user_role(self, target_id: int) -> None:
        actor = self._current_user()
        self._require_role(actor, (roles.ROLE_ADMIN, roles.ROLE_DEPUTY),
                           "Chỉ Admin/Phó Admin mới đổi được vai trò.")
        body = self._read_json()
        role = body.get("role")
        if role not in roles.ALL_ROLES:
            raise ApiError(HTTPStatus.BAD_REQUEST,
                           f"Vai trò không hợp lệ: {role}")
        if not roles.can_grant(actor["role"], role):
            raise ApiError(HTTPStatus.FORBIDDEN,
                           "Bạn không được cấp vai trò này.")
        target = self.app.store.get_user(target_id)
        if target is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "Không tìm thấy người dùng.")
        if target_id == actor["telegram_id"] and role != roles.ROLE_ADMIN:
            raise ApiError(HTTPStatus.FORBIDDEN,
                           "Không thể tự hạ vai trò của chính mình.")
        if "can_publish" in body:
            can_publish = bool(body.get("can_publish"))
        else:
            can_publish = role == roles.ROLE_ADMIN or bool(target["can_publish"])
        self.app.store.set_role(target_id, role, can_publish=can_publish)
        self.app.store.audit(
            actor["telegram_id"], "grant_role", "user", target_id,
            detail=f"role={role} via=webapp")
        updated = self.app.webdb.get_user(target_id)
        self._send_json(HTTPStatus.OK, {"user": user_public(updated)})

    def _revoke_user(self, target_id: int) -> None:
        actor = self._current_user()
        self._require_role(actor, (roles.ROLE_ADMIN, roles.ROLE_DEPUTY),
                           "Chỉ Admin/Phó Admin mới thu hồi được quyền.")
        target = self.app.store.get_user(target_id)
        if target is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "Không tìm thấy người dùng.")
        if target_id == actor["telegram_id"]:
            raise ApiError(HTTPStatus.FORBIDDEN,
                           "Không thể tự thu hồi quyền của chính mình.")
        if not roles.can_revoke(actor["role"], target["role"]):
            raise ApiError(HTTPStatus.FORBIDDEN,
                           "Bạn không được thu hồi quyền của người này.")
        self.app.store.revoke_role(target_id)
        self.app.webdb.delete_user_sessions(target_id)
        self.app.store.audit(
            actor["telegram_id"], "revoke_role", "user", target_id,
            detail="via=webapp")
        updated = self.app.webdb.get_user(target_id)
        self._send_json(HTTPStatus.OK, {"user": user_public(updated)})


# ------------------------------------------------- GĐ3: daily summary
def daily_summary_data(store, now=None) -> dict:
    """Today's numbers (Vietnam time), shared by the API endpoint,
    the overview card and the 20:00 digest. "Đã đăng hôm nay" counts
    outputs whose publish moment is today; "chờ duyệt / chờ đăng"
    are current totals, exactly like the bot's daily summary."""
    now = now or datetime.now(ICT)
    data = stats.collect_stats(store, "today", now)
    by_status: dict = {}
    for per_channel in data["output_channel_status"].values():
        for status, count in per_channel.items():
            by_status[status] = by_status.get(status, 0) + count
    current = {}
    for _channel, status, count in store.count_outputs_by_status():
        current[status] = current.get(status, 0) + count
    return {
        "date": now.strftime("%Y-%m-%d"),
        "label": data["label"],
        "tasks_created": len(data["tasks"]),
        "outputs_total": len(data["outputs"]),
        "outputs_by_status": by_status,
        "published_today": len(data["published"]),
        "pending_review": current.get(storage.STATUS_PENDING, 0),
        "approved_waiting": current.get(
            storage.STATUS_APPROVED_WAITING, 0),
    }


def daily_summary_lines(data: dict, now: datetime):
    """Title + body lines mirroring the bot's 20:00 Telegram digest."""
    title = f"🌆 Tổng kết ngày {now.strftime('%d/%m/%Y')}"
    lines = [
        f"🗂 Việc tạo hôm nay: {data['tasks_created']}",
        f"🚀 Đầu ra đã đăng hôm nay: {data['published_today']}",
        f"⏳ Đang chờ duyệt: {data['pending_review']} đầu ra",
        f"🕐 Đang chờ đăng: {data['approved_waiting']} đầu ra",
    ]
    return title, lines


#: web_meta key holding the date of the last in-app daily summary.
DAILY_SUMMARY_META_KEY = "web_daily_summary_date"


def maybe_send_daily_summary(app: App, now=None) -> bool:
    """The 20:00 digest, web-app edition: once a day, at/after
    20:00 Vietnam time, push the summary to subscribed Admins and
    add it to every user's in-app inbox. The sent date is persisted
    in web_meta so restarts never re-send. Returns True when sent."""
    now = now or datetime.now(ICT)
    if now.hour < 20:
        return False
    today = now.strftime("%Y-%m-%d")
    if app.webdb.get_meta(DAILY_SUMMARY_META_KEY) == today:
        return False
    data = daily_summary_data(app.store, now)
    title, lines = daily_summary_lines(data, now)
    app.webdb.add_notification_item(
        key=f"daily-summary:{today}", kind="daily_summary",
        title=title, body="\n".join(lines),
        created_at=now.astimezone(timezone.utc).isoformat(
            timespec="seconds"))
    if app.push is not None:
        try:
            admin_ids = [u["telegram_id"]
                         for u in app.store.list_users()
                         if u["role"] == roles.ROLE_ADMIN]
            app.push.notify_users(admin_ids, title, " · ".join(lines),
                                  "/")
        except Exception:  # push is best-effort; the inbox item stays
            pass
    app.webdb.set_meta(DAILY_SUMMARY_META_KEY, today)
    return True


def _daily_summary_loop(app: App, interval: int = 60) -> None:
    while True:
        try:
            maybe_send_daily_summary(app)
        except Exception as err:  # the loop must survive anything
            print(f"daily summary check failed: {err}")
        time.sleep(interval)


def make_server(host: str, port: int, app: App) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), Handler)
    server.app = app  # type: ignore[attr-defined]
    server.daemon_threads = True
    return server


def main() -> None:
    host = os.environ.get("WEBAPP_HOST", "0.0.0.0")
    port = int(os.environ.get("WEBAPP_PORT", "8790"))
    app = App()
    server = make_server(host, port, app)
    threading.Thread(target=_daily_summary_loop, args=(app,),
                     daemon=True, name="webapp-daily-summary").start()
    print(f"Web App Giao Việc v{VERSION} — http://{host}:{port} "
          f"(db: {app.db_path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        app.close()


if __name__ == "__main__":
    main()
