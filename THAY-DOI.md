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

## Mục chờ cập nhật vào SRS

- **TD-0006** — ✅ Đã tổng hợp vào **SRS 1.1** ngày 24/10/2026 (đóng GĐ2).
