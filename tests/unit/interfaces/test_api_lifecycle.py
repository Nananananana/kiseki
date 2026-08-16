"""/lifecycle answers honestly on an empty history."""

import json
import threading
import urllib.request

from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.pipeline import Pipeline
from kiseki.interfaces.api import make_server


def _pipeline() -> Pipeline:
    return Pipeline(
        InMemoryPhotoRepository(),
        InMemoryOutingRepository(),
        InMemoryAnchorRepository(),
    )


def test_lifecycle_reports_not_enough_history():
    server = make_server(_pipeline, lambda: None, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{server.server_address[1]}/lifecycle"
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["lifecycles"] is None
    finally:
        server.shutdown()
        server.server_close()
