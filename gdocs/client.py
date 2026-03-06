import json
import subprocess


def _run_gws(args: list[str], body: dict | None = None) -> dict:
    cmd = ["gws"] + args
    if body is not None:
        cmd += ["--json", json.dumps(body)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if not result.stdout.strip():
        raise RuntimeError(f"gws returned no output. stderr: {result.stderr}")
    data = json.loads(result.stdout)
    if "error" in data:
        raise RuntimeError(f"gws API error: {data['error']['message']}")
    return data


def fetch_doc(doc_id: str) -> dict:
    """Fetch a Google Doc and return the full API response dict."""
    params = json.dumps({"documentId": doc_id})
    return _run_gws(["docs", "documents", "get", "--params", params])


def batch_update(doc_id: str, requests: list[dict]) -> dict:
    """Apply batchUpdate requests to a doc. Returns the API response."""
    params = json.dumps({"documentId": doc_id})
    return _run_gws(
        ["docs", "documents", "batchUpdate", "--params", params],
        body={"requests": requests},
    )
