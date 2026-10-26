"""Strict UTF-8 decoding for historical unittest subprocess output.

Raw bytes must be persisted before decoding. This module never substitutes or
normalizes invalid bytes, and callers can bind a decoded result to its SHA-256.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import hashlib
from typing import Any


def decode_subprocess_output(payload: bytes) -> tuple[str, dict[str, Any]]:
    """Decode captured output as strict UTF-8 without silently repairing bytes.

    Empty output is valid bytes but will fail the caller's unittest-summary
    contract. NUL-bearing output and malformed UTF-8 are rejected because they
    are not safe text evidence for the historical test parser.
    """
    if not isinstance(payload, bytes):
        raise TypeError("captured subprocess output must be raw bytes")

    digest = hashlib.sha256(payload).hexdigest()
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "captured subprocess output is not valid UTF-8; refusing lossy decoding "
            f"(byte_offset={exc.start}, reason={exc.reason}, payload_sha256={digest})"
        ) from exc

    nul_index = text.find("\x00")
    if nul_index >= 0:
        byte_offset = len(text[:nul_index].encode("utf-8"))
        raise ValueError(
            "captured subprocess output contains NUL; refusing probable binary input "
            f"(byte_offset={byte_offset}, payload_sha256={digest})"
        )

    return text, {
        "decoder": "utf-8-strict",
        "payload_byte_count": len(payload),
        "payload_sha256": digest,
        "lossy_decoding_used": False,
        "nul_bytes_rejected": False,
        "utf8_bom_present": payload.startswith(b"\xef\xbb\xbf"),
    }
