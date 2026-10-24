# SRS — Đặc tả yêu cầu phần mềm: Web App Giao Việc IAICT

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản SRS | **1.0** (bản gốc — baseline) |
| Ngày hiệu lực | 24/10/2026 |
| Trạng thái | Đã chốt theo bản thiết kế được duyệt ngày 24/10/2026 |
| Sản phẩm | Web App Giao Việc (PWA) — hệ thống giao việc, duyệt và đăng bài truyền thông đa kênh của IAICT |
| Kho mã nguồn | github.com/dungnt-mhy/Web-giao-viec-media-iaict |
| Tài liệu liên quan | `README.md` (kiến trúc, cách chạy), `NHAT-KY-PHAT-TRIEN.md` (nhật ký xây dựng), `THAY-DOI.md` (sổ ghi thay đổi — nguồn để cập nhật các bản SRS sau) |

**Quy trình quản trị tài liệu:** mọi thay đổi yêu cầu phát sinh sau bản 1.0 được ghi
vào `THAY-DOI.md` trước. Cuối mỗi giai đoạn, các thay đổi được tổng hợp vào SRS
và SRS tăng phiên bản (1.1, 1.2, … hoặc 2.0 khi đổi lớn). Bảng lịch sử phiên bản
ở cuối tài liệu này.

**Quy ước trạng thái yêu cầu:**
- ✅ **Đã triển khai** — đã có trong hệ thống đang chạy (ghi rõ ở bot hay Web App).
- 🔶 **Đang triển khai** — thuộc giai đoạn Web App hiện tại.
- 📋 **Kế hoạch** — đã chốt hướng, chưa xây.

---

## 1. Giới thiệu

### 1.1 Mục đích

Tài liệu này đặc tả toàn bộ yêu cầu của Web App Giao Việc: hệ thống để đội
truyền thông IAICT **giao việc bằng tư liệu + gợi ý ngắn → Muse viết bài nháp
riêng cho từng kênh → người có quyền duyệt trên từng thẻ kênh → đăng lên
Website / Facebook / Instagram / các kênh video**, kèm thống kê và quản trị
người dùng. Web App thay thế dần bot Telegram giao việc hiện tại, dùng chung
dữ liệu với bot trong giai đoạn chuyển đổi.

### 1.2 Phạm vi

Trong phạm vi:
- Giao việc, theo dõi việc, duyệt/đăng theo từng kênh trên Web App (điện thoại
  và máy tính, một hệ thống duy nhất dạng PWA).
- Đăng nhập riêng, phân quyền 5 vai trò, quản lý tài khoản do Admin cấp.
- Tích hợp với Muse (tác nhân viết nháp, gắn bản nháp, đăng bài thật, dựng
  video) và dùng chung cơ sở dữ liệu `bot.db` với bot Telegram khi chạy song song.

Ngoài phạm vi (hiện tại):
- App native trên App Store/CH Play (chỉ đóng gói sau này nếu cần — mục 2.5).
- Đăng nhập OTP qua SMS/email (chưa có dịch vụ gửi SMS; Gmail chưa kết nối).
- Tự đăng ký tài khoản bởi người ngoài (tài khoản chỉ do Admin/Phó Admin tạo).
- Đăng thật lên YouTube/TikTok (thuộc GĐ3 của hệ thống bot, chưa nối).
- Đăng bài lên website thật (chờ chủ dự án cung cấp link website).

### 1.3 Thuật ngữ

| Thuật ngữ | Nghĩa |
|---|---|
| Việc (task) | Một đầu việc giao cho Muse, có mã `CV-xxxx` tăng dần, gồm tư liệu + gợi ý |
| Đầu ra / thẻ kênh (output) | Bản nội dung riêng cho MỘT kênh đăng của một việc; là đơn vị duyệt/đăng |
| Kênh chữ | Website 🌐, Facebook 📘, Instagram 📸 |
| Kênh video | 🎬 Video dọc 9:16 (TikTok/Shorts/Reels), 🎞 Video ngang 16:9 (YouTube) |
| Người duyệt | Vai trò có quyền duyệt: Admin, Phó Admin, Biên tập viên |
| botctl | Công cụ dòng lệnh để Muse gắn nháp/video/link đã đăng và ghi trạng thái vào hệ thống |
| Di trú (migration) | Nâng cấp cấu trúc dữ liệu theo kiểu chỉ cộng thêm, chạy lặp lại không lỗi (idempotent) |

