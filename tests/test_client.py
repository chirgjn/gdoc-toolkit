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
