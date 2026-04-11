"""Synthesis prompt — handles all six synthesizer response modes.

This module is pure Python with zero infrastructure dependencies.
It exposes two public names:
  - build_synthesis_prompt(mode, context) -> str
  - _scope_level_name(scope_code) -> str   (internal; also imported by synthesizer.py)

Six modes (evaluated in priority order by synthesizer_node):
  1. error              — state["errors"] is non-empty
  2. circuit_breaker    — plan stalled, no errors
  3. form_fill_complete — all required fields filled, PDF promoted
  4. form_fill_partial  — some required fields missing
  5. rag_only           — retrieved_chunks non-empty, no form fill
  6. fallback           — none of the above (greeting / unclassifiable)

Usage in synthesizer_node:
    prompt = build_synthesis_prompt(mode, context)
    response = await llm.async_invoke(system=prompt, messages=[...])
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Shared base rules injected into every prompt
# ---------------------------------------------------------------------------

_BASE_RULES = """Bạn là trợ lý hành chính của cổng dịch vụ công Việt Nam.

## Quy tắc bắt buộc
1. Trả lời HOÀN TOÀN bằng tiếng Việt.
2. KHÔNG tiết lộ thông tin nội bộ hệ thống: đường dẫn file, chunk ID, điểm số,
   stack trace Python, tên biến, hoặc bất kỳ chi tiết kỹ thuật nào.
3. KHÔNG bịa đặt thông tin pháp lý không có trong ngữ cảnh được cung cấp.
4. Giữ giọng điệu lịch sự, chuyên nghiệp và thân thiện."""


# ---------------------------------------------------------------------------
# Scope level name mapping
# ---------------------------------------------------------------------------

def _scope_level_name(scope_code: str) -> str:
    """Map a scope code to its Vietnamese administrative level name.

    Uses the number of hyphen-separated parts:
        "VN"           (1 part) → "cấp quốc gia"
        "VN-HCM"       (2 parts) → "cấp thành phố"
        "VN-HCM-26968" (3 parts) → "cấp phường"

    Args:
        scope_code: A hyphen-separated geographic scope code.

    Returns:
        Vietnamese level name string.
    """
    parts = scope_code.split("-")
    n = len(parts)
    if n == 1:
        return "cấp quốc gia"
    elif n == 2:
        return "cấp thành phố"
    else:
        return "cấp phường"


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------

def build_synthesis_prompt(mode: str, context: dict) -> str:
    """Build the system prompt for the given response mode.

    Args:
        mode:    One of the six mode strings.
        context: Mode-specific context dict assembled by synthesizer_node.
                 Keys vary by mode — see synthesizer_node._build_context().

    Returns:
        Complete system prompt string to pass to LLMService.async_invoke().
    """
    if mode == "error":
        return _error_prompt(context)
    elif mode == "circuit_breaker":
        return _circuit_breaker_prompt(context)
    elif mode == "form_fill_complete":
        return _form_fill_complete_prompt(context)
    elif mode == "form_fill_partial":
        return _form_fill_partial_prompt(context)
    elif mode == "rag_only":
        return _rag_only_prompt(context)
    elif mode == "fallback":
        return _fallback_prompt(context)
    else:
        # Unknown mode — safe catch-all
        return f"""{_BASE_RULES}

Hãy trả lời lịch sự bằng tiếng Việt và đề nghị người dùng thử lại."""


# ---------------------------------------------------------------------------
# Per-mode prompt builders
# ---------------------------------------------------------------------------

def _error_prompt(context: dict) -> str:
    errors = context.get("errors") or ["Lỗi không xác định"]
    errors_text = "\n".join(f"- {e}" for e in errors)
    return f"""{_BASE_RULES}

## Nhiệm vụ: Xử lý lỗi
Hệ thống gặp sự cố khi xử lý yêu cầu. Thông tin lỗi nội bộ (chỉ dùng để tạo thông báo):

<internal_errors>
{errors_text}
</internal_errors>

Hãy:
- Tạo một thông báo lỗi lịch sự, thân thiện bằng tiếng Việt.
- Tóm tắt vấn đề bằng ngôn ngữ đơn giản — KHÔNG sao chép nguyên văn chuỗi lỗi kỹ thuật.
- Đề xuất người dùng thử lại sau hoặc liên hệ hỗ trợ nếu vấn đề tiếp tục.
- KHÔNG đề cập đến tên biến Python, stack trace, đường dẫn file, hoặc chi tiết kỹ thuật nào."""


def _circuit_breaker_prompt(context: dict) -> str:
    return f"""{_BASE_RULES}

## Nhiệm vụ: Xử lý lỗi hệ thống
Hệ thống đã vượt quá giới hạn bước xử lý cho yêu cầu này mà không hoàn thành được.

Hãy:
- Tạo một thông báo lịch sự bằng tiếng Việt, xin lỗi vì không thể hoàn thành yêu cầu.
- Đề xuất người dùng thử lại với câu hỏi đơn giản hơn hoặc liên hệ hỗ trợ.
- KHÔNG đề cập đến giới hạn kỹ thuật nội bộ, số bước, hoặc kiến trúc hệ thống."""


def _form_fill_complete_prompt(context: dict) -> str:
    procedure_name = context.get("procedure_name", "thủ tục đăng ký cư trú")
    scope_section = _scope_notice_section(context)
    return f"""{_BASE_RULES}

