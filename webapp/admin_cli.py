"""CLI to create web accounts — starting with the first Admin.

Usage:
    python3 -m webapp.admin_cli create-admin --email a@b.c --name "Tên"
    python3 -m webapp.admin_cli create-admin --email a@b.c --name "Tên" \
        --telegram-id 123456789        # attach to an existing bot user

The password is read from the WEBAPP_ADMIN_PASSWORD environment
variable, or prompted with getpass. It is never accepted as a command
line argument and never printed.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from .db import WebDB, default_db_path, import_bot_modules

storage, roles, _stats = import_bot_modules()


def _read_password() -> str:
    password = os.environ.get("WEBAPP_ADMIN_PASSWORD")
    if password:
        return password
    password = getpass.getpass("Mật khẩu cho tài khoản Admin mới: ")
    if password != getpass.getpass("Nhập lại mật khẩu: "):
        raise SystemExit("Mật khẩu nhập lại không khớp.")
    return password


def create_admin(email: str, name: str, phone: str | None = None,
                 telegram_id: int | None = None, password: str = "",
                 db_path=None) -> int:
    """Create (or credential) an Admin web account; returns user id."""
    from .auth import hash_password

    if len(password) < 8:
        raise SystemExit("Mật khẩu phải có ít nhất 8 ký tự.")
    webdb = WebDB(db_path or default_db_path())
    try:
        email = (email or "").strip().lower()
        if not email:
            raise SystemExit("Cần --email.")
        existing = webdb.find_user_by_email(email)
        if existing is not None:
            raise SystemExit(f"Email {email} đã có tài khoản "
                             f"(id {existing['telegram_id']}).")
        store = storage.Store(webdb.db_path)
        try:
            if telegram_id is not None:
                target = store.get_user(telegram_id)
                if target is None:
                    raise SystemExit(
                        f"Không tìm thấy người dùng Telegram {telegram_id}.")
                webdb.set_credentials(
                    telegram_id, email, phone, hash_password(password))
                user_id = telegram_id
            else:
                user_id = webdb.create_web_user(
                    display_name=name, email=email, phone=phone,
                    password_hash=hash_password(password))
            store.set_role(user_id, roles.ROLE_ADMIN, can_publish=True)
            store.audit(None, "create_web_user", "user", user_id,
                        detail="role=admin via=admin_cli")
        finally:
            store.close()
        return user_id
    finally:
        webdb.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="webapp.admin_cli")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-admin", help="Tạo tài khoản Admin")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--phone")
    create.add_argument("--telegram-id", type=int)
    args = parser.parse_args(argv)

    if args.command == "create-admin":
        password = _read_password()
        user_id = create_admin(
            email=args.email, name=args.name, phone=args.phone,
            telegram_id=args.telegram_id, password=password)
        print(f"Đã tạo tài khoản Admin web: id={user_id} email={args.email}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
