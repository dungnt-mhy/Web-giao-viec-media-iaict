# Web App Giao Việc

Web App độc lập (không phụ thuộc Telegram) cho quy trình giao việc
truyền thông: **gửi tư liệu + gợi ý → Muse viết bài nháp theo từng
kênh → duyệt trên thẻ kênh → đăng Website / Facebook / Instagram /
video**. Web App **dùng chung dữ liệu với bot Telegram** hiện tại
(`~/workspace/telegram-bot-giao-viec/data/bot.db`) để hai hệ thống chạy
song song trong giai đoạn chuyển đổi.

> Trạng thái: **Giai đoạn 1 — API + đăng nhập riêng + di trú dữ liệu**
> (xem `NHAT-KY-PHAT-TRIEN.md`). Giao diện chính thức thuộc Giai đoạn 2;
> trang tại `/` hiện tại chỉ là trang kiểm chứng đăng nhập tạm.

## Kiến trúc

```
webapp/
  app.py        HTTP API (http.server, ThreadingHTTPServer) + phân quyền
  db.py         WebDB: migration + bảng web_sessions + truy vấn riêng của web
  auth.py       Băm mật khẩu PBKDF2-HMAC-SHA256 + token phiên
  admin_cli.py  CLI tạo tài khoản Admin đầu tiên
  static/       Trang kiểm chứng tạm (GĐ1)
tests/
  test_webapp.py
```

### Quyết định kỹ thuật

- **Thuần Python stdlib** (`http.server`, `sqlite3`, `hashlib`) — không
  cài thêm gói nào, cùng triết lý với dự án bot: máy chủ từng bị thay
  mới nhiều lần, càng ít phụ thuộc càng bền.
- **Dùng lại code của bot, không sao chép**: `storage.Store`, `roles`,
  `stats` được import từ thư mục bot qua `sys.path`
  (`WEBAPP_BOT_DIR`, mặc định `~/workspace/telegram-bot-giao-viec`).
  Mọi quy tắc nghiệp vụ (mã việc `CV-xxxx`, outputs theo kênh,
  audit log, ma trận quyền) là của bot, web chỉ là một mặt tiền khác.
- **Phân quyền kiểm tra ở server** theo đúng `roles.py` cho mọi
  endpoint; client không được tin. Tạo việc: mọi vai trò đã được cấp
  quyền (kể cả Cộng tác viên — khớp `CREATOR_ROLES` của bot); tài
  khoản chờ cấp quyền (role NULL) bị 403. Thống kê: chỉ người duyệt
  (Admin/Phó Admin/Biên tập viên). Quản lý người dùng: Admin/Phó
  Admin, và cấp vai trò theo `roles.can_grant` (Phó Admin chỉ tạo
  được Nhân viên/Cộng tác viên).
- **Đăng nhập riêng** bằng email/SĐT + mật khẩu; tài khoản do Admin
  tạo (không tự đăng ký). Mật khẩu băm **PBKDF2-HMAC-SHA256**, 200.000
  vòng, salt ngẫu nhiên riêng từng mật khẩu; không bao giờ lưu/ghi
  log/trả về mật khẩu thô hay bản băm.
- **Phiên đăng nhập**: token ngẫu nhiên 32 byte; DB chỉ lưu **băm
  SHA-256 của token** trong bảng `web_sessions` (kèm hạn dùng, mặc
  định 7 ngày — `WEBAPP_SESSION_TTL_DAYS`). API chấp nhận cookie
  `webapp_session` (HttpOnly, SameSite=Lax) hoặc header
  `Authorization: Bearer <token>`.
- **Người dùng web-only**: bảng `users` của bot lấy `telegram_id` làm
  khóa chính, nên tài khoản chỉ có trên web được cấp **telegram_id
  tổng hợp ≥ 9.000.000.000** — mọi phương thức sẵn có của `Store` vẫn
  chạy bình thường cho họ. Tài khoản Telegram sẵn có cũng gắn thêm
  thông tin đăng nhập web được (xem `admin_cli --telegram-id`) mà
  không tạo dòng mới.

## Di trú dữ liệu (migration)

`WebDB.migrate()` chạy tự động khi server/CLI khởi động, **idempotent**
(chạy nhiều lần không đổi gì thêm), thuần cộng thêm:

