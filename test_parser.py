#!/usr/bin/env python3
"""Test the Pararius detail page parser."""

from scrapers.pararius import ParariusScraper

scraper = ParariusScraper()

# Test with the Woenselse Markt listing
url = "https://www.pararius.com/apartment-for-rent/eindhoven/f5ee71fb/woenselse-markt"

print(f"Testing detail page parser on: {url}\n")
details = scraper._fetch_listing_details(url)

print("Extracted details:")
for key, value in details.items():
    print(f"  {key}: {value}")
