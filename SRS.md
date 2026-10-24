# SRS — Đặc tả yêu cầu phần mềm: Web App Giao Việc IAICT

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản SRS | **1.4** (tổng hợp TD-0012, TD-0013, TD-0014, TD-0015, TD-0016, TD-0017, TD-0018) |
| Ngày hiệu lực | 25/10/2026 |
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
- Riêng Facebook, một đầu ra đăng tới một **tập hợp các nơi** (TD-0013):
  khóa nơi đăng là `profile` (trang cá nhân Nguyễn Trọng Minh Huy, cố định
  1 mục) và `page_<fb_page_id>` (mỗi Fanpage một khóa). Danh sách nơi đăng
  lấy từ dữ liệu — trang cá nhân + bảng `facebook_pages` (hiện chỉ có
  1 dòng: Fanpage Minhy, id 61595515900524); thêm Fanpage về sau chỉ cần
  thêm dòng vào bảng (chưa có màn hình quản lý Fanpage). Mỗi nơi có link
  bài đã đăng riêng; trạng thái Đã đăng chỉ khi TẤT CẢ nơi trong tập hợp
  đều đăng xong.

### 2.4 Mô hình chạy song song với bot Telegram 🔶

- Web App và bot dùng **chung một file dữ liệu `bot.db`** trong suốt giai đoạn
  chuyển đổi; việc tạo ở hệ thống nào cũng thấy ở hệ thống kia.
- Bot giữ vai trò kênh thông báo dự phòng. Việc chuyển đội + tắt dần bot
  (GĐ4) đang **TẠM DỪNG theo quyết định của chủ dự án ngày 24/10/2026**
  ("Không chuyển nhé") — bot giữ nguyên toàn bộ, không tắt dần, cho tới
  khi có quyết định mới.
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
- Triển khai production tại **https://post.iaict-platform.com** qua
  Cloudflare Tunnel `webapp-giao-viec` (ingress → http://127.0.0.1:8790,
  DNS CNAME proxied) ✅ xong 24/10/2026 (TD-0007). Vì netstack của máy
  chủ ảo chặn DNS-SRV/UDP/cổng 7844 trực tiếp, kèm 2 dịch vụ phụ trợ
  riêng của máy này: `cf-dns-stub` (DNS tĩnh cho edge discovery +
  forward gateway) và `cf-edge-relay` (CONNECT qua proxy egress tới
  edge thật, ép HTTP/2); khôi phục sau khi máy chủ bị thay theo quy
  trình trong nhật ký phát triển.

### 2.6 Giả định

- Muse là tác nhân duy nhất viết nháp, dựng video và đăng bài thật (qua
  trình duyệt/connector hiện có); Web App không tự soạn nội dung.
