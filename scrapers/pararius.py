"""Pararius.com scraper for Dutch rental listings."""

import json
import re
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, Listing


class ParariusScraper(BaseScraper):
    """Scraper for Pararius.com rental listings."""

    BASE_URL = "https://www.pararius.com"

    @property
    def name(self) -> str:
        return "Pararius"

    def scrape(self, location: str = "eindhoven", max_pages: int = 3) -> List[Listing]:
        """
        Scrape Pararius listings for a location.

        Args:
            location: City to search in
            max_pages: Maximum number of pages to scrape

        Returns:
            List of Listing objects
        """
        listings = []

        for page_num in range(1, max_pages + 1):
            page_url = self._build_url(location, page_num)
            print(f"Scraping {page_url}...")

            try:
                page_listings = self._scrape_page(page_url)
                listings.extend(page_listings)
                print(f"  Found {len(page_listings)} listings")

                if len(page_listings) == 0:
                    # No more listings, stop pagination
                    break

            except Exception as e:
                print(f"  Error scraping page {page_num}: {e}")
                continue

        return listings

    def _build_url(self, location: str, page_num: int = 1) -> str:
        """Build search URL for location and page number."""
        base_path = f"/apartments/{location}"
        if page_num > 1:
            return f"{self.BASE_URL}{base_path}/page-{page_num}"
        return f"{self.BASE_URL}{base_path}"

    def _scrape_page(self, url: str) -> List[Listing]:
        """Scrape a single page of listings."""
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "lxml")
        listings = []

        # Try to extract JSON-LD structured data first
        json_ld_listings = self._extract_json_ld(soup)
        if json_ld_listings:
            # Parse HTML for additional details
            listing_cards = soup.select("li.search-list__item")

            for json_data in json_ld_listings:
                # Try to find matching HTML card for extra details
                card_data = self._parse_card(listing_cards, json_data.get("url"))

                # Fetch detailed information from listing page
                print(f"    Fetching details for: {json_data.get('name', 'Unknown')}")
                detail_data = self._fetch_listing_details(json_data["url"])

                listing = Listing(
                    url=json_data["url"],
                    title=json_data.get("name", "Unknown"),
                    price=float(json_data.get("price", 0)),
                    location=card_data.get("location", "Eindhoven"),
                    size_sqm=card_data.get("size_sqm") or detail_data.get("size_sqm"),
                    rooms=card_data.get("rooms") or detail_data.get("rooms"),
                    description=detail_data.get("description"),
                    available_from=detail_data.get("available_from"),
                    landlord=detail_data.get("landlord"),
                    source="Pararius",
                    # Financial
                    service_costs=detail_data.get("service_costs"),
                    deposit=detail_data.get("deposit"),
                    # Property details
                    floor_level=detail_data.get("floor_level"),
                    energy_label=detail_data.get("energy_label"),
                    furnished_status=detail_data.get("furnished_status"),
                    # Amenities
                    has_washing_machine=detail_data.get("has_washing_machine"),
                    has_balcony=detail_data.get("has_balcony"),
                    has_garden=detail_data.get("has_garden"),
                    has_rooftop=detail_data.get("has_rooftop"),
                    has_storage=detail_data.get("has_storage"),
                    has_bike_storage=detail_data.get("has_bike_storage"),
                    has_elevator=detail_data.get("has_elevator"),
                    has_parking=detail_data.get("has_parking"),
                    # Policies
                    pets_allowed=detail_data.get("pets_allowed"),
                    smoking_allowed=detail_data.get("smoking_allowed"),
                )
                listings.append(listing)
        else:
            # Fallback: parse HTML directly
            listing_cards = soup.select("li.search-list__item")
            for card in listing_cards:
                try:
                    listing = self._parse_card_full(card)
                    if listing:
                        # Fetch detailed information from listing page
                        print(f"    Fetching details for: {listing.title}")
                        detail_data = self._fetch_listing_details(listing.url)

                        # Update listing with detail data
                        listing.description = detail_data.get("description") or listing.description
                        listing.available_from = detail_data.get("available_from") or listing.available_from
                        listing.landlord = detail_data.get("landlord")
                        listing.service_costs = detail_data.get("service_costs")
                        listing.deposit = detail_data.get("deposit")
                        listing.floor_level = detail_data.get("floor_level")
                        listing.energy_label = detail_data.get("energy_label")
                        listing.furnished_status = detail_data.get("furnished_status")
                        listing.has_washing_machine = detail_data.get("has_washing_machine")
                        listing.has_balcony = detail_data.get("has_balcony")
                        listing.has_garden = detail_data.get("has_garden")
                        listing.has_rooftop = detail_data.get("has_rooftop")
                        listing.has_storage = detail_data.get("has_storage")
                        listing.has_bike_storage = detail_data.get("has_bike_storage")
                        listing.has_elevator = detail_data.get("has_elevator")
                        listing.has_parking = detail_data.get("has_parking")
                        listing.pets_allowed = detail_data.get("pets_allowed")
                        listing.smoking_allowed = detail_data.get("smoking_allowed")

                        listings.append(listing)
                except Exception as e:
                    print(f"    Error parsing card: {e}")
                    continue

        return listings

    def _extract_json_ld(self, soup: BeautifulSoup) -> List[dict]:
        """Extract JSON-LD structured data from page."""
        script_tags = soup.find_all("script", type="application/ld+json")

        for script in script_tags:
            try:
                data = json.loads(script.string)

                # Look for ItemList with listings
                if isinstance(data, dict) and data.get("@type") == "ItemList":
                    items = data.get("itemListElement", [])
                    return [
                        {
                            "url": item["item"]["url"],
                            "name": item["item"].get("name", ""),
                            "price": item["item"]["offers"]["price"],
                        }
                        for item in items
                        if item.get("@type") == "ListItem"
                    ]
            except (json.JSONDecodeError, KeyError):
                continue

        return []

    def _parse_card(self, cards: List, url: str) -> dict:
        """Extract additional details from HTML card matching the URL."""
        for card in cards:
            card_url = card.select_one("a.listing-search-item__link")
            if card_url and url in card_url.get("href", ""):
                return self._parse_card_details(card)
        return {}

    def _parse_card_details(self, card) -> dict:
        """Parse details from a listing card."""
        details = {}

        # Extract location
        location_tag = card.select_one("div.listing-search-item__location")
        if location_tag:
            details["location"] = location_tag.get_text(strip=True)

        # Extract size and rooms from features
        features = card.select("li.illustrated-features__item")
        for feature in features:
            text = feature.get_text(strip=True)

            # Size in m²
            size_match = re.search(r"(\d+)\s*m²", text)
            if size_match:
                details["size_sqm"] = float(size_match.group(1))

            # Number of rooms
            rooms_match = re.search(r"(\d+)\s*room", text)
            if rooms_match:
                details["rooms"] = int(rooms_match.group(1))

        return details

    def _parse_card_full(self, card) -> Listing:
        """Parse a full listing from HTML card (fallback method)."""
        # Extract URL
        link = card.select_one("a.listing-search-item__link")
        if not link or not link.get("href"):
            return None

        url = urljoin(self.BASE_URL, link["href"])

        # Extract title
        title_tag = card.select_one("h2.listing-search-item__title")
        title = title_tag.get_text(strip=True) if title_tag else "Unknown"

        # Extract price
        price_tag = card.select_one("div.listing-search-item__price")
        price = 0.0
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            price_match = re.search(r"€\s*([\d,]+)", price_text)
            if price_match:
                price = float(price_match.group(1).replace(",", ""))

        # Extract location
        location_tag = card.select_one("div.listing-search-item__location")
        location = location_tag.get_text(strip=True) if location_tag else "Eindhoven"

        # Extract features
        details = self._parse_card_details(card)

        return Listing(
            url=url,
            title=title,
            price=price,
            location=location,
            size_sqm=details.get("size_sqm"),
            rooms=details.get("rooms"),
            source="Pararius",
        )

    def _fetch_listing_details(self, url: str) -> dict:
        """
        Fetch detailed information from a listing's detail page.

        Args:
            url: URL of the listing detail page

        Returns:
            Dictionary with detailed listing information
        """
        details = {}

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "lxml")

            # Get full page text for parsing
            page_text = soup.get_text()
            page_text_lower = page_text.lower()

            # Extract JSON-LD schema data
            script_tags = soup.find_all("script", type="application/ld+json")
            for script in script_tags:
                try:
                    data = json.loads(script.string)
                    # Energy label from JSON-LD
                    if isinstance(data, dict) and "energylabel" in data:
                        details["energy_label"] = data["energylabel"]
                except (json.JSONDecodeError, KeyError, AttributeError):
                    continue

            # Extract description text - try multiple selectors
            desc_text = ""

            # Try specific description containers first
            desc_containers = soup.select("div[class*='description'], section[class*='description'], article")
            for container in desc_containers:
                paragraphs = container.find_all("p", recursive=True)
                if paragraphs:
                    text = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50])
                    if text:
                        desc_text = text
                        break

            # Fallback: get all substantial paragraphs
            if not desc_text:
                all_paragraphs = soup.find_all("p")
                substantial = [p.get_text(strip=True) for p in all_paragraphs if len(p.get_text(strip=True)) > 100]
                if substantial:
                    desc_text = " ".join(substantial[:3])  # First 3 substantial paragraphs

            if desc_text:
                details["description"] = desc_text

                # Parse service costs from description
                service_match = re.search(r"service cost.*?€\s*([\d,]+)", desc_text, re.IGNORECASE)
                if service_match:
                    details["service_costs"] = float(service_match.group(1).replace(",", ""))

                # Parse deposit from description
                deposit_match = re.search(r"deposit.*?(\d+)\s*month", desc_text, re.IGNORECASE)
                if deposit_match:
                    # Estimate deposit as N months of rent (we have price from main listing)
                    pass  # Can't calculate without knowing the rent price here

                # Parse floor level from description
                floor_match = re.search(r"(\d+)(?:st|nd|rd|th)\s*floor", desc_text, re.IGNORECASE)
                if floor_match:
                    floor_num = floor_match.group(1)
                    details["floor_level"] = f"{floor_num}{floor_match.group(0).split('floor')[0].strip()[-2:]} floor"
                elif "ground floor" in desc_text.lower():
                    details["floor_level"] = "Ground floor"

                # Parse furnished status
                if "furnished" in desc_text.lower():
                    if "unfurnished" in desc_text.lower():
                        details["furnished_status"] = "unfurnished"
                    elif "soft furnished" in desc_text.lower():
                        details["furnished_status"] = "soft furnished"
                    else:
                        details["furnished_status"] = "furnished"

            # Extract landlord/agency name
            agency_links = soup.select("a[href*='makelaar'], a[href*='agent'], div.agent-name")
            if agency_links:
                details["landlord"] = agency_links[0].get_text(strip=True)

            # Parse availability from anywhere on page
            avail_match = re.search(r"available.*?:?\s*([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}|immediately|per direct)", page_text, re.IGNORECASE)
            if avail_match:
                details["available_from"] = avail_match.group(1).strip()

            # Dream features (check page text)
            details["has_balcony"] = bool(re.search(r"\bbalcon(y|ies)\b|\bbalkon\b", page_text_lower))
            details["has_garden"] = bool(re.search(r"\bgarden\b|\btuin\b", page_text_lower))
            details["has_rooftop"] = bool(re.search(r"\brooftop\b|\broof terrace\b|\bdakterras\b", page_text_lower))

            # Amenities
            details["has_washing_machine"] = bool(re.search(r"\bwashing machine\b|\bwasmachine\b|\bwasher\b", page_text_lower))
            details["has_storage"] = bool(re.search(r"\bstorage\b|\bberging\b", page_text_lower))
            details["has_bike_storage"] = bool(re.search(r"\bbike storage\b|\bbicycle storage\b|\bfietsenstalling\b", page_text_lower))
            details["has_elevator"] = bool(re.search(r"\belevator\b|\blift\b", page_text_lower))
            details["has_parking"] = bool(re.search(r"\bparking\b|\bparkeren\b|\bgarage\b", page_text_lower))

            # Policies
            if re.search(r"\bno pets\b|\bgeen huisdieren\b", page_text_lower):
                details["pets_allowed"] = False
            elif re.search(r"\bpets allowed\b|\bhuisdieren toegestaan\b", page_text_lower):
                details["pets_allowed"] = True

            if re.search(r"\bno smoking\b|\bniet roken\b|\brookvrij\b", page_text_lower):
                details["smoking_allowed"] = False
            elif re.search(r"\bsmoking allowed\b|\broken toegestaan\b", page_text_lower):
                details["smoking_allowed"] = True

        except Exception as e:
            print(f"      Error fetching details from {url}: {e}")

        return details
