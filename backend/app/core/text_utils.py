"""Pure-Python text post-processing utilities.

Zero infrastructure dependencies — importable without a running DB, Redis, or LLM.
"""

from __future__ import annotations

import re


def strip_markdown(text: str) -> str:
    """Remove markdown formatting symbols from LLM output.

    Applied server-side to final_response before streaming.
    Handles the most common markdown patterns the LLM produces
    despite system prompt prohibitions.

    Strips:
    - Headers:      ## Header    -> Header
    - Bold+italic:  ***text***   -> text
    - Bold:         **text**     -> text
    - Italic:       *text*       -> text  (single asterisk)
    - __underline__ variants for bold / italic
    - Bullets:      - item       -> item  (leading dash + space)
    - Bullets:      * item       -> item  (leading asterisk + space)
    - Horizontal:   ---          -> (removed)
    - Inline code:  `code`       -> code
    - Code blocks:  ```...```    -> (content preserved, fences removed)

    Does NOT strip:
    - Numbered lists (1., 2.) — these are semantic, not decorative
    - Vietnamese dashes used in text (em dashes, not list markers)
    - Citation brackets [Dieu X, ...]
    """
    # Remove code fences (``` or ~~~), keep content between them
    text = re.sub(r'```[^\n]*\n?', '', text)
    text = re.sub(r'~~~[^\n]*\n?', '', text)

    # Remove ATX headers (## Header -> Header), any level 1-6
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove bold+italic (*** or ___), then bold (** or __), then italic (* or _)
    # Process longest sequences first to avoid partial stripping.
    # No re.DOTALL — inline formatting never spans lines; DOTALL would cause
    # the italic pattern to consume bullet markers across line boundaries.
    text = re.sub(r'\*{3}(.+?)\*{3}', r'\1', text)
    text = re.sub(r'_{3}(.+?)_{3}', r'\1', text)
    text = re.sub(r'\*{2}(.+?)\*{2}', r'\1', text)
    text = re.sub(r'_{2}(.+?)_{2}', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)

    # Remove inline code backticks
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # Remove bullet list markers at start of line (- item or * item)
    # Only remove when followed by a space — preserves em-dashes and * in text
    text = re.sub(r'^[\-\*]\s+', '', text, flags=re.MULTILINE)

    # Remove standalone horizontal rules (--- or *** on their own line)
    text = re.sub(r'^\s*[-\*]{3,}\s*$', '', text, flags=re.MULTILINE)

    # Collapse 3+ consecutive newlines to 2 (cleanup after removal)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()
