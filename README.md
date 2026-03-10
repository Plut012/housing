# Dutch Housing Finder

AI-powered rental listing finder for Eindhoven, Netherlands. Scrapes Dutch rental sites and uses Claude to identify perfect matches based on your specific requirements and preferences.

## Features

- 🔍 Scrapes major Dutch rental platforms (Pararius, and more to come)
- 🤖 Claude AI analysis to identify "gems" that match your criteria
- 📊 Three-tier evaluation system:
  - **Requirements**: Strict budget + general preferences
  - **Considerations**: Practical factors (utilities, landlord reputation, amenities)
  - **Dreams**: Aspirational features (gardens, rooftops, skylights, tall ceilings)
- 📝 Dual output: terminal summary + detailed markdown reports
- 💎 Highlights exceptional matches and dream features

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Define Your Criteria

Edit three configuration files to specify your needs:

**requirements.md** - Budget and preferences:
- YAML frontmatter: `max_budget`, `min_budget`, `location`
- Markdown body: General preferences, must-haves, nice-to-haves, dealbreakers

**considerations.md** - Practical factors to evaluate:
- Additional monthly costs (servicekosten)
- Landlord/listing reputation
- Utilities (gas, water, electric, wifi)
- Nearby amenities (grocery stores, parks)

**dreams.md** - Aspirational features (rare but valuable):
- Outdoor spaces: rooftop, garden (tuin), balcony
- Indoor features: skylights, tall ceilings, unique layouts
- Architectural character

All three files have example templates to guide you.

## Usage

Run the finder:

```bash
python finder.py
```

Or:

```bash
./finder.py
```

The script will:

1. Load your criteria from all three config files
2. Scrape rental listings from configured sites
3. Filter by budget (€800-1600 by default)
4. Analyze each listing with Claude AI against:
   - Your preferences (must-haves, nice-to-haves)
   - Practical considerations (utilities, amenities, reputation)
   - Dream features (gardens, skylights, etc.)
5. Display gems and top matches in terminal
6. Save detailed report to `results/report-YYYY-MM-DD_HH-MM.md`

## Output

### Terminal
- Quick summary of gems and top 5 matches
- Match scores and key reasoning

### Markdown Report
- Complete analysis of all listings
- Sorted by match score
- Detailed reasoning for each property
- Statistics and summary

## Project Structure

```
/data/dev/housing/
├── finder.py              # Main script
├── config.py             # Config parser (loads all 3 files)
├── analyzer.py           # Claude API integration
├── scrapers/
│   ├── base.py          # Base scraper interface
│   └── pararius.py      # Pararius scraper
├── requirements.md       # Budget + preferences
├── considerations.md     # Practical factors to evaluate
├── dreams.md            # Aspirational features
├── .env                 # API keys (not in git)
└── results/             # Generated reports
```

## Adding More Scrapers

To add support for additional Dutch rental sites:

1. Create a new scraper in `scrapers/` (e.g., `kamernet.py`)
2. Inherit from `BaseScraper` in `scrapers/base.py`
3. Implement the `scrape()` method returning `List[Listing]`
4. Add to the scrapers list in `finder.py`

See `scrapers/pararius.py` for reference.

## Roadmap

- [ ] Add Kamernet scraper
- [ ] Add Funda scraper
- [ ] Add Huisly aggregator support
- [ ] Implement caching to avoid re-analyzing same listings
- [ ] Add scheduling/cron support for automated checks
- [ ] Email notifications for new gems

## Notes

- Scraping respects rate limits (30s timeout per request)
- Some sites use JavaScript rendering - scrapers parse JSON-LD or static HTML
- Claude API calls are made sequentially to analyze each listing
- Results are sorted by match score (0-100)

## Example Configuration

The three template files include examples tailored for Eindhoven:

**requirements.md**:
- Budget: €800-1600/month
- Neighborhoods: Strijp-S, city center, Woensel-Zuid
- Must-haves: Public transport, natural light, quiet street

**considerations.md**:
- Check utilities (g/w/e) and additional costs
- Verify landlord reputation
- Nearby grocery stores and parks
- Internet availability

**dreams.md**:
- Outdoor spaces: garden (tuin), balcony, rooftop
- Indoor features: skylights, tall ceilings
- Architectural character

Customize all three files to match your actual needs!