---

## 2. Mô tả tổng thể

### 2.1 Bối cảnh và luồng nghiệp vụ chính

1. Người được cấp quyền **tạo việc**: tải tư liệu (ảnh/video/tệp) + ghi gợi ý
   ngắn + chọn kênh đăng.
2. Hệ thống sinh mã việc, tạo một đầu ra cho mỗi kênh được chọn, ghi nhật ký.
3. **Muse** nhận việc, viết nội dung **riêng cho từng kênh** từ cùng tư liệu
   gốc (không rút gọn chéo giữa các kênh) và gắn bản nháp vào từng thẻ kênh.
4. Người duyệt xem nháp trên thẻ kênh: **Duyệt**, **Trả lại** kèm lý do cần sửa,
   hoặc **Hủy bài**. Người tạo có nút **Sửa lại** trên thẻ kênh của việc mình.
5. Thẻ kênh đã duyệt được **Đăng ngay** hoặc **Đặt lịch đăng**; đến giờ hệ
   thống phát lệnh và Muse đăng thật, sau đó gắn link bài đã đăng vào thẻ.
6. Thống kê theo trạng thái/kênh/người tạo phục vụ quản lý; mọi thao tác đều
   ghi nhật ký kiểm toán (audit log).

### 2.2 Người dùng và ma trận vai trò ✅ (đã chốt 22/10/2026, dùng chung bot và Web App)

| Vai trò | Tạo việc | Xem việc | Duyệt / Trả lại | Đăng | Quản lý người dùng | Thống kê |
|---|---|---|---|---|---|---|
| Admin | ✔ | Tất cả | ✔ (duyệt cuối) | ✔ | ✔ Cấp/thu hồi mọi vai trò | ✔ |
| Phó Admin | ✔ | Tất cả | ✔ | Theo quyền được cấp | ✔ Chỉ cấp vai trò cấp dưới (Nhân viên, Cộng tác viên) | ✔ |
| Biên tập viên | ✔ | Tất cả | ✔ | ✖ | ✖ | ✔ |
| Nhân viên | ✔ | Của mình (và việc liên quan) | ✖ | ✖ | ✖ | ✖ |
| Cộng tác viên | ✔ (chỉ gửi tư liệu/gợi ý) | Của mình | ✖ | ✖ | ✖ | ✖ |

Quy tắc bổ sung:
- Tài khoản chưa được cấp vai trò (role rỗng) = đang chờ cấp quyền, không thao
  tác được gì ngoài đăng nhập. ✅
- Việc do chính Admin tạo **bỏ qua khâu duyệt**: thẻ kênh có nháp thì hiện
  thẳng nút Đăng, bấm Đăng tự ghi nhận đã duyệt (audit `auto=admin_own`). ✅
- Kiểm tra quyền thực hiện **ở phía máy chủ** cho mọi thao tác, không tin
  giao diện. ✅

### 2.3 Kênh đăng và quy tắc chọn kênh ✅

- Mặc định khi tạo việc: chọn sẵn **3 kênh chữ** (Website, Facebook, Instagram).
- Hai kênh video **không** nằm trong mặc định; chọn thêm thủ công khi cần.
- Nút chọn kênh chỉ hiện **icon + tên kênh**; kênh đang chọn hiện icon của kênh,
  bỏ chọn thì icon đổi thành ❌ (giữ tên kênh); chạm lại để chọn lại.
- Nội dung cho mỗi kênh được viết tách riêng; video nháp được dựng từ cùng
  tư liệu gốc của việc (dọc 1080×1920, ngang 1920×1080, bằng ffmpeg).

### 2.4 Mô hình chạy song song với bot Telegram 🔶

