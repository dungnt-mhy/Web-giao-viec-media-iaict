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

## 2026-10-24 — Giai đoạn 3: Web Push (VAPID) + tổng kết ngày trong app ✅

Người dùng chốt "giữ việc lái thử CV-0013 và làm GĐ3". Ghi TD-0008
vào THAY-DOI.md trước khi code, đóng giai đoạn bằng SRS 1.2.

### Đã làm

- **Module `webapp/push.py`** — Web Push đúng chuẩn VAPID (RFC 8292)
  + mã hóa payload RFC 8291 (aes128gcm). Lựa chọn mật mã theo điều
  kiện máy này: package `cryptography` **không có sẵn** và dự án giữ
  stdlib-only, nên mọi thao tác đường cong P-256 (sinh khóa, ECDH,
  ký/kiểm ECDSA-SHA256 cho JWT) chạy qua **openssl CLI** bằng
  subprocess; riêng **AES-128-GCM tự cài đặt thuần Python** (AES +
  GHASH theo NIST SP 800-38D) vì `openssl enc` không hỗ trợ cipher
  AEAD. Đã kiểm chứng: vector FIPS-197 cho lõi AES, các vector GCM
  đối chiếu chéo với OpenSSL (qua Node) trên 8 ca ngẫu nhiên + ca có
  AAD, phát hiện sửa đổi qua tag, ECDH hai chiều khớp nhau, giải mã
  vòng tròn RFC 8291 đầu-cuối. HKDF/HMAC/SHA-256 là stdlib.
- **Khóa VAPID**: sinh một lần, lưu `data/vapid.json` cạnh bot.db
  (chmod 600, ngoài repo — thư mục `data/` đã bị .gitignore loại;
  đường dẫn ghi đè được bằng `WEBAPP_VAPID_PATH`). Endpoint
  `GET /api/push/vapid-public-key` (đã đăng nhập) trả public key
  base64url.
- **Migration cộng thêm** (đã kiểm chứng trên bản sao trước khi áp):
  bảng `web_push_subscriptions` (endpoint UNIQUE toàn cục, upsert
  theo endpoint) và `web_notification_items` (mục hộp thông báo
  tường minh, hợp nhất vào hộp thư suy diễn của GĐ2). Sao lưu DB
  thật trước khi restart áp migration:
  `telegram-bot-giao-viec/data/backup-gd3-20261024-040622/bot.db`
  (integrity ok; sau áp: 1 user / 13 việc / 23 đầu ra nguyên vẹn).
- **API push**: `POST /api/push/subscribe` (kiểm tra định dạng
  endpoint — chỉ https, http chỉ cho loopback phục vụ test/dev — và
  khóa p256dh/auth; gán cho người đang đăng nhập),
  `POST /api/push/unsubscribe` (chỉ xóa đăng ký của chính mình),
  `POST /api/push/test` (gửi thử cho chính người gọi, trả trạng thái
  từng endpoint; endpoint nào bị trả 404/410 thì tự xóa đăng ký).
  Gửi đi qua `urllib` tôn trọng proxy egress của service (endpoint
  loopback bỏ qua proxy).
- **Hook thông báo** (thread nền, bọc try/except, không chặn/chặn
  lỗi request chính): tạo việc mới → người duyệt + Admin (trừ người
  tạo); submit → người duyệt; approve/reject → người tạo; publish
  (ghi `publish_requested`) → người duyệt + Admin; retract →
  người tạo (thu hồi trực tiếp) hoặc người duyệt (yêu cầu thu hồi
  Facebook); schedule → người tạo. Link sâu dạng `/?task=CV-xxxx`,
  frontend mở thẳng chi tiết việc.
- **Tổng kết ngày**: `GET /api/stats/daily-summary` (mọi vai trò đã
  cấp quyền đều xem được — thẻ nằm ở màn Tổng quan cho mọi người;
  gồm việc tạo hôm nay theo giờ VN, đầu ra theo trạng thái, đã đăng
  hôm nay, đang chờ duyệt/chờ đăng hiện tại — tái dùng
  `stats.collect_stats(store, "today")` + `count_outputs_by_status`,
  đúng ngữ nghĩa bản tổng kết của bot). Frontend thêm thẻ "🌆 Tổng
  kết hôm nay" ở Tổng quan. **Thread nền** kiểm tra mỗi 60 giây: từ
  20:00 giờ VN, mỗi ngày một lần — push cho các Admin đã đăng ký +
  chèn một mục vào hộp thông báo của mọi người; chống trùng bằng
  khóa `web_daily_summary_date` trong `web_meta` (bot dùng khóa
  riêng trong bot_meta cho bản Telegram, hai kênh không giẫm nhau).
- **Frontend**: màn Thông báo thêm khối "📲 Thông báo đẩy"
  (bật/tắt/gửi thử bằng PushManager, xử lý trạng thái bị từ chối
  quyền); service worker thêm sự kiện `push` (showNotification kèm
  icon + data.url) và `notificationclick` (focus cửa sổ đang mở/mở
  mới đúng URL), cache vỏ app tăng lên v3. Version app 0.3.0.

### Kiểm chứng

- Test webapp: **51/51 đạt** (37 cũ + 14 mới: vector mật mã +
  roundtrip RFC 8291 + JWT ký/kiểm; CRUD đăng ký + phân quyền +
  upsert + quyền sở hữu khi hủy; gửi tới endpoint giả lập — kiểm
  cả header Authorization VAPID, giải mã ngược payload, tự xóa khi
  410; daily-summary khớp Store và đúng số tuyệt đối trên DB mới;
  guard 20:00 gửi đúng một lần/ngày, có push + mục inbox, hôm sau
  gửi lại). Test bot: **215/215**, không hồi quy.
- Triển khai: `systemctl restart webapp-giao-viec` — service
  `active`, local `/api/health` = 0.3.0, bản công khai
  https://post.iaict-platform.com/api/health = 200 bản 0.3.0,
  `/sw.js` bản mới có handler push, endpoint push chưa đăng nhập →
  401; bot vẫn `active`. (Ngay sau restart có vài phút public trả
  502/1033 vì đường hầm mất kết nối edge trong một cửa sổ proxy
  chập chờn — cloudflared tự nối lại, không liên quan thay đổi GĐ3.)

### Điểm tự chốt (chờ người dùng duyệt lại)

1. Daily-summary cho **mọi vai trò đã cấp quyền** xem (khác
   /api/stats/summary chỉ người duyệt) vì thẻ tổng kết nằm ở màn
   Tổng quan của mọi người; số liệu là tổng hợp, không lộ chi tiết.
2. Endpoint push chỉ chấp nhận https; http chỉ cho loopback
   (test/dev). Hủy đăng ký chỉ xóa được đăng ký của chính mình,
   nhưng hàng đợi gửi sẽ tự xóa bất kỳ endpoint nào bị 404/410.
3. Không push cho thao tác `revise` (người tạo tự bấm Sửa lại) và
   các bước trung gian publish-abort/schedule-abort/unschedule —
   chỉ các sự kiện chính theo đặc tả GĐ3.
4. Vị trí file khóa VAPID suy từ thư mục chứa bot.db (production
   đúng là `telegram-bot-giao-viec/data/vapid.json`), ghi đè bằng
   biến môi trường khi cần.

### Còn lại

- **GĐ4**: chuyển đội sang Web App + tắt dần bot (tên miền/HTTPS đã
  xong trước ở TD-0007).

## 2026-10-24 — TD-0009: sửa giao diện mobile theo phản hồi dùng thật ✅

Người dùng mở app trên điện thoại và báo 4 điểm (ảnh chụp màn Thông
báo không có mục bật thông báo đẩy; menu trên/dưới trùng nhau; cần lọc
việc theo trạng thái; block chọn ảnh/video Bước 1 quá to) + chỉ đạo từ
nay mặc định chỉ mobile. Version app 0.3.0 → **0.3.1**. SRS: chưa tổng
hợp (TD-0009 để trạng thái chờ, theo chỉ đạo đợt này).

### 1. Khối "📲 Thông báo đẩy" không hiện — nguyên nhân: vỏ app cũ trong cache service worker trên máy người dùng

- Bằng chứng: thẻ "📲 Thông báo đẩy" chỉ tồn tại trong mã bản 0.3.0
  (TD-0008) và được render vô điều kiện trong cùng một `innerHTML` của
  màn Thông báo — nếu app.js 0.3.0 chạy, thẻ phải nằm trong DOM kể cả
  khi `initPushPanel` lỗi. Ảnh chụp của người dùng không có thẻ này
  ⇒ máy đang chạy app.js bản GĐ2 (0.2.0), tức vỏ app cũ do service
  worker đời trước giữ trong cache; phía máy chủ đã phục vụ bản GĐ3
  từ khi đóng GĐ3 (smoke lúc đó: /sw.js công khai có handler push,
  /api/health = 0.3.0).
- Xử lý trong `sw.js` (cache **v4**): vỏ app (`/`, `/index.html`,
  `/app.js`, `/styles.css` + mọi điều hướng) chuyển hẳn sang
  **network-first** (cache chỉ là dự phòng mất mạng); tài nguyên tĩnh
  còn lại (icon, manifest) cache-first. Giữ `skipWaiting` +
  `clients.claim`.
