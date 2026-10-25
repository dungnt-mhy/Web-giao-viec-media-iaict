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
- Trạng thái SRS: ⏳ Chờ cập nhật
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

### TD-0012 — Sửa thanh điều hướng mobile sau phản hồi: nút + to hơn, bớt nhô cao; mục đang chọn không còn nền tối che chữ (bản 0.4.1)
- Ngày: 24/10/2026 — Người yêu cầu: chủ dự án (phản hồi qua ảnh chụp
  sau khi 0.4.0 lên sóng; đồng thời yêu cầu TẠM DỪNG việc build Mini
  App Telegram để sửa nav trước — Mini App chưa có số TD, sẽ đánh số
  khi tiếp tục).
- Nội dung thay đổi (CHỈ giao diện/bố cục, KHÔNG đổi API, schema,
  audit/state semantics, phân quyền, logic nghiệp vụ):
  (1) Nút +: từ 54px (48px ở màn ≤340px) lên 58px (52px ở màn ≤340px);
  độ nhô khỏi mép thanh giảm từ ~19px xuống ~7px (translateY -32px
  → -20px) để nút không "nhảy vọt" lên cao mà vẫn nổi nhẹ; giữ nguyên
  gradient Mẫu 1, viền trắng 3px, vòng mỏng ngoài, không đổ bóng,
  nhãn "Giao việc" teal đậm.
  (2) Sửa lỗi mục đang chọn bị nền tối che chữ: quy tắc chung
  `.nav-btn.active{background:var(--teal)}` của sidebar rò rỉ sang nút
  thanh dưới, kết hợp chữ teal đậm → chữ chìm trên nền tối khi bấm
  sang mục khác. Nay nút thanh dưới khi active có nền trong suốt,
  chỉ viên thuốc sau icon giữ nền teal nhạt (chế độ sáng) với chữ
  tương phản đúng từng chế độ.
  (3) Bản app 0.4.0 → 0.4.1 (VERSION, APP_VERSION, ?v=0.4.1, SW cache
  v7, dòng phiên bản trong app) để vượt cache cạnh và nhận bản sửa
  ngay.
- Ảnh hưởng: chỉ thẩm mỹ/bố cục. Kiểm thử: webapp 53/53 (cập nhật
  test version + assertion CSS mới), bot 215/215.
- Trạng thái SRS: ✅ Đã tổng hợp vào **SRS 1.4** ngày 25/10/2026

---