- Web App và bot dùng **chung một file dữ liệu `bot.db`** trong suốt giai đoạn
  chuyển đổi; việc tạo ở hệ thống nào cũng thấy ở hệ thống kia.
- Bot giữ vai trò kênh thông báo dự phòng cho tới khi đội chuyển hẳn sang
  Web App (GĐ4), sau đó tắt dần bot.
- Cấu trúc dữ liệu của Web App chỉ **cộng thêm** (cột/bảng mới), không sửa hay
  xóa cấu trúc bot đang dùng.

### 2.5 Ràng buộc kỹ thuật ✅

- Backend **thuần Python stdlib** (không thư viện ngoài), dùng lại trực tiếp
  module nghiệp vụ của bot (`storage.Store`, `roles`, `stats`) — Web App là
  một "mặt tiền" khác trên cùng lõi nghiệp vụ, không sao chép logic.
- Web App là **PWA**: cài được ra màn hình chính điện thoại, chạy trên cả
  điện thoại và máy tính; kiến trúc đóng gói được thành app native
  (Capacitor) sau này mà không viết lại.
- Dữ liệu và mã nguồn nằm trong thư mục người dùng trên máy chủ (sống sót qua
  các lần máy chủ bị thay mới); dịch vụ có thể khôi phục thủ công theo quy
  trình đã có của dự án.
- Triển khai production cần tên miền + HTTPS (chưa thực hiện — thuộc bước
  triển khai sau GĐ2/GĐ3); trước mắt chạy nội bộ trên cổng 8790.

### 2.6 Giả định

- Muse là tác nhân duy nhất viết nháp, dựng video và đăng bài thật (qua
  trình duyệt/connector hiện có); Web App không tự soạn nội dung.
- Đăng Facebook qua trình duyệt của Muse (trang cá nhân và Fanpage Minhy);
  nơi đăng phải được chốt ngay tại thao tác Đăng (mục 3.4).

---

## 3. Yêu cầu chức năng

### 3.1 Xác thực và tài khoản

| Mã | Yêu cầu | Trạng thái |
|---|---|---|
| FR-AUTH-01 | Đăng nhập bằng email **hoặc** số điện thoại + mật khẩu; tài khoản do Admin/Phó Admin tạo, không tự đăng ký | ✅ GĐ1 Web App |
| FR-AUTH-02 | Mật khẩu băm PBKDF2-HMAC-SHA256 (200.000 vòng, salt riêng); không lưu/ghi log/trả về mật khẩu thô hoặc bản băm | ✅ GĐ1 |
| FR-AUTH-03 | Phiên đăng nhập bằng token ngẫu nhiên 32 byte; máy chủ chỉ lưu băm SHA-256 của token; cookie HttpOnly, SameSite=Lax; mặc định hết hạn sau 7 ngày; hỗ trợ Bearer token cho API | ✅ GĐ1 |
| FR-AUTH-04 | Đăng xuất hủy phiên hiện tại; phiên hết hạn/không hợp lệ bị từ chối (401) | ✅ GĐ1 |
| FR-AUTH-05 | Tài khoản trên Telegram có thể gắn thêm thông tin đăng nhập Web App mà không tạo người dùng trùng | ✅ GĐ1 |
| FR-AUTH-06 | Người dùng chỉ dùng Web App (không có Telegram) vẫn hoạt động đầy đủ với mọi tính năng theo vai trò (máy chủ cấp định danh nội bộ tổng hợp ≥ 9.000.000.000 thay cho telegram_id) | ✅ GĐ1 |

### 3.2 Giao việc