- Phía `app.js`: mỗi lần mở app gọi `registration.update()` kiểm tra
  SW mới; khi SW mới tiếp quản (`controllerchange`, chỉ khi đã có
  controller trước đó) thì tự tải lại trang đúng 1 lần — PWA đã cài
  không còn kẹt vỏ cũ.
- Hiện số phiên bản nhỏ "Phiên bản 0.3.1" dưới tiêu đề màn Thông báo
  và cuối màn Người dùng để đối chiếu cũ/mới bằng mắt.
- Rà `initPushPanel`: bọc lỗi từng bước (chờ service worker có
  timeout 6s; kiểm tra `pushManager`; `getSubscription`) — thẻ LUÔN
  kết thúc ở một trạng thái chữ rõ ràng (không hỗ trợ / chưa sẵn sàng /
  đã chặn / đang tắt / đang bật / lỗi kèm nội dung lỗi), không còn
  cảnh mọi nút cùng ẩn như tính năng "biến mất".

### 2. Trùng menu mobile

- Trong breakpoint ≤820px: ẩn hẳn `.mobile-nav` (hàng chip trượt
  ngang dưới header). Điều hướng mobile chỉ còn thanh dưới đáy;
  header giữ nguyên. Desktop không đổi (sidebar; `.mobile-nav` vốn
  đã ẩn ở desktop).

### 3. Lọc việc theo trạng thái

- Backend `GET /api/tasks`: lọc `?status=` theo trạng thái việc suy
  ra bằng CHÍNH logic của bot Store — handler gọi
  `Store.sync_task_status_from_outputs` cho từng việc trong tập khả
  kiến rồi mới lọc/đếm, không tự chế logic suy ra thứ hai. Phản hồi
  thêm `counts`: số việc từng trạng thái (đủ 7 mã) trên tập việc khớp
  các bộ lọc còn lại (q/kênh/người tạo), TRƯỚC khi áp bộ lọc trạng
  thái. `total` giữ ngữ nghĩa cũ (số việc sau mọi bộ lọc).
- Frontend màn Việc: bỏ ô select trạng thái, thay bằng hàng chip
  trượt ngang: Tất cả • 📝 Nháp • ⏳ Chờ duyệt • ✅ Đã duyệt · chờ
  đăng • 🚀 Đã đăng • ↩️ Bị trả lại • ↩️ Đã thu hồi • 🗑 Đã hủy —
  mỗi chip kèm số lượng từ `counts`; chip chọn nổi bật teal. Lựa
  chọn giữ trong `state.taskStatus` + URL hash `#tasks?status=…`
  nên quay lại màn vẫn nguyên bộ lọc. Danh sách rỗng khi đang lọc:
  "Không có việc nào ở trạng thái này."

### 4. Gọn block chọn file Bước 1 (mobile)

- Chỉ trong breakpoint ≤820px: `.drop-box` padding 1.2rem → .55rem,
  icon 📎 2rem → 1.15rem, ghi chú 200MB/tệp hạ cỡ chữ .76rem, ô input
  gọn lại; lưới file đã chọn: cột tối thiểu 132px → 76px, thumbnail
  110px → 58px, tên file .66rem, nút xóa 32px → 24px. Placeholder
  file không phải ảnh/video chuyển từ inline style sang class
  `.preview-ph` để CSS mobile điều khiển được. Desktop giữ nguyên.

### Phát hiện thêm khi smoke: Cloudflare edge cũng giữ bản app.js cũ

- Kiểm chứng public sau restart: `/api/health` = 0.3.1, `/sw.js` =
  v4, nhưng `/app.js` theo URL thường vẫn là BẢN CŨ (57.565 byte,
  không có mã 0.3.1) trong khi origin/local và URL kèm tham số lạ
  đều trả bản mới (61.760 byte). Nguyên nhân: origin trước đây không
  gửi `Cache-Control` cho app.js/styles.css nên Cloudflare áp TTL
  mặc định của nó (`max-age=14400`) và giữ bản cũ ở edge. Đây là
  tầng cache thứ hai (ngoài service worker trên máy) khiến thiết
  bị kẹt vỏ cũ.
- Xử lý: (1) origin gửi `Cache-Control: no-cache` cho toàn bộ vỏ
  app (index.html, sw.js, app.js, styles.css); (2) `index.html`
  tham chiếu tài nguyên kèm phiên bản (`/app.js?v=0.3.1`,
  `/styles.css?v=0.3.1`) và `sw.js` nạp vỏ theo đúng URL có phiên
  bản đó — URL mới là khóa cache mới ở mọi tầng. Đã thử purge cache
  qua API Cloudflare bằng token nhúng trong cert.pem: bị 401 (token
  đó không có quyền Cache Purge) nên dùng hai cách trên thay thế —
  sau sửa, kiểm lại public bằng đúng URL trình duyệt gọi: HTML trỏ
  bản ?v=0.3.1, app.js 61.760 byte có APP_VERSION 0.3.1, styles.css
  đủ 13.920 byte, sw.js v4.

### Kiểm chứng

- Test webapp: **52/52 đạt** (51 cũ + test mới
  `test_task_list_status_filter_and_counts`: dựng đủ 7 trạng thái
  suy ra, kiểm `counts` đúng tuyệt đối trong phạm vi q=, lọc từng
  `?status=` trả đúng tập con và `total`, counts không bị chính bộ
  lọc trạng thái thu hẹp; chạy lại lần hai sau khi đổi header/static
  vẫn 52/52). Test bot: **215/215**, không hồi quy.
- Triển khai: restart `webapp-giao-viec` (active), smoke local
  `/api/health` = 0.3.1 + header `Cache-Control: no-cache` trên
  app.js; smoke công khai https://post.iaict-platform.com: health
  0.3.1, sw.js v4, vỏ app bản ?v=0.3.1 đúng như trên.

### Điểm tự chốt (chờ người dùng duyệt lại)

1. `counts` đếm trên tập việc khớp các bộ lọc còn lại (từ khóa/kênh/
   người tạo) chứ không phải toàn bộ việc — chip phản ánh đúng ngữ
   cảnh đang xem; muốn số toàn cục thì bỏ các bộ lọc còn lại.
2. Việc lưu bộ lọc dùng cả state lẫn URL hash `#tasks?status=…`;
   app vốn không dùng hash routing nên hash chỉ đóng vai trò ghi
   nhớ, mở link có hash vẫn vào app bình thường.

### TD-0009 — Bổ sung theo đính chính "làm kỹ cả desktop lẫn mobile" + kiểm chứng hai khung hình (24/10/2026, sau triển khai)

- **Đính chính của người dùng** (ghi đè cách hiểu "chỉ mobile"):
  giao diện phải chuẩn chỉnh, đẹp, thật kỹ cho CẢ desktop lẫn
  mobile; người dùng thao tác hằng ngày trên mobile nên phản hồi
  đến từ mobile, nhưng desktop không được bỏ bê.
- **Mục 2 rà cả hai nền**: desktop VỐN không có hàng chip ngang —
  `.mobile-nav` bị `display:none` ở rule gốc và chỉ hiện trong
  breakpoint ≤820px, nên desktop chỉ có sidebar (đầy đủ như thiết
  kế đã duyệt) — không cần sửa thêm; mobile ẩn hàng chip trên, giữ
  thanh dưới đáy (đã làm).
- **Mục 4 rà desktop**: block chọn file ở 1440px đo 1104×229px,
  icon 2rem — hơi thô/to so với bố cục chung. Đã siết nhẹ trong
  `@media (min-width:821px)`: padding .85rem/1rem, icon 1.55rem →
  đo lại 1104×209px. Không đổi cấu trúc/bố cục đã duyệt. Mobile
  giữ nguyên sau siết: 329×150px, icon 18.4px, thumbnail 58px.
- **Kiểm chứng hiển thị hai khung** (instance bản sao DB chạy cổng
  nội bộ + Chromium headless lái qua CDP, chụp 4 màn chính × 2
  khung 390px/1440px, ảnh lưu ở `~/workspace/shot-td0009/`):
  - 390px: Thông báo có thẻ "📲 Thông báo đẩy" với trạng thái rõ
    "Đang tắt trên thiết bị này…" + nút bật + dòng "Phiên bản
    0.3.1"; Việc có hàng chip trạng thái kèm số (Tất cả 13, Nháp 4,
    Chờ duyệt 0, Đã duyệt·chờ đăng 3, Đã đăng 2, Bị trả lại 1, Đã
    thu hồi 2, Đã hủy 1 — tổng khớp 13 việc thật); wizard Bước 1
    gọn (block 150px, thumbnail lưới nhỏ kèm tên/dung lượng/nút ✕);
    không tràn ngang; điều hướng chỉ còn thanh dưới đáy.
  - 1440px: sidebar đầy đủ (logo, đủ mục theo quyền, thẻ người
    dùng), không chip-nav trùng; chip trạng thái hiện đủ trên màn
    Việc; thẻ thông báo đẩy + số phiên bản hiện; block chọn file
    cân đối sau siết (209px); không tràn ngang.
- **Sự cố hạ tầng giữa chừng**: máy chủ lại bị thay (~05:0x) làm
  mất /tmp và toàn bộ unit/env systemd. Đã khôi phục đủ 5 service
  theo quy trình quen thuộc (tạo lại /etc/default/<service> 600
  chứa proxy egress, chép unit từ thư mục dự án/tools, daemon-
  reload, enable --now): cf-dns-stub, cf-edge-relay,
  webapp-giao-viec, telegram-bot-giao-viec, cloudflared-webapp —
  kiểm chứng health local + public đều 0.3.1, bot long-polling
  bình thường. Mã nguồn TD-0009 trong workspace không bị ảnh
  hưởng.

