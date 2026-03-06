"""
Extract Mermaid diagram blocks from a Markdown file and write each to a .mmd file.

Usage:
  uv run scripts/extract_diagrams.py <source.md> <output_dir> [name1 name2 ...]

If names are not provided, diagrams are named diagram-01, diagram-02, etc.

Example:
  uv run scripts/extract_diagrams.py docs/spec.md docs/diagrams/ \\
    architecture journey-engineer journey-pm
"""
import re
import sys
from pathlib import Path


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)

    source = Path(args[0])
    output_dir = Path(args[1])
    names = args[2:]

    if not source.exists():
        print(f"Error: {source} not found")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    content = source.read_text()
    pattern = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)
    matches = pattern.findall(content)

    if not matches:
        print("No mermaid blocks found.")
        sys.exit(0)

    if not names:
        names = [f"diagram-{i+1:02d}" for i in range(len(matches))]

    for i, (name, diagram) in enumerate(zip(names, matches)):
        path = output_dir / f"{name}.mmd"
        path.write_text(diagram.strip())
        print(f"Written: {path}")

    if len(matches) > len(names):
        print(f"Warning: {len(matches) - len(names)} diagrams had no names and were skipped.")


if __name__ == "__main__":
    main()