| Mã | Yêu cầu | Trạng thái |
|---|---|---|
| FR-TASK-01 | Tạo việc theo wizard 3 bước: (1) tải tư liệu, (2) ghi/sửa gợi ý, (3) chọn kênh theo quy tắc 2.3, bấm "🚀 Chốt! Gửi Muse" là hoàn tất tạo việc | 📋 thiết kế đã chốt — Web App GĐ2 (bot ✅) |
| FR-TASK-02 | Mỗi việc có mã `CV-xxxx` duy nhất tăng dần liên tục giữa cả bot và Web App; hiển thị kèm **người tạo** và **thời gian tạo (giờ Việt Nam)** | ✅ lõi dùng chung |
| FR-TASK-03 | Tải tư liệu trực tiếp lên Web App (ảnh, video, tệp) thay cho gửi qua Telegram; tư liệu gắn với việc và được Muse truy cập để làm bài | 📋 GĐ2 |
| FR-TASK-04 | Danh sách việc có tìm kiếm và lọc theo trạng thái / kênh / người tạo, có phân trang | ✅ API GĐ1; giao diện 📋 GĐ2 |
| FR-TASK-05 | Việc giữ nguyên gợi ý và tư liệu gốc làm hồ sơ; người tạo sửa được gợi ý của việc mình | ✅ bot; giao diện Web App 📋 GĐ2 |
| FR-TASK-06 | Mọi vai trò đã được cấp quyền (kể cả Cộng tác viên) đều tạo việc được; tài khoản chờ cấp quyền bị chặn (403) | ✅ GĐ1 |

### 3.3 Thẻ việc và thẻ kênh (mô hình "Cách A") ✅ (đã chốt và chạy ở bot; Web App kế thừa)

| Mã | Yêu cầu |
|---|---|
| FR-CARD-01 | Mỗi kênh đăng có **thẻ kênh riêng** chứa bản nháp thật của kênh đó. Duyệt/đăng chỉ thực hiện trên thẻ kênh; **thẻ việc chỉ là hồ sơ tư liệu + mục lục trạng thái các thẻ kênh**, không có nút duyệt/đăng |
| FR-CARD-02 | Thẻ kênh chưa có bản nháp thì không được gửi duyệt |
| FR-CARD-03 | Trạng thái của việc tự suy ra từ trạng thái các thẻ kênh |
| FR-CARD-04 | Định dạng thẻ: mỗi dòng đúng **1 icon ở đầu dòng**, gộp trường liên quan cùng dòng, không dòng nhãn trơ; tối thiểu gồm tiêu đề, mã việc · loại kênh, người tạo · thời gian, gợi ý, link bản nháp/trạng thái |
| FR-CARD-05 | Khi một thẻ kênh mới được gửi/cập nhật, các thẻ cũ của cùng đầu ra không còn thao tác được (chỉ thẻ mới nhất có nút bấm) — trên Web App tương đương: luôn hiển thị trạng thái mới nhất, thao tác cũ bị vô hiệu |
| FR-CARD-06 | Bản nháp xem được bằng **một link nhấn là xem** (trong Telegram là trang telegra.ph); trên Web App, bản nháp phải xem được ngay trong giao diện, không tải file trung gian |

### 3.4 Duyệt và đăng

| Mã | Yêu cầu | Trạng thái |
|---|---|---|
| FR-PUB-01 | Luồng trạng thái thẻ kênh: Nháp → Chờ duyệt → Đã duyệt (chờ đăng) → Đã đăng; các nhánh: Trả lại (kèm lý do → viết lại), Hủy bài, Thu hồi sau đăng | ✅ bot; Web App theo GĐ2 |
| FR-PUB-02 | Người duyệt **Trả lại** phải nhập nội dung cần sửa; yêu cầu được ghi nguyên văn và chuyển cho Muse viết lại; người tạo nhận lại thẻ khi có bản sửa mới | ✅ bot |
| FR-PUB-03 | Người tạo có nút **Sửa lại** trên thẻ kênh của việc mình (khác nút Trả lại của người duyệt) với cùng cơ chế ghi yêu cầu nguyên văn | ✅ bot |
| FR-PUB-04 | Nút Đăng trên thẻ kênh chỉ là **lệnh đăng**: trạng thái chỉ chuyển Đã đăng **sau khi** Muse đăng thật và gắn link bài; không tự báo đã đăng khi chưa có link thật | ✅ bot |
| FR-PUB-05 | Riêng Facebook: khi bấm Đăng phải chọn nơi đăng ngay trong cùng giao diện — **trang cá nhân Nguyễn Trọng Minh Huy** hoặc **Fanpage Minhy** — rồi lệnh đăng mới được ghi kèm nơi đăng đã chốt; có nút hủy tại bước chọn | ✅ bot; Web App 📋 GĐ2 |
| FR-PUB-06 | Thu hồi bài Facebook = **xóa thật** trên Facebook, kiểm chứng biến mất rồi mới đổi trạng thái Thu hồi và thông báo; kênh khác thu hồi trong hệ thống | ✅ bot |
| FR-PUB-07 | Việc của chính Admin tạo: bỏ qua Gửi duyệt/Duyệt (xem 2.2) | ✅ |

