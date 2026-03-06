import re
from gdocs.models import get_paragraphs, get_text, get_style, is_empty, is_heading

VALID_STYLES = {"TITLE", "HEADING_1", "HEADING_2", "HEADING_3", "NORMAL_TEXT"}
MAX_IMAGE_WIDTH_PT = 468

# System standalone names that get fully bolded when they appear as short lines
_SYSTEM_NAMES = re.compile(r"^(Ad Platform|Offers Engine|RMP|Gratification|SSP)\b")

# Sub-label keywords (from apply_bold.py)
_SUB_LABELS = (
    "Principle", "Enforcement", "Approach", "Benefit",
    "Challenge", "Core Concept", "Key tenant",
)

# Keyword labels that get their keyword bolded
_KEYWORD_LABELS = ("Decision", "Background", "Rationale", "Trade-offs")


def delete_range(start: int, end: int) -> dict:
    return {"deleteContentRange": {"range": {"startIndex": start, "endIndex": end}}}


def insert_text_at(index: int, text: str) -> dict:
    return {"insertText": {"location": {"index": index}, "text": text}}


def replace_full_content(new_text: str, end_index: int) -> list[dict]:
    """
    Replace all document body content.
    Deletes from index 1 to end_index-1 (can't delete the final newline),
    then inserts new_text at index 1.
    """
    return [
        delete_range(1, end_index - 1),
        insert_text_at(1, new_text),
    ]


def apply_heading(start: int, end: int, style: str) -> dict:
    if style not in VALID_STYLES:
        raise ValueError(f"Invalid style: {style!r}. Must be one of {VALID_STYLES}")
    return {
        "updateParagraphStyle": {
            "range": {"startIndex": start, "endIndex": end},
            "paragraphStyle": {"namedStyleType": style},
            "fields": "namedStyleType",
        }
    }


def replace_text(find: str, replace: str, match_case: bool = True) -> dict:
    return {
        "replaceAllText": {
            "containsText": {"text": find, "matchCase": match_case},
            "replaceText": replace,
        }
    }


def fix_garbled_text(replacements: list[tuple[str, str]]) -> list[dict]:
    """
    Return replaceAllText requests for a list of (find, replace) pairs.
    Use this to fix text corrupted by incorrect prefix deletion (e.g. lettered lists).
    Safer than index-based correction. matchCase=True always.
    """
    return [replace_text(find, rep) for find, rep in replacements]


def remove_blank_paragraphs(content: list[dict]) -> list[dict]:
    """
    Return deleteContentRange requests for blank paragraphs.
    Sorted descending to preserve index validity.

    Rules (extracted from remove_whitespace.py):
    - Always delete consecutive duplicate blanks.
    - Keep blanks adjacent to headings (breathing room).
    - Keep blanks adjacent to non-paragraph blocks (tables, TOC).
    - Delete blanks between two normal-text paragraphs.
    """
    blocks = []
    for b in content:
        if "paragraph" in b:
            blocks.append({
                "type": "para",
                "start": b["startIndex"],
                "end": b["endIndex"],
                "is_empty": is_empty(b),
                "is_heading": is_heading(b),
                "block": b,
            })
        else:
            blocks.append({
                "type": "other",  # table, TOC, section break
                "start": b.get("startIndex"),
                "end": b.get("endIndex"),
            })

    to_delete = []

    for i, b in enumerate(blocks):
        if b["type"] != "para" or not b["is_empty"]:
            continue

        prev = blocks[i - 1] if i > 0 else None
        nxt = blocks[i + 1] if i < len(blocks) - 1 else None

        prev_empty = prev and prev["type"] == "para" and prev["is_empty"]
        prev_heading = prev and prev["type"] == "para" and prev["is_heading"]
        next_heading = nxt and nxt["type"] == "para" and nxt["is_heading"]
        prev_other = prev and prev["type"] == "other"
        next_other = nxt and nxt["type"] == "other"

        if prev_empty:
            to_delete.append((b["start"], b["end"]))
        elif prev_heading or next_heading:
            pass  # keep breathing room
        elif prev_other or next_other:
            pass  # keep around tables/TOC
        elif prev and not prev["is_heading"] and nxt and not nxt["is_heading"]:
            to_delete.append((b["start"], b["end"]))

    to_delete.sort(key=lambda x: x[0], reverse=True)
    return [delete_range(s, e) for s, e in to_delete]