- Đăng Facebook qua trình duyệt của Muse (trang cá nhân và Fanpage Minhy);
  nơi đăng (một hoặc nhiều nơi, xem 2.3) phải được chốt ngay tại thao tác
  Đăng hoặc Đặt lịch (mục 3.4–3.5); nơi đã đăng xong không đăng lại, nơi
  đang chờ đăng không chọn lại (mục 3.4, FR-PUB-08).

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
| FR-TASK-01 | Tạo việc theo wizard 3 bước: (1) tải tư liệu, (2) ghi/sửa gợi ý, (3) chọn kênh theo quy tắc 2.3, bấm "🚀 Chốt! Gửi Muse" là hoàn tất tạo việc | ✅ Web App GĐ2 (bot ✅) |
| FR-TASK-02 | Mỗi việc có mã `CV-xxxx` duy nhất tăng dần liên tục giữa cả bot và Web App; hiển thị kèm **người tạo** và **thời gian tạo (giờ Việt Nam)** | ✅ lõi dùng chung |
| FR-TASK-03 | Tải tư liệu trực tiếp lên Web App (ảnh, video, tệp) thay cho gửi qua Telegram; tư liệu gắn với việc và được Muse truy cập để làm bài; giới hạn 200MB/tệp, lưu đúng cấu trúc `data/files/<MÃ VIỆC>/` của bot, hai điểm vào: kèm lúc tạo việc và gắn thêm vào việc đã có. Gắn thêm tư liệu vào việc đã có thẻ kênh: form hiện chú thích (tư liệu mới chỉ gắn vào việc, Muse chưa được báo — nhắn Muse nếu muốn dùng) và hệ thống gửi thông báo đẩy cho người duyệt/Admin; không đổi trạng thái việc, phân quyền giữ nguyên (chỉ người tạo/Admin được gắn thêm) (TD-0015) | ✅ GĐ2; chú thích + thông báo gắn thêm ✅ TD-0015 |
| FR-TASK-04 | Danh sách việc có tìm kiếm và lọc theo trạng thái / kênh / người tạo, có phân trang; lọc theo trạng thái theo đúng trạng thái việc suy ra từ các thẻ kênh, API trả thêm `counts` từng trạng thái và giao diện hiện chip lọc kèm số lượng (TD-0009) | ✅ API GĐ1 + giao diện GĐ2; lọc + counts ✅ TD-0009 |
| FR-TASK-05 | Việc giữ nguyên gợi ý và tư liệu gốc làm hồ sơ; người tạo sửa được gợi ý của việc mình | ✅ bot + Web App GĐ2 |
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
| FR-PUB-01 | Luồng trạng thái thẻ kênh: Nháp → Chờ duyệt → Đã duyệt (chờ đăng) → Đã đăng; các nhánh: Trả lại (kèm lý do → viết lại), Hủy bài, Thu hồi sau đăng | ✅ bot + Web App GĐ2 |
| FR-PUB-02 | Người duyệt **Trả lại** phải nhập nội dung cần sửa; yêu cầu được ghi nguyên văn và chuyển cho Muse viết lại; người tạo nhận lại thẻ khi có bản sửa mới | ✅ bot |
| FR-PUB-03 | Người tạo có nút **Sửa lại** trên thẻ kênh của việc mình (khác nút Trả lại của người duyệt) với cùng cơ chế ghi yêu cầu nguyên văn | ✅ bot |
| FR-PUB-04 | Nút Đăng trên thẻ kênh chỉ là **lệnh đăng**: trạng thái chỉ chuyển Đã đăng **sau khi** Muse đăng thật và gắn link bài; không tự báo đã đăng khi chưa có link thật. Link bài đã đăng Facebook lưu theo từng nơi đăng (FR-PUB-05); đầu ra PUBLISHED/RETRACTED kiểu cũ chỉ có một `public_url` mà không có target ở cột thì suy nơi đăng từ audit `publish_requested` gần nhất, không suy được thì hiển thị chung "Facebook" (TD-0015) | ✅ bot |
| FR-PUB-05 | Riêng Facebook: khi bấm Đăng phải chọn nơi đăng ngay trong cùng giao diện — chọn **một hoặc nhiều nơi** trong danh sách (trang cá nhân Nguyễn Trọng Minh Huy, Fanpage Minhy và các Fanpage thêm sau — mục 2.3), bắt buộc chọn ít nhất 1 nơi mới cho xác nhận; nơi đã đăng xong hiện "đã đăng" và không chọn lại, nơi đang chờ đăng hiện "đang chờ đăng" và không chọn lại (xem FR-PUB-08); lệnh đăng ghi kèm tập hợp nơi đã chốt; có nút hủy tại bước chọn. Modal chọn nơi không bao giờ trống oan: nếu không tải được danh sách nơi đăng thì hiện lỗi rõ ràng kèm nút thử lại, không hiện dòng "không còn nơi nào để chọn" khi chưa tải được (TD-0018). Mọi modal đều có nút X góc phải trên để đóng (chỉ đóng, không xác nhận, không hủy lệnh — xem NFR-USE-01) (TD-0016) | ✅ bot + Web App GĐ2; chọn nhiều nơi ✅ TD-0013; modal lỗi + thử lại ✅ TD-0018 |
| FR-PUB-06 | Thu hồi bài Facebook = **xóa thật** trên Facebook ở **TẤT CẢ các nơi đã đăng thành công**, kiểm chứng từng nơi biến mất rồi mới đổi trạng thái Thu hồi và thông báo; kênh khác thu hồi trong hệ thống | ✅ bot; thu hồi từng nơi ✅ TD-0013 |
| FR-PUB-07 | Việc của chính Admin tạo: bỏ qua Gửi duyệt/Duyệt (xem 2.2) | ✅ |
| FR-PUB-08 | Khóa nơi đang chờ đăng Facebook (TD-0015): tập khóa = nơi đã đăng xong ∪ (tập lệnh đang chờ − nơi đã đăng − nơi đăng lỗi); nơi đăng lỗi vẫn chọn lại được để đăng lại. Lịch đang chờ giờ không khóa nơi đăng (sửa lịch được). Hủy lệnh đăng dọn tập lệnh đã hủy để không khóa oan. Máy chủ từ chối (409) khi toàn bộ nơi chọn đều đã khóa (kèm tên nơi bị khóa); chọn lẫn nơi khóa + nơi mở thì chỉ đăng nơi mở và báo rõ nơi bị bỏ qua | ✅ bot + Web App TD-0015 |

### 3.5 Đặt lịch đăng ✅ (bot + Web App GĐ2)

