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
