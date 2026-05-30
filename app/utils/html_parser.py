"""
HTML parsing utilities for page analysis
"""

from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from .bs4_attrs import soup_attr_str, tag_attr_str
from .helpers import sanitize_text, truncate_text


class HTMLParser:
    """
    HTML parsing utility class for extracting and analyzing page content
    """

    def __init__(self, html: str):
        """Initialize parser with HTML content"""
        self.soup = BeautifulSoup(html, "lxml")
        self.raw_html = html

    def get_title(self) -> Optional[str]:
        """Extract page title"""
        title_tag = self.soup.find("title")
        return title_tag.get_text(strip=True) if title_tag else None

    def get_meta_tags(self) -> List[Dict[str, str]]:
        """Extract all meta tags"""
        meta_tags = []
        for meta in self.soup.find_all("meta"):
            meta_dict = {}
            if tag_attr_str(meta, "name"):
                meta_dict["name"] = tag_attr_str(meta, "name")
            if tag_attr_str(meta, "property"):
                meta_dict["property"] = tag_attr_str(meta, "property")
            if tag_attr_str(meta, "content"):
                meta_dict["content"] = tag_attr_str(meta, "content")
            if tag_attr_str(meta, "http-equiv"):
                meta_dict["http_equiv"] = tag_attr_str(meta, "http-equiv")
            if meta_dict:
                meta_tags.append(meta_dict)
        return meta_tags

    def get_meta_description(self) -> Optional[str]:
        """Extract meta description"""
        meta = self.soup.find("meta", attrs={"name": "description"})
        if meta:
            return tag_attr_str(meta, "content") or None

        # Try og:description as fallback
        og_meta = self.soup.find("meta", attrs={"property": "og:description"})
        if og_meta:
            return tag_attr_str(og_meta, "content") or None

        return None

    def get_headings(self) -> Dict[str, List[str]]:
        """Extract all headings (h1-h6)"""
        headings = {}
        for i in range(1, 7):
            tag = f"h{i}"
            headings[tag] = [h.get_text(strip=True) for h in self.soup.find_all(tag)]
        return headings

    def get_links(self) -> List[Dict[str, str]]:
        """Extract all links"""
        links = []
        for a in self.soup.find_all("a", href=True):
            links.append(
                {
                    "href": tag_attr_str(a, "href"),
                    "text": a.get_text(strip=True)[:100],
                    "rel": tag_attr_str(a, "rel"),
                    "target": tag_attr_str(a, "target"),
                }
            )
        return links

    def get_images(self) -> List[Dict[str, Any]]:
        """Extract all images"""
        images = []
        for img in self.soup.find_all("img"):
            images.append(
                {
                    "src": tag_attr_str(img, "src"),
                    "alt": tag_attr_str(img, "alt"),
                    "title": tag_attr_str(img, "title"),
                    "width": tag_attr_str(img, "width"),
                    "height": tag_attr_str(img, "height"),
                    "loading": tag_attr_str(img, "loading"),
                    "has_alt": bool(tag_attr_str(img, "alt")),
                }
            )
        return images

    def get_text_content(self, max_length: int = 50000) -> str:
        """Extract clean text content from page"""
        # Remove script and style elements
        for element in self.soup(["script", "style", "noscript", "iframe"]):
            element.decompose()

        # Get text
        text = self.soup.get_text(separator=" ", strip=True)

        # Clean and truncate
        text = sanitize_text(text)
        return truncate_text(text, max_length)

    def get_structure_stats(self) -> Dict[str, int]:
        """Get structural statistics about the page"""
        return {
            "total_elements": len(self.soup.find_all()),
            "links": len(self.soup.find_all("a")),
            "images": len(self.soup.find_all("img")),
            "videos": len(self.soup.find_all("video")),
            "forms": len(self.soup.find_all("form")),
            "inputs": len(self.soup.find_all("input")),
            "buttons": len(self.soup.find_all("button")),
            "tables": len(self.soup.find_all("table")),
            "lists": len(self.soup.find_all(["ul", "ol"])),
            "paragraphs": len(self.soup.find_all("p")),
            "divs": len(self.soup.find_all("div")),
            "spans": len(self.soup.find_all("span")),
            "scripts": len(self.soup.find_all("script")),
            "stylesheets": len(self.soup.find_all("link", rel="stylesheet")),
        }

    def get_semantic_elements(self) -> Dict[str, Any]:
        """Analyze semantic HTML5 elements"""
        return {
            "has_header": bool(self.soup.find("header")),
            "has_nav": bool(self.soup.find("nav")),
            "has_main": bool(self.soup.find("main")),
            "has_footer": bool(self.soup.find("footer")),
            "has_aside": bool(self.soup.find("aside")),
            "article_count": len(self.soup.find_all("article")),
            "section_count": len(self.soup.find_all("section")),
            "figure_count": len(self.soup.find_all("figure")),
        }

    def get_seo_data(self) -> Dict[str, Any]:
        """Extract SEO-relevant data"""
        title = self.get_title()
        description = self.get_meta_description()
        headings = self.get_headings()

        # Get canonical URL
        canonical = self.soup.find("link", rel="canonical")
        canonical_url = tag_attr_str(canonical, "href") or None if canonical else None

        # Get robots meta
        robots = self.soup.find("meta", attrs={"name": "robots"})
        robots_content = tag_attr_str(robots, "content") or None if robots else None

        # Get Open Graph data
        og_data: Dict[str, str] = {}
        for meta in self.soup.find_all("meta"):
            prop = tag_attr_str(meta, "property")
            if not prop.startswith("og:"):
                continue
            key = prop.replace("og:", "")
            val = tag_attr_str(meta, "content")
            if key:
                og_data[key] = val

        # Get Twitter Card data
        twitter_data: Dict[str, str] = {}
        for meta in self.soup.find_all("meta"):
            name = tag_attr_str(meta, "name")
            if not name.startswith("twitter:"):
                continue
            key = name.replace("twitter:", "")
            val = tag_attr_str(meta, "content")
            if key:
                twitter_data[key] = val

        return {
            "title": title,
            "title_length": len(title) if title else 0,
            "description": description,
            "description_length": len(description) if description else 0,
            "h1_count": len(headings.get("h1", [])),
            "h1_texts": headings.get("h1", []),
            "canonical_url": canonical_url,
            "robots": robots_content,
            "open_graph": og_data,
            "twitter_card": twitter_data,
            "has_favicon": bool(
                self.soup.find("link", rel=lambda x: x and "icon" in x.lower())
            ),
        }

    def analyze_images_seo(self) -> Dict[str, Any]:
        """Analyze images for SEO"""
        images = self.get_images()

        images_with_alt = [img for img in images if img.get("has_alt")]
        images_without_alt = [img for img in images if not img.get("has_alt")]

        return {
            "total_images": len(images),
            "images_with_alt": len(images_with_alt),
            "images_without_alt": len(images_without_alt),
            "alt_coverage_percent": (
                round(len(images_with_alt) / len(images) * 100, 1) if images else 100
            ),
            "missing_alt_images": [img.get("src") for img in images_without_alt[:10]],
        }

    def get_word_count(self) -> int:
        """Get word count of page content"""
        text = self.get_text_content()
        return len(text.split())

    def extract_structured_data(self) -> List[Dict[str, Any]]:
        """Extract JSON-LD structured data"""
        structured_data = []
        for script in self.soup.find_all("script", type="application/ld+json"):
            try:
                import json

                raw = script.string
                if not raw:
                    continue
                data = json.loads(raw)
                structured_data.append(data)
            except (json.JSONDecodeError, TypeError):
                pass
        return structured_data

    def extract_tables(self) -> List[Dict[str, Any]]:
        """Extract all HTML tables with headers and data"""
        tables = []
        for table in self.soup.find_all("table"):
            try:
                table_data: Dict[str, Any] = {
                    "headers": [],
                    "rows": [],
                    "caption": None,
                }

                # Extract caption
                caption = table.find("caption")
                if caption:
                    table_data["caption"] = caption.get_text(strip=True)

                # Extract headers (th elements)
                header_row = table.find("tr")
                if header_row:
                    headers = header_row.find_all(["th", "td"])
                    table_data["headers"] = [h.get_text(strip=True) for h in headers]

                # Extract data rows
                rows = table.find_all("tr")[1:] if header_row else table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    row_data = [cell.get_text(strip=True) for cell in cells]
                    if row_data:
                        table_data["rows"].append(row_data)

                if table_data["rows"] or table_data["headers"]:
                    tables.append(table_data)
            except Exception:
                continue
        return tables

    def extract_forms(self) -> List[Dict[str, Any]]:
        """Extract form structure and fields"""
        forms = []
        for form in self.soup.find_all("form"):
            try:
                form_data: Dict[str, Any] = {
                    "action": soup_attr_str(form.get("action")),
                    "method": soup_attr_str(form.get("method"), "GET").upper(),
                    "fields": [],
                }

                # Extract input fields
                inputs = form.find_all(["input", "textarea", "select"])
                for input_elem in inputs:
                    field_info: Dict[str, Any] = {
                        "type": soup_attr_str(
                            input_elem.get("type"), input_elem.name or ""
                        ),
                        "name": soup_attr_str(input_elem.get("name")),
                        "id": soup_attr_str(input_elem.get("id")),
                        "label": None,
                        "placeholder": soup_attr_str(input_elem.get("placeholder")),
                        "required": input_elem.has_attr("required"),
                    }

                    # Try to find associated label
                    if field_info["id"]:
                        label = self.soup.find("label", {"for": field_info["id"]})
                        if label:
                            field_info["label"] = label.get_text(strip=True)

                    # For textarea and select, get options
                    if input_elem.name == "textarea":
                        field_info["value"] = input_elem.get_text(strip=True)
                    elif input_elem.name == "select":
                        options = input_elem.find_all("option")
                        field_info["options"] = [
                            {
                                "value": soup_attr_str(opt.get("value")),
                                "text": opt.get_text(strip=True),
                            }
                            for opt in options
                        ]
                    else:
                        field_info["value"] = soup_attr_str(input_elem.get("value"))

                    form_data["fields"].append(field_info)

                if form_data["fields"]:
                    forms.append(form_data)
            except Exception:
                continue
        return forms

    def extract_lists(self) -> List[Dict[str, Any]]:
        """Extract ordered and unordered lists with nested structure"""
        lists = []

        def extract_list_items(list_elem):
            items = []
            for li in list_elem.find_all("li", recursive=False):
                item_text = li.get_text(strip=True, separator=" ")
                nested_lists = li.find_all(["ul", "ol"], recursive=False)
                if nested_lists:
                    nested_items = []
                    for nested_list in nested_lists:
                        nested_items.append(
                            {
                                "type": nested_list.name,
                                "items": extract_list_items(nested_list),
                            }
                        )
                    items.append({"text": item_text, "nested": nested_items})
                else:
                    items.append(item_text)
            return items

        for list_elem in self.soup.find_all(["ul", "ol"]):
            try:
                list_data = {
                    "type": list_elem.name,
                    "items": extract_list_items(list_elem),
                }
                if list_data["items"]:
                    lists.append(list_data)
            except Exception:
                continue
        return lists

    def detect_page_type(self) -> Dict[str, Any]:
        """Detect page type using heuristics (basic version, full detection in PageDetector)"""
        html_lower = self.raw_html.lower()

        # Check for course indicators
        course_indicators = [
            "curriculum",
            "syllabus",
            "lecture",
            "instructor",
            "enroll",
        ]
        if any(indicator in html_lower for indicator in course_indicators):
            return {"page_type": "course", "confidence": 65.0}

        # Check for product indicators
        product_indicators = ["add-to-cart", "buy-now", "shopping-cart", "add-to-bag"]
        if any(indicator in html_lower for indicator in product_indicators):
            return {"page_type": "product", "confidence": 65.0}

        # Check for article indicators
        article_indicators = [
            "article-content",
            "post-content",
            "author",
            "publish-date",
        ]
        if any(indicator in html_lower for indicator in article_indicators):
            return {"page_type": "article", "confidence": 65.0}

        # Check structured data
        structured_data = self.extract_structured_data()
        for data in structured_data:
            if isinstance(data, dict):
                items = data.get("@graph", [data])
                for item in items:
                    if isinstance(item, dict):
                        item_type = item.get("@type", "")
                        if isinstance(item_type, str):
                            item_type = item_type.split("/")[-1]
                        if item_type == "Course":
                            return {"page_type": "course", "confidence": 85.0}
                        elif item_type == "Product":
                            return {"page_type": "product", "confidence": 85.0}
                        elif item_type == "Article":
                            return {"page_type": "article", "confidence": 85.0}

        return {"page_type": "generic", "confidence": 50.0}

    def get_full_analysis(self) -> Dict[str, Any]:
        """Get comprehensive page analysis"""
        return {
            "title": self.get_title(),
            "meta_description": self.get_meta_description(),
            "meta_tags": self.get_meta_tags(),
            "headings": self.get_headings(),
            "structure_stats": self.get_structure_stats(),
            "semantic_elements": self.get_semantic_elements(),
            "seo_data": self.get_seo_data(),
            "image_analysis": self.analyze_images_seo(),
            "word_count": self.get_word_count(),
            "links_count": len(self.get_links()),
            "structured_data": self.extract_structured_data(),
            "tables": self.extract_tables(),
            "forms": self.extract_forms(),
            "lists": self.extract_lists(),
        }