| Mã | Yêu cầu |
|---|---|
| FR-SCH-01 | Thẻ kênh đang chờ đăng đặt được lịch: nhập giờ dạng `HH:MM` hoặc `DD/MM HH:MM` (giờ Việt Nam) hoặc chọn nhanh (sau 1 giờ, sau 2 giờ, tối nay 20:00, sáng mai 8:00); Facebook phải chốt nơi đăng trước khi nhập giờ; lịch đăng Facebook lưu cả tập hợp nơi đăng đã chốt (TD-0013) |
| FR-SCH-02 | Thẻ kênh hiển thị lịch đã đặt; đổi lịch/hủy lịch được; bấm Đăng ngay thì lịch tự hủy; lịch đang chờ giờ không khóa nơi đăng (sửa lịch được — TD-0015) |
| FR-SCH-03 | Cảnh báo (không chặn) khi bài cùng kênh đặt cách nhau chưa tới 1 giờ hoặc vừa có bài đăng trong vòng 1 giờ trước giờ chọn |
| FR-SCH-04 | Đến giờ, hệ thống tự phát lệnh đăng kèm nơi đăng đã chốt; có màn hình quản lý tập trung mọi bài đang đặt lịch, thao tác được ngay (Đăng ngay / Đổi lịch / Hủy lịch) |

### 3.6 Kênh video ✅ (bot + Web App GĐ2 — xem video nháp ngay trong trang)

| Mã | Yêu cầu |
|---|---|
| FR-VID-01 | Hai kênh video là kênh đăng thật có thẻ kênh riêng và phân vai nút như kênh chữ: 🎬 dọc 9:16 (TikTok/Shorts/Reels), 🎞 ngang 16:9 (YouTube) |
| FR-VID-02 | Video nháp phải xem duyệt được ngay trong giao diện trước khi đăng |
| FR-VID-03 | Muse dựng video bằng ffmpeg đúng chuẩn 1080×1920 (dọc) / 1920×1080 (ngang) từ tư liệu gốc của việc rồi gắn vào thẻ kênh |
| FR-VID-04 | Đăng thật lên YouTube/TikTok là giai đoạn riêng (GĐ3 của hệ thống); trước đó nút Đăng video chỉ ghi lệnh chờ |

### 3.7 Thống kê

| Mã | Yêu cầu | Trạng thái |
|---|---|---|
| FR-STAT-01 | Thống kê theo kỳ: Hôm nay / Tuần này / Tháng này / Tất cả; đếm việc và đầu ra theo trạng thái, theo kênh (gồm video), theo người tạo | ✅ API GĐ1 (dùng lại `stats.py` của bot) + giao diện GĐ2 |
| FR-STAT-02 | Biểu đồ trực quan; xuất CSV (BOM UTF-8) và xuất Excel | ✅ bot + Web App GĐ2 |
| FR-STAT-03 | Chỉ người duyệt trở lên xem được thống kê | ✅ |
| FR-STAT-04 | Tin tổng kết ngày gửi Admin lúc 20:00 giờ VN: qua Telegram của bot và — từ GĐ3 — qua **Web Push cho Admin đã đăng ký + mục tổng kết trong hộp thông báo của Web App cho mọi người** (mỗi ngày một lần, chống gửi trùng bằng ngày đã gửi lưu trong DB); thẻ "Tổng kết hôm nay" trên màn Tổng quan và endpoint `/api/stats/daily-summary` cho số liệu trong ngày | ✅ bot; ✅ Web App GĐ3 |

### 3.8 Thông báo ✅ (hộp thông báo trong app ✅ GĐ2; Web Push ✅ GĐ3)

