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
    """

    execution_plan: list[str]
    entities: dict[str, Any] = {}


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
  "entities": {{}}
}}

Trường "entities" chứa các thực thể được trích xuất (tên thủ tục, điều luật, v.v.) — để trống nếu không tìm thấy.

## Ví dụ

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
{{"execution_plan": [], "entities": {{}}}}"""

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