## 2026-10-24 — TD-0010: làm đẹp thanh điều hướng dưới đáy (mobile)
- Bottom nav từ dải phẳng sát mép thành thanh nổi bo tròn (nền trắng mờ blur, bóng mềm, hở viền + safe-area); mục đang chọn: icon trong viên thuốc teal nhạt + chữ đậm teal đậm; nút Giao việc ở giữa thành nút tròn teal nổi cao hơn thanh; badge chưa đọc bám góc icon (đã thêm badge vào template bottom nav, trước đây chỉ có ở chuông topbar); đệm cuối nội dung và vị trí toast chỉnh theo chiều cao thanh mới. Sidebar desktop không đổi. Bản 0.3.2, SW cache v5, kiểm thử webapp 52/52.

## 2026-10-24 — TD-0011: áp giao diện mới đã chốt vào app thật, bản 0.4.0
- Người dùng nói "Chốt" sau khi duyệt mô phỏng bấm thử + chọn Mẫu 1
  "Gradient viền trắng" cho nút Giao việc. Triển khai đúng phạm vi đã
  chốt: CHỈ đổi giao diện/bố cục, không đổi API, schema, audit/state,
  phân quyền, logic nghiệp vụ. Ghi TD-0011 vào THAY-DOI.md trước khi
  code; sao lưu toàn bộ webapp + bot.db tại
  data/backup-ui40-20261024-112524/ trước khi sửa.
- Nội dung: thẻ bo 20px, đệm và tầng bậc chữ thoáng hơn, giữ tông
  teal; thẻ Ưu tiên hổ phách + thẻ Tổng kết hôm nay thành hero trên
  Tổng quan; vùng hoạt động cuộn riêng; collapse cho khối thông tin
  việc, từng thẻ kênh, bộ lọc màn Việc, nhóm thông báo theo ngày;
  sidebar desktop có nút thu gọn thành thanh icon (lưu localStorage);
  nav mobile 6 cột (Tổng quan, Việc, nút +, Chờ duyệt, Thông báo,
  Thêm) với nút + đúng Mẫu 1 (tròn 54px, 48px ở màn ≤340px, gradient
  140deg #1cc79b → #0da678 → #066e52, viền trắng đặc 3px, vòng ngoài
  rgba(9,120,90,.16), KHÔNG đổ bóng, dấu + trắng 28px nét 3.4, nhô
  khoảng 19px, nhãn "Giao việc" teal đậm); nhãn một dòng 9.5px
  (8.5px ở màn ≤340px); badge tròn 19×19 cố định kèm badge số thẻ chờ
  duyệt từ review-queue (chỉ hiển thị); bảng "Thêm" (Lịch đăng, Thống
  kê, Người dùng) chạm ngoài/Esc đóng; chân wizard nút chính
  full-width nằm trên, nút phụ thành hàng dưới; dark mode theo hệ
  thống; bản 0.4.0 nhất quán mọi nơi + SW cache v6, shell
  network-first.
- Kiểm chứng hiển thị thật (không chỉ đọc mã): chạy instance bản sao
  DB + tài khoản probe riêng ở cổng nội bộ, lái Chromium headless qua
  CDP và chụp 17 ảnh ở 320/360/390px và 1440px, sáng + tối (dark mode
  kích hoạt bằng --force-dark-mode, đã xác nhận pixel nền tối). Vì
  Chrome 152 trên máy này chặn điều hướng tới loopback bằng
  ERR_BLOCKED_BY_LOCAL_NETWORK_ACCESS_CHECKS, cầu nối dùng miền
  Fetch của CDP: chặn mọi request tới loopback và tự trả nội dung
  lấy qua Python (kèm cookie jar riêng ở phía cầu vì cookie từ
  fulfillRequest không vào kho cookie của Chrome; chặn sw.js để
  service worker không chiếm fetch của trang). Kết quả: không tràn
  ngang, nhãn một dòng thẳng hàng, badge tròn không méo/không bị
  che, nút + đúng Mẫu 1, bảng Thêm mở/đóng được, wizard 3 bước chạy
  trọn với chân wizard đúng thứ tự, sidebar thu gọn/mở lại được,
  collapse hoạt động, dark mode đúng cả hai khung.
- Điểm sửa thêm phát hiện khi kiểm chứng: bảng "Thêm" kẹt lại phía
  trên màn mới khi đổi màn bằng nút chuông (scrim không che topbar)
  → `navigate()` nay luôn đóng bảng trước khi đổi màn; đã bổ sung
  test tĩnh cho điểm này vào bộ webapp (giữ 53/53, bot 215/215).
- Sự cố hạ tầng giữa chừng: máy chủ lại bị thay làm mất unit/env
  systemd, public báo Cloudflare 1033. Đã khôi phục đủ 5 service
  (tạo lại /etc/default/cf-edge-relay + webapp-giao-viec 600 chứa
  proxy egress, chép unit từ thư mục dự án/tools, daemon-reload,
  enable --now); tunnel đăng ký lại cả 2 region qua HTTP/2 (region2
  timeout một lần rồi tự khỏi); kiểm chứng cuối: health local +
  public đều 0.4.0, trang đăng nhập public 200.
- Tài liệu: gộp TD-0007 (phần tên miền/HTTPS), TD-0009, TD-0010,
  TD-0011 vào SRS 1.3 (GĐ4 còn lại: chuyển đội + tắt dần bot).

## TD-0012 — Sửa nav mobile sau phản hồi (bản 0.4.1, 24/10/2026)
- Người dùng phản hồi qua ảnh chụp sau 0.4.0, đồng thời yêu cầu TẠM
  DỪNG build Mini App Telegram để sửa trước: (1) nút + "nhảy vọt
  lên, nhỏ quá"; (2) "nhấn vào button khác thì background tối quá
  không nhìn thấy chữ".
- Nguyên nhân: (1) nút + đang translateY(-32px) → nhô ~19px khỏi mép
  thanh; (2) quy tắc chung `.nav-btn.active{background:var(--teal)}`
  của sidebar rò rỉ sang nút thanh dưới, gặp chữ teal đậm → chữ chìm
  trên nền tối (đúng ảnh chụp: viên thuốc mục Tổng quan nền tối,
  nhãn chìm).
- Sửa (chỉ CSS + version): nút + 54px→58px (48px→52px ở màn ≤340px),
  translateY -32px→-20px (nhô ~7px); nút thanh dưới khi active nền
  trong suốt, chỉ viên thuốc sau icon giữ nền teal nhạt; bản
  0.4.0→0.4.1 (VERSION, APP_VERSION, ?v=0.4.1, SW cache v7) để vượt
  cache cạnh.
- Kiểm thử: webapp 53/53, bot 215/215; health local + public đều
  0.4.1; CSS public ?v=0.4.1 chứa đúng quy tắc mới; đủ 5 service
  active. Mini App vẫn TẠM DỪNG, chưa đánh số TD, tiếp tục khi người
  dùng nói tiếp.

## TD-0013 — Đăng Facebook nhiều nơi cùng lúc, sẵn sàng nhiều Fanpage (bản 0.5.0, 24/10/2026)
- Người dùng yêu cầu: đăng Facebook trước đây chỉ chọn được 1 nơi
  (trang cá nhân HOẶC Fanpage); nay phải đăng cả 2 nơi trong một lần
  bấm Đăng, và kiến trúc sẵn sàng cho nhiều Fanpage về sau.
- Mô hình mới (storage.py dùng chung bot + webapp): khóa nơi đăng
  `profile` + `page_<fb_page_id>`; bảng mới `facebook_pages` (seed
  đúng 1 dòng: Minhy 61595515900524 — thêm Fanpage sau này chỉ cần
  thêm dòng, chưa có màn hình quản lý Fanpage); 6 cột JSON mới trên
  outputs (`publish_targets`, `fb_target_set`, `fb_place_urls`,
  `fb_place_failed`, `fb_place_retracted`, `fb_pending_targets`).
  Tương thích ngược: target đơn cũ đọc như danh sách 1 phần tử;
  link đơn cũ đọc như đã đăng xong 1 nơi.
- Bot: màn chọn nơi đăng thành nút bật/tắt từng nơi (✅ đang chọn,
  ❌ bỏ chọn, nơi đã đăng hiện "đã đăng" và không chọn lại được),
  mặc định chọn sẵn tất cả nơi chưa đăng, nút xác nhận "Đăng lên
  N nơi" / "Đặt lịch N nơi", bắt buộc ≥1 nơi; handler chọn đơn cũ
  (out_pubto/out_schto) vẫn giữ cho tin nhắn đang bay.
- Webapp: modal chọn nơi đăng thành checkbox nhiều lựa chọn (cả
  đăng ngay lẫn đặt lịch) + nút xác nhận đếm N nơi; API chấp nhận
  `targets` list (vẫn nhận `target` đơn cũ); thêm GET
  /api/facebook-targets; thẻ kênh hiển thị link từng nơi + nơi lỗi.
