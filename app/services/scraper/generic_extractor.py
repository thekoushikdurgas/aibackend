"""
Generic Content Extractor - Extracts common page elements
"""

import re
import logging
from typing import Any, Dict, List

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.utils.bs4_attrs import soup_attr_list, soup_attr_str

logger = logging.getLogger(__name__)


class GenericExtractor:
    """
    Extracts common page elements:
    - Tables (with headers and data)
    - Forms (fields, labels, validation)
    - Lists (ul/ol with nested structure)
    - Headings hierarchy
    - Contact info (emails, phones, addresses)
    - Quotes and code blocks
    """

    def __init__(self, html_content: str):
        """
        Initialize extractor with HTML content.

        Args:
            html_content: HTML content to extract from
        """
        self.soup = BeautifulSoup(html_content, "lxml")
        self.raw_html = html_content

    def extract_all(self) -> Dict[str, Any]:
        """
        Extract all generic content types.

        Returns:
            Dictionary with all extracted content
        """
        return {
            "tables": self.extract_tables(),
            "forms": self.extract_forms(),
            "lists": self.extract_lists(),
            "headings": self.extract_headings_hierarchy(),
            "contact_info": self.extract_contact_info(),
            "quotes": self.extract_quotes(),
            "code_blocks": self.extract_code_blocks(),
        }

    def extract_tables(self) -> List[Dict[str, Any]]:
        """
        Extract all HTML tables with headers and data.

        Returns:
            List of table dictionaries with:
            - headers: List of header texts
            - rows: List of row data
            - caption: Table caption if present
        """
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
                    if row_data:  # Only add non-empty rows
                        table_data["rows"].append(row_data)

                if table_data["rows"] or table_data["headers"]:
                    tables.append(table_data)

            except Exception as e:
                logger.warning(f"Error extracting table: {e}")
                continue

        return tables

    def extract_forms(self) -> List[Dict[str, Any]]:
        """
        Extract form structure and fields.

        Returns:
            List of form dictionaries with:
            - action: Form action URL
            - method: Form method (GET/POST)
            - fields: List of field information
        """
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

            except Exception as e:
                logger.warning(f"Error extracting form: {e}")
                continue

        return forms

    def extract_lists(self) -> List[Dict[str, Any]]:
        """
        Extract ordered and unordered lists with nested structure.

        Returns:
            List of list dictionaries with:
            - type: 'ul' or 'ol'
            - items: List of item texts (including nested lists)
        """
        lists = []

        for list_elem in self.soup.find_all(["ul", "ol"]):
            try:
                list_data = {
                    "type": list_elem.name,
                    "items": self._extract_list_items(list_elem),
                }

                if list_data["items"]:
                    lists.append(list_data)

            except Exception as e:
                logger.warning(f"Error extracting list: {e}")
                continue

        return lists

    def _extract_list_items(self, list_elem: Tag) -> List[Any]:
        """Recursively extract list items, handling nested lists"""
        items: List[Any] = []

        for li in list_elem.find_all("li", recursive=False):
            item_text = li.get_text(strip=True, separator=" ")

            # Check for nested lists
            nested_lists = li.find_all(["ul", "ol"], recursive=False)
            if nested_lists:
                nested_items = []
                for nested_list in nested_lists:
                    nested_items.append(
                        {
                            "type": nested_list.name,
                            "items": self._extract_list_items(nested_list),
                        }
                    )
                items.append({"text": item_text, "nested": nested_items})
            else:
                items.append(item_text)

        return items

    def extract_headings_hierarchy(self) -> Dict[str, Any]:
        """
        Extract headings with their hierarchy and nesting.

        Returns:
            Dictionary with:
            - hierarchy: List of headings with level and text
            - structure: Tree structure of headings
        """
        headings = []
        heading_elements = self.soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])

        for heading in heading_elements:
            level = int(heading.name[1])  # Extract number from h1, h2, etc.
            text = heading.get_text(strip=True)
            headings.append(
                {
                    "level": level,
                    "text": text,
                    "id": heading.get("id", ""),
                }
            )

        return {
            "headings": headings,
            "count_by_level": {
                f"h{i}": len([h for h in headings if h["level"] == i])
                for i in range(1, 7)
            },
        }

    def extract_contact_info(self) -> Dict[str, List[str]]:
        """
        Extract contact information: emails, phones, addresses.

        Returns:
            Dictionary with:
            - emails: List of email addresses
            - phones: List of phone numbers
            - addresses: List of addresses (basic extraction)
        """
        text = self.soup.get_text()

        # Extract emails
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        emails = list(set(re.findall(email_pattern, text)))

        # Extract phone numbers (various formats)
        phone_patterns = [
            r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}",  # General
            r"\(\d{3}\)\s?\d{3}[-.\s]?\d{4}",  # (123) 456-7890
            r"\d{3}[-.\s]?\d{3}[-.\s]?\d{4}",  # 123-456-7890
        ]
        phones = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            phones.extend(matches)
        phones = list(set(phones))

        # Extract addresses (basic - looks for common address patterns)
        address_pattern = r"\d+\s+[A-Za-z0-9\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Place|Pl)[\s,]+[A-Za-z\s,]+(?:[A-Z]{2})?\s+\d{5}"
        addresses = list(set(re.findall(address_pattern, text, re.IGNORECASE)))

        return {
            "emails": emails,
            "phones": phones,
            "addresses": addresses,
        }

    def extract_quotes(self) -> List[Dict[str, str]]:
        """
        Extract blockquotes and citations.

        Returns:
            List of quote dictionaries with:
            - text: Quote text
            - citation: Citation if present
        """
        quotes = []

        for blockquote in self.soup.find_all("blockquote"):
            try:
                quote_text = blockquote.get_text(strip=True)

                # Look for citation
                citation = None
                cite_elem = blockquote.find("cite")
                if cite_elem:
                    citation = cite_elem.get_text(strip=True)
                else:
                    cite_attr = soup_attr_str(blockquote.get("cite"))
                    citation = cite_attr if cite_attr else ""

                quotes.append(
                    {
                        "text": quote_text,
                        "citation": citation,
                    }
                )

            except Exception as e:
                logger.warning(f"Error extracting quote: {e}")
                continue

        return quotes

    def extract_code_blocks(self) -> List[Dict[str, str]]:
        """
        Extract code blocks (pre/code elements).

        Returns:
            List of code block dictionaries with:
            - code: Code content
            - language: Language if specified
        """
        code_blocks = []

        for pre in self.soup.find_all("pre"):
            try:
                code_elem = pre.find("code")
                if code_elem:
                    code_text = code_elem.get_text()
                    class_tokens = soup_attr_list(code_elem.get("class"))
                    language: str | None
                    if class_tokens:
                        lang_class = [
                            c for c in class_tokens if c.startswith("language-")
                        ]
                        language = (
                            lang_class[0].replace("language-", "")
                            if lang_class
                            else None
                        )
                    else:
                        language = None
                else:
                    code_text = pre.get_text()
                    language = None

                code_blocks.append(
                    {
                        "code": code_text,
                        "language": language if language is not None else "",
                    }
                )

            except Exception as e:
                logger.warning(f"Error extracting code block: {e}")
                continue

        return code_blocks
