"""
WeCom group robot webhook client.
"""

from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import requests

from .locale import _


DEFAULT_BASE_URL: str = "https://qyapi.weixin.qq.com"
WEBHOOK_PATH: str = "/cgi-bin/webhook/send"
REQUEST_TIMEOUT: float = 30.0


class WecomError(Exception):
    """WeCom webhook request failed."""


def normalize_webhook_url(value: str) -> str:
    """
    Validate and normalize a WeCom group robot webhook URL or key.
    """
    value = value.strip()
    if not value:
        raise WecomError(_("企业微信 Webhook 不能为空"))

    if "://" not in value:
        key: str = value
    else:
        parsed = urlsplit(value)
        try:
            port: int | None = parsed.port
        except ValueError as exc:
            raise WecomError(_("企业微信 Webhook 地址无效")) from exc

        if (
            parsed.scheme.lower() != "https"
            or parsed.hostname != "qyapi.weixin.qq.com"
            or parsed.path.rstrip("/") != WEBHOOK_PATH
            or parsed.username
            or parsed.password
            or port not in (None, 443)
        ):
            raise WecomError(_("请输入企业微信群机器人的官方 Webhook 地址"))

        keys: list[str] = parse_qs(parsed.query).get("key", [])
        key = keys[0].strip() if keys else ""

    if not key or any(char.isspace() for char in key):
        raise WecomError(_("企业微信 Webhook 缺少有效的 key"))

    query: str = urlencode({"key": key})
    return urlunsplit(("https", "qyapi.weixin.qq.com", WEBHOOK_PATH, query, ""))


def mask_webhook_url(value: str) -> str:
    """Mask the secret key in a webhook URL for logs."""
    try:
        normalized: str = normalize_webhook_url(value)
        parsed = urlsplit(normalized)
        key: str = parse_qs(parsed.query)["key"][0]
    except (KeyError, WecomError):
        return _("无效 Webhook")

    if len(key) <= 8:
        masked: str = "*" * len(key)
    else:
        masked = f"{key[:4]}...{key[-4:]}"

    query: str = urlencode({"key": masked})
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, ""))


def send_text(webhook_url: str, text: str) -> None:
    """Send a text message through a WeCom group robot."""
    url: str = normalize_webhook_url(webhook_url)
    payload: dict[str, Any] = {
        "msgtype": "text",
        "text": {
            "content": text,
        },
    }

    try:
        response: requests.Response = requests.post(
            url,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise WecomError(_("企业微信请求超时")) from exc
    except requests.RequestException as exc:
        raise WecomError(_("企业微信 HTTP 请求失败：{}").format(exc)) from exc

    try:
        data: Any = response.json()
    except ValueError as exc:
        raise WecomError(_("企业微信返回了非 JSON 响应")) from exc

    if not isinstance(data, dict):
        raise WecomError(_("企业微信返回格式无效"))

    errcode: Any = data.get("errcode", 0)
    if errcode:
        raise WecomError(
            _("企业微信错误 errcode={} errmsg={}").format(
                errcode,
                data.get("errmsg", ""),
            )
        )
