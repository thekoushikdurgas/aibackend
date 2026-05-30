"""BeautifulSoup Tag.get() helpers — attributes may be str, multi-value, or None."""

from __future__ import annotations

from typing import Any

from bs4.element import Tag


def soup_attr_str(val: Any, default: str = "") -> str:
    """Normalize Tag attribute values to a single string."""
    if val is None:
        return default
    if isinstance(val, str):
        return val
    if isinstance(val, (list, tuple)):
        joined = " ".join(soup_attr_str(x, "") for x in val).strip()
        return joined if joined else default
    return str(val)


def soup_attr_list(val: Any) -> list[str]:
    """Normalize class-like multi-value attributes to a list of strings."""
    if val is None:
        return []
    if isinstance(val, str):
        return val.split()
    if isinstance(val, (list, tuple)):
        return [str(x) for x in val]
    return [str(val)]


def tag_attr_str(el: Any, attr: str, default: str = "") -> str:
    """Read a named attribute from a BeautifulSoup Tag; return *default* for non-tags."""
    if isinstance(el, Tag):
        return soup_attr_str(el.get(attr), default)
    return default
