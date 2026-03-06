# Google Docs Utilities Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a reusable Python library (`gdocs/`) that wraps the `gws` CLI and Google Docs batchUpdate API into composable, safe utility functions — eliminating the one-off scripting pattern from the restructure session.

**Architecture:** A single `gdocs/` package with three layers: (1) a thin `client.py` that shells out to `gws` and handles JSON I/O, (2) a `transforms.py` module of pure functions that produce batchUpdate request dicts, (3) a `pipeline.py` orchestrator that sequences transforms, re-fetches the doc between passes, and applies batches safely. A `cli.py` entry point exposes common operations as commands.

**Tech Stack:** Python 3.11+, `uv` for running scripts, `subprocess` + `json` + `re` stdlib only (no third-party deps beyond `pytest` for tests), `gws` CLI for all API calls.

**Root directory:** `adhoc/gdoc-toolkit/` — this folder has its own isolated git repo.
All paths in this plan are relative to `adhoc/gdoc-toolkit/`.

---

## Progress

| Task | Status |
|------|--------|
| Repo init | ✅ Done — `git init` + empty commit `266647c` |
| 1 — Scaffold | ✅ Done |
| 2 — client.py | ✅ Done |
| 3 — models.py | ✅ Done |
| 4 — transforms.py | ✅ Done |
| 5 — pipeline.py | ✅ Done |
| 6 — cli.py | ✅ Done |
| 7 — README + final check | ✅ Done |

---

## Project Layout

```
adhoc/gdoc-toolkit/          ← git root (own repo, empty commit done)
  gdocs/
    __init__.py
    client.py          # gws shell wrapper — fetch, batchUpdate
    models.py          # plain helper functions: get_text, is_empty, is_heading, get_image_info
    transforms.py      # pure functions returning request dicts
    pipeline.py        # orchestrator: sequence + apply passes
    cli.py             # thin CLI entry point
  tests/
    conftest.py        # shared fixtures (fake doc JSON)
    test_client.py
    test_models.py
    test_transforms.py
    test_pipeline.py
  pyproject.toml
  README.md
```

---

## Task 1: Project scaffold

**Files:**
- Create: `gdocs/__init__.py`
- Create: `pyproject.toml`
- Create: `tests/conftest.py`

**Step 1: Create `pyproject.toml`**

```toml
[project]
name = "gdocs"
version = "0.1.0"
requires-python = ">=3.11"

[project.optional-dependencies]
dev = ["pytest"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 2: Create empty `gdocs/__init__.py`**

```python
```

**Step 3: Create `tests/conftest.py` with shared doc fixture**

The fixture mirrors the real Docs API structure from `get_paras.py` (elements with `startIndex`/`endIndex`, `textRun.content`, `paragraphStyle.namedStyleType`).

```python
import pytest