### 3.5 Đặt lịch đăng ✅ (bot) / 📋 giao diện Web App ở GĐ2

| Mã | Yêu cầu |
|---|---|
| FR-SCH-01 | Thẻ kênh đang chờ đăng đặt được lịch: nhập giờ dạng `HH:MM` hoặc `DD/MM HH:MM` (giờ Việt Nam) hoặc chọn nhanh (sau 1 giờ, sau 2 giờ, tối nay 20:00, sáng mai 8:00); Facebook phải chốt nơi đăng trước khi nhập giờ |
| FR-SCH-02 | Thẻ kênh hiển thị lịch đã đặt; đổi lịch/hủy lịch được; bấm Đăng ngay thì lịch tự hủy |
| FR-SCH-03 | Cảnh báo (không chặn) khi bài cùng kênh đặt cách nhau chưa tới 1 giờ hoặc vừa có bài đăng trong vòng 1 giờ trước giờ chọn |
| FR-SCH-04 | Đến giờ, hệ thống tự phát lệnh đăng kèm nơi đăng đã chốt; có màn hình quản lý tập trung mọi bài đang đặt lịch, thao tác được ngay (Đăng ngay / Đổi lịch / Hủy lịch) |

### 3.6 Kênh video ✅ (bot GĐ2) / 📋 Web App GĐ2

| Mã | Yêu cầu |
|---|---|
| FR-VID-01 | Hai kênh video là kênh đăng thật có thẻ kênh riêng và phân vai nút như kênh chữ: 🎬 dọc 9:16 (TikTok/Shorts/Reels), 🎞 ngang 16:9 (YouTube) |
| FR-VID-02 | Video nháp phải xem duyệt được ngay trong giao diện trước khi đăng |
| FR-VID-03 | Muse dựng video bằng ffmpeg đúng chuẩn 1080×1920 (dọc) / 1920×1080 (ngang) từ tư liệu gốc của việc rồi gắn vào thẻ kênh |
| FR-VID-04 | Đăng thật lên YouTube/TikTok là giai đoạn riêng (GĐ3 của hệ thống); trước đó nút Đăng video chỉ ghi lệnh chờ |

### 3.7 Thống kê

| Mã | Yêu cầu | Trạng thái |
|---|---|---|
| FR-STAT-01 | Thống kê theo kỳ: Hôm nay / Tuần này / Tháng này / Tất cả; đếm việc và đầu ra theo trạng thái, theo kênh (gồm video), theo người tạo | ✅ API GĐ1 (dùng lại `stats.py` của bot); giao diện 📋 GĐ2 |
| FR-STAT-02 | Biểu đồ trực quan; xuất CSV (BOM UTF-8) và xuất Excel | ✅ bot; Web App 📋 GĐ2 |
| FR-STAT-03 | Chỉ người duyệt trở lên xem được thống kê | ✅ |
| FR-STAT-04 | Tin tổng kết ngày gửi Admin (hiện qua Telegram 20:00 giờ VN; khi chuyển hẳn sang Web App sẽ thay bằng thông báo trong Web App) | ✅ bot; 📋 GĐ3 |

### 3.8 Thông báo 📋 GĐ3

| Mã | Yêu cầu |
|---|---|
| FR-NOTI-01 | Thông báo đẩy (Web Push) + hộp thông báo trong Web App cho các sự kiện: có việc mới, có thẻ chờ duyệt, bị trả lại/yêu cầu sửa, đã đăng thành công kèm link, đến lịch đăng |
| FR-NOTI-02 | Trong giai đoạn song song, bot Telegram vẫn gửi thông báo như hiện tại (kênh dự phòng) |
| FR-NOTI-03 | Badge số thông báo chưa đọc trên biểu tượng chuông; mở thông báo đi thẳng tới việc/thẻ kênh liên quan |

