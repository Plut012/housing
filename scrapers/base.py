"""Base scraper interface for rental listing websites."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Listing:
    """Standardized rental listing data."""

    url: str
    title: str
    price: float
    location: str
    size_sqm: Optional[float] = None
    rooms: Optional[int] = None
    available_from: Optional[str] = None
    description: Optional[str] = None
    landlord: Optional[str] = None
    image_urls: Optional[List[str]] = None
    source: str = ""

    # Financial details
    service_costs: Optional[float] = None  # Monthly servicekosten
    deposit: Optional[float] = None

    # Property details
    floor_level: Optional[str] = None  # e.g., "2nd floor", "ground floor"
    energy_label: Optional[str] = None  # A, B, C, etc.
    furnished_status: Optional[str] = None  # "furnished", "soft furnished", "unfurnished"

    # Amenities and features
    has_washing_machine: Optional[bool] = None
    has_balcony: Optional[bool] = None
    has_garden: Optional[bool] = None
    has_rooftop: Optional[bool] = None
    has_storage: Optional[bool] = None
    has_bike_storage: Optional[bool] = None
    has_elevator: Optional[bool] = None
    has_parking: Optional[bool] = None

    # Policies
    pets_allowed: Optional[bool] = None
    smoking_allowed: Optional[bool] = None

    def __str__(self) -> str:
        """Human-readable representation."""
        parts = [
            f"{self.title}",
            f"  Price: €{self.price:.2f}/month",
        ]

        if self.service_costs:
            parts.append(f"  Service costs: €{self.service_costs:.2f}/month")
            parts.append(f"  Total: €{self.price + self.service_costs:.2f}/month")

        parts.extend([
            f"  Location: {self.location}",
            f"  Size: {self.size_sqm}m² | Rooms: {self.rooms}",
        ])

        if self.floor_level:
            parts.append(f"  Floor: {self.floor_level}")

        if self.energy_label:
            parts.append(f"  Energy: {self.energy_label}")

        if self.furnished_status:
            parts.append(f"  Furnished: {self.furnished_status}")

        parts.append(f"  Available: {self.available_from or 'Not specified'}")

        # Dream features
        dreams = []
        if self.has_balcony:
            dreams.append("balcony")
        if self.has_garden:
            dreams.append("garden")
        if self.has_rooftop:
            dreams.append("rooftop")

        if dreams:
            parts.append(f"  ✨ Features: {', '.join(dreams)}")

        parts.append(f"  URL: {self.url}")

        return "\n".join(parts)


class BaseScraper(ABC):
    """Base class for website scrapers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Scraper name/identifier."""
        pass

    @abstractmethod
    def scrape(self, location: str = "eindhoven") -> List[Listing]:
        """
        Scrape rental listings for a given location.

        Args:
            location: City or area to search

        Returns:
            List of Listing objects
        """
        pass