| Mã | Yêu cầu | Trạng thái |
|---|---|---|
| FR-NOTI-01 | Thông báo đẩy (Web Push chuẩn VAPID/RFC 8291) + hộp thông báo trong Web App cho các sự kiện: có việc mới, có thẻ chờ duyệt, bị duyệt/trả lại, có lệnh đăng, thu hồi, đặt lịch, tổng kết ngày 20:00. Người dùng tự bật/tắt trên từng thiết bị ở màn Thông báo; đăng ký bị dịch vụ đẩy trả 404/410 được tự xóa; thẻ bật thông báo đẩy LUÔN hiện kèm dòng trạng thái rõ ràng (không ẩn khi lỗi sớm) và giao diện hiện dòng số phiên bản app để đối chiếu cache (TD-0009). Sự kiện đăng/thu hồi/đăng lỗi qua botctl cũng ghi hàng `web_notification_items` (key `published:`/`publish_failed:`/`retracted:` + id đầu ra + id audit, kèm link từng nơi) VÀ gửi Web Push tới mọi subscription đã đăng ký (TD-0015, TD-0017); `--no-notify` tắt cả Telegram, hàng web và push; thiếu token Telegram không chặn push web; lỗi gửi push không làm hỏng lệnh botctl. Thêm tư liệu muộn vào việc đã có thẻ kênh cũng gửi push cho người duyệt/Admin (xem FR-TASK-03) | ✅ GĐ3; thẻ luôn hiện + dòng phiên bản ✅ TD-0009; hàng web botctl ✅ TD-0015; push kèm botctl ✅ TD-0017 |
| FR-NOTI-02 | Trong giai đoạn song song, bot Telegram vẫn gửi thông báo như hiện tại (kênh dự phòng) |
| FR-NOTI-03 | Badge số thông báo chưa đọc trên biểu tượng chuông; mở thông báo đi thẳng tới việc/thẻ kênh liên quan; thanh điều hướng mobile cũng có badge chưa đọc và badge số thẻ chờ duyệt (hình tròn cố định, không méo, không bị nút Giao việc che — TD-0010/TD-0011). Badge trong app đồng bộ `navigator.setAppBadge(số chưa đọc)` mỗi khi hộp thông báo tải/làm mới (kể cả khi quay lại app và theo poll đồng bộ sống — FR-NOTI-04) và xóa khi đã đọc hết; service worker cũng đồng bộ badge khi nhận push (best-effort). **Giới hạn nền tảng đã xác minh (TD-0018, theo MDN): Badging API KHÔNG hỗ trợ trên trình duyệt Chromium chạy Android — `setAppBadge` ở đó là no-op; Android chỉ tự hiện chấm thông báo khi có thông báo chưa đọc, và chấm chỉ hiện trên icon app đã cài đặt thật; ghim bằng Brave chỉ tạo lối tắt (Brave không mint WebAPK) nên không có badge — muốn chấm thì cài bằng Chrome (app thật, WebAPK) + bật push riêng trong app đó + có push thật tới. iOS cũng không hỗ trợ Badging API (TD-0015)** |
| FR-NOTI-04 | Đồng bộ sống (TD-0018): app tự tải lại thông báo + badge mỗi 30 giây khi tab đang hiển thị (không tải lại danh sách để khỏi mất vị trí cuộn); quay lại app thì tải lại ngay dữ liệu màn hiện tại + thông báo + badge; service worker khi nhận push báo cho client đang mở (postMessage `"gv-push"`) để tải lại. Nút "Gửi thử" trong màn Thông báo báo đã gửi tới N/T thiết bị (không lộ endpoint) | ✅ TD-0018 |

### 3.9 Quản lý người dùng

| Mã | Yêu cầu | Trạng thái |
|---|---|---|
| FR-USER-01 | Admin xem danh sách tài khoản, tạo tài khoản mới (tên, email/SĐT, mật khẩu tạm, vai trò, quyền đăng), đổi vai trò, thu hồi quyền | ✅ API GĐ1 (theo `roles.can_grant`) + giao diện GĐ2 |
| FR-USER-02 | Phó Admin chỉ cấp được vai trò cấp dưới mình (Nhân viên, Cộng tác viên) | ✅ |
| FR-USER-03 | API danh sách người dùng không bao giờ trả về bản băm mật khẩu | ✅ GĐ1 |
| FR-USER-04 | Mọi thao tác cấp/thu hồi/đổi vai trò đều ghi audit log | ✅ |

### 3.10 Tích hợp Muse và nhật ký