### 3.9 Quản lý người dùng

| Mã | Yêu cầu | Trạng thái |
|---|---|---|
| FR-USER-01 | Admin xem danh sách tài khoản, tạo tài khoản mới (tên, email/SĐT, mật khẩu tạm, vai trò, quyền đăng), đổi vai trò, thu hồi quyền | ✅ API GĐ1 (theo `roles.can_grant`); giao diện 📋 GĐ3 |
| FR-USER-02 | Phó Admin chỉ cấp được vai trò cấp dưới mình (Nhân viên, Cộng tác viên) | ✅ |
| FR-USER-03 | API danh sách người dùng không bao giờ trả về bản băm mật khẩu | ✅ GĐ1 |
| FR-USER-04 | Mọi thao tác cấp/thu hồi/đổi vai trò đều ghi audit log | ✅ |

### 3.10 Tích hợp Muse và nhật ký

| Mã | Yêu cầu | Trạng thái |
|---|---|---|
| FR-INT-01 | Hệ thống quét/nhận diện việc mới và đầu ra cần viết lại (kể cả chưa có nháp) để Muse tiếp tục làm mà không cần người dùng nhắc; "xong" chỉ tính khi thẻ kênh kèm bản nháp đã tới tay người nhận | ✅ quy trình bot; giữ nguyên với Web App |
| FR-INT-02 | Muse gắn nháp/video/link đã đăng qua cơ chế tương đương botctl cho đầu ra của Web App; trạng thái chỉ đổi khi có bằng chứng thật (link bài, tệp video) | 🔶 GĐ1 có API đọc/ghi nền; hoàn thiện cùng GĐ2 |
| FR-INT-03 | Mọi thao tác nghiệp vụ (tạo việc, duyệt, trả lại, đăng, đặt lịch, thu hồi, cấp quyền…) ghi audit log gồm người thực hiện, hành động, đối tượng, thời gian | ✅ |

---

## 4. Yêu cầu phi chức năng

| Mã | Yêu cầu |
|---|---|
| NFR-SEC-01 | Kiểm quyền ở máy chủ cho 100% endpoint/thao tác; dữ liệu của người khác không lộ qua API khi vai trò không cho phép |
| NFR-SEC-02 | Bí mật (token, mật khẩu) chỉ lưu qua cơ chế bảo mật của hệ thống; không ghi bí mật vào mã nguồn, log, hay tài liệu trong repo |
| NFR-SEC-03 | Production bắt buộc HTTPS; cookie phiên HttpOnly + SameSite=Lax |
| NFR-REL-01 | Dữ liệu nghiệp vụ nằm trong `bot.db` dùng chung; sao lưu bắt buộc trước mọi lần di trú dữ liệu; di trú phải idempotent và chỉ cộng thêm |
| NFR-REL-02 | Hệ thống khôi phục được sau khi máy chủ bị thay mới: mã nguồn + dữ liệu trong thư mục người dùng còn nguyên; dịch vụ cài lại theo quy trình đã ghi trong nhật ký phát triển |
| NFR-PERF-01 | Quy mô đội nội bộ nhỏ; API danh sách có phân trang; thao tác thường dùng phản hồi dưới 1 giây trên máy chủ hiện tại |
| NFR-USE-01 | Giao diện tiếng Việt có dấu; dùng được bằng một tay trên điện thoại; chuẩn hiển thị mỗi dòng 1 icon trên các thẻ |
| NFR-MNT-01 | Không thêm thư viện ngoài khi stdlib đáp ứng được; mọi thay đổi ghi vào `NHAT-KY-PHAT-TRIEN.md` và `THAY-DOI.md`; cuối mỗi giai đoạn hoàn thiện lại tài liệu thiết kế/SRS cho khớp |
| NFR-MNT-02 | Kiểm thử tự động: bộ test của Web App và của bot đều phải đạt trước khi coi một giai đoạn là xong (GĐ1: webapp 19/19, bot 215/215) |

