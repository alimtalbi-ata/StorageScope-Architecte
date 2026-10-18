"""Bounded, deterministic pagination for StorageScope maintenance diagnostics.

Pure Python; safe for Tkinter integration. No filesystem access or mutation.
Auteur : Abdelhalim Talbi.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

MAX_PAGE_SIZE = 500
DEFAULT_PAGE_SIZE = 100

@dataclass(frozen=True)
class Page:
    rows: tuple[Mapping[str, Any], ...]
    total: int
    page: int
    page_size: int
    pages: int
    has_previous: bool
    has_next: bool

def paginate_diagnostics(
    rows: Iterable[Mapping[str, Any]],
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> Page:
    """Return one bounded page. Reject invalid input instead of silently truncating."""
    if type(page) is not int or page < 1:
        raise ValueError("page must be a positive integer")
    if type(page_size) is not int or not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValueError(f"page_size must be in [1, {MAX_PAGE_SIZE}]")
    if isinstance(rows, (str, bytes)):
        raise TypeError("rows must contain mappings")
    materialized = tuple(rows)
    if any(not isinstance(row, Mapping) for row in materialized):
        raise TypeError("every diagnostic row must be a mapping")
    total = len(materialized)
    pages = max(1, (total + page_size - 1) // page_size)
    if page > pages:
        raise ValueError(f"page {page} exceeds {pages} available pages")
    start = (page - 1) * page_size
    return Page(
        rows=materialized[start:start + page_size],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        has_previous=page > 1,
        has_next=page < pages,
    )
