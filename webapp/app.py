"""Web App Giao Việc — HTTP API server (Giai đoạn 1).

Pure Python stdlib (``http.server.ThreadingHTTPServer``). All business
rules come from the bot project: ``storage.Store`` for data,
``roles`` for the 5-role permission matrix, ``stats`` for reporting.
Every endpoint re-checks permissions server-side against the session
user's role; nothing the client sends about roles is trusted.

Run:  python3 -m webapp.app     (port: $WEBAPP_PORT, default 8790)
"""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import VERSION
from .auth import hash_password, new_session_token, verify_password
from .db import WebDB, default_db_path, import_bot_modules

storage, roles, stats = import_bot_modules()

STATIC_DIR = Path(__file__).resolve().parent / "static"
SESSION_COOKIE = "webapp_session"
SESSION_TTL_DAYS = int(os.environ.get("WEBAPP_SESSION_TTL_DAYS", "7"))
MIN_PASSWORD_LENGTH = 8

#: Roles allowed to create tasks (mirrors handlers.CREATOR_ROLES of the
#: bot: every granted role; pending users with role NULL cannot).
CREATOR_ROLES = roles.ALL_ROLES


def user_public(row) -> dict:
    """API view of a user row — never includes password_hash."""
    return {
        "id": row["telegram_id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "email": row["email"] if "email" in row.keys() else None,
        "phone": row["phone"] if "phone" in row.keys() else None,
        "role": row["role"],
        "role_title": roles.role_title(row["role"]),
        "can_publish": roles.can_publish(row),
        "can_review": roles.can_review(row["role"]),
        "created_at": row["created_at"],
    }


def _json_list(raw):
    try:
        value = json.loads(raw) if raw else []
    except (ValueError, TypeError):
        return []
    return value if isinstance(value, list) else []


def task_public(row) -> dict:
    return {
        "id": row["id"],
        "code": row["code"],
        "creator_id": row["creator_id"],
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
        "status": row["status"],
        "draft_ref": row["draft_ref"],
        "public_url": row["public_url"],
        "reject_reason": row["reject_reason"],
        "scheduled_at": row["scheduled_at"],
        "publish_target": row["publish_target"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


class App:
    """Holds the shared store + web db; one instance per server."""

    def __init__(self, db_path=None):
        self.db_path = str(db_path or default_db_path())
        self.webdb = WebDB(self.db_path)
        self.store = storage.Store(self.db_path)

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

    # ------------------------------------------------------------- routes
    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        try:
            if method == "GET" and path == "/":
                return self._serve_index()
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
            if method == "GET" and path == "/api/tasks":
                return self._list_tasks(query)
            if method == "POST" and path == "/api/tasks":
                return self._create_task()
            if method == "GET" and path.startswith("/api/tasks/"):
                return self._task_detail(path[len("/api/tasks/"):])
            if method == "GET" and path == "/api/stats/summary":
                return self._stats_summary(query)
            if method == "GET" and path == "/api/users":
                return self._list_users()
            if method == "POST" and path == "/api/users":
                return self._create_user()
            raise ApiError(HTTPStatus.NOT_FOUND, "Không tìm thấy đường dẫn.")
        except ApiError as err:
            self._send_json(err.status, {"error": err.message})
        except BrokenPipeError:
            pass
        except Exception as err:  # never leak a stack trace to clients
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR,
                            {"error": f"Lỗi máy chủ: {err}"})

    def _serve_index(self) -> None:
        page = STATIC_DIR / "index.html"
        body = page.read_bytes() if page.exists() else (
            b"<!doctype html><title>Web App Giao Viec</title>"
            b"<p>Trang kiem chung chua duoc tao.</p>")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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

    # -------------------------------------------------------------- tasks
    def _list_tasks(self, query: dict) -> None:
        user = self._current_user()
        self._require_role(user, CREATOR_ROLES,
                           "Tài khoản chưa được cấp quyền.")
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
        self._require_role(user, CREATOR_ROLES,
                           "Tài khoản chưa được cấp quyền.")
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
        self._send_json(HTTPStatus.OK, {
            "task": task_public(task),
            "outputs": [output_public(o) for o in outputs],
            "audit": audit,
        })

    def _create_task(self) -> None:
        user = self._current_user()
        self._require_role(
            user, CREATOR_ROLES,
            "Tài khoản chưa được cấp quyền tạo việc.")
        body = self._read_json()
        hint = str(body.get("hint") or "").strip()
        destinations = body.get("destinations")
        if destinations is None:
            destinations = list(storage.DEFAULT_DESTINATIONS)
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
        # Mirror the bot exactly: audit + one output per channel.
        self.app.store.audit(
            user["telegram_id"], "create_task", "task", task["code"],
            detail=f"role={user['role']} files=0 via=webapp")
        outputs = self.app.store.sync_outputs_for_task(task)
        task = self.app.store.get_task(task["code"])
        self._send_json(HTTPStatus.CREATED, {
            "task": task_public(task),
            "outputs": [output_public(o) for o in outputs],
        })

    # -------------------------------------------------------------- stats
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
