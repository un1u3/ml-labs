"""Append-only JSONL audit log. Only redacted text is ever written."""
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


class AuditLogger:
    def __init__(self, path: Optional[Path]):
        self.path = Path(path) if path else None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, original_input: str, record: Dict[str, Any]) -> None:
        if not self.path:
            return
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "request_sha256": hashlib.sha256(original_input.encode()).hexdigest()[:16],
            **record,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
