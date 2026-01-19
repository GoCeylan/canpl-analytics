# Contributing to CPL Analytics

Thank you for your interest in contributing to the CPL Analytics dataset!

## How to Contribute

### Reporting Issues

Found an error in the data? Please open an issue with:

1. **Which file** contains the error
2. **What's wrong** (expected vs actual value)
3. **Source** to verify the correct value (link if possible)

Example:
```
File: data/matches/cpl_2024.csv
Row: 2024-05-15, Forge FC vs Cavalry FC
Issue: Attendance listed as 6500, should be 7200
Source: https://canpl.ca/match/12345
```

### Adding Data

#### Match Results

1. Fork the repository
2. Add data to appropriate CSV file
3. Run the validator: `python scripts/data_validator.py`
4. Submit a pull request

Data format:
```csv
season,date,home_team,away_team,home_goals,away_goals,venue,attendance
2024,2024-05-20,Forge FC,Pacific FC,2,1,Tim Hortons Field,6500
```

#### New Statistics

Want to add a new statistic or data type? Please:

1. Open an issue first to discuss
2. Propose schema changes
3. Provide sample data
4. Update documentation

### Code Contributions

#### Scrapers

Improving scrapers? Great! Please ensure:

- Code follows existing style
- Error handling is robust
- Rate limiting respects source websites
- Tests are included

#### Analysis Examples

Adding examples? Please:

- Include clear documentation
- Use only public dataset fields
- Test with sample data

## Pull Request Process

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/add-2024-week-15`
3. Make your changes
4. Run validation: `python scripts/data_validator.py`
5. Commit with clear message: `Add 2024 match week 15 data`
6. Push and create PR

### PR Checklist

- [ ] Data passes validation
- [ ] Documentation updated (if needed)
- [ ] Commit messages are clear
- [ ] No sensitive data included

## Code of Conduct

- Be respectful and constructive
- Credit sources appropriately
- Don't submit scraped data that violates ToS
- No gambling advice or tips

## Data Standards

### Required Fields

Every match must have:
- `date` (YYYY-MM-DD)
- `home_team` (exact team name)
- `away_team` (exact team name)
- `home_goals` (integer)
- `away_goals` (integer)

### Team Names

Use exact names:
```
Forge FC
Cavalry FC
Pacific FC
York United FC
Valour FC
HFX Wanderers FC
FC Edmonton
Atletico Ottawa
Vancouver FC
```

### Date Format

Always use ISO 8601: `YYYY-MM-DD`

## Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes for significant additions
- Twitter mentions for major contributions

## Questions?

Open an issue with the `question` label or reach out directly.

Thank you for helping make CPL data accessible!