- `users` thêm cột `email`, `phone`, `password_hash` (đều nullable)
  + unique index từng phần cho email/phone.
- Thêm bảng `web_sessions`.

An toàn với bot: mọi câu INSERT của bot đều nêu tên cột tường minh và
SELECT đọc theo tên cột, nên cột mới vô hình với bot (đã kiểm chứng
bằng bộ test của bot trên DB đã migrate + test Store trên bản sao DB
thật).

**Trạng thái trên DB thật (2026-10-24)**: ĐÃ ÁP migration lên
`telegram-bot-giao-viec/data/bot.db`. Trước khi áp đã sao lưu tại
`telegram-bot-giao-viec/data/backup-webapp-20261024-011905/bot.db`
(qua SQLite backup API, `integrity_check` = ok; 1 người dùng,
12 việc, `task_seq` = 12 — khớp số liệu sau khi áp). Sau khi áp:
Store của bot mở DB thật bình thường, dữ liệu nguyên vẹn.
⚠️ Tại thời điểm kiểm tra cuối, service bot không chạy vì **máy ảo
vừa bị thay mới** (uptime 3 phút, đăng ký systemd bị mất — sự cố môi
trường đã biết, không liên quan migration); chờ khôi phục service
theo quy trình quen thuộc của dự án bot.

## Chạy server

```bash
cd ~/workspace/webapp-giao-viec
python3 -m webapp.app            # cổng mặc định 8790
```

Biến môi trường:

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `WEBAPP_PORT` | `8790` | Cổng HTTP |
| `WEBAPP_HOST` | `0.0.0.0` | Địa chỉ bind |
| `WEBAPP_DB_PATH` | DB của bot | Đường dẫn file SQLite |
| `WEBAPP_BOT_DIR` | `~/workspace/telegram-bot-giao-viec` | Nơi import `storage/roles/stats` |
| `WEBAPP_SESSION_TTL_DAYS` | `7` | Hạn phiên đăng nhập |

GĐ1 chưa cài systemd service và chưa có tên miền/HTTPS — thuộc bước
triển khai sau.

## Tạo tài khoản Admin đầu tiên

```bash
cd ~/workspace/webapp-giao-viec
# Cách 1: gắn đăng nhập web cho tài khoản Admin Telegram sẵn có
WEBAPP_ADMIN_PASSWORD='…' python3 -m webapp.admin_cli create-admin \
    --email admin@example.vn --name "Ng TDung" --telegram-id <id>
# Cách 2: tạo tài khoản web-only mới (không có --telegram-id);
# không đặt biến môi trường thì CLI hỏi mật khẩu bằng getpass.
```

Mật khẩu **không** nhận qua tham số dòng lệnh và không in ra log.

## API (GĐ1)

| Method & path | Quyền | Mô tả |
|---|---|---|
| `GET /api/health` | công khai | `{ok, version, db}` |
| `POST /api/auth/login` | công khai | `{login: email/SĐT, password}` → phiên (cookie + token) |
| `POST /api/auth/logout` | đã đăng nhập | Huỷ phiên hiện tại |
| `GET /api/auth/me` | đã đăng nhập | Thông tin + vai trò + quyền của mình |
| `GET /api/tasks?status=&channel=&creator=&q=&limit=&offset=` | đã cấp quyền | Danh sách việc có lọc + phân trang |
| `GET /api/tasks/<code>` | đã cấp quyền | Việc + outputs theo kênh + audit liên quan |
| `POST /api/tasks` | đã cấp quyền | `{hint, destinations[]}` → tạo việc (sinh mã CV- tiếp nối, tạo outputs, ghi audit như bot) |
| `GET /api/stats/summary?period=today\|week\|month\|all` | người duyệt | Thống kê qua `stats.collect_stats` |
| `GET /api/users` | Admin/Phó Admin | Danh sách tài khoản (không có password_hash) |
| `POST /api/users` | theo `can_grant` | `{name, email?, phone?, password, role, can_publish?}` → tài khoản web mới |

## Kiểm thử

```bash
cd ~/workspace/webapp-giao-viec
python3 -m unittest discover -s tests     # 19 test — chạy trên BẢN SAO bot.db

cd ~/workspace/telegram-bot-giao-viec
python3 -m unittest discover -s tests     # 215 test của bot (không hồi quy)
```
