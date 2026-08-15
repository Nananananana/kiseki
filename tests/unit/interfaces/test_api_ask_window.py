"""/ask validates its since/until window."""

import json
import threading
import urllib.error
import urllib.request

from kiseki.interfaces.api import make_server


def test_a_bad_since_is_refused():
    server = make_server(
        lambda: None,
        lambda: None,
        host="127.0.0.1",
        port=0,
        ask_factory=lambda question, language, since, until: None,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{server.server_address[1]}/ask?q=ramen&since=bad"
            ) as response:
                json.loads(response.read().decode("utf-8"))
            raise AssertionError("expected 400")
        except urllib.error.HTTPError as error:
            assert error.code == 400
    finally:
        server.shutdown()
        server.server_close()
