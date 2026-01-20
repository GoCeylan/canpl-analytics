import { readFileSync } from 'fs';
import { join } from 'path';

export const config = {
  runtime: 'nodejs18.x',
};

export default function handler(req, res) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    const { season, team, limit = '100', offset = '0' } = req.query;

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
    if (season) {
      const seasonNum = parseInt(season, 10);
      matches = matches.filter(m => m.season === seasonNum);
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
    const offsetNum = parseInt(offset, 10);
    const limitNum = parseInt(limit, 10);
    const paginatedMatches = matches.slice(offsetNum, offsetNum + limitNum);

    return res.status(200).json({
      total: matches.length,
      count: paginatedMatches.length,
      offset: offsetNum,
      limit: limitNum,
      matches: paginatedMatches
    });
  } catch (error) {
    console.error('Error reading matches:', error);
    return res.status(500).json({ error: 'Failed to load matches data' });
  }
}