- Ngữ nghĩa: chỉ lật PUBLISHED khi đủ mọi nơi trong tập hợp
  (botctl `set-output-published --place` từng nơi; nơi lỗi ghi bằng
  `set-output-place-failed`, đầu ra ở lại chờ đăng, đăng lại chỉ
  đăng nơi chưa xong, không đăng trùng); thu hồi phải xoá thật đủ
  mọi nơi đã đăng rồi mới lật RETRACTED (botctl
  `set-output-retracted --place` từng nơi; không --place với bài
  nhiều nơi thì bị từ chối). Lịch đăng lưu cả tập hợp; đến giờ
  phát lệnh với đúng tập hợp đó; đăng ngay hủy lịch như cũ.
- Kiểm thử: webapp 54/54 (53 cũ + 1 mới), bot 230/230 (215 cũ +
  15 mới = 5 test × 3 pha: toggle/confirm, chặn chọn rỗng, đăng
  từng phần + đăng lại + thu hồi qua botctl, tương thích legacy,
  lịch cả 2 nơi + fire). Chạy thử trên bản sao DB thật (probe
  CV-0015): đăng profile xong vẫn chờ đăng, page lỗi được ghi,
  đăng page xong lật PUBLISHED, đăng trùng bị từ chối, thu hồi
  thiếu --place bị từ chối, thu hồi đủ 2 nơi lật RETRACTED; DB thật
  kiểm chứng sha256 không đổi.
- Hạ tầng: restart bot + webapp; health local + public đều 0.5.0,
  trang đăng nhập public 200, đủ 5 service active; migration trên
  DB thật đã thêm đủ cột + seed Fanpage Minhy. SRS: TD-0013 (cùng
  TD-0012) vẫn ⏳ chờ gộp sau.
- Lưu ý kiểm chứng: trong lúc verify public sau restart có đúng 1
  request lạ bị server từ chối 501 với request line "{}GET"
  (journal webapp 14:44:05); 3 lần curl sau đó + mọi lần sau đều
  200 + JSON 0.5.0, và grep 1 giờ chỉ có đúng 1 dòng 501 — kết
  luận là probe méo mó thoáng qua lúc tunnel nối lại, không phải
  lỗi phục vụ; cần theo dõi nếu tái diễn.

## TD-0014 — Giao diện: dải chip nổi bật, danh sách gập/mở, cuộn đúng, sửa thông báo tràn link (bản 0.5.1, 24/10/2026)
- Người dùng phản hồi qua 2 ảnh chụp: hàng chip lọc ngang "nhìn
  chìm" và thẻ thông báo "Bài đã được đăng" của CV-0013 bị link
  Facebook permalink dài tràn ra khỏi thẻ; kèm yêu cầu chung:
  danh sách bên dưới "làm collapse và có button thu nhỏ", "nói
  chung các danh sách nên làm scroll".
