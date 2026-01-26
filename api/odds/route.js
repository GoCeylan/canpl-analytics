const { readFileSync, existsSync } = require('fs');
const { join } = require('path');
const { withMiddleware } = require('../lib/middleware.js');

async function oddsHandler(req, res, { track, errors, validateNumber }) {
  const { season, team, bookmaker, match_id, limit = '100', offset = '0' } = req.query;

  // Validate parameters
  const seasonValidation = validateNumber(season, 'season', 2019, 2030);
  if (!seasonValidation.valid) {
    track(400);
    return errors.badRequest(res, seasonValidation.error);
  }

  const limitValidation = validateNumber(limit, 'limit', 1, 500);
  if (!limitValidation.valid) {
    track(400);
    return errors.badRequest(res, limitValidation.error);
  }

  const offsetValidation = validateNumber(offset, 'offset', 0);
  if (!offsetValidation.valid) {
    track(400);
    return errors.badRequest(res, offsetValidation.error);
  }

  // Determine which season file to read
  const seasonYear = seasonValidation.value || new Date().getFullYear();
  const csvPath = join(process.cwd(), 'data', 'closing_odds', `cpl_${seasonYear}_closing_odds.csv`);

  // Check if file exists
  if (!existsSync(csvPath)) {
    track(404);
    return res.status(404).json({
      error: 'Odds data not found',
      message: `No closing odds data available for season ${seasonYear}`,
      available_seasons: getAvailableSeasons()
    });
  }

  try {
    // Read and parse CSV
    const csvData = readFileSync(csvPath, 'utf-8');
    const lines = csvData.trim().split('\n');

    if (lines.length < 2) {
      track(200);
      return res.status(200).json({
        total: 0,
        count: 0,
        offset: 0,
        limit: parseInt(limit),
        season: seasonYear,
        note: 'No closing odds recorded yet for this season',
        odds: []
      });
    }

    const headers = lines[0].split(',');

    let odds = lines.slice(1)
      .filter(line => line.trim())
      .map(line => {
        // Handle CSV parsing (basic - handles simple cases)
        const values = parseCSVLine(line);
        const obj = {};
        headers.forEach((header, index) => {
          const value = values[index];
          // Convert numeric fields
          if (['closing_home', 'closing_draw', 'closing_away', 'closing_over_2.5', 'closing_under_2.5'].includes(header)) {
            obj[header] = value ? parseFloat(value) : null;
          } else {
            obj[header] = value;
          }
        });
        return obj;
      })
      .filter(o => o.match_id); // Filter out empty rows

    // Apply filters
    if (team) {
      const teamLower = team.toLowerCase();
      odds = odds.filter(o =>
        o.home_team.toLowerCase().includes(teamLower) ||
        o.away_team.toLowerCase().includes(teamLower)
      );
    }

    if (bookmaker) {
      const bookmakerLower = bookmaker.toLowerCase();
      odds = odds.filter(o =>
        o.bookmaker.toLowerCase() === bookmakerLower
      );
    }

    if (match_id) {
      odds = odds.filter(o =>
        o.match_id === match_id || o.match_id.includes(match_id)
      );
    }

    // Pagination
    const total = odds.length;
    const offsetNum = offsetValidation.value || 0;
    const limitNum = limitValidation.value || 100;
    const paginatedOdds = odds.slice(offsetNum, offsetNum + limitNum);

    track(200);
    return res.status(200).json({
      total,
      count: paginatedOdds.length,
      offset: offsetNum,
      limit: limitNum,
      season: seasonYear,
      note: 'Closing odds only (final odds before kickoff). Updated weekly.',
      odds: paginatedOdds
    });

  } catch (error) {
    track(500);
    return res.status(500).json({
      error: 'Internal server error',
      message: error.message
    });
  }
}

/**
 * Parse a CSV line handling quoted fields
 */
function parseCSVLine(line) {
  const values = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];

    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      values.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  values.push(current.trim());

  return values;
}

/**
 * Get list of available seasons with odds data
 */
function getAvailableSeasons() {
  const oddsDir = join(process.cwd(), 'data', 'closing_odds');
  const seasons = [];

  for (let year = 2019; year <= new Date().getFullYear(); year++) {
    const path = join(oddsDir, `cpl_${year}_closing_odds.csv`);
    if (existsSync(path)) {
      seasons.push(year);
    }
  }

  return seasons;
}

module.exports = withMiddleware(oddsHandler, { endpoint: '/api/odds' });