| Mã | Yêu cầu | Trạng thái |
|---|---|---|
| FR-INT-01 | Hệ thống quét/nhận diện việc mới và đầu ra cần viết lại (kể cả chưa có nháp) để Muse tiếp tục làm mà không cần người dùng nhắc; "xong" chỉ tính khi thẻ kênh kèm bản nháp đã tới tay người nhận | ✅ quy trình bot; giữ nguyên với Web App |
| FR-INT-02 | Muse gắn nháp/video/link đã đăng qua cơ chế tương đương botctl cho đầu ra của Web App; trạng thái chỉ đổi khi có bằng chứng thật (link bài, tệp video) | ✅ GĐ2 — API thao tác thẻ kênh ghi đúng tên audit và chuyển trạng thái của bot |
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
| NFR-USE-01 | Giao diện tiếng Việt có dấu; dùng được bằng một tay trên điện thoại; chuẩn hiển thị mỗi dòng 1 icon trên các thẻ; làm kỹ CẢ mobile lẫn desktop. Ngôn ngữ thị giác từ bản 0.4.0 (TD-0011, theo bản thiết kế mới đã chốt): thẻ bo 20px, tầng bậc chữ rõ, tông teal chủ đạo; thanh điều hướng mobile 6 cột (Tổng quan, Việc, nút Giao việc, Chờ duyệt, Thông báo, Thêm) với nút Giao việc tròn gradient viền trắng nổi trên thanh, nhãn một dòng, badge tròn cố định; bảng menu nổi "Thêm" (chạm ngoài/Esc đóng, đổi màn tự đóng); collapse cho khối thông tin việc, thẻ kênh, bộ lọc, nhóm thông báo theo ngày; sidebar desktop thu gọn thành thanh icon; wizard 3 bước với nút chính full-width nằm trên, nút phụ thành hàng dưới; sáng/tối theo hệ thống (prefers-color-scheme). Trước đó: thanh dưới mobile dạng thanh nổi bo tròn (TD-0010, bản 0.3.2); sửa cache vỏ app network-first + SW v4→v6 để người dùng nhận giao diện mới ngay (TD-0009, bản 0.3.1). Sửa sau phản hồi (TD-0012, bản 0.4.1): nút Giao việc 58px (52px ở màn ≤340px), nhô ~7px khỏi mép thanh; nút thanh dưới khi active có nền trong suốt (sửa lỗi nền tối của sidebar rò sang làm chữ chìm). Dải chip lọc (TD-0014, bản 0.5.1): dải riêng nền teal nhạt, chữ đậm 800, chip đang chọn nền teal đậm + chữ trắng + số đếm, trượt ngang kèm fade ở mép phải; danh sách việc/chờ duyệt/lịch đăng/người dùng có nút thu gọn/mở rộng (nhớ vào localStorage); desktop (≥821px) danh sách có vùng cuộn dọc riêng, mobile (≤820px) cuộn trang tự nhiên và tuyệt đối không tràn ngang; thẻ thông báo ngắt được link dài (overflow-wrap:anywhere). Nút "Thêm" ở thanh dưới dùng icon ••• (TD-0015). Mọi modal đều có nút X góc phải trên (TD-0016, bản 0.5.3): vùng chạm tối thiểu 40px, rõ cả sáng lẫn tối, không đè tiêu đề; bấm X chỉ đóng modal, không xác nhận, không hủy lệnh (với modal xác nhận thì X tương đương từ chối, giống bấm ra nền modal). Modal chọn nơi đăng khi không tải được danh sách thì hiện lỗi rõ ràng kèm nút thử lại (TD-0018, bản 0.5.5) |
| NFR-MNT-01 | Không thêm thư viện ngoài khi stdlib đáp ứng được; mọi thay đổi ghi vào `NHAT-KY-PHAT-TRIEN.md` và `THAY-DOI.md`; cuối mỗi giai đoạn hoàn thiện lại tài liệu thiết kế/SRS cho khớp |
| NFR-MNT-02 | Kiểm thử tự động: bộ test của Web App và của bot đều phải đạt trước khi coi một giai đoạn là xong (GĐ1: webapp 19/19, bot 215/215; GĐ2: webapp 37/37, bot 215/215; GĐ3: webapp 51/51, bot 215/215; TD-0009/TD-0010: webapp 52/52, bot 215/215; TD-0011: webapp 53/53, bot 215/215, bản app 0.4.0; TD-0012: webapp 53/53, bot 215/215; TD-0013: webapp 54/54, bot 230/230; TD-0014: webapp 54/54, bot 230/230; TD-0015: webapp 57/57, bot 242/242; TD-0016: webapp 58/58, bot 242/242; TD-0017: webapp 58/58, bot 251/251; TD-0018: webapp 58/58, bot 251/251, bản app 0.5.5) |

---

## 5. Yêu cầu dữ liệu ✅ GĐ1

- Dùng chung SQLite `bot.db` của bot. Các bảng nghiệp vụ sẵn có: `users`,
  `tasks`, `outputs`, `audit_log`, `bot_meta`, `intake_buffer`,
  `output_cards`, `user_state`.
- Di trú của Web App (idempotent, chỉ cộng thêm):
  - `users` thêm `email`, `phone`, `password_hash` (nullable) + unique index
    từng phần cho email/phone.
  - Thêm bảng `web_sessions` (băm token, người dùng, thời gian tạo, hạn dùng).
  - GĐ2: `web_meta` (khóa/giá trị nội bộ của Web App), `web_notification_reads`
    (đánh dấu đã đọc của hộp thông báo).
  - GĐ3: `web_push_subscriptions` (đăng ký Web Push theo endpoint, UNIQUE
    toàn cục), `web_notification_items` (mục hộp thông báo tường minh như
    tổng kết ngày). Khóa VAPID của máy chủ lưu ngoài DB tại
    `telegram-bot-giao-viec/data/vapid.json` (chmod 600, không vào repo).
  - TD-0013: thêm bảng `facebook_pages` (id, name; seed Fanpage Minhy
    61595515900524) và `outputs` thêm 6 cột JSON (cộng thêm):
    `publish_targets`, `fb_target_set`, `fb_place_urls`,
    `fb_place_failed`, `fb_place_retracted`, `fb_pending_targets`;
    target đơn cũ (`publish_target`) được hiểu như danh sách 1 phần tử.
  - TD-0015: hàng `web_notification_items` cho sự kiện botctl dùng key
    theo mẫu `published:`/`publish_failed:`/`retracted:` + id đầu ra +
    id audit.
