"""Prompt for classifying an uploaded identity document image into one of 5 types.

This is a separate vision LLM call from the field extraction call in
ocr_extraction_prompt.py. Never merge these two calls — they use different
model capabilities and must remain independently observable in LangSmith.
"""

import base64
import os

VALID_DOCUMENT_TYPES: frozenset[str] = frozenset(
    {"cccd", "birth_certificate", "land_certificate", "household_book", "other"}
)

CLASSIFIER_SYSTEM_PROMPT: str = (
    "You are a Vietnamese document classifier. "
    "Examine the provided image and classify it into exactly one of these categories:\n"
    "  cccd              — Căn cước công dân (national ID card)\n"
    "  birth_certificate — Giấy khai sinh (birth certificate)\n"
    "  land_certificate  — Giấy chứng nhận quyền sử dụng đất (land use certificate)\n"
    "  household_book    — Sổ hộ khẩu (household registration book)\n"
    "  other             — Any other document type\n\n"
    "Respond with a SINGLE WORD from the list above. "
    "No explanation, no punctuation, no other text."
)

_MEDIA_TYPES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _media_type(image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower()
    return _MEDIA_TYPES.get(ext, "image/jpeg")


def build_classifier_messages(image_base64: str, image_path: str = "") -> list[dict]:
    """Build the messages list for the document classifier vision call.

    Args:
        image_base64: Base64-encoded image bytes (no data-URI prefix).
        image_path:   Original file path, used only for media_type detection.

    Returns:
        A messages list suitable for LLMService.async_invoke(messages=...).
    """
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": _media_type(image_path),
                        "data": image_base64,
                    },
                },
                {
                    "type": "text",
                    "text": "Classify this document. Respond with a single word.",
                },
            ],
        }
    ]
