"""Claude-powered listing analyzer."""

import os
from dataclasses import dataclass
from typing import List

from anthropic import Anthropic

from config import Requirements
from scrapers.base import Listing


@dataclass
class AnalysisResult:
    """Result of listing analysis."""

    listing: Listing
    score: float  # 0-100
    reasoning: str
    is_gem: bool  # True if it exceeds expectations

    def __str__(self) -> str:
        gem_indicator = "💎 GEM" if self.is_gem else ""
        return (
            f"{gem_indicator}\n"
            f"Score: {self.score}/100\n"
            f"{self.listing}\n"
            f"\nAnalysis:\n{self.reasoning}\n"
        )


class ListingAnalyzer:
    """Analyze rental listings using Claude API."""

    def __init__(self, api_key: str | None = None):
        """
        Initialize analyzer with Anthropic API client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    def analyze(self, listing: Listing, requirements: Requirements) -> AnalysisResult:
        """
        Analyze a single listing against requirements.

        Args:
            listing: The rental listing to analyze
            requirements: User's requirements

        Returns:
            AnalysisResult with score and reasoning
        """
        prompt = self._build_prompt(listing, requirements)

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse response
        content = response.content[0].text
        score, reasoning, is_gem = self._parse_response(content)

        return AnalysisResult(
            listing=listing,
            score=score,
            reasoning=reasoning,
            is_gem=is_gem,
        )

    def analyze_batch(
        self, listings: List[Listing], requirements: Requirements
    ) -> List[AnalysisResult]:
        """
        Analyze multiple listings.

        Args:
            listings: List of rental listings
            requirements: User's requirements

        Returns:
            List of AnalysisResults sorted by score (highest first)
        """
        results = []

        for i, listing in enumerate(listings, 1):
            print(f"Analyzing listing {i}/{len(listings)}: {listing.title}")
            try:
                result = self.analyze(listing, requirements)
                results.append(result)
            except Exception as e:
                print(f"  Error analyzing: {e}")
                continue

        # Sort by score, highest first
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _build_prompt(self, listing: Listing, requirements: Requirements) -> str:
        """Build analysis prompt for Claude."""
        return f"""You are a rental property analyst. Analyze this listing against the user's requirements, practical considerations, and dream features.

# User's Requirements

## Strict Requirements
- Budget: €{requirements.min_budget or 0} - €{requirements.max_budget}
- Location: {requirements.location}

## Preferences
{requirements.preferences}

## Practical Considerations
{requirements.considerations}

## Dream Features
{requirements.dreams}

# Listing to Analyze

**Title**: {listing.title}
**Price**: €{listing.price}/month{f" + €{listing.service_costs}/month servicekosten = €{listing.price + listing.service_costs}/month total" if listing.service_costs else ""}
**Location**: {listing.location}
**Size**: {listing.size_sqm}m² ({listing.rooms} rooms)
**Floor**: {listing.floor_level or 'Not specified'}
**Energy Label**: {listing.energy_label or 'Not specified'}
**Furnished**: {listing.furnished_status or 'Not specified'}
**Deposit**: €{listing.deposit} if listing.deposit else 'Not specified'
**Available from**: {listing.available_from or 'Not specified'}
**Landlord/Agency**: {listing.landlord or 'Not specified'}

**Features & Amenities**:
- Washing machine: {"✅ Yes" if listing.has_washing_machine else "❌ No" if listing.has_washing_machine is False else "❓ Unknown"}
- Storage: {"✅ Yes" if listing.has_storage else "❌ No" if listing.has_storage is False else "❓ Unknown"}
- Bike storage: {"✅ Yes" if listing.has_bike_storage else "❌ No" if listing.has_bike_storage is False else "❓ Unknown"}
- Elevator: {"✅ Yes" if listing.has_elevator else "❌ No" if listing.has_elevator is False else "❓ Unknown"}
- Parking: {"✅ Yes" if listing.has_parking else "❌ No" if listing.has_parking is False else "❓ Unknown"}

**DREAM FEATURES** (highly valuable):
- 🌟 Balcony: {"✅ YES!" if listing.has_balcony else "❌ No" if listing.has_balcony is False else "❓ Unknown"}
- 🌟 Garden (tuin): {"✅ YES!" if listing.has_garden else "❌ No" if listing.has_garden is False else "❓ Unknown"}
- 🌟 Rooftop/terrace: {"✅ YES!" if listing.has_rooftop else "❌ No" if listing.has_rooftop is False else "❓ Unknown"}

**Policies**:
- Pets: {"✅ Allowed" if listing.pets_allowed else "❌ Not allowed" if listing.pets_allowed is False else "❓ Unknown"}
- Smoking: {"✅ Allowed" if listing.smoking_allowed else "❌ Not allowed" if listing.smoking_allowed is False else "❓ Unknown"}

{f"**Description**: {listing.description[:500]}..." if listing.description else "**Description**: Not provided"}

**URL**: {listing.url}

# Task

1. Check if this listing meets the STRICT requirements (budget and location)
2. Evaluate how well it matches the user's preferences
3. Assess practical considerations (utilities, landlord reputation, nearby amenities, etc.)
4. Check for any DREAM features - these are rare but highly valuable
5. Identify if this is a "gem" - something that exceptionally matches requirements OR has dream features
6. Provide a match score from 0-100

**Scoring guidance:**
- Budget match: baseline
- Good preferences match: 60-75
- Strong preferences + good practical considerations: 75-85
- Above + at least one dream feature: 85-95
- Multiple dream features or exceptional overall match: 95-100

Return your analysis in this EXACT format:

SCORE: [number 0-100]
GEM: [yes/no]
REASONING:
[Your detailed reasoning covering:
- Budget/location fit
- Which preferences it matches/misses
- Practical considerations (what to watch for or ask about)
- Any dream features present (highlight these!)
- Why this score and gem status]
"""

    def _parse_response(self, content: str) -> tuple[float, str, bool]:
        """
        Parse Claude's response to extract score, reasoning, and gem status.

        Returns:
            (score, reasoning, is_gem)
        """
        lines = content.strip().split("\n")

        score = 0.0
        is_gem = False
        reasoning_lines = []
        in_reasoning = False

        for line in lines:
            line_stripped = line.strip()

            if line_stripped.startswith("SCORE:"):
                try:
                    score = float(line_stripped.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    score = 0.0

            elif line_stripped.startswith("GEM:"):
                gem_value = line_stripped.split(":", 1)[1].strip().lower()
                is_gem = gem_value in ["yes", "true", "1"]

            elif line_stripped.startswith("REASONING:"):
                in_reasoning = True

            elif in_reasoning:
                reasoning_lines.append(line)

        reasoning = "\n".join(reasoning_lines).strip()

        return score, reasoning, is_gem