- Việc gắn đăng nhập web cho tài khoản Telegram sẵn có không tạo dòng trùng.
- Trạng thái áp dụng: đã áp lên `bot.db` thật ngày 24/10/2026 sau khi sao lưu
  (`data/backup-webapp-20261024-011905/`), dữ liệu cũ nguyên vẹn
  (1 người dùng, 12 việc, 21 đầu ra tại thời điểm áp).

---

## 6. Giao diện bên ngoài — API (GĐ1 ✅, bổ sung GĐ2 ✅)

| Method & path | Quyền | Mô tả |
|---|---|---|
| `GET /api/health` | Công khai | Kiểm tra sống: `{ok, version, db}` |
| `POST /api/auth/login` | Công khai | `{login, password}` → phiên (cookie + token) |
| `POST /api/auth/logout` | Đã đăng nhập | Hủy phiên hiện tại |
| `GET /api/auth/me` | Đã đăng nhập | Thông tin + vai trò + quyền của mình |
| `GET /api/tasks?status=&channel=&creator=&q=&limit=&offset=` | Đã cấp quyền | Danh sách việc có lọc + phân trang; lọc `status` theo đúng trạng thái việc suy ra từ các thẻ kênh, kèm `counts` từng trạng thái (TD-0009) |
| `GET /api/tasks/<code>` | Đã cấp quyền | Việc + outputs theo kênh + audit liên quan |
| `POST /api/tasks` | Đã cấp quyền | `{hint, destinations[]}` → tạo việc, sinh mã CV- tiếp nối, tạo outputs, ghi audit |
| `GET /api/stats/summary?period=today\|week\|month\|all` | Người duyệt | Thống kê tổng hợp |
| `GET /api/users` | Admin/Phó Admin | Danh sách tài khoản (không có password_hash) |
| `POST /api/users` | Theo `can_grant` | Tạo tài khoản web mới kèm vai trò |
| `POST /api/uploads` · `POST /api/tasks` (multipart) · `POST /api/tasks/<code>/files` | Đã cấp quyền | Tải tư liệu (≤200MB/tệp) kèm tạo việc hoặc gắn thêm vào việc | ✅ GĐ2 |
| `GET /api/files/<code>/<filename>` · `GET /api/outputs/<id>/draft-video` | Xem được việc | Xem/tải tư liệu và phát video nháp (hỗ trợ Range) | ✅ GĐ2 |
| `POST /api/outputs/<id>/<action>` | Theo ma trận bot | submit / approve / reject / revise / cancel / publish / publish-abort / schedule / schedule-abort / unschedule / retract — khớp audit và trạng thái của bot; publish chấp nhận `targets[]` (target đơn cũ vẫn chạy); máy chủ từ chối 409 khi mọi nơi chọn đều đã khóa (TD-0015) | ✅ GĐ2; chọn nhiều nơi ✅ TD-0013 |
| `GET /api/facebook-targets` | Đã đăng nhập | Danh sách nơi đăng Facebook (trang cá nhân + các Fanpage trong bảng `facebook_pages`) để modal chọn nơi đăng dùng | ✅ TD-0013 |
| `GET /api/review-queue` · `GET /api/scheduled` | Người duyệt | Hàng thẻ chờ duyệt; bài đang đặt lịch theo giờ tăng dần | ✅ GĐ2 |
| `GET /api/stats/export?format=csv\|xlsx&period=...` | Người duyệt | Xuất thống kê (CSV có BOM UTF-8) | ✅ GĐ2 |
| `GET /api/notifications` · `POST /api/notifications/read` | Đã đăng nhập | Hộp thông báo + đánh dấu đã đọc | ✅ GĐ2 |
| `POST /api/auth/change-password` | Đã đăng nhập | Đổi mật khẩu (hủy các phiên khác) | ✅ GĐ2 |
| `PATCH /api/users/<id>/role` · `POST /api/users/<id>/revoke` | Theo `can_grant`/`can_revoke` | Đổi vai trò / thu hồi quyền, ghi audit | ✅ GĐ2 |
| `GET /api/push/vapid-public-key` | Đã đăng nhập | Public key VAPID (base64url) để trình duyệt đăng ký Web Push | ✅ GĐ3 |
| `POST /api/push/subscribe` · `POST /api/push/unsubscribe` · `POST /api/push/test` | Đã cấp quyền | Đăng ký/hủy đăng ký thiết bị nhận push (upsert theo endpoint; hủy chỉ xóa của chính mình); gửi push thử cho chính người gọi, trả về đếm đã gửi/tổng số thiết bị (không lộ endpoint — TD-0018) | ✅ GĐ3; đếm gửi thử ✅ TD-0018 |
| `GET /api/stats/daily-summary` | Đã cấp quyền | Số liệu hôm nay (giờ VN): việc tạo mới, đầu ra theo trạng thái, đã đăng hôm nay, đang chờ duyệt/chờ đăng | ✅ GĐ3 |

