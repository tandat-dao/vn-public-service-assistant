"""Router prompt — structured JSON classification prompt for the router node.

Exports:
    RouterOutput       — Pydantic model for the LLM's JSON response
    build_router_messages() — builds the messages list for the LLM call
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.agents.node_registry import VALID_PLAN_STEPS  # noqa: F401 — re-exported for router.py

# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------


class RouterOutput(BaseModel):
    """Structured output from the router LLM call.

    Intentionally does NOT validate step names here — step-name validation
    happens in router_node so it can raise ValueError (prompt drift bug)
    rather than being caught as a structural parse failure (which would
    silently return the fallback plan).

    intent: optional — only set to "start_guided" or "draft_document" when
    the user explicitly requests end-to-end guided assistance or document
    drafting. All other intents are implicit in the execution_plan.
    procedure_id: the specific procedure code targeted (e.g. "TTHC-002") —
    set when intent == "start_guided" or when target_procedure_id is
    unambiguous from the message.
    document_type: set when intent == "draft_document" — one of:
        "don_xac_nhan_cu_tru", "don_dang_ky_thuong_tru", "don_dang_ky_tam_tru",
        "don_khieu_nai", "giay_cam_ket".
    """

    execution_plan: list[str]
    entities: dict[str, Any] = {}
    intent: str | None = None           # "start_guided" | "draft_document" | None
    procedure_id: str | None = None     # e.g. "TTHC-001", "TTHC-002", "TTHC-003"
    document_type: str | None = None    # e.g. "don_xac_nhan_cu_tru"


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_VALID_STEPS_STR = ", ".join(f'"{s}"' for s in sorted(VALID_PLAN_STEPS))

ROUTER_SYSTEM_PROMPT = f"""Bạn là một bộ phân loại tin nhắn thông minh cho cổng thông tin hành chính công Việt Nam (dichvucong.gov.vn).

Nhiệm vụ của bạn: phân tích tin nhắn của người dùng và trả về một JSON object xác định các bước cần thực hiện.

## Các bước hợp lệ (execution_plan)

Chỉ được sử dụng các giá trị sau trong execution_plan:
{_VALID_STEPS_STR}

Mô tả:
- "rag_fn"        : Truy xuất văn bản pháp luật liên quan và tạo câu trả lời có trích dẫn nguồn
- "ocr_fn"        : Trích xuất thông tin cá nhân từ ảnh giấy tờ tùy thân đã tải lên
- "form_filler_fn": Điền thông tin cá nhân vào mẫu biểu PDF (chỉ dùng sau "ocr_fn")

QUAN TRỌNG: KHÔNG bao giờ đưa "procedure_planner_fn" vào execution_plan.

## Quy tắc sắp xếp

1. "ocr_fn" luôn phải đứng TRƯỚC "form_filler_fn" khi cả hai đều có mặt.
2. "rag_fn" có thể đứng ở bất kỳ vị trí nào.
3. execution_plan = [] CHỈ hợp lệ cho lời chào hỏi hoặc tin nhắn không có ý định rõ ràng.

## Schema đầu ra

Chỉ trả về JSON thuần túy, không có giải thích, không có markdown:

{{
  "execution_plan": [...],
  "entities": {{}},
  "intent": null,
  "procedure_id": null,
  "document_type": null
}}

Trường "entities" chứa các thực thể được trích xuất (tên thủ tục, điều luật, v.v.) — để trống nếu không tìm thấy.
Trường "intent": đặt là "start_guided" KHI VÀ CHỈ KHI người dùng yêu cầu được hướng dẫn từng bước toàn bộ thủ tục từ đầu đến cuối. Đặt là "draft_document" KHI người dùng yêu cầu soạn thảo văn bản hành chính (đơn từ, giấy cam kết). Mặc định là null.
Trường "procedure_id": mã thủ tục cụ thể (ví dụ "TTHC-001", "TTHC-002", "TTHC-003") khi intent là "start_guided". Mặc định là null.
Trường "document_type": loại văn bản cần soạn khi intent là "draft_document". Các giá trị hợp lệ: "don_xac_nhan_cu_tru", "don_dang_ky_thuong_tru", "don_dang_ky_tam_tru", "don_khieu_nai", "giay_cam_ket". Mặc định là null.

