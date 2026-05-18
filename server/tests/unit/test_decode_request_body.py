"""Sanity for UTF-8 / GBK fallback path."""

from __future__ import annotations

import pytest

from app.core.encoding import decode_request_body


def test_decode_utf8():
    assert decode_request_body("hello".encode("utf-8")) == "hello"


def test_decode_gbk_fallback():
    text = "测试中文"
    body = text.encode("gbk")
    assert decode_request_body(body) == text


def test_decode_failure_raises():
    junk = b"\xff\xfe\x00\x00\xff\xfe"
    with pytest.raises(UnicodeDecodeError):
        decode_request_body(junk)
