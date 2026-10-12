"""Flask runs each request in its own asyncio.run(); long-lived LLMs must survive that."""

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from tools.llm_config import create_default_llm

COMPLETION = {
    "id": "chatcmpl-test", "object": "chat.completion", "created": 0, "model": "gpt-4o-mini",
    "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "ok"}}],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}


class _FakeOpenAI(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # keep-alive, like the real API

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        body = json.dumps(COMPLETION).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def fake_openai(monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeOpenAI)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("OPENAI_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    yield
    server.shutdown()


def test_llm_works_across_fresh_event_loops(fake_openai):
    llm = create_default_llm()
    for _ in range(3):
        assert asyncio.run(llm.ainvoke("hola")).content == "ok"
