from typing import Any

import pytest
import requests

from vnpy.trader import engine as engine_module
from vnpy.trader.engine import WecomEngine
from vnpy.trader.wecom import (
    WecomError,
    mask_webhook_url,
    normalize_webhook_url,
    send_text,
)


WEBHOOK_KEY: str = "12345678-abcd-efgh-ijkl-123456789012"
WEBHOOK_URL: str = (
    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
    f"?key={WEBHOOK_KEY}"
)


class FakeResponse:
    def __init__(self, data: Any, status_error: Exception | None = None) -> None:
        self.data: Any = data
        self.status_error: Exception | None = status_error

    def raise_for_status(self) -> None:
        if self.status_error:
            raise self.status_error

    def json(self) -> Any:
        return self.data


class DummyMainEngine:
    def __init__(self) -> None:
        self.logs: list[tuple[str, str]] = []

    def write_log(self, msg: str, source: str = "MainEngine") -> None:
        self.logs.append((msg, source))


def test_normalize_webhook_url() -> None:
    assert normalize_webhook_url(WEBHOOK_KEY) == WEBHOOK_URL
    assert normalize_webhook_url(WEBHOOK_URL) == WEBHOOK_URL

    with pytest.raises(WecomError):
        normalize_webhook_url(
            f"https://example.com/cgi-bin/webhook/send?key={WEBHOOK_KEY}"
        )

    with pytest.raises(WecomError):
        normalize_webhook_url(
            "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        )


def test_mask_webhook_url() -> None:
    masked: str = mask_webhook_url(WEBHOOK_URL)

    assert WEBHOOK_KEY not in masked
    assert "1234...9012" in masked


def test_send_text_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse({"errcode": 0, "errmsg": "ok"})

    monkeypatch.setattr("vnpy.trader.wecom.requests.post", fake_post)

    send_text(WEBHOOK_URL, "test message")

    assert captured["url"] == WEBHOOK_URL
    assert captured["json"] == {
        "msgtype": "text",
        "text": {"content": "test message"},
    }
    assert captured["timeout"] == 30.0


def test_send_text_business_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        return FakeResponse({"errcode": 93000, "errmsg": "invalid webhook"})

    monkeypatch.setattr("vnpy.trader.wecom.requests.post", fake_post)

    with pytest.raises(WecomError, match="93000"):
        send_text(WEBHOOK_URL, "test message")


def test_send_text_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        raise requests.exceptions.Timeout

    monkeypatch.setattr("vnpy.trader.wecom.requests.post", fake_post)

    with pytest.raises(WecomError, match="超时"):
        send_text(WEBHOOK_URL, "test message")


def test_engine_configure_and_send_multiple_groups(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved: dict[str, Any] = {}
    main_engine: DummyMainEngine = DummyMainEngine()

    monkeypatch.setattr(engine_module, "load_json", lambda filename: {})
    monkeypatch.setattr(
        engine_module,
        "save_json",
        lambda filename, data: saved.update(data),
    )
    monkeypatch.setattr(WecomEngine, "activate", lambda self: None)
    monkeypatch.setattr(WecomEngine, "deactivate", lambda self: None)

    engine: WecomEngine = WecomEngine(main_engine, object())  # type: ignore[arg-type]
    second_key: str = "87654321-abcd-efgh-ijkl-210987654321"
    engine.configure([WEBHOOK_URL, second_key, WEBHOOK_URL], 0)

    assert len(engine.webhook_urls) == 2
    assert saved == {
        "webhook_urls": engine.webhook_urls,
        "send_interval": 0,
    }
    assert engine.send_wecom("first")
    engine.queue.put("second")

    sent: list[tuple[str, str]] = []

    def fake_send(webhook_url: str, text: str) -> None:
        sent.append((webhook_url, text))
        if len(sent) == 2:
            engine.active = False

    monkeypatch.setattr(engine_module, "send_wecom_text", fake_send)

    engine.active = True
    engine.run()

    assert [item[0] for item in sent] == engine.webhook_urls
    assert all(item[1] == "first\nsecond" for item in sent)