def apply_bullets_to_fake_lists(
    content: list[dict],
    skip_ranges: set[tuple[int, int]] | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Detect fake list items (prefixed "- " or "N. ") and return two lists:
    - deletes: deleteContentRange to strip prefixes (sorted descending)
    - bullets: createParagraphBullets requests

    IMPORTANT: Apply deletes first, re-fetch doc, then apply bullets.
    Mixing both in one batch causes index corruption.

    skip_ranges: set of (start, end) tuples — paragraphs whose startIndex falls
    in any range are skipped (e.g. TOC sections, standalone section ref lines).
    """
    skip_ranges = skip_ranges or set()
    deletes = []
    bullets = []

    for block in get_paragraphs(content):
        para = block.get("paragraph", {})
        if para.get("bullet"):
            continue  # already a real bullet

        s, e = block["startIndex"], block["endIndex"]

        # Check skip ranges
        if any(lo <= s <= hi for lo, hi in skip_ranges):
            continue

        text = get_text(block)

        if re.match(r"^- .", text):
            prefix_len = 2
            preset = "BULLET_DISC_CIRCLE_SQUARE"
        elif re.match(r"^\d+[.)]\s", text):
            m = re.match(r"^(\d+[.)]\s)", text)
            prefix_len = len(m.group(1))
            preset = "NUMBERED_DECIMAL_ALPHA_ROMAN"
        else:
            continue

        deletes.append(delete_range(s, s + prefix_len))
        bullets.append({
            "createParagraphBullets": {
                "range": {"startIndex": s, "endIndex": e - 1},
                "bulletPreset": preset,
            }
        })

    deletes.sort(key=lambda r: r["deleteContentRange"]["range"]["startIndex"], reverse=True)
    return deletes, bullets


def apply_bold_to_labels(content: list[dict]) -> list[dict]:
    """
    Apply bold to well-known label patterns in NORMAL_TEXT paragraphs.
    Extracted from apply_bold.py.

    Patterns (in priority order):
    1. Glossary: "TERM: description" → bold the term (up to colon)
    2. Risk labels: "X Risk/Complexity/Dependency:" → bold label
    3. Tenet: "Tenet N — Name" → bold full label
    4. Keyword labels: Decision/Background/Rationale/Trade-offs → bold keyword
    5. "Why X:" / "Why Not X:" → bold the why-label
    6. System names as short standalone lines → bold entire line
    7. Sub-labels: Principle/Enforcement/Approach/Benefit/Challenge/Core Concept/Key tenant
    """
    requests = []

    def bold(start: int, end: int):
        requests.append({
            "updateTextStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "textStyle": {"bold": True},
                "fields": "bold",
            }
        })

    for block in get_paragraphs(content):
        if get_style(block) != "NORMAL_TEXT":
            continue
        text = get_text(block)
        if not text:
            continue
        s = block["startIndex"]
        e = block["endIndex"]

        # 1. Glossary: "TERM: description"
        m = re.match(r"^([A-Z][A-Za-z0-9 /()&\-]+?)(?::\s)", text)
        if m:
            bold(s, s + m.end(1))
            continue

        # 2. Risk/Complexity/Dependency labels
        m2 = re.match(
            r"^([A-Z][A-Za-z /()&\-]+? (?:Risk|Complexity|Dependency)):\s", text
        )
        if m2:
            bold(s, s + m2.end(1))
            continue

        # 3. Tenet: "Tenet N — Name"
        m3 = re.match(r"^(Tenet \d+ — [^:]+)", text)
        if m3:
            bold(s, s + len(m3.group(1)))
            continue

        # 4. Keyword labels
        matched_kw = False
        for kw in _KEYWORD_LABELS:
            if text.startswith(kw + ":"):
                bold(s, s + len(kw))
                matched_kw = True
                break
        if matched_kw:
            continue

        # 5. "Why X:" / "Why Not X:"
        m4 = re.match(r"^(Why (?:Not )?[^:]+):", text)
        if m4:
            bold(s, s + m4.end(1))
            continue

        # 6. System standalone names (short lines)
        if _SYSTEM_NAMES.match(text) and len(text) < 80:
            bold(s, e - 1)  # exclude trailing \n
            continue

        # 7. Sub-labels
        for label in _SUB_LABELS:
            if text.startswith(label):
                bold(s, s + len(label))
                break

    return requests


def insert_image(index: int, uri: str, width: float, height: float) -> dict:
    """
    Return insertInlineImage request, scaling down if width > MAX_IMAGE_WIDTH_PT (468pt).
    Mirrors scale() + insertInlineImage pattern from insert_images_v2.py.
    """
    scale = min(1.0, MAX_IMAGE_WIDTH_PT / width) if width > MAX_IMAGE_WIDTH_PT else 1.0
    w_pt = round(width * scale)
    h_pt = round(height * scale)
    return {
        "insertInlineImage": {
            "uri": uri,
            "location": {"index": index},
            "objectSize": {
                "width": {"magnitude": w_pt, "unit": "PT"},
                "height": {"magnitude": h_pt, "unit": "PT"},
            },
        }
    }
