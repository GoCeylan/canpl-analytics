const { readFileSync } = require('fs');
const { join } = require('path');
const { withMiddleware } = require('../lib/middleware.js');

async function matchStatsHandler(req, res, { track, errors }) {
  const { match_id } = req.query;

  if (!match_id) {
    track(400);
    return errors.badRequest(res, 'match_id is required');
  }

  // Load match data from CSV
  const matchesPath = join(process.cwd(), 'data', 'matches', 'cpl_2025_api.csv');
  const refereesPath = join(process.cwd(), 'data', 'matches', 'cpl_referees_2019_2025.csv');

  let matchesCsv, refereesCsv;
  try {
    matchesCsv = readFileSync(matchesPath, 'utf-8');
  } catch (err) {
    console.error('Failed to read matches file:', err);
    track(500);
    return errors.serverError(res, 'Failed to load match data');
  }

  try {
    refereesCsv = readFileSync(refereesPath, 'utf-8');
  } catch (err) {
    console.error('Failed to read referees file:', err);
    // Referees are optional, continue without them
    refereesCsv = '';
  }

  // Parse matches CSV (handle CRLF line endings)
  const matchLines = matchesCsv.trim().replace(/\r/g, '').split('\n');
  const matchHeaders = matchLines[0].split(',');
  const matches = matchLines.slice(1).map(line => {
    const values = parseCSVLine(line);
    const obj = {};
    matchHeaders.forEach((header, index) => {
      const value = values[index];
      if (['home_goals', 'away_goals', 'season'].includes(header)) {
        obj[header] = parseInt(value, 10);
      } else {
        obj[header] = value;
      }
    });
    return obj;
  });

  // Find the requested match
  const match = matches.find(m => m.match_id === match_id);
  if (!match) {
    track(404);
    return errors.notFound(res, 'Match not found');
  }

  // Parse referees CSV and find referee for this match (handle CRLF line endings)
  let referee = null;
  if (refereesCsv) {
    const refLines = refereesCsv.trim().replace(/\r/g, '').split('\n');
    const refHeaders = refLines[0].split(',');
    for (let i = 1; i < refLines.length; i++) {
      const values = parseCSVLine(refLines[i]);
      const refObj = {};
      refHeaders.forEach((header, index) => {
        refObj[header] = values[index];
      });
      if (refObj.match_id === match_id) {
        referee = {
          id: refObj.referee_id,
          name: refObj.referee_name,
          short_name: refObj.referee_short_name
        };
        break;
      }
    }
  }

  // Build response
  const response = {
    match_id: match.match_id,
    date: match.date,
    season: match.season,
    matchday: match.matchday,
    status: match.status,
    home_team: match.home_team,
    away_team: match.away_team,
    score: {
      home: match.home_goals,
      away: match.away_goals
    },
    venue: match.venue
  };

  if (referee) {
    response.referee = referee;
  }

  track(200);
  return res.status(200).json(response);
}

/**
 * Parse a CSV line handling quoted values with commas
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
      values.push(current);
      current = '';
    } else {
      current += char;
    }
  }
  values.push(current);
  return values;
}

module.exports = withMiddleware(matchStatsHandler, { endpoint: '/api/match-stats' });
