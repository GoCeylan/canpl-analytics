import { readFileSync } from 'fs';
import { join } from 'path';
import { withMiddleware } from '../lib/middleware.js';

export const config = {
  runtime: 'nodejs',
};

async function matchesHandler(req, res, { track, errors, validateNumber }) {
  const { season, team, limit = '100', offset = '0' } = req.query;

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

  // Read the combined matches file
  const dataPath = join(process.cwd(), 'data', 'matches', 'cpl_all.csv');
  const csvData = readFileSync(dataPath, 'utf-8');

  // Parse CSV
  const lines = csvData.trim().split('\n');
  const headers = lines[0].split(',');

  let matches = lines.slice(1).map(line => {
    const values = line.split(',');
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
    return obj;
  }).filter(m => m.date); // Filter out empty rows

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

export default withMiddleware(matchesHandler, { endpoint: '/api/matches' });