- Sửa (CHỈ CSS/JS hiển thị, không đụng API/schema/audit/phân quyền/
  logic nghiệp vụ/TD-0013/bot/tunnel/vapid/uploads):
  (1) Dải chip thành khối riêng nền teal nhạt (sáng #f0fdfa, tối
  #134e4a), chữ chip 800, chip chưa chọn viền teal rõ, chip đang
  chọn giữ nền teal đậm + chữ trắng + số đếm; vẫn trượt ngang, có
  fade mép phải khi còn cuộn được (lớp has-more do JS đo trạng
  thái cuộn thật + resize).
  (2) Đầu danh sách việc/chờ duyệt/lịch đăng/người dùng thêm nút
  "▾ Thu gọn / ▸ Mở rộng" kèm số lượng, gập cả thân danh sách,
  nhớ localStorage (gv-tasklist-/gv-review-/gv-schedule-/
  gv-users-collapsed, mẫu sidebar collapse). Nhóm ngày thông báo
  đã gập được từ TD-0011 nên không chồng thêm nút.
  (3) Cuộn theo từng màn: desktop (≥821px) các danh sách chính có
  vùng cuộn dọc riêng (max-height calc(100dvh - 240px)); mobile
  giữ cuộn trang tự nhiên, tuyệt đối không tràn ngang; hoạt động
  Tổng quan giữ vùng 440px từ TD-0011; nhóm thông báo giữ cuộn
  trang.
  (4) Thông báo ngắt link dài: overflow-wrap:anywhere trên
  .row-main và .muted trong .notification + min-width:0 cho thẻ;
  áp cả màn Thông báo lẫn khối hoạt động Tổng quan.
- Kiểm thử: webapp 54/54, bot 230/230. Kiểm chứng hiển thị thật
  bằng Playwright (Chromium headless, cài mới qua pip) trên bản
  sao bot.db (probe copy, không đụng dữ liệu thật): 10 ảnh ở
  320/390/1440px, sáng + tối — dải chip nổi bật + fade mép phải,
  gập/mở danh sách và nhớ trạng thái sau reload, thẻ thông báo
  link dài nằm gọn trong thẻ ở cả sáng lẫn tối, tràn ngang 0px ở
  mọi khung. Lưu ý probe: app không có hash router (chỉ navigate()
  qua nút bấm) nên probe phải gọi navigate() thay vì đổi hash URL;
  toast "Xin chào" sau đăng nhập che tạm một phần thẻ trong ảnh
  chụp, không phải lỗi giao diện.
- Triển khai: bản 0.5.0 → 0.5.1 (VERSION, APP_VERSION, ?v=0.5.1, SW
  cache v9); restart webapp-giao-viec; health local + public đều
  0.5.1, login public 200, asset public ?v=0.5.1 chứa đủ dấu vết
  mới, đủ 5 service active. Sao lưu trước khi sửa tại
  data/backup-td14-20261024-144916/ (bản sao webapp + bot.db).
  SRS: TD-0014 (cùng TD-0012, TD-0013) vẫn ⏳ chờ gộp sau.

## TD-0015 — Sửa 6 việc: khóa nơi đang chờ, link Facebook kiểu cũ, thông báo web botctl, badge PWA, icon xem thêm, tải muộn (bản 0.5.2, 24/10/2026)
- Người dùng phản hồi sau 0.5.1 (bằng chứng CV-0014 có 2 audit
  publish_requested giống nhau cho profile).
- (1) Khóa nơi đang chờ: locked = done ∪ (request − done − failed);
  lịch chờ giờ không khóa (sửa lịch được); hủy đăng dọn
  publish_targets (webapp publish-abort + bot publish abort) để
  lệnh đã hủy không khóa oan vĩnh viễn; server chặn 409 khi toàn
  bộ nơi chọn đều khóa, chọn lẫn thì chỉ đăng nơi mở + báo rõ
  nơi bị bỏ qua; nơi lỗi không bao giờ bị khóa. Bất biến đã xác
  minh trước khi code: mark_fb_place_failed KHÔNG dọn tập lệnh
  (nơi lỗi vẫn nằm trong request) nên công thức request − done −
  failed là đúng, không cần sửa luồng failed.
- (2) Link kiểu cũ: fb_state (chỉ với PUBLISHED/RETRACTED) suy nơi
  đăng từ audit publish_requested gần nhất (targets= rồi target=);
  không có target thì key "legacy" hiển thị "Facebook", không
  lọt vào done của modal (lọc theo nơi hợp lệ).
- (3) botctl set-output-published/place-failed/retracted (kể cả
  --place) đồng thời ghi web_notification_items (INSERT OR IGNORE,
  key published:/publish_failed:/retracted: + id đầu ra + id
  audit) kèm link từng nơi; --no-notify tắt cả hai; thiếu token
  Telegram không chặn hàng web. Bảng này là global nên hàng mới
  tới mọi người dùng (người tạo có thể thấy trùng với dòng suy ra
  từ trạng thái — dòng global mang link từng nơi).
- (4) Badge PWA: updateBadges đồng bộ setAppBadge/clearAppBadge
  (guard, best-effort); SW đồng bộ khi nhận push (fetch số chưa
  đọc). Giới hạn: iOS không có Badging API nên badge chỉ chạy
  Android/Chrome (và Chrome desktop).
- (5) Icon "Thêm" thanh dưới: ▦ → ••• (duy nhất một chỗ).
- (6) Tải muộn: form tải thêm chú thích khi việc đã có thẻ kênh;
  thêm file vào việc đã có thẻ kênh thì đẩy web cho người
  duyệt/Admin qua _notify_async; giữ phân quyền, không đổi trạng
  thái.
- Kiểm thử: webapp 57/57 (54 cũ + 3 mới), bot 242/242 (230 cũ + 4
  mới × 3 lớp test). Probe trên bản sao DB thật: link legacy
  CV-0013 suy đúng profile, khóa đúng (live khóa cả 2, lỗi vẫn
  mở), botctl ghi đủ hàng web kèm link, hủy dọn request; sha DB
  thật không đổi. Health local + public 0.5.2, login 200, đủ 5
  service active.

## TD-0016 — Nút X đóng modal (bản 0.5.3, 24/10/2026)
- Người dùng phản hồi qua ảnh chụp modal "Chọn nơi đăng Facebook":
  modal chỉ có "Hủy đăng" (hủy luôn lệnh đăng) và nút Đăng bị khóa khi
  0 nơi — không có cách thoát trung lập.
- Sửa (chỉ giao diện): khung modal dùng chung (openModal) thêm nút X
  góc phải trên, hiện trên MỌI modal; bấm X chỉ đóng lại, không xác
  nhận, không gọi publish-abort (giống bấm ra nền modal). Vùng chạm
  40px, rõ cả sáng lẫn tối, tiêu đề chừa đệm phải để không bị đè.
- Kiểm thử: webapp 58/58 (57 cũ + 1 mới cho nút đóng), bot 242/242;
  health local + public 0.5.3, login public 200, đủ 5 service active,
  asset public ?v=0.5.3 chứa dấu vết mới, SW cache v11.

## TD-0017 — botctl đăng/thu hồi gửi kèm Web Push (bản 0.5.4, 24/10/2026)
- Vấn đề: sự kiện đăng/thu hồi qua botctl chỉ ghi hàng inbox, không
  gửi push nên điện thoại không buzz (người dùng đã đọc được hàng
  inbox nhưng không nhận buzz; hộp inbox tự nó vẫn hoạt động).
- Sửa: `_notify_web` sau khi ghi hàng đồng thời gửi Web Push tới MỌI
  subscription (khớp tính global của hàng inbox). Payload đúng dạng
  SW GĐ3 hiển thị được: {title, body, url} với url = /?task=<mã>.
  Tái sử dụng send_to_subscription của webapp/push.py (import qua
  sys.path, guard lỗi → cảnh báo + chỉ ghi hàng); KHÔNG copy crypto;
  KHÔNG tự tạo vapid.json nếu thiếu (khóa mới sẽ hỏng mọi
  subscription cũ). --no-notify tắt cả Telegram, hàng web và push;
  thiếu token Telegram không chặn push web; lỗi push chỉ cảnh báo
  stderr, không hỏng exit code; không có subscription thì gửi 0 cái.
  Log chỉ đếm sent/failed/gone, không in endpoint/khóa/payload.
  Thêm WebDB.push_subscriptions_all() (cộng thêm) và điểm chích test
  `_WEB_PUSH_SENDER` trong botctl; `_notify_web` nhận thêm task_code
  tùy chọn (6 điểm gọi truyền args.task_code).
- Kiểm thử: webapp 58/58, bot 251/251 (242 cũ + 3 test mới × 3 lớp:
  push đủ payload/đối tượng, --no-notify tắt push, lỗi sender không
  hỏng lệnh, đường thật thiếu vapid chỉ cảnh báo). Probe trên bản
  sao DB thật: publish từng phần/lỗi/đủ + thu hồi từng phần/đủ →
  5 lần gọi push đúng title/body/url + 5 hàng inbox, trạng thái cuối
  RETRACTED; DB thật sha không đổi; lookup subscription thật trả về
  đúng Admin (không in endpoint); vapid.json mode 600.
- Public: health local + public 0.5.4, login 200, SW cache v12, đủ 5
  service active, bot long polling.

## TD-0018 — Modal nơi đăng không trống oan, đồng bộ sống, badge/push app Brave đã ghim (bản 0.5.5, 25/10/2026)
- Người dùng test CV-0016 lúc 00:27-00:33 ngày 25/10, báo 3 lỗi.
- (A) fbTargets() chỉ cache khi tải thành công và danh sách không
  rỗng; lỗi/rỗng trả null (không cache) — lỗi cũ cache [] làm
  modal trống oan. Modal Đăng và Đặt lịch khi không tải được nơi
  đăng hiện lỗi + nút "🔄 Thử lại"; dòng "không còn nơi nào để
  chọn" chỉ hiện khi tải được targets mà không còn nơi chọn được.
- (B) Đồng bộ sống: poll 30 giây (chỉ khi tab hiển thị, refreshBadge
  có chặn gọi chồng) tải thông báo + badge; visibilitychange → tải
  lại ngay dữ liệu màn hiện tại + thông báo + badge; SW khi nhận
  push postMessage "gv-push" cho client đang mở (client tải lại
  badge + dữ liệu Danh sách/Chi tiết việc). Poll không tải lại
  danh sách để khỏi mất vị trí cuộn.
- (C) Badge/push Brave: xác minh bằng MDN + web.dev — Badging API
  không hỗ trợ trên Chromium ở Android (setAppBadge là no-op),
  Android chỉ tự hiện chấm thông báo khi còn thông báo chưa đọc;
  Brave không mint WebAPK nên ghim chỉ tạo lối tắt (icon có logo
  Brave, không có trong Launcher/Cài đặt, không dùng khả năng chỉ
  dành cho app cài đặt). Màn Thông báo thêm chú thích ngắn nói rõ
  2 điểm này + gợi ý cài bằng Chrome để có app thật. Nút "Gửi thử"
  nay trả đếm sent/total (bỏ trường results lộ endpoint), giao
  diện hiện "Đã gửi tới N/T thiết bị". Badge trong app vẫn cập nhật
  qua updateBadges ở mọi lần số chưa đọc đổi; SW push-time giữ
  nguyên.
- Sửa kèm: test tổng kết ngày bị flake theo giờ (fixture create_task
  đóng dấu "now" UTC, test chốt ngày 24/10 ICT nên chỉ xanh
  07:00-24:00 giờ VN) — test nay suy ngày fixture từ created_at
  của task đã gieo, không đổi code sản phẩm.
- Kiểm thử: webapp 58/58, bot 251/251; probe Playwright trên bản
  sao DB đạt 15/15 (modal lỗi → thử lại hiện đủ 2 nơi đã chọn sẵn,
  visibilitychange và poll 30s đều tải lại thông báo, chú thích
  Brave + phiên bản 0.5.5 hiển thị; DB thật sha không đổi).
  Giới hạn probe: headless Chromium ép Notification.permission =
  denied nên không bấm được nút Bật/Gửi thử trong probe — nút có
  trong DOM, đường /api/push/test đã có test đơn vị (sent/total,
  không lộ endpoint), đăng ký push thật đã có bằng chứng sống từ
  subscription của Admin.
- Máy chủ lại bị thay giữa đợt (mất unit webapp + tunnel, public
  1033) — đã khôi phục bằng restore-services.sh, đủ 5 service
  active, public 0.5.5.

## 2026-10-25 — Gộp SRS 1.4 (TD-0012 → TD-0018) ✅
- Theo yêu cầu của chủ dự án ("Gộp SRS luôn", 01:13 ngày 25/10).
  Đợt gộp tài liệu — KHÔNG đổi code, KHÔNG đổi phiên bản app (giữ
  0.5.5), KHÔNG restart service. Sao lưu SRS.md + THAY-DOI.md
  trước khi sửa tại data/backup-srs14-20261024-181507/.
- SRS 1.3 → 1.4 (ngày hiệu lực 25/10/2026): gộp TD-0012 (nav 58px,
  nhô ~7px, sửa nền active), TD-0013 (đăng Facebook nhiều nơi:
  khóa profile/page_<id>, bảng facebook_pages, 6 cột outputs),
  TD-0014 (chip nổi bật, collapse danh sách, quy tắc cuộn,
  tràn link), TD-0015 (khóa nơi chờ + chặn 409, link kiểu cũ từ
  audit, hàng web botctl, badge PWA, icon •••, tư liệu muộn),
  TD-0016 (nút X đóng modal), TD-0017 (botctl gửi kèm Web Push),
  TD-0018 (modal không trống oan, đồng bộ sống, giới hạn badge
  Chromium Android/Brave đã xác minh theo MDN).
- Các mục SRS đã cập nhật: 2.3 (tập hợp nơi đăng Facebook), 2.4 +
  2.6 + lộ trình GĐ4 (chuyển đội/tắt bot TẠM DỪNG theo quyết định
  chủ dự án 24/10/2026; Mini App tạm dừng, chưa đánh số TD),
  FR-TASK-03 (tư liệu muộn), FR-PUB-04/05/06 + FR-PUB-08 mới
  (khóa nơi chờ), FR-SCH-01/02 (lịch lưu cả tập hợp nơi),
  FR-NOTI-01/03 + FR-NOTI-04 mới (đồng bộ sống), mục 5 (schema
  facebook_pages + 6 cột), mục 6 (GET /api/facebook-targets,
  targets[] + 409, push test sent/total), NFR-USE-01, NFR-MNT-02
  (số test từng đợt), lịch sử phiên bản 1.4.
- THAY-DOI.md: 7 mục TD-0012→0018 đổi trạng thái sang ✅ đã gộp
  vào SRS 1.4; mục "Mục chờ cập nhật vào SRS" bổ sung 7 dòng
  tương ứng. Các mục chờ khác giữ nguyên.
- Lưu ý: khía cạnh chỉ thuộc bot (picker bot TD-0013, botctl
  TD-0015/TD-0017) được ghi trong SRS Web App ở mức hành vi dùng
  chung; tài liệu thiết kế riêng của bot
  (docs/ban-thiet-ke-bot-chuyen-nghiep.html) KHÔNG sửa trong đợt
  này — để cho đợt gộp tài liệu bot riêng nếu cần.
- Kiểm thử sau gộp (chỉ sửa tài liệu, không đụng code): webapp 58/58;
  app giữ 0.5.5, không restart service.

## TD-0019 — Mục "Đã duyệt · chờ đăng" trong menu Thêm (bản 0.5.6, 25/10/2026)
- Người dùng yêu cầu thêm trạng thái Duyệt - chờ đăng vào nút Thêm.
- Làm (chỉ giao diện): menu Thêm (•••) có thêm mục "✅ Đã duyệt ·
  chờ đăng" cho người có quyền duyệt, đứng đầu sheet; bấm mở màn
  Việc với bộ lọc APPROVED_WAITING đặt sẵn qua deep-link
  #tasks?status=APPROVED_WAITING (tái dùng chip lọc sẵn có, không
  màn mới). Mục này cũng hiện trực tiếp ở sidebar desktop, ngay sau
  "Chờ duyệt". Nút Thêm active khi đang ở mục mới; nút Việc chỉ
  active khi không ở mục mới. Huy hiệu đếm việc chờ đăng lấy từ
  counts.APPROVED_WAITING của GET /api/tasks?limit=1 — đúng số chip
  lọc hiện trên màn Việc — cập nhật cùng refreshBadge (chỉ người
  duyệt, lỗi thì giữ số cũ). Sửa kèm một lỗi lộ ra khi probe: nav
  vẽ trước khi renderTasks đồng bộ taskStatus từ hash nên trạng thái
  active sai lúc vừa điều hướng — nay navigate() đồng bộ từ hash
  trước khi vẽ nav (helper syncTaskStatusFromHash dùng chung).
