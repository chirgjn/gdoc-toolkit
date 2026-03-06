# scripts/

Doc-specific scripts that use the `gdocs` library.

| Script | Purpose |
|--------|---------|
| `restructure.py` | Run the full post-restructure pipeline for the 1P Ads in Ad Server tech spec. Supports running individual steps via `--step`. |
| `inspect_doc.py` | Print all paragraphs with index ranges. Useful for finding indices before heading or deletion operations. |
| `extract_diagrams.py` | Extract Mermaid diagram blocks from a Markdown file into `.mmd` files. |

## Usage

```bash
# Run all restructure steps
uv run scripts/restructure.py

# Run a single step
uv run scripts/restructure.py --step fix-headers
uv run scripts/restructure.py --step apply-headings
uv run scripts/restructure.py --step insert-images
uv run scripts/restructure.py --step remove-blanks
uv run scripts/restructure.py --step apply-bold
uv run scripts/restructure.py --step convert-lists
uv run scripts/restructure.py --step fix-garbled

# Inspect a doc
uv run scripts/inspect_doc.py <doc_id>
uv run scripts/inspect_doc.py <doc_id> --headings-only
uv run scripts/inspect_doc.py <doc_id> --max-len 120

# Extract Mermaid diagrams
uv run scripts/extract_diagrams.py docs/spec.md docs/diagrams/ arch journey-pm
```
