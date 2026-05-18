"""Helpers for decoding OC-originated request bodies (UTF-8 / GBK fallback)."""

from __future__ import annotations

from app.core.logging import logger


def decode_request_body(body: bytes) -> str:
    """OC sometimes encodes bodies as GBK. Try UTF-8 first, then fallback."""

    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = body.decode("gbk")
            logger.debug("UTF-8 decode failed, used GBK fallback")
            return text
        except UnicodeDecodeError as exc:
            logger.error("Both UTF-8 and GBK decode failed: %s", exc)
            raise UnicodeDecodeError(
                "utf-8",
                body,
                0,
                len(body),
                "Body decodable neither as UTF-8 nor as GBK",
            ) from exc
