# Nhật ký phát triển — Web App Giao Việc

## 2026-10-24 — Giai đoạn 1: API + đăng nhập riêng + di trú dữ liệu ✅

Người dùng chốt bản thiết kế Web App (artifact
`b-n-thi-t-k-web-app-giao-vi-c`) và duyệt bắt đầu xây thật theo lộ
trình 4 giai đoạn. GĐ1 xây dự án mới `~/workspace/webapp-giao-viec/`,
độc lập với Telegram nhưng dùng chung `bot.db` với bot hiện tại.

### Đã làm

- **Backend thuần stdlib** (`http.server.ThreadingHTTPServer`, không
  Flask/FastAPI, không cài thêm gói): `webapp/app.py` (API + phân
  quyền server-side), `webapp/db.py` (WebDB), `webapp/auth.py`
  (PBKDF2-HMAC-SHA256, 200k vòng, salt riêng; token phiên chỉ lưu băm
  SHA-256), `webapp/admin_cli.py`, trang kiểm chứng tạm ở
  `webapp/static/index.html` (ghi rõ là tạm, không phải giao diện
  chính thức).
- **Dùng lại code bot qua import** (`storage.Store`, `roles`,
  `stats`) — không sao chép, không sửa một dòng nào của dự án bot.
- **Migration idempotent**: `users` += `email`, `phone`,
  `password_hash` + unique index từng phần; thêm bảng `web_sessions`.
  Người dùng web-only nhận telegram_id tổng hợp ≥ 9.000.000.000.
- **Endpoints**: health; auth login/logout/me (cookie HttpOnly +
  Bearer); tasks list (lọc status/channel/creator/q + phân trang),
  detail (kèm outputs + audit), create (mã CV- tiếp nối, tạo outputs
  theo kênh, audit `create_task ... via=webapp` như bot); stats
  summary (period today/week/month/all qua `stats.collect_stats`);
  users list/create.
- **CLI tạo Admin**: `python3 -m webapp.admin_cli create-admin
  --email … --name … [--telegram-id …]`; mật khẩu qua biến môi trường
  `WEBAPP_ADMIN_PASSWORD` hoặc getpass, không qua argv, không in log.

### Kiểm chứng (toàn bộ trên bản sao DB / DB tạm, trừ bước cuối)

- Test webapp: **19/19 đạt** (`python3 -m unittest discover -s tests`)
  — migration idempotent + giữ dữ liệu; đăng nhập đúng/sai; phiên hết
  hạn/không hợp lệ → 401; ma trận quyền (vai thấp → 403 ở /api/users
  và /api/stats; Phó Admin tạo Nhân viên được, tạo Biên tập viên bị
  403 theo `can_grant`; trùng email → 409); tạo việc sinh đúng mã
  CV- kế tiếp + audit; lọc/phân trang khớp; stats khớp số đếm Store;
  CLI tạo được Admin đăng nhập được + gắn credentials cho user
  Telegram sẵn có không tạo dòng mới.
- Test bot gốc: **215/215 đạt** — không hồi quy. Store của bot cũng
  được chạy trực tiếp trên bản sao DB thật đã migrate trong bộ test
  webapp (tạo việc/cấp quyền/thống kê đều chạy).
- Chạy thử server thật trên bản sao DB đã migrate: `/api/health` 200,
  `/` 200, `/api/auth/me` chưa đăng nhập → 401.

### Di trú trên DB thật — ĐÃ ÁP (2026-10-24 ~01:19 giờ VN)

1. Sao lưu trước: `telegram-bot-giao-viec/data/backup-webapp-20261024-011905/bot.db`
   (SQLite backup API, integrity_check ok; 1 user / 12 việc / seq 12).
2. Áp migration (chạy 2 lần liên tiếp để chứng minh idempotent ngay
   trên DB thật): cột mới + bảng `web_sessions` đã có; Store của bot
   mở DB thật đọc bình thường, số liệu nguyên vẹn (12 việc, seq 12,
   Admin "Ng TDung" còn nguyên).
