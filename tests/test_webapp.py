"""Tests for the Web App Giao Việc (Giai đoạn 1).

Everything runs against a COPY of the bot's real database (or a fresh
sample database if the bot DB is absent) inside a temp directory —
the production bot.db is never touched by tests.
"""

from __future__ import annotations

import http.client
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import quote

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from webapp import admin_cli  # noqa: E402
from webapp import push as push_mod  # noqa: E402
from webapp.app import (  # noqa: E402
    ICT, App, daily_summary_data, make_server, maybe_send_daily_summary,
)
from webapp.auth import hash_password, verify_password  # noqa: E402
from webapp.db import SYNTHETIC_ID_BASE, WebDB, bot_dir, import_bot_modules  # noqa: E402

storage, roles, stats = import_bot_modules()

PASSWORDS = {
    "admin": "admin-pass-1",
    "deputy": "deputy-pass-1",
    "editor": "editor-pass-1",
    "writer": "writer-pass-1",
    "contributor": "contrib-pass-1",
    "pending": "pending-pass-1",
}
EMAILS = {key: f"{key}@test.vn" for key in PASSWORDS}
ROLE_OF = {
    "admin": roles.ROLE_ADMIN,
    "deputy": roles.ROLE_DEPUTY,
    "editor": roles.ROLE_EDITOR,
    "writer": roles.ROLE_WRITER,
    "contributor": roles.ROLE_CONTRIBUTOR,
    "pending": None,
}


class FakePushServer:
    """A local HTTP endpoint standing in for a real push service:
    captures every POST (headers + raw body) and answers with a
    configurable status code."""

    def __init__(self, status=201):
        import http.server

        self.status = status
        self.requests = []
        outer = self

        class _Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                outer.requests.append({
                    "path": self.path,
                    "headers": dict(self.headers),
                    "body": body,
                })
                self.send_response(outer.status)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *args):
                pass

        self._server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), _Handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        daemon=True)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}"

    def endpoint(self, name="push"):
        return f"{self.url}/{name}"

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._server.shutdown()
        self._server.server_close()


def _raw_counts(db_path):
    conn = sqlite3.connect(str(db_path))
    try:
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        seq_row = conn.execute(
            "SELECT value FROM bot_meta WHERE key = 'task_seq'").fetchone()
        columns = [r[1] for r in conn.execute("PRAGMA table_info(users)")]
        return users, tasks, (int(seq_row[0]) if seq_row else 0), columns
    finally:
        conn.close()


class WebAppTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="webapp-test-")
        cls.db_path = Path(cls.tmp) / "bot.db"
        real_db = bot_dir() / "data" / "bot.db"
        if real_db.exists():
            shutil.copy(real_db, cls.db_path)
        else:  # pragma: no cover - fallback sample data
            seed = storage.Store(cls.db_path)
            seed.register_user(1, "admin", "Admin Mẫu", 1)
            seed.set_role(1, roles.ROLE_ADMIN, can_publish=True)
            task = seed.create_task(1, roles.ROLE_ADMIN,
                                    "Việc mẫu một", [], None)
            seed.sync_outputs_for_task(task)
            seed.create_task(1, roles.ROLE_ADMIN, "Việc mẫu hai", [], None)
            seed.close()

        cls.pre_users, cls.pre_tasks, cls.pre_seq, pre_columns = \
            _raw_counts(cls.db_path)
        cls.had_email_column = "email" in pre_columns

        # Migration runs (twice — idempotency is asserted in tests).
        cls.webdb = WebDB(cls.db_path)
        cls.webdb.migrate()
        cls.store = storage.Store(cls.db_path)

        # Seed one web account per role.
        cls.user_ids = {}
        for key, password in PASSWORDS.items():
            user_id = cls.webdb.create_web_user(
                display_name=f"Test {key}", email=EMAILS[key], phone=None,
                password_hash=hash_password(password))
            role = ROLE_OF[key]
            if role is not None:
                cls.store.set_role(user_id, role,
                                   can_publish=(role == roles.ROLE_ADMIN))
            cls.user_ids[key] = user_id

        # A known task created through the store for detail/filter tests.
        known = cls.store.create_task(
            cls.user_ids["writer"], roles.ROLE_WRITER,
            "Hội thảo nông nghiệp thông minh xã Chân Mộng", [],
            ["website", "facebook"])
        cls.store.sync_outputs_for_task(known)
        cls.known_code = known["code"]

        cls.files_dir = Path(cls.tmp) / "files"
        cls.app = App(cls.db_path, files_dir=cls.files_dir)
        cls.server = make_server("127.0.0.1", 0, cls.app)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.app.close()
        cls.store.close()
        cls.webdb.close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # ------------------------------------------------------------ helpers
    def req(self, method, path, body=None, token=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = json.dumps(body) if body is not None else None
        all_headers = {"Content-Type": "application/json"}
        if token:
            all_headers["Authorization"] = f"Bearer {token}"
        all_headers.update(headers or {})
        conn.request(method, path, body=payload, headers=all_headers)
        response = conn.getresponse()
        raw = response.read()
        conn.close()
        try:
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            data = {"_raw": raw.decode("utf-8", "replace")}
        return response.status, data, dict(response.getheaders())

    def login(self, key):
        status, data, _headers = self.req(
            "POST", "/api/auth/login",
            {"login": EMAILS[key], "password": PASSWORDS[key]})
        self.assertEqual(status, 200, data)
        return data["token"]

    def req_bytes(self, method, path, body=None, token=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        all_headers = dict(headers or {})
        if token:
            all_headers["Authorization"] = f"Bearer {token}"
        conn.request(method, path, body=body, headers=all_headers)
        response = conn.getresponse()
        raw = response.read()
        result_headers = dict(response.getheaders())
        conn.close()
        return response.status, raw, result_headers

    @staticmethod
    def multipart(fields, files):
        """fields: [(name, value)]; files: [(field, filename, bytes)]."""
        import uuid

        boundary = "----webapp-test-" + uuid.uuid4().hex
        chunks = []
        for name, value in fields:
            chunks.append(f"--{boundary}\r\n".encode())
            chunks.append(
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                .encode())
            chunks.append(str(value).encode("utf-8") + b"\r\n")
        for field, filename, content in files:
            chunks.append(f"--{boundary}\r\n".encode())
            chunks.append(
                (f'Content-Disposition: form-data; name="{field}"; '
                 f'filename="{filename}"\r\n').encode())
            chunks.append(b"Content-Type: application/octet-stream\r\n\r\n")
            chunks.append(content + b"\r\n")
        chunks.append(f"--{boundary}--\r\n".encode())
        return b"".join(chunks), f"multipart/form-data; boundary={boundary}"

    def make_output(self, creator_key="writer", channel="website",
                    draft=True, status=None, hint="Việc kiểm thử GĐ2"):
        creator_id = self.user_ids[creator_key]
        role = ROLE_OF[creator_key]
        task = self.store.create_task(
            creator_id, role, hint, [], [channel])
        self.store.sync_outputs_for_task(task)
        output = self.store.get_output_by_channel(task["code"], channel)
        if draft:
            if channel.startswith("video"):
                self.store.set_output_draft(
                    output["id"], f"https://example.test/{task['code']}.mp4")
            else:
                self.store.set_output_draft(
                    output["id"], f"https://telegra.ph/{task['code']}")
        if status:
            self.store.set_output_status(output["id"], status)
        return self.store.get_task(task["code"]), \
            self.store.get_output(output["id"])

    def audits_for(self, action, output_id):
        return [e for e in self.store.audit_entries(action)
                if e["target_id"] == str(output_id)]

    def action(self, token, output_id, name, body=None):
        return self.req("POST", f"/api/outputs/{output_id}/{name}",
                        body=body or {}, token=token)

    # ------------------------------------------------------------ tests
    def test_health(self):
        status, data, _ = self.req("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertIn("version", data)

    def test_index_page_is_served(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", "/")
        response = conn.getresponse()
        html = response.read().decode("utf-8")
        conn.close()
        self.assertEqual(response.status, 200)
        self.assertIn("Giao Việc IAICT", html)
        self.assertIn("/app.js", html)
        self.assertIn("/manifest.webmanifest", html)
        self.assertNotIn("Trang kiểm chứng", html)

    def test_migration_idempotent_and_preserves_data(self):
        users, tasks, _seq, columns = _raw_counts(self.db_path)
        for column in ("email", "phone", "password_hash"):
            self.assertIn(column, columns)
        conn = sqlite3.connect(str(self.db_path))
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        conn.close()
        self.assertIn("web_sessions", tables)
        # Other tests may have added tasks/users since the pre-migration
        # snapshot; what migration must guarantee is that nothing that
        # existed before it disappeared.
        self.assertGreaterEqual(tasks, self.pre_tasks)
        self.assertGreaterEqual(users, self.pre_users)
        # Running migration again changes nothing at all.
        self.webdb.migrate()
        users2, tasks2, _s, _c = _raw_counts(self.db_path)
        self.assertEqual((users, tasks), (users2, tasks2))

    def test_password_hashing(self):
        stored = hash_password("mat-khau-bi-mat")
        self.assertTrue(stored.startswith("pbkdf2_sha256$"))
        self.assertNotIn("mat-khau-bi-mat", stored)
        self.assertTrue(verify_password("mat-khau-bi-mat", stored))
        self.assertFalse(verify_password("sai-mat-khau", stored))
        row = self.webdb.get_user(self.user_ids["admin"])
        self.assertNotIn(PASSWORDS["admin"], row["password_hash"])

    def test_login_success_and_me(self):
        token = self.login("admin")
        status, data, _ = self.req("GET", "/api/auth/me", token=token)
        self.assertEqual(status, 200)
        self.assertEqual(data["user"]["role"], roles.ROLE_ADMIN)
        self.assertEqual(data["user"]["email"], EMAILS["admin"])
        self.assertNotIn("password_hash", data["user"])
        self.assertTrue(data["user"]["can_publish"])

    def test_login_wrong_password_and_unknown_user(self):
        status, _d, _h = self.req(
            "POST", "/api/auth/login",
            {"login": EMAILS["admin"], "password": "sai-mat-khau"})
        self.assertEqual(status, 401)
        status, _d, _h = self.req(
            "POST", "/api/auth/login",
            {"login": "khong-ton-tai@test.vn", "password": "bat-ky-123"})
        self.assertEqual(status, 401)

    def test_login_by_phone(self):
        conn_id = self.webdb.create_web_user(
            display_name="Phone User", email=None, phone="0909000111",
            password_hash=hash_password("phone-pass-1"))
        self.store.set_role(conn_id, roles.ROLE_WRITER)
        status, data, _ = self.req(
            "POST", "/api/auth/login",
            {"login": "0909000111", "password": "phone-pass-1"})
        self.assertEqual(status, 200, data)
        self.assertEqual(data["user"]["phone"], "0909000111")

    def test_session_required_invalid_and_expired(self):
        status, _d, _h = self.req("GET", "/api/auth/me")
        self.assertEqual(status, 401)
        status, _d, _h = self.req("GET", "/api/auth/me", token="token-gia")
        self.assertEqual(status, 401)
        # Expired session inserted directly.
        import hashlib
        from datetime import datetime, timedelta, timezone
        raw = "expired-token"
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT INTO web_sessions (token_hash, user_id, created_at,"
            " expires_at) VALUES (?, ?, ?, ?)",
            (hashlib.sha256(raw.encode()).hexdigest(),
             self.user_ids["admin"],
             (datetime.now(timezone.utc) - timedelta(days=9)).isoformat(
                 timespec="seconds"),
             (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(
                 timespec="seconds")))
        conn.commit()
        conn.close()
        status, _d, _h = self.req("GET", "/api/auth/me", token=raw)
        self.assertEqual(status, 401)

    def test_logout_invalidates_session(self):
        token = self.login("writer")
        status, _d, _h = self.req("POST", "/api/auth/logout", token=token)
        self.assertEqual(status, 200)
        status, _d, _h = self.req("GET", "/api/auth/me", token=token)
        self.assertEqual(status, 401)

    def test_role_matrix_on_admin_endpoints(self):
        contributor = self.login("contributor")
        editor = self.login("editor")
        writer = self.login("writer")
        for token in (contributor, editor, writer):
            status, _d, _h = self.req("GET", "/api/users", token=token)
            self.assertEqual(status, 403)
            status, _d, _h = self.req(
                "POST", "/api/users", token=token,
                body={"name": "X", "email": "x@test.vn",
                      "password": "tam-thoi-123", "role": "writer"})
            self.assertEqual(status, 403)
        # Stats require a reviewer role.
        for token in (contributor, writer):
            status, _d, _h = self.req("GET", "/api/stats/summary",
                                      token=token)
            self.assertEqual(status, 403)
        admin = self.login("admin")
        status, data, _ = self.req("GET", "/api/users", token=admin)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(data["items"]), len(PASSWORDS))

    def test_grant_rules_for_user_creation(self):
        deputy = self.login("deputy")
        # Deputy may create writer/contributor only (roles.can_grant).
        status, data, _ = self.req(
            "POST", "/api/users", token=deputy,
            body={"name": "NV Mới", "email": "nvmoi@test.vn",
                  "password": "tam-thoi-123", "role": "writer"})
        self.assertEqual(status, 201, data)
        self.assertGreaterEqual(data["user"]["id"], SYNTHETIC_ID_BASE)
        status, _d, _h = self.req(
            "POST", "/api/users", token=deputy,
            body={"name": "BTV Mới", "email": "btvmoi@test.vn",
                  "password": "tam-thoi-123", "role": "editor"})
        self.assertEqual(status, 403)
        # Admin may create an editor; duplicate email is a conflict.
        admin = self.login("admin")
        status, _d, _h = self.req(
            "POST", "/api/users", token=admin,
            body={"name": "Trùng", "email": "nvmoi@test.vn",
                  "password": "tam-thoi-123", "role": "writer"})
        self.assertEqual(status, 409)
        # The deputy-created writer can actually log in.
        status, data, _ = self.req(
            "POST", "/api/auth/login",
            {"login": "nvmoi@test.vn", "password": "tam-thoi-123"})
        self.assertEqual(status, 200, data)
        self.assertEqual(data["user"]["role"], roles.ROLE_WRITER)

    def test_pending_user_cannot_create_task(self):
        pending = self.login("pending")
        status, _d, _h = self.req("POST", "/api/tasks", token=pending,
                                  body={"hint": "việc của pending"})
        self.assertEqual(status, 403)
        status, _d, _h = self.req("GET", "/api/tasks", token=pending)
        self.assertEqual(status, 403)

    def test_create_task_via_api_sequence_audit_outputs(self):
        _u, _t, seq_before, _c = _raw_counts(self.db_path)
        contributor = self.login("contributor")
        status, data, _ = self.req(
            "POST", "/api/tasks", token=contributor,
            body={"hint": "Ảnh hội thảo Chân Mộng",
                  "destinations": ["website", "facebook", "instagram"]})
        self.assertEqual(status, 201, data)
        expected_code = f"CV-{seq_before + 1:04d}"
        self.assertEqual(data["task"]["code"], expected_code)
        self.assertEqual(data["task"]["creator_id"],
                         self.user_ids["contributor"])
        self.assertEqual(
            sorted(o["channel"] for o in data["outputs"]),
            ["facebook", "instagram", "website"])
        entries = [e for e in self.store.audit_entries("create_task")
                   if e["target_id"] == expected_code]
        self.assertTrue(entries)
        self.assertEqual(entries[-1]["actor_id"],
                         self.user_ids["contributor"])

    def test_task_list_filters_and_pagination(self):
        admin = self.login("admin")
        status, data, _ = self.req(
            "GET", "/api/tasks?q=" + quote("Chân Mộng"), token=admin)
        self.assertEqual(status, 200)
        codes = [item["code"] for item in data["items"]]
        self.assertIn(self.known_code, codes)
        status, data, _ = self.req(
            "GET", "/api/tasks?channel=facebook", token=admin)
        self.assertIn(self.known_code,
                      [item["code"] for item in data["items"]])
        status, data, _ = self.req(
            "GET", "/api/tasks?channel=video_vertical", token=admin)
        self.assertNotIn(self.known_code,
                         [item["code"] for item in data["items"]])
        status, data, _ = self.req(
            "GET", f"/api/tasks?creator={self.user_ids['writer']}",
            token=admin)
        self.assertTrue(all(
            item["creator_id"] == self.user_ids["writer"]
            for item in data["items"]))
        self.assertGreaterEqual(data["total"], 1)
        status, page, _ = self.req("GET", "/api/tasks?limit=1&offset=0",
                                   token=admin)
        self.assertEqual(len(page["items"]), 1)
        self.assertGreaterEqual(page["total"], 2)
        status, _d, _h = self.req("GET", "/api/tasks?status=KHONG-CO",
                                  token=admin)
        self.assertEqual(status, 400)

    def test_task_detail_and_404(self):
        admin = self.login("admin")
        status, data, _ = self.req("GET", f"/api/tasks/{self.known_code}",
                                   token=admin)
        self.assertEqual(status, 200)
        self.assertEqual(data["task"]["code"], self.known_code)
        self.assertEqual(
            sorted(o["channel"] for o in data["outputs"]),
            ["facebook", "website"])
        self.assertIn("audit", data)
        status, _d, _h = self.req("GET", "/api/tasks/CV-9999", token=admin)
        self.assertEqual(status, 404)

    def test_stats_summary_matches_store(self):
        admin = self.login("admin")
        status, data, _ = self.req(
            "GET", "/api/stats/summary?period=all", token=admin)
        self.assertEqual(status, 200, data)
        self.assertEqual(data["task_status_counts"],
                         self.store.count_tasks_by_status())
        self.assertEqual(data["tasks_total"],
                         sum(data["task_status_counts"].values()))
        channel_status = {}
        for channel, status_name, n in self.store.count_outputs_by_status():
            channel_status.setdefault(channel, {})[status_name] = n
        # Period "all" covers every output ever created.
        self.assertEqual(data["output_channel_status"], channel_status)
        status, _d, _h = self.req(
            "GET", "/api/stats/summary?period=khong-co", token=admin)
        self.assertEqual(status, 400)

    def test_synthetic_ids_work_with_bot_store(self):
        for key, user_id in self.user_ids.items():
            self.assertGreaterEqual(user_id, SYNTHETIC_ID_BASE, key)
            row = self.store.get_user(user_id)
            self.assertIsNotNone(row)
            self.assertEqual(row["role"], ROLE_OF[key])

    # ------------------------------------------------ GĐ2: static / PWA
    def test_pwa_assets_are_served(self):
        admin = self.login("admin")
        status, raw, headers = self.req_bytes("GET", "/app.js", token=admin)
        self.assertEqual(status, 200)
        self.assertIn(b"serviceWorker", raw)
        self.assertIn(b"/api/review-queue", raw)
        status, raw, _ = self.req_bytes("GET", "/manifest.webmanifest")
        self.assertEqual(status, 200)
        manifest = json.loads(raw.decode("utf-8"))
        self.assertEqual(manifest["name"], "Giao Việc IAICT")
        self.assertEqual(manifest["display"], "standalone")
        status, raw, _ = self.req_bytes("GET", "/sw.js")
        self.assertEqual(status, 200)
        self.assertIn(b"giao-viec-iaict", raw)
        status, raw, headers = self.req_bytes("GET", "/icon-192.png")
        self.assertEqual(status, 200)
        self.assertTrue(raw.startswith(b"\x89PNG"))

    # ------------------------------------------------ GĐ2: uploads/files
    def test_upload_create_task_files_download_and_range(self):
        admin = self.login("admin")
        png = b"\x89PNG\r\n\x1a\n" + b"webapp-image-bytes" * 8
        body, content_type = self.multipart(
            [("hint", "Việc upload từ Web App"),
             ("destinations", "website"), ("destinations", "facebook")],
            [("files", "anh-mau.png", png)])
        status, raw, _ = self.req_bytes(
            "POST", "/api/tasks", body=body, token=admin,
            headers={"Content-Type": content_type})
        self.assertEqual(status, 201, raw)
        data = json.loads(raw.decode("utf-8"))
        code = data["task"]["code"]
        self.assertEqual(data["task"]["file_ids"], ["anh-mau.png"])
        saved = self.files_dir / code / "anh-mau.png"
        self.assertTrue(saved.exists())
        self.assertEqual(saved.read_bytes(), png)
        self.assertTrue(self.audits_for("create_task", code) or
                        [e for e in self.store.audit_entries("create_task")
                         if e["target_id"] == code])
        self.assertTrue(
            [e for e in self.store.audit_entries("destinations_confirmed")
             if e["target_id"] == code])

        status, detail, _ = self.req("GET", f"/api/tasks/{code}",
                                     token=admin)
        self.assertEqual(status, 200)
        self.assertEqual([f["name"] for f in detail["files"]],
                         ["anh-mau.png"])
        status, raw, headers = self.req_bytes(
            "GET", f"/api/files/{code}/anh-mau.png", token=admin)
        self.assertEqual(status, 200)
        self.assertEqual(raw, png)
        status, raw, headers = self.req_bytes(
            "GET", f"/api/files/{code}/anh-mau.png", token=admin,
            headers={"Range": "bytes=0-7"})
        self.assertEqual(status, 206)
        self.assertEqual(raw, png[:8])
        self.assertEqual(headers.get("Content-Range"),
                         f"bytes 0-7/{len(png)}")

        # /api/uploads appends a second material file to the same task.
        body, content_type = self.multipart(
            [("task_code", code)],
            [("files", "ghi-chu.txt", b"noi dung ghi chu")])
        status, raw, _ = self.req_bytes(
            "POST", "/api/uploads", body=body, token=admin,
            headers={"Content-Type": content_type})
        self.assertEqual(status, 201, raw)
        self.assertTrue((self.files_dir / code / "ghi-chu.txt").exists())
        # A non-creator, non-admin may not add materials.
        writer = self.login("writer")
        body, content_type = self.multipart(
            [("task_code", code)], [("files", "x.txt", b"x")])
        status, _raw, _ = self.req_bytes(
            "POST", "/api/uploads", body=body, token=writer,
            headers={"Content-Type": content_type})
        self.assertEqual(status, 403)

    def test_upload_rejects_file_over_limit(self):
        # Exercise the validator directly with a fake part descriptor:
        # building a real 200MB body in the suite would be wasteful.
        from webapp.app import Handler

        class FakeHandler(Handler):
            def __init__(self):  # no socket setup needed
                pass

        handler = FakeHandler()
        with self.assertRaises(Exception) as ctx:
            handler._validate_parts(
                [{"filename": "to.mp4", "size": 201 * 1024 * 1024}])
        self.assertEqual(ctx.exception.status, 413)

    # ---------------------------------------------- GĐ2: output actions
    def test_submit_approve_and_permission_audits(self):
        writer = self.login("writer")
        editor = self.login("editor")
        _task, output = self.make_output("writer", "website")
        status, data, _ = self.action(writer, output["id"], "submit")
        self.assertEqual(status, 200, data)
        self.assertEqual(self.store.get_output(output["id"])["status"],
                         "PENDING")
        self.assertTrue(self.audits_for("submit_output", output["id"]))
        # Writer may not approve — and the denial itself is audited.
        status, _d, _ = self.action(writer, output["id"], "approve")
        self.assertEqual(status, 403)
        self.assertTrue(self.audits_for(
            "denied_output_approve_attempt", output["id"]))
        status, data, _ = self.action(editor, output["id"], "approve")
        self.assertEqual(status, 200, data)
        self.assertEqual(self.store.get_output(output["id"])["status"],
                         "APPROVED_WAITING")
        self.assertTrue(self.audits_for("approve_output", output["id"]))

    def test_submit_without_draft_is_conflict(self):
        writer = self.login("writer")
        _task, output = self.make_output("writer", "website", draft=False)
        status, _d, _ = self.action(writer, output["id"], "submit")
        self.assertEqual(status, 409)

    def test_reject_requires_reason_and_revise_by_creator(self):
        writer = self.login("writer")
        editor = self.login("editor")
        _task, output = self.make_output(
            "writer", "facebook", status="PENDING")
        status, _d, _ = self.action(editor, output["id"], "reject", {})
        self.assertEqual(status, 400)
        status, data, _ = self.action(
            editor, output["id"], "reject", {"reason": "Thiếu ảnh bìa"})
        self.assertEqual(status, 200, data)
        updated = self.store.get_output(output["id"])
        self.assertEqual(updated["status"], "REJECTED")
        self.assertEqual(updated["reject_reason"], "Thiếu ảnh bìa")
        self.assertTrue(self.audits_for("reject_output", output["id"]))
        # Revise belongs to the creator; the editor is not the creator.
        status, _d, _ = self.action(editor, output["id"], "revise",
                                    {"reason": "Sửa lại"})
        self.assertEqual(status, 403)
        status, data, _ = self.action(
            writer, output["id"], "revise", {"reason": "Đổi tiêu đề"})
        self.assertEqual(status, 200, data)
        self.assertTrue(self.audits_for("revise_output", output["id"]))

    def test_cancel_output_reviewer_only(self):
        writer = self.login("writer")
        editor = self.login("editor")
        _task, output = self.make_output("writer", "instagram")
        status, _d, _ = self.action(writer, output["id"], "cancel")
        self.assertEqual(status, 403)
        self.assertTrue(self.audits_for(
            "denied_output_cancel_attempt", output["id"]))
        status, data, _ = self.action(editor, output["id"], "cancel")
        self.assertEqual(status, 200, data)
        self.assertEqual(self.store.get_output(output["id"])["status"],
                         "CANCELLED")
        self.assertTrue(self.audits_for("cancel_output", output["id"]))

    def test_admin_own_publish_auto_approves_but_never_published(self):
        admin = self.login("admin")
        _task, output = self.make_output("admin", "website")
        status, data, _ = self.action(admin, output["id"], "publish")
        self.assertEqual(status, 200, data)
        updated = self.store.get_output(output["id"])
        # The Đăng button only records the order; Muse publishes for
        # real later, so the status must NOT claim PUBLISHED here.
        self.assertEqual(updated["status"], "APPROVED_WAITING")
        self.assertEqual(updated["pending_choice"], 1)
        auto = [e for e in self.audits_for("approve_output", output["id"])
                if "auto=admin_own" in (e["detail"] or "")]
        self.assertTrue(auto)
        self.assertTrue(self.audits_for("publish_requested", output["id"]))

    def test_publish_denied_for_writer_with_audit(self):
        writer = self.login("writer")
        _task, output = self.make_output(
            "writer", "website", status="APPROVED_WAITING")
        status, _d, _ = self.action(writer, output["id"], "publish")
        self.assertEqual(status, 403)
        self.assertTrue(self.audits_for(
            "denied_output_publish_attempt", output["id"]))

    def test_facebook_publish_requires_target_then_abort(self):
        admin = self.login("admin")
        _task, output = self.make_output("admin", "facebook")
        status, data, _ = self.action(admin, output["id"], "publish", {})
        self.assertEqual(status, 422, data)
        self.assertEqual(data["code"], "target_required")
        self.assertEqual(self.store.get_output(output["id"])
                         ["pending_choice"], 1)
        status, data, _ = self.action(admin, output["id"], "publish-abort")
        self.assertEqual(status, 200, data)
        self.assertEqual(self.store.get_output(output["id"])
                         ["pending_choice"], 0)
        self.assertTrue(self.audits_for("publish_aborted", output["id"]))
        # Now publish for real (still only an order), target = page.
        status, data, _ = self.action(
            admin, output["id"], "publish", {"target": "page"})
        self.assertEqual(status, 200, data)
        entries = self.audits_for("publish_requested", output["id"])
        self.assertTrue(any("target=page" in (e["detail"] or "")
                            for e in entries))
        status, _d, _ = self.action(
            admin, output["id"], "publish", {"target": "khac"})
        self.assertIn(status, (400, 409))

    def test_schedule_unschedule_and_close_warning(self):
        admin = self.login("admin")
        from datetime import datetime, timedelta, timezone

        def future(minutes):
            return (datetime.now(timezone.utc)
                    + timedelta(minutes=minutes)).isoformat(
                        timespec="seconds")

        _t1, first = self.make_output("admin", "website")
        status, data, _ = self.action(
            admin, first["id"], "schedule", {"scheduled_at": future(180)})
        self.assertEqual(status, 200, data)
        self.assertEqual(data["warnings"], [])
        self.assertIsNotNone(self.store.get_output(first["id"])
                              ["scheduled_at"])
        self.assertTrue(self.audits_for("schedule_set", first["id"]))
        # Second post on the same channel 30 minutes later must warn.
        _t2, second = self.make_output("admin", "website")
        status, data, _ = self.action(
            admin, second["id"], "schedule", {"scheduled_at": future(210)})
        self.assertEqual(status, 200, data)
        self.assertTrue(data["warnings"])
        # Facebook scheduling needs its target first.
        _t3, fb = self.make_output("admin", "facebook")
        status, data, _ = self.action(
            admin, fb["id"], "schedule", {"preset": "60"})
        self.assertEqual(status, 422, data)
        self.assertEqual(data["code"], "target_required")
        status, data, _ = self.action(
            admin, fb["id"], "schedule",
            {"preset": "60", "target": "profile"})
        self.assertEqual(status, 200, data)
        self.assertEqual(self.store.get_output(fb["id"])["publish_target"],
                         "profile")
        # Scheduled list (reviewer-only) contains the posts.
        status, data, _ = self.req("GET", "/api/scheduled", token=admin)
        self.assertEqual(status, 200)
        ids = [item["id"] for item in data["items"]]
        self.assertIn(first["id"], ids)
        self.assertIn(fb["id"], ids)
        writer = self.login("writer")
        status, _d, _ = self.req("GET", "/api/scheduled", token=writer)
        self.assertEqual(status, 403)
        # Unschedule clears the slot and audits schedule_cancelled.
        status, data, _ = self.action(admin, first["id"], "unschedule")
        self.assertEqual(status, 200, data)
        self.assertIsNone(self.store.get_output(first["id"])
                          ["scheduled_at"])
        self.assertTrue(self.audits_for("schedule_cancelled", first["id"]))

    def test_review_queue_reviewer_only(self):
        writer = self.login("writer")
        editor = self.login("editor")
        _task, output = self.make_output(
            "writer", "website", status="PENDING")
        status, _d, _ = self.req("GET", "/api/review-queue", token=writer)
        self.assertEqual(status, 403)
        status, data, _ = self.req("GET", "/api/review-queue", token=editor)
        self.assertEqual(status, 200)
        self.assertIn(output["id"], [i["id"] for i in data["items"]])

    def test_retract_nonfacebook_and_facebook_request_only(self):
        admin = self.login("admin")
        _task, web = self.make_output("admin", "website", draft=True)
        self.store.set_output_public_url(
            web["id"], "https://example.test/bai-web")
        status, data, _ = self.action(admin, web["id"], "retract")
        self.assertEqual(status, 200, data)
        self.assertEqual(self.store.get_output(web["id"])["status"],
                         "RETRACTED")
        self.assertTrue(self.audits_for("retract_output", web["id"]))

        _task, fb = self.make_output("admin", "facebook", draft=True)
        self.store.set_output_public_url(
            fb["id"], "https://facebook.test/bai-fb")
        status, data, _ = self.action(admin, fb["id"], "retract")
        self.assertEqual(status, 200, data)
        # Facebook retract is only an order here — Muse deletes the
        # real post; the status must stay PUBLISHED until then.
        self.assertEqual(self.store.get_output(fb["id"])["status"],
                         "PUBLISHED")
        self.assertTrue(self.audits_for("retract_requested", fb["id"]))
        status, _d, _ = self.action(admin, fb["id"], "retract")
        self.assertEqual(status, 409)

    # ------------------------------------------- GĐ2: stats / inbox
    def test_stats_export_csv_bom_and_xlsx(self):
        admin = self.login("admin")
        status, raw, headers = self.req_bytes(
            "GET", "/api/stats/export?format=csv&period=all", token=admin)
        self.assertEqual(status, 200)
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))  # UTF-8 BOM
        self.assertIn("Mã việc", raw.decode("utf-8-sig"))
        self.assertIn("attachment", headers.get("Content-Disposition", ""))
        status, raw, headers = self.req_bytes(
            "GET", "/api/stats/export?format=xlsx&period=all", token=admin)
        self.assertEqual(status, 200)
        self.assertTrue(raw.startswith(b"PK"))
        writer = self.login("writer")
        status, _raw, _ = self.req_bytes(
            "GET", "/api/stats/export?format=csv", token=writer)
        self.assertEqual(status, 403)
        status, _d, _ = self.req(
            "GET", "/api/stats/export?format=pdf", token=admin)
        self.assertEqual(status, 400)

    def test_notifications_flow_and_mark_read(self):
        writer = self.login("writer")
        editor = self.login("editor")
        _task, pending = self.make_output(
            "writer", "website", status="PENDING")
        status, data, _ = self.req("GET", "/api/notifications",
                                   token=editor)
        self.assertEqual(status, 200)
        review_items = [i for i in data["items"]
                        if i["kind"] == "review_pending"
                        and i["output_id"] == pending["id"]]
        self.assertTrue(review_items)
        key = review_items[0]["key"]
        self.assertFalse(review_items[0]["read"])
        status, data, _ = self.req(
            "POST", "/api/notifications/read", token=editor,
            body={"keys": [key]})
        self.assertEqual(status, 200)
        status, data, _ = self.req("GET", "/api/notifications",
                                   token=editor)
        again = [i for i in data["items"] if i["key"] == key]
        self.assertTrue(again and again[0]["read"])
        # The creator is notified about a rejection of their output.
        _task, rejected = self.make_output(
            "writer", "instagram", status="PENDING")
        status, _d, _ = self.action(
            editor, rejected["id"], "reject", {"reason": "Cần sửa ảnh"})
        self.assertEqual(status, 200)
        status, data, _ = self.req("GET", "/api/notifications",
                                   token=writer)
        kinds = {(i["output_id"], i["kind"]) for i in data["items"]}
        self.assertIn((rejected["id"], "rejected"), kinds)

    # -------------------------------------- GĐ2: password / user admin
    def test_change_password_flow(self):
        user_id = self.webdb.create_web_user(
            display_name="Đổi Mật Khẩu", email="doimk@test.vn",
            phone=None, password_hash=hash_password("mat-khau-cu-1"))
        self.store.set_role(user_id, roles.ROLE_WRITER)
        status, data, _ = self.req(
            "POST", "/api/auth/login",
            {"login": "doimk@test.vn", "password": "mat-khau-cu-1"})
        self.assertEqual(status, 200, data)
        token1 = data["token"]
        status, data, _ = self.req(
            "POST", "/api/auth/login",
            {"login": "doimk@test.vn", "password": "mat-khau-cu-1"})
        token2 = data["token"]
        status, _d, _ = self.req(
            "POST", "/api/auth/change-password", token=token1,
            body={"old_password": "sai-mat-khau",
                  "new_password": "mat-khau-moi-1"})
        self.assertEqual(status, 401)
        status, data, _ = self.req(
            "POST", "/api/auth/change-password", token=token1,
            body={"old_password": "mat-khau-cu-1",
                  "new_password": "mat-khau-moi-1"})
        self.assertEqual(status, 200, data)
        # Current session survives; the other session is invalidated.
        status, _d, _ = self.req("GET", "/api/auth/me", token=token1)
        self.assertEqual(status, 200)
        status, _d, _ = self.req("GET", "/api/auth/me", token=token2)
        self.assertEqual(status, 401)
        # Old password no longer works, the new one does.
        status, _d, _ = self.req(
            "POST", "/api/auth/login",
            {"login": "doimk@test.vn", "password": "mat-khau-cu-1"})
        self.assertEqual(status, 401)
        status, data, _ = self.req(
            "POST", "/api/auth/login",
            {"login": "doimk@test.vn", "password": "mat-khau-moi-1"})
        self.assertEqual(status, 200, data)

    def test_user_role_patch_and_revoke(self):
        admin = self.login("admin")
        status, data, _ = self.req(
            "POST", "/api/users", token=admin,
            body={"name": "Người Bị Đổi Vai", "email": "doivai@test.vn",
                  "password": "tam-thoi-123", "role": "contributor"})
        self.assertEqual(status, 201, data)
        target = data["user"]["id"]
        status, data, _ = self.req(
            "PATCH", f"/api/users/{target}/role", token=admin,
            body={"role": "writer", "can_publish": False})
        self.assertEqual(status, 200, data)
        self.assertEqual(data["user"]["role"], roles.ROLE_WRITER)
        self.assertTrue([e for e in self.store.audit_entries("grant_role")
                         if e["target_id"] == str(target)])
        # Deputy may not grant a role above their grantable set.
        deputy = self.login("deputy")
        status, _d, _ = self.req(
            "PATCH", f"/api/users/{target}/role", token=deputy,
            body={"role": "editor"})
        self.assertEqual(status, 403)
        status, data, _ = self.req(
            "POST", f"/api/users/{target}/revoke", token=admin, body={})
        self.assertEqual(status, 200, data)
        self.assertIsNone(data["user"]["role"])
        self.assertTrue([e for e in self.store.audit_entries("revoke_role")
                         if e["target_id"] == str(target)])

    def test_draft_video_streaming_with_range(self):
        admin = self.login("admin")
        _task, output = self.make_output("admin", "video_vertical",
                                         draft=False)
        video_dir = self.files_dir / _task["code"] / "video-drafts"
        video_dir.mkdir(parents=True, exist_ok=True)
        video_path = video_dir / "draft.mp4"
        payload = b"\x00\x00\x00\x18ftypmp42" + b"video-bytes" * 16
        video_path.write_bytes(payload)
        self.store.set_output_video(output["id"], str(video_path))
        status, raw, headers = self.req_bytes(
            "GET", f"/api/outputs/{output['id']}/draft-video", token=admin,
            headers={"Range": "bytes=0-11"})
        self.assertEqual(status, 206)
        self.assertEqual(raw, payload[:12])
        status, raw, _ = self.req_bytes(
            "GET", f"/api/outputs/{output['id']}/draft-video", token=admin)
        self.assertEqual(status, 200)
        self.assertEqual(raw, payload)

    def test_admin_cli_creates_loginable_admin(self):
        env = dict(os.environ)
        env["WEBAPP_DB_PATH"] = str(self.db_path)
        env["WEBAPP_ADMIN_PASSWORD"] = "cli-pass-123"
        env["PYTHONPATH"] = str(PROJECT_ROOT)
        result = subprocess.run(
            [sys.executable, "-m", "webapp.admin_cli", "create-admin",
             "--email", "cli@test.vn", "--name", "CLI Admin"],
            cwd=str(PROJECT_ROOT), env=env, capture_output=True, text=True,
            timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("cli-pass-123", result.stdout)
        self.assertNotIn("cli-pass-123", result.stderr)
        status, data, _ = self.req(
            "POST", "/api/auth/login",
            {"login": "cli@test.vn", "password": "cli-pass-123"})
        self.assertEqual(status, 200, data)
        self.assertEqual(data["user"]["role"], roles.ROLE_ADMIN)
        # Duplicate email is refused.
        result = subprocess.run(
            [sys.executable, "-m", "webapp.admin_cli", "create-admin",
             "--email", "cli@test.vn", "--name", "CLI Admin 2"],
            cwd=str(PROJECT_ROOT), env=env, capture_output=True, text=True,
            timeout=60)
        self.assertNotEqual(result.returncode, 0)

    def test_admin_cli_attach_existing_telegram_user(self):
        # The real bot admin row (created by the bot, telegram_id from
        # the copied DB) can gain web credentials without a new row.
        users_before, _t, _s, _c = _raw_counts(self.db_path)
        target = None
        for row in self.store.list_users():
            if row["telegram_id"] < SYNTHETIC_ID_BASE:
                target = row["telegram_id"]
                break
        if target is None:
            self.skipTest("no telegram user in sample db")
        user_id = admin_cli.create_admin(
            email="attach@test.vn", name="Attach", telegram_id=target,
            password="attach-pass-1", db_path=self.db_path)
        self.assertEqual(user_id, target)
        users_after, _t, _s, _c = _raw_counts(self.db_path)
        self.assertEqual(users_before, users_after)
        status, data, _ = self.req(
            "POST", "/api/auth/login",
            {"login": "attach@test.vn", "password": "attach-pass-1"})
        self.assertEqual(status, 200, data)
        self.assertEqual(data["user"]["id"], target)

    # ------------------------------------------------ GĐ3: Web Push
    def _subscribe(self, token, endpoint, recv_point=None, auth=None):
        import os

        if recv_point is None:
            _pem, recv_point = push_mod.generate_ec_keypair()
        if auth is None:
            auth = os.urandom(16)
        status, data, _ = self.req("POST", "/api/push/subscribe", {
            "endpoint": endpoint,
            "keys": {"p256dh": push_mod.b64url_encode(recv_point),
                     "auth": push_mod.b64url_encode(auth)},
        }, token=token)
        return status, data, recv_point, auth

    def test_push_vapid_key_requires_login(self):
        status, _data, _ = self.req("GET", "/api/push/vapid-public-key")
        self.assertEqual(status, 401)
        token = self.login("writer")
        status, data, _ = self.req("GET", "/api/push/vapid-public-key",
                                   token=token)
        self.assertEqual(status, 200, data)
        self.assertEqual(data["public_key"], self.app.push.public_key)
        point = push_mod.b64url_decode(data["public_key"])
        self.assertEqual(len(point), 65)
        self.assertEqual(point[0], 0x04)

    def test_push_subscribe_crud_and_permissions(self):
        writer = self.login("writer")
        editor = self.login("editor")
        pending = self.login("pending")
        endpoint = "https://push.example.test/sub/crud-1"

        # Pending (ungranted) accounts cannot subscribe.
        status, _d, _p, _a = self._subscribe(pending, endpoint)
        self.assertEqual(status, 403)

        # Invalid payloads are rejected.
        status, _data, _ = self.req("POST", "/api/push/subscribe", {
            "endpoint": "ftp://not-a-push-endpoint",
            "keys": {"p256dh": "x", "auth": "y"},
        }, token=writer)
        self.assertEqual(status, 400)
        status, _data, _ = self.req("POST", "/api/push/subscribe", {
            "endpoint": endpoint,
            "keys": {"p256dh": push_mod.b64url_encode(b"\x04" + b"\x01" * 10),
                     "auth": push_mod.b64url_encode(b"\x02" * 16)},
        }, token=writer)
        self.assertEqual(status, 400)

        # Subscribe properly; the row belongs to the writer.
        status, data, _p, _a = self._subscribe(writer, endpoint)
        self.assertEqual(status, 200, data)
        subs = self.webdb.push_subscriptions_for_user(
            self.user_ids["writer"])
        self.assertEqual([s["endpoint"] for s in subs], [endpoint])

        # Upsert: subscribing again refreshes keys, still one row.
        status, _d, _p2, _a2 = self._subscribe(writer, endpoint)
        self.assertEqual(status, 200)
        subs = self.webdb.push_subscriptions_for_user(
            self.user_ids["writer"])
        self.assertEqual(len(subs), 1)

        # Another user cannot remove the writer's subscription.
        status, data, _ = self.req("POST", "/api/push/unsubscribe",
                                   {"endpoint": endpoint}, token=editor)
        self.assertEqual(status, 200, data)
        self.assertEqual(data["removed"], 0)
        self.assertEqual(len(self.webdb.push_subscriptions_for_user(
            self.user_ids["writer"])), 1)

        # The owner can.
        status, data, _ = self.req("POST", "/api/push/unsubscribe",
                                   {"endpoint": endpoint}, token=writer)
        self.assertEqual(data["removed"], 1)
        self.assertEqual(self.webdb.push_subscriptions_for_user(
            self.user_ids["writer"]), [])

    def test_push_test_delivers_encrypted_payload(self):
        fake = FakePushServer(status=201).start()
        try:
            writer = self.login("writer")
            recv_pem, recv_point = push_mod.generate_ec_keypair()
            import os

            auth = os.urandom(16)
            endpoint = fake.endpoint("writer")
            status, _d, _p, _a = self._subscribe(
                writer, endpoint, recv_point=recv_point, auth=auth)
            self.assertEqual(status, 200)

            status, data, _ = self.req("POST", "/api/push/test", {},
                                       token=writer)
            self.assertEqual(status, 200, data)
            self.assertEqual(data["sent"], 1)
            self.assertEqual(len(fake.requests), 1)
            captured = fake.requests[0]

            # VAPID authorization header: t=<JWT>, k=<our public key>,
            # and the JWT verifies against that key.
            header = captured["headers"].get("Authorization", "")
            self.assertTrue(header.startswith("vapid t="), header)
            token_part, _, key_part = header[len("vapid "):].partition(", k=")
            token_part = token_part[len("t="):]
            self.assertEqual(key_part, self.app.push.public_key)
            head_b64, claims_b64, sig_b64 = token_part.split(".")
            claims = json.loads(push_mod.b64url_decode(claims_b64))
            self.assertEqual(claims["aud"], fake.url)
            self.assertEqual(claims["sub"], "mailto:ntdung.lak@gmail.com")
            self.assertGreater(claims["exp"], 0)
            self.assertTrue(push_mod.ec_verify_sha256(
                push_mod.b64url_decode(key_part),
                f"{head_b64}.{claims_b64}".encode(),
                push_mod.b64url_decode(sig_b64)))

            # The body decrypts (receiver side) to the test message.
            self.assertEqual(captured["headers"].get("Content-Encoding"),
                             "aes128gcm")
            plain = push_mod.decrypt_payload(
                captured["body"], recv_pem, recv_point, auth)
            payload = json.loads(plain.decode("utf-8"))
            self.assertEqual(payload["title"], "🔔 Thông báo thử")
            self.assertEqual(payload["url"], "/")
        finally:
            fake.stop()
            self.webdb.delete_push_subscription(fake.endpoint("writer"))

    def test_push_subscription_removed_when_endpoint_gone(self):
        fake = FakePushServer(status=410).start()
        try:
            writer = self.login("writer")
            endpoint = fake.endpoint("gone")
            status, _d, _p, _a = self._subscribe(writer, endpoint)
            self.assertEqual(status, 200)
            status, data, _ = self.req("POST", "/api/push/test", {},
                                       token=writer)
            self.assertEqual(status, 200, data)
            self.assertEqual(data["sent"], 0)
            self.assertEqual(len(data["results"]), 1)
            self.assertEqual(data["results"][0]["status"], 410)
            self.assertTrue(data["results"][0]["gone"])
            # 410 => the subscription is dropped automatically.
            self.assertEqual(self.webdb.push_subscriptions_for_user(
                self.user_ids["writer"]), [])
        finally:
            fake.stop()

    # ------------------------------------------- GĐ3: daily summary
    def test_daily_summary_matches_store(self):
        status, _data, _ = self.req("GET", "/api/stats/daily-summary")
        self.assertEqual(status, 401)
        pending = self.login("pending")
        status, _data, _ = self.req("GET", "/api/stats/daily-summary",
                                    token=pending)
        self.assertEqual(status, 403)

        writer = self.login("writer")
        status, data, _ = self.req("GET", "/api/stats/daily-summary",
                                   token=writer)
        self.assertEqual(status, 200, data)
        expected = daily_summary_data(self.store)
        for field in ("date", "label", "tasks_created", "outputs_total",
                      "published_today", "pending_review",
                      "approved_waiting"):
            self.assertEqual(data[field], expected[field], field)
        self.assertEqual(data["outputs_by_status"],
                         expected["outputs_by_status"])

    def test_daily_summary_item_appears_in_inbox(self):
        self.app.webdb.add_notification_item(
            key="daily-summary:test-day", kind="daily_summary",
            title="🌆 Tổng kết ngày (test)",
            body="🗂 Việc tạo hôm nay: 1")
        writer = self.login("writer")
        status, data, _ = self.req("GET", "/api/notifications",
                                   token=writer)
        self.assertEqual(status, 200, data)
        mine = [i for i in data["items"]
                if i["key"] == "daily-summary:test-day"]
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0]["kind"], "daily_summary")
        self.assertIsNone(mine[0]["task_code"])
        self.assertFalse(mine[0]["read"])
        status, data, _ = self.req(
            "POST", "/api/notifications/read",
            {"keys": ["daily-summary:test-day"]}, token=writer)
        self.assertEqual(status, 200, data)
        status, data, _ = self.req("GET", "/api/notifications",
                                   token=writer)
        mine = [i for i in data["items"]
                if i["key"] == "daily-summary:test-day"]
        self.assertTrue(mine[0]["read"])


class PushCryptoTests(unittest.TestCase):
    """GĐ3 crypto units: AES-128-GCM against reference vectors
    (cross-verified with OpenSSL), ECDH/ECDSA via openssl, and the
    RFC 8291 encrypt→decrypt round-trip."""

    def test_aes128_block_fips197(self):
        keys = push_mod._aes128_expand_key(
            bytes.fromhex("000102030405060708090a0b0c0d0e0f"))
        out = push_mod._aes_encrypt_block(
            keys, bytes.fromhex("00112233445566778899aabbccddeeff"))
        self.assertEqual(out.hex(), "69c4e0d86a7b0430d8cdb78070b4c55a")

    def test_aes128gcm_reference_vectors(self):
        # Key/IV all zero, empty plaintext (tag only).
        out = push_mod.aes128gcm_encrypt(b"\x00" * 16, b"\x00" * 12, b"")
        self.assertEqual(out.hex(), "58e2fccefa7e3061367f1d57a4e7455a")
        # Key/IV all zero, one zero block of plaintext.
        out = push_mod.aes128gcm_encrypt(b"\x00" * 16, b"\x00" * 12,
                                         b"\x00" * 16)
        self.assertEqual(
            out.hex(),
            "0388dace60b6a392f328c2b971b2fe78"
            "ab6e47d42cec13bdf53a67b21257bddf")
        # The classic GCM-spec case with AAD (60-byte plaintext).
        key = bytes.fromhex("feffe9928665731c6d6a8f9467308308")
        iv = bytes.fromhex("cafebabefacedbaddecaf888")
        aad = bytes.fromhex("feedfacedeadbeeffeedfacedeadbeefabaddad2")
        plain = bytes.fromhex(
            "d9313225f88406e5a55909c5aff5269a"
            "86a7a9531534f7da2e4c303d8a318a72"
            "1c3c0c95956809532fcf0e2449a6b525"
            "b16aedf5aa0de657ba637b39")
        out = push_mod.aes128gcm_encrypt(key, iv, plain, aad)
        self.assertEqual(
            out.hex(),
            "42831ec2217774244b7221b784d0d49c"
            "e3aa212f2c02a4e035c17e2329aca12e"
            "21d514b25466931c7d8f6a5aac84aa05"
            "1ba30b396a0aac973d58e091"
            "5bc94fbc3221a5db94fae95ae7121a47")
        self.assertEqual(push_mod.aes128gcm_decrypt(key, iv, out, aad),
                         plain)

    def test_aes128gcm_tamper_is_detected(self):
        key, nonce = os.urandom(16), os.urandom(12)
        blob = bytearray(push_mod.aes128gcm_encrypt(key, nonce,
                                                    b"secret"))
        blob[0] ^= 1
        with self.assertRaises(ValueError):
            push_mod.aes128gcm_decrypt(key, nonce, bytes(blob))

    def test_ecdh_agreement_and_ecdsa_roundtrip(self):
        pem_a, point_a = push_mod.generate_ec_keypair()
        pem_b, point_b = push_mod.generate_ec_keypair()
        self.assertEqual(push_mod.ecdh_derive(pem_a, point_b),
                         push_mod.ecdh_derive(pem_b, point_a))
        sig = push_mod.ec_sign_sha256(pem_a, b"vapid-signing-input")
        self.assertEqual(len(sig), 64)
        self.assertTrue(push_mod.ec_verify_sha256(
            point_a, b"vapid-signing-input", sig))
        self.assertFalse(push_mod.ec_verify_sha256(
            point_a, b"other-input", sig))

    def test_vapid_jwt_claims_and_signature(self):
        pem, point = push_mod.generate_ec_keypair()
        keys = {"private_pem": pem, "public_point": point,
                "public_key": push_mod.b64url_encode(point)}
        token = push_mod.build_vapid_jwt(keys, "https://push.example.test")
        head_b64, claims_b64, sig_b64 = token.split(".")
        header = json.loads(push_mod.b64url_decode(head_b64))
        claims = json.loads(push_mod.b64url_decode(claims_b64))
        self.assertEqual(header, {"typ": "JWT", "alg": "ES256"})
        self.assertEqual(claims["aud"], "https://push.example.test")
        self.assertEqual(claims["sub"], "mailto:ntdung.lak@gmail.com")
        import time

        remaining = claims["exp"] - int(time.time())
        self.assertGreater(remaining, 0)
        self.assertLessEqual(remaining, 24 * 3600)
        self.assertTrue(push_mod.ec_verify_sha256(
            point, f"{head_b64}.{claims_b64}".encode(),
            push_mod.b64url_decode(sig_b64)))

    def test_rfc8291_encrypt_decrypt_roundtrip(self):
        recv_pem, recv_point = push_mod.generate_ec_keypair()
        auth = os.urandom(16)
        payload = json.dumps(
            {"title": "⏳ Thẻ kênh chờ duyệt", "body": "CV-0001 · Website",
             "url": "/?task=CV-0001"}, ensure_ascii=False).encode("utf-8")
        body = push_mod.encrypt_payload(
            push_mod.b64url_encode(recv_point),
            push_mod.b64url_encode(auth), payload)
        # Header: salt(16) || rs(4)=4096 || idlen(1)=65 || sender key.
        self.assertEqual(int.from_bytes(body[16:20], "big"), 4096)
        self.assertEqual(body[20], 65)
        self.assertEqual(body[21], 0x04)
        back = push_mod.decrypt_payload(body, recv_pem, recv_point, auth)
        self.assertEqual(back, payload)
        # A wrong auth secret must fail the GCM tag check.
        with self.assertRaises(ValueError):
            push_mod.decrypt_payload(body, recv_pem, recv_point,
                                     os.urandom(16))


class DailySummaryFreshTests(unittest.TestCase):
    """GĐ3 daily summary against a brand-new database (exact counts)
    plus the 20:00 once-per-day guard."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="webapp-daily-")
        cls.db_path = Path(cls.tmp) / "bot.db"
        cls.webdb = WebDB(cls.db_path)
        cls.store = storage.Store(cls.db_path)
        cls.admin_id = cls.webdb.create_web_user(
            display_name="Admin Test", email="admin@daily.test",
            phone=None, password_hash=hash_password("admin-pass-9"))
        cls.store.set_role(cls.admin_id, roles.ROLE_ADMIN,
                           can_publish=True)
        cls.writer_id = cls.webdb.create_web_user(
            display_name="Writer Test", email="writer@daily.test",
            phone=None, password_hash=hash_password("writer-pass-9"))
        cls.store.set_role(cls.writer_id, roles.ROLE_WRITER)

        # Two tasks today: one's output waits for review, the
        # other's output is already published.
        t1 = cls.store.create_task(cls.writer_id, roles.ROLE_WRITER,
                                   "Việc chờ duyệt", [], ["website"])
        cls.store.sync_outputs_for_task(t1)
        o1 = cls.store.get_output_by_channel(t1["code"], "website")
        cls.store.set_output_draft(o1["id"], "https://telegra.ph/t1")
        cls.store.set_output_status(o1["id"], storage.STATUS_PENDING)

        t2 = cls.store.create_task(cls.writer_id, roles.ROLE_WRITER,
                                   "Việc đã đăng", [], ["website"])
        cls.store.sync_outputs_for_task(t2)
        o2 = cls.store.get_output_by_channel(t2["code"], "website")
        cls.store.set_output_draft(o2["id"], "https://telegra.ph/t2")
        cls.store.set_output_status(o2["id"],
                                    storage.STATUS_APPROVED_WAITING)
        cls.store.set_output_status(o2["id"], storage.STATUS_PUBLISHED)
        cls.store.set_output_public_url(o2["id"],
                                        "https://example.test/post")

        cls.files_dir = Path(cls.tmp) / "files"
        cls.app = App(cls.db_path, files_dir=cls.files_dir)
        cls.server = make_server("127.0.0.1", 0, cls.app)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.app.close()
        cls.store.close()
        cls.webdb.close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _login(self, email, password):
        conn = http.client.HTTPConnection("127.0.0.1", self.port,
                                          timeout=10)
        conn.request("POST", "/api/auth/login",
                     body=json.dumps({"login": email,
                                      "password": password}),
                     headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        conn.close()
        self.assertEqual(response.status, 200, data)
        return data["token"]

    def test_daily_summary_exact_numbers(self):
        token = self._login("writer@daily.test", "writer-pass-9")
        conn = http.client.HTTPConnection("127.0.0.1", self.port,
                                          timeout=10)
        conn.request("GET", "/api/stats/daily-summary",
                     headers={"Authorization": f"Bearer {token}"})
        response = conn.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        conn.close()
        self.assertEqual(response.status, 200, data)
        self.assertEqual(data["tasks_created"], 2)
        self.assertEqual(data["outputs_total"], 2)
        self.assertEqual(data["outputs_by_status"],
                         {"PENDING": 1, "PUBLISHED": 1})
        self.assertEqual(data["published_today"], 1)
        self.assertEqual(data["pending_review"], 1)
        self.assertEqual(data["approved_waiting"], 0)

    def test_daily_summary_guard_and_delivery(self):
        from datetime import datetime, timedelta

        fake = FakePushServer(status=201).start()
        try:
            # The Admin subscribes (directly at the webdb layer).
            recv_pem, recv_point = push_mod.generate_ec_keypair()
            auth = os.urandom(16)
            self.webdb.upsert_push_subscription(
                self.admin_id, fake.endpoint("admin"),
                push_mod.b64url_encode(recv_point),
                push_mod.b64url_encode(auth), "test-agent")

            day1_morning = datetime(2026, 10, 24, 19, 59, tzinfo=ICT)
            day1_evening = datetime(2026, 10, 24, 20, 5, tzinfo=ICT)
            day1_later = datetime(2026, 10, 24, 21, 30, tzinfo=ICT)
            day2_evening = day1_evening + timedelta(days=1)

            self.assertFalse(maybe_send_daily_summary(
                self.app, now=day1_morning))
            self.assertTrue(maybe_send_daily_summary(
                self.app, now=day1_evening))
            # Once per day: a second pass the same evening is a no-op.
            self.assertFalse(maybe_send_daily_summary(
                self.app, now=day1_later))
            self.assertEqual(self.webdb.get_meta(
                "web_daily_summary_date"), "2026-10-24")

            # Exactly one push went to the Admin's endpoint, and it
            # decrypts to the summary text.
            self.assertEqual(len(fake.requests), 1)
            plain = push_mod.decrypt_payload(
                fake.requests[0]["body"], recv_pem, recv_point, auth)
            payload = json.loads(plain.decode("utf-8"))
            self.assertIn("Tổng kết ngày 24/10/2026", payload["title"])
            self.assertIn("Việc tạo hôm nay: 2", payload["body"])

            # Exactly one inbox item exists for everyone.
            token = self._login("writer@daily.test", "writer-pass-9")
            conn = http.client.HTTPConnection("127.0.0.1", self.port,
                                              timeout=10)
            conn.request("GET", "/api/notifications",
                         headers={"Authorization": f"Bearer {token}"})
            response = conn.getresponse()
            data = json.loads(response.read().decode("utf-8"))
            conn.close()
            dailies = [i for i in data["items"]
                       if i["kind"] == "daily_summary"]
            self.assertEqual(len(dailies), 1)
            self.assertIn("Tổng kết ngày 24/10/2026", dailies[0]["title"])

            # The next day it fires again (second push, second item).
            self.assertTrue(maybe_send_daily_summary(
                self.app, now=day2_evening))
            self.assertEqual(len(fake.requests), 2)
        finally:
            fake.stop()


if __name__ == "__main__":
    unittest.main()
