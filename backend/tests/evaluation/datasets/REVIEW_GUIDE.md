# Hướng dẫn Xem xét Tập dữ liệu Benchmark

Tài liệu này hướng dẫn người xem xét (reviewer) cách kiểm tra và xác minh từng loại tập dữ liệu benchmark trước khi đưa vào đánh giá tự động.

---

## Phạm vi tài liệu

Bốn tập dữ liệu cần xem xét:

| Tệp | Loại | Số mục | Trạng thái |
|---|---|---|---|
| `tier1_router.json` | Tier 1 — Phân loại ý định | 60 | Tự nhãn (không cần xác minh pháp lý) |
| `tier1_scope.json` | Tier 1 — Chọn phạm vi tìm kiếm | 20 | Tự nhãn (không cần xác minh pháp lý) |
| `tier2_citations.json` | Tier 2 — Trích dẫn văn bản pháp luật | 30 | **Cần xác minh pháp lý** |
| `tier2_negative.json` | Tier 2 — Trường hợp ngoài phạm vi | 10 | Tự nhãn (hành vi hệ thống) |

---

## Phần 1 — `tier1_router.json` (60 mục)

### Mục đích
Kiểm tra độ chính xác phân loại ý định của `router_node`. Mỗi câu hỏi tiếng Việt được gán nhãn với `execution_plan` mong đợi và `domain` mong đợi.

### Các trường cần xem xét

| Trường | Kiểm tra |
|---|---|
| `input_message` | Câu hỏi phải tự nhiên, đúng ngữ pháp tiếng Việt |
| `expected.intent` | Ý định phải khớp với định nghĩa trong `router_prompt.py` |
| `expected_execution_plan` | Các bước hợp lệ: `rag_fn`, `ocr_fn`, `form_filler_fn` |
| `has_image` | `true` chỉ khi câu hỏi đề cập đến ảnh/CCCD/tải lên tài liệu |
| `session_context` | Bắt buộc có `guided_procedure_id` và `guided_step` cho `continue_guided` |

### Các ý định hợp lệ và execution_plan tương ứng

| Ý định | `execution_plan` | Ghi chú |
|---|---|---|
| `rag_only` | `["rag_fn"]` | Hỏi thông tin pháp lý thuần túy |
| `form_fill` | `["form_filler_fn"]` hoặc `["rag_fn", "form_filler_fn"]` | Đã có CCCD từ session |
| `form_fill_with_ocr` | `["ocr_fn", "form_filler_fn"]` | Cần quét CCCD trước |
| `start_guided` | `["rag_fn"]` | Bắt đầu quy trình mới |
| `draft_document` | `["rag_fn", "form_filler_fn"]` | Soạn đơn |
| `fallback` | `[]` | Ngoài phạm vi |
| `ocr_only` | `["ocr_fn"]` | Chỉ trích xuất thông tin từ ảnh |
| `continue_guided` | Phụ thuộc bước | Tiếp tục quy trình đang dở |
| `domain_clarification` | `["rag_fn"]` | Cần làm rõ |

### Phân phối mục theo ý định (kiểm tra đếm)

- `rag_only`: 20 mục (R-001 đến R-020)
- `form_fill_with_ocr`: 5 mục (R-021 đến R-025)
- `form_fill`: 5 mục (R-026 đến R-030)
- `start_guided`: 7 mục (R-031 đến R-037, một mục mỗi thủ tục)
- `draft_document`: 5 mục (R-038 đến R-042)
- `fallback`: 5 mục (R-043 đến R-047)
- `ocr_only`: 4 mục (R-048 đến R-051)
- `continue_guided`: 4 mục (R-052 đến R-055)
- `domain_clarification`: 5 mục (R-056 đến R-060)

### Quy trình xem xét
1. Đọc từng `input_message` và tự hỏi: "Ý định thực sự của người dùng là gì?"
2. So sánh với nhãn `expected.intent` đã gán.
3. Nếu không đồng ý, ghi chú trong cột `notes` và đề xuất nhãn thay thế.
4. Không cần kiến thức pháp lý — chỉ cần nhận biết ý định người dùng.

---

## Phần 2 — `tier1_scope.json` (20 mục)

### Mục đích
Kiểm tra logic cascade phạm vi tìm kiếm Qdrant. Mỗi mục xác nhận rằng khi không có chunks ở cấp ward hoặc city, hệ thống sẽ fallback đúng cấp.