3. ⚠️ **Service bot tại thời điểm kiểm tra cuối: KHÔNG chạy** —
   `systemctl` báo không tìm thấy unit, máy ảo uptime mới 3 phút:
   VM lại bị thay mới làm mất đăng ký systemd (sự cố môi trường đã
   xảy ra nhiều lần ngày 22–23/10, **không liên quan migration** —
   migration chỉ là SQL cộng thêm trên file DB thuộc workspace, file
   này còn nguyên). Cần khôi phục service bot theo quy trình quen
   thuộc (cài lại unit + EnvironmentFile proxy + enable --now) —
   việc này nằm ngoài phạm vi GĐ1, đã báo cáo lên.

### Điểm tự chốt (chờ người dùng duyệt lại)

1. **Phiên 7 ngày**, cookie `SameSite=Lax` + hỗ trợ Bearer token.
2. **Mật khẩu tạm tối thiểu 8 ký tự** khi Admin tạo tài khoản.
3. Tạo việc qua API ở GĐ1 chưa kèm file (tải file thuộc GĐ2);
   `file_ids` để rỗng, audit ghi `files=0 via=webapp`.
4. `GET /api/tasks` và chi tiết việc: mọi tài khoản đã được cấp
   quyền đều xem được (ma trận hiện hành của bot không giới hạn
   việc xem danh sách theo người tạo; nếu cần siết theo vai trò thì
   chốt ở GĐ2).
5. Chưa tạo tài khoản Admin web nào trên DB thật — chờ thông tin
   email/SĐT thật của người dùng để chạy `admin_cli` (nên dùng
   `--telegram-id` gắn vào đúng tài khoản Admin hiện có).
6. Sự cố service bot do VM thay mới (nêu trên) — chờ khôi phục riêng.

### Còn lại

- **GĐ2**: giao diện chính thức (đăng nhập, tổng quan, wizard giao
  việc có tải file, danh sách/chi tiết việc + thẻ kênh, chờ duyệt,
  lịch đăng, thống kê biểu đồ, quản lý người dùng, thông báo).
- **GĐ3**: thông báo đẩy + hoàn thiện quản lý người dùng.
- **GĐ4**: chạy song song, chuyển đội sang Web App, tắt dần bot;
  cài systemd service + tên miền/HTTPS cho webapp ở bước triển khai.
- Chưa push GitHub (theo kế hoạch GĐ1).

## 2026-10-24 — Giai đoạn 2: giao diện PWA + backend bổ sung + triển khai nội bộ ✅

Người dùng yêu cầu "làm luôn tất cả 1 lượt": giao diện đầy đủ, backend
bổ sung, cài dịch vụ chạy nền, tài khoản Admin đầu tiên, kiểm thử,
tài liệu và đẩy GitHub — trong một đợt.

### Đã làm

- **Backend bổ sung** (`webapp/app.py`, `webapp/db.py`; version
  0.2.0): upload multipart thuần stdlib (`cgi`) kèm tạo việc
  (`POST /api/tasks`) và gắn thêm (`POST /api/uploads`,
  `POST /api/tasks/<code>/files`), lưu đúng `data/files/<MÃ VIỆC>/`
  của bot, `file_ids` lưu tên file, giới hạn **200MB/file**; tải file
  qua `GET /api/files/<code>/<filename>` (kiểm quyền, chống path
  traversal, Range); phát video nháp
  `GET /api/outputs/<id>/draft-video`.
- **Thao tác thẻ kênh** `POST /api/outputs/<id>/<action>`: submit,
  approve, reject (bắt buộc lý do), revise, cancel, publish (chỉ ghi
  lệnh `publish_requested`; Facebook bắt buộc target profile/page,
  thiếu → 422 + `pending_choice`; Admin đăng việc của mình tự qua
  duyệt `auto=admin_own`; không tự lật Đã đăng), publish-abort,
  schedule/schedule-abort/unschedule (giờ ISO/mẫu bot/preset, cảnh
  báo trùng <1 giờ không chặn), retract (Facebook →
  `retract_requested`, kênh khác thu hồi trong hệ thống). Tên audit,
  chuyển trạng thái và ma trận quyền bám đúng `handlers.py` +
  `roles.py` của bot; sai quyền → 403 + audit `denied_*`.
- **Các API mới**: `GET /api/review-queue`, `GET /api/scheduled`,
  `GET /api/stats/export` (CSV BOM UTF-8 + xlsx dùng lại
  `stats.py`), `GET /api/notifications` +
  `POST /api/notifications/read` (suy từ outputs/audit; đã đọc lưu ở
  bảng mới `web_notification_reads`; cộng thêm bảng `web_meta`),
  `POST /api/auth/change-password`, `PATCH /api/users/<id>/role`,
  `POST /api/users/<id>/revoke`.
