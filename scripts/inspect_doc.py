"""
Print all paragraphs in a Google Doc with their index ranges and text.
Useful for finding indices before applying heading or deletion operations.

Usage:
  uv run scripts/inspect_doc.py <doc_id>
  uv run scripts/inspect_doc.py <doc_id> --max-len 120
  uv run scripts/inspect_doc.py <doc_id> --headings-only
"""
import sys
from gdocs.client import fetch_doc
from gdocs.models import get_paragraphs, get_text, get_style


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    doc_id = args[0]
    max_len = 90
    headings_only = False

    if "--max-len" in args:
        max_len = int(args[args.index("--max-len") + 1])
    if "--headings-only" in args:
        headings_only = True

    doc = fetch_doc(doc_id)
    content = doc.get("body", {}).get("content", [])

    for block in get_paragraphs(content):
        style = get_style(block)
        if headings_only and style == "NORMAL_TEXT":
            continue
        text = get_text(block)
        if not text:
            continue
        s, e = block["startIndex"], block["endIndex"]
        style_tag = f"[{style}] " if style != "NORMAL_TEXT" else ""
        print(f"{s}-{e}: {style_tag}{text[:max_len]}")


if __name__ == "__main__":
    main()
