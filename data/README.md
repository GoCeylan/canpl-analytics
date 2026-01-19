# CPL Analytics Data

This directory contains the Canadian Premier League dataset.

## Directory Structure

```
data/
├── matches/           # Match results by season
│   ├── cpl_2019.csv
│   ├── cpl_2020.csv
│   ├── cpl_2021.csv
│   ├── cpl_2022.csv
│   ├── cpl_2023.csv
│   ├── cpl_2024.csv
│   └── cpl_2025.csv
├── team_stats/        # Aggregated team statistics
│   └── team_season_stats.csv
├── historical_odds/   # Betting odds history
│   └── odds_YYYY.csv
└── travel_distances.csv  # Distance matrix between stadiums
```

## Quick Load

```python
import pandas as pd

# Load single season
matches_2024 = pd.read_csv('data/matches/cpl_2024.csv')

# Load all seasons
import glob
all_files = glob.glob('data/matches/cpl_*.csv')
matches = pd.concat([pd.read_csv(f) for f in all_files])
```

## Data Quality

All data is validated before inclusion. See `scripts/data_validator.py` for validation rules.

## Updates

- Match data updated within 24 hours of match completion
- Team stats updated weekly on Mondays
- During off-season, historical corrections may be made

## File Formats

All files are UTF-8 encoded CSV with:
- Header row
- Comma delimiter
- Double-quote escaping

## See Also

- [Data Dictionary](../docs/data_dictionary.md) - Field definitions
- [Methodology](../docs/methodology.md) - How data is collected
