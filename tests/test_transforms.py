import pytest
from gdocs.transforms import (
    delete_range,
    insert_text_at,
    replace_full_content,
    apply_heading,
    replace_text,
    fix_garbled_text,
    remove_blank_paragraphs,
    apply_bullets_to_fake_lists,
    apply_bold_to_labels,
    insert_image,
)

# --- Helpers ---

def para_block(start, end, text, style="NORMAL_TEXT", has_bullet=False, has_img=False):
    elements = []
    if has_img:
        elements.append({"startIndex": start, "endIndex": start + 1,
                          "inlineObjectElement": {"inlineObjectId": "kix.x"}})
        elements.append({"startIndex": start + 1, "endIndex": end,
                          "textRun": {"content": "\n"}})
    else:
        elements.append({"startIndex": start, "endIndex": end,
                          "textRun": {"content": text + "\n"}})
    block = {
        "startIndex": start,
        "endIndex": end,
        "paragraph": {
            "elements": elements,
            "paragraphStyle": {"namedStyleType": style},
        },
    }
    if has_bullet:
        block["paragraph"]["bullet"] = {"listId": "kix.abc", "nestingLevel": 0}
    return block


# --- delete_range ---

def test_delete_range():
    assert delete_range(5, 10) == {
        "deleteContentRange": {"range": {"startIndex": 5, "endIndex": 10}}
    }


# --- insert_text_at ---

def test_insert_text_at():
    assert insert_text_at(100, "hello\n") == {
        "insertText": {"location": {"index": 100}, "text": "hello\n"}
    }


# --- replace_full_content ---

def test_replace_full_content_two_requests():
    reqs = replace_full_content("new\n", end_index=500)
    assert len(reqs) == 2
    assert reqs[0]["deleteContentRange"]["range"] == {"startIndex": 1, "endIndex": 499}
    assert reqs[1]["insertText"]["location"]["index"] == 1
    assert reqs[1]["insertText"]["text"] == "new\n"


# --- apply_heading ---

def test_apply_heading_structure():
    req = apply_heading(5, 20, "HEADING_2")
    assert req == {
        "updateParagraphStyle": {
            "range": {"startIndex": 5, "endIndex": 20},
            "paragraphStyle": {"namedStyleType": "HEADING_2"},
            "fields": "namedStyleType",
        }
    }


def test_apply_heading_rejects_invalid_style():
    with pytest.raises(ValueError):
        apply_heading(5, 20, "BOLD")


# --- replace_text ---

def test_replace_text():
    req = replace_text("old", "new")
    assert req == {
        "replaceAllText": {
            "containsText": {"text": "old", "matchCase": True},
            "replaceText": "new",
        }
    }


def test_replace_text_case_insensitive():
    req = replace_text("old", "new", match_case=False)
    assert req["replaceAllText"]["containsText"]["matchCase"] is False


# --- fix_garbled_text ---

def test_fix_garbled_text_returns_replace_all_requests():
    reqs = fix_garbled_text([
        ("M  aaps slot type", "Maps slot type"),
        ("F  betches all", "Fetches all"),
    ])
    assert len(reqs) == 2
    assert reqs[0]["replaceAllText"]["containsText"]["text"] == "M  aaps slot type"
    assert reqs[0]["replaceAllText"]["replaceText"] == "Maps slot type"
    assert reqs[1]["replaceAllText"]["containsText"]["matchCase"] is True


# --- remove_blank_paragraphs ---

def test_remove_blank_paragraphs_deletes_between_normal():
    content = [
        para_block(1, 12, "Some text"),
        para_block(12, 13, ""),        # blank between two normal paras → delete
        para_block(13, 24, "More text"),
    ]
    reqs = remove_blank_paragraphs(content)
    assert len(reqs) == 1
    assert reqs[0]["deleteContentRange"]["range"]["startIndex"] == 12


def test_remove_blank_paragraphs_keeps_blank_after_heading():
    content = [
        para_block(1, 12, "Section", style="HEADING_2"),
        para_block(12, 13, ""),        # after heading → keep
        para_block(13, 24, "Body"),
    ]
    reqs = remove_blank_paragraphs(content)
    assert reqs == []


def test_remove_blank_paragraphs_keeps_blank_before_heading():
    content = [
        para_block(1, 12, "Body"),
        para_block(12, 13, ""),        # before heading → keep
        para_block(13, 23, "Section", style="HEADING_2"),
    ]
    reqs = remove_blank_paragraphs(content)
    assert reqs == []


def test_remove_blank_paragraphs_deletes_duplicate_blanks():
    content = [
        para_block(1, 12, "Body"),
        para_block(12, 13, ""),
        para_block(13, 14, ""),        # second consecutive blank → delete
        para_block(14, 25, "More"),
    ]
    reqs = remove_blank_paragraphs(content)
    starts = [r["deleteContentRange"]["range"]["startIndex"] for r in reqs]
    assert 13 in starts


def test_remove_blank_paragraphs_keeps_blank_adjacent_to_table():
    table_block = {"startIndex": 12, "endIndex": 50, "table": {}}
    content = [
        para_block(1, 12, "Text"),
        table_block,
        para_block(50, 51, ""),        # after table → keep
        para_block(51, 62, "After"),
    ]
    reqs = remove_blank_paragraphs(content)
    assert reqs == []


def test_remove_blank_paragraphs_sorted_descending():
    content = [
        para_block(1, 12, "A"),
        para_block(12, 13, ""),
        para_block(13, 24, "B"),
        para_block(24, 25, ""),
        para_block(25, 36, "C"),
    ]
    reqs = remove_blank_paragraphs(content)
    starts = [r["deleteContentRange"]["range"]["startIndex"] for r in reqs]
    assert starts == sorted(starts, reverse=True)


