#!/usr/bin/env python3
"""Main script to find rental listings matching your requirements."""

import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from analyzer import ListingAnalyzer
from config import Requirements
from scrapers.pararius import ParariusScraper


def main():
    """Main entry point."""
    # Load environment variables
    load_dotenv()

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY not found in environment")
        print("Please create a .env file with your API key:")
        print("  ANTHROPIC_API_KEY=your_api_key_here")
        return

    # Load requirements
    print("📋 Loading requirements...")
    try:
        requirements = Requirements.from_file(Path("requirements.md"))
        print(f"✓ Requirements loaded:")
        print(f"  Budget: €{requirements.min_budget or 0} - €{requirements.max_budget}")
        print(f"  Location: {requirements.location}")
        print()
    except FileNotFoundError:
        print("❌ Error: requirements.md not found")
        print("Please create requirements.md with your search criteria")
        return
    except Exception as e:
        print(f"❌ Error loading requirements: {e}")
        return

    # Initialize scrapers
    scrapers = [
        ParariusScraper(),
        # Add more scrapers here as implemented
    ]

    # Scrape listings
    print("🔍 Scraping rental listings...")
    all_listings = []

    for scraper in scrapers:
        print(f"\n{scraper.name}:")
        try:
            listings = scraper.scrape(location=requirements.location, max_pages=2)
            all_listings.extend(listings)
            print(f"✓ Found {len(listings)} listings from {scraper.name}")
        except Exception as e:
            print(f"❌ Error scraping {scraper.name}: {e}")
            continue

    if not all_listings:
        print("\n❌ No listings found. Check your scrapers or try a different location.")
        return

    print(f"\n✓ Total listings collected: {len(all_listings)}")

    # Filter by strict requirements first
    print("\n🔍 Filtering by strict requirements...")
    filtered_listings = []

    for listing in all_listings:
        # Budget check
        if listing.price > requirements.max_budget:
            continue
        if requirements.min_budget and listing.price < requirements.min_budget:
            continue

        filtered_listings.append(listing)

    print(f"✓ {len(filtered_listings)} listings match strict requirements")

    if not filtered_listings:
        print("\n❌ No listings match your budget requirements.")
        print("Consider adjusting your budget range.")
        return

    # Analyze with Claude
    print("\n🤖 Analyzing listings with Claude...")
    analyzer = ListingAnalyzer()

    try:
        results = analyzer.analyze_batch(filtered_listings, requirements)
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        return

    # Output results
    print("\n" + "=" * 80)
    print("📊 RESULTS")
    print("=" * 80)

    # Terminal output - top matches
    gems = [r for r in results if r.is_gem]
    top_matches = results[:5]  # Top 5 by score

    if gems:
        print(f"\n💎 GEMS FOUND ({len(gems)}):\n")
        for result in gems:
            print(result)
            print("-" * 80)

    print(f"\n🏆 TOP MATCHES:\n")
    for i, result in enumerate(top_matches, 1):
        print(f"#{i}")
        print(result)
        print("-" * 80)

    # Save detailed report
    report_path = Path("results") / f"report-{datetime.now().strftime('%Y-%m-%d_%H-%M')}.md"
    print(f"\n💾 Saving detailed report to {report_path}...")

    try:
        save_report(results, requirements, report_path)
        print(f"✓ Report saved successfully")
    except Exception as e:
        print(f"❌ Error saving report: {e}")

    # Save gems report if any gems found
    if gems:
        gems_path = Path("results") / f"gems-{datetime.now().strftime('%Y-%m-%d_%H-%M')}.md"
        print(f"\n💎 Saving gems report to {gems_path}...")
        try:
            save_gems_report(gems, requirements, gems_path)
            print(f"✓ Gems report saved successfully")
        except Exception as e:
            print(f"❌ Error saving gems report: {e}")

    print(f"\n✅ Done! Analyzed {len(results)} listings.")


