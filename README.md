# Canadian Premier League Analytics Database

The most comprehensive open dataset for the Canadian Premier League (CPL).

## What's Included

- Complete match results (2019-2026)
- Team statistics (shots, possession, corners, etc.)
- Historical lineups
- Weather data for every match
- Travel distance calculations
- Historical betting odds (Bet365, Sports Interaction)

## Data Coverage

- **Matches:** 500+ matches across 7 seasons
- **Teams:** All 9 CPL clubs (current and historical)
- **Updates:** Weekly during season
- **Quality:** Validated against official CPL records

## Quick Start

```python
import pandas as pd

# Load all CPL matches
matches = pd.read_csv('data/matches/cpl_2024.csv')

# Filter for Forge FC home matches
forge_home = matches[matches['home_team'] == 'Forge FC']

# Calculate home win percentage
win_pct = (forge_home['home_goals'] > forge_home['away_goals']).mean()
print(f"Forge FC home win rate: {win_pct:.1%}")
```

## Using the Data Loader

```python
from scripts.data_loader import CPLDataLoader

loader = CPLDataLoader()

# Load matches for specific seasons
matches = loader.load_matches(seasons=[2023, 2024])

# Get standings
standings = loader.get_standings(2024)

# Get team form
form = loader.get_recent_form('Forge FC', n_matches=5)

# Head-to-head record
h2h = loader.get_head_to_head('Forge FC', 'Cavalry FC')
```

## Project Structure

```
canpl-analytics/
├── README.md                    # This file
├── schema.sql                   # Database schema
├── data/
│   ├── matches/                 # Match results by season
│   │   ├── cpl_2019.csv
│   │   ├── cpl_2020.csv
│   │   └── ...
│   ├── team_stats/              # Team statistics
│   ├── historical_odds/         # Betting odds history
│   └── README.md                # Data dictionary
├── scripts/
│   ├── data_loader.py           # Helper to load data
│   ├── data_validator.py        # Quality checks
│   ├── cpl_results_scraper.py   # Match scraper
│   └── weather_integration.py   # Weather data
├── examples/
│   ├── basic_analysis.ipynb     # Jupyter notebook tutorial
│   └── poisson_model.py         # Example betting model
├── docs/
│   ├── data_dictionary.md       # Field definitions
│   ├── methodology.md           # Data collection methods
│   └── contributing.md          # How to contribute
└── LICENSE
```

## Example Use Cases

1. **Betting Models** - Build Poisson regression models for match predictions
2. **Performance Analysis** - Track team form and trends over time
3. **Travel Impact Studies** - Quantify away travel disadvantage
4. **Weather Effects** - Analyze how temperature/rain affects scoring
5. **Playoff Predictions** - ML models for championship odds

## Example: Simple Prediction Model

```python
from examples.poisson_model import PoissonModel
from scripts.data_loader import load_cpl_matches

# Load and train
matches = load_cpl_matches()
model = PoissonModel()
model.fit(matches)

# Predict match
probs = model.predict_probabilities('Forge FC', 'Cavalry FC')
print(f"Home win: {probs['home_win']:.1%}")
print(f"Draw: {probs['draw']:.1%}")
print(f"Away win: {probs['away_win']:.1%}")
```

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/canpl-analytics.git
cd canpl-analytics

# Install dependencies
pip install pandas numpy scipy matplotlib seaborn requests beautifulsoup4

# Or use requirements.txt
pip install -r requirements.txt
```

## Data Sources

- [CanPL.ca](https://canpl.ca) - Official match results
- [OneSoccer](https://onesoccer.ca) - Match statistics
- OpenWeatherMap - Weather data
- Public betting markets - Historical odds

## Contributing

Found an error? Have additional data? Submit a pull request!

See [docs/contributing.md](docs/contributing.md) for guidelines.

### Ways to Contribute

- Add missing match data
- Improve data quality
- Add new statistics
- Create analysis examples
- Report bugs

## License

CC-BY-4.0 - Free to use with attribution.

## Acknowledgments

Data sourced from CanPL.ca, OneSoccer, and public betting markets.

Special thanks to the CPL community for supporting open data initiatives.

## Contact

Questions? Open an issue or reach out on Twitter.

---

If you use this data, please star the repo!
