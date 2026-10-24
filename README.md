# Web App Giao Việc

Web App độc lập (không phụ thuộc Telegram) cho quy trình giao việc
truyền thông: **gửi tư liệu + gợi ý → Muse viết bài nháp theo từng
kênh → duyệt trên thẻ kênh → đăng Website / Facebook / Instagram /
video**. Web App **dùng chung dữ liệu với bot Telegram** hiện tại
(`~/workspace/telegram-bot-giao-viec/data/bot.db`) để hai hệ thống chạy
song song trong giai đoạn chuyển đổi.

> Trạng thái: **Giai đoạn 2 — giao diện PWA đầy đủ + backend bổ sung**
> (xem `NHAT-KY-PHAT-TRIEN.md`). Đã cài systemd service
> `webapp-giao-viec` (cổng 8790) và đã tạo tài khoản Admin đầu tiên
> gắn vào tài khoản Admin Telegram hiện có.

## Kiến trúc

```
webapp/
  app.py        HTTP API (http.server, ThreadingHTTPServer) + phân quyền
  db.py         WebDB: migration + bảng web_sessions + truy vấn riêng của web
  auth.py       Băm mật khẩu PBKDF2-HMAC-SHA256 + token phiên
  admin_cli.py  CLI tạo tài khoản Admin đầu tiên
  static/       Giao diện PWA chính thức (GĐ2): index.html + app.js +
                styles.css + manifest.webmanifest + sw.js + icon
webapp-giao-viec.service   Unit systemd (bản trong repo; bản chạy thật
                nằm ở /etc/systemd/system/)
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
- GĐ2 cộng thêm: bảng `web_meta` (key/value phía web) và
  `web_notification_reads` (đánh dấu thông báo đã đọc theo người
  dùng) — vẫn thuần cộng thêm, bot không bị ảnh hưởng.

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
ℹ️ Cập nhật cùng ngày 24/10/2026: tại thời điểm kiểm tra cuối, service
bot không chạy vì **máy ảo vừa bị thay mới** (đăng ký systemd bị mất —
sự cố môi trường đã biết, không liên quan migration). Service đã được
cài lại và khởi động ngay sau đó theo quy trình quen thuộc của dự án
bot; bot chạy bình thường, dữ liệu nguyên vẹn.

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
| `WEBAPP_FILES_DIR` | `data/files` của bot | Thư mục tư liệu dùng chung với bot |

Chưa có tên miền/HTTPS — thuộc GĐ4 (triển khai production).

## Triển khai nội bộ (systemd) + khôi phục sau khi máy bị thay mới

Service `webapp-giao-viec` chạy nền trên cổng **8790**, unit nằm trong
repo (`webapp-giao-viec.service`) và được cài vào
`/etc/systemd/system/`. Proxy egress của VM nằm trong
`/etc/default/webapp-giao-viec` (root-only, mode 600 — theo đúng tiền
lệ của bot; **không** để giá trị proxy hay mật khẩu trong workspace).

Khôi phục khi VM bị thay mới (đăng ký systemd + file `/etc/default`
bị mất, dữ liệu trong workspace còn nguyên):

```bash
# 1) Viết lại /etc/default/webapp-giao-viec từ biến proxy của shell
{ for v in http_proxy https_proxy HTTP_PROXY HTTPS_PROXY no_proxy NO_PROXY; do
    [ -n "${!v:-}" ] && printf '%s=%s\n' "$v" "${!v}"; done; } \
  > /etc/default/webapp-giao-viec && chmod 600 /etc/default/webapp-giao-viec
