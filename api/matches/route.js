const { readFileSync } = require('fs');
const { join } = require('path');
const { withMiddleware } = require('../lib/middleware.js');

const VALID_COMPETITIONS = ['cpl', 'canadian-championship', 'ccl'];

async function matchesHandler(req, res, { track, errors, validateNumber }) {
  const { season, team, competition, limit = '100', offset = '0' } = req.query;

  // Validate parameters
  const seasonValidation = validateNumber(season, 'season', 2019, 2030);
  if (!seasonValidation.valid) {
    track(400);
    return errors.badRequest(res, seasonValidation.error);
  }

  if (competition !== undefined && !VALID_COMPETITIONS.includes(competition)) {
    track(400);
    return errors.badRequest(res, 'competition must be one of: ' + VALID_COMPETITIONS.join(', '));
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

  // Read the combined matches file with match_ids
  const dataPath = join(process.cwd(), 'data', 'matches', 'cpl_all_with_ids.csv');
  const csvData = readFileSync(dataPath, 'utf-8');

  // Parse CSV (handle CRLF line endings)
  const lines = csvData.trim().replace(/\r/g, '').split('\n');
  const headers = lines[0].split(',');

  let matches = lines.slice(1).map(line => {
    const values = parseCSVLine(line);
    const obj = {};
    headers.forEach((header, index) => {
      const value = values[index];
      // Convert numeric fields
      if (['home_goals', 'away_goals', 'season'].includes(header)) {
        obj[header] = parseInt(value, 10);
      } else {
        obj[header] = value;
      }
    });
    // Backfill competition for rows without it (legacy data)
    if (!obj.competition) {
      obj.competition = 'cpl';
    }
    return obj;
  }).filter(m => m.date && m.match_id); // Filter out empty rows

  // Filter by competition if provided
  if (competition) {
    matches = matches.filter(m => m.competition === competition);
  }

  // Filter by season if provided
  if (seasonValidation.value !== undefined) {
    matches = matches.filter(m => m.season === seasonValidation.value);
  }

  // Filter by team if provided
  if (team) {
    const teamLower = team.toLowerCase();
    matches = matches.filter(m =>
      m.home_team.toLowerCase().includes(teamLower) ||
      m.away_team.toLowerCase().includes(teamLower)
    );
  }

  // Apply pagination
  const offsetNum = offsetValidation.value || 0;
  const limitNum = limitValidation.value || 100;
  const paginatedMatches = matches.slice(offsetNum, offsetNum + limitNum);

  track(200);
  return res.status(200).json({
    total: matches.length,
    count: paginatedMatches.length,
    offset: offsetNum,
    limit: limitNum,
    matches: paginatedMatches
  });
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

module.exports = withMiddleware(matchesHandler, { endpoint: '/api/matches' });
