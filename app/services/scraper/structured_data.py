"""
Structured Data Parser - Extracts JSON-LD, microdata, and schema.org data
Similar to the Udemy scraper's structured data extraction
"""

import json
import logging
from typing import Dict, List, Any
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class StructuredDataParser:
    """
    Parses structured data from web pages:
    - JSON-LD (application/ld+json)
    - Microdata (itemscope, itemtype, itemprop)
    - RDFa (vocab, typeof, property)
    - Schema.org entities
    """

    def __init__(self, html_content: str):
        """
        Initialize parser with HTML content.

        Args:
            html_content: HTML content to parse
        """
        self.soup = BeautifulSoup(html_content, "lxml")
        self.raw_html = html_content

    def extract_all(self) -> Dict[str, Any]:
        """
        Extract all types of structured data.

        Returns:
            Dictionary with:
            - json_ld: List of JSON-LD objects
            - microdata: List of microdata objects
            - rdfa: List of RDFa objects
            - schema_org: Combined schema.org entities
        """
        return {
            "json_ld": self.extract_json_ld(),
            "microdata": self.extract_microdata(),
            "rdfa": self.extract_rdfa(),
            "schema_org": self.extract_schema_org(),
            "open_graph": self.extract_open_graph(),
            "twitter_card": self.extract_twitter_card(),
        }

    def extract_json_ld(self) -> List[Dict[str, Any]]:
        """
        Extract JSON-LD structured data.
        Similar to Udemy scraper's extract_json_ld method.

        Returns:
            List of parsed JSON-LD objects
        """
        json_ld_data = []

        # Find all JSON-LD script tags
        json_ld_scripts = self.soup.find_all("script", type="application/ld+json")

        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)

                # Handle both single objects and @graph arrays
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict) and "@graph" in data:
                    items = data["@graph"]
                else:
                    items = [data]

                json_ld_data.extend(items)

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON-LD: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error processing JSON-LD: {e}")
                continue

        return json_ld_data

    def extract_microdata(self) -> List[Dict[str, Any]]:
        """
        Extract microdata (itemscope, itemtype, itemprop).

        Returns:
            List of microdata objects
        """
        microdata_items = []

        # Find all elements with itemscope
        items = self.soup.find_all(attrs={"itemscope": True})

        for item in items:
            try:
                item_data = {"itemtype": item.get("itemtype", ""), "properties": {}}

                # Get all properties
                props = item.find_all(attrs={"itemprop": True})
                for prop in props:
                    prop_name = prop.get("itemprop", "")
                    prop_value = prop.get("content") or prop.get_text(strip=True)

                    if prop_name:
                        if prop_name in item_data["properties"]:
                            # Handle multiple values
                            if not isinstance(item_data["properties"][prop_name], list):
                                item_data["properties"][prop_name] = [
                                    item_data["properties"][prop_name]
                                ]
                            item_data["properties"][prop_name].append(prop_value)
                        else:
                            item_data["properties"][prop_name] = prop_value

                microdata_items.append(item_data)

            except Exception as e:
                logger.warning(f"Error extracting microdata: {e}")
                continue

        return microdata_items

    def extract_rdfa(self) -> List[Dict[str, Any]]:
        """
        Extract RDFa data (vocab, typeof, property).

        Returns:
            List of RDFa objects
        """
        rdfa_items = []

        # Find elements with typeof
        items = self.soup.find_all(attrs={"typeof": True})

        for item in items:
            try:
                item_data = {
                    "typeof": item.get("typeof", ""),
                    "vocab": item.get("vocab", ""),
                    "properties": {},
                }

                # Get all properties
                props = item.find_all(attrs={"property": True})
                for prop in props:
                    prop_name = prop.get("property", "")
                    prop_value = prop.get("content") or prop.get_text(strip=True)

                    if prop_name:
                        item_data["properties"][prop_name] = prop_value

                rdfa_items.append(item_data)

            except Exception as e:
                logger.warning(f"Error extracting RDFa: {e}")
                continue

        return rdfa_items

    def extract_schema_org(self) -> Dict[str, Any]:
        """
        Extract and organize Schema.org entities from all structured data.

        Returns:
            Dictionary organized by entity type
        """
        schema_org: Dict[str, List[Dict[str, Any]]] = {}

        # Get JSON-LD data
        json_ld = self.extract_json_ld()

        for item in json_ld:
            if isinstance(item, dict):
                item_type = item.get("@type", "")
                if isinstance(item_type, str):
                    # Extract type name
                    type_name = (
                        item_type.split("/")[-1] if "/" in item_type else item_type
                    )

                    if type_name not in schema_org:
                        schema_org[type_name] = []

                    schema_org[type_name].append(item)

        return schema_org

    def extract_open_graph(self) -> Dict[str, str]:
        """
        Extract Open Graph metadata.

        Returns:
            Dictionary of Open Graph properties
        """
        og_data = {}

        for meta in self.soup.find_all(
            "meta", property=lambda x: x and x.startswith("og:")
        ):
            key = meta.get("property", "").replace("og:", "")
            value = meta.get("content", "")
            if key and value:
                og_data[key] = value

        return og_data

    def extract_twitter_card(self) -> Dict[str, str]:
        """
        Extract Twitter Card metadata.

        Returns:
            Dictionary of Twitter Card properties
        """
        twitter_data = {}

        for meta in self.soup.find_all(
            "meta", attrs={"name": lambda x: x and x.startswith("twitter:")}
        ):
            key = meta.get("name", "").replace("twitter:", "")
            value = meta.get("content", "")
            if key and value:
                twitter_data[key] = value

        return twitter_data

    def extract_course_data(self) -> Dict[str, Any]:
        """
        Extract course-specific data (like Udemy scraper).
        Looks for Course, CourseInstance, or LearningResource types.

        Returns:
            Dictionary with course information
        """
        course_data: Dict[str, Any] = {
            "title": None,
            "url": None,
            "instructors": [],
            "rating": None,
            "rating_count": None,
            "description": None,
            "price": None,
            "duration": None,
            "language": None,
            "curriculum": [],
            "requirements": [],
            "learning_objectives": [],
        }

        json_ld = self.extract_json_ld()

        for item in json_ld:
            if isinstance(item, dict):
                item_type = item.get("@type", "")
                if isinstance(item_type, str):
                    item_type = item_type.split("/")[-1]

                # Check if it's a course-related type
                if item_type in ["Course", "CourseInstance", "LearningResource"]:
                    # Extract course title
                    if "name" in item:
                        course_data["title"] = item["name"]

                    # Extract URL
                    if "@id" in item:
                        course_data["url"] = item["@id"]
                    elif "url" in item:
                        course_data["url"] = item["url"]

                    # Extract instructors
                    if "author" in item or "instructor" in item:
                        authors = item.get("author") or item.get("instructor", [])
                        if isinstance(authors, list):
                            course_data["instructors"] = [
                                a.get("name", "")
                                for a in authors
                                if isinstance(a, dict)
                            ]
                        elif isinstance(authors, dict):
                            course_data["instructors"] = [authors.get("name", "")]

                    # Extract ratings
                    if "aggregateRating" in item:
                        rating_data = item["aggregateRating"]
                        if isinstance(rating_data, dict):
                            course_data["rating"] = float(
                                rating_data.get("ratingValue", 0)
                            )
                            course_data["rating_count"] = int(
                                rating_data.get("ratingCount", 0)
                            )

                    # Extract description
                    if "description" in item:
                        course_data["description"] = item["description"]

                    # Extract duration
                    if "timeRequired" in item:
                        course_data["duration"] = item["timeRequired"]

                    # Extract price
                    if "offers" in item:
                        offers = item["offers"]
                        if isinstance(offers, list) and len(offers) > 0:
                            offers = offers[0]
                        if isinstance(offers, dict):
                            price = offers.get("price", "")
                            currency = offers.get("priceCurrency", "USD")
                            if price:
                                course_data["price"] = f"{currency} {price}"

                    # Extract learning objectives
                    if "teaches" in item:
                        teaches = item["teaches"]
                        if isinstance(teaches, list):
                            course_data["learning_objectives"] = teaches
                        elif isinstance(teaches, str):
                            course_data["learning_objectives"] = [teaches]

        return course_data

    def extract_product_data(self) -> Dict[str, Any]:
        """
        Extract product-specific data from structured data.

        Returns:
            Dictionary with product information
        """
        product_data: Dict[str, Any] = {
            "name": None,
            "description": None,
            "price": None,
            "currency": None,
            "availability": None,
            "brand": None,
            "sku": None,
            "rating": None,
            "rating_count": None,
            "images": [],
        }

        json_ld = self.extract_json_ld()

        for item in json_ld:
            if isinstance(item, dict):
                item_type = item.get("@type", "")
                if isinstance(item_type, str):
                    item_type = item_type.split("/")[-1]

                if item_type == "Product":
                    # Extract product name
                    if "name" in item:
                        product_data["name"] = item["name"]

                    # Extract description
                    if "description" in item:
                        product_data["description"] = item["description"]

                    # Extract price
                    if "offers" in item:
                        offers = item["offers"]
                        if isinstance(offers, list) and len(offers) > 0:
                            offers = offers[0]
                        if isinstance(offers, dict):
                            product_data["price"] = offers.get("price", "")
                            product_data["currency"] = offers.get(
                                "priceCurrency", "USD"
                            )
                            product_data["availability"] = offers.get(
                                "availability", ""
                            )

                    # Extract brand
                    if "brand" in item:
                        brand = item["brand"]
                        if isinstance(brand, dict):
                            product_data["brand"] = brand.get("name", "")
                        elif isinstance(brand, str):
                            product_data["brand"] = brand

                    # Extract SKU
                    if "sku" in item:
                        product_data["sku"] = item["sku"]

                    # Extract ratings
                    if "aggregateRating" in item:
                        rating_data = item["aggregateRating"]
                        if isinstance(rating_data, dict):
                            product_data["rating"] = float(
                                rating_data.get("ratingValue", 0)
                            )
                            product_data["rating_count"] = int(
                                rating_data.get("ratingCount", 0)
                            )

                    # Extract images
                    if "image" in item:
                        images = item["image"]
                        if isinstance(images, list):
                            product_data["images"] = images
                        elif isinstance(images, str):
                            product_data["images"] = [images]

        return product_data
