# THAY-DOI.md — Sổ ghi thay đổi yêu cầu (nguồn cập nhật SRS)

File này ghi lại **mọi thay đổi** liên quan tới yêu cầu, phạm vi và quyết định
sản phẩm của Web App Giao Việc, để về sau **tổng hợp cập nhật vào `SRS.md`**
mà không bỏ sót và không phải lục lại lịch sử trò chuyện.

## Quy trình

1. Mỗi khi có thay đổi (người dùng yêu cầu, quyết định mới, sửa quy tắc, đổi
   phạm vi, phát sinh trong lúc xây…), ghi **ngay một mục mới** vào bảng dưới
   đây — kể cả thay đổi nhỏ. Chưa cần sửa SRS ngay.
2. Cuối mỗi giai đoạn (hoặc khi người dùng yêu cầu), tổng hợp tất cả mục đang
   "⏳ Chờ cập nhật" vào `SRS.md`, tăng phiên bản SRS, rồi đổi trạng thái các
   mục đó thành "✅ Đã vào SRS x.y".
3. Không xóa mục cũ; quyết định bị thay thế thì ghi mục mới và ghi rõ
   "thay thế TD-xxxx".

## Mẫu một mục

```
### TD-XXXX — <tiêu đề ngắn>
- Ngày: DD/MM/YYYY
- Nguồn: Người dùng yêu cầu / Muse đề xuất được duyệt / Phát sinh khi xây GĐ…
- Nội dung thay đổi: <trước đây …, nay …>
- Ảnh hưởng: mục SRS liên quan (vd 3.4), phạm vi giai đoạn, dữ liệu/API…
- Trạng thái SRS: ⏳ Chờ cập nhật | ✅ Đã vào SRS x.y
```

---

## Danh sách thay đổi

### TD-0001 — Chốt làm Web App PWA độc lập thay cho app native và Mini App
- Ngày: 24/10/2026
- Nguồn: Người dùng chốt sau phân tích so sánh app native vs web app
- Nội dung thay đổi: Không làm app native lên store ở thời điểm này, không làm
  Telegram Mini App; làm Web App dạng PWA độc lập khỏi Telegram (ghim ra màn
  hình chính, chạy điện thoại + máy tính), kiến trúc đóng gói được (Capacitor)
  để sau này bọc native khi cần mà không viết lại.
- Ảnh hưởng: Toàn bộ SRS (căn cứ tạo SRS 1.0); lộ trình mục 7.
- Trạng thái SRS: ✅ Đã vào SRS 1.0

### TD-0002 — Đăng nhập bằng mật khẩu, tài khoản do Admin tạo (chưa làm OTP)
- Ngày: 24/10/2026
- Nguồn: Muse tự chốt trong bản thiết kế, người dùng duyệt khi chốt thiết kế
- Nội dung thay đổi: Đăng nhập bằng email/SĐT + mật khẩu thay cho telegram_id;
  chưa làm OTP vì chưa có dịch vụ SMS và Gmail chưa kết nối. Tài khoản do
  Admin/Phó Admin tạo, không tự đăng ký.
- Ảnh hưởng: SRS mục 1.2, 3.1 (FR-AUTH-01…06), 3.9.
- Trạng thái SRS: ✅ Đã vào SRS 1.0

### TD-0003 — Chạy song song với bot, giữ bot làm thông báo dự phòng
- Ngày: 24/10/2026
- Nguồn: Muse tự chốt trong bản thiết kế, người dùng duyệt khi chốt thiết kế
- Nội dung thay đổi: Web App dùng chung `bot.db` với bot Telegram trong giai
  đoạn chuyển đổi; bot giữ vai trò thông báo dự phòng; tắt dần bot ở GĐ4 khi
  đội đã chuyển hẳn.
- Ảnh hưởng: SRS mục 2.4, 3.8 (FR-NOTI-02), 7 (GĐ4).
- Trạng thái SRS: ✅ Đã vào SRS 1.0

