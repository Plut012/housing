"""SQLite-based caching for listing analysis results."""

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from scrapers.base import Listing


class ListingCache:
    """Cache for storing and retrieving listing analysis results."""

    def __init__(self, db_path: str = "cache/listings.db"):
        """
        Initialize cache with SQLite database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                url TEXT PRIMARY KEY,
                source TEXT,
                title TEXT,
                price REAL,
                location TEXT,
                size_sqm REAL,
                rooms INTEGER,
                description TEXT,
                features TEXT,

                -- Analysis results
                score REAL,
                is_gem INTEGER,
                reasoning TEXT,

                -- Metadata
                first_seen TEXT,
                last_seen TEXT,
                last_analyzed TEXT,
                listing_hash TEXT,

                -- Version tracking
                schema_version INTEGER DEFAULT 1
            )
        """)

        # Create indexes for common queries
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_last_seen ON listings(last_seen)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_score ON listings(score DESC)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_is_gem ON listings(is_gem)"
        )

        self.conn.commit()

    def get_cached_analysis(
        self, listing: Listing, max_age_days: int = 30
    ) -> Optional[dict]:
        """
        Get cached analysis for a listing if available and valid.

        Args:
            listing: The listing to check cache for
            max_age_days: Maximum age of cache entry in days

        Returns:
            Dictionary with 'score', 'is_gem', 'reasoning' if cache valid, None otherwise
        """
        listing_hash = self._hash_listing(listing)

        cursor = self.conn.execute(
            """
            SELECT score, is_gem, reasoning, last_analyzed, listing_hash
            FROM listings
            WHERE url = ?
        """,
            (listing.url,),
        )

        result = cursor.fetchone()
        if not result:
            return None

        # Check if listing content has changed
        if result["listing_hash"] != listing_hash:
            return None  # Listing changed, re-analyze

        # Check if cache is stale
        last_analyzed = datetime.fromisoformat(result["last_analyzed"])
        if datetime.now() - last_analyzed > timedelta(days=max_age_days):
            return None  # Cache expired

        return {
            "score": result["score"],
            "is_gem": bool(result["is_gem"]),
            "reasoning": result["reasoning"],
        }

    def store_analysis(
        self, listing: Listing, score: float, is_gem: bool, reasoning: str
    ):
        """
        Store or update analysis result for a listing.

        Args:
            listing: The listing that was analyzed
            score: Match score (0-100)
            is_gem: Whether it's a gem
            reasoning: Analysis reasoning text
        """
        listing_hash = self._hash_listing(listing)
        now = datetime.now().isoformat()

        # Serialize features to JSON
        features = self._serialize_features(listing)

        # Check if listing exists
        cursor = self.conn.execute(
            "SELECT first_seen FROM listings WHERE url = ?", (listing.url,)
        )
        existing = cursor.fetchone()
        first_seen = existing["first_seen"] if existing else now

        self.conn.execute(
            """
            INSERT INTO listings (
                url, source, title, price, location, size_sqm, rooms,
                description, features,
                score, is_gem, reasoning,
                first_seen, last_seen, last_analyzed, listing_hash, schema_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(url) DO UPDATE SET
                title = excluded.title,
                price = excluded.price,
                size_sqm = excluded.size_sqm,
                rooms = excluded.rooms,
                description = excluded.description,
                features = excluded.features,
                score = excluded.score,
                is_gem = excluded.is_gem,
                reasoning = excluded.reasoning,
                last_seen = excluded.last_seen,
                last_analyzed = excluded.last_analyzed,
                listing_hash = excluded.listing_hash
        """,
            (
                listing.url,
                listing.source,
                listing.title,
                listing.price,
                listing.location,
                listing.size_sqm,
                listing.rooms,
                listing.description,
                features,
                score,
                int(is_gem),
                reasoning,
                first_seen,
                now,
                now,
                listing_hash,
            ),
        )

        self.conn.commit()

    def mark_seen(self, active_urls: list[str]):
        """
        Mark listings as seen in current scrape.

        Args:
            active_urls: List of URLs found in current scrape
        """
        if not active_urls:
            return

        now = datetime.now().isoformat()
        placeholders = ",".join("?" * len(active_urls))

        self.conn.execute(
            f"""
            UPDATE listings
            SET last_seen = ?
            WHERE url IN ({placeholders})
        """,
            [now] + active_urls,
        )

        self.conn.commit()

    def get_disappeared_gems(self, days: int = 7) -> list[dict]:
        """
        Find gems that haven't been seen recently.

        Args:
            days: Number of days since last seen

        Returns:
            List of dictionaries with listing info
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        cursor = self.conn.execute(
            """
            SELECT url, title, price, score, last_seen
            FROM listings
            WHERE is_gem = 1 AND last_seen < ?
            ORDER BY score DESC
        """,
            (cutoff,),
        )

        return [
            {
                "url": row["url"],
                "title": row["title"],
                "price": row["price"],
                "score": row["score"],
                "last_seen": row["last_seen"],
            }
            for row in cursor.fetchall()
        ]

    def get_stats(self) -> dict:
        """Get cache statistics."""
        cursor = self.conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_gem = 1 THEN 1 ELSE 0 END) as gems,
                AVG(score) as avg_score,
                COUNT(DISTINCT source) as sources
            FROM listings
        """
        )

        row = cursor.fetchone()
        return {
            "total_listings": row["total"],
            "total_gems": row["gems"],
            "avg_score": round(row["avg_score"], 1) if row["avg_score"] else 0,
            "sources": row["sources"],
        }

    def _hash_listing(self, listing: Listing) -> str:
        """
        Generate hash of listing content to detect changes.

        Args:
            listing: The listing to hash

        Returns:
            16-character hash string
        """
        # Hash key fields that would trigger re-analysis if changed
        key_fields = [
            str(listing.price),
            str(listing.service_costs),
            listing.description or "",
            str(listing.size_sqm),
            str(listing.rooms),
            str(listing.floor_level),
            # Include boolean features
            str(listing.has_balcony),
            str(listing.has_garden),
            str(listing.has_rooftop),
            str(listing.has_washing_machine),
        ]

        content = "|".join(key_fields)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _serialize_features(self, listing: Listing) -> str:
        """Serialize listing features to JSON."""
        features = {
            "service_costs": listing.service_costs,
            "deposit": listing.deposit,
            "floor_level": listing.floor_level,
            "energy_label": listing.energy_label,
            "furnished_status": listing.furnished_status,
            "has_washing_machine": listing.has_washing_machine,
            "has_balcony": listing.has_balcony,
            "has_garden": listing.has_garden,
            "has_rooftop": listing.has_rooftop,
            "has_storage": listing.has_storage,
            "has_bike_storage": listing.has_bike_storage,
            "has_elevator": listing.has_elevator,
            "has_parking": listing.has_parking,
            "pets_allowed": listing.pets_allowed,
            "smoking_allowed": listing.smoking_allowed,
        }
        return json.dumps(features)

    def close(self):
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
