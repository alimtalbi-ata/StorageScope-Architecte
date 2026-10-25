"""Strict, auditable UTF-8 decoding for GitHub Actions job-log downloads.

The decoder never repairs corrupt bytes silently. It also records the hash and
size of the exact text payload selected from either a raw log response or a ZIP.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import hashlib
import io
import zipfile
from typing import Any


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_github_actions_job_log_payload(downloaded: bytes) -> tuple[str, dict[str, Any]]:
    """Decode one raw or ZIP-wrapped job log, rejecting ambiguity and bad UTF-8.

    A ZIP response must contain exactly one non-directory ``.txt`` or ``.log``
    member. Content uses strict UTF-8 (with an optional UTF-8 BOM); invalid byte
    sequences and NUL characters are rejected before any test classification.
    """
    if not isinstance(downloaded, bytes):
        raise TypeError("downloaded job-log payload must be bytes")
    if not downloaded:
        raise ValueError("downloaded job-log payload is empty")

    archive = io.BytesIO(downloaded)
    is_zip = zipfile.is_zipfile(archive)
    member_name: str | None = None
    payload = downloaded
    if is_zip:
        try:
            with zipfile.ZipFile(archive, "r") as zf:
                candidates = [
                    info for info in zf.infolist()
                    if not info.is_dir()
                    and info.filename.lower().endswith((".txt", ".log"))
                    and not info.filename.replace("\\", "/").startswith("__MACOSX/")
                ]
                if len(candidates) != 1:
                    raise ValueError(
                        "expected exactly one text log member in downloaded archive; found "
                        + str(len(candidates))
                    )
                member_name = candidates[0].filename
                payload = zf.read(candidates[0])
        except zipfile.BadZipFile as exc:
            raise ValueError("downloaded job-log archive is malformed") from exc

    try:
        text = payload.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "GitHub Actions job log is not valid UTF-8; refusing lossy decoding "
            f"(byte_offset={exc.start}, reason={exc.reason}, "
            f"payload_sha256={_sha256(payload)})"
        ) from exc
    if "\x00" in text:
        raise ValueError(
            "decoded job log contains NUL characters; refusing probable binary input "
            f"(payload_sha256={_sha256(payload)})"
        )

    metadata: dict[str, Any] = {
        "decoder": "utf-8-sig-strict",
        "transport": "zip_member" if is_zip else "raw",
        "download_byte_count": len(downloaded),
        "download_sha256": _sha256(downloaded),
        "payload_byte_count": len(payload),
        "payload_sha256": _sha256(payload),
        "utf8_bom_stripped": payload.startswith(b"\xef\xbb\xbf"),
        "lossy_decoding_used": False,
        "decoded_character_count": len(text),
    }
    if member_name is not None:
        metadata["zip_member"] = member_name
    return text, metadata