# Mirrors real Docs API body.content structure
FAKE_DOC = {
    "documentId": "test-doc-id",
    "title": "Test Doc",
    "revisionId": "abc123",
    "body": {
        "content": [
            {
                "startIndex": 1,
                "endIndex": 13,
                "paragraph": {
                    "elements": [
                        {"startIndex": 1, "endIndex": 13,
                         "textRun": {"content": "Hello world\n", "textStyle": {}}}
                    ],
                    "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                },
            },
            {
                "startIndex": 13,
                "endIndex": 23,
                "paragraph": {
                    "elements": [
                        {"startIndex": 13, "endIndex": 23,
                         "textRun": {"content": "A heading\n", "textStyle": {}}}
                    ],
                    "paragraphStyle": {"namedStyleType": "HEADING_2"},
                },
            },
            {
                "startIndex": 23,
                "endIndex": 24,
                "paragraph": {
                    "elements": [
                        {"startIndex": 23, "endIndex": 24,
                         "textRun": {"content": "\n", "textStyle": {}}}
                    ],
                    "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                },
            },
        ]
    },
    "inlineObjects": {},
    "lists": {},
}


@pytest.fixture
def fake_doc():
    return FAKE_DOC


@pytest.fixture
def fake_content(fake_doc):
    return fake_doc["body"]["content"]
```

**Step 4: Verify setup**

```bash
uv run pytest --collect-only
```
Expected: `0 tests collected`, no errors.

**Step 5: Commit**

```bash
git add gdocs/ tests/ pyproject.toml
git commit -m "feat: scaffold gdocs package and test fixtures"
```

---

## Task 2: `client.py` — gws shell wrapper

Extracted from the shell invocation pattern in all /tmp scripts:
- `gws docs documents get --params '{"documentId": "..."}' `
- `gws docs documents batchUpdate --params '...' --json '...'`

**Files:**
- Create: `gdocs/client.py`
- Create: `tests/test_client.py`

**Step 1: Write failing tests**

```python
# tests/test_client.py
import json
from unittest.mock import patch, MagicMock
from gdocs.client import fetch_doc, batch_update


def _mock_run(stdout_data, returncode=0):
    m = MagicMock()
    m.stdout = json.dumps(stdout_data)
    m.stderr = ""
    m.returncode = returncode
    return m


FAKE_DOC = {"documentId": "abc", "body": {"content": []}}


def test_fetch_doc_returns_parsed_json():
    with patch("subprocess.run", return_value=_mock_run(FAKE_DOC)):
        doc = fetch_doc("abc")
    assert doc["documentId"] == "abc"


def test_fetch_doc_passes_correct_gws_command():
    with patch("subprocess.run", return_value=_mock_run(FAKE_DOC)) as mock_run:
        fetch_doc("abc")
    cmd = mock_run.call_args[0][0]
    assert cmd[:4] == ["gws", "docs", "documents", "get"]
    assert "--params" in cmd
    # params must contain documentId
    params_idx = cmd.index("--params")
    assert "abc" in cmd[params_idx + 1]


def test_batch_update_returns_response():
    resp = {"replies": [{}]}
    reqs = [{"insertText": {"location": {"index": 1}, "text": "hi"}}]
    with patch("subprocess.run", return_value=_mock_run(resp)):
        result = batch_update("abc", reqs)
    assert result == resp


def test_batch_update_passes_json_body():
    resp = {"replies": [{}]}
    reqs = [{"insertText": {"location": {"index": 1}, "text": "hi"}}]
    with patch("subprocess.run", return_value=_mock_run(resp)) as mock_run:
        batch_update("abc", reqs)
    cmd = mock_run.call_args[0][0]
    assert "--json" in cmd
    json_idx = cmd.index("--json")
    body = json.loads(cmd[json_idx + 1])
    assert body["requests"] == reqs


def test_batch_update_raises_on_api_error():
    err = {"error": {"code": 400, "message": "Invalid range"}}
    with patch("subprocess.run", return_value=_mock_run(err)):
        try:
            batch_update("abc", [])
            assert False, "should have raised"
        except RuntimeError as e:
            assert "Invalid range" in str(e)


def test_fetch_doc_raises_on_empty_output():
    m = MagicMock()
    m.stdout = ""
    m.stderr = "auth error"
    with patch("subprocess.run", return_value=m):
        try:
            fetch_doc("abc")
            assert False
        except RuntimeError as e:
            assert "no output" in str(e).lower() or "auth" in str(e).lower()
```

**Step 2: Run to verify failure**

```bash
uv run pytest tests/test_client.py -v
```
Expected: `ImportError: No module named 'gdocs.client'`

**Step 3: Implement `gdocs/client.py`**

```python
import json
import subprocess


def _run_gws(args: list[str], body: dict | None = None) -> dict:
    cmd = ["gws"] + args
    if body is not None:
        cmd += ["--json", json.dumps(body)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if not result.stdout.strip():
        raise RuntimeError(f"gws returned no output. stderr: {result.stderr}")
    data = json.loads(result.stdout)
    if "error" in data:
        raise RuntimeError(f"gws API error: {data['error']['message']}")
    return data


def fetch_doc(doc_id: str) -> dict:
    """Fetch a Google Doc and return the full API response dict."""
    params = json.dumps({"documentId": doc_id})
    return _run_gws(["docs", "documents", "get", "--params", params])


def batch_update(doc_id: str, requests: list[dict]) -> dict:
    """Apply batchUpdate requests to a doc. Returns the API response."""
    params = json.dumps({"documentId": doc_id})
    return _run_gws(
        ["docs", "documents", "batchUpdate", "--params", params],
        body={"requests": requests},
    )
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_client.py -v
```
Expected: 6 PASSED

**Step 5: Commit**

```bash
git add gdocs/client.py tests/test_client.py
git commit -m "feat: add gws shell wrapper (fetch_doc, batch_update)"
```

---

## Task 3: `models.py` — doc structure helpers

Extracted from the traversal pattern repeated in every /tmp script (`block.get('paragraph')`, `el.get('textRun')`, `el.get('inlineObjectElement')`). Also includes `get_image_info` from `insert_images_v2.py`.

**Files:**
- Create: `gdocs/models.py`
- Create: `tests/test_models.py`

**Step 1: Write failing tests**

```python
# tests/test_models.py
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
```

**Step 2: Run to verify failure**

```bash
uv run pytest tests/test_models.py -v
```
Expected: `ImportError: No module named 'gdocs.models'`

**Step 3: Implement `gdocs/models.py`**

```python
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
    Mirrors get_image_info() from insert_images_v2.py.
    """
    obj = inline_objects.get(obj_id, {})
    props = obj.get("inlineObjectProperties", {}).get("embeddedObject", {})
    size = props.get("size", {})
    w = size.get("width", {}).get("magnitude", 600)
    h = size.get("height", {}).get("magnitude", 400)
    img_props = props.get("imageProperties", {})
    uri = img_props.get("contentUri") or img_props.get("sourceUri", "")
    return uri, w, h
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_models.py -v
```
Expected: all PASSED

**Step 5: Commit**

```bash
git add gdocs/models.py tests/test_models.py
git commit -m "feat: add doc model helpers (get_text, is_empty, is_heading, get_image_info)"
```

---

## Task 4: `transforms.py` — pure request builders

These are pure functions: no subprocess calls, no side effects. They take doc content + parameters and return lists of batchUpdate request dicts. Every pattern here is directly extracted from the /tmp scripts.

**Files:**
- Create: `gdocs/transforms.py`
- Create: `tests/test_transforms.py`

**Step 1: Write failing tests**

```python
# tests/test_transforms.py
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
# Extracted from fix_garbled2.py: replaceAllText for each (find, replace) pair.
# Safer than index-based deletion for restoring corrupted text.

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
# Logic extracted from remove_whitespace.py:
# - Keep blanks adjacent to headings (breathing room)
# - Keep blanks adjacent to non-paragraph blocks (tables, TOC)
# - Always delete consecutive duplicate blanks
# - Delete blanks between two normal-text paragraphs

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
    # At least the second blank should be deleted
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
# Extracted from apply_lists.py.
# Returns (delete_requests, bullet_requests) — caller applies them in two separate batches.
# Skip ranges can be passed as a set of (start, end) tuples (for TOC, standalone section refs).

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
    # endIndex in createParagraphBullets should be endIndex - 1 (exclude trailing \n)
    assert bullets[0]["createParagraphBullets"]["range"]["endIndex"] == 13  # 14 - 1


# --- apply_bold_to_labels ---
# Extracted from apply_bold.py. Patterns:
# 1. Glossary: "TERM: description" → bold term (up to the colon)
# 2. Risk labels: "X Risk:", "X Complexity:", "X Dependency:" → bold label
# 3. Tenet: "Tenet N — Name" → bold the tenet label
# 4. Keyword labels: Decision, Background, Rationale, Trade-offs → bold keyword
# 5. "Why X:" / "Why Not X:" → bold the why-label
# 6. System names as standalone short lines: Ad Platform, Offers Engine, RMP, etc. → bold whole line
# 7. Sub-labels: Principle, Enforcement, Approach, Benefit, Challenge, Core Concept, Key tenant

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
    # full "Tenet 1 — Compliance" should be bolded
    end = reqs[0]["updateTextStyle"]["range"]["endIndex"]
    assert end == 1 + len("Tenet 1 — Compliance")


def test_bold_why_label():
    content = [para_block(1, 50, "Why this works: Because segments are reusable")]
    reqs = apply_bold_to_labels(content)
    assert len(reqs) == 1


def test_bold_system_name_standalone():
    # Short lines starting with known system names → bold entire line (minus trailing \n)
    content = [para_block(1, 30, "Ad Platform (Ad Server + Tracker + CDP)")]
    reqs = apply_bold_to_labels(content)
    assert len(reqs) == 1
    r = reqs[0]["updateTextStyle"]["range"]
    # endIndex should be block endIndex - 1 (exclude trailing \n)
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
# Extracted from insert_images_v2.py scale() + insertInlineImage pattern.

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
```

**Step 2: Run to verify failure**

```bash
uv run pytest tests/test_transforms.py -v
```
Expected: `ImportError: No module named 'gdocs.transforms'`

**Step 3: Implement `gdocs/transforms.py`**

```python
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

    Example:
        fix_garbled_text([("M  aaps slot type", "Maps slot type")])
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
    # Build enriched block list including non-paragraph blocks
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
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_transforms.py -v
```
Expected: all PASSED

**Step 5: Commit**

```bash
git add gdocs/transforms.py tests/test_transforms.py
git commit -m "feat: add pure batchUpdate request builders (transforms.py)"
```

---

## Task 5: `pipeline.py` — orchestrator

Wraps client + transforms into a stateful object. Re-fetches the doc after each mutating operation to keep indices fresh. Handles the mandatory two-pass list conversion.

**Files:**
- Create: `gdocs/pipeline.py`
- Create: `tests/test_pipeline.py`

**Step 1: Write failing tests**

```python
# tests/test_pipeline.py
import json
from unittest.mock import patch, MagicMock, call
from gdocs.pipeline import GDocsPipeline

FAKE_DOC = {
    "documentId": "doc-abc",
    "body": {"content": [
        {
            "startIndex": 1, "endIndex": 13,
            "paragraph": {
                "elements": [{"startIndex": 1, "endIndex": 13,
                               "textRun": {"content": "Hello world\n"}}],
                "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            },
        },
    ]},
    "inlineObjects": {},
    "lists": {},
}

BLANK_DOC = {
    "documentId": "doc-abc",
    "body": {"content": [
        {
            "startIndex": 1, "endIndex": 12,
            "paragraph": {
                "elements": [{"startIndex": 1, "endIndex": 12,
                               "textRun": {"content": "Some text\n"}}],
                "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            },
        },
        {
            "startIndex": 12, "endIndex": 13,
            "paragraph": {
                "elements": [{"startIndex": 12, "endIndex": 13,
                               "textRun": {"content": "\n"}}],
                "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            },
        },
        {
            "startIndex": 13, "endIndex": 24,
            "paragraph": {
                "elements": [{"startIndex": 13, "endIndex": 24,
                               "textRun": {"content": "More text\n"}}],
                "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            },
        },
    ]},
    "inlineObjects": {},
    "lists": {},
}

FAKE_LIST_DOC = {
    "documentId": "doc-abc",
    "body": {"content": [
        {
            "startIndex": 1, "endIndex": 14,
            "paragraph": {
                "elements": [{"startIndex": 1, "endIndex": 14,
                               "textRun": {"content": "- list item\n"}}],
                "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            },
        },
    ]},
    "inlineObjects": {},
    "lists": {},
}

AFTER_DELETE_DOC = {
    "documentId": "doc-abc",
    "body": {"content": [
        {
            "startIndex": 1, "endIndex": 12,
            "paragraph": {
                "elements": [{"startIndex": 1, "endIndex": 12,
                               "textRun": {"content": "list item\n"}}],
                "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            },
        },
    ]},
    "inlineObjects": {},
    "lists": {},
}

FAKE_RESP = {"replies": [{}]}


def _patch_fetch(side_effect):
    return patch("gdocs.pipeline.fetch_doc", side_effect=side_effect)

def _patch_update():
    return patch("gdocs.pipeline.batch_update", return_value=FAKE_RESP)


def test_pipeline_fetches_doc_on_init():
    with _patch_fetch([FAKE_DOC]) as mock_fetch, _patch_update():
        p = GDocsPipeline("doc-abc")
    mock_fetch.assert_called_once_with("doc-abc")
    assert p.doc["documentId"] == "doc-abc"


def test_pipeline_apply_calls_batch_update():
    reqs = [{"insertText": {"location": {"index": 1}, "text": "hi\n"}}]
    with _patch_fetch([FAKE_DOC, FAKE_DOC]), _patch_update() as mock_update:
        p = GDocsPipeline("doc-abc")
        p.apply(reqs)
    mock_update.assert_called_once_with("doc-abc", reqs)


def test_pipeline_apply_refetches_after_update():
    reqs = [{"insertText": {"location": {"index": 1}, "text": "hi\n"}}]
    with _patch_fetch([FAKE_DOC, FAKE_DOC]) as mock_fetch, _patch_update():
        p = GDocsPipeline("doc-abc")
        p.apply(reqs)
    assert mock_fetch.call_count == 2  # init + after apply


def test_pipeline_apply_skips_empty_requests():
    with _patch_fetch([FAKE_DOC]), _patch_update() as mock_update:
        p = GDocsPipeline("doc-abc")
        p.apply([])
    mock_update.assert_not_called()


def test_pipeline_replace_text():
    with _patch_fetch([FAKE_DOC, FAKE_DOC]), _patch_update() as mock_update:
        p = GDocsPipeline("doc-abc")
        p.replace_text("Hello", "Hi")
    req = mock_update.call_args[0][1][0]
    assert req["replaceAllText"]["containsText"]["text"] == "Hello"
    assert req["replaceAllText"]["replaceText"] == "Hi"


def test_pipeline_remove_blank_paragraphs():
    with _patch_fetch([BLANK_DOC, BLANK_DOC]), _patch_update() as mock_update:
        p = GDocsPipeline("doc-abc")
        p.remove_blank_paragraphs()
    mock_update.assert_called_once()
    reqs = mock_update.call_args[0][1]
    assert reqs[0]["deleteContentRange"]["range"]["startIndex"] == 12


def test_pipeline_convert_fake_lists_two_passes():
    # init → FAKE_LIST_DOC
    # after pass 1 delete → AFTER_DELETE_DOC
    # after pass 2 bullets → AFTER_DELETE_DOC (no more fake items)
    fetch_seq = [FAKE_LIST_DOC, AFTER_DELETE_DOC, AFTER_DELETE_DOC]
    with _patch_fetch(fetch_seq), _patch_update() as mock_update:
        p = GDocsPipeline("doc-abc")
        p.convert_fake_lists()
    # Two batch_update calls: one for prefix deletions, one for bullet application
    assert mock_update.call_count == 2
    # First call: deletes
    first = mock_update.call_args_list[0][0][1]
    assert "deleteContentRange" in first[0]
    # Second call: bullets
    second = mock_update.call_args_list[1][0][1]
    assert "createParagraphBullets" in second[0]


def test_pipeline_fix_garbled():
    pairs = [("M  aaps slot", "Maps slot")]
    with _patch_fetch([FAKE_DOC, FAKE_DOC]), _patch_update() as mock_update:
        p = GDocsPipeline("doc-abc")
        p.fix_garbled_text(pairs)
    req = mock_update.call_args[0][1][0]
    assert req["replaceAllText"]["containsText"]["text"] == "M  aaps slot"
```

**Step 2: Run to verify failure**

```bash
uv run pytest tests/test_pipeline.py -v
```
Expected: `ImportError: No module named 'gdocs.pipeline'`

**Step 3: Implement `gdocs/pipeline.py`**

```python
from gdocs.client import fetch_doc, batch_update
from gdocs.transforms import (
    replace_text as _replace_text_req,
    fix_garbled_text as _garbled_reqs,
    remove_blank_paragraphs as _blank_reqs,
    apply_bullets_to_fake_lists,
    apply_bold_to_labels as _bold_reqs,
)


class GDocsPipeline:
    """
    Stateful orchestrator for a single Google Doc.
    Fetches the doc on init and re-fetches after every mutating operation
    so that index-based transforms always work against fresh offsets.
    """

    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        self.doc = fetch_doc(doc_id)

    @property
    def content(self) -> list[dict]:
        return self.doc.get("body", {}).get("content", [])

    @property
    def inline_objects(self) -> dict:
        return self.doc.get("inlineObjects", {})

    def _refetch(self):
        self.doc = fetch_doc(self.doc_id)

    def apply(self, requests: list[dict]) -> dict | None:
        """Send requests via batchUpdate then re-fetch. No-op if requests is empty."""
        if not requests:
            return None
        result = batch_update(self.doc_id, requests)
        self._refetch()
        return result

    def replace_text(self, find: str, replace: str, match_case: bool = True):
        """Find-and-replace across entire doc."""
        self.apply([_replace_text_req(find, replace, match_case)])

    def fix_garbled_text(self, replacements: list[tuple[str, str]]):
        """
        Fix text corrupted by bad prefix deletion using replaceAllText.
        Pass a list of (corrupted_text, correct_text) tuples.
        """
        self.apply(_garbled_reqs(replacements))

    def remove_blank_paragraphs(self):
        """Remove blank paragraphs (keeps blanks near headings and tables)."""
        reqs = _blank_reqs(self.content)
        self.apply(reqs)

    def apply_bold(self):
        """Apply bold to glossary terms, decision labels, tenet labels, etc."""
        reqs = _bold_reqs(self.content)
        self.apply(reqs)

    def convert_fake_lists(self, skip_ranges: set[tuple[int, int]] | None = None):
        """
        Two-pass conversion of fake list items to real Docs bullets.
        Pass 1: delete text prefixes (- , 1. ) — sorted descending.
        Pass 2: apply createParagraphBullets — after mandatory re-fetch.

        skip_ranges: index ranges to exclude (e.g. TOC section, standalone refs).
        """
        deletes, _ = apply_bullets_to_fake_lists(self.content, skip_ranges)
        if deletes:
            self.apply(deletes)  # triggers re-fetch internally
        # Re-detect on fresh content (indices shifted after deletions)
        _, bullets = apply_bullets_to_fake_lists(self.content, skip_ranges)
        self.apply(bullets)
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_pipeline.py -v
```
Expected: all PASSED

**Step 5: Run full suite**

```bash
uv run pytest -v
```
Expected: all PASSED across all test files.

**Step 6: Commit**

```bash
git add gdocs/pipeline.py tests/test_pipeline.py
git commit -m "feat: add GDocsPipeline orchestrator with two-pass list conversion"
```

---

## Task 6: `cli.py` — command-line entry point

Thin wrapper so the library is usable without writing Python.

**Files:**
- Create: `gdocs/cli.py`

No unit tests (thin dispatch only). Verify manually.

**Step 1: Implement `gdocs/cli.py`**

```python
"""
gdocs CLI — thin wrapper around GDocsPipeline.

Usage:
  uv run -m gdocs.cli remove-blanks <doc_id>
  uv run -m gdocs.cli convert-lists <doc_id>
  uv run -m gdocs.cli apply-bold <doc_id>
  uv run -m gdocs.cli replace-text <doc_id> <find> <replace>
  uv run -m gdocs.cli fix-garbled <doc_id> <corrupted> <correct> [<corrupted> <correct> ...]
"""
import sys
from gdocs.pipeline import GDocsPipeline


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)

    command, doc_id, *rest = args
    p = GDocsPipeline(doc_id)

    match command:
        case "remove-blanks":
            p.remove_blank_paragraphs()
            print("Done: blank paragraphs removed.")

        case "convert-lists":
            p.convert_fake_lists()
            print("Done: fake lists converted to real bullets.")

        case "apply-bold":
            p.apply_bold()
            print("Done: bold labels applied.")

        case "replace-text":
            if len(rest) < 2:
                print("Usage: replace-text <doc_id> <find> <replace>")
                sys.exit(1)
            p.replace_text(rest[0], rest[1])
            print(f"Done: replaced {rest[0]!r} → {rest[1]!r}.")

        case "fix-garbled":
            if len(rest) < 2 or len(rest) % 2 != 0:
                print("Usage: fix-garbled <doc_id> <corrupted> <correct> ...")
                sys.exit(1)
            pairs = [(rest[i], rest[i + 1]) for i in range(0, len(rest), 2)]
            p.fix_garbled_text(pairs)
            print(f"Done: fixed {len(pairs)} garbled strings.")

        case _:
            print(f"Unknown command: {command!r}")
            print(__doc__)
            sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 2: Verify full test suite still passes**

```bash
uv run pytest -v
```
Expected: all PASSED

**Step 3: Commit**

```bash
git add gdocs/cli.py
git commit -m "feat: add CLI entry point (remove-blanks, convert-lists, apply-bold, replace-text, fix-garbled)"
```

---

## Task 7: README and final check

**Step 1: Create `README.md`**

```markdown
# gdocs — Google Docs utilities

Reusable Python utilities for programmatic Google Doc manipulation via the `gws` CLI.
Distilled from a doc restructuring session involving heading application, image insertion,
blank removal, bold labeling, and list conversion.

## Setup

```bash
uv sync --extra dev
gws auth login   # authenticate once
```

## As a library

```python
from gdocs.pipeline import GDocsPipeline

p = GDocsPipeline("YOUR_DOC_ID")

# Remove mid-content blank paragraphs (keeps blanks near headings/tables)
p.remove_blank_paragraphs()

# Convert "- item" and "1. item" plain text into real Docs bullet lists
p.convert_fake_lists()

# Bold glossary terms, Decision:/Rationale: labels, tenet names, etc.
p.apply_bold()

# Safe find-and-replace (index-free)
p.replace_text("old section name", "new section name")

# Fix text garbled by bad list prefix deletion
p.fix_garbled_text([
    ("M  aaps slot type", "Maps slot type"),
    ("F  betches all candidate ads.", "Fetches all candidate ads."),
])
```

## As CLI

```bash
uv run -m gdocs.cli remove-blanks YOUR_DOC_ID
uv run -m gdocs.cli convert-lists YOUR_DOC_ID
uv run -m gdocs.cli apply-bold YOUR_DOC_ID
uv run -m gdocs.cli replace-text YOUR_DOC_ID "old text" "new text"
uv run -m gdocs.cli fix-garbled YOUR_DOC_ID "corrupted text" "correct text"
```

## Low-level transforms (no API calls)

```python
from gdocs.transforms import (
    replace_full_content,   # delete all + insert new text
    apply_heading,          # updateParagraphStyle request
    insert_image,           # insertInlineImage request (auto-scales to 468pt width)
    fix_garbled_text,       # replaceAllText for corrupted strings
)
from gdocs.models import get_image_info  # extract uri/size from inlineObjects
from gdocs.client import fetch_doc, batch_update  # raw gws wrappers
```

## Key rules

- **Always sort deletions descending** — all multi-delete transforms do this internally.
- **Two-pass list conversion** — prefix deletion and bullet application cannot be in the same batch. `convert_fake_lists()` handles this automatically.
- **Prefer `replace_text` over index-based edits** — it's index-safe and always correct.
- **Re-fetch between passes** — `GDocsPipeline.apply()` always re-fetches after each batch.
- **Image width limit** — Google Docs letter page max ≈ 468pt. `insert_image()` scales automatically.
```

**Step 2: Final test run**

```bash
uv run pytest -v --tb=short
```
Expected: all PASSED, no warnings.

**Step 3: Final commit**

```bash
git add README.md
git commit -m "docs: add README with library, CLI, and key rules"
```

---

## Summary

| Task | What it builds | Key source scripts |
|------|---------------|-------------------|
| 1 | Scaffold: pyproject.toml, package, fixtures | — |
| 2 | `client.py`: `fetch_doc`, `batch_update` | All /tmp scripts |
| 3 | `models.py`: `get_text`, `is_empty`, `is_heading`, `get_image_info` | `get_paras.py`, `insert_images_v2.py` |
| 4 | `transforms.py`: all pure request builders | `apply_bold.py`, `apply_lists.py`, `remove_whitespace.py`, `fix_garbled2.py`, `insert_images_v2.py` |
| 5 | `pipeline.py`: `GDocsPipeline` orchestrator | `apply_lists.py` (two-pass pattern) |
| 6 | `cli.py`: CLI entry point | `fix_garbled2.py`, `fix_lettered.py` |
| 7 | README + final test run | — |