# --- apply_bullets_to_fake_lists ---

def test_apply_bullets_detects_dash_prefix():
    content = [para_block(1, 14, "- bullet item")]
    deletes, bullets = apply_bullets_to_fake_lists(content)
    assert len(deletes) == 1
    assert deletes[0]["deleteContentRange"]["range"] == {"startIndex": 1, "endIndex": 3}
    assert bullets[0]["createParagraphBullets"]["bulletPreset"] == "BULLET_DISC_CIRCLE_SQUARE"


def test_apply_bullets_detects_numbered_prefix_single_digit():
    content = [para_block(1, 14, "1. numbered")]
    deletes, bullets = apply_bullets_to_fake_lists(content)
    assert deletes[0]["deleteContentRange"]["range"]["endIndex"] == 4  # "1. " = 3 chars
    assert bullets[0]["createParagraphBullets"]["bulletPreset"] == "NUMBERED_DECIMAL_ALPHA_ROMAN"


def test_apply_bullets_detects_numbered_prefix_two_digit():
    content = [para_block(1, 15, "10. numbered")]
    deletes, bullets = apply_bullets_to_fake_lists(content)
    assert deletes[0]["deleteContentRange"]["range"]["endIndex"] == 5  # "10. " = 4 chars


def test_apply_bullets_skips_already_bulleted():
    content = [para_block(1, 14, "- already", has_bullet=True)]
    deletes, bullets = apply_bullets_to_fake_lists(content)
    assert deletes == []
    assert bullets == []


def test_apply_bullets_skips_ranges():
    content = [para_block(100, 114, "- in toc range")]
    deletes, _ = apply_bullets_to_fake_lists(content, skip_ranges={(90, 120)})
    assert deletes == []


def test_apply_bullets_deletes_sorted_descending():
    content = [
        para_block(i * 20, i * 20 + 15, f"- item {i}")
        for i in range(1, 5)
    ]
    deletes, _ = apply_bullets_to_fake_lists(content)
    starts = [d["deleteContentRange"]["range"]["startIndex"] for d in deletes]
    assert starts == sorted(starts, reverse=True)


def test_apply_bullets_bullet_range_excludes_trailing_newline():
    content = [para_block(1, 14, "- bullet item")]
    _, bullets = apply_bullets_to_fake_lists(content)
    assert bullets[0]["createParagraphBullets"]["range"]["endIndex"] == 13  # 14 - 1


# --- apply_bold_to_labels ---

def test_bold_glossary_term():
    content = [para_block(1, 30, "Ad Server: the central system")]
    reqs = apply_bold_to_labels(content)
    assert len(reqs) == 1
    r = reqs[0]["updateTextStyle"]
    assert r["range"]["startIndex"] == 1
    assert r["range"]["endIndex"] == 10  # "Ad Server" = 9 chars, start=1 → end=10
    assert r["textStyle"]["bold"] is True
    assert r["fields"] == "bold"


def test_bold_decision_keyword():
    content = [para_block(1, 35, "Decision: Use approach 2")]
    reqs = apply_bold_to_labels(content)
    assert reqs[0]["updateTextStyle"]["range"]["endIndex"] == 9  # "Decision"=8, start=1 → 9


def test_bold_rationale_keyword():
    content = [para_block(1, 35, "Rationale: Because of compliance")]
    reqs = apply_bold_to_labels(content)
    assert len(reqs) == 1
    assert reqs[0]["updateTextStyle"]["range"]["endIndex"] == 10  # "Rationale"=9


def test_bold_tenet_label():
    content = [para_block(1, 50, "Tenet 1 — Compliance")]
    reqs = apply_bold_to_labels(content)
    assert len(reqs) == 1
    end = reqs[0]["updateTextStyle"]["range"]["endIndex"]
    assert end == 1 + len("Tenet 1 — Compliance")


def test_bold_why_label():
    content = [para_block(1, 50, "Why this works: Because segments are reusable")]
    reqs = apply_bold_to_labels(content)
    assert len(reqs) == 1


def test_bold_system_name_standalone():
    content = [para_block(1, 40, "Ad Platform (Ad Server + Tracker + CDP)")]
    reqs = apply_bold_to_labels(content)
    assert len(reqs) == 1
    r = reqs[0]["updateTextStyle"]["range"]
    assert r["endIndex"] == 39  # block endIndex (40) - 1 = 39; start=1, text len=39


def test_bold_sub_label_principle():
    content = [para_block(1, 30, "Principle: All data is hashed")]
    reqs = apply_bold_to_labels(content)
    assert len(reqs) == 1


def test_bold_skips_heading_paragraphs():
    content = [para_block(1, 30, "Decision: something", style="HEADING_2")]
    reqs = apply_bold_to_labels(content)
    assert reqs == []


# --- insert_image ---

def test_insert_image_no_scaling_needed():
    req = insert_image(100, "https://example.com/img.png", width=400, height=300)
    obj = req["insertInlineImage"]["objectSize"]
    assert obj["width"]["magnitude"] == 400
    assert obj["height"]["magnitude"] == 300
    assert obj["width"]["unit"] == "PT"


def test_insert_image_scales_down_to_max_width():
    req = insert_image(100, "https://example.com/img.png", width=600, height=400)
    obj = req["insertInlineImage"]["objectSize"]
    assert obj["width"]["magnitude"] == 468
    assert obj["height"]["magnitude"] == pytest.approx(312, rel=0.01)


def test_insert_image_location():
    req = insert_image(999, "https://example.com/img.png", width=200, height=100)
    assert req["insertInlineImage"]["location"]["index"] == 999
    assert req["insertInlineImage"]["uri"] == "https://example.com/img.png"
