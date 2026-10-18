"""Bounded pagination for StorageScope diagnostic tables.

Sequence inputs are sliced without copying the full collection; generic iterables
are materialized once. Filtering should be applied before pagination.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500

@dataclass(frozen=True)
class Page:
    rows: tuple[Mapping[str, Any], ...]
    total: int
    page: int
    page_size: int
    pages: int
    has_previous: bool
    has_next: bool

def paginate_diagnostics(rows: Iterable[Mapping[str, Any]], page: int = 1,
                         page_size: int = DEFAULT_PAGE_SIZE) -> Page:
    """Page read-only diagnostics; reject malformed page settings and selected rows."""
    if type(page) is not int or page < 1:
        raise ValueError("page must be a positive integer")
    if type(page_size) is not int or not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValueError(f"page_size must be in [1, {MAX_PAGE_SIZE}]")
    if isinstance(rows, (str, bytes, Mapping)):
        raise TypeError("rows must be an iterable of mappings")
    # Avoid O(N) copying on every page when the UI already holds a list or tuple.
    source = rows if isinstance(rows, Sequence) else tuple(rows)
    total = len(source)
    pages = max(1, (total + page_size - 1) // page_size)
    if page > pages:
        raise ValueError(f"page {page} exceeds {pages} available pages")
    start = (page - 1) * page_size
    selected = tuple(source[start:start + page_size])
    if any(not isinstance(item, Mapping) for item in selected):
        raise TypeError("selected diagnostic rows must be mappings")
    return Page(selected, total, page, page_size, pages,
                page > 1, page < pages)
