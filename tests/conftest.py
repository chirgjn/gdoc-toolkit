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