# 2) Cài lại unit và bật service
install -m 664 webapp-giao-viec.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now webapp-giao-viec
# 3) Kiểm chứng
systemctl is-active webapp-giao-viec
curl -fsS http://127.0.0.1:8790/api/health
```

## Tải tư liệu (upload) — quyết định GĐ2

- **Hai điểm vào, cùng một định dạng lưu trữ của bot**: (a) upload
  **kèm khi tạo việc** — `POST /api/tasks` dạng `multipart/form-data`
  (field `hint`, `destinations` lặp, `files` lặp); (b) gắn thêm vào
  việc đã có — `POST /api/uploads` (field `task_code` + `files`) hoặc
  `POST /api/tasks/<code>/files`.
- File được lưu vào đúng `data/files/<MÃ VIỆC>/` của bot, tên file vệ
  sinh (bỏ ký tự nguy hiểm, chống trùng bằng hậu tố `-2`, `-3`…);
  `tasks.file_ids` lưu **tên file** — Muse xử lý việc từ web giống
  hệt việc từ Telegram.
- **Giới hạn 200MB mỗi file** (tổng request 1GB) — khác hẳn giới hạn
  20MB của Telegram Bot API; đây là một lý do chính để có Web App.
- Tải/xem lại: `GET /api/files/<code>/<filename>` có kiểm quyền xem
  việc, chống path traversal, hỗ trợ HTTP Range (phát video).

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

✅ Đã tạo tài khoản Admin đầu tiên (24/10/2026): gắn đăng nhập web
(email + SĐT của chủ dự án) vào đúng tài khoản Admin Telegram hiện
có, mật khẩu tạm đã bàn giao ngoài tài liệu này; đăng nhập xong nên
đổi ngay bằng màn hình đổi mật khẩu trong app
(`POST /api/auth/change-password`).

## API (GĐ1 + GĐ2)

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

API bổ sung ở GĐ2:

| Method & path | Quyền | Mô tả |
|---|---|---|
| `POST /api/tasks` (multipart) | đã cấp quyền | Tạo việc kèm upload tư liệu (xem mục Upload) |
| `POST /api/uploads` / `POST /api/tasks/<code>/files` | người tạo việc/Admin | Gắn thêm tư liệu vào việc |
| `GET /api/files/<code>/<filename>` | xem được việc | Tải/xem tư liệu, hỗ trợ Range |
| `GET /api/outputs/<id>/draft-video` | xem được việc | Phát video nháp trong trang (Range) |
| `POST /api/outputs/<id>/<action>` | theo thao tác | `submit` (gửi duyệt, người tạo, chặn khi chưa có nháp), `approve`/`reject` (người duyệt; reject bắt buộc lý do), `revise` (người tạo), `cancel` (người duyệt), `publish` (chỉ ghi lệnh `publish_requested`; Facebook bắt buộc `target` ∈ {profile, page}, thiếu → 422 `target_required`; Admin đăng việc của mình tự qua duyệt `auto=admin_own`; **không** tự lật Đã đăng), `publish-abort` (`publish_aborted`), `schedule`/`schedule-abort`/`unschedule` (giờ ISO hoặc mẫu bot `16:30`, `24/10 16:30`, preset `60/120/eve/mor`; Facebook chốt target trước; cảnh báo trùng <1 giờ trả trong `warnings`, không chặn), `retract` (Facebook: ghi `retract_requested`; kênh khác: thu hồi trong hệ thống). Mọi thao tác ghi đúng tên audit + chuyển trạng thái như `handlers.py` của bot; sai quyền → 403 kèm audit `denied_output_*_attempt` |
| `GET /api/review-queue` | người duyệt | Các thẻ kênh đang PENDING mà mình có quyền duyệt |
| `GET /api/scheduled` | người duyệt | Mọi bài đang đặt lịch, theo giờ tăng dần |
| `GET /api/stats/export?format=csv\|xlsx&period=` | người duyệt | Xuất qua `stats.write_csv` (BOM UTF-8) / `stats.write_xlsx` của bot |
| `GET /api/notifications` / `POST /api/notifications/read` | đã đăng nhập | Hộp thông báo suy từ outputs + audit (chờ duyệt mới cho người duyệt; việc của mình bị trả/có bản mới/đã đăng/đã thu hồi); trạng thái đã đọc lưu ở `web_notification_reads`. Web Push thật thuộc GĐ3 |
| `POST /api/auth/change-password` | đã đăng nhập | `{old_password, new_password}`; đổi xong huỷ mọi phiên khác |
| `PATCH /api/users/<id>/role` | theo `can_grant` | Đổi vai trò + quyền đăng (`grant_role`) |
| `POST /api/users/<id>/revoke` | theo `can_revoke` | Thu hồi quyền (`revoke_role`) + huỷ phiên web của người bị thu hồi |

## Kiểm thử

```bash
cd ~/workspace/webapp-giao-viec
python3 -m unittest discover -s tests     # 37 test (GĐ2) — chạy trên BẢN SAO/temp DB

cd ~/workspace/telegram-bot-giao-viec
python3 -m unittest discover -s tests     # 215 test của bot (không hồi quy)
```
