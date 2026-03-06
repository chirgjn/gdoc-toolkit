from gdocs.models import get_paragraphs, get_text, get_style, is_empty, is_heading, get_image_info

CONTENT = [
    {
        "startIndex": 1, "endIndex": 13,
        "paragraph": {
            "elements": [
                {"startIndex": 1, "endIndex": 13,
                 "textRun": {"content": "Hello world\n"}}
            ],
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
        },
    },
    {
        "startIndex": 13, "endIndex": 23,
        "paragraph": {
            "elements": [
                {"startIndex": 13, "endIndex": 23,
                 "textRun": {"content": "A heading\n"}}
            ],
            "paragraphStyle": {"namedStyleType": "HEADING_2"},
        },
    },
    {
        "startIndex": 23, "endIndex": 24,
        "paragraph": {
            "elements": [
                {"startIndex": 23, "endIndex": 24,
                 "textRun": {"content": "\n"}}
            ],
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
        },
    },
    # Table — should be excluded by get_paragraphs
    {"startIndex": 24, "endIndex": 50, "table": {}},
]


def test_get_paragraphs_excludes_tables():
    paras = get_paragraphs(CONTENT)
    assert len(paras) == 3


def test_get_text_strips_newline():
    assert get_text(CONTENT[0]) == "Hello world"


def test_get_text_joins_multiple_runs():
    block = {
        "startIndex": 1, "endIndex": 12,
        "paragraph": {
            "elements": [
                {"startIndex": 1, "endIndex": 6, "textRun": {"content": "Hello"}},
                {"startIndex": 6, "endIndex": 12, "textRun": {"content": " world\n"}},
            ],
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
        },
    }
    assert get_text(block) == "Hello world"


def test_get_text_ignores_inline_image_elements():
    block = {
        "startIndex": 1, "endIndex": 3,
        "paragraph": {
            "elements": [
                {"startIndex": 1, "endIndex": 2, "inlineObjectElement": {"inlineObjectId": "kix.abc"}},
                {"startIndex": 2, "endIndex": 3, "textRun": {"content": "\n"}},
            ],
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
        },
    }
    assert get_text(block) == ""


def test_get_style_returns_named_style():
    assert get_style(CONTENT[1]) == "HEADING_2"
    assert get_style(CONTENT[0]) == "NORMAL_TEXT"


def test_is_empty_true_for_newline_only():
    assert is_empty(CONTENT[2]) is True


def test_is_empty_false_when_has_text():
    assert is_empty(CONTENT[0]) is False


def test_is_empty_false_when_has_inline_image():
    block = {
        "startIndex": 1, "endIndex": 3,
        "paragraph": {
            "elements": [
                {"startIndex": 1, "endIndex": 2, "inlineObjectElement": {"inlineObjectId": "kix.abc"}},
                {"startIndex": 2, "endIndex": 3, "textRun": {"content": "\n"}},
            ],
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
        },
    }
    assert is_empty(block) is False


def test_is_heading_true_for_heading_styles():
    assert is_heading(CONTENT[1]) is True


def test_is_heading_false_for_normal_text():
    assert is_heading(CONTENT[0]) is False


def test_get_image_info_extracts_uri_and_size():
    inline_objects = {
        "kix.abc": {
            "inlineObjectProperties": {
                "embeddedObject": {
                    "imageProperties": {"contentUri": "https://example.com/img.png"},
                    "size": {
                        "width": {"magnitude": 500},
                        "height": {"magnitude": 300},
                    },
                }
            }
        }
    }
    uri, w, h = get_image_info(inline_objects, "kix.abc")
    assert uri == "https://example.com/img.png"
    assert w == 500
    assert h == 300


def test_get_image_info_falls_back_to_source_uri():
    inline_objects = {
        "kix.abc": {
            "inlineObjectProperties": {
                "embeddedObject": {
                    "imageProperties": {"sourceUri": "https://example.com/src.png"},
                    "size": {
                        "width": {"magnitude": 200},
                        "height": {"magnitude": 100},
                    },
                }
            }
        }
    }
    uri, w, h = get_image_info(inline_objects, "kix.abc")
    assert uri == "https://example.com/src.png"


def test_get_image_info_returns_defaults_for_missing_id():
    uri, w, h = get_image_info({}, "kix.missing")
    assert uri == ""
    assert w == 600
    assert h == 400
