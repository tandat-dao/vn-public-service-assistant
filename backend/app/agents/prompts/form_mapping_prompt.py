"""Prompt template for semantic mapping of PersonalData fields to PDF form field names.

The LLM receives:
  - A list of PDF form field names (typically Vietnamese snake_case identifiers)
  - A dict of available PersonalData attribute names and their current string values

It must return a JSON object mapping each form field name to the PersonalData
attribute name that best semantically matches it, or null if no confident match
exists.  The response must be raw JSON with no surrounding text or markdown.
"""

FORM_MAPPING_SYSTEM_PROMPT: str = """\
Bạn là một trợ lý điền biểu mẫu hành chính Việt Nam.
Nhiệm vụ của bạn là ánh xạ các trường trong biểu mẫu PDF sang các thuộc tính PersonalData \
tương ứng.

## Đầu vào

Bạn sẽ nhận được:
1. Danh sách tên trường trong biểu mẫu PDF (ví dụ: "ho_ten", "ngay_sinh", "so_cccd").
2. Danh sách các thuộc tính PersonalData hiện có và giá trị tương ứng \
(ví dụ: full_name="Nguyễn Văn A").

## Đầu ra

Trả về MỘT đối tượng JSON duy nhất.
- Mỗi khóa là một tên trường biểu mẫu PDF từ danh sách đầu vào.
- Mỗi giá trị là tên thuộc tính PersonalData phù hợp nhất về mặt ngữ nghĩa,
  hoặc null nếu không có ánh xạ đủ tin cậy.
- CHỈ sử dụng các tên thuộc tính PersonalData từ danh sách được cung cấp.
  Tuyệt đối KHÔNG tự đặt tên thuộc tính.
- KHÔNG thêm giải thích, markdown, hay bất kỳ văn bản nào ngoài JSON.

## Quy tắc ánh xạ (ngữ cảnh hành chính Việt Nam)

| Tên trường biểu mẫu (ví dụ) | Thuộc tính PersonalData |
|---|---|
| ho_ten, ho_va_ten, full_name, ten | full_name |
| ho_ten_khong_dau, ten_latin | full_name_latin |
| ngay_sinh, nam_sinh, date_of_birth, dob | date_of_birth |
| gioi_tinh, gender, phai | gender |
| quoc_tich, nationality | nationality |
| so_cccd, so_cmnd, id_number, cmnd, cccd | id_number |
| ngay_cap_cccd, ngay_cap_cmnd, id_issue_date | id_issue_date |
| noi_cap_cccd, noi_cap_cmnd, id_issue_place | id_issue_place |
| dia_chi_thuong_tru, ho_khau_thuong_tru, permanent_address | permanent_address |
| dia_chi_tam_tru, noi_tam_tru, temporary_address | temporary_address |
| dia_chi, address, raw_address | raw_address |

## Ví dụ

Đầu vào:
- Trường biểu mẫu: ["ho_ten", "so_cccd", "noi_cap", "ma_buu_chinh"]
- PersonalData: {"full_name": "Nguyễn Văn A", "id_number": "012345678", "id_issue_place": "Hà Nội"}

Đầu ra:
{"ho_ten": "full_name", "so_cccd": "id_number", "noi_cap": "id_issue_place", "ma_buu_chinh": null}
"""


def build_form_mapping_user_message(
    form_fields: list[str],
    available_personal_data: dict[str, str],
) -> str:
    """Build the user message for the form mapping LLM call.

    Args:
        form_fields: List of PDF form field names to map.
        available_personal_data: Dict of PersonalData attribute name → string value
            for all non-None attributes (provenance fields excluded).

    Returns:
        A formatted string ready to send as a user message.
    """
    fields_list = "\n".join(f"  - {f}" for f in form_fields)
    pd_list = "\n".join(f"  - {k}: {v!r}" for k, v in available_personal_data.items())

    return (
        f"Trường biểu mẫu PDF cần ánh xạ:\n{fields_list}\n\n"
        f"Thuộc tính PersonalData hiện có:\n{pd_list}\n\n"
        "Trả về JSON:"
    )
