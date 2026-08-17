"""Local HTTP interface.

Answers what the command line answers, as JSON over loopback, so a
thin client (a phone, a desktop shell) can ask without linking the
library. Standard library only: the server carries no more machinery
than the local, single-owner use it exists for. Reading is all it
does -- a GET changes nothing, and served payloads blur coordinates
unless raw=true is asked for explicitly. See ADR-0026.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

from kiseki.application.asking import Answer
from kiseki.application.narrative import tell
from kiseki.application.pipeline import Pipeline
from kiseki.interfaces.payloads import (
    answer_payload,
    comparison_payload,
    discovery_payload,
    insights_payload,
    lifecycle_payload,
    profile_payload,
    report_payload,
    trend_payload,
)
from kiseki.ports.models import (
    LanguageModel,
    ModelRefusedError,
    ModelUnavailableError,
)

DEFAULT_HOST = "127.0.0.1"
"""Loopback, deliberately: reaching the server from another device
takes an explicit --host, never a default."""

DEFAULT_PORT = 8765

LANGUAGES = ("ja", "en")

AskFactory = Callable[[str, str, "datetime | None", "datetime | None"], "Answer"]
"""Question, language, since, until -> one Answer."""


def _moment(text: str) -> datetime | None:
    """An ISO date or datetime, made timezone aware; empty means None."""
    if not text:
        return None
    moment = datetime.fromisoformat(text)
    return moment if moment.tzinfo is not None else moment.astimezone()


class ApiServer(ThreadingHTTPServer):
    """Carries the factories the handler composes each answer from.

    A pipeline is built per request because SQLite connections belong
    to the thread that opened them, and every request runs in its own.
    """

    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        pipeline_factory: Callable[[], Pipeline],
        language_model_factory: Callable[[], LanguageModel],
        ask_factory: AskFactory | None = None,
    ) -> None:
        super().__init__(address, _Handler)
        self.pipeline_factory = pipeline_factory
        self.language_model_factory = language_model_factory
        self.ask_factory: AskFactory | None = ask_factory


def make_server(
    pipeline_factory: Callable[[], Pipeline],
    language_model_factory: Callable[[], LanguageModel],
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    ask_factory: AskFactory | None = None,
) -> ApiServer:
    """Build a bound server without starting it. Port 0 picks freely."""
    return ApiServer((host, port), pipeline_factory, language_model_factory, ask_factory)


def serve(
    pipeline_factory: Callable[[], Pipeline],
    language_model_factory: Callable[[], LanguageModel],
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    ask_factory: AskFactory | None = None,
) -> None:
    """Serve until interrupted."""
    server = make_server(pipeline_factory, language_model_factory, host, port, ask_factory)
    print(f"kiseki listening on http://{host}:{server.server_address[1]} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


class _Handler(BaseHTTPRequestHandler):
    server: ApiServer

    def do_GET(self) -> None:
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        raw = query.get("raw", ["false"])[0].lower() in ("true", "1")
        try:
            self._answer(url.path, query, blur=not raw)
        except (ModelRefusedError, ModelUnavailableError) as error:
            self._send(503, {"error": str(error)})

    def do_POST(self) -> None:
        self._send(405, {"error": "only GET is served"})

    def _answer(self, path: str, query: dict[str, list[str]], blur: bool) -> None:
        if path == "/health":
            self._send(200, {"status": "ok"})
        elif path == "/report":
            report = self.server.pipeline_factory().report()
            self._send(200, report_payload(report, blur=blur))
        elif path == "/profile":
            profile = self.server.pipeline_factory().profile(keep=False)
            self._send(200, profile_payload(profile, blur=blur))
        elif path == "/trend":
            trends = self.server.pipeline_factory().trend()
            if trends is None:
                self._send(200, {"trends": None, "reason": "not enough history"})
            else:
                self._send(200, trend_payload(trends, blur=blur))
        elif path == "/tell":
            language = query.get("lang", ["ja"])[0]
            if language not in LANGUAGES:
                self._send(400, {"error": f"lang must be one of: {', '.join(LANGUAGES)}"})
                return
            pipeline = self.server.pipeline_factory()
            story = tell(
                pipeline.profile(keep=False),
                pipeline.report(),
                self.server.language_model_factory(),
                language=language,
            )
            self._send(200, {"story": story})
        elif path == "/compare":
            comparison = self.server.pipeline_factory().compare()
            if comparison is None:
                self._send(200, {"entries": None, "reason": "not enough history"})
            else:
                self._send(200, comparison_payload(comparison, blur=blur))
        elif path == "/discover":
            feed = self.server.pipeline_factory().discover()
            if feed is None:
                self._send(200, {"discoveries": None, "reason": "not enough history"})
            else:
                self._send(200, discovery_payload(feed, blur=blur))
        elif path == "/insights":
            findings = self.server.pipeline_factory().insights()
            if findings is None:
                self._send(200, {"insights": None, "reason": "not enough history"})
            else:
                self._send(200, insights_payload(findings, blur=blur))
        elif path == "/lifecycle":
            lifecycle = self.server.pipeline_factory().lifecycle()
            if lifecycle is None:
                self._send(200, {"lifecycles": None, "reason": "not enough history"})
            else:
                self._send(200, lifecycle_payload(lifecycle, blur=blur))
        elif path == "/ask":
            question = query.get("q", [""])[0].strip()
            if not question:
                self._send(400, {"error": "q is required"})
                return
            language = query.get("lang", ["ja"])[0]
            if language not in LANGUAGES:
                self._send(400, {"error": f"lang must be one of: {', '.join(LANGUAGES)}"})
                return
            if self.server.ask_factory is None:
                self._send(404, {"error": "not found"})
                return
            try:
                since = _moment(query.get("since", [""])[0])
                until = _moment(query.get("until", [""])[0])
            except ValueError:
                self._send(400, {"error": "since/until must be ISO dates"})
                return
            self._send(
                200, answer_payload(self.server.ask_factory(question, language, since, until))
            )
        else:
            self._send(404, {"error": "not found"})

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