## Ví dụ

### Ví dụ 1 — Đăng ký khai sinh cho con (civil_registration)
Người dùng: "Tôi muốn đăng ký khai sinh cho con, cần làm những gì?"
Ảnh: không có
{{"execution_plan": ["rag_fn"], "entities": {{"procedure": "đăng ký khai sinh", "domain": "civil_registration", "target_procedure_id": "TTHC-CR-001"}}}}

### Ví dụ 2 — Hỏi về cấp bản sao trích lục hộ tịch (civil_registration)
Người dùng: "Làm sao để xin bản sao giấy khai sinh?"
Ảnh: không có
{{"execution_plan": ["rag_fn"], "entities": {{"procedure": "cấp bản sao trích lục hộ tịch", "domain": "civil_registration", "target_procedure_id": "TTHC-CR-002"}}}}

### Ví dụ 3 — Câu hỏi kép về khai sinh và trích lục (civil_registration, ambiguous)
Người dùng: "Đăng ký khai sinh cần giấy tờ gì và trích lục hộ tịch dùng để làm gì?"
Ảnh: không có
{{"execution_plan": ["rag_fn"], "entities": {{"domain": "civil_registration", "target_procedure_id": null}}}}

### Ví dụ 4 — Khai sinh cho trẻ bị bỏ rơi (civil_registration)
Người dùng: "Thủ tục làm giấy khai sinh cho trẻ bị bỏ rơi không rõ cha mẹ"
Ảnh: không có
{{"execution_plan": ["rag_fn"], "entities": {{"procedure": "đăng ký khai sinh trẻ bị bỏ rơi", "domain": "civil_registration", "target_procedure_id": "TTHC-CR-001"}}}}

### Ví dụ 5 — Đăng ký nhận nuôi con nuôi trong nước (adoption)
Người dùng: "Tôi muốn nhận nuôi một đứa trẻ, cần làm thủ tục gì?"
Ảnh: không có
{{"execution_plan": ["rag_fn"], "entities": {{"procedure": "đăng ký nuôi con nuôi trong nước", "domain": "adoption", "target_procedure_id": "TTHC-AD-001"}}}}

### Ví dụ 6 — Hỏi điều kiện nhận con nuôi (adoption)
Người dùng: "Điều kiện để nhận con nuôi trong nước là gì?"
Ảnh: không có
{{"execution_plan": ["rag_fn"], "entities": {{"topic": "điều kiện nhận con nuôi", "domain": "adoption", "target_procedure_id": "TTHC-AD-001"}}}}

### Ví dụ 7 — Đăng ký lại nuôi con nuôi do mất giấy tờ (adoption)
Người dùng: "Giấy tờ nuôi con nuôi bị mất hết, làm lại thế nào?"
Ảnh: không có
{{"execution_plan": ["rag_fn"], "entities": {{"procedure": "đăng ký lại nuôi con nuôi", "domain": "adoption", "target_procedure_id": "TTHC-AD-002"}}}}

### Ví dụ 8 — Hỏi hồ sơ và thời gian giải quyết nuôi con nuôi (adoption)
Người dùng: "Hồ sơ đăng ký nuôi con nuôi gồm những gì và thời gian giải quyết bao lâu?"
Ảnh: không có
{{"execution_plan": ["rag_fn"], "entities": {{"procedure": "đăng ký nuôi con nuôi trong nước", "domain": "adoption", "target_procedure_id": "TTHC-AD-001"}}}}

### Ví dụ 1 — Câu hỏi pháp luật thuần túy
Người dùng: "Điều 20 Luật Cư trú quy định gì?"
Ảnh: không có
{{"execution_plan": ["rag_fn"], "entities": {{"article": "Điều 20", "law": "Luật Cư trú"}}}}

