# Hướng dẫn Sử dụng — DichVuCong AI Assistant

> Phiên bản: v3.79 | Cập nhật: 2026-05-11

---

## Mục lục

1. [Giới thiệu hệ thống](#1-giới-thiệu-hệ-thống)
2. [Truy cập hệ thống](#2-truy-cập-hệ-thống)
3. [Các trang chính của cổng dịch vụ](#3-các-trang-chính-của-cổng-dịch-vụ)
4. [Trợ lý AI](#4-trợ-lý-ai)
5. [Hỏi thông tin pháp lý](#5-hỏi-thông-tin-pháp-lý)
6. [Upload CCCD và nhận dạng tự động](#6-upload-cccd-và-nhận-dạng-tự-động)
7. [Trình hướng dẫn thủ tục từng bước](#7-trình-hướng-dẫn-thủ-tục-từng-bước)
8. [Điền và tải tờ khai](#8-điền-và-tải-tờ-khai)
9. [Tra cứu hồ sơ](#9-tra-cứu-hồ-sơ)
10. [Phản hồi và đánh giá chất lượng](#10-phản-hồi-và-đánh-giá-chất-lượng)
11. [Các thủ tục được hỗ trợ](#11-các-thủ-tục-được-hỗ-trợ)
12. [Xử lý sự cố thường gặp](#12-xử-lý-sự-cố-thường-gặp)

---

## 1. Giới thiệu hệ thống

**DichVuCong AI Assistant** là cổng dịch vụ công trực tuyến thử nghiệm tích hợp trợ lý AI. Hệ thống hỗ trợ người dùng:

- Tra cứu thông tin pháp lý liên quan đến các thủ tục hành chính
- Tìm hiểu quy trình và hồ sơ cần thiết cho từng thủ tục
- Tự động nhận dạng thông tin từ ảnh CCCD (Căn cước công dân) qua mã QR hoặc OCR
- Tự động điền tờ khai hành chính và xuất file PDF
- Theo dõi tiến trình hoàn thành các thủ tục phụ thuộc lẫn nhau

**Lĩnh vực hiện được hỗ trợ:**

| Lĩnh vực | Mô tả |
|---|---|
| Cư trú (Đăng ký hộ khẩu) | Đăng ký thường trú, đăng ký tạm trú, xác nhận thông tin cư trú |
| Hộ tịch | Đăng ký khai sinh, cấp bản sao trích lục hộ tịch |
| Nuôi con nuôi | Đăng ký nuôi con nuôi, đăng ký lại nuôi con nuôi |

---

## 2. Truy cập hệ thống

### Yêu cầu

- Trình duyệt web hiện đại: Chrome 90+, Firefox 88+, Edge 90+, Safari 14+
- Kết nối internet ổn định
- Cho phép JavaScript

### Đăng nhập

Khi truy cập lần đầu, hệ thống hiển thị cửa sổ nhập mã PIN.

1. Nhập PIN: **`2026`** (mặc định)
2. Nhấn **Xác nhận** hoặc phím `Enter`
3. Hệ thống ghi nhớ trạng thái đăng nhập trong tab trình duyệt hiện tại

> **Lưu ý:** PIN có thể được cấu hình khác nhau tùy môi trường triển khai. Liên hệ quản trị viên nếu PIN mặc định không hoạt động.

### URL

- **Môi trường phát triển:** [http://localhost:3000](http://localhost:3000)
- **Môi trường demo (Ngrok):** URL được cung cấp riêng bởi người vận hành

---

## 3. Các trang chính của cổng dịch vụ

### Trang chủ (`/`)

Trang giới thiệu tổng quan về cổng dịch vụ. Bao gồm:
- Widget chat AI dạng nhúng (inline) ở vị trí nổi bật
- Danh sách nhanh các dịch vụ phổ biến
- Thông tin hướng dẫn bắt đầu

### Dịch vụ công (`/dich-vu-cong`)

Danh sách tất cả dịch vụ hành chính trực tuyến được phân loại theo lĩnh vực.

### Tra cứu hồ sơ (`/tra-cuu-ho-so`)

Tra cứu tiến trình xử lý hồ sơ đã nộp bằng mã hồ sơ (dạng `DVC-YYYYMMDD-XXXXXX`).

### Chat với AI (`/chat`)

Giao diện chat đầy đủ với trợ lý AI, phù hợp khi cần hội thoại dài. Bao gồm cả panel hiển thị hoạt động agent (Agent Activity Panel).

### Câu hỏi thường gặp (`/cau-hoi-thuong-gap`)

Kho câu hỏi phổ biến về các thủ tục hành chính, được phân loại theo chủ đề.

### Đánh giá chất lượng (`/danh-gia-chat-luong`)

Gửi phản hồi tổng thể về chất lượng dịch vụ (khác với nút đánh giá từng câu trả lời của AI).

### Thanh toán lệ phí (`/thanh-toan`)

Thanh toán trực tuyến lệ phí hành chính (tính năng thử nghiệm).

### Trang thủ tục (`/thu-tuc/<ten-thu-tuc>`)

Mỗi thủ tục có trang riêng với form điền tờ khai tương tác, hướng dẫn chi tiết, và danh sách giấy tờ cần thiết.

---

## 4. Trợ lý AI

Trợ lý AI xuất hiện ở hai vị trí:

### 4.1 Widget nổi (Floating Widget)

- Biểu tượng chat ở **góc dưới bên phải** mọi trang
- Nhấn biểu tượng để mở/đóng cửa sổ chat (360×520px)
- Nhấn **↗** để mở rộng sang trang `/chat` đầy đủ

### 4.2 Widget nhúng (Inline — Trang chủ)

- Hiển thị cố định trên trang chủ, không thể thu nhỏ
- Phù hợp để bắt đầu cuộc hội thoại đầu tiên

### 4.3 Giao diện chat

#### Gửi tin nhắn

- **Gõ** nội dung vào ô nhập liệu bên dưới
- Nhấn `Enter` để gửi
- Nhấn `Shift + Enter` để xuống dòng
- Nhấn **↑** (nút mũi tên) hoặc biểu tượng **paperclip** để đính kèm ảnh/tài liệu

#### Trong khi AI trả lời

- Chỉ thị **"Đang sinh câu trả lời..."** với ba dấu chấm nhấp nháy xuất hiện
- Văn bản phản hồi hiển thị từng chữ theo thời gian thực (streaming)
- Nếu không có phản hồi sau 5 giây, hệ thống hiển thị thông báo chờ

#### Sau khi nhận phản hồi

- **Nút đánh giá:** 👍 (hữu ích) và 👎 (không hữu ích) — chỉ chọn được một lần
- **Nút thử lại:** Xuất hiện nếu có lỗi, cho phép gửi lại tin nhắn cuối cùng
- **Nút tải xuống:** Xuất hiện khi tờ khai đã được điền xong (xem mục 8)

#### Quản lý hội thoại

- **Nút ↻ (Cuộc hội thoại mới):** Xóa toàn bộ lịch sử và tạo phiên mới
- **Nút ↗ (Mở rộng):** Chuyển sang trang `/chat` đầy đủ
- **Nút × (Đóng):** Thu nhỏ widget (chỉ với widget nổi)

---

## 5. Hỏi thông tin pháp lý

Trợ lý AI tích hợp hệ thống RAG (Retrieval-Augmented Generation) để trả lời câu hỏi dựa trên văn bản pháp luật thực tế.

### Cách đặt câu hỏi hiệu quả

**Câu hỏi về hồ sơ, giấy tờ:**
> "Đăng ký thường trú cần những giấy tờ gì?"
> "Để đăng ký khai sinh cho con, tôi cần chuẩn bị những gì?"

**Câu hỏi về quy trình:**
> "Quy trình đăng ký tạm trú như thế nào?"
> "Thời gian xử lý hồ sơ đăng ký thường trú là bao lâu?"

**Câu hỏi về điều kiện:**
> "Ai được phép đăng ký thường trú tại chỗ ở thuê?"
> "Điều kiện để đăng ký nuôi con nuôi là gì?"

**Câu hỏi theo địa bàn:**
> "Thủ tục đăng ký tạm trú ở TP. Hồ Chí Minh như thế nào?"
> "Tại Hà Nội, tôi nộp hồ sơ đăng ký thường trú ở đâu?"

### Đọc trích dẫn pháp luật

Các câu trả lời có cơ sở pháp lý thường kèm theo **chip trích dẫn** màu xanh dưới phản hồi.

- **Nhấn/hover** vào chip để xem nội dung điều khoản đầy đủ
- Định dạng trích dẫn: `Điều X, Nghị định/Thông tư YYY/YYYY/NĐ-CP`
- Mỗi trích dẫn đã được hệ thống xác minh là có trong văn bản được tải vào hệ thống

> **Ví dụ chip trích dẫn:**
> `[Điều 20, Luật 68/2020/QH14]` `[Điều 7, Nghị định 62/2021/NĐ-CP]`

### Giới hạn của hệ thống

- Hệ thống chỉ trả lời về **3 lĩnh vực** đã được cấu hình (cư trú, hộ tịch, nuôi con nuôi)
- Câu hỏi ngoài phạm vi sẽ nhận thông báo từ chối lịch sự
- Thông tin dựa trên văn bản pháp luật đã được nạp — không tra cứu internet thời gian thực

---

## 6. Upload CCCD và nhận dạng tự động

Hệ thống có thể tự động đọc thông tin từ ảnh **Căn cước công dân (CCCD)** và điền vào tờ khai hành chính.

### 6.1 Các loại giấy tờ được hỗ trợ

| Loại | Mô tả |
|---|---|
| CCCD (Căn cước công dân) | Có chip hoặc không chip, thế hệ 2016 và 2021 |
| Giấy khai sinh | Hỗ trợ qua OCR |
| Sổ hộ khẩu | Hỗ trợ qua OCR |
| Giấy chứng nhận đất | Hỗ trợ qua OCR |

### 6.2 Cách upload

**Cách 1 — Trong chat:**
1. Nhấn biểu tượng **paperclip** (📎) trong ô nhập tin nhắn
2. Chọn file ảnh (JPEG, PNG) hoặc PDF
3. Ảnh preview xuất hiện ở góc trên ô nhập
4. Gửi tin nhắn kèm ảnh (có thể kèm câu hỏi hoặc để trống)

**Cách 2 — Trong hướng dẫn thủ tục:**
Khi đang ở bước 1 của trình hướng dẫn (xem mục 7), hệ thống tự động hiện hướng dẫn upload tài liệu.

### 6.3 Quy trình xử lý

Hệ thống thực hiện theo hai đường:

**Đường nhanh — Quét mã QR (~200ms):**
- CCCD thế hệ 2021 có mã QR mã hóa toàn bộ thông tin
- Hệ thống tự động phát hiện và đọc mã QR
- Độ chính xác: 100% (dữ liệu lấy trực tiếp từ chip)

**Đường dự phòng — OCR (~2–5 giây):**
- Áp dụng khi không có mã QR hoặc QR bị hỏng
- Ảnh được tiền xử lý: làm thẳng, tăng tương phản, khử nhiễu
- PaddleOCR nhận dạng văn bản
- AI trích xuất và cấu trúc hóa các trường thông tin

### 6.4 Kết quả nhận dạng

Sau khi xử lý, AI phản hồi với thông tin đã trích xuất:

```
Đọc thông tin CCCD thành công (qua mã QR):
- Họ tên: NGUYỄN VĂN AN
- Ngày sinh: 15/05/1990
- Giới tính: Nam
- Số CCCD: 001090012345
- Địa chỉ thường trú: 123 Đường Láng, Phường Láng Thượng, Quận Đống Đa, Hà Nội
```

### 6.5 Dữ liệu carry-forward

Thông tin cá nhân được trích xuất sẽ **tự động lưu trong phiên làm việc**. Bạn không cần upload lại khi chuyển sang bước tiếp theo hoặc điền tờ khai khác trong cùng phiên.

---

## 7. Trình hướng dẫn thủ tục từng bước

Trình hướng dẫn là tính năng tự động dẫn dắt người dùng qua toàn bộ quy trình hoàn thành một thủ tục, từ chuẩn bị hồ sơ đến xuất tờ khai đã điền.

### 7.1 Khởi động hướng dẫn

Để bắt đầu hướng dẫn, gõ yêu cầu theo một trong các mẫu sau:

> "Hướng dẫn tôi đăng ký thường trú"
> "Giúp tôi làm thủ tục đăng ký khai sinh"
> "Tôi muốn đăng ký tạm trú, bắt đầu từ đâu?"

Khi hướng dẫn bắt đầu, thanh tiến trình xuất hiện phía trên khung chat với 4 bước.

### 7.2 Bốn bước của hướng dẫn

#### Bước 0 — Giới thiệu (INTRO)

Hệ thống trình bày:
- Tổng quan về thủ tục
- Danh sách giấy tờ cần chuẩn bị
- Điều kiện và lưu ý quan trọng

Thanh tiến trình: ● ○ ○ ○

#### Bước 1 — Upload CCCD (AWAIT_CCCD)

Hệ thống yêu cầu upload ảnh CCCD để tự động điền thông tin.

Thanh tiến trình: ● ● ○ ○

**Hành động của người dùng:**
1. Nhấn biểu tượng 📎 trong ô chat
2. Chọn ảnh CCCD
3. Gửi (có thể kèm tin nhắn hoặc không)

Hệ thống tự động chuyển sang bước tiếp theo sau khi xử lý thành công.

#### Bước 2 — Điền tờ khai (FORM_FILLING)

**Với thủ tục cư trú (TTHC-001/002/003):**
- AI tự động điền tờ khai bằng dữ liệu từ CCCD
- Nút tải xuống PDF xuất hiện trong chat
- Thông báo các trường còn thiếu (nếu có)

**Với thủ tục hộ tịch và nuôi con nuôi:**
- AI thông báo dữ liệu đã được điền vào form trên trang thủ tục
- Chuyển sang trang `/thu-tuc/<ten-thu-tuc>` để kiểm tra và hoàn thiện
- Nhấn **"Tải xuống tờ khai đã điền"** trên trang thủ tục

Thanh tiến trình: ● ● ● ○

#### Bước 3 — Hoàn thành (COMPLETE)

Hệ thống xác nhận hoàn thành, cung cấp hướng dẫn nộp hồ sơ và thông tin liên hệ cơ quan tiếp nhận.

Thanh tiến trình: ● ● ● ●

### 7.3 Thoát hướng dẫn

Tại bất kỳ bước nào, gõ một trong các từ sau để thoát:

> `thoát` · `hủy` · `dừng lại` · `thôi`

Nhấn **"Thoát hướng dẫn"** trên thanh tiến trình cũng có tác dụng tương tự.

---

## 8. Điền và tải tờ khai

### 8.1 Tự động điền qua AI

Sau khi upload CCCD và kết nối với thủ tục (qua trình hướng dẫn), hệ thống:

1. Ánh xạ dữ liệu CCCD sang các trường của tờ khai tương ứng
2. Điền tờ khai và lưu file PDF tạm thời
3. Hiển thị nút **"📄 Tải xuống tờ khai đã điền"** trong chat

### 8.2 Trường chưa điền được

Nếu một số trường bắt buộc không thể tự động điền (thiếu thông tin từ CCCD), AI sẽ liệt kê rõ ràng:

```
Tờ khai đã được điền một phần. Các trường còn cần bổ sung:
- Quan hệ với chủ hộ
- Họ tên chủ hộ
- Số CCCD của chủ hộ

Vui lòng cung cấp các thông tin trên để hoàn thiện tờ khai.
```

### 8.3 Điền thủ công trên trang thủ tục

Mỗi trang thủ tục có form điền trực tiếp:

1. Truy cập trang thủ tục (ví dụ: `/thu-tuc/dang-ky-thuong-tru`)
2. Nếu đã upload CCCD trước đó, các trường được hỗ trợ sẽ tự động được điền
3. Kiểm tra và bổ sung thông tin còn thiếu
4. Nhấn **"Tải xuống tờ khai đã điền"** để tải PDF
5. Nhấn **"Nộp hồ sơ"** để nộp trực tuyến và nhận mã hồ sơ

### 8.4 Thông tin về file PDF

- File PDF là tờ khai có thể in ngay, sẵn sàng để nộp tại cơ quan có thẩm quyền
- File tạm thời được lưu trong 1 giờ — tải xuống ngay sau khi nhận
- Tên file: `to-khai-<ma-thu-tuc>.pdf`

---

## 9. Tra cứu hồ sơ

Sau khi nộp hồ sơ trực tuyến, bạn nhận được **mã hồ sơ** dạng `DVC-YYYYMMDD-XXXXXX`.

### Cách tra cứu

1. Truy cập trang **Tra cứu hồ sơ** (`/tra-cuu-ho-so`)
2. Nhập mã hồ sơ vào ô tìm kiếm
3. Nhấn **Tra cứu**

### Trạng thái hồ sơ

| Trạng thái | Mô tả |
|---|---|
| `Đã tiếp nhận` | Hồ sơ đã được ghi nhận, chờ xử lý |
| `Đang xử lý` | Cơ quan chức năng đang xem xét |
| `Hoàn thành` | Hồ sơ đã được giải quyết |

---

## 10. Phản hồi và đánh giá chất lượng

### Đánh giá từng câu trả lời

Mỗi phản hồi của AI có nút **👍** và **👎**:
- Nhấn 👍 nếu câu trả lời hữu ích và chính xác
- Nhấn 👎 nếu câu trả lời không phù hợp hoặc sai
- Chỉ chọn được một lần cho mỗi tin nhắn

### Đánh giá tổng thể dịch vụ

Truy cập trang **Đánh giá chất lượng** (`/danh-gia-chat-luong`) để gửi phản hồi về toàn bộ trải nghiệm sử dụng dịch vụ.

---

## 11. Các thủ tục được hỗ trợ

### Lĩnh vực Cư trú

| Mã thủ tục | Tên thủ tục | Tờ khai | Thời gian xử lý |
|---|---|---|---|
| TTHC-001 | Đăng ký thường trú | 2 tờ khai | 3–5 ngày làm việc |
| TTHC-002 | Đăng ký tạm trú | 1 tờ khai | 2–3 ngày làm việc |
| TTHC-003 | Xác nhận thông tin cư trú | 1 tờ khai | 1–2 ngày làm việc |

### Lĩnh vực Hộ tịch

| Mã thủ tục | Tên thủ tục | Tờ khai | Thời gian xử lý |
|---|---|---|---|
| TTHC-CR-001 | Đăng ký khai sinh | 1 tờ khai | 2–3 ngày làm việc |
| TTHC-CR-002 | Cấp bản sao trích lục hộ tịch | 1 tờ khai | 1–2 ngày làm việc |

### Lĩnh vực Nuôi con nuôi

| Mã thủ tục | Tên thủ tục | Tờ khai | Thời gian xử lý |
|---|---|---|---|
| TTHC-AD-001 | Đăng ký nuôi con nuôi | 1 tờ khai | 15–30 ngày làm việc |
| TTHC-AD-002 | Đăng ký lại nuôi con nuôi | 1 tờ khai | 5–7 ngày làm việc |

> **Lưu ý:** Thời gian xử lý là ước tính. Thời gian thực tế có thể thay đổi tùy theo cơ quan có thẩm quyền và tính đầy đủ của hồ sơ.

### Phụ thuộc thủ tục

Một số thủ tục cần hoàn thành thủ tục khác trước:

- **Đăng ký thường trú (TTHC-001)** yêu cầu đã có **địa chỉ cư trú hợp pháp** (có thể cần TTHC-002 trước nếu chưa có)
- AI tự động phát hiện và thông báo các thủ tục còn thiếu trong kế hoạch

---

## 12. Xử lý sự cố thường gặp

### Không nhận được phản hồi / màn hình trắng

**Nguyên nhân thường gặp:** Server backend chưa sẵn sàng (đang tải model AI).

**Giải pháp:**
1. Đợi 30–60 giây rồi thử lại
2. Kiểm tra bằng cách truy cập `http://localhost:8000/health` — nếu thấy `"status": "warming_up"` thì chờ thêm
3. Làm mới trang (F5) sau khi server sẵn sàng

### Lỗi "Quá nhiều yêu cầu" (HTTP 429)

**Nguyên nhân:** Gửi quá 10 tin nhắn/phút hoặc quá 5 upload/phút.

**Giải pháp:**
- Đợi 60 giây rồi thử lại
- Tránh gửi nhiều yêu cầu liên tiếp trong thời gian ngắn

### Upload CCCD thất bại hoặc nhận dạng sai

**Nguyên nhân thường gặp:**
- Ảnh mờ, thiếu sáng, hoặc bị xoay
- Phần mã QR bị che khuất
- Định dạng file không được hỗ trợ

**Giải pháp:**
1. Chụp lại ảnh CCCD với ánh sáng đủ, đặt thẳng
2. Đảm bảo toàn bộ mã QR (góc dưới phải) hiện rõ
3. Dùng ảnh JPEG hoặc PNG (không phải HEIC/WebP)
4. Nếu OCR trả về thông tin sai, nhập thủ công trên trang thủ tục

### Phản hồi AI ngoài chủ đề

**Nguyên nhân:** Câu hỏi không thuộc lĩnh vực cư trú, hộ tịch, hoặc nuôi con nuôi.

**Giải pháp:**
- Đặt lại câu hỏi với ngữ cảnh cụ thể hơn
- Hỏi đúng về một trong các thủ tục được hỗ trợ

### Nút tải xuống tờ khai không xuất hiện

**Nguyên nhân:** Tờ khai chưa được điền xong hoặc còn trường bắt buộc.

**Giải pháp:**
1. Kiểm tra tin nhắn của AI — thường có danh sách các trường còn thiếu
2. Cung cấp thông tin còn thiếu trong chat
3. Hoặc chuyển sang trang thủ tục để điền thủ công

### Mất phiên làm việc

**Nguyên nhân:** Phiên hết hạn sau 1 giờ không hoạt động, hoặc xóa dữ liệu trình duyệt.

**Giải pháp:**
- Nhấn nút ↻ **Cuộc hội thoại mới** để bắt đầu phiên mới
- Upload lại CCCD nếu cần tiếp tục điền tờ khai
- Dữ liệu hồ sơ đã nộp không bị ảnh hưởng (lưu trong hệ thống)
