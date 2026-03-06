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
    fetch_seq = [FAKE_LIST_DOC, AFTER_DELETE_DOC, AFTER_DELETE_DOC]
    with _patch_fetch(fetch_seq), _patch_update() as mock_update:
        p = GDocsPipeline("doc-abc")
        p.convert_fake_lists()
    assert mock_update.call_count == 2
    first = mock_update.call_args_list[0][0][1]
    assert "deleteContentRange" in first[0]
    second = mock_update.call_args_list[1][0][1]
    assert "createParagraphBullets" in second[0]


def test_pipeline_fix_garbled():
    pairs = [("M  aaps slot", "Maps slot")]
    with _patch_fetch([FAKE_DOC, FAKE_DOC]), _patch_update() as mock_update:
        p = GDocsPipeline("doc-abc")
        p.fix_garbled_text(pairs)
    req = mock_update.call_args[0][1][0]
    assert req["replaceAllText"]["containsText"]["text"] == "M  aaps slot"
