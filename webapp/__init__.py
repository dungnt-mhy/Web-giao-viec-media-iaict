"""Web App Giao Việc — backend (Giai đoạn 1 + 2 + 3).

Pure-stdlib HTTP API + PWA frontend that shares the Telegram bot's
SQLite database (``data/bot.db`` of ~/workspace/telegram-bot-giao-viec)
and reuses its ``storage.Store`` / ``roles`` / ``stats`` modules
unchanged. GĐ3 adds Web Push notifications (``webapp/push.py``) and
the in-app daily summary.
"""

VERSION = "0.5.0"
