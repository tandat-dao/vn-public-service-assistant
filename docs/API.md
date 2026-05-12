# Tài liệu API — DichVuCong AI Assistant

> Phiên bản: v3.79 | Cập nhật: 2026-05-11

---

## Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Giới hạn tốc độ](#2-giới-hạn-tốc-độ)
3. [Định dạng SSE (Server-Sent Events)](#3-định-dạng-sse)
4. [Endpoints](#4-endpoints)
   - [POST /api/v1/chat](#41-post-apiv1chat)
   - [POST /api/v1/documents/upload](#42-post-apiv1documentsupload)
   - [GET /api/v1/documents/download](#43-get-apiv1documentsdownload)
   - [POST /api/v1/forms/fill](#44-post-apiv1formsfill)
   - [GET /api/v1/forms/configs/{procedure_id}](#45-get-apiv1formsconfigsprocedure_id)
   - [POST /api/v1/forms/submit](#46-post-apiv1formssubmit)
   - [POST /api/v1/feedback](#47-post-apiv1feedback)
   - [GET /health](#48-get-health)
5. [Schemas](#5-schemas)
6. [Cấu hình CORS](#6-cấu-hình-cors)

---

## 1. Tổng quan

| Thuộc tính | Giá trị |
|---|---|
| Base URL | `http://localhost:8000` |
| Prefix API | `/api/v1` |
| Xác thực | Không có (PIN gate chỉ ở frontend) |
| Content-Type yêu cầu | `application/json` (trừ upload: `multipart/form-data`) |
| Content-Type phản hồi | `application/json`, `text/event-stream`, `application/pdf` |

> Các endpoint `/api/v1/procedures/*` và `/api/v1/legal/*` được khai báo trong router nhưng **chưa được triển khai** — trả về `501 Not Implemented`.

---

## 2. Giới hạn tốc độ

| Endpoint | Giới hạn mặc định | Cấu hình |
|---|---|---|
| `POST /api/v1/chat` | 10 yêu cầu/phút | `CHAT_RATE_LIMIT` trong `.env` |
| `POST /api/v1/documents/upload` | 5 yêu cầu/phút | `UPLOAD_RATE_LIMIT` trong `.env` |

**Khóa rate limit:** Hệ thống ưu tiên dùng `session_id` từ request body. Nếu không có, fallback về địa chỉ IP.

**Khi vượt giới hạn — HTTP 429:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Quá nhiều yêu cầu. Vui lòng thử lại sau."
}
```

---

## 3. Định dạng SSE

Endpoint `/api/v1/chat` trả về luồng [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events). Một kết nối SSE chứa nhiều loại event khác nhau.

### 3.1 Pipeline Events (hoạt động agent)

Định dạng:
```
event: pipeline_event
data: {"type": "<EVENT_TYPE>", ...}

```

| `type` | Mô tả | Trường dữ liệu bổ sung |
|---|---|---|
| `pipeline_start` | Router node bắt đầu | — |
| `plan_decided` | Router hoàn thành, có execution plan | `plan: list[str]`, `intent: str`, `domain: str \| null` |
| `enrichment_result` | Enrichment node hoàn thành | `procedure_id: str`, `steps: int` |
| `parallel_wave_start` | Nhiều worker bắt đầu song song | `workers: list[str]` |
| `worker_start` | Một worker bắt đầu | `worker: str`, `label: str` |
| `worker_complete` | Một worker hoàn thành | `worker: str`, `duration_ms: int` |
| `rag_result` | RAG truy xuất xong | `chunks: int`, `scope: str \| null` |
| `ocr_result` | OCR trích xuất xong | `document_type: str`, `confidence: float`, `fields_extracted: int` |
| `form_result` | Form fill hoàn thành | `complete: bool`, `unfilled: int` |
| `pipeline_complete` | Synthesizer hoàn thành | `mode: str`, `total_ms: int` |

> **Lưu ý bảo mật:** Payload pipeline events **không bao giờ** chứa thông tin cá nhân (PII). Chỉ có số lượng trường, độ tin cậy, và loại tài liệu.

### 3.2 Text Chunks (nội dung phản hồi)

```
data: {"content": "Để đăng ký thường trú, bạn cần"}

```

Các chunk được gửi từng nhóm nhỏ (~3 ký tự). Frontend ghép lại để tạo hiệu ứng đánh máy.

### 3.3 Metadata

```
data: {"metadata": {"mode": "rag_only", "citations": [...], "guided_step": null}}

```

Gửi **một lần** sau khi toàn bộ text đã stream xong.

### 3.4 Kết thúc luồng

```
data: [DONE]

```

Frontend dùng event này để biết phản hồi đã hoàn tất.

### 3.5 Nhãn Worker

| `worker` | `label` hiển thị |
|---|---|
| `rag_fn` | `RAG` |
| `ocr_fn` | `OCR` |
| `form_filler_fn` | `Form filler` |

---

## 4. Endpoints

### 4.1 POST /api/v1/chat

Gửi tin nhắn của người dùng và nhận phản hồi AI qua SSE.

**Rate limit:** 10/phút (keyed by session_id → IP)

#### Request Body

```json
{
  "message": "Đăng ký thường trú cần những giấy tờ gì?",
  "session_id": "user-session-abc123",
  "image_path": null,
  "citizen_id": null
}
```

| Trường | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `message` | `string` | **Có** | Nội dung tin nhắn (1–2000 ký tự) |
| `session_id` | `string` | **Có** | Mã phiên người dùng (≤128 ký tự) |
| `image_path` | `string \| null` | Không | Đường dẫn MinIO đến file ảnh đã upload (dạng `tmp/{session_id}/...`) |
| `citizen_id` | `string \| null` | Không | Mã công dân để tải dữ liệu cá nhân carry-forward từ Redis |

#### Response

`Content-Type: text/event-stream`

Luồng SSE gồm các event theo thứ tự:
1. Một hoặc nhiều `pipeline_event` (hoạt động agent)
2. Nhiều `data: {"content": "..."}` (text câu trả lời)
3. Một `data: {"metadata": {...}}` (thông tin bổ sung)
4. `data: [DONE]` (kết thúc)

**Ví dụ phản hồi (rút gọn):**
```
event: pipeline_event
data: {"type": "pipeline_start"}

event: pipeline_event
data: {"type": "plan_decided", "plan": ["rag_fn"], "intent": "rag_query", "domain": "housing"}

event: pipeline_event
data: {"type": "worker_start", "worker": "rag_fn", "label": "RAG"}

event: pipeline_event
data: {"type": "rag_result", "chunks": 8, "scope": "VN"}

event: pipeline_event
data: {"type": "pipeline_complete", "mode": "rag_only", "total_ms": 1842}

data: {"content": "Để đăng ký thường trú"}

data: {"content": ", bạn cần chuẩn bị"}

data: {"metadata": {"mode": "rag_only", "citations": [{"doc_id": "...", "article": "Điều 20", "document_number": "68/2020/QH14", "excerpt": "..."}]}}

data: [DONE]
```

#### Xử lý lỗi

| Tình huống | Phản hồi |
|---|---|
| Vượt giới hạn tốc độ | HTTP 429 JSON |
| Lỗi vòng lặp agent (`GraphRecursionError`) | HTTP 200 SSE với text thông báo lỗi |
| Redis không khởi động được phiên | Bắt đầu phiên mới (không báo lỗi người dùng) |
| Worker thất bại (RAG/OCR/Form) | Lỗi được tích lũy trong state, tóm tắt trong phản hồi cuối |

---

### 4.2 POST /api/v1/documents/upload

Tải lên ảnh/PDF giấy tờ tùy thân để trích xuất thông tin cá nhân qua OCR.

**Rate limit:** 5/phút (keyed by session_id → IP)

**Content-Type:** `multipart/form-data`

#### Request (Form Data)

| Trường | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `file` | `UploadFile` | **Có** | File ảnh (JPEG/PNG) hoặc PDF |
| `session_id` | `string` | **Có** | Mã phiên người dùng (≤128 ký tự) |
| `citizen_id` | `string` | Không | Mã công dân để lưu dữ liệu carry-forward vào Redis |

#### Response — HTTP 200

```json
{
  "status": "success",
  "tmp_path": "tmp/user-session-abc123/f7e3a1b2-cccd.jpg",
  "personal_data": {
    "full_name": "NGUYỄN VĂN AN",
    "full_name_latin": "NGUYEN VAN AN",
    "date_of_birth": "1990-05-15",
    "gender": "Nam",
    "nationality": "Việt Nam",
    "id_number": "001090012345",
    "id_issue_date": "2021-03-20",
    "id_issue_place": "CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    "permanent_address": {
      "street": "123 Đường Láng",
      "ward": "Phường Láng Thượng",
      "district": "Quận Đống Đa",
      "province": null,
      "city": "Hà Nội",
      "country": "Việt Nam"
    },
    "source_document_type": "cccd",
    "source_image_path": "tmp/user-session-abc123/f7e3a1b2-cccd.jpg",
    "extraction_confidence": 1.0,
    "field_confidences": {
      "full_name": 1.0,
      "id_number": 1.0,
      "date_of_birth": 1.0
    },
    "extracted_at": "2026-05-11T10:30:00Z"
  },
  "ocr_confidence": 1.0,
  "message": "Đọc thông tin CCCD thành công qua mã QR."
}
```

**Khi OCR thất bại (status: "partial"):**
```json
{
  "status": "partial",
  "tmp_path": "tmp/user-session-abc123/f7e3a1b2-cccd.jpg",
  "personal_data": null,
  "ocr_confidence": 0.0,
  "message": "File đã được lưu nhưng không thể đọc thông tin. Vui lòng nhập thủ công."
}
```

#### HTTP Status Codes

| Code | Tình huống |
|---|---|
| `200` | Thành công hoặc partial (file đã lưu) |
| `422` | File rỗng hoặc không hợp lệ (định dạng, kích thước) |
| `429` | Vượt giới hạn tốc độ |
| `500` | MinIO upload thất bại |

#### Pipeline OCR

```
Upload file
  ↓
Kiểm tra định dạng và kích thước (file_validator.py)
  ↓
Lưu vào MinIO: tmp/{session_id}/{uuid}{ext}
  ↓
Thử decode QR code CCCD (~200ms, confidence=1.0)
  ↓ (nếu QR thất bại)
PaddleOCR + tiền xử lý ảnh (OpenCV: làm thẳng, tăng tương phản, khử nhiễu)
  ↓
LLM trích xuất trường dữ liệu từ text OCR
  ↓
Trả về PersonalData + lưu vào Redis session
```

---

### 4.3 GET /api/v1/documents/download

Tải xuống file PDF đã điền từ MinIO.

#### Query Parameters

| Tham số | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `path` | `string` | **Có** | Đường dẫn MinIO (dạng `tmp/{session_id}/...` hoặc `forms/{session_id}/...`) |
| `session_id` | `string` | **Có** | Mã phiên người dùng để xác minh quyền truy cập |

**Ví dụ:**
```
GET /api/v1/documents/download?path=forms/abc123/TTHC-001.pdf&session_id=abc123
```

#### Response — HTTP 200

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="to-khai-TTHC-001.pdf"

<binary PDF data>
```

#### HTTP Status Codes

| Code | Tình huống |
|---|---|
| `200` | File PDF trả về thành công |
| `403` | `session_id` trong `path` không khớp với tham số `session_id` |
| `404` | File không tồn tại hoặc đã hết hạn |

---

### 4.4 POST /api/v1/forms/fill

Điền tờ khai `.doc` với dữ liệu được cung cấp và trả về file PDF.

#### Request Body

```json
{
  "procedure_id": "TTHC-001",
  "form_file": "to_khai_thay_doi_tt_cu_tru.doc",
  "field_values": {
    "ho_ten": "NGUYỄN VĂN AN",
    "ngay_sinh": "15/05/1990",
    "so_cccd": "001090012345"
  }
}
```

| Trường | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `procedure_id` | `string` | **Có** | Mã thủ tục (phải tồn tại trong hệ thống) |
| `form_file` | `string` | **Có** | Tên file `.doc` của tờ khai |
| `field_values` | `dict[str, str]` | Không | Giá trị các trường cần điền |

#### Response — HTTP 200

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="to-khai-TTHC-001.pdf"

<binary PDF data>
```

#### HTTP Status Codes

| Code | Tình huống |
|---|---|
| `200` | PDF trả về thành công |
| `404` | File `.doc` không tìm thấy |
| `422` | `form_file` không hợp lệ với `procedure_id` |
| `500` | Lỗi chuyển đổi doc → PDF (LibreOffice) |

---

### 4.5 GET /api/v1/forms/configs/{procedure_id}

Lấy cấu hình trường của tất cả tờ khai thuộc một thủ tục (dùng để render form ở frontend).

#### Path Parameters

| Tham số | Kiểu | Mô tả |
|---|---|---|
| `procedure_id` | `string` | Mã thủ tục (ví dụ: `TTHC-001`, `TTHC-CR-001`) |

#### Response — HTTP 200

```json
{
  "procedure_id": "TTHC-001",
  "forms": [
    {
      "form_file": "to_khai_thay_doi_tt_cu_tru.doc",
      "tab_label": "Tờ khai thay đổi TT cư trú",
      "fields": [
        {
          "field_name": "ho_ten",
          "field_type": "text",
          "label": "Họ và tên",
          "is_required": true,
          "source": "ocr_extraction"
        },
        {
          "field_name": "ngay_sinh",
          "field_type": "date",
          "label": "Ngày sinh",
          "is_required": true,
          "source": "ocr_extraction"
        },
        {
          "field_name": "gioi_tinh",
          "field_type": "radio",
          "label": "Giới tính",
          "is_required": true,
          "source": "ocr_extraction"
        }
      ]
    }
  ]
}
```

**Kiểu trường (`field_type`):**

| Giá trị | Mô tả |
|---|---|
| `text` | Trường văn bản thông thường |
| `date` | Ngày tháng (DD/MM/YYYY) |
| `checkbox` | Hộp kiểm |
| `radio` | Lựa chọn đơn |
| `signature` | Chữ ký |
| `year` | Năm (YYYY) |
| `email` | Địa chỉ email |
| `tel` | Số điện thoại |

**Nguồn dữ liệu (`source`):**

| Giá trị | Mô tả |
|---|---|
| `ocr_extraction` | Tự động điền từ OCR/QR CCCD |
| `user_input` | Người dùng phải nhập thủ công |
| `derived` | Tính toán từ dữ liệu khác |
| `carry_forward` | Lấy từ phiên trước |

#### HTTP Status Codes

| Code | Tình huống |
|---|---|
| `200` | Cấu hình trả về thành công |
| `404` | `procedure_id` không tồn tại |

---

### 4.6 POST /api/v1/forms/submit

Nộp form cư trú (thủ công hoặc qua AI) và nhận mã hồ sơ.

#### Request Body

```json
{
  "form_type": "thuong-tru",
  "session_id": "user-session-abc123",
  "submission_mode": "ai",
  "form_data": {
    "ho_ten": "NGUYỄN VĂN AN",
    "ngay_sinh": "15/05/1990",
    "gioi_tinh": "Nam",
    "so_cccd": "001090012345",
    "noi_thuong_tru_cu": "123 Đường Láng, Láng Thượng, Đống Đa, Hà Nội",
    "dia_chi_thuong_tru_moi": "456 Nguyễn Trãi, Phường 2, Quận 5, TP.HCM"
  }
}
```

| Trường | Kiểu | Bắt buộc | Giá trị hợp lệ |
|---|---|---|---|
| `form_type` | `string` | **Có** | `"thuong-tru"`, `"tam-tru"`, `"xac-nhan"` |
| `session_id` | `string` | **Có** | Mã phiên |
| `submission_mode` | `string` | Không | `"manual"` (mặc định), `"ai"` |
| `form_data` | `object` | **Có** | Dữ liệu form (xem bảng trường bên dưới) |

**Trường dữ liệu form (`form_data`):**

| Trường | Dùng cho | Mô tả |
|---|---|---|
| `ho_ten` | Tất cả | Họ và tên đầy đủ |
| `ngay_sinh` | Tất cả | Ngày sinh (DD/MM/YYYY) |
| `gioi_tinh` | Tất cả | `"Nam"` hoặc `"Nữ"` |
| `so_cccd` | Tất cả | Số CCCD |
| `noi_thuong_tru_cu` | Thường trú | Địa chỉ thường trú cũ |
| `dia_chi_thuong_tru_moi` | Thường trú | Địa chỉ thường trú mới |
| `quan_he_chu_ho` | Thường trú | Quan hệ với chủ hộ |
| `ten_chu_ho` | Thường trú | Họ tên chủ hộ |
| `cccd_chu_ho` | Thường trú | Số CCCD chủ hộ |
| `dia_chi_thuong_tru` | Tạm trú | Địa chỉ thường trú hiện tại |
| `dia_chi_tam_tru` | Tạm trú | Địa chỉ tạm trú đăng ký |
| `tu_ngay` | Tạm trú | Ngày bắt đầu tạm trú |
| `den_ngay` | Tạm trú | Ngày kết thúc tạm trú |
| `muc_dich` | Tạm trú | Mục đích tạm trú |
| `dia_chi_can_xac_nhan` | Xác nhận | Địa chỉ cần xác nhận |
| `loai_xac_nhan` | Xác nhận | `"Thường trú"` hoặc `"Tạm trú"` |
| `muc_dich_xac_nhan` | Xác nhận | Mục đích xác nhận |

#### Response — HTTP 200

```json
{
  "ma_ho_so": "DVC-20260511-K7FX3P",
  "form_type": "thuong-tru",
  "submitted_at": "2026-05-11T10:30:00Z",
  "status": "received",
  "message": "Hồ sơ đã được tiếp nhận thành công. Mã hồ sơ của bạn là DVC-20260511-K7FX3P."
}
```

#### HTTP Status Codes

| Code | Tình huống |
|---|---|
| `200` | Nộp thành công, trả về mã hồ sơ |
| `422` | Dữ liệu form trống hoặc không hợp lệ |
| `500` | Lỗi lưu vào cơ sở dữ liệu |

---

### 4.7 POST /api/v1/feedback

Ghi nhận đánh giá của người dùng về phản hồi của AI.

#### Request Body

```json
{
  "session_id": "user-session-abc123",
  "message_id": "msg-001",
  "feedback": "helpful",
  "timestamp": "2026-05-11T10:30:00Z"
}
```

| Trường | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `session_id` | `string` | **Có** | Mã phiên người dùng |
| `message_id` | `string` | **Có** | Mã tin nhắn được đánh giá |
| `feedback` | `string` | **Có** | `"helpful"` hoặc `"unhelpful"` |
| `timestamp` | `string` | **Có** | Thời gian đánh giá (ISO 8601) |

#### Response — HTTP 200

```json
{"status": "ok"}
```

Phản hồi luôn là `200` — lỗi ghi log được ghi cảnh báo nhưng không ảnh hưởng đến người dùng.

---

### 4.8 GET /health

Kiểm tra trạng thái sẵn sàng của hệ thống.

#### Response — HTTP 200 (sẵn sàng)

```json
{
  "status": "ready",
  "embedding_model": "loaded",
  "services": {
    "qdrant": true,
    "redis": true,
    "postgres": true
  },
  "gpu": {
    "cuda_available": false,
    "device_name": null,
    "vram_total_mb": null
  }
}
```

#### Response — HTTP 503 (đang khởi động)

```json
{
  "status": "warming_up",
  "embedding_model": "not_loaded"
}
```

**Lưu ý:** Chỉ trạng thái model embedding mới gây ra `503`. Các dịch vụ hạ tầng (Qdrant/Redis/PostgreSQL) thất bại chỉ làm `services.<name>: false` nhưng vẫn trả về `200`.

---

## 5. Schemas

### PersonalData

Dữ liệu cá nhân được trích xuất từ giấy tờ tùy thân.

```json
{
  "full_name": "NGUYỄN VĂN AN",
  "full_name_latin": "NGUYEN VAN AN",
  "date_of_birth": "1990-05-15",
  "gender": "Nam",
  "nationality": "Việt Nam",
  "id_number": "001090012345",
  "id_issue_date": "2021-03-20",
  "id_issue_place": "CỤC CẢNH SÁT QLHC VỀ TTXH",
  "permanent_address": {
    "street": "123 Đường Láng",
    "ward": "Phường Láng Thượng",
    "district": "Quận Đống Đa",
    "province": null,
    "city": "Hà Nội",
    "country": "Việt Nam"
  },
  "temporary_address": null,
  "raw_address": "123 Đường Láng, Phường Láng Thượng, Quận Đống Đa, Hà Nội",
  "source_document_type": "cccd",
  "source_image_path": "tmp/session-abc/uuid.jpg",
  "extraction_confidence": 1.0,
  "field_confidences": {
    "full_name": 1.0,
    "id_number": 1.0,
    "date_of_birth": 1.0,
    "gender": 1.0,
    "permanent_address": 1.0
  },
  "extracted_at": "2026-05-11T10:30:00Z"
}
```

Tất cả trường (trừ `nationality`, `source_document_type`, `source_image_path`, `extraction_confidence`, `extracted_at`) đều có thể là `null`.

### Citation

Trích dẫn văn bản pháp luật trong phản hồi AI.

```json
{
  "doc_id": "qdrant-point-uuid",
  "document_number": "68/2020/QH14",
  "article": "Điều 20",
  "excerpt": "Công dân được đăng ký thường trú tại chỗ ở hợp pháp do mình..."
}
```

### DocumentChunk

Đoạn văn bản pháp luật được lưu trong Qdrant.

```json
{
  "point_id": "uuid",
  "legal_document_id": "uuid",
  "document_number": "68/2020/QH14",
  "article_number": "20",
  "content": "Công dân được đăng ký thường trú tại chỗ ở hợp pháp...",
  "procedure_tags": ["TTHC-001", "TTHC-002"],
  "status": "active",
  "rrf_score": 0.021
}
```

### ProcedureStep

Một bước trong kế hoạch thực hiện thủ tục.

```json
{
  "procedure_id": "TTHC-001",
  "procedure_name": "Đăng ký thường trú",
  "status": "pending",
  "order": 1
}
```

`status` nhận một trong các giá trị: `"completed"`, `"pending"`, `"blocked"`.

### SessionData

Dữ liệu phiên lưu trữ trong Redis.

```json
{
  "session_id": "user-session-abc123",
  "personal_data": null,
  "completed_procedure_ids": [],
  "form_fill_state": {},
  "conversation_history": [],
  "filing_jurisdiction": null,
  "domain": null,
  "extracted_personal_data": null,
  "uploaded_document_path": null,
  "guided_procedure_id": null,
  "guided_step": null,
  "created_at": "2026-05-11T10:00:00Z",
  "updated_at": "2026-05-11T10:30:00Z"
}
```

**Lưu ý về phiên:**
- Lịch sử hội thoại (`conversation_history`) được giới hạn tối đa **6 lượt** (12 messages).
- Phiên hết hạn sau **3600 giây** không hoạt động.
- Dữ liệu được mã hóa Fernet trước khi lưu vào Redis.

---

## 6. Cấu hình CORS

Backend chấp nhận yêu cầu cross-origin từ các origin được cấu hình trong `.env`:

```bash
# Origin cơ bản (frontend local)
CORS_ALLOW_ORIGINS=http://localhost:3000

# Origin bổ sung (cách nhau bởi dấu phẩy)
CORS_EXTRA_ORIGINS=https://abc123.ngrok-free.app
```

Cấu hình CORS:

| Thuộc tính | Giá trị |
|---|---|
| `allow_credentials` | `true` |
| `allow_methods` | `*` (tất cả phương thức) |
| `allow_headers` | `*` (tất cả header) |
| `allow_origins` | Danh sách từ `CORS_ALLOW_ORIGINS` + `CORS_EXTRA_ORIGINS` |

> Wildcard `*` cho origins **không được phép** — luôn phải chỉ định domain cụ thể.
