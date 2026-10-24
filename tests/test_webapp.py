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
from webapp.app import App, make_server  # noqa: E402
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

        cls.app = App(cls.db_path)
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

    # ------------------------------------------------------------ tests
    def test_health(self):
        status, data, _ = self.req("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertIn("version", data)

    def test_index_page_is_served_and_marked_temporary(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", "/")
        response = conn.getresponse()
        html = response.read().decode("utf-8")
        conn.close()
        self.assertEqual(response.status, 200)
        self.assertIn("kiểm chứng", html)
        self.assertIn("/api/auth/login", html)

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


if __name__ == "__main__":
    unittest.main()
