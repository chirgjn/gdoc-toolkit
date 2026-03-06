# gdocs — Google Docs utilities

Reusable Python utilities for programmatic Google Doc manipulation via the `gws` CLI.
Distilled from a doc restructuring session involving heading application, image insertion,
blank removal, bold labeling, and list conversion.

---

## Setup

```bash
uv sync --extra dev
gws auth login   # authenticate once
```

**Requirements:** Python 3.11+, [`gws` CLI](https://github.com/googleworkspace/gws-cli) authenticated.

---

## Architecture

```
gdocs/
  client.py      # gws shell wrapper — fetch_doc, batch_update
  models.py      # doc structure helpers — get_text, is_empty, is_heading, get_image_info
  transforms.py  # pure functions returning batchUpdate request dicts
  pipeline.py    # GDocsPipeline orchestrator
  cli.py         # CLI entry point
```

Three layers:
1. **`client.py`** — shells out to `gws`, handles JSON I/O
2. **`transforms.py`** — pure functions, no API calls, composable
3. **`pipeline.py`** — stateful orchestrator that sequences transforms and re-fetches between passes

---

## Quick start

```python
from gdocs.pipeline import GDocsPipeline

p = GDocsPipeline("YOUR_DOC_ID")

p.remove_blank_paragraphs()
p.convert_fake_lists()
p.apply_bold()
p.replace_text("old section name", "new section name")
```

---

## `GDocsPipeline`

High-level stateful orchestrator. Fetches the doc on init and **re-fetches after every
mutating operation** so that index-based transforms always see fresh offsets.

```python
from gdocs.pipeline import GDocsPipeline

p = GDocsPipeline(doc_id)
```

### `p.apply(requests) → dict | None`

Send a list of batchUpdate request dicts directly. Re-fetches the doc afterwards.
No-op (no API call) if `requests` is empty.

```python
from gdocs.transforms import insert_text_at
p.apply([insert_text_at(100, "New paragraph\n")])
```

### `p.replace_text(find, replace, match_case=True)`

Find-and-replace across the entire doc using `replaceAllText`. Index-safe — preferred
over any index-based edit when the target text is unique enough to match.

```python
p.replace_text("Old Title", "New Title")
p.replace_text("HTTP", "HTTPS", match_case=False)
```

### `p.fix_garbled_text(replacements)`

Fix text corrupted by incorrect list prefix deletion (e.g. `a. Maps...` → `aaps...`).
Applies a `replaceAllText` for each `(corrupted, correct)` pair.

```python
p.fix_garbled_text([
    ("M  aaps slot type", "Maps slot type"),
    ("F  betches all candidate ads.", "Fetches all candidate ads."),
])
```

### `p.remove_blank_paragraphs()`

Delete blank paragraphs selectively. Keeps blanks that provide breathing room
(adjacent to headings or non-paragraph blocks like tables). Deletes mid-content
blanks and all consecutive duplicate blanks.

```python
p.remove_blank_paragraphs()
```

### `p.convert_fake_lists(skip_ranges=None)`

Convert plain-text fake list items (`- item`, `1. item`) to real Docs bullet lists.
Enforces the mandatory two-pass pattern automatically:
1. Delete text prefixes (`- `, `1. `) — sorted descending to avoid index drift
2. Re-fetch the doc
3. Apply `createParagraphBullets`

`skip_ranges` — optional set of `(start, end)` index tuples. Paragraphs whose
`startIndex` falls within any range are skipped (e.g. a TOC section or standalone
section reference lines).

```python
p.convert_fake_lists()

# Skip a known TOC range
p.convert_fake_lists(skip_ranges={(3191, 3711)})
```

### `p.apply_bold(keyword_labels=..., sub_labels=..., standalone_names=...)`

Apply bold formatting to label patterns in `NORMAL_TEXT` paragraphs.
Headings are always skipped. See [Bold patterns](#bold-patterns) for full details.

```python
# Use all defaults
p.apply_bold()

# Custom keyword labels only, no standalone names
p.apply_bold(
    keyword_labels=("Summary", "Context", "Decision"),
    standalone_names=(),
)

# Disable sub-labels entirely
p.apply_bold(sub_labels=())
```

---

## `transforms.py` — pure request builders

All functions return request dicts (or lists of them) suitable for passing to
`batch_update` or `p.apply()`. No API calls, no side effects.

### `delete_range(start, end) → dict`

```python
delete_range(5, 10)
# → {"deleteContentRange": {"range": {"startIndex": 5, "endIndex": 10}}}
```

### `insert_text_at(index, text) → dict`

```python
insert_text_at(100, "New paragraph\n")
# → {"insertText": {"location": {"index": 100}, "text": "New paragraph\n"}}
```

### `replace_full_content(new_text, end_index) → list[dict]`

Replace the entire document body. Returns two requests: delete from index 1 to
`end_index - 1`, then insert `new_text` at index 1.

```python
reqs = replace_full_content(new_text, end_index=doc["body"]["content"][-1]["endIndex"])
p.apply(reqs)
```

### `apply_heading(start, end, style) → dict`

Returns an `updateParagraphStyle` request. Raises `ValueError` for invalid styles.

Valid styles: `TITLE`, `HEADING_1`, `HEADING_2`, `HEADING_3`, `NORMAL_TEXT`.

```python
apply_heading(5, 20, "HEADING_2")
```

### `replace_text(find, replace, match_case=True) → dict`

Returns a single `replaceAllText` request.

```python
replace_text("old", "new")
replace_text("http", "https", match_case=False)
```

### `fix_garbled_text(replacements) → list[dict]`

Returns a `replaceAllText` request for each `(find, replace)` pair. Always
`matchCase=True`.

```python
fix_garbled_text([("M  aaps slot type", "Maps slot type")])
```

### `remove_blank_paragraphs(content) → list[dict]`

Returns `deleteContentRange` requests for blank paragraphs, sorted descending.

Rules:
- **Delete** blanks between two normal-text paragraphs
- **Delete** consecutive duplicate blanks (second blank onward)
- **Keep** blanks adjacent to headings (breathing room)
- **Keep** blanks adjacent to non-paragraph blocks (tables, TOC)

```python
reqs = remove_blank_paragraphs(p.content)
p.apply(reqs)
```

### `apply_bullets_to_fake_lists(content, skip_ranges=None) → (list[dict], list[dict])`

Detect fake list items and return `(deletes, bullets)` — two separate lists that
**must be applied in separate batches** (delete first, re-fetch, then bullets).

- Dash items (`- text`) → `BULLET_DISC_CIRCLE_SQUARE`
- Numbered items (`1. text`, `10. text`) → `NUMBERED_DECIMAL_ALPHA_ROMAN`
- Already-bulleted paragraphs are skipped
- `skip_ranges`: set of `(start, end)` tuples to exclude

Deletes are sorted descending. `GDocsPipeline.convert_fake_lists()` handles the
two-pass sequencing automatically.

```python
deletes, bullets = apply_bullets_to_fake_lists(content, skip_ranges={(3191, 3711)})
p.apply(deletes)   # re-fetches internally
p.apply(bullets)
```

### `apply_bold_to_labels(content, keyword_labels=..., sub_labels=..., standalone_names=...) → list[dict]`

See [Bold patterns](#bold-patterns) below.

### `insert_image(index, uri, width, height) → dict`

Returns an `insertInlineImage` request. Scales down proportionally if `width`
exceeds 468pt (Google Docs letter-page maximum).

```python
uri, w, h = get_image_info(p.inline_objects, "kix.abc")
req = insert_image(index=500, uri=uri, width=w, height=h)
p.apply([req])
```

---

## `models.py` — doc structure helpers

### `get_paragraphs(content) → list[dict]`

Filter `body.content` to paragraph blocks only (excludes tables, TOC, section breaks).

### `get_text(block) → str`

Join all `textRun` elements in a paragraph block and strip the trailing newline.
Ignores `inlineObjectElement` (image) elements.

### `get_style(block) → str`

Return the `namedStyleType` of a paragraph block (e.g. `"HEADING_2"`, `"NORMAL_TEXT"`).

### `is_empty(block) → bool`

True if the paragraph has no text and no inline images.

### `is_heading(block) → bool`

True if the paragraph style is `HEADING_1`, `HEADING_2`, or `HEADING_3`.

### `get_image_info(inline_objects, obj_id) → (uri, width, height)`

Extract `(uri, width_pt, height_pt)` from a doc's `inlineObjects` dict.
Falls back to `sourceUri` if `contentUri` is absent.
Returns `("", 600, 400)` if `obj_id` is not found.

```python
uri, w, h = get_image_info(doc["inlineObjects"], "kix.abc123")
```

---

## `client.py` — raw gws wrappers

### `fetch_doc(doc_id) → dict`

Fetch a Google Doc and return the full API response dict. Raises `RuntimeError`
on empty output or auth failure.

### `batch_update(doc_id, requests) → dict`

Apply a list of batchUpdate request dicts. Returns the API response.
Raises `RuntimeError` if the response contains an `"error"` key.

---

## Bold patterns

`apply_bold_to_labels` (and `p.apply_bold()`) applies bold to `NORMAL_TEXT`
paragraphs by matching seven patterns in priority order. The first matching
pattern wins and processing moves to the next paragraph.

| Priority | Pattern | Example | What gets bolded |
|----------|---------|---------|-----------------|
| 1 | Glossary | `Ad Server: the central system` | `Ad Server` |
| 2 | Risk labels | `Low Risk: mitigated by X` | `Low Risk` |
| 3 | Tenet | `Tenet 1 — Compliance` | `Tenet 1 — Compliance` |
| 4 | Keyword labels | `Decision: use approach 2` | `Decision` |
| 5 | Why-label | `Why this works: because...` | `Why this works` |
| 6 | Standalone names | `Ad Platform (Ad Server + Tracker)` | entire line |
| 7 | Sub-labels | `Principle some explanation` | `Principle` |

Patterns 4, 6, and 7 are configurable via parameters:

| Parameter | Default | Controls |
|-----------|---------|---------|
| `keyword_labels` | `("Decision", "Background", "Rationale", "Trade-offs")` | Pattern 4 |
| `standalone_names` | `("Ad Platform", "Offers Engine", "RMP", "Gratification", "SSP")` | Pattern 6 |
| `sub_labels` | `("Principle", "Enforcement", "Approach", "Benefit", "Challenge", "Core Concept", "Key tenant")` | Pattern 7 |

Pass an empty tuple `()` to disable any group:

```python
# Only glossary, tenet, and why-label patterns — nothing domain-specific
p.apply_bold(keyword_labels=(), sub_labels=(), standalone_names=())
```

---

## CLI reference

```bash
uv run -m gdocs.cli <command> <doc_id> [args...]
```

| Command | Args | Effect |
|---------|------|--------|
| `remove-blanks` | — | Remove blank paragraphs |
| `convert-lists` | — | Convert fake lists to real bullets |
| `apply-bold` | — | Apply bold label patterns |
| `replace-text` | `<find> <replace>` | Find-and-replace across doc |
| `fix-garbled` | `<corrupted> <correct> ...` | Fix garbled strings (pairs) |

```bash
uv run -m gdocs.cli remove-blanks 1VvNIj9z...
uv run -m gdocs.cli replace-text 1VvNIj9z... "Old Title" "New Title"
uv run -m gdocs.cli fix-garbled 1VvNIj9z... "M  aaps slot" "Maps slot" "F  betches" "Fetches"
```

---

## Key rules

- **Always sort deletions descending** — all multi-delete transforms do this internally to prevent index drift.
- **Two-pass list conversion** — prefix deletion and bullet application cannot be in the same batch. `convert_fake_lists()` handles this automatically.
- **Prefer `replace_text` over index-based edits** — it's index-safe and always correct when the target string is unique.
- **Re-fetch between passes** — `GDocsPipeline.apply()` always re-fetches after each batch so subsequent transforms see accurate indices.
- **Image width limit** — Google Docs letter-page max is ≈ 468pt. `insert_image()` scales down automatically.
- **Glossary pattern takes priority** — any `CAPITALISED TERM: description` line will be matched by pattern 1 before reaching keyword or sub-label checks.
