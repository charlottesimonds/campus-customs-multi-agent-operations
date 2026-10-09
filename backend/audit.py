"""Append-only audit trail at output/audit_trail.json.

The file is one JSON array that grows across runs; records are never
rewritten or removed. Each append takes an exclusive file lock (on macOS and
Linux) so tickets run at the same time cannot overwrite each other's records.
Credentials are redacted before anything is written.
"""

import json
import os
import re
import threading
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows: no cross-process lock, the in-process lock still applies
    fcntl = None

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"

# Field names that hold credentials. "token" only matches as a whole word part (access_token, token),
# so usage counters like input_tokens are kept.
_SENSITIVE_KEY = re.compile(
    r"api[_-]?key|secret|password|passwd|authorization|bearer|credential|(?:^|[_-])token$", re.IGNORECASE
)
_JSON_STRING_FIELD = re.compile(r'"((?:[^"\\]|\\.)*)"(\s*:\s*)"(?:[^"\\]|\\.)*"')
_thread_lock = threading.Lock()


class AuditTrailCorrupted(RuntimeError):
    """The existing audit file is not a JSON array. It is left untouched rather than overwritten."""


def _secrets() -> list[str]:
    return [v for k, v in os.environ.items() if _SENSITIVE_KEY.search(k) and v and len(v) >= 8]


def _redact_json_field(match: re.Match) -> str:
    key, sep = match.group(1), match.group(2)
    return f'"{key}"{sep}"[REDACTED]"' if _SENSITIVE_KEY.search(key) else match.group(0)


def redact(value, secrets: list[str] | None = None):
    """Remove credentials: values under sensitive-looking keys, and any env secret appearing in text."""
    secrets = _secrets() if secrets is None else secrets
    if isinstance(value, dict):
        return {
            k: "[REDACTED]" if _SENSITIVE_KEY.search(str(k)) else redact(v, secrets) for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v, secrets) for v in value]
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, "[REDACTED]")
        value = _JSON_STRING_FIELD.sub(_redact_json_field, value)  # sensitive fields inside serialized JSON
    return value


def read_records() -> list[dict]:
    """Every record in the audit trail, oldest first. A record's position in this list never changes."""
    if not AUDIT_PATH.exists():
        return []
    with _thread_lock, open(AUDIT_PATH, encoding="utf-8") as f:
        if fcntl:
            fcntl.flock(f, fcntl.LOCK_SH)
        try:
            text = f.read().strip()
        finally:
            if fcntl:
                fcntl.flock(f, fcntl.LOCK_UN)
    records = json.loads(text) if text else []
    if not isinstance(records, list):
        raise AuditTrailCorrupted(f"{AUDIT_PATH} is not a JSON array.")
    return records


def append_records(records: list[dict]) -> None:
    if not records:
        return
    clean = redact(records)
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _thread_lock:
        fd = os.open(AUDIT_PATH, os.O_RDWR | os.O_CREAT, 0o644)
        with os.fdopen(fd, "r+", encoding="utf-8") as f:
            if fcntl:
                fcntl.flock(f, fcntl.LOCK_EX)
            try:
                text = f.read().strip()
                existing = json.loads(text) if text else []
                if not isinstance(existing, list):
                    raise AuditTrailCorrupted(f"{AUDIT_PATH} is not a JSON array; refusing to overwrite it.")
                existing.extend(clean)
                f.seek(0)
                json.dump(existing, f, indent=2, ensure_ascii=False)
                f.write("\n")
                f.truncate()
                f.flush()
                os.fsync(f.fileno())
            finally:
                if fcntl:
                    fcntl.flock(f, fcntl.LOCK_UN)