---

## 5. Yêu cầu dữ liệu ✅ GĐ1

- Dùng chung SQLite `bot.db` của bot. Các bảng nghiệp vụ sẵn có: `users`,
  `tasks`, `outputs`, `audit_log`, `bot_meta`, `intake_buffer`,
  `output_cards`, `user_state`.
- Di trú của Web App (idempotent, chỉ cộng thêm):
  - `users` thêm `email`, `phone`, `password_hash` (nullable) + unique index
    từng phần cho email/phone.
  - Thêm bảng `web_sessions` (băm token, người dùng, thời gian tạo, hạn dùng).
- Việc gắn đăng nhập web cho tài khoản Telegram sẵn có không tạo dòng trùng.
- Trạng thái áp dụng: đã áp lên `bot.db` thật ngày 24/10/2026 sau khi sao lưu
  (`data/backup-webapp-20261024-011905/`), dữ liệu cũ nguyên vẹn
  (1 người dùng, 12 việc, 21 đầu ra tại thời điểm áp).

---

## 6. Giao diện bên ngoài — API (GĐ1 ✅)

| Method & path | Quyền | Mô tả |
|---|---|---|
| `GET /api/health` | Công khai | Kiểm tra sống: `{ok, version, db}` |
| `POST /api/auth/login` | Công khai | `{login, password}` → phiên (cookie + token) |
| `POST /api/auth/logout` | Đã đăng nhập | Hủy phiên hiện tại |
| `GET /api/auth/me` | Đã đăng nhập | Thông tin + vai trò + quyền của mình |
| `GET /api/tasks?status=&channel=&creator=&q=&limit=&offset=` | Đã cấp quyền | Danh sách việc có lọc + phân trang |
| `GET /api/tasks/<code>` | Đã cấp quyền | Việc + outputs theo kênh + audit liên quan |
| `POST /api/tasks` | Đã cấp quyền | `{hint, destinations[]}` → tạo việc, sinh mã CV- tiếp nối, tạo outputs, ghi audit |
| `GET /api/stats/summary?period=today\|week\|month\|all` | Người duyệt | Thống kê tổng hợp |
| `GET /api/users` | Admin/Phó Admin | Danh sách tài khoản (không có password_hash) |
| `POST /api/users` | Theo `can_grant` | Tạo tài khoản web mới kèm vai trò |

Cổng mặc định 8790; cấu hình qua biến môi trường (xem `README.md`).

---

## 7. Lộ trình triển khai

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| GĐ1 | API + đăng nhập riêng + di trú dữ liệu | ✅ Xong 24/10/2026 (19/19 test webapp, 215/215 test bot) |
| GĐ2 | Giao diện các luồng chính: đăng nhập, tổng quan, giao việc 3 bước, danh sách/chi tiết việc + thẻ kênh, chờ duyệt, lịch đăng, thống kê | 📋 |
| GĐ3 | Thông báo đẩy + quản lý người dùng trên giao diện + tổng kết ngày trong Web App | 📋 |
| GĐ4 | Triển khai production (dịch vụ chạy nền, tên miền, HTTPS) → chạy song song với bot → đội chuyển hẳn sang Web App → tắt dần bot | 📋 |
| Ngoài lộ trình | Tạo tài khoản Admin Web App đầu tiên (chờ chủ dự án cấp email/SĐT + mật khẩu qua kênh bảo mật); đóng gói native (Capacitor) khi thật sự cần | 📋 |

---

## 8. Lịch sử phiên bản SRS

| Phiên bản | Ngày | Nội dung |
|---|---|---|
| 1.0 | 24/10/2026 | Bản gốc: tổng hợp từ bản thiết kế Web App đã được duyệt (24/10/2026), toàn bộ quy tắc nghiệp vụ đã chốt của hệ thống bot (GĐ1–GĐ2 bot) và GĐ1 Web App đã xây. Từ bản sau, thay đổi đi qua `THAY-DOI.md` rồi tổng hợp vào đây |