def save_report(results, requirements, output_path: Path):
    """Save detailed analysis report to markdown file."""
    output_path.parent.mkdir(exist_ok=True)

    with output_path.open("w") as f:
        # Header
        f.write(f"# Housing Search Report\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Requirements summary
        f.write("## Your Requirements\n\n")
        f.write(f"- **Budget**: €{requirements.min_budget or 0} - €{requirements.max_budget}\n")
        f.write(f"- **Location**: {requirements.location}\n\n")

        f.write("### Preferences\n\n")
        f.write(f"{requirements.preferences}\n\n")

        if requirements.considerations:
            f.write("### Practical Considerations\n\n")
            f.write(f"{requirements.considerations}\n\n")

        if requirements.dreams:
            f.write("### Dream Features\n\n")
            f.write(f"{requirements.dreams}\n\n")

        # Statistics
        gems = [r for r in results if r.is_gem]
        avg_score = sum(r.score for r in results) / len(results) if results else 0

        f.write("## Statistics\n\n")
        f.write(f"- **Total analyzed**: {len(results)}\n")
        f.write(f"- **Gems found**: {len(gems)}\n")
        f.write(f"- **Average score**: {avg_score:.1f}/100\n")
        f.write(f"- **Score range**: {min(r.score for r in results):.0f} - {max(r.score for r in results):.0f}\n\n")

        # Gems section
        if gems:
            f.write("## 💎 Gems\n\n")
            for result in gems:
                write_listing_section(f, result)

        # All results
        f.write("## All Results (by score)\n\n")
        for i, result in enumerate(results, 1):
            f.write(f"### {i}. {result.listing.title} ({result.score}/100)\n\n")
            write_listing_section(f, result, include_title=False)


def write_listing_section(f, result, include_title=True):
    """Write a listing section to the report file."""
    listing = result.listing

    if include_title:
        f.write(f"### {listing.title} ({result.score}/100)\n\n")

    f.write(f"**Price**: €{listing.price}/month  \n")
    f.write(f"**Location**: {listing.location}  \n")
    if listing.size_sqm:
        f.write(f"**Size**: {listing.size_sqm}m²  \n")
    if listing.rooms:
        f.write(f"**Rooms**: {listing.rooms}  \n")
    if listing.available_from:
        f.write(f"**Available from**: {listing.available_from}  \n")

    f.write(f"**URL**: [{listing.url}]({listing.url})  \n\n")

    f.write(f"**Analysis**:  \n{result.reasoning}\n\n")
    f.write("---\n\n")


def save_gems_report(gems, requirements, output_path: Path):
    """Save actionable gems-only report to markdown file."""
    output_path.parent.mkdir(exist_ok=True)

    with output_path.open("w") as f:
        # Header
        f.write(f"# 💎 Housing Gems\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**Found {len(gems)} exceptional match{'es' if len(gems) != 1 else ''}!**\n\n")

        f.write("---\n\n")

        # Each gem as a rich card
        for i, result in enumerate(gems, 1):
            listing = result.listing

            # Title with emoji indicator
            f.write(f"## 🌟 #{i}: {listing.title}\n\n")

            # Prominent link
            f.write(f"### **[📍 View on Pararius →]({listing.url})**\n\n")

            # Quick facts box
            f.write("**Quick Facts:**\n")
            total_cost = listing.price
            if listing.service_costs:
                total_cost += listing.service_costs
                f.write(f"- 💰 €{listing.price}/month + €{listing.service_costs} servicekosten = **€{total_cost}/month total**\n")
            else:
                f.write(f"- 💰 **€{listing.price}/month**\n")

            f.write(f"- 📐 {listing.size_sqm}m², {listing.rooms} rooms\n")

            if listing.floor_level:
                f.write(f"- 🏢 {listing.floor_level}\n")
            if listing.energy_label:
                f.write(f"- ⚡ Energy label: {listing.energy_label}\n")
            if listing.furnished_status:
                f.write(f"- 🛋️ {listing.furnished_status.capitalize()}\n")
            if listing.available_from:
                f.write(f"- 📅 Available: {listing.available_from}\n")

            f.write(f"\n**Match Score:** {result.score}/100\n\n")

            # Dream features section
            dream_features = []
            if listing.has_balcony:
                dream_features.append("Balcony")
            if listing.has_garden:
                dream_features.append("Garden (tuin)")
            if listing.has_rooftop:
                dream_features.append("Rooftop/terrace")

            if dream_features:
                f.write(f"### ✨ Dream Features:\n")
                for feature in dream_features:
                    f.write(f"- 🌟 **{feature}**\n")
                f.write("\n")

            # Key amenities
            amenities = []
            if listing.has_washing_machine:
                amenities.append("Washing machine")
            if listing.has_storage:
                amenities.append("Storage")
            if listing.has_bike_storage:
                amenities.append("Bike storage")
            if listing.has_elevator:
                amenities.append("Elevator")
            if listing.has_parking:
                amenities.append("Parking")

            if amenities:
                f.write(f"**Amenities:** {', '.join(amenities)}\n\n")

            # Why it's a gem
            f.write(f"### Why it's a gem:\n\n")
            f.write(f"{result.reasoning}\n\n")

            # Action checklist
            f.write(f"### Next Steps:\n\n")
            f.write(f"- [ ] [View listing on Pararius]({listing.url})\n")
            f.write(f"- [ ] Schedule viewing\n")

            # Suggest specific questions based on missing info
            questions = []
            if not listing.service_costs:
                questions.append("What are the monthly servicekosten?")
            if not listing.energy_label:
                questions.append("What is the energy label?")
            if not listing.floor_level:
                questions.append("Which floor is the apartment on?")
            if listing.has_washing_machine is None:
                questions.append("Is there a washing machine or hookup?")

            if questions:
                f.write(f"- [ ] Ask landlord:\n")
                for q in questions:
                    f.write(f"  - {q}\n")

            f.write(f"\n---\n\n")

        # Summary at bottom
        f.write(f"## Summary\n\n")
        f.write(f"**Budget range:** €{requirements.min_budget or 0} - €{requirements.max_budget}\n\n")
        f.write(f"These {len(gems)} gem{'s' if len(gems) != 1 else ''} scored {min(r.score for r in gems):.0f}-{max(r.score for r in gems):.0f}/100 ")
        f.write(f"and {'match' if len(gems) == 1 else 'match'} your requirements exceptionally well")

        dream_count = sum(1 for g in gems if g.listing.has_balcony or g.listing.has_garden or g.listing.has_rooftop)
        if dream_count:
            f.write(f", with {dream_count} featuring dream outdoor spaces")
        f.write(".\n\n")

        f.write(f"**Action:** Contact landlords quickly - quality listings disappear fast in Eindhoven!\n")


if __name__ == "__main__":
    main()