## Nhiệm vụ: Thông báo điền biểu mẫu thành công
Thủ tục: {procedure_name}
{scope_section}
Hãy:
- Thông báo cho người dùng rằng biểu mẫu đã được điền thành công và sẵn sàng để nộp.
- Đề cập tên thủ tục nếu có.
- KHÔNG tiết lộ đường dẫn MinIO, đường dẫn file nội bộ, hoặc bất kỳ đường dẫn kỹ thuật nào.
- Hướng dẫn bước tiếp theo (ví dụ: kiểm tra lại biểu mẫu và tiến hành nộp)."""


def _form_fill_partial_prompt(context: dict) -> str:
    missing = context.get("unfilled_required_fields") or []
    missing_list = "\n".join(f"- {field}" for field in missing)
    scope_section = _scope_notice_section(context)
    return f"""{_BASE_RULES}

## Nhiệm vụ: Yêu cầu thông tin còn thiếu
{scope_section}
Các trường bắt buộc chưa được điền:

<missing_fields>
{missing_list if missing_list else "- (danh sách trống)"}
</missing_fields>

Hãy:
- Liệt kê RÕ RÀNG từng trường còn thiếu và yêu cầu người dùng cung cấp thông tin.
- Dịch tên trường sang tiếng Việt thông thường nếu cần (ví dụ: "cmnd" → "Số CCCD/CMND").
- Chỉ đề cập các trường CÒN THIẾU — không nhắc các trường đã điền xong.
- Giữ thông điệp ngắn gọn và rõ ràng."""


def _rag_only_prompt(context: dict) -> str:
    """RAG-only mode — used only when scope notice must be woven in.

    When include_scope_notice is False, synthesizer_node skips the LLM call
    entirely and returns state["final_response"] directly. This function is
    only called when a scope notice must be prepended naturally.
    """
    rag_response = context.get("final_response", "")
    scope_used_level = context.get("scope_used_level", "cấp quốc gia")
    filing_jurisdiction_level = context.get("filing_jurisdiction_level", "")

    scope_notice_instruction = ""
    if context.get("include_scope_notice") and filing_jurisdiction_level:
        scope_notice_instruction = f"""
Đầu tiên, hãy thêm thông báo phạm vi sau vào đầu câu trả lời một cách tự nhiên
(không như thông báo hệ thống):
"Đang áp dụng quy định {scope_used_level} vì chưa tìm thấy quy định {filing_jurisdiction_level}."

"""

    return f"""{_BASE_RULES}

## Nhiệm vụ: Trả lời câu hỏi pháp lý
{scope_notice_instruction}Sau đây là câu trả lời pháp lý đã được tạo ra từ các văn bản được truy xuất.
Hãy trình bày lại nội dung này, giữ nguyên tất cả các trích dẫn pháp lý theo đúng định dạng:

<rag_response>
{rag_response}
</rag_response>

Quy tắc bổ sung:
- Giữ nguyên định dạng trích dẫn: [Điều X, Nghị định YYY/YYYY/NĐ-CP]
- KHÔNG thêm thông tin pháp lý mới không có trong nội dung trên.
- KHÔNG tiết lộ điểm số, chunk ID, hoặc bất kỳ thông tin kỹ thuật nào."""


def _fallback_prompt(context: dict) -> str:
    user_message = context.get("user_message", "")
    user_section = f'\nNgười dùng đã nhắn: "{user_message}"\n' if user_message else ""
    return f"""{_BASE_RULES}

## Nhiệm vụ: Hướng dẫn người dùng
{user_section}
Hệ thống này hỗ trợ ba thủ tục đăng ký và xác nhận cư trú tại Việt Nam:
1. Đăng ký thường trú (TTHC-001) — đăng ký hộ khẩu thường trú
2. Đăng ký tạm trú (TTHC-002) — đăng ký nơi tạm trú
3. Xác nhận thông tin cư trú (TTHC-003) — xin xác nhận thông tin cư trú

Hãy:
- Chào hỏi người dùng lịch sự.
- Giới thiệu ngắn gọn ba thủ tục trên.
- Hỏi người dùng muốn được hỗ trợ thủ tục nào hoặc có câu hỏi gì về các thủ tục này.
- Giữ thông điệp ngắn gọn, thân thiện (không quá 150 từ)."""


# ---------------------------------------------------------------------------
# Scope notice helper
# ---------------------------------------------------------------------------

def _scope_notice_section(context: dict) -> str:
    """Return a formatted scope notice paragraph, or empty string if not applicable."""
    if not context.get("include_scope_notice"):
        return ""
    scope_used_level = context.get("scope_used_level", "")
    filing_jurisdiction_level = context.get("filing_jurisdiction_level", "")
    if not scope_used_level or not filing_jurisdiction_level:
        return ""
    return (
        f"\nLưu ý phạm vi áp dụng: đang sử dụng quy định {scope_used_level} "
        f"vì chưa tìm thấy quy định {filing_jurisdiction_level}.\n"
    )
