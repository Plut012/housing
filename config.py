"""Parse and validate requirements configuration."""

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Requirements:
    """User's rental requirements."""

    # Strict requirements from YAML frontmatter
    max_budget: float
    min_budget: Optional[float] = None
    location: str = "eindhoven"

    # Natural language preferences from markdown body
    preferences: str = ""

    # Practical considerations
    considerations: str = ""

    # Dream features
    dreams: str = ""

    @classmethod
    def from_file(
        cls,
        requirements_path: Path = Path("requirements.md"),
        considerations_path: Path = Path("considerations.md"),
        dreams_path: Path = Path("dreams.md"),
    ) -> "Requirements":
        """Parse requirements from markdown files."""
        # Load requirements.md
        if not requirements_path.exists():
            raise FileNotFoundError(f"Requirements file not found: {requirements_path}")

        content = requirements_path.read_text()

        # Split frontmatter and body
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                preferences = parts[2].strip()
            else:
                raise ValueError("Invalid frontmatter format")
        else:
            raise ValueError("Requirements file must start with YAML frontmatter (---)")

        # Load considerations.md (optional)
        considerations = ""
        if considerations_path.exists():
            considerations = considerations_path.read_text().strip()

        # Load dreams.md (optional)
        dreams = ""
        if dreams_path.exists():
            dreams = dreams_path.read_text().strip()

        return cls(
            max_budget=frontmatter["max_budget"],
            min_budget=frontmatter.get("min_budget"),
            location=frontmatter.get("location", "eindhoven"),
            preferences=preferences,
            considerations=considerations,
            dreams=dreams,
        )

    def __str__(self) -> str:
        """Human-readable summary."""
        return (
            f"Budget: €{self.min_budget or 0} - €{self.max_budget}\n"
            f"Location: {self.location}\n"
            f"\nPreferences:\n{self.preferences[:200]}..."
        )
