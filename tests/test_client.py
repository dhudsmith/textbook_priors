"""The client's retry policy and request shape, with a fake transport: no network, no key."""
import numpy as np
import pytest

from priors import llm


class Err(Exception):
    def __init__(self, status):
        super().__init__(f"HTTP {status}")
        self.status_code = status


class APIConnectionError(Exception):
    pass


def test_backoff_retries_retryable_errors_then_succeeds():
    calls, sleeps = [], []
    outcomes = [Err(429), Err(503), "ok"]

    def send():
        calls.append(1)
        r = outcomes[len(calls) - 1]
        if isinstance(r, Exception):
            raise r
        return r

    result, attempts = llm.call_with_backoff(send, http_retries=5, backoff_s=1.0, sleep=sleeps.append, rng=lambda: 0.5)
    assert result == "ok" and attempts == 3 and len(sleeps) == 2
    assert sleeps[1] == 2 * sleeps[0]                       # exponential


def test_non_retryable_status_raises_at_once():
    sleeps = []

    def send():
        raise Err(400)

    with pytest.raises(Err):
        llm.call_with_backoff(send, http_retries=5, backoff_s=1.0, sleep=sleeps.append)
    assert sleeps == []


def test_exhausted_retries_raise_the_last_error():
    sleeps, n = [], []

    def send():
        n.append(1)
        raise Err(502)

    with pytest.raises(Err):
        llm.call_with_backoff(send, http_retries=3, backoff_s=0.1, sleep=sleeps.append, rng=lambda: 0.5)
    assert len(n) == 3 and len(sleeps) == 2


def test_retryable_classification():
    assert llm.is_retryable(Err(429)) and llm.is_retryable(Err(500)) and llm.is_retryable(Err(504))
    assert not llm.is_retryable(Err(401)) and not llm.is_retryable(Err(404)) and not llm.is_retryable(ValueError("x"))
    assert llm.is_retryable(APIConnectionError("boom"))


def test_backoff_is_capped():
    sleeps = []
    k = [0]

    def send():
        k[0] += 1
        if k[0] < 8:
            raise Err(503)
        return 1

    llm.call_with_backoff(send, http_retries=10, backoff_s=30.0, sleep=sleeps.append, rng=lambda: 0.5, max_backoff_s=120.0)
    assert max(sleeps) <= 120.0 and len(sleeps) == 7


def test_chat_request_shape(cfg):
    req = llm.chat_request("m", "SYS", "USER", "data:image/png;base64,AAAA", cfg["vlm"])
    assert req["model"] == "m" and req["temperature"] == 0.0 and req["max_tokens"] == cfg["vlm"]["max_tokens"]
    assert req["messages"][0] == {"role": "system", "content": "SYS"}
    parts = req["messages"][1]["content"]
    assert parts[0] == {"type": "text", "text": "USER"} and parts[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert req["response_format"] == {"type": "json_object"}
    assert req["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    quiet = dict(cfg["vlm"], json_mode=None, reasoning_extra_body={})
    req2 = llm.chat_request("m", "SYS", "USER", "u", quiet)
    assert "response_format" not in req2 and "extra_body" not in req2


class _Msg:
    def __init__(self, content, reasoning_content=None):
        self.content, self.reasoning_content = content, reasoning_content


class _Resp:
    def __init__(self, content, reasoning=None, model="served/x"):
        self.choices = [type("C", (), {"message": _Msg(content, reasoning), "finish_reason": "stop"})()]
        self.model = model
        self.usage = type("U", (), {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})()


class _Client:
    def __init__(self, resp):
        self.chat = type("Chat", (), {})()
        self.chat.completions = type("Comp", (), {"create": lambda self_, **kw: resp})()


def test_complete_reads_content_or_falls_back_to_reasoning_content(cfg):
    req = llm.chat_request("m", "S", "U", "u", cfg["vlm"])
    r = llm.complete(_Client(_Resp('{"a": 1}')), req, cfg["vlm"], sleep=lambda s: None)
    assert r["text"] == '{"a": 1}' and r["served_model"] == "served/x" and r["usage"]["total_tokens"] == 15 and r["http_attempts"] == 1
    r = llm.complete(_Client(_Resp("", reasoning='{"b": 2}')), req, cfg["vlm"], sleep=lambda s: None)
    assert r["text"] == '{"b": 2}' and r["content"] == "" and r["reasoning_content"] == '{"b": 2}'
    r = llm.complete(_Client(_Resp(None, reasoning=None)), req, cfg["vlm"], sleep=lambda s: None)
    assert r["text"] is None


def test_image_data_url_encodes_png():
    pytest.importorskip("PIL")
    grey = np.zeros((224, 224), np.uint8)
    rgb = np.zeros((224, 224, 3), np.uint8)
    for img in (grey, rgb):
        url = llm.image_data_url(img)
        assert url.startswith("data:image/png;base64,iVBOR")       # PNG magic, base64


def test_read_key(tmp_path):
    with pytest.raises(FileNotFoundError):
        llm.read_key(tmp_path / "missing")
    (tmp_path / "empty").write_text("\n")
    with pytest.raises(ValueError):
        llm.read_key(tmp_path / "empty")
    (tmp_path / "key").write_text("abc\n")
    assert llm.read_key(tmp_path / "key") == "abc"