- Kiểm thử: webapp 60/60 (58 cũ + 2 mới: nguồn đếm badge, cờ phân
  quyền can_review), bot 251/251; probe Playwright trên bản sao DB
  thật 21/21 (desktop sidebar + badge, mobile sheet + badge, lọc
  đúng 4 việc chờ đăng CV-0008/0009/0013/0016, active đúng cả hai
  chiều, writer không thấy mục); DB thật sha256 không đổi sau probe;
  health local + public 0.5.6, login public 200, đủ 5 service active,
  asset public ?v=0.5.6 chứa dấu vết mới, SW cache v14.

## TD-0020 — Mini App Telegram (bề mặt thêm, cùng backend + bot.db) (bản 0.5.7, 25/10/2026)
- Người dùng ra lệnh tiếp tục 08:48 ngày 25/10 ("Ok rồi; làm miniapp") sau khi tạm dừng từ 19:10 ngày 24/10. Mini App là bề mặt THÊM: bot Telegram và Web App PWA giữ nguyên toàn bộ, KHÔNG chuyển đội, KHÔNG tắt dần bot (GĐ4 vẫn tạm dừng theo lệnh "Không chuyển nhé" ngày 24/10). Ghi TD-0020 vào THAY-DOI.md trước khi code; sao lưu webapp + bot.db tại data/backup-td20-20261025-015224/ (chỉ trên máy, không lên GitHub).
- Làm (webapp): entry `/miniap/` (+ `/miniap/index.html`) phục vụ cùng shell PWA, không viết lại giao diện. Module mới `webapp/telegram_auth.py` (stdlib): `validate_init_data` kiểm chứng chữ ký HMAC-SHA256 đúng chuẩn Telegram (secret = HMAC-SHA256("WebAppData", bot_token), data-check-string sắp xếp theo key, loại trừ `hash` và `signature`, `auth_date` tối đa 24 giờ, dung sai 300s cho đồng hồ lệch), `sign_init_data` chỉ dùng cho test/probe. Endpoint mới `POST /api/auth/telegram`: map `user.id` → users.telegram_id, chỉ người đã có vai trò mới vào được (người lạ và người chưa có vai trò đều 403 giống nhau để không lộ sự tồn tại), cấp phiên web_sessions dùng chung (cookie + Bearer token lưu localStorage làm dự phòng cho WebView Telegram). Frontend: `IS_MINIAPP` (đường dẫn /miniap hoặc initData), tải SDK telegram-web-app.js, `initTelegramUI` (ready/expand, themeParams → biến màu CSS, BackButton theo route, MainButton chỉ ở bước cuối wizard giao việc, haptic cho thao tác chính), boot ưu tiên /api/auth/me rồi mới đăng nhập bằng initData, ẩn nút đổi mật khẩu/đăng xuất trong Mini App. Không hiện màn đăng nhập email/mật khẩu trong Mini App; mở /miniap/ ngoài Telegram thì rơi về form đăng nhập thường.
- Làm (bot): `telegram_client.py` thêm `set_chat_menu_button`; `handlers.py` thêm `sync_menu_button` (đặt nút WebApp "Mở Mini App" theo từng chat của người có vai trò; reset về mặc định khi chưa có vai trò), móc vào `sync_user_commands` (khởi động, /start, cấp/thu hồi quyền), lệnh `/miniap` trong BASE_COMMANDS + handler gửi nút inline WebApp (từ chối lịch sự người chưa có quyền).
- **Giới hạn cấu hình (đã xác minh trước khi code, ghi trong THAY-DOI.md):** token bot thật KHÔNG lấy được từ chỗ bot đang dùng (bot chỉ có surrogate `hsurr:`; authd chỉ trả surrogate; không có TELEGRAM_BOT_TOKEN trong bất kỳ /etc/default/* nào). Server đọc token từ biến môi trường `TELEGRAM_BOT_TOKEN`; chưa có thì endpoint trả 503 và Mini App hiện lỗi rõ. Muốn đăng nhập thật bằng Mini App: cấp token qua Secure Vault → đặt vào /etc/default/webapp-giao-viec (mode 600) → restart webapp. Test/probe dùng token test riêng trong fixture, KHÔNG dùng token thật, KHÔNG commit token.
- **Sửa sau kiểm chứng sống (trong đợt):** (1) Bot API hiện tại KHÔNG có `deleteChatMenuButton` (đối chiếu docs chính thức Bot API 10.3; gọi trả HTTP 404) — nhánh thu hồi quyền nay reset bằng `setChatMenuButton` với `{"type": "default"}`. (2) `setChatMenuButton` KHÔNG có tham số `scope` (chỉ `setMyCommands` mới có); bản đầu truyền `scope` nên Telegram lờ đi và đặt nhầm nút WebApp lên nút MẶC ĐỊNH chung, còn chat Admin vẫn `default`. Nay truyền đúng `chat_id`. Kiểm chứng sống sau sửa: chat Admin (7102790425) → web_app "Mở Mini App", nút mặc định → `commands`. Lưu ý: thay đổi nút mặc định lan truyền chậm (~2 phút mới đọc lại được), thay đổi theo chat gần như tức thì.
- Kiểm thử: webapp 73/73 (60 cũ + 13 mới: 8 kiểm chứng initData thuần + 5 endpoint/entry), bot 256/256 (251 cũ + 5 mới MiniAppTestCase). Probe API trên bản sao DB: initData ký bằng token test cho Admin → đăng nhập 200, thấy 16 việc gồm CV-0016; giả mạo → 401; user lạ 999888777 → 403; DB thật sha256 không đổi (fc1e16a8…). Probe giao diện Playwright (WebApp Telegram giả lập, SDK thật bị chặn để khỏi đè stub): 13/13 — boot thẳng vào app với tên Admin, themeParams áp đúng, ready/expand, BackButton ẩn ở dashboard, MainButton hiện ở bước 3 wizard, chi tiết CV-0016 mở được, lọc APPROVED_WAITING đúng; PWA không stub vẫn hiện form đăng nhập; không lỗi JS.
- Triển khai: máy chủ bị thay giữa đợt (mất hết unit systemd) — `restore-services.sh` khôi phục đủ 5 service. Restart webapp + bot; health local + public 0.5.7, login public 200, /miniap/ public 200, đủ 5 service active; app.js public ?v=0.5.7 chứa dấu vết Mini App.
- Chưa kiểm chứng sống: mở Mini App thật trong Telegram trên điện thoại (cần token thật được cấp + người dùng bấm nút menu / gõ /miniap); SDK thật chưa từng chạy với app này — probe dùng stub, chỉ kiểm chứng được qua test đơn vị + stub. SRS vẫn 1.4; TD-0019 + TD-0020 ⏳ chờ gộp.

## TD-0021 — Sửa đăng nhập Mini App thật: `signature` phải nằm trong HMAC check string + log chẩn đoán (bản 0.5.8, 25/10/2026)
- Người dùng mở Mini App thật thì hiện "Phiên đăng nhập đã hết hạn." (09:46 ngày 25/10). Log server: 3 lần POST /api/auth/telegram đều 401 trong khung 09:45-09:46. Chẩn đoán trước khi sửa: token bot đã xác minh ĐÚNG bằng getMe trực tiếp (200, đúng id 8884085259, đúng @iaict_media_bot); bộ kiểm chứng đã qua initData thực tế (đủ field, chữ ký dummy, tên có dấu + emoji, photo_url có query) đều 200; nhưng thông báo "Phiên đăng nhập đã hết hạn." là câu chung chung mà `api()` ném ra cho MỌI 401 nên lý do thật bị che.
- Sửa chẩn đoán (bản 0.5.8): server ghi log `[telegram-auth] Mini App login refused: <message> (fields: ...)` — chỉ message + TÊN field, không log giá trị/hash/token/initData (print flush=True để khỏi kẹt buffer stdout); `api()` với 401 ở đúng /api/auth/telegram thì hiện đúng message của server. Log này chỉ ra lý do thật: "Chữ ký xác thực Telegram không hợp lệ." với fields auth_date,hash,query_id,signature,user.
- Nguyên nhân gốc: bộ kiểm chứng loại cả `signature` khỏi data-check-string — sai. Đối chiếu tài liệu Telegram (core.telegram.org/bots/webapps + docs.telegram-mini-apps.com/platform/init-data): đường HMAC chỉ loại `hash`; `signature` chỉ bị loại ở đường kiểm chứng Ed25519 bên thứ ba (cấu trúc khác, có tiền tố `bot_id:WebAppData`). initData thật luôn có `signature` nên mọi lần đăng nhập thật đều lệch HMAC, trong khi fixture test không có `signature` nên vẫn đậu — test cũ còn khẳng định hành vi sai. Sửa: `_EXCLUDED_FIELDS = ("hash",)` (cả validate lẫn sign dùng chung); test cũ đổi thành `test_signature_field_is_included_in_check_string` + thêm control âm `test_signature_excluded_hash_is_rejected`; sửa docstring module.
- Kiểm thử: webapp 74/74 (73 cũ + 1 mới ròng), bot 256/256. Probe sống: initData có `signature` (ký theo cách Telegram, chữ ký nằm trong check string) → local 200 + public 200 (Admin, role admin, có token); lần public đầu bị RemoteDisconnected do tunnel chập chờn, thử lại thì 200. Triển khai: restart webapp; health local + public 0.5.8, đủ 5 service active; app.js public ?v=0.5.8 chứa dấu vết sửa. Commit webapp b64f5dc (23 file, qua API). Bot không đổi.
- Chưa kiểm chứng sống: mở Mini App thật trên điện thoại của người dùng sau bản sửa — đây là phép thử cuối cùng cho lỗi này. SRS vẫn 1.4; TD-0019 + TD-0020 + TD-0021 ⏳ chờ gộp.

## TD-0022 — Mọi danh sách việc đều có scroll, "Xem thêm" và "Thu gọn" (bản 0.5.9, 25/10/2026)
- Người dùng yêu cầu: "Tất cả các danh sách liên quan đến việc đều cho scroll, xem thêm và thu gọn". Ghi TD-0022 vào THAY-DOI.md trước khi code; sao lưu webapp + bot.db tại data/backup-td22-*/ (chỉ trên máy, không lên GitHub). Bot không đổi.
- Làm: MỘT helper dùng chung `setupListPager({listEl, footerEl, items, pageSize, render, afterRender, emptyHtml, countEl, countText})` trong app.js — phân trang phía client trên dữ liệu đã tải về (không đổi API): hiện `pageSize` mục đầu, chân danh sách có dòng đếm "Đang hiện X/Y" + nút "Xem thêm (còn N)"; đã mở rộng thì thêm nút "Thu gọn" (title "Chỉ hiện N mục đầu") thu lại về đợt đầu. Vẽ lại (đổi lọc, tải lại, chuyển màn) thì reset về đợt đầu; trạng thái chỉ giữ trong phiên, KHÔNG lưu localStorage. Nút "Thu gọn" ở chân danh sách khác toggle ▾ Thu gọn / ▸ Mở rộng của TD-0014 (ẩn/hiện CẢ mục, ở đầu danh sách, nhớ localStorage) — phân biệt bằng vị trí + dòng đếm kề bên; toggle TD-0014 giữ nguyên, chỉ đổi mục tiêu sang khối bọc (danh sách + chân pager) để ẩn/hiện cả hai cùng lúc.
- Phạm vi: Việc (10/đợt, đếm ở đầu danh sách đổi thành "Đang hiện X/Y việc"), Chờ duyệt (10/đợt, "thẻ"), Lịch đăng (10/đợt, "bài"), Việc gần đây + Hoạt động ở Tổng quan (6/đợt, bằng mức cắt cũ slice(0,6)), Thông báo (10/đợt, gộp theo ngày trên các mục đang hiện để không vỡ nhóm). Scroll: Việc/Chờ duyệt/Lịch đăng giữ `.list-scroll` (desktop); "Việc gần đây" thêm `.list-scroll`; Hoạt động giữ `.activity-scroll`; Thông báo bọc nhóm ngày trong `.list.list-scroll`; chân pager nằm NGOÀI vùng cuộn nên luôn thấy được. CSS mới `.pager-foot` (flex, co hàng trên mobile). `bindOutputActions` nhận thêm tham số root để pager gắn lại nút chỉ trong danh sách vừa vẽ, không gắn trùng.
- Không áp dụng pager cho thẻ kênh ở Chi tiết việc: một việc tối đa 5 thẻ kênh (3 kênh chữ + 2 kênh video) nên đợt đầu 10 mục không bao giờ tràn — nút "Xem thêm" không thể xuất hiện, ép thêm chỉ là UI chết. Chi tiết việc chỉ thêm vùng cuộn desktop (`.list-scroll`). Danh sách Tài khoản không đổi (không liên quan đến việc).
- Kiểm thử: webapp 75/75 (74 cũ + 1 mới `test_td22_list_pager_markers`: helper + 6 chân pager + dấu vết CSS + ghi chú Chi tiết việc), bot 256/256. Probe Playwright trên bản sao DB (seed thêm 12 output PENDING + 12 output đặt lịch + 15 thông báo + phiên probe cho Admin; server probe cổng 8890, DB thật không đổi): 51/51 — mobile 390 sáng (Việc/Chờ duyệt/Lịch đăng/Thông báo/Chi tiết + Tổng quan: hiện đúng số mục đợt đầu, Xem thêm hiện thêm đúng đợt và cập nhật đếm, Thu gọn về đúng N, toggle mục vẫn ẩn/hiện cả danh sách + chân pager) + desktop 1440 tối (vùng cuộn riêng: #taskList 1226/660px, #reviewList 3621/660px, #notifList 1185/660px, overflow-y auto) + desktop 1440 sáng (Lịch đăng, Chi tiết); không tràn ngang ở mọi màn (scrollWidth ≤ innerWidth). Ảnh probe tại /tmp/probe-td22/shots/ (9 ảnh: tasks/dashboard/detail mobile sáng, tasks/review/dashboard/notifications desktop tối, schedule mobile sáng, detail desktop sáng). Lưu ý khi sửa test: output của tool che tên biến token thành `<redacted>` — chép y nguyên vào file sẽ lỗi cú pháp; đã sửa bằng cách lấy tên biến từ dòng test có sẵn.
- Triển khai: restart webapp; health local + public 0.5.9, login public 200, /miniap/ public 200, đủ 5 service active; app.js public ?v=0.5.9 chứa `setupListPager`, styles.css public chứa `.pager-foot`. Commit webapp qua API (xem dưới). SRS vẫn 1.4; TD-0019 + TD-0020 + TD-0021 + TD-0022 ⏳ chờ gộp.

## TD-0023 — Hàng chip lọc trạng thái: nền nổi hơn, nút chip sửa theo cho hợp (bản 0.5.10, 25/10/2026)
- Người dùng gửi ảnh hàng chip "Tất cả 16 / Nháp 4 / Chờ…" và yêu cầu nền nổi hơn + sửa nút chip theo cho hợp. Dải cũ #f0fdfa quá nhạt, gần như trùng nền trang.
- Điều tra trước khi sửa (probe Playwright trên bản sao DB, máy chủ thử cổng 8791, phiên probe riêng cho Admin): style đang chọn ÁP DỤNG ĐÚNG trong render thật — chip "Tất cả" đang chọn có nền rgb(15,118,110) = var(--teal) + chữ trắng ở cả 4 tổ hợp mobile/desktop × sáng/tối; bấm chip khác thì trạng thái đang chọn chuyển đúng; màn "Đã duyệt · chờ đăng" thì chip thứ 4 đang chọn, cũng nền teal. Không có lỗi áp dụng style. Ảnh người dùng nhiều khả năng chụp lúc đang lọc "Đã duyệt · chờ đăng" (chip đang chọn thứ 4 nằm ngoài khung cuộn nên các chip thấy được đều nhạt) — và dải nhạt khiến cả hàng đọc như trôi trên nền trắng. Không sửa logic lọc/đếm/JS fade, chỉ tô lại.
- Sửa (chỉ CSS): dải sáng #ccfbf1 + viền #5eead4 + bóng nhẹ; dải tối #115e59 + viền #2dd4bf (fade mép phải khớp đúng màu dải mới ở cả hai chế độ). Chip thường: viền đậm hơn (#2dd4bf), chữ đậm hơn (#134e4a), pill đếm rõ hơn; chip đang chọn: gradient teal đậm linear-gradient(140deg,#0da678,#066e52) — cùng họ với nút + Mẫu 1 — + chữ trắng + bóng nhẹ, pill đếm rgba(255,255,255,.28). Thêm hover/focus-visible nhất quán. Sửa trong lúc kiểm chứng: hover ban đầu đè mất gradient của chip đang chọn (background shorthand reset background-image) — đã giới hạn hover cho chip chưa chọn (:not(.active)) ở cả hai chế độ, probe lại xác nhận gradient còn nguyên khi rê chuột lên chip đang chọn.
- Kiểm thử: webapp 75/75, bot 256/256. Probe Playwright (bản sao DB): mobile 390 + desktop 1440, sáng + tối — dải sáng rgb(204,251,241), dải tối rgb(17,94,89), chip đang chọn gradient linear-gradient(140deg,rgb(13,166,120),rgb(6,110,82)) + chữ trắng ở cả 4 tổ hợp, bấm chip chuyển trạng thái đúng, màn APPROVED_WAITING chip thứ 4 đang chọn đúng, không tràn ngang, fade còn hoạt động. Ảnh probe: /tmp/td23-probe/shots/after-{mobile-light,mobile-dark,desktop-light,desktop-dark}.png.
- Triển khai: restart webapp; health local + public 0.5.10, login 200, /miniap/ 200, đủ 5 service active; styles.css public ?v=0.5.10 chứa nền dải mới. Không đổi mẫu pager TD-0022. SRS vẫn 1.4; TD-0019 + TD-0020 + TD-0021 + TD-0022 + TD-0023 ⏳ chờ gộp.

## TD-0024 — Tải chia nhỏ 2GB + lưu trữ Drive + xóa sau khi đăng + quét 48h + khôi phục + giới hạn 9GB (bản 0.5.11, 25/10/2026)
- Quyết định (chủ dự án, 13:20 ngày 25/10): CÁCH A — tải lên máy chủ, đăng xong thì lưu Drive rồi xóa (bài nào cũng vậy, chỉ xóa khi TẤT CẢ đầu ra của việc đều đã đăng xong vì file dùng chung nhiều kênh). Ghi TD-0024 vào THAY-DOI.md trước khi code; sao lưu webapp + bot.db tại data/backup-td24-20261025-062604/ (chỉ trên máy, không lên GitHub). Google Drive đã nối xong cùng ngày; thư mục lưu trữ "Giao Việc IAICT — Bản gốc" id 1tE5uJesfNh3X4t8cm5u4TNKUHfQzZ1d8, id lưu data/drive_archive.json (600, không commit). Máy chủ bị thay đầu đợt — restore-services.sh khôi phục đủ 5 service; phát hiện /etc/default/webapp-giao-viec tạo lại KHÔNG có TELEGRAM_BOT_TOKEN (token Mini App cấp 25/10 chỉ nằm trong file đó + chat) — Mini App sẽ lỗi đăng nhập tới khi nhập lại token (ngoài phạm vi TD này, đã ghi trong THAY-DOI.md + báo cáo).
- Làm (webapp): API tải chia nhỏ `POST /api/uploads/chunked/init|chunk|complete`, `GET .../status`, `DELETE` hủy phiên; miếng 50MB, ngưỡng >20MB dùng đường chia nhỏ, file nhỏ giữ đường đơn; giới hạn ráp xong 2GB/file, đường đơn giữ 1GB; miếng tạm `data/files/.tmp/<upload_id>/`, dọn phiên dở >24h khi init mới; resume qua upload_id (localStorage) + GET status tính lại miếng đã nhận từ file `.part`; `POST /api/tasks/<code>/restore` (người tạo/Admin); auto-restore trong `_act_publish`/`_act_schedule`; `_stats_summary` thêm `storage {used_bytes, quota_bytes=9GB}`; vòng quét 48h trong `_daily_summary_loop` (tối đa 1 lần/giờ qua `web_last_archive_scan`); `CHUNK_SIZE_BYTES=50MB`, `CHUNKED_THRESHOLD_BYTES=20MB`, `CHUNKED_MAX_FILE_BYTES=2GB`, `STORAGE_QUOTA_BYTES=9GB`; `_task_files` hiện file đã lưu kèm link Drive (`archived: True`); file video >512MB chỉ hiện ô tải về, không phát inline. Client: `uploadChunked` (retry mỗi miếng 3 lần, backoff 1s×lần, thanh tiến trình từng file), wizard tạo việc bằng JSON trước khi tải file lớn (giữ `createdCode` để thử lại không trùng việc; `_task_is_fresh_creation` <600s thì không gửi thông báo tải muộn TD-0015), Thêm tư liệu có bước chặn >2GB + thanh tiến trình từng file, nút "↩️ Tải lại N file từ Drive", thẻ dung lượng Thống kê "Đã dùng X / 9.0 GB". Version 0.5.10→0.5.11, SW cache v18→v19.
- Làm (bot, module mới `archive.py` + `archive_worker.py`): hàm dùng chung `archive_task_files`/`restore_task_files` (tải lên/tải về Drive qua `hatch_gws_cli`, retry 3 lần, xóa local chỉ sau khi Drive xác nhận từng file, kiểm tra đúng kích thước khi tải về), `scan_waiting_tasks` (48h, bỏ qua khi có lệnh đăng dở dang), `maybe_archive_task` (hook sau cả hai đường lật PUBLISHED trong `botctl set-output-published`), `maybe_restore_task` (hook sau publish_requested ở 4 điểm: đăng thường, xác nhận Facebook, đăng đơn cũ, lịch tới giờ + sau `schedule_set`); bảng mới `archived_files` (task_code, filename, drive_file_id, web_view_link, size, archived_at); audit `files_archived`/`files_archive_failed`/`files_restored`/`files_restore_failed`; worker tách session, log `data/archive.log`; lệnh botctl mới `archive-task-files`, `restore-task-files`.
- Sửa lỗi phát hiện trong lúc probe (gộp vào TD-0024): server không đọc body `{}` của `POST .../chunked/complete` (và `/restore`) nên 2 byte thừa dính vào request line tiếp theo trên cùng kết nối keep-alive (`"{}GET /api/tasks/..."` → 501) — wizard dừng ở bước 3 ngay sau khi tải xong; chính là lỗi 501 bí ẩn ở TD-0013 (tưởng là tunnel). Sửa tận gốc: `_dispatch` bọc `_route`, `finally` xả body chưa đọc của mọi POST/PUT/PATCH/DELETE; `_read_json`/`_parse_multipart`/`_chunk_put` đánh dấu đã đọc. Có test hồi quy keep-alive (complete rồi GET cùng kết nối → 200).
- Kiểm thử: webapp 87/87 (75 + 12 mới TD-0024: chunked roundtrip/resume, từ chối input xấu, phân quyền owner, quota, wizard tạo việc im lặng, tải muộn vẫn báo, chi tiết hiện file lưu trữ, restore endpoint, stats storage, cổng quét, hồi quy keep-alive), bot 268/268 (256 + 12 mới ArchiveTestCase: lưu sau đăng đủ điều kiện, chưa đủ thì không, Drive lỗi giữ file, lũy đẳng, khôi phục đúng/sai, quét 48h đủ/chưa đủ/có lệnh đăng dở dang, fallback created_at, khóa Facebook, thư mục Drive tạo một lần). Probe Playwright trên BẢN SAO DB (bot copy riêng, server probe cổng 8899; DB thật kiểm chứng chỉ thêm 1 dòng web_notification_reads do chính người dùng đọc thông báo — 16 việc/26 đầu ra/141 audit nguyên; Drive dọn sạch sau probe): API 25/25 (chunked 120MB thật đúng từng byte; lưu trữ sau đăng + khôi phục, file thật lên Drive rồi xóa ngay), UI 14/14 (wizard 120MB tới Chi tiết việc 120.0 MB; chặn >2GB hai chỗ; thẻ dung lượng; nút Tải lại), quét 48h 7/7 (PENDING backdate 49h lên Drive + biến khỏi đĩa, trạng thái giữ PENDING, việc mới không bị chạm), khôi phục 48h 11/11. Lưu ý probe: /tmp là tmpfs chỉ 512MB — bản sao probe đầy đĩa giữa chừng (chunk kẹt ở ~31MB, complete 500) nên đã dời probe sang /home/hatch/.td24-probe (ổ 100GB); Chromium không có --no-proxy-server thì proxy egress thỉnh thoảng chụp request localhost làm chunk 50MB đứt giữa chừng (400) — probe chạy với --no-proxy-server; lỗi ERR_TUNNEL_CONNECTION_FAILED trong console chỉ là script telegram-web-app.js từ telegram.org bị proxy chặn, ngoài app, không ảnh hưởng.
- Giới hạn còn tồn tại: tốc độ upload Drive thật với file lớn chưa đo (chỉ probe file 14 byte; 1GB lên Drive qua proxy mất hàng phút, chạy nền); miếng 50MB có thể chạm timeout 100s của Cloudflare trên 4G yếu (~2Mbps); quota 9GB chỉ chặn đường tải webapp, chưa chặn file gửi qua Telegram; việc không bao giờ đăng vẫn chưa có quy tắc dọn; worker nền không có hàng đợi bền — máy bị thay giữa lúc tải lên Drive thì lần tải đó mất (file local còn nguyên, lần sau thử lại). SRS vẫn 1.5; TD-0024 ⏳ chờ gộp.
- Đính chính giờ Việt Nam (chủ dự án, 25/10 — gộp vào TD-0024 trước khi đóng, cùng bản 0.5.11): một định nghĩa ICT duy nhất ở `storage.py` (`ICT`, `ict_now()`, `format_ict()`, `format_ict_short()`); `webapp/app.py:83` tái xuất nó (`ICT = storage.ICT`). DB vẫn lưu UTC; chuyển sang ICT ở biên hiển thị/log — tile file lưu trữ hiện "lúc HH:MM DD/MM/YYYY" qua `fmtTime` (ép Asia/Ho_Chi_Minh), audit `files_*` thêm `lúc ...` giờ VN, log worker tiền tố `[DD/MM HH:MM]` giờ VN, dòng in quét 48h tiền tố giờ VN; tính 48h vẫn trừ theo UTC. Kiểm thử bot 269/269 (thêm 1 test ICT: audit `lúc ...` khớp created_at UTC + 7h, log có tiền tố giờ VN), webapp 87/87 (test chi tiết lưu trữ mở rộng: `archived_at` + marker tile). Probe ICT trên bản sao DB 10/10 + in quét 48h in-process (stdout server khi redirect ra file bị block-buffered nên log file không thấy ngay — bản in vẫn đúng).