### TD-0004 — GĐ1 hoàn thành: API + di trú dữ liệu cộng thêm
- Ngày: 24/10/2026
- Nguồn: Phát sinh khi xây GĐ1
- Nội dung thay đổi: Xác lập các quyết định kỹ thuật có tính yêu cầu:
  backend thuần Python stdlib; dùng lại module nghiệp vụ của bot; người dùng
  web-only nhận telegram_id tổng hợp ≥ 9.000.000.000; di trú chỉ cộng thêm
  (cột email/phone/password_hash + bảng web_sessions), idempotent, sao lưu
  trước khi áp. Đã áp lên DB thật ngày 24/10/2026.
- Ảnh hưởng: SRS mục 2.5, 5, 6; kiểm thử đạt webapp 19/19, bot 215/215.
- Trạng thái SRS: ✅ Đã vào SRS 1.0

### TD-0005 — Thiết lập bộ đôi tài liệu SRS.md + THAY-DOI.md
- Ngày: 24/10/2026
- Nguồn: Người dùng yêu cầu ("Thêm 2 file .md để lưu: 1 SRS; 1 lưu các thay
  đổi để sau cập nhật SRS")
- Nội dung thay đổi: Từ nay dự án duy trì `SRS.md` (đặc tả yêu cầu, tăng
  phiên bản theo giai đoạn) và `THAY-DOI.md` (sổ ghi thay đổi theo quy trình
  ở đầu file này). Mọi thay đổi yêu cầu mới phải qua THAY-DOI.md trước khi
  vào SRS.
- Ảnh hưởng: SRS mục đầu (Quy trình quản trị tài liệu), NFR-MNT-01.
- Trạng thái SRS: ✅ Đã vào SRS 1.0

### TD-0006 — GĐ2 + cài dịch vụ + tài khoản Admin đầu tiên trong một lượt
- Ngày: 24/10/2026
- Nguồn: Người dùng yêu cầu ("Làm luôn tất cả 1 lượt")
- Nội dung thay đổi: Hoàn thành Giai đoạn 2 trong một đợt gồm cả phần
  trước đây dự kiến để bước triển khai sau: (1) giao diện PWA đầy đủ 9
  màn hình theo thiết kế đã chốt; (2) backend bổ sung — upload tư
  liệu 200MB/file lưu đúng cấu trúc `data/files/<MÃ VIỆC>/` của bot
  (hai điểm vào: kèm tạo việc và gắn thêm), đủ thao tác thẻ kênh khớp
  ngữ nghĩa/audit của bot, review-queue, scheduled, xuất thống kê
  CSV/Excel, hộp thông báo trong app, đổi mật khẩu, đổi vai trò/thu
  hồi qua API; (3) cài systemd service `webapp-giao-viec` cổng 8790
  (trước đây thuộc bước triển khai/GĐ4); (4) tạo tài khoản Admin Web
  App đầu tiên gắn vào tài khoản Admin Telegram hiện có (email + SĐT
  của chủ dự án, mật khẩu tạm bàn giao riêng, không ghi trong tài
  liệu). Kiểm thử: webapp 37/37, bot 215/215; lái thử thật qua HTTP
  tạo việc CV-0013 + ghi lệnh đăng đúng quy tắc.
- Ảnh hưởng: SRS mục 3 (toàn bộ FR của GĐ2), 2.4 (chạy song song —
  nay đã có service thật), 7 (lộ trình: mục "cài systemd service" của
  GĐ4 đã làm trước một phần; tên miền/HTTPS vẫn ở GĐ4).
- Trạng thái SRS: ✅ Đã vào SRS 1.1 (tổng hợp ngày 24/10/2026 khi đóng GĐ2).

---

### TD-0007 — Mở Web App ra Internet qua Cloudflare Tunnel (làm trước phần "tên miền/HTTPS" của GĐ4)
- Ngày: 24/10/2026 — Người yêu cầu: chủ dự án (chọn tên miền + cấp quyền Cloudflare).
- Nội dung: Web App truy cập được từ Internet tại **https://post.iaict-platform.com**
  qua Cloudflare Tunnel `webapp-giao-viec` (ingress → http://127.0.0.1:8790,
  DNS CNAME proxied). Vì netstack của máy chủ ảo chặn DNS-SRV/UDP/7844 trực
  tiếp, hệ thống kèm 2 dịch vụ phụ trợ riêng của máy này: `cf-dns-stub`
  (DNS tĩnh cho edge discovery + forward gateway) và `cf-edge-relay`
  (CONNECT qua proxy egress tới edge thật, ép giao thức HTTP/2). Cả ba
  chạy bằng systemd cùng `webapp-giao-viec`. Kiểm chứng từ ngoài: trang
  đăng nhập + `/api/health` trả 200.
- Ảnh hưởng: SRS mục 7 (GĐ4: phần tên miền/HTTPS ✅ xong; còn chuyển đội
  sang Web App + tắt dần bot).
- Trạng thái SRS: ✅ Phần tên miền/HTTPS đã vào **SRS 1.3** (24/10/2026);
  phần chuyển đội sang Web App + tắt dần bot vẫn chờ GĐ4.

### TD-0008 — GĐ3: Thông báo đẩy Web Push (VAPID) + tổng kết ngày trong Web App
- Ngày: 24/10/2026
- Nguồn: Người dùng yêu cầu ("giữ và làm GĐ3") theo lộ trình đã chốt trong SRS mục 7
- Nội dung thay đổi: Trước đây Web App chỉ có hộp thông báo trong app (GĐ2),
  tổng kết ngày chỉ có qua Telegram của bot. Nay bổ sung:
  (1) **Web Push thật theo chuẩn VAPID/RFC 8291**: khóa VAPID sinh một lần,
  lưu ngoài repo (`data/vapid.json`, chmod 600); API lấy public key,
  đăng ký/hủy đăng ký thiết bị, gửi thử; máy chủ tự gửi push khi có việc
  mới, thẻ chờ duyệt, duyệt/trả lại, lệnh đăng, thu hồi, đặt lịch; đăng ký
  nào bị dịch vụ đẩy trả 404/410 thì tự xóa. Mật mã: EC (sinh khóa, ECDH,
  ký JWT-ES256) qua **openssl CLI** vì máy chủ không có sẵn package
  `cryptography`; AES-128-GCM của RFC 8291 tự cài đặt thuần Python
  (openssl `enc` không hỗ trợ AEAD) và kiểm chứng bằng test vector NIST +
  giải mã vòng tròn. (2) **Tổng kết ngày trong app**: endpoint
  `/api/stats/daily-summary` (việc tạo hôm nay, đầu ra theo trạng thái,
  đã đăng hôm nay, đang chờ duyệt/chờ đăng), thẻ "Tổng kết hôm nay" trên
  màn Tổng quan; thread nền 20:00 giờ VN mỗi ngày gửi push tổng kết cho
  Admin + thêm mục tổng kết vào hộp thông báo của mọi người, chống gửi
  trùng bằng ngày đã gửi lưu trong DB (web_meta). Version app 0.2.0 → 0.3.0.
- Ảnh hưởng: SRS mục 3.7 (FR-STAT-04), 3.8 (FR-NOTI-01), 5 (bảng
  `web_push_subscriptions`, `web_notification_items`), 6 (API push +
  daily-summary), 7 (GĐ3 ✅); kiểm thử mở rộng ở cả hai bộ.
- Trạng thái SRS: ✅ Đã vào SRS 1.2 (tổng hợp ngày 24/10/2026 khi đóng
  GĐ3; kiểm thử webapp 51/51, bot 215/215; version app 0.3.0 đã chạy
  tại https://post.iaict-platform.com)

### TD-0009 — Sửa giao diện mobile theo phản hồi dùng thật: thông báo đẩy không hiện, trùng menu, lọc việc theo trạng thái, gọn block chọn file
- Ngày: 24/10/2026
- Nguồn: Người dùng phản hồi trên mobile kèm ảnh chụp màn Thông báo (không
  thấy mục bật thông báo đẩy), kèm chỉ đạo từ nay chỉ làm/kiểm chứng mobile
  trừ khi người dùng báo đang ở desktop.
- Nội dung thay đổi (chỉ mobile, desktop giữ nguyên; version app 0.3.0 → 0.3.1):
  (1) **Khối "📲 Thông báo đẩy" không hiện trên máy người dùng**: bản app
  shell GĐ3 đã có thẻ này trong mã, nhưng thiết bị còn chạy vỏ app cũ do
  service worker đời trước giữ cache. Xử lý: đổi chiến lược cache của
  `sw.js` — vỏ app (index.html/app.js/styles.css) luôn network-first, tĩnh
  khác cache-first, tăng cache lên v4 (skipWaiting + clients.claim như cũ),
  app tự gọi kiểm tra bản SW mới mỗi lần mở và tự tải lại một lần khi SW mới
  tiếp quản; hiện số phiên bản app nhỏ trong giao diện để đối chiếu bằng
  mắt; rà `initPushPanel` để thẻ LUÔN hiện kèm dòng trạng thái rõ ràng
  trong mọi trường hợp (đang kiểm tra/không hỗ trợ/đã chặn/đang tắt/đang
  bật/lỗi) thay vì ẩn hết nút khi lỗi sớm. Khi triển khai còn phát hiện
  thêm tầng cache thứ hai: Cloudflare edge giữ bản `/app.js` cũ theo
  TTL mặc định (origin không gửi Cache-Control) — đã xử lý bằng cách
  origin gửi `Cache-Control: no-cache` cho toàn bộ vỏ app và
  `index.html`/`sw.js` tham chiếu tài nguyên kèm phiên bản
  (`?v=0.3.1`), vì token Cloudflare sẵn có không có quyền purge cache
  (API trả 401).
  (2) **Trùng menu mobile**: ẩn hẳn hàng chip điều hướng trượt ngang ngay
  dưới header trên khung mobile; điều hướng chỉ còn thanh dưới đáy. Header
  giữ nguyên.
  (3) **Lọc việc theo trạng thái** ở màn Việc: backend `GET /api/tasks`
  lọc `?status=` theo đúng trạng thái việc đã suy ra bằng logic của Store
  (`sync_task_status_from_outputs`) và trả thêm `counts` từng trạng thái
  trên cùng tập việc người dùng thấy (trước khi lọc theo trạng thái).
  Frontend: hàng chip lọc trượt ngang (Tất cả • Nháp • Chờ duyệt • Đã
  duyệt · chờ đăng • Đã đăng • Bị trả lại • Đã thu hồi • Đã hủy) kèm số
  lượng từng trạng thái, giữ lựa chọn khi quay lại màn (state + URL hash),
  danh sách rỗng hiện "Không có việc nào ở trạng thái này."
  (4) **Gọn block chọn ảnh/video ở Bước 1 wizard** trên mobile: giảm mạnh
  padding/chiều cao vùng chọn file, file đã chọn hiện lưới thumbnail nhỏ
  gọn kèm tên/dung lượng + nút xóa, ghi chú giới hạn 200MB/tệp chữ nhỏ.
- Ảnh hưởng: SRS mục 3.2 (FR-TASK — lọc theo trạng thái), 3.8 (FR-NOTI-01 —
  hiển thị mục thông báo đẩy), 6 (API tasks thêm `counts`), giao diện
  mobile các màn Việc/Giao việc/Thông báo. Kiểm thử: thêm test API lọc
  `?status=` + counts vào bộ webapp; giữ nguyên toàn bộ test cũ hai bộ.
- Trạng thái SRS: ✅ Đã vào **SRS 1.3** (24/10/2026).
- **Bổ sung (đính chính người dùng, cùng ngày)**: bỏ cách hiểu "chỉ
  mobile" — giao diện làm kỹ CẢ desktop lẫn mobile. Đã rà: desktop
  vốn không có chip-nav trùng (sidebar đầy đủ như thiết kế); block
  chọn file desktop siết nhẹ cho cân đối (`@media (min-width:821px)`:
  padding .85rem/1rem, icon 1.55rem; đo 229→209px). Kiểm chứng hiển
  thị bằng ảnh chụp thật ở CẢ hai khung 390px và 1440px cho 4 màn
  chính (chi tiết trong NHAT-KY-PHAT-TRIEN.md). Giữa đợt máy chủ bị
  thay làm mất unit/env — đã khôi phục đủ 5 service, health local +
  public 0.3.1.

---

### TD-0010 — Làm đẹp thanh điều hướng dưới đáy (mobile)
- Ngày: 24/10/2026 — Người yêu cầu: chủ dự án ("Menu dưới thiết kế đẹp chút").
- Nội dung: thanh dưới đáy mobile từ dạng dải phẳng sát mép thành thanh
  nổi bo tròn (khoảng hở hai bên + dưới, nền trắng mờ blur, bóng mềm);
  mục đang chọn hiện icon trong viên thuốc màu teal nhạt + chữ đậm màu
  teal đậm; nút Giao việc ở giữa thành nút tròn teal nổi cao hơn thanh
  (nhận diện chính của app); badge chưa đọc bám góc trên của icon;
  khoảng đệm cuối nội dung tăng để thanh nổi không che nội dung. Chỉ
  đổi CSS/HTML của bottom nav (mobile); sidebar desktop không đổi.
- Ảnh hưởng: không đổi SRS (chỉ thẩm mỹ) — bản app 0.3.1 → 0.3.2.
- Trạng thái SRS: ✅ Đã vào **SRS 1.3** (24/10/2026).

---

### TD-0011 — Áp giao diện mới đã chốt (bản thiết kế mới) vào app thật, bản 0.4.0
- Ngày: 24/10/2026 — Người yêu cầu: chủ dự án (nói "Chốt" sau khi duyệt
  bản thiết kế mới qua mô phỏng bấm thử + chọn Mẫu 1 "Gradient viền
  trắng" cho nút Giao việc vì đơn giản).
- Nội dung thay đổi (CHỈ giao diện/bố cục, KHÔNG đổi API, schema,
  audit/state semantics, phân quyền, logic nghiệp vụ):
  (1) Ngôn ngữ thị giác mới: không gian thoáng hơn (thẻ bo 20px, đệm
  lớn hơn, chữ tầng bậc rõ hơn), giữ tông teal chủ đạo; thẻ Chờ duyệt
  màu hổ phách gắn nhãn Ưu tiên trên Tổng quan, thẻ Tổng kết hôm nay
  thành hero (nền gradient teal), nút hành động chính nổi bật nhất.
  (2) Scroll đúng chỗ: hàng chip lọc trượt ngang (có sẵn, giữ nguyên);
  danh sách việc/chờ duyệt/lịch đăng cuộn dọc; bảng thống kê cuộn
  ngang trên mobile (table-wrap có sẵn); dòng hoạt động trên Tổng
  quan có vùng cuộn riêng.
  (3) Collapse đúng chỗ: khối thông tin việc (Gợi ý/Tư liệu) và từng
  thẻ kênh trên màn chi tiết gập/mở được; bộ lọc màn Việc gập/mở
  được; thông báo gộp theo ngày, nhóm mới nhất mở sẵn, nhóm cũ bấm
  mới mở; sidebar desktop có nút thu gọn thành thanh icon (lưu lựa
  chọn vào localStorage).
  (4) Thanh điều hướng mobile mới: lưới 6 cột đều nhau, thứ tự Tổng
  quan, Việc, nút +, Chờ duyệt, Thông báo, Thêm (các mục theo quyền
  như cũ: Chờ duyệt/Lịch đăng/Thống kê chỉ người duyệt, Người dùng
  chỉ người quản lý; không đủ quyền thì mục đó không hiện). Nút +
  nằm cạnh nút Việc, đúng Mẫu 1 đã chọn: hình tròn 54px (48px ở màn
  ≤340px), nền teal chuyển sắc 140deg #1cc79b → #0da678 → #066e52,
  viền trắng đặc 3px, vòng mỏng ngoài rgba(9,120,90,.16), KHÔNG đổ
  bóng, dấu + trắng 28px nét 3.4, nhô lên khỏi mép thanh khoảng
  19px, nhãn "Giao việc" teal đậm bên dưới, bấm mở wizard như cũ.
  Nhãn 5 mục còn lại một dòng (9.5px, 8.5px ở màn ≤340px), không tách
  từ, thẳng hàng. Badge thanh dưới: hình tròn 19×19 cố định, bo
  50%, số chính giữa (hiển thị tối đa 99), không méo, không bị che;
  thêm badge số thẻ chờ duyệt (lấy từ review-queue, chỉ hiển thị,
  không đổi API). Nút "Thêm" mở bảng menu nổi với các mục còn lại
  (Lịch đăng, Thống kê, Người dùng & phân quyền — theo quyền), icon
  giống sidebar, mục đang chọn được đánh dấu, chạm ngoài/Esc đóng.
  Bổ sung sau khi kiểm chứng hiển thị: `navigate()` luôn đóng bảng
  "Thêm" trước khi đổi màn, vì scrim của bảng không che topbar nên
  bấm chuông khi bảng đang mở sẽ đổi màn mà bảng vẫn kẹt lại phía
  trên màn mới.
  (5) Wizard giao việc 3 bước: vừa đúng chiều rộng mobile (không
  tràn ngang); chân wizard đổi bố cục: nút chính (Tiếp tục, bước
  cuối là Chốt! Gửi Muse) nằm TRÊN cùng full-width nổi bật nhất,
  các nút phụ (Huỷ việc, Quay lại) nằm dưới thành hàng gọn.
  (6) Sáng/tối theo hệ thống (prefers-color-scheme) cho cả mobile
  lẫn desktop, đủ biến màu cho cả hai chế độ.
  (7) Version + cache: bản app 0.3.2 → 0.4.0, cập nhật nhất quán ở
  mọi nơi (VERSION, APP_VERSION, index.html + sw.js ?v=0.4.0, SW
  cache v6, dòng "Phiên bản 0.4.0" hiển thị trong app); shell giữ
  network-first để người dùng nhận giao diện mới ngay.
- Ảnh hưởng: không đổi SRS về hành vi (chỉ thẩm mỹ/bố cục) — bản app
  0.3.2 → 0.4.0. Kiểm thử: giữ nguyên 2 bộ (webapp 52/52, bot
  215/215) + thêm test cho version 0.4.0, nav mới và wizard footer
  mới ở mức tĩnh (HTML/JS phục vụ). Sao lưu trước khi sửa tại
  data/backup-ui40-20261024-112524/ (bản sao webapp + bot.db).
- Trạng thái SRS: ✅ Đã vào **SRS 1.3** (24/10/2026).

---

## Mục chờ cập nhật vào SRS

- **TD-0006** — ✅ Đã tổng hợp vào **SRS 1.1** ngày 24/10/2026 (đóng GĐ2).
- **TD-0007** — ✅ Đã tổng hợp phần tên miền/HTTPS vào **SRS 1.3** ngày 24/10/2026 (phần chuyển đội + tắt dần bot vẫn chờ GĐ4).
- **TD-0010** — ✅ Đã tổng hợp vào **SRS 1.3** ngày 24/10/2026 (thanh dưới mobile dạng nổi bo tròn, bản 0.3.2).
- **TD-0008** — ✅ Đã tổng hợp vào **SRS 1.2** ngày 24/10/2026 (đóng GĐ3).
- **TD-0009** — ✅ Đã tổng hợp vào **SRS 1.3** ngày 24/10/2026 (sửa giao diện mobile: thông báo đẩy/cache SW v4, bỏ trùng menu, lọc việc theo trạng thái, gọn block chọn file; bản 0.3.1).
- **TD-0011** — ✅ Đã tổng hợp vào **SRS 1.3** ngày 24/10/2026 (áp giao diện mới đã chốt: nav mobile 6 cột + nút Giao việc Mẫu 1, collapse/scroll, wizard footer nút chính lên trên, dark mode theo hệ thống; bản 0.4.0).