- **Giao diện PWA** (`webapp/static/`): vanilla JS không build step,
  đủ 9 màn hình theo thiết kế đã chốt (Đăng nhập; Tổng quan; wizard
  Giao việc 3 bước có tải tệp + xem trước, nút kênh icon/tên, bỏ
  chọn thành ❌, nút "🚀 Chốt! Gửi Muse"; Danh sách việc có tìm
  kiếm/lọc; Chi tiết việc + thẻ kênh từng kênh đúng chuẩn 1 icon/dòng,
  modal chọn nơi đăng Facebook; Chờ duyệt; Lịch đăng; Thống kê biểu
  đồ SVG + xuất CSV/Excel; Người dùng & phân quyền; Thông báo có
  badge). Điều hướng: sidebar trên máy tính, thanh dưới trên điện
  thoại. `manifest.webmanifest` + service worker cache vỏ app (không
  cache API) + icon tự sinh; tên app "Giao Việc IAICT".
- **Triển khai nội bộ**: systemd service `webapp-giao-viec` (unit
  trong repo, cài vào `/etc/systemd/system/`), cổng 8790,
  `Restart=on-failure`, `EnvironmentFile` root-only mode 600 chỉ
  chứa proxy env — đã `enable --now`, kiểm chứng `/api/health` 200
  và trang chủ 200 qua 127.0.0.1:8790. Quy trình khôi phục sau khi
  máy bị thay mới đã ghi vào README.
- **Tài khoản Admin đầu tiên**: gắn email + SĐT của chủ dự án vào
  đúng tài khoản Admin Telegram hiện có (không tạo dòng mới, không
  ghi đè ai khác); mật khẩu tạm sinh ngẫu nhiên, bàn giao ngoài tài
  liệu; đã tự kiểm chứng đăng nhập bằng cả email và SĐT qua API trên
  service thật (`/api/auth/me` → role admin) rồi đăng xuất.

### Kiểm chứng

- Test webapp: **37/37 đạt** (bổ sung test cho PWA assets, upload +
  tải file + Range + giới hạn 200MB, từng thao tác thẻ kênh kèm 403
  và audit đúng tên, review-queue, scheduled, export CSV có BOM +
  xlsx, notifications + đánh dấu đã đọc, change-password,
  PATCH role/revoke, draft video streaming). Test bot: **215/215**,
  service bot vẫn `active`.
- **Lái thử bằng HTTP thật trên service**: đăng nhập Admin → tạo
  việc **CV-0013** kèm upload 1 ảnh mẫu (outputs website + facebook
  đúng kênh, file nằm trong `data/files/CV-0013/`) → gắn nháp qua
  botctl như luồng Muse thật → bấm Đăng kênh Website: ghi đúng
  audit `approve_output auto=admin_own` + `publish_requested`, trạng
  thái dừng ở APPROVED_WAITING (không tự nhận Đã đăng) → thống kê
  phản ánh 13 việc. CV-0013 là việc lái thử, để nguyên cho chủ dự án
  xem/hủy.

### Điểm tự chốt (chờ người dùng duyệt lại)

1. Upload chọn **cả hai điểm vào** (kèm tạo việc + gắn thêm sau) —
   sạch hơn một endpoint tạm vì không sinh trạng thái lơ lửng.
2. Parse multipart bằng module `cgi` của stdlib (Python 3.12 còn
   dùng được; khi lên 3.13+ sẽ cần thay bằng parser tự viết).
3. Thông báo GĐ2 là hộp thư trong app suy từ trạng thái/audit;
   Web Push thật để GĐ3 như lộ trình.
4. Service webapp bind `0.0.0.0:8790` (nội bộ) — tên miền + HTTPS
   thuộc GĐ4.

### Còn lại

- **SRS 1.1**: tổng hợp TD-0006 vào SRS.md ở bước sau (theo quy
  trình THAY-DOI.md).
- **GĐ3**: Web Push thật + hoàn thiện quản lý người dùng/tổng kết.
- **GĐ4**: tên miền + HTTPS, chạy song song rồi tắt dần bot.