### Các trường cần xem xét

| Trường | Kiểm tra |
|---|---|
| `filing_jurisdiction` | Mã phải có định dạng `VN`, `VN-HCM`, hoặc `VN-HCM-XXXXX` |
| `expected_scope_cascade` | Phải là chuỗi từ cụ thể đến tổng quát |
| `expected_primary_scope` | Phải là scope đầu tiên có chunks trong Qdrant |
| `expected_scope_notice` | `true` khi `filing_jurisdiction != "VN"` (vì chỉ VN có chunks) |

### Trạng thái hiện tại của Qdrant (thông tin quan trọng)

Tính đến phiên bản 3.32, **tất cả chunks đều ở cấp `VN`** (quốc gia):
- Housing: ~27 chunks (từ Docling ingestion)
- Civil registration: 30 chunks (từ YAML thủ công)
- Adoption: 16 chunks (từ YAML thủ công)

Do đó, `expected_primary_scope = "VN"` cho **tất cả 20 mục** là đúng. Khi chunks cấp ward/city được thêm vào trong tương lai, các mục này phải được cập nhật lại.

### Quy trình xem xét
1. Xác nhận `expected_scope_cascade` đúng thứ tự (cụ thể → tổng quát).
2. Xác nhận `expected_scope_notice = true` cho tất cả mục có `filing_jurisdiction != "VN"`.
3. Chạy `QdrantService.scroll_by_scope(procedure_id, scope)` để kiểm tra Qdrant thực tế nếu cần.

---

## Phần 3 — `tier2_citations.json` (30 mục) ⭐ Ưu tiên xem xét

### Mục đích
Kiểm tra độ chính xác trích dẫn văn bản pháp luật của pipeline RAG. Mỗi mục xác định câu hỏi, điều khoản mong đợi được trích dẫn, và nội dung trích dẫn.

### Trạng thái xác minh
- **Civil registration (C-001 đến C-010)**: Nội dung dựa trên manual_chunks YAML đã ingest. Cần đối chiếu với `backend/ingestion/manual_chunks/civil_registration.yaml`.
- **Adoption (C-011 đến C-020)**: Nội dung dựa trên manual_chunks YAML đã ingest. Cần đối chiếu với `backend/ingestion/manual_chunks/adoption.yaml`.
- **Housing (C-021 đến C-030)**: Tất cả `content_excerpt = "Chưa xác minh — xem Qdrant trực tiếp"`. Cần scroll Qdrant trực tiếp.

### Quy trình xem xét — Civil Registration và Adoption

1. **Mở tệp YAML tương ứng:**
   - `backend/ingestion/manual_chunks/civil_registration.yaml`
   - `backend/ingestion/manual_chunks/adoption.yaml`

2. **Với mỗi mục Tier 2**, tìm chunk trong YAML bằng `document_number` và `article_number`:
   ```yaml
   # Tìm kiếm trong YAML:
   document_number: "60/2014/QH13"
   article_number: 15
   ```

3. **So sánh `content_excerpt`** trong JSON với nội dung thực trong YAML.

4. **Nếu không khớp**, cập nhật `content_excerpt` trong JSON theo nội dung YAML thực tế và đổi `verified: true`.

5. **Nếu số điều/khoản sai**, sửa `article_number` và/hoặc `khoản` theo YAML thực tế.

6. **Nếu không tìm thấy điều khoản** trong YAML, ghi chú rằng chunk không được ingest và đánh dấu mục là `"chunk_not_ingested": true`.

### Quy trình xem xét — Housing

1. **Kết nối Qdrant** tại `http://localhost:6333`.

2. **Scroll chunks theo procedure_id:**
   ```python
   from app.services.qdrant_service import QdrantService
   svc = QdrantService(...)
   chunks = await svc.scroll_by_procedure("TTHC-001")
   ```

3. **Tìm chunk liên quan** đến câu hỏi trong từng mục C-021 đến C-030.

4. **Cập nhật `content_excerpt`** với đoạn văn thực tế từ Qdrant payload.

5. **Xác nhận `document_number` và `article_number`** từ chunk payload.

6. **Đổi `verified: true`** khi đã xác nhận.

### Tiêu chí đánh giá recall trong run_benchmark.py

Benchmark đo `citation_recall@k`: tỷ lệ `expected_articles` xuất hiện trong top-k chunks được truy xuất. Để đo lường chính xác, `document_number` và `article_number` trong `expected_articles` phải khớp **chính xác** với payload Qdrant:

```json
// Payload Qdrant cần có:
{
  "document_number": "60/2014/QH13",
  "article_number": 15
}
```

Không khớp case-sensitive hoặc dấu gạch ngang sẽ gây miss trong benchmark.

---

## Phần 4 — `tier2_negative.json` (10 mục)

### Mục đích
Kiểm tra khả năng router từ chối hoặc giải thích phạm vi hỗ trợ cho các câu hỏi ngoài phạm vi.

### Các trường cần xem xét

| Trường | Kiểm tra |
|---|---|
| `is_out_of_scope` | Phải là `true` cho tất cả 10 mục |
| `expected_behavior` | `"reject"` hoặc `"clarify"` |
| `category` | Phân loại lý do: `wrong_procedure_type`, `wrong_province`, `adversarial_injection`, `adversarial_probe`, `off_topic` |

### Các trường hợp trong tập dữ liệu

| ID | Câu hỏi tóm tắt | Lý do ngoài phạm vi |
|---|---|---|
| N-001 | Đăng ký biển số xe | Sai loại thủ tục |
| N-002 | Cấp hộ chiếu | Sai loại thủ tục |
| N-003 | Thành lập công ty | Sai loại thủ tục |
| N-004 | Khai thuế | Sai loại thủ tục |
| N-005 | Kháng cáo hình sự | Sai loại thủ tục |
| N-006 | Đăng ký thường trú ở Hà Nội | Sai tỉnh/thành phố |
| N-007 | Prompt injection | Tấn công bảo mật |
| N-008 | Yêu cầu tiết lộ system prompt | Tấn công thăm dò |
| N-009 | Nấu phở | Hoàn toàn ngoài chủ đề |
| N-010 | Thủ tục ly hôn | Sai loại thủ tục (tòa án) |

### Quy trình xem xét
1. Xác nhận từng câu hỏi thực sự nằm ngoài phạm vi hỗ trợ của hệ thống.
2. Kiểm tra xem câu hỏi có thể bị nhầm là hợp lệ bởi hệ thống không (ví dụ: N-006 có từ "thường trú" nhưng ở Hà Nội).
3. Đảm bảo N-007 và N-008 đủ "adversarial" để kiểm tra bảo vệ prompt injection.
4. Không cần kiến thức pháp lý.

---

## Quy trình xem xét tổng thể

### Bước 1 — Xem xét nhanh Tier 1 (1–2 giờ)
- Đọc nhanh `tier1_router.json`: kiểm tra phân phối ý định và tính tự nhiên của câu hỏi.
- Đọc nhanh `tier1_scope.json`: xác nhận logic cascade và `expected_scope_notice`.
- Đánh dấu bất kỳ mục nào có vẻ sai trong cột `notes`.

### Bước 2 — Xem xét chi tiết Tier 2 (4–6 giờ)
- Ưu tiên xem xét civil_registration (C-001 đến C-010) và adoption (C-011 đến C-020) trước vì có YAML tham chiếu.
- Housing (C-021 đến C-030) yêu cầu Qdrant đang chạy — để sau.
- Sau khi xác minh, đổi `verified: true` trong JSON.

### Bước 3 — Cập nhật `benchmark_config.json`
- Sau khi xác minh đủ mục để chạy benchmark, cập nhật `tier2_review_status` trong `benchmark_config.json`.

### Bước 4 — Chạy benchmark lần đầu
```bash
cd backend
PYTHONPATH=. python tests/evaluation/run_benchmark.py
```

---

## Định dạng trích dẫn chuẩn

Tất cả response RAG phải dùng định dạng nội tuyến:

| Loại văn bản | Định dạng |
|---|---|
| Nghị định | `[Điều X, Nghị định YYY/YYYY/NĐ-CP]` |
| Luật | `[Điều X, Luật YYY năm YYYY]` |
| Thông tư | `[Điều X, Thông tư YYY/YYYY/TT-BCA]` |
| Có khoản cụ thể | `[Điều X Khoản Y, Tên văn bản]` |

Ví dụ: `[Điều 15 Khoản 1, Luật Hộ tịch 60/2014/QH13]`

---

## Liên hệ

Câu hỏi về tập dữ liệu: xem `docs/PROJECT_STATUS.md` (TASK-18) hoặc `docs/PROJECT_CONTEXT.md` (Phần 3 — Pipeline RAG).