### TD-0013 — Đăng Facebook nhiều nơi cùng lúc, sẵn sàng nhiều Fanpage (bản 0.5.0)
- Ngày: 24/10/2026 — Người yêu cầu: chủ dự án ("khi chọn đăng trên
  trang cá nhân hay fanpage thì chỉ được 1; tôi muốn đăng cả 2 nơi,
  sau này còn chọn fanpage (nhiều fanpage) để đăng").
- Vấn đề cũ: mỗi lần đăng Facebook chỉ chọn được ĐÚNG 1 nơi (trang
  cá nhân HOẶC Fanpage Minhy); danh sách nơi đăng gắn cứng 2 mục
  trong code (bot `FB_PUBLISH_TARGETS`, webapp `FB_TARGETS`); target
  của đăng ngay chỉ nằm trong audit, target của đặt lịch chỉ là 1
  cột `publish_target` đơn; link chỉ có 1 `public_url` đơn.
- Nội dung thay đổi:
  (1) Mô hình target thành DANH SÁCH: một đầu ra Facebook mang một
  tập hợp các nơi đăng, mỗi nơi có link bài đã đăng riêng. Khóa nơi
  đăng: `profile` (trang cá nhân, cố định 1 mục) và
  `page_<fb_page_id>` (mỗi Fanpage một khóa). Danh sách nơi đăng lấy
  từ dữ liệu: trang cá nhân + bảng mới `facebook_pages` (seed sẵn
  đúng 1 dòng: Minhy, id 61595515900524). Về sau thêm Fanpage chỉ
  cần thêm dòng vào bảng này (chưa có màn hình quản lý Fanpage
  trong đợt này).
  (2) Cột mới trên outputs (JSON, cộng thêm, không phá dữ liệu cũ):
  `publish_targets` (tập hợp của lệnh đăng/lịch gần nhất),
  `fb_target_set` (tập hợp đầy đủ, đóng băng khi đã có nơi đăng
  xong), `fb_place_urls` (link từng nơi), `fb_place_failed` (nơi
  đăng lỗi), `fb_place_retracted` (nơi đã xoá khi thu hồi),
  `fb_pending_targets` (lựa chọn đang bật/tắt dở trên bot).
  Tương thích ngược: target đơn cũ (`publish_target` = profile/page)
  được hiểu như danh sách 1 phần tử; đầu ra đã PUBLISHED với
  `public_url` đơn cũ được hiểu như đã đăng xong 1 nơi.
  (3) Giao diện chọn nhiều ở CẢ bot lẫn webapp: bot đổi màn chọn
  nơi đăng thành nút bật/tắt từng nơi (đang chọn hiện ✅, chạm để
  bỏ chọn thành ❌ như quy ước nút kênh; nơi đã đăng xong hiện
  "đã đăng", chạm chỉ báo chứ không chọn lại), mặc định chọn sẵn
  tất cả nơi chưa đăng, thêm nút xác nhận "Đăng lên N nơi" (bot) /
  checkbox + nút xác nhận tương tự (webapp); bắt buộc chọn ít nhất
  1 nơi mới cho xác nhận; nút Hủy giữ nguyên hành vi cũ.
  (4) Đăng: một lần bấm Đăng đăng lần lượt tới từng nơi đã chọn
  (giữ nguyên đường đăng trình duyệt của Muse). Ghi nhận link theo
  từng nơi (botctl `set-output-published --place`).
  (5) Thất bại từng phần: chỉ lật PUBLISHED khi TẤT CẢ nơi trong
  tập hợp đều đăng thành công (giữ nguyên quy tắc: nút Đăng chỉ ghi
  lệnh, trạng thái chỉ lật khi Muse đăng thật + gắn link). Nơi thất
  bại được ghi nhận (botctl `set-output-place-failed`) và báo rõ
  từng nơi thành công/thất bại; đầu ra ở lại chờ đăng với link của
  nơi đã xong được giữ lại; lần đăng lại chỉ đăng tiếp các nơi chưa
  xong (không đăng trùng nơi đã xong).
  (6) Thu hồi: thu hồi Facebook phải XOÁ THẬT ở TẤT CẢ các nơi đã
  đăng thành công, kiểm chứng từng nơi biến mất rồi mới lật
  RETRACTED (botctl `set-output-retracted --place` từng nơi).
  (7) Đặt lịch: lịch đăng Facebook lưu cả tập hợp nơi đăng; đến giờ
  phát lệnh với đúng tập hợp đó; đăng ngay hủy lịch như cũ.
  (8) Không đổi: phân quyền, các kênh khác, luồng duyệt, thẻ nháp
  telegra.ph, audit/state semantics ngoài phần target Facebook này.
  (9) Bản app 0.4.1 → 0.5.0 (VERSION, APP_VERSION, ?v=0.5.0, SW
  cache v8, dòng phiên bản trong app). Mini App đang tạm dừng chưa
  gắn số phiên bản nào nên 0.5.0 không xung đột; khi Mini App tiếp
  tục sẽ bump tiếp từ 0.5.0.
- Ảnh hưởng: SRS mục 3.x (luồng đăng Facebook, đặt lịch, thu hồi),
  schema outputs + bảng facebook_pages mới; kiểm thử: webapp 53/53
  + test mới, bot 215/215 + test mới. Sao lưu trước khi sửa tại
  data/backup-fbmulti-20261024-143152/ (bản sao webapp + bot.db).
- Trạng thái SRS: ✅ Đã tổng hợp vào **SRS 1.4** ngày 25/10/2026

---

### TD-0014 — Giao diện: dải chip lọc nổi bật, danh sách gập/mở được, danh sách cuộn đúng, sửa thông báo tràn link dài (bản 0.5.1)
- Ngày: 24/10/2026 — Người yêu cầu: chủ dự án (2 phản hồi qua ảnh
  chụp: hàng chip lọc ngang "nhìn chìm, cần nổi bật lên để dễ nhận
  biết", danh sách bên dưới "làm collapse và có button thu nhỏ,
  nói chung các danh sách nên làm scroll"; và thẻ thông báo "Bài đã
  được đăng" của CV-0013 bị link Facebook permalink dài tràn ra
  khỏi thẻ).
- Nội dung thay đổi (CHỈ giao diện/bố cục, KHÔNG đổi API, schema,
  audit/state semantics, phân quyền, logic nghiệp vụ, logic target
  Facebook của TD-0013, luồng bot, tunnel, vapid.json, uploads):
  (1) Hàng chip lọc: thành dải riêng nền teal nhạt (sáng #f0fdfa,
  tối #134e4a), chữ chip đậm hơn (800), chip chưa chọn viền teal
  rõ, chip đang chọn giữ nền teal đậm + chữ trắng + số đếm; vẫn
  trượt ngang như cũ và có fade ở mép phải khi còn cuộn được
  (lớp has-more bật/tắt bằng JS theo trạng thái cuộn thật).
  (2) Danh sách có nút thu nhỏ: đầu danh sách việc, chờ duyệt, lịch
  đăng, người dùng thêm nút "▾ Thu gọn / ▸ Mở rộng" kèm số lượng;
  bấm gập cả phần thân danh sách, bấm nữa mở ra; lựa chọn nhớ vào
  localStorage (đúng mẫu sidebar collapse đã có: gv-tasklist-,
  gv-review-, gv-schedule-, gv-users-collapsed). Nhóm ngày của
  thông báo/lịch đăng đã gập được từ TD-0011 nên KHÔNG chồng thêm
  nút.
  (3) Quyết định cuộn theo từng màn (ghi rõ): desktop (≥821px) các
  danh sách chính (việc, chờ duyệt, lịch đăng, người dùng) có vùng
  cuộn dọc riêng (max-height calc(100dvh - 240px), overflow-y:auto)
  để bộ lọc/tiêu đề luôn thấy; mobile (≤820px) giữ cuộn trang tự
  nhiên (tránh cuộn lồng khó dùng trên màn nhỏ) nhưng tuyệt đối
  không tràn ngang (html/body đã overflow-x:hidden + min-width:0
  cho .list và thẻ thông báo). Danh sách hoạt động trên Tổng quan
  giữ vùng cuộn 440px từ TD-0011, không đổi. Nhóm thông báo theo
  ngày giữ cuộn trang (nội dung mỗi nhóm ngắn, đã gập được).
  (4) Sửa thông báo tràn link dài: khối chữ trong thẻ thông báo
  ngắt được chuỗi dài không khoảng trắng (overflow-wrap:anywhere
  trên .row-main và .muted trong .notification, min-width:0 cho
  thẻ), áp cho cả màn Thông báo lẫn khối hoạt động trên Tổng quan
  (cùng dùng notificationRow).
  (5) Bản app 0.5.0 → 0.5.1 (VERSION, APP_VERSION, ?v=0.5.1, SW
  cache v9, dòng phiên bản trong app). Không đụng nút Giao việc
  Mẫu 1 (58px, nhô ~7px, gradient, viền trắng, không đổ bóng),
  nhãn một dòng, badge tròn, dark mode theo hệ thống.
- Ảnh hưởng: chỉ thẩm mỹ/bố cục. Kiểm thử: webapp 54/54 + test mới,
  bot 230/230.
- Trạng thái SRS: ✅ Đã tổng hợp vào **SRS 1.4** ngày 25/10/2026

---

### TD-0015 — Sửa 6 việc: khóa nơi đang chờ đăng, link Facebook kiểu cũ, thông báo web khi đăng/thu hồi qua botctl, badge PWA, icon xem thêm, tải thêm tư liệu muộn (bản 0.5.2)
- Ngày: 24/10/2026 — Người yêu cầu: chủ dự án (phản hồi sau 0.5.1:
  chọn đăng rồi thì nơi đó phải khóa — bằng chứng CV-0014 có 2
  audit publish_requested giống nhau cho profile; web không hiện
  link bài Facebook đã đăng kiểu cũ; web không có thông báo khi
  đăng/thu hồi qua botctl; không hiện badge ở icon khi ghim web ra
  màn chính; đổi icon xem thêm ở menu trang chính; thêm tư liệu
  sau khi gửi Muse thì có tác dụng gì).
- Nội dung thay đổi:
  (1) Khóa nơi đang chờ: tập khóa = nơi đã đăng xong ∪ (tập lệnh
  đang chờ − nơi đã đăng − nơi đăng lỗi); nơi đang chờ hiện
  disabled "· đang chờ đăng", nơi lỗi vẫn chọn được để đăng lại.
  Áp cho modal Đăng ngay + Đặt lịch (webapp) và màn chọn bot.
  Bất biến đã xác minh trước khi code: nơi lỗi vẫn nằm trong
  publish_targets (mark_fb_place_failed không dọn tập lệnh) nên
  "đang chờ" phải tính request − done − failed. Phân biệt lịch
  chờ giờ (scheduled_at còn → không khóa, để sửa lịch được) với
  lệnh đăng đang chạy (scheduled_at rỗng). Hủy đăng (webapp
  publish-abort + bot publish abort) nay dọn publish_targets để
  lệnh đã hủy không khóa oan vĩnh viễn. Server chặn: lệnh đăng mà
  toàn bộ nơi chọn đều đã khóa thì từ chối 409 kèm tên nơi bị
  khóa; chọn lẫn nơi khóa + nơi mở thì chỉ đăng nơi mở và báo rõ
  nơi bị bỏ qua; không chặn đăng lại nơi lỗi.
  (2) Link kiểu cũ: đầu ra PUBLISHED/RETRACTED có public_url nhưng
  publish_target NULL (CV-0012/0013/0014) nay hiện link: fb_state
  suy ra nơi đăng từ audit publish_requested gần nhất (targets=
  rồi target=); không có target trong audit thì dùng key "legacy"
  hiển thị "Facebook". Key "legacy" chỉ để hiển thị, không lọt
  vào danh sách done của modal (modal lọc theo nơi hợp lệ).
  (3) Thông báo web khi botctl đăng/thu hồi: set-output-published
  (kể cả --place), set-output-place-failed, set-output-retracted
  (kể cả --place) đồng thời ghi hàng web_notification_items
  (INSERT OR IGNORE, key theo mẫu published:/publish_failed:/
  retracted: + id đầu ra + id audit) kèm link từng nơi;
  --no-notify tắt cả Telegram lẫn web. Lưu ý: bảng này là global
  (mọi người dùng đều thấy, như dòng tổng kết ngày) nên hàng mới
  tới được người tạo + người duyệt/Admin (và cả người dùng khác);
  người tạo có thể thấy trùng với dòng suy ra từ trạng thái (dòng
  global mang link từng nơi, dòng suy ra chỉ mang link đầu tiên).
  (4) Badge PWA: đồng bộ navigator.setAppBadge(số chưa đọc) mỗi
  khi tải/làm mới hộp thông báo, xóa badge khi đã đọc hết; chỉ
  gọi khi API hỗ trợ. Service worker cũng đồng bộ badge khi nhận
  push (fetch số chưa đọc, best-effort). Giới hạn: iOS không hỗ
  trợ Badging API nên badge chỉ chạy trên Android/Chrome (và
  Chrome desktop).
  (5) Icon xem thêm: nút "Thêm" ở thanh dưới đổi từ ▦ sang •••
  (duy nhất một chỗ dùng ▦).
  (6) Tải thêm tư liệu muộn: form tải thêm hiện chú thích khi việc
  đã có thẻ kênh (tư liệu mới chỉ gắn vào việc, Muse chưa được
  báo — nhắn Muse nếu muốn dùng); khi thêm file vào việc đã có
  thẻ kênh thì gửi thông báo đẩy web cho người duyệt/Admin (kể
  cả Admin) qua _notify_async. Giữ nguyên phân quyền (chỉ người
  tạo/Admin) và không đổi trạng thái việc.
  (7) Bản app 0.5.1 → 0.5.2 (VERSION, APP_VERSION, ?v=0.5.2, SW
  cache v10, dòng phiên bản trong app).
- Ảnh hưởng: webapp + bot (storage/botctl dùng chung); không đổi
  phân quyền, luồng duyệt, đường đăng trình duyệt. Kiểm thử:
  webapp 57/57 (54 cũ + 3 mới), bot 242/242 (230 cũ + 4 mới × 3 lớp
  test); probe trên bản sao DB thật đạt (link legacy CV-0013,
  khóa đúng, hàng web botctl, hủy dọn request; sha DB thật không
  đổi); health local + public 0.5.2, đủ 5 service active.
- Trạng thái SRS: ✅ Đã tổng hợp vào **SRS 1.4** ngày 25/10/2026

---

### TD-0016 — Nút X đóng modal ở góc phải trên (bản 0.5.3)
- Ngày: 24/10/2026 — Người yêu cầu: chủ dự án (phản hồi qua ảnh chụp
  modal "Chọn nơi đăng Facebook": modal chỉ có "Hủy đăng" (hủy luôn
  lệnh đăng) và nút Đăng bị khóa khi 0 nơi — không có cách thoát
  trung lập).
- Nội dung thay đổi (CHỈ giao diện): khung modal dùng chung
  (openModal) thêm nút X góc phải trên, hiện trên MỌI modal (Đăng,
  Đặt lịch, xác nhận, nhập lý do, đổi mật khẩu...). Bấm X chỉ ĐÓNG
  modal, không có tác dụng phụ — tuyệt đối không gọi publish-abort,
  không xác nhận gì cả; với modal kiểu xác nhận thì X tương đương
  từ chối (giống bấm ra nền modal). Vùng chạm tối thiểu 40px, hiển
  thị rõ cả sáng lẫn tối, không đè tiêu đề (tiêu đề modal chừa đệm
  phải).
- Ảnh hưởng: chỉ giao diện. Bản 0.5.2 → 0.5.3 (VERSION, APP_VERSION,
  ?v=0.5.3, SW cache v11). Kiểm thử: webapp + bot phải xanh, thêm
  test tĩnh cho nút đóng modal.
- Trạng thái SRS: ✅ Đã tổng hợp vào **SRS 1.4** ngày 25/10/2026

---

### TD-0017 — botctl đăng/thu hồi gửi kèm Web Push (bản 0.5.4)
- Ngày: 24/10/2026 — Nguồn: người dùng phản hồi (sự kiện đăng thật
  không làm điện thoại buzz; hộp inbox web vẫn có hàng nên lỗi chỉ
  là thiếu push, không phải thiếu inbox).
- Nội dung thay đổi: `_notify_web` trong botctl sau khi ghi hàng
  web_notification_items đồng thời gửi Web Push tới MỌI subscription
  trong web_push_subscriptions — khớp tính global của hàng inbox
  (hàng ai cũng thấy thì push cũng tới mọi người đăng ký; không thu
  hẹp lặng lẽ). Payload đúng dạng service worker GĐ3 hiển thị được:
  {title, body, url} với url = /?task=<mã việc>. Tái sử dụng
  send_to_subscription của webapp/push.py (import qua sys.path tới
  thư mục webapp, guard lỗi → cảnh báo + chỉ ghi hàng); KHÔNG copy
  code crypto sang botctl; KHÔNG tự tạo vapid.json nếu thiếu (tạo
  khóa mới sẽ làm hỏng mọi subscription cũ — thiếu file thì cảnh
  báo + bỏ qua push). --no-notify tắt cả Telegram, hàng web và push;
  thiếu token Telegram không chặn push web; lỗi push chỉ cảnh báo
  stderr, không làm hỏng exit code hay luồng chính; không có
  subscription thì gửi 0 cái, không lỗi. Log chỉ đếm sent/failed/
  gone, không in endpoint, khóa hay payload.
- Kỹ thuật: thêm WebDB.push_subscriptions_all() (webapp/db.py, cộng
  thêm); botctl thêm `_WEB_PUSH_SENDER` (điểm chích cho test) +
  `_send_web_push`/`_web_push_service`; `_notify_web` thêm tham số
  task_code tùy chọn để làm deep-link (6 điểm gọi truyền
  args.task_code).
- Ảnh hưởng: botctl + webapp/db.py (cộng thêm); không đổi nội dung/
  cơ chế thông báo Telegram, định dạng hàng inbox, phân quyền, luồng
  đăng/thu hồi, logic target Facebook. Bản 0.5.3 → 0.5.4 (VERSION,
  APP_VERSION, ?v=0.5.4, SW cache v12).
- Trạng thái SRS: ✅ Đã tổng hợp vào **SRS 1.4** ngày 25/10/2026

---

### TD-0018 — Modal nơi đăng không trống oan, đồng bộ sống, badge/push app Brave đã ghim (bản 0.5.5)
- Ngày: 25/10/2026 — Người yêu cầu: chủ dự án (test CV-0016 lúc
  00:27-00:33, 3 lỗi).
- (A) Modal "Chọn nơi đăng Facebook" trống hoàn toàn với CV-0016
  (output facebook id 26 DRAFT, chưa có target): nguyên nhân
  fbTargets() cache luôn [] khi gọi /api/facebook-targets lỗi —
  modal sau đó không bao giờ thử lại. Sửa: chỉ cache khi tải thành
  công và danh sách không rỗng; lỗi/rỗng trả null (không cache) và
  modal hiện trạng thái lỗi + nút "Thử lại". Dòng "Tất cả nơi đăng
  đều đã xong..." chỉ hiện khi tải được targets và không còn nơi
  nào chọn được. Áp cả modal Đăng và Đặt lịch; nơi đã đăng/đang
  chờ vẫn hiện hàng disabled có nhãn.
- (B) Đồng bộ sống: trước đây không có setInterval, visibilitychange
  hay postMessage SW → client, app đang mở không tự cập nhật. Sửa:
  poll 30 giây (chỉ khi tab hiển thị, có chặn gọi chồng) tải lại
  thông báo + badge; quay lại app (visibilitychange) tải lại ngay
  dữ liệu màn hiện tại + thông báo + badge; SW khi nhận push
  postMessage "gv-push" cho client đang mở để tải lại. Poll chỉ
  gọi thông báo + badge (không tải lại danh sách để khỏi mất vị
  trí cuộn).
- (C) Badge/push app Brave đã ghim: đã xác minh bằng MDN + web.dev
  (không đoán): Badging API KHÔNG hỗ trợ trên trình duyệt Chromium
  ở Android — setAppBadge ở đó là no-op, Android chỉ tự hiện chấm
  thông báo khi còn thông báo chưa đọc; Brave không có máy chủ
  mint WebAPK nên "ghim" chỉ tạo lối tắt (icon có logo Brave,
  đúng ảnh người dùng gửi), không có icon trong Launcher/Cài đặt,
  không dùng được khả năng chỉ dành cho app cài đặt. Vì vậy badge
  số trên icon là không làm được ở Brave Android — thông báo đẩy
  là đường duy nhất để có chấm thông báo; subscription là theo
  từng trình duyệt (Brave cần bật riêng). Sửa: màn Thông báo thêm
  chú thích ngắn nói rõ 2 điểm này + gợi ý cài bằng Chrome để có
  app thật (WebAPK); nút "Gửi thử" trả về đếm sent/total (bỏ
  trường results lộ endpoint), giao diện hiện "Đã gửi tới N/T
  thiết bị". Badge trong app vẫn cập nhật ở mọi lần số chưa đọc
  đổi (tải trang, poll, quay lại app, nhận push, đánh dấu đã đọc)
  qua updateBadges; SW push-time giữ nguyên.
- Ảnh hưởng: chỉ webapp (bot không đổi). Bản 0.5.4 → 0.5.5 (VERSION,
  APP_VERSION, ?v=0.5.5, SW cache v13). Kiểm thử: webapp + bot phải
  xanh; test mới: fbTargets không cache lỗi/rỗng, modal lỗi + thử
  lại, poll/visibility refresh, SW postMessage, /api/push/test trả
  sent/total không lộ endpoint.
- Trạng thái SRS: ✅ Đã tổng hợp vào **SRS 1.4** ngày 25/10/2026

---

### TD-0019 — Thêm mục "Đã duyệt · chờ đăng" vào menu Thêm (bản 0.5.6)
- Ngày: 25/10/2026 — Người yêu cầu: chủ dự án ("Ở nút Thêm, cho
  thêm trạng thái Duyệt - chờ đăng").
- Nội dung thay đổi (CHỈ giao diện): menu Thêm (nút •••) có thêm
  mục "✅ Đã duyệt · chờ đăng" cho người có quyền duyệt, mở màn Việc
  với bộ lọc trạng thái đặt sẵn APPROVED_WAITING (tái dùng chip lọc
  sẵn có + deep-link #tasks?status=APPROVED_WAITING, không tạo màn
  mới). Mục này cũng hiện trực tiếp ở sidebar desktop (cùng hành vi).
  Nút Thêm hiện active khi đang ở mục mới; nút Việc chỉ active khi
  không ở mục mới. Huy hiệu số lượng: đếm việc ở trạng thái
  APPROVED_WAITING lấy từ `counts` của GET /api/tasks?limit=1 — đúng
  số chip lọc hiện trên màn Việc — cập nhật cùng cơ chế refreshBadge
  (chỉ với người có quyền duyệt, lỗi thì giữ nguyên số cũ).
- Ảnh hưởng: chỉ webapp (bot không đổi). Bản 0.5.5 → 0.5.6 (VERSION,
  APP_VERSION, ?v=0.5.6, SW cache v14). Kiểm thử: webapp + bot phải
  xanh; test mới: mục chỉ hiện với người duyệt, bấm mở đúng màn Việc
  lọc APPROVED_WAITING, nút Thêm active ở mục mới, badge đếm đúng.
- Trạng thái SRS: ✅ SRS 1.5

---

### TD-0020 — Mini App Telegram (bề mặt thêm, cùng backend + bot.db) (bản 0.5.7)
- Ngày: 25/10/2026 — Người yêu cầu: chủ dự án ("Ok rồi; làm miniapp",
  tiếp tục sau khi tạm dừng từ 19:10 ngày 24/10). Bot Telegram và Web
  App PWA giữ nguyên toàn bộ, KHÔNG chuyển đội, KHÔNG tắt dần bot
  (GĐ4 vẫn tạm dừng theo lệnh "Không chuyển nhé" ngày 24/10).
- Nội dung thay đổi:
  - Entry Mini App `/miniap/` (+ `/miniap/index.html`) phục vụ cùng
    shell PWA (app.js/styles.css/API), không viết lại giao diện.
    Frontend nhận biết chế độ Mini App (đường dẫn /miniap hoặc
    `window.Telegram.WebApp`), tải Telegram WebApp SDK, áp themeParams
    lên biến màu CSS, expand viewport, nút Back hệ thống theo route,
    MainButton ở bước cuối wizard giao việc, haptic cho thao tác chính.
    Không hiện màn đăng nhập email/mật khẩu trong Mini App; ẩn nút đổi
    mật khẩu/đăng xuất (Mini App gắn với danh tính Telegram).
  - Xác thực bằng Telegram initData: `POST /api/auth/telegram`
    kiểm chứng chữ ký HMAC-SHA256 theo đúng chuẩn Telegram
    (secret = HMAC-SHA256("WebAppData", bot_token), data-check-string
    sắp xếp theo key, `auth_date` tối đa 24 giờ), map `user.id` sang
    users.telegram_id, chỉ người đã có vai trò mới vào được; cấp phiên
    web dùng chung cơ chế web_sessions (cookie + Bearer).
  - **Giới hạn cấu hình đã xác minh trước khi code:** token bot thật
    KHÔNG lấy được từ chỗ bot đang dùng — bot chỉ có surrogate
    `hsurr:` của kết nối custom.telegram (authd chỉ trả surrogate,
    không trả giá trị thật; không có TELEGRAM_BOT_TOKEN trong bất kỳ
    file /etc/default/* nào; unit bot ghi rõ token không đặt ở đó).
    Server đọc token từ biến môi trường `TELEGRAM_BOT_TOKEN`; khi
    chưa có thì endpoint trả 503 "Mini App chưa được cấu hình" và Mini
    App hiện thông báo rõ. Muốn đăng nhập thật bằng Mini App cần cấp
    token qua Secure Vault rồi đặt vào /etc/default/webapp-giao-viec
    (mode 600) và restart webapp. Test/probe dùng token test riêng
    trong fixture, KHÔNG dùng token thật, KHÔNG commit token.
  - Phía bot: `setChatMenuButton` (WebApp → URL Mini App) đặt theo
    từng chat của người đã có vai trò (kèm đồng bộ khi cấp/thu hồi
    quyền), lệnh `/miniap` gửi nút mở Mini App; khách lạ bấm vào thì
    Mini App tự từ chối đăng nhập, không lộ dữ liệu.
  - **Sửa sau kiểm chứng sống (25/10, trong đợt TD-0020):**
    (1) Bot API hiện tại KHÔNG có `deleteChatMenuButton` (đối chiếu
    docs chính thức Bot API 10.3: chỉ còn set/getChatMenuButton; gọi
    phương thức đã bỏ trả HTTP 404) — nhánh thu hồi quyền nay reset
    nút bằng `setChatMenuButton` với `{"type": "default"}`.
    (2) `setChatMenuButton` KHÔNG có tham số `scope` (tham số đó chỉ
    thuộc `setMyCommands`); bản đầu truyền `scope` nên Telegram lờ
    đi và đặt nhầm nút WebApp lên nút MẶC ĐỊNH chung (mọi người dùng
    kể cả khách lạ đều thấy), còn chat Admin vẫn ở `default`. Nay
    truyền đúng `chat_id`. Kiểm chứng sống sau sửa: chat Admin →
    web_app "Mở Mini App", nút mặc định → `commands`. Lưu ý: thay
    đổi nút mặc định lan truyền chậm (~2 phút mới đọc lại được giá
    trị mới), thay đổi theo chat thì gần như tức thì.
- Ảnh hưởng: webapp (auth + entry + SDK) và bot (menu button +
  /miniap); không đổi hành vi bot/PWA hiện tại, phân quyền, luồng
  duyệt/đăng/lịch, thông báo/push. Bản 0.5.6 → 0.5.7 (VERSION,
  APP_VERSION, ?v=0.5.7, SW cache v15). Kiểm thử: webapp + bot phải
  xanh; test mới: kiểm chứng initData (đúng cho qua, sai/tamper/hết
  hạn bị từ chối, user lạ/không vai trò bị từ chối), menu button +
  /miniap, entry Mini App trả đúng shell.
- Trạng thái SRS: ✅ SRS 1.5

---

### TD-0021 — Chẩn đoán lỗi đăng nhập Mini App thật: ghi lý do từ chối + hiện đúng lý do (bản 0.5.8)
- Ngày: 25/10/2026 — Người yêu cầu: chủ dự án (mở Mini App thật
  trên điện thoại thì hiện "Phiên đăng nhập đã hết hạn.").
- Chẩn đoán trước khi sửa: token bot đã xác minh ĐÚNG bằng getMe
  trực tiếp (200, đúng id 8884085259, đúng @iaict_media_bot); bộ kiểm
  chứng initData đã qua initData thực tế (đủ field, chữ ký dummy,
  tên có dấu + emoji, photo_url có query) đều trả 200; nhưng 3 lần mở
  Mini App thật (09:45-09:46 ngày 25/10) đều bị POST
  /api/auth/telegram trả 401. Nguyên nhân thật chưa biết vì thông báo
  "Phiên đăng nhập đã hết hạn." là câu chung chung mà `api()` ném ra
  cho MỌI 401 (kể cả khi server đã trả lý do cụ thể trong body) —
  lý do thật của server bị che mất.
- Nội dung thay đổi: (a) server ghi log chẩn đoán mỗi lần
  POST /api/auth/telegram bị từ chối — CHỈ message lỗi + danh sách
  TÊN field có trong initData (không log giá trị, hash, token hay
  initData nguyên văn); (b) `api()` với 401 ở đúng
  /api/auth/telegram thì hiện đúng message của server thay vì câu
  chung chung.
- Nguyên nhân gốc (tìm ra cùng ngày nhờ log TD-0021 + đối chiếu tài
  liệu Telegram): bộ kiểm chứng loại cả `signature` khỏi
  data-check-string — SAI. Tài liệu Telegram (core.telegram.org/
  bots/webapps và docs.telegram-mini-apps.com/platform/init-data)
  quy định đường HMAC chỉ loại `hash`; `signature` chỉ bị loại ở
  đường kiểm chứng Ed25519 bên thứ ba (cấu trúc khác, có tiền tố
  `bot_id:WebAppData`). initData thật luôn có `signature` nên mọi
  lần đăng nhập thật đều lệch HMAC → 401 "Chữ ký xác thực Telegram
  không hợp lệ.", trong khi fixture test không có `signature` nên
  vẫn đậu — test cũ `test_signature_field_is_excluded_from_check_
  string` còn khẳng định hành vi sai. Sửa: chỉ loại `hash` (cả
  `validate_init_data` lẫn `sign_init_data` dùng chung
  `_EXCLUDED_FIELDS`); test cũ đổi thành
  `test_signature_field_is_included_in_check_string` + thêm control
  âm `test_signature_excluded_hash_is_rejected`. Không đổi phân
  quyền hay luồng đăng nhập.
- Ảnh hưởng: chỉ chẩn đoán + thông báo lỗi. Bản 0.5.7 → 0.5.8
  (VERSION, APP_VERSION, ?v=0.5.8, SW cache v15→v16). Kiểm thử:
  webapp + bot phải xanh, thêm test cho body lỗi 401 và dấu vết
  frontend.
- Trạng thái SRS: ✅ SRS 1.5

---

### TD-0022 — Mọi danh sách liên quan đến việc đều có scroll, "Xem thêm" và "Thu gọn" (bản 0.5.9)
- Ngày: 25/10/2026 — Người yêu cầu: chủ dự án ("Tất cả các danh
  sách liên quan đến việc đều cho scroll, xem thêm và thu gọn").
- Hiện trạng trước khi sửa: toggle ẩn/hiện cả mục (▾ Thu gọn /
  ▸ Mở rộng, lưu localStorage) đã có ở Việc/Chờ duyệt/Lịch đăng
  (TD-0014); scroll vùng riêng đã có ở #taskList/.list-scroll
  (desktop) và khối Hoạt động ở Tổng quan (.activity-scroll);
  CHƯA có "Xem thêm" ở bất kỳ danh sách nào; "Việc gần đây" ở Tổng
  quan cắt cứng 6 mục, không scroll/không thu gọn; màn Thông báo vẽ
  toàn bộ mục trong `.list` thường, không scroll/không thu gọn;
  thẻ kênh ở Chi tiết việc cần rà soát.
- Nội dung thay đổi: mẫu thống nhất cho mọi danh sách liên quan
  đến việc — (a) vùng scroll riêng (desktop: max-height +
  overflow-y auto theo mẫu .list-scroll; mobile: cuộn trang tự
  nhiên, không tràn ngang); (b) "Xem thêm" hiện thêm theo đợt
  trên dữ liệu đã tải về (mặc định 10 mục ở danh sách chính, 6 mục
  ở khối Tổng quan; hết mục thì ẩn nút); (c) "Thu gọn" thu lại về
  số mục mặc định khi đã mở rộng. Giữ nguyên toggle ẩn/hiện cả mục
  của TD-0014. Phạm vi: Việc, Chờ duyệt, Lịch đăng, Việc gần đây +
  Hoạt động (Tổng quan), Thông báo, thẻ kênh ở Chi tiết việc (đánh
  giá; nếu ít mục thì ghi rõ lý do không áp dụng). Không đổi danh
  sách Tài khoản (không liên quan đến việc).
- Ảnh hưởng: chỉ giao diện danh sách, không đổi API hay logic
  lọc/duyệt/đăng. Bản 0.5.8 → 0.5.9 (VERSION, APP_VERSION, ?v=0.5.9,
  SW cache v16→v17). Kiểm thử: webapp + bot phải xanh, thêm test
  cho mẫu mới; probe Playwright mobile 390 + desktop 1440
  (sáng + tối): nút Xem thêm/Thu gọn hoạt động, đếm đúng số mục,
  không tràn ngang, scroll vùng riêng trên desktop.
- Trạng thái SRS: ✅ SRS 1.5

---

### TD-0023 — Hàng chip lọc trạng thái: nền nổi hơn, nút chip sửa theo cho hợp (bản 0.5.10)
- Ngày: 25/10/2026 — Người yêu cầu: chủ dự án (kèm ảnh chụp hàng
  chip "Tất cả 16 / Nháp 4 / Chờ…": "Xử lý chỗ này để có background
  nổi hơn; các Button cũng phải sửa theo cho hợp").
- Hiện trạng trước khi sửa (TD-0014): `.status-chips-wrap` nền
  #f0fdfa rất nhạt, viền #ccfbf1; chip thường nền trắng, viền
  #5eead4; chip đang chọn `background:var(--teal)` + chữ trắng.
  Ảnh người dùng gửi cho thấy chip đang chọn vẫn nhạt/trắng — cần
  kiểm chứng khi làm xem style đang chọn có thực sự áp dụng không
  (màu tính toán của chip đang chọn), nếu không áp dụng thì sửa
  tận nguyên nhân chứ không chỉ tô lại màu.
- Nội dung thay đổi: nền dải chip đậm và rõ ranh giới hơn (đọc
  được ngay là một dải riêng trên mobile); nút chip sửa theo cho
  hợp — chip thường rõ viền/nền/độ tương phản hơn, chip đang chọn
  khác biệt không thể nhầm (nền teal đậm + chữ trắng + pill đếm
  đọc được), trạng thái hover/focus nhất quán; giữ cuộn ngang +
  fade mép phải (gradient fade phải khớp nền dải mới). Giữ nguyên
  hành vi lọc, đếm, JS fade và mẫu pager của TD-0022. Sáng + tối
  đều phải chuẩn.
- Ảnh hưởng: chỉ CSS hàng chip (và markup chip nếu cần). Bản
  0.5.9 → 0.5.10 (VERSION, APP_VERSION, ?v=0.5.10, SW cache
  v17→v18). Kiểm thử: webapp + bot phải xanh, thêm test cho dấu
  vết mới; probe Playwright mobile 390 + desktop 1440 (sáng +
  tối): chụp hàng chip, chip đang chọn khác biệt rõ, không tràn
  ngang.
- Trạng thái SRS: ✅ SRS 1.5

---

### TD-0024 — Tải video lớn chia nhỏ + lưu trữ bản gốc lên Google Drive + xóa sau khi đăng thành công (bản 0.5.11)
- Ngày: 25/10/2026 — Người yêu cầu: chủ dự án. Xuất phát từ câu
  hỏi "tải video nặng cả 1GB lên thì sao?": hiện tại file 1GB không
  tải lên được (wizard chặn >200MB ngay trong trình duyệt; mục Thêm
  tư liệu không có bước chặn nên trình duyệt tải lên rồi bị Cloudflare
  cắt ở 100MB với lỗi 413 — Cloudflare gói Free/Pro giới hạn mỗi lần
  gửi 100MB, Business 200MB, Enterprise tối đa 5GB; máy chủ giới hạn
  mỗi file 200MB và mỗi lần gửi tối đa 1GB). Cloudflare Tunnel không
  tính tiền theo dung lượng (băng thông unmetered), nên tải nhiều
  không phát sinh hóa đơn Cloudflare; chi phí thật là thời gian tải,
  data điện thoại và ổ đĩa máy chủ (còn trống 98GB).
- Quyết định của chủ dự án (25/10, đính chính lần 2 cùng ngày): (a)
  **đăng thành công thì xóa file của bài đó khỏi máy chủ, bài nào cũng
  vậy** — không chỉ video 1GB; (b) **lưu trữ lên Google Drive của chủ
  dự án** ("lưu tẹt bô") trước khi xóa, để sau này cần thì lấy lại từ
  đó được. Điểm kỹ thuật bắt buộc: file của một việc dùng chung cho
  nhiều kênh (cùng ảnh cho Facebook + Instagram) nên chỉ xóa khi TẤT
  CẢ đầu ra của việc đó đều đã đăng thành công; xóa theo từng đầu ra
  riêng lẻ sẽ làm kênh còn lại mất file để đăng.
- Phương án thay thế chủ dự án nêu (25/10, chưa chọn): tải lên thẳng
  Google Drive, máy chủ lấy data từ đó. Khuyến nghị KHÔNG chọn vì:
  máy chủ vẫn cần bản local để dựng video bằng ffmpeg, đăng Facebook,
  hiện ảnh thu nhỏ — nghĩa là mỗi lần dùng lại phải tải file từ Drive
  về (chậm qua proxy, phụ thuộc Google API + token OAuth), và việc tải
  từ điện thoại lên thẳng Drive cũng không nhanh hơn hay nhẹ data hơn;
  connector Drive hiện chỉ có upload từ file local trên máy chủ
  (`hatch_gws_cli drive +upload`), chưa có luồng tạo resumable session
  cho trình duyệt tải thẳng.
- Quyết định cuối (25/10 13:20): chọn CÁCH A — tải lên máy chủ, đăng
  xong thì lưu Drive rồi xóa. Google Drive đã nối xong cùng ngày
  (trước khi chọn). Giới hạn mỗi file chốt 2GB cho đường tải chia nhỏ.
- Nội dung thay đổi: (a) tải lên chia nhỏ có tiếp tục được (chunked/
  resumable): trình duyệt cắt file thành miếng ~50MB (dưới ngưỡng
  100MB của Cloudflare và dưới timeout 100 giây mỗi miếng), gửi lần
  lượt, máy chủ ráp lại thành file hoàn chỉnh bằng cách ghi nối ra
  đĩa (không giữ cả file trong RAM), rớt mạng thì tiếp tục từ miếng
  dở dang; nâng giới hạn mỗi file của máy chủ lên 2GB (đã chốt),
  giữ nguyên giới hạn 1GB cho lần gửi đơn không chia nhỏ; bổ sung
  bước kiểm tra kích thước + thông báo còn thiếu ở mục Thêm tư liệu;
  (b) khi TẤT CẢ đầu ra của một việc đều đã đăng thành công: tải toàn
  bộ file tư liệu của việc đó lên Google Drive của chủ dự án (thư mục
  riêng, chốt khi làm; triển khai bằng `hatch_gws_cli drive +upload`
  từ máy chủ) rồi mới xóa các file đó khỏi máy chủ; (c) bản xem trước/
  bản nháp luôn dùng bản đã nén bằng ffmpeg (vài chục MB), không bao
  giờ phát bản gốc 1GB (bản gốc >512MB không được Cloudflare cache
  nên mỗi lần xem lại kéo đủ 1GB qua tunnel). Mở: việc không bao giờ
  đăng (hủy/bỏ dở) cần quy tắc dọn riêng (vd xóa khi hủy việc, hoặc
  sau N ngày không hoạt động) — chờ chủ dự án chốt.
- Quy tắc bổ sung (25/10, gộp vào TD-0024): (d) việc nằm quá lâu ở
  trạng thái chờ duyệt (PENDING) hoặc chờ đăng (APPROVED_WAITING) —
  quá 48h kể từ khi đầu ra rơi vào trạng thái đó — thì đẩy toàn bộ
  file tư liệu của việc lên Google Drive (cùng thư mục lưu trữ) rồi
  xóa khỏi máy chủ; bản thân việc và trạng thái giữ nguyên, chỉ file
  chuyển chỗ. Không lưu trữ khi đang có lệnh đăng dở dang
  (publish_requested chưa hoàn tất). Ghi audit cho lần lưu trữ này.
  (e) khôi phục: khi cần dùng lại file đã lưu trữ thì tải lại từ
  Drive về máy chủ — nút "↩️ Tải lại từ Drive" ở Chi tiết việc khi
  file đang lưu trữ, và tự động tải lại khi bấm Đăng/Đặt lịch mà file
  chưa có trên máy chủ. (f) giới hạn tổng: toàn bộ file tư liệu trên
  máy chủ (kể cả thư mục tạm của tải chia nhỏ) không quá 9GB — đường
  tải lên từ chối file mới khi tổng dung lượng sẽ vượt 9GB (thông báo
  rõ lý do), và màn Thống kê hiển thị mức đã dùng (X/9GB). Cơ chế quét
  48h chạy nền định kỳ (tái dùng cơ chế job có sẵn của webapp, ví dụ
  luồng tổng kết 20:00).
- Điều kiện tiên quyết: Google Drive phải được nối thì mới xây/kiểm
  chứng được chân lưu trữ Drive; chân tải chia nhỏ không cần Drive.
  Đã nối xong 25/10 (trước khi chọn cách A).
- Ảnh hưởng: webapp (API tải chia nhỏ + hook sau khi đăng + dọn file)
  và bot (botctl/luồng đăng video — chỉ nếu hook chạm tới; ghi rõ khi
  làm). Bản 0.5.10 → 0.5.11 (VERSION, APP_VERSION, ?v=0.5.11, SW cache
  v18→v19). Kiểm thử: webapp + bot phải xanh, thêm test cho tải chia
  nhỏ (ghép đủ/thiếu miếng, tiếp tục sau rớt, từ chối miếng quá lớn)
  và cho quy tắc lưu trữ/xóa; probe Playwright + kiểm chứng thật với
  file lớn (vd 300MB) qua đường công khai.
- Trạng thái SRS: ⏳ Chờ cập nhật
- Kết quả (25/10, ĐÃ XONG — bản 0.5.11): (a) API tải chia nhỏ
  `POST /api/uploads/chunked/init|chunk|complete|status`, `DELETE`
  hủy phiên; miếng 50MB, ngưỡng dùng đường chia nhỏ >20MB, file nhỏ
  giữ đường đơn cũ; giới hạn ráp xong 2GB/file, đường đơn giữ 1GB;
  miếng tạm ở `data/files/.tmp/<upload_id>/`, dọn phiên dở >24h khi
  init mới; resume qua `upload_id` lưu localStorage + `GET status`
  (server tính lại danh sách miếng đã nhận từ file `.part` — chuẩn
  hơn meta.json); retry mỗi miếng tối đa 3 lần, thanh tiến trình theo
  từng file ở wizard và Thêm tư liệu; wizard chặn >2GB, Thêm tư liệu
  đã có bước chặn + thông báo rõ. (b) Lưu trữ/xóa: hook ở cả hai
  đường lật PUBLISHED trong `botctl set-output-published` (theo nơi
  đăng và không theo nơi); khi TẤT CẢ đầu ra (trừ đã hủy) đều
  PUBLISHED thì worker nền tách riêng (`archive_worker.py`, tách
  session, log `data/archive.log`) tải từng file lên Drive rồi mới
  xóa file local đó; Drive lỗi thì giữ file + ghi audit
  `files_archive_failed`, không xóa; lũy đẳng qua audit
  `files_archived` + bảng `archived_files` (không lưu lại lần hai);
  thư mục Drive "Giao Việc IAICT — Bản gốc" id
  `1tE5uJesfNh3X4t8cm5u4TNKUHfQzZ1d8`, mỗi việc một thư mục con, id
  lưu `data/drive_archive.json` (600, không commit); Chi tiết việc
  hiện file đã lưu dưới dạng link Drive thay vì ảnh vỡ. (c) Xem trước:
  video gốc >512MB chỉ hiện ô tải về, không phát inline; bản nháp
  video vẫn dùng bản nén ffmpeg. (d) Quét 48h: `scan_waiting_tasks`
  chạy trong luồng tổng kết sẵn có của webapp (tối đa 1 lần/giờ, qua
  `web_last_archive_scan`), đo từ audit `submit_output`/`approve_output`
  (fallback `created_at`); bỏ qua khi có lệnh đăng dở dang, khi chưa
  đủ 48h, khi không còn file local; audit `files_archived
  reason=waiting_48h`. (e) Khôi phục: nút "↩️ Tải lại từ Drive" ở Chi
  tiết việc + tự động tải lại khi bấm Đăng/Đặt lịch mà file thiếu
  (webapp `_act_publish`/`_act_schedule` và 4 điểm bấm Đăng/Đặt lịch
  của bot); tải về bằng `drive files get ... alt=media`, nền, kiểm
  tra đúng kích thước rồi mới xóa bản ghi lưu trữ. (f) Giới hạn 9GB:
  mọi đường tải lên của webapp (đơn + chia nhỏ, kiểm tra lúc init và
  lúc ráp) từ chối khi tổng `data/files/` (kể cả `.tmp`) sẽ vượt 9GB
  kèm thông báo rõ; Thống kê hiện "Đã dùng X / 9.0 GB" + thanh tiến
  trình. Hàm dùng chung: `archive.archive_task_files` +
  `archive.restore_task_files` (cả hai nút kích hoạt cùng gọi một
  chỗ), `scan_waiting_tasks`, `maybe_archive_task`,
  `maybe_restore_task`. Lệnh botctl mới: `archive-task-files`,
  `restore-task-files`.
- Sửa lỗi phát hiện trong lúc probe (gộp vào TD-0024): server không
  đọc body `{}` của `POST .../chunked/complete` (và `/restore`) nên
  2 byte thừa dính vào request line tiếp theo trên cùng kết nối
  keep-alive (`"{}GET /api/tasks/..."` → 501) — làm wizard dừng ở
  bước 3 ngay sau khi tải xong. Đây cũng chính là lỗi 501 bí ẩn ở
  TD-0013 (tưởng là tunnel). Sửa tận gốc: `_dispatch` bọc `_route`,
  `finally` xả (drain) body chưa đọc của mọi POST/PUT/PATCH/DELETE
  (`_read_json`, `_parse_multipart`, `_chunk_put` đánh dấu đã đọc);
  có test hồi quy keep-alive (complete rồi GET cùng kết nối → 200).
- Kiểm thử: webapp 87/87 (75 + 12 test mới TD-0024), bot 268/268
  (256 + 12 test mới). Probe Playwright trên BẢN SAO DB (DB thật
  không đổi — kiểm chứng: chỉ thêm 1 dòng `web_notification_reads`
  do chính người dùng đọc thông báo trong lúc probe; 16 việc, 26 đầu
  ra, 141 audit đều nguyên): API 25/25 (chunked 120MB thật: init/
  status/resume/gửi lại miếng/lắp ráp đúng từng byte; lưu trữ sau
  đăng + khôi phục qua botctl, file thật lên Drive rồi xóa ngay);
  UI 14/14 (wizard tải 120MB thật lên tới Chi tiết việc 120.0 MB;
  chặn >2GB ở wizard và Thêm tư liệu; thẻ dung lượng Thống kê;
  nút Tải lại từ Drive); quét 48h 7/7 (việc PENDING backdate 49h
  lên Drive + biến khỏi đĩa, trạng thái giữ PENDING, việc mới tạo
  không bị chạm); khôi phục 48h 11/11 (UI + botctl, file về đúng
  từng byte). Thư mục Drive gốc đã dọn sạch sau probe.
- Giới hạn còn tồn tại: (1) tốc độ upload Drive thật với file lớn
  chưa đo (probe chỉ tải file 14 byte; upload 1GB lên Drive qua
  proxy mất hàng phút, chạy nền nên không chặn đăng bài); (2) miếng
  50MB có thể chạm timeout 100s của Cloudflare trên đường truyền
  rất chậm (~2Mbps → ~200s/miếng; retry sẽ lỗi tiếp — cân nhắc giảm
  miếng xuống 25MB nếu người dùng hay tải bằng 4G yếu); (3) quota
  9GB chỉ chặn ở đường tải webapp, chưa chặn file gửi qua Telegram
  vào bot; (4) việc không bao giờ đăng (hủy/bỏ dở) vẫn chưa có quy
  tắc dọn — chờ chủ dự án chốt (như đã ghi ở phần Mở); (5) upload
  Drive chạy nền bằng tiến trình tách riêng, không có hàng đợi bền —
  nếu máy bị thay giữa lúc worker đang tải lên Drive thì lần tải đó
  mất, file local vẫn còn (an toàn) và lần quét/đăng sau sẽ thử lại.
- ⚠️ Phát hiện ngoài phạm vi TD-0024 (cần xử lý riêng): máy chủ bị
  thay đầu ngày 25/10, `restore-services.sh` đã tạo lại
  `/etc/default/webapp-giao-viec` nhưng KHÔNG có
  `TELEGRAM_BOT_TOKEN` (token Mini App người dùng cấp 25/10 chỉ nằm
  trong file đó + chat) — đăng nhập Mini App sẽ lỗi cho tới khi nhập
  lại token. Token không lưu ở đâu khác; cần người dùng cấp lại. | ✅ Đã vào SRS x.y

---

## Mục chờ cập nhật vào SRS

- **TD-0006** — ✅ Đã tổng hợp vào **SRS 1.1** ngày 24/10/2026 (đóng GĐ2).
- **TD-0007** — ✅ Đã tổng hợp phần tên miền/HTTPS vào **SRS 1.3** ngày 24/10/2026 (phần chuyển đội + tắt dần bot vẫn chờ GĐ4).
- **TD-0010** — ✅ Đã tổng hợp vào **SRS 1.3** ngày 24/10/2026 (thanh dưới mobile dạng nổi bo tròn, bản 0.3.2).
- **TD-0008** — ✅ Đã tổng hợp vào **SRS 1.2** ngày 24/10/2026 (đóng GĐ3).
- **TD-0009** — ✅ Đã tổng hợp vào **SRS 1.3** ngày 24/10/2026 (sửa giao diện mobile: thông báo đẩy/cache SW v4, bỏ trùng menu, lọc việc theo trạng thái, gọn block chọn file; bản 0.3.1).
- **TD-0011** — ✅ Đã tổng hợp vào **SRS 1.3** ngày 24/10/2026 (áp giao diện mới đã chốt: nav mobile 6 cột + nút Giao việc Mẫu 1, collapse/scroll, wizard footer nút chính lên trên, dark mode theo hệ thống; bản 0.4.0).
- **TD-0012** — ✅ Đã tổng hợp vào **SRS 1.4** ngày 25/10/2026 (sửa thanh điều hướng mobile: nút Giao việc 58px nhô ~7px, nút thanh dưới khi active nền trong suốt; bản 0.4.1).
- **TD-0013** — ✅ Đã tổng hợp vào **SRS 1.4** ngày 25/10/2026 (đăng Facebook nhiều nơi cùng lúc, sẵn sàng nhiều Fanpage; bản 0.5.0).
- **TD-0014** — ✅ Đã tổng hợp vào **SRS 1.4** ngày 25/10/2026 (dải chip lọc nổi bật, danh sách gập/mở được, danh sách cuộn đúng, sửa thông báo tràn link dài; bản 0.5.1).
- **TD-0015** — ✅ Đã tổng hợp vào **SRS 1.4** ngày 25/10/2026 (khóa nơi đang chờ đăng, link Facebook kiểu cũ, thông báo web khi đăng/thu hồi qua botctl, badge PWA, icon xem thêm, tải thêm tư liệu muộn; bản 0.5.2).
- **TD-0016** — ✅ Đã tổng hợp vào **SRS 1.4** ngày 25/10/2026 (nút X đóng modal ở góc phải trên; bản 0.5.3).
- **TD-0017** — ✅ Đã tổng hợp vào **SRS 1.4** ngày 25/10/2026 (botctl đăng/thu hồi gửi kèm Web Push; bản 0.5.4).
- **TD-0018** — ✅ Đã tổng hợp vào **SRS 1.4** ngày 25/10/2026 (modal nơi đăng không trống oan, đồng bộ sống, badge/push app Brave đã ghim; bản 0.5.5).