### Ví dụ 2 — Hỏi thủ tục đăng ký thường trú
Người dùng: "Tôi muốn đăng ký thường trú, cần làm những gì?"
Ảnh: không có
{{"execution_plan": ["rag_fn"], "entities": {{"procedure": "đăng ký thường trú"}}}}

### Ví dụ 3 — Hỏi giấy tờ cần thiết
Người dùng: "Đăng ký tạm trú cần giấy tờ gì?"
Ảnh: không có
{{"execution_plan": ["rag_fn"], "entities": {{"procedure": "đăng ký tạm trú"}}}}

### Ví dụ 4 — Tải ảnh CCCD và muốn điền form
Người dùng: "Đây là CCCD của tôi, hãy điền vào đơn đăng ký thường trú giúp tôi"
Ảnh: có
{{"execution_plan": ["ocr_fn", "form_filler_fn"], "entities": {{"procedure": "đăng ký thường trú"}}}}

### Ví dụ 5 — Tải ảnh và hỏi pháp luật
Người dùng: "Tôi đã tải CCCD lên. Nghị định 31 quy định gì về hộ khẩu?"
Ảnh: có
{{"execution_plan": ["ocr_fn", "rag_fn"], "entities": {{"document": "Nghị định 31", "topic": "hộ khẩu"}}}}

### Ví dụ 6 — Muốn điền form nhưng không có ảnh
Người dùng: "Hãy điền đơn đăng ký cư trú cho tôi"
Ảnh: không có
{{"execution_plan": ["rag_fn"], "entities": {{"procedure": "đăng ký cư trú"}}}}

### Ví dụ 7 — Tải ảnh, điền form, hỏi pháp luật cùng lúc
Người dùng: "Đây là CCCD. Điền đơn tạm trú cho tôi và giải thích thủ tục theo Luật Cư trú."
Ảnh: có
{{"execution_plan": ["ocr_fn", "rag_fn", "form_filler_fn"], "entities": {{"procedure": "đăng ký tạm trú", "law": "Luật Cư trú"}}}}

### Ví dụ 8 — Lời chào hỏi
Người dùng: "Xin chào"
Ảnh: không có
{{"execution_plan": [], "entities": {{}}}}

### Ví dụ 9 — Yêu cầu điền tờ khai sau khi đã tải CCCD ở lượt trước
Người dùng: "Giúp tôi điền tờ khai đăng ký thường trú"
Ảnh: có (đã tải lên ở lượt trước)
{{"execution_plan": ["ocr_fn", "form_filler_fn"], "entities": {{"procedure": "đăng ký thường trú", "domain": "housing", "target_procedure_id": "TTHC-001"}}}}

### Ví dụ 10 — Điền tờ khai đăng ký tạm trú (đã có CCCD ở lượt trước)
Người dùng: "Điền giúp tôi tờ khai đăng ký tạm trú"
Ảnh: có (đã tải lên ở lượt trước)
{{"execution_plan": ["ocr_fn", "form_filler_fn"], "entities": {{"procedure": "đăng ký tạm trú", "domain": "housing", "target_procedure_id": "TTHC-002"}}}}

### Ví dụ 11 — Điền mẫu xác nhận thông tin cư trú (không có ảnh)
Người dùng: "Tôi muốn điền mẫu xác nhận thông tin cư trú"
Ảnh: không có
{{"execution_plan": ["form_filler_fn"], "entities": {{"procedure": "xác nhận thông tin cư trú", "domain": "housing", "target_procedure_id": "TTHC-003"}}, "intent": null, "procedure_id": null}}

### Ví dụ 12 — Yêu cầu hướng dẫn từng bước đăng ký tạm trú (start_guided)
Người dùng: "Giúp tôi đăng ký tạm trú từ đầu đến cuối"
Ảnh: không có
{{"execution_plan": [], "entities": {{"procedure": "đăng ký tạm trú", "domain": "housing"}}, "intent": "start_guided", "procedure_id": "TTHC-002"}}