Cổng mặc định 8790; cấu hình qua biến môi trường (xem `README.md`).

---

## 7. Lộ trình triển khai

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| GĐ1 | API + đăng nhập riêng + di trú dữ liệu | ✅ Xong 24/10/2026 (19/19 test webapp, 215/215 test bot) |
| GĐ2 | Giao diện các luồng chính: đăng nhập, tổng quan, giao việc 3 bước, danh sách/chi tiết việc + thẻ kênh, chờ duyệt, lịch đăng, thống kê; cài dịch vụ chạy nền (cổng 8790) và tạo tài khoản Admin đầu tiên | ✅ Xong 24/10/2026 (37/37 test webapp, 215/215 test bot; commit c9ec262) |
| GĐ3 | Thông báo đẩy Web Push + tổng kết ngày trong Web App (quản lý người dùng trên giao diện đã xong ở GĐ2) | ✅ Xong 24/10/2026 (51/51 test webapp, 215/215 test bot; version app 0.3.0; TD-0008) |
| GĐ4 | Tên miền + HTTPS → chạy song song với bot → đội chuyển hẳn sang Web App → tắt dần bot (dịch vụ chạy nền đã cài từ GĐ2) | 🔶 Tên miền + HTTPS ✅ xong 24/10/2026 (TD-0007: post.iaict-platform.com qua Cloudflare Tunnel); chuyển đội + tắt dần bot 📋 **TẠM DỪNG theo quyết định của chủ dự án ngày 24/10/2026 ("Không chuyển nhé") — bot giữ nguyên toàn bộ, không tắt dần** |
| Sau GĐ3 | Hoàn thiện giao diện theo phản hồi dùng thật và bản thiết kế mới đã chốt: sửa cache vỏ app + lọc việc theo trạng thái (TD-0009, bản 0.3.1), thanh dưới mobile dạng nổi bo tròn (TD-0010, bản 0.3.2), áp toàn bộ giao diện mới — nav mobile 6 cột + nút Giao việc Mẫu 1, collapse/scroll, wizard footer nút chính lên trên, dark mode theo hệ thống (TD-0011, bản 0.4.0) | ✅ Xong 24/10/2026 (53/53 test webapp, 215/215 test bot; kiểm chứng hiển thị thật ở 320/360/390px và 1440px, sáng + tối) |
| Sau GĐ3 — đợt sửa theo phản hồi dùng thật | Sửa nav (TD-0012, bản 0.4.1); đăng Facebook nhiều nơi + khóa nơi chờ (TD-0013, bản 0.5.0; TD-0015, bản 0.5.2); giao diện chip/collapse/cuộn + sửa tràn link (TD-0014, bản 0.5.1); nút X đóng modal (TD-0016, bản 0.5.3); botctl gửi kèm Web Push (TD-0017, bản 0.5.4); modal không trống oan + đồng bộ sống + badge/push app Brave (TD-0018, bản 0.5.5) | ✅ Xong 24–25/10/2026 (bản app 0.5.5; webapp 58/58, bot 251/251; kiểm chứng hiển thị thật ở 320/390/1440, sáng + tối — TD-0014; probe Playwright 15/15 — TD-0018) |
| Ngoài lộ trình | Mini App Telegram (bề mặt thêm, cùng backend/bot.db, nút menu bot + lệnh /miniap) | 📋 Tạm dừng theo quyết định của chủ dự án ngày 24/10/2026 ("Tạm dừng, sửa đã"); chưa đánh số TD; tiếp tục khi chủ dự án nói, bump phiên bản từ bản hiện tại |
| Ngoài lộ trình | Đóng gói native (Capacitor) khi thật sự cần | 📋 |

---

## 8. Lịch sử phiên bản SRS

