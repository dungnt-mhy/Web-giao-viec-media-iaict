"""Database access for the Web App.

The web app does NOT own a separate database: it reads and writes the
bot's ``bot.db`` so the Telegram bot and the web app stay in sync while
both run side by side. The bot's own modules (``storage``, ``roles``,
``stats``) are imported from the bot project directory — never copied,
never modified.

Web-specific schema (added by an idempotent migration):

- ``users`` gains ``email``, ``phone`` and ``password_hash`` columns.
  The bot only ever names columns explicitly on INSERT and reads with
  ``SELECT *`` keyed by column name, so extra nullable columns are
  invisible to it.
- ``web_sessions`` holds web login sessions. Only the SHA-256 hash of
  a session token is stored, never the token itself.

Users that exist only on the web (no Telegram account) still need a
``telegram_id`` because it is the users-table primary key and the key
every ``Store`` method uses. They are allocated synthetic ids in the
range >= 9_000_000_000, far above any real Telegram id, so all
existing store methods keep working for them unchanged.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = PROJECT_ROOT.parent

#: First synthetic telegram_id for web-only users.
SYNTHETIC_ID_BASE = 9_000_000_000


def bot_dir() -> Path:
    """Directory of the Telegram bot project (source of storage.py)."""
    override = os.environ.get("WEBAPP_BOT_DIR")
    if override:
        return Path(override)
    return WORKSPACE / "telegram-bot-giao-viec"


def default_db_path() -> Path:
    override = os.environ.get("WEBAPP_DB_PATH")
    if override:
        return Path(override)
    return bot_dir() / "data" / "bot.db"


def import_bot_modules():
    """Import and return (storage, roles, stats) from the bot project."""
    directory = str(bot_dir())
    if directory not in sys.path:
        sys.path.insert(0, directory)
    import roles  # noqa: E402  (path set up above)
    import stats  # noqa: E402
    import storage  # noqa: E402
    return storage, roles, stats


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


class WebDB:
    """Web-owned tables/columns on top of the shared bot database.

    Uses its own sqlite connection (the bot's ``Store`` keeps its own),
    guarded by a lock; the bot's single-process store is unaffected.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self.migrate()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ------------------------------------------------------------ migrate
    def migrate(self) -> None:
        """Idempotent web schema migration; safe to run any number of
        times and safe on a live bot database (purely additive)."""
        storage, _roles, _stats = import_bot_modules()
        with self._lock, self._conn:
            # Base schema first so a brand-new database file also works.
            self._conn.executescript(storage.SCHEMA)
            columns = {
                row["name"]
                for row in self._conn.execute("PRAGMA table_info(users)")
            }
            if "email" not in columns:
                self._conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
            if "phone" not in columns:
                self._conn.execute("ALTER TABLE users ADD COLUMN phone TEXT")
            if "password_hash" not in columns:
                self._conn.execute(
                    "ALTER TABLE users ADD COLUMN password_hash TEXT")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS web_sessions (
                    token_hash  TEXT PRIMARY KEY,
                    user_id     INTEGER NOT NULL,
                    created_at  TEXT NOT NULL,
                    expires_at  TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email"
                " ON users (email) WHERE email IS NOT NULL"
            )
            self._conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone"
                " ON users (phone) WHERE phone IS NOT NULL"
            )
            # Giai đoạn 2 additions: tiny web-owned key/value store and
            # per-user notification read markers. Both are additive
            # tables in the shared database; the bot ignores them.
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS web_meta (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS web_notification_reads (
                    user_id         INTEGER NOT NULL,
                    notification_key TEXT NOT NULL,
                    read_at         TEXT NOT NULL,
                    PRIMARY KEY (user_id, notification_key)
                )
                """
            )

    # -------------------------------------------------------------- users
    def get_user(self, user_id: int):
        with self._lock:
            return self._conn.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (user_id,)
            ).fetchone()

    def find_user_by_login(self, login: str):
        """Find a user by email (case-insensitive) or phone number."""
        login = (login or "").strip()
        if not login:
            return None
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM users WHERE lower(email) = lower(?)",
                (login,),
            ).fetchone()
            if row is None:
                row = self._conn.execute(
                    "SELECT * FROM users WHERE phone = ?", (login,)
                ).fetchone()
        return row

    def find_user_by_email(self, email: str):
        with self._lock:
            return self._conn.execute(
                "SELECT * FROM users WHERE lower(email) = lower(?)",
                ((email or "").strip(),),
            ).fetchone()

    def find_user_by_phone(self, phone: str):
        with self._lock:
            return self._conn.execute(
                "SELECT * FROM users WHERE phone = ?",
                ((phone or "").strip(),),
            ).fetchone()

    def next_synthetic_id(self) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT MAX(telegram_id) AS m FROM users WHERE telegram_id >= ?",
                (SYNTHETIC_ID_BASE,),
            ).fetchone()
        current = row["m"] if row else None
        return SYNTHETIC_ID_BASE if current is None else current + 1

    def create_web_user(self, display_name: str, email: str | None,
                        phone: str | None, password_hash: str) -> int:
        """Insert a web-only user (pending role) with a synthetic id.

        Role assignment is left to the caller (via the bot Store's
        ``set_role``) so the grant rules stay in one place.
        """
        user_id = self.next_synthetic_id()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO users (telegram_id, username, display_name,
                                   role, can_publish, categories, chat_id,
                                   created_at, email, phone, password_hash)
                VALUES (?, NULL, ?, NULL, 0, '[]', NULL, ?, ?, ?, ?)
                """,
                (user_id, display_name, _iso(_utcnow()),
                 (email or None), (phone or None), password_hash),
            )
        return user_id

    def set_credentials(self, user_id: int, email: str | None,
                        phone: str | None, password_hash: str) -> None:
        """Attach/replace web login credentials on an existing user."""
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE users SET email = ?, phone = ?, password_hash = ?"
                " WHERE telegram_id = ?",
                (email or None, phone or None, password_hash, user_id),
            )

    # ----------------------------------------------------------- sessions
    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_session(self, user_id: int, raw_token: str,
                       ttl_days: int = 7) -> None:
        now = _utcnow()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO web_sessions (token_hash, user_id, created_at,"
                " expires_at) VALUES (?, ?, ?, ?)",
                (self._token_hash(raw_token), user_id, _iso(now),
                 _iso(now + timedelta(days=ttl_days))),
            )

    def get_session_user(self, raw_token: str):
        """User row for a valid session token, else None (expired
        sessions are deleted on sight)."""
        if not raw_token:
            return None
        token_hash = self._token_hash(raw_token)
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM web_sessions WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()
        if row is None:
            return None
        if row["expires_at"] <= _iso(_utcnow()):
            self.delete_session(raw_token)
            return None
        return self.get_user(row["user_id"])

    def delete_session(self, raw_token: str) -> None:
        if not raw_token:
            return
        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM web_sessions WHERE token_hash = ?",
                (self._token_hash(raw_token),),
            )

    # -------------------------------------------------------------- tasks
    def list_tasks(self, status=None, channel=None, creator_id=None,
                   q=None, limit: int = 50, offset: int = 0):
        """Filtered task listing for the API (the bot Store only offers
        unfiltered listings). Returns (rows, total)."""
        clauses, args = [], []
        if status:
            clauses.append("t.status = ?")
            args.append(status)
        if creator_id is not None:
            clauses.append("t.creator_id = ?")
            args.append(creator_id)
        if channel:
            clauses.append(
                "EXISTS (SELECT 1 FROM outputs o"
                " WHERE o.task_code = t.code AND o.channel = ?)")
            args.append(channel)
        if q:
            clauses.append("(t.code LIKE ? OR t.hint LIKE ?)")
            args.extend([f"%{q}%", f"%{q}%"])
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) AS n FROM tasks t{where}", args
            ).fetchone()["n"]
            rows = self._conn.execute(
                "SELECT t.id, t.code, t.creator_id, t.creator_role, t.hint,"
                " t.file_ids, t.draft_url, t.public_url, t.status,"
                " t.reject_reason, t.destinations, t.created_at, t.updated_at,"
                " u.display_name AS creator_name"
                f" FROM tasks t LEFT JOIN users u"
                " ON u.telegram_id = t.creator_id"
                f"{where} ORDER BY t.id DESC LIMIT ? OFFSET ?",
                [*args, limit, offset],
            ).fetchall()
        return rows, total

    # -------------------------------------------------- GĐ2: account/meta
    def set_password_hash(self, user_id: int, password_hash: str) -> None:
        """Replace only the password hash, preserving email/phone."""
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE users SET password_hash = ? WHERE telegram_id = ?",
                (password_hash, user_id),
            )

    def delete_user_sessions(self, user_id: int,
                             except_raw_token: str | None = None) -> None:
        """Invalidate a user's web sessions, optionally sparing one."""
        except_hash = (self._token_hash(except_raw_token)
                       if except_raw_token else None)
        with self._lock, self._conn:
            if except_hash:
                self._conn.execute(
                    "DELETE FROM web_sessions WHERE user_id = ?"
                    " AND token_hash != ?", (user_id, except_hash))
            else:
                self._conn.execute(
                    "DELETE FROM web_sessions WHERE user_id = ?",
                    (user_id,))

    def get_meta(self, key: str, default=None):
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM web_meta WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else default

    def set_meta(self, key: str, value: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO web_meta (key, value) VALUES (?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def set_task_file_ids(self, code: str, file_ids) -> None:
        """Persist the task's material file list (web uploads store
        file *names*; the actual bytes live under data/files/<code>/,
        exactly where the bot's downloader puts Telegram materials)."""
        import json

        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE tasks SET file_ids = ?, updated_at = ?"
                " WHERE code = ?",
                (json.dumps(list(file_ids), ensure_ascii=False),
                 _iso(_utcnow()), code),
            )

    # ------------------------------------------- GĐ2: queues and schedules
    def outputs_where(self, where: str, args=()):
        """Outputs joined with their task + creator display name."""
        with self._lock:
            return self._conn.execute(
                "SELECT o.*, t.creator_id AS task_creator_id,"
                " t.creator_role AS task_creator_role,"
                " t.hint AS task_hint,"
                " u.display_name AS creator_name"
                " FROM outputs o JOIN tasks t ON t.code = o.task_code"
                " LEFT JOIN users u ON u.telegram_id = t.creator_id"
                f" WHERE {where} ORDER BY o.scheduled_at, o.id",
                args,
            ).fetchall()

    def review_queue(self):
        return self.outputs_where("o.status = 'PENDING'")

    def scheduled_outputs(self):
        return self.outputs_where(
            "o.scheduled_at IS NOT NULL"
            " AND o.status = 'APPROVED_WAITING'")

    # --------------------------------------------- GĐ2: notifications
    def _latest_audits(self):
        """Latest audit row per (target output id, action)."""
        latest = {}
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM audit_log WHERE target_type = 'output'"
                " ORDER BY id"
            ).fetchall()
        for row in rows:
            latest[(str(row["target_id"]), row["action"])] = row
        return latest

    def notifications_for_user(self, user, limit: int = 100):
        """Derive the user's inbox from current output states plus
        the audit trail:

        - reviewers: every output currently PENDING review;
        - creators: their outputs that were rejected / sent back for
          revision, that gained a fresh draft, that were published,
          or that were retracted.
        """
        _storage, roles, _stats = import_bot_modules()
        user_id = user["telegram_id"]
        latest = self._latest_audits()
        items = []

        def add(key, kind, title, body, created_at, output, audit_id=None):
            items.append({
                "key": key,
                "kind": kind,
                "title": title,
                "body": body,
                "created_at": created_at,
                "task_code": output["task_code"],
                "output_id": output["id"],
                "channel": output["channel"],
                "audit_id": audit_id,
            })

        if roles.can_review(user["role"]):
            for output in self.review_queue():
                audit = latest.get((str(output["id"]), "submit_output"))
                stamp = audit["created_at"] if audit else output["updated_at"]
                aid = audit["id"] if audit else None
                add(f"review:{output['id']}:{aid or output['updated_at']}",
                    "review_pending", "Có thẻ kênh chờ duyệt",
                    f"{output['task_code']} · kênh {output['channel']}"
                    f" của {output['creator_name'] or output['task_creator_id']}",
                    stamp, output, aid)

        mine = self.outputs_where("t.creator_id = ?", (user_id,))
        for output in mine:
            oid = str(output["id"])
            label = f"{output['task_code']} · kênh {output['channel']}"
            reject_audit = None
            for action in ("revise_output", "reject_output"):
                candidate = latest.get((oid, action))
                if candidate and (reject_audit is None
                                   or candidate["id"] > reject_audit["id"]):
                    reject_audit = candidate
            if output["status"] == "REJECTED" and reject_audit is not None:
                kind = ("revision_requested"
                        if reject_audit["action"] == "revise_output"
                        else "rejected")
                add(f"reject:{output['id']}:{reject_audit['id']}", kind,
                    "Thẻ kênh bị trả lại / cần sửa",
                    f"{label}: {output['reject_reason'] or ''}",
                    reject_audit["created_at"], output, reject_audit["id"])
            attach_audit = None
            for action in ("attach_output_video", "attach_output_draft"):
                candidate = latest.get((oid, action))
                if candidate and (attach_audit is None
                                  or candidate["id"] > attach_audit["id"]):
                    attach_audit = candidate
            if output["draft_ref"] and attach_audit is not None and (
                    reject_audit is None
                    or attach_audit["id"] > reject_audit["id"]):
                add(f"draft:{output['id']}:{attach_audit['id']}",
                    "draft_ready", "Đã có bản nháp mới",
                    label, attach_audit["created_at"], output,
                    attach_audit["id"])
            if output["status"] == "PUBLISHED":
                audit = latest.get((oid, "set_output_published"))
                stamp = audit["created_at"] if audit else output["updated_at"]
                aid = audit["id"] if audit else None
                add(f"published:{output['id']}:{aid or output['updated_at']}",
                    "published", "Bài đã được đăng",
                    f"{label}: {output['public_url'] or ''}",
                    stamp, output, aid)
            if output["status"] == "RETRACTED":
                audit = latest.get((oid, "retract_output"))
                stamp = audit["created_at"] if audit else output["updated_at"]
                aid = audit["id"] if audit else None
                add(f"retracted:{output['id']}:{aid or output['updated_at']}",
                    "retracted", "Bài đã bị thu hồi", label, stamp,
                    output, aid)

        items.sort(key=lambda item: item["created_at"] or "", reverse=True)
        items = items[:limit]
        with self._lock:
            read_keys = {
                row["notification_key"]
                for row in self._conn.execute(
                    "SELECT notification_key FROM web_notification_reads"
                    " WHERE user_id = ?", (user_id,))
            }
        for item in items:
            item["read"] = item["key"] in read_keys
        return items

    def mark_notifications_read(self, user_id: int, keys) -> int:
        now = _iso(_utcnow())
        with self._lock, self._conn:
            for key in keys:
                self._conn.execute(
                    "INSERT OR IGNORE INTO web_notification_reads"
                    " (user_id, notification_key, read_at)"
                    " VALUES (?, ?, ?)", (user_id, str(key), now))
        return len(list(keys))
