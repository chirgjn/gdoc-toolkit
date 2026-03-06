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