| Phiên bản | Ngày | Nội dung |
|---|---|---|
| 1.0 | 24/10/2026 | Bản gốc: tổng hợp từ bản thiết kế Web App đã được duyệt (24/10/2026), toàn bộ quy tắc nghiệp vụ đã chốt của hệ thống bot (GĐ1–GĐ2 bot) và GĐ1 Web App đã xây. Từ bản sau, thay đổi đi qua `THAY-DOI.md` rồi tổng hợp vào đây |
| 1.1 | 24/10/2026 | Tổng hợp TD-0006 (GĐ2): giao diện PWA 9 màn hình, upload tư liệu 200MB/tệp, API thao tác thẻ kênh khớp bot, hàng chờ duyệt/lịch đăng, xuất thống kê, hộp thông báo trong app, đổi mật khẩu, quản lý vai trò trên giao diện; cài dịch vụ chạy nền và tạo tài khoản Admin đầu tiên. Việc còn lại: Web Push (GĐ3), tên miền/HTTPS (GĐ4) |
| 1.2 | 24/10/2026 | Tổng hợp TD-0008 (GĐ3): Web Push chuẩn VAPID/RFC 8291 (EC qua openssl CLI, AES-128-GCM thuần Python đã kiểm chứng vector; khóa VAPID ngoài repo), API đăng ký/hủy/gửi thử push, hook thông báo tại tạo việc và các thao tác thẻ kênh, tổng kết ngày trong app (endpoint + thẻ Tổng quan + push/inbox 20:00 giờ VN chống gửi trùng). Kiểm thử: webapp 51/51, bot 215/215; app 0.3.0. Việc còn lại: chuyển đội + tắt dần bot (GĐ4; tên miền/HTTPS đã xong trước — TD-0007) |
| 1.3 | 24/10/2026 | Tổng hợp TD-0007 (phần tên miền/HTTPS của GĐ4: post.iaict-platform.com qua Cloudflare Tunnel + 2 dịch vụ phụ trợ cf-dns-stub/cf-edge-relay do netstack máy chủ ảo), TD-0009 (sửa cache vỏ app network-first + SW v4, thẻ thông báo đẩy luôn hiện kèm trạng thái, bỏ hàng chip-nav trùng mobile, lọc việc theo trạng thái kèm counts, gọn block chọn file; bản 0.3.1), TD-0010 (thanh dưới mobile dạng nổi bo tròn, mục chọn viên thuốc teal nhạt, nút Giao việc tròn nổi; bản 0.3.2), TD-0011 (áp toàn bộ giao diện mới đã chốt: nav mobile 6 cột + nút Giao việc Mẫu 1 "Gradient viền trắng" 54px không đổ bóng nhô 19px, badge tròn 19×19, bảng "Thêm", collapse/scroll, wizard footer nút chính lên trên, dark mode theo hệ thống; bản 0.4.0, SW cache v6). Kiểm thử: webapp 53/53, bot 215/215; kiểm chứng hiển thị thật ở 320/360/390px và 1440px, sáng + tối. Việc còn lại: chuyển đội + tắt dần bot (GĐ4) |
| 1.4 | 25/10/2026 | Tổng hợp TD-0012 (sửa nav mobile: nút Giao việc 58px nhô ~7px, nút thanh dưới khi active nền trong suốt sửa lỗi chữ chìm; bản 0.4.1, SW cache v7), TD-0013 (đăng Facebook nhiều nơi cùng lúc: khóa nơi `profile`/`page_<id>`, bảng `facebook_pages` + 6 cột outputs mới, picker bot toggle + modal web checkbox, PUBLISHED chỉ khi đủ các nơi, thu hồi từng nơi, lịch lưu cả tập hợp; bản 0.5.0, SW cache v8), TD-0014 (dải chip lọc nổi bật + fade, nút thu gọn danh sách nhớ localStorage, quy tắc cuộn desktop/mobile, sửa thông báo tràn link dài; bản 0.5.1, SW cache v9), TD-0015 (khóa nơi đang chờ đăng + chặn 409 + hủy dọn request, link Facebook kiểu cũ suy từ audit, botctl ghi hàng web khi đăng/thu hồi, badge PWA, icon Thêm •••, tải thêm tư liệu muộn có chú thích + báo người duyệt/Admin; bản 0.5.2, SW cache v10), TD-0016 (nút X đóng modal góc phải trên, chỉ đóng không xác nhận; bản 0.5.3, SW cache v11), TD-0017 (botctl đăng/thu hồi/lỗi gửi kèm Web Push tới mọi subscription, tôn trọng `--no-notify`, lỗi gửi không hỏng lệnh; bản 0.5.4, SW cache v12), TD-0018 (modal nơi đăng không cache kết quả lỗi + nút thử lại, đồng bộ sống poll 30 giây + quay lại app + SW postMessage "gv-push", giới hạn badge thật trên Chromium Android/Brave đã xác minh theo MDN; bản 0.5.5, SW cache v13). Kiểm thử: webapp 58/58, bot 251/251. Việc còn lại: chuyển đội + tắt dần bot (GĐ4, TẠM DỪNG theo quyết định chủ dự án 24/10/2026), Mini App Telegram (tạm dừng), kênh Website (chưa có link), SMS Meta chưa xác nhận, đăng YouTube/TikTok thật (GĐ3 bot) |
