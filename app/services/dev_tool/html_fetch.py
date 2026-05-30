"""Safe HTTP fetch and HTML asset extraction for Website Analyzer."""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.utils.bs4_attrs import tag_attr_str

logger = logging.getLogger(__name__)

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
FETCH_TIMEOUT = 25.0
USER_AGENT = "DurgasAI-DevTool/1.0 (+https://thekoushikdurgas.ai)"


class FetchPageError(Exception):
    """Raised when a page cannot be fetched safely."""


def _hostname_resolves_to_blocked_ip(hostname: str) -> bool:
    if not hostname:
        return True
    lowered = hostname.lower().strip(".")
    if lowered in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            return True
    return False


def _validate_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise FetchPageError("Only http and https URLs are allowed.")
    if not parsed.netloc:
        raise FetchPageError("Invalid URL.")
    host = parsed.hostname or ""
    if _hostname_resolves_to_blocked_ip(host):
        raise FetchPageError("URL host is not allowed.")
    return url.strip()


async def fetch_page_for_analysis(url: str) -> str:
    """Fetch HTML for a public URL with SSRF guards."""
    safe_url = _validate_url(url)
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    charset = "utf-8"
    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT,
        follow_redirects=True,
        max_redirects=5,
    ) as client:
        async with client.stream("GET", safe_url, headers=headers) as response:
            response.raise_for_status()
            if response.charset_encoding:
                charset = response.charset_encoding
            chunks: List[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise FetchPageError("Response exceeds maximum allowed size.")
                chunks.append(chunk)
    raw = b"".join(chunks)
    try:
        return raw.decode(charset, errors="replace")
    except Exception:
        return raw.decode("utf-8", errors="replace")


def _abs_url(base: str, path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    try:
        return urljoin(base, path)
    except Exception:
        return path


def parse_page_assets(html: str, page_url: str) -> Dict[str, Any]:
    """Extract assets and page metadata from HTML (mirrors reference client logic)."""
    soup = BeautifulSoup(html, "html.parser")
    base = page_url

    images: List[str] = []
    for el in soup.find_all("img", src=True):
        u = _abs_url(base, el.get("src"))
        if u:
            images.append(u)

    videos: List[str] = []
    for el in soup.find_all(["video", "source"], src=True):
        u = _abs_url(base, el.get("src"))
        if u:
            videos.append(u)

    scripts: List[str] = []
    for el in soup.find_all("script", src=True):
        u = _abs_url(base, el.get("src"))
        if u:
            scripts.append(u)

    styles: List[str] = []
    for el in soup.find_all("link", rel=True, href=True):
        rel = " ".join(el.get("rel") or []).lower()
        if "stylesheet" in rel:
            u = _abs_url(base, el.get("href"))
            if u:
                styles.append(u)

    internal_link_urls: List[str] = []
    external_links = 0
    seen_internal: set[str] = set()
    parsed_base = urlparse(base)

    for a in soup.find_all("a", href=True):
        href = a.get("href") or ""
        if href.startswith("#") or href.startswith("javascript:"):
            continue
        abs_href = _abs_url(base, href)
        if not abs_href:
            continue
        try:
            link_host = urlparse(abs_href).netloc
        except Exception:
            continue
        if link_host and link_host != parsed_base.netloc:
            external_links += 1
        else:
            if abs_href not in seen_internal:
                seen_internal.add(abs_href)
                internal_link_urls.append(abs_href)

    title_el = soup.find("title")
    title = title_el.get_text(strip=True) if title_el else ""
    desc_el = soup.find("meta", attrs={"name": "description"})
    description = ""
    description = tag_attr_str(desc_el, "content")

    return {
        "html": html,
        "assets": {
            "images": sorted(set(images)),
            "videos": sorted(set(videos)),
            "scripts": sorted(set(scripts)),
            "styles": sorted(set(styles)),
        },
        "pageInfo": {
            "title": title,
            "description": description,
            "internalLinks": len(internal_link_urls),
            "externalLinks": external_links,
            "internalLinkUrls": internal_link_urls[:50],
        },
    }
