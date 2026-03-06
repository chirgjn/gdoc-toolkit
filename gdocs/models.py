HEADING_STYLES = {"HEADING_1", "HEADING_2", "HEADING_3"}


def get_paragraphs(content: list[dict]) -> list[dict]:
    """Return only paragraph blocks (skip tables, TOC, section breaks)."""
    return [b for b in content if "paragraph" in b]


def get_text(block: dict) -> str:
    """Return stripped plain text of a paragraph block (joins all textRun elements)."""
    para = block.get("paragraph", {})
    parts = []
    for el in para.get("elements", []):
        tr = el.get("textRun")
        if tr:
            parts.append(tr.get("content", ""))
    return "".join(parts).strip()


def get_style(block: dict) -> str:
    """Return the namedStyleType of a paragraph block."""
    para = block.get("paragraph", {})
    return para.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")


def is_empty(block: dict) -> bool:
    """True if block is a paragraph with no text and no inline images."""
    para = block.get("paragraph")
    if not para:
        return False
    has_img = any(el.get("inlineObjectElement") for el in para.get("elements", []))
    return get_text(block) == "" and not has_img


def is_heading(block: dict) -> bool:
    """True if block is a HEADING_1/2/3 paragraph (not TITLE)."""
    return get_style(block) in HEADING_STYLES


def get_image_info(
    inline_objects: dict, obj_id: str
) -> tuple[str, float, float]:
    """
    Extract (uri, width_pt, height_pt) from a doc's inlineObjects dict.
    Falls back to sourceUri if contentUri is absent. Returns defaults if obj_id missing.
    """
    obj = inline_objects.get(obj_id, {})
    props = obj.get("inlineObjectProperties", {}).get("embeddedObject", {})
    size = props.get("size", {})
    w = size.get("width", {}).get("magnitude", 600)
    h = size.get("height", {}).get("magnitude", 400)
    img_props = props.get("imageProperties", {})
    uri = img_props.get("contentUri") or img_props.get("sourceUri", "")
    return uri, w, h
