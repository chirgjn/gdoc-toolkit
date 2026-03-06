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
        deletes, bullets = apply_bullets_to_fake_lists(self.content, skip_ranges)
        if deletes:
            self.apply(deletes)  # triggers re-fetch internally
        # Apply bullets as a separate batch (indices are now shifted after deletions)
        self.apply(bullets)
