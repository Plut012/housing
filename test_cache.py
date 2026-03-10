#!/usr/bin/env python3
"""Quick test of caching functionality."""

from cache import ListingCache
from scrapers.base import Listing

# Create test listing
test_listing = Listing(
    url="https://example.com/test",
    title="Test Apartment",
    price=1200.0,
    location="Eindhoven",
    size_sqm=50.0,
    rooms=2,
    source="test",
    description="A nice test apartment",
    has_balcony=True,
    has_garden=False,
)

# Initialize cache
cache = ListingCache()

# First check - should return None (not in cache)
print("1. Checking cache (should be empty)...")
result = cache.get_cached_analysis(test_listing)
print(f"   Result: {result}")

# Store analysis
print("\n2. Storing analysis in cache...")
cache.store_analysis(
    test_listing,
    score=85.5,
    is_gem=True,
    reasoning="This is a great apartment because it has a balcony!"
)
print("   ✓ Stored")

# Check again - should return cached result
print("\n3. Checking cache again (should have result)...")
result = cache.get_cached_analysis(test_listing)
print(f"   Result: {result}")

# Modify listing (change price)
print("\n4. Modifying listing (price change)...")
test_listing.price = 1250.0
result = cache.get_cached_analysis(test_listing)
print(f"   Result (should be None due to change): {result}")

# Show stats
print("\n5. Cache statistics:")
stats = cache.get_stats()
print(f"   Total listings: {stats['total_listings']}")
print(f"   Total gems: {stats['total_gems']}")
print(f"   Average score: {stats['avg_score']}")

cache.close()

print("\n✓ Cache test completed!")
print(f"\nCache database created at: cache/listings.db")
print("You can inspect it with: sqlite3 cache/listings.db")