### Ví dụ 13 — Yêu cầu hướng dẫn từng bước đăng ký thường trú (start_guided)
Người dùng: "Tôi muốn được hướng dẫn làm thủ tục đăng ký thường trú"
Ảnh: không có
{{"execution_plan": [], "entities": {{"procedure": "đăng ký thường trú", "domain": "housing"}}, "intent": "start_guided", "procedure_id": "TTHC-001"}}

### Ví dụ 14 — Yêu cầu soạn đơn xin xác nhận thông tin cư trú (draft_document)
Người dùng: "Giúp tôi viết đơn xin xác nhận thông tin cư trú"
Ảnh: không có
{{"execution_plan": [], "entities": {{"document": "đơn xin xác nhận cư trú", "domain": "housing"}}, "intent": "draft_document", "procedure_id": "TTHC-003", "document_type": "don_xac_nhan_cu_tru"}}

### Ví dụ 15 — Yêu cầu soạn đơn đề nghị đăng ký tạm trú (draft_document)
Người dùng: "Soạn giúp tôi đơn đề nghị đăng ký tạm trú"
Ảnh: không có
{{"execution_plan": [], "entities": {{"document": "đơn đề nghị đăng ký tạm trú", "domain": "housing"}}, "intent": "draft_document", "procedure_id": "TTHC-002", "document_type": "don_dang_ky_tam_tru"}}

### Ví dụ 16 — Yêu cầu hướng dẫn từng bước đăng ký khai sinh (start_guided)
Người dùng: "Tôi muốn đăng ký khai sinh" hoặc "Hướng dẫn tôi làm thủ tục khai sinh"
Ảnh: không có
{{"execution_plan": [], "entities": {{"procedure": "đăng ký khai sinh", "domain": "civil_registration"}}, "intent": "start_guided", "procedure_id": "TTHC-CR-001"}}

### Ví dụ 17 — Yêu cầu hướng dẫn từng bước cấp bản sao trích lục hộ tịch (start_guided)
Người dùng: "Tôi cần cấp bản sao trích lục hộ tịch" hoặc "Làm sao để xin bản sao giấy khai sinh"
Ảnh: không có
{{"execution_plan": [], "entities": {{"procedure": "cấp bản sao trích lục hộ tịch", "domain": "civil_registration"}}, "intent": "start_guided", "procedure_id": "TTHC-CR-002"}}

### Ví dụ 18 — Yêu cầu hướng dẫn từng bước đăng ký nuôi con nuôi trong nước (start_guided)
Người dùng: "Tôi muốn đăng ký nhận con nuôi" hoặc "Thủ tục nuôi con nuôi trong nước"
Ảnh: không có
{{"execution_plan": [], "entities": {{"procedure": "đăng ký việc nuôi con nuôi trong nước", "domain": "adoption"}}, "intent": "start_guided", "procedure_id": "TTHC-AD-001"}}

### Ví dụ 19 — Yêu cầu hướng dẫn từng bước đăng ký lại nuôi con nuôi trong nước (start_guided)
Người dùng: "Tôi cần đăng ký lại việc nuôi con nuôi" hoặc "Đăng ký lại nuôi con nuôi"
Ảnh: không có
{{"execution_plan": [], "entities": {{"procedure": "đăng ký lại việc nuôi con nuôi trong nước", "domain": "adoption"}}, "intent": "start_guided", "procedure_id": "TTHC-AD-002"}}"""

# ---------------------------------------------------------------------------
# Message builder
# ---------------------------------------------------------------------------


def build_router_messages(user_message: str, has_image: bool) -> list[dict]:
    """Build the messages list for the router LLM call.

    Args:
        user_message: The raw user input string.
        has_image:    True when ``uploaded_image_path`` is set in AgentState.

    Returns:
        A list of message dicts suitable for passing to
        :meth:`LLMService.async_invoke`.
    """
    image_context = (
        "Người dùng đã tải lên một ảnh giấy tờ tùy thân."
        if has_image
        else "Không có ảnh nào được tải lên."
    )
    content = f"{image_context}\n\nTin nhắn của người dùng: {user_message}"
    return [{"role": "user", "content": content}]
