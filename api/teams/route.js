const { readFileSync } = require('fs');
const { join } = require('path');
const { withMiddleware } = require('../lib/middleware.js');

// CPL team information (supports both full names and short names from API)
const TEAM_INFO = {
  'Forge FC': {
    city: 'Hamilton',
    stadium: 'Tim Hortons Field',
    founded: 2018,
    latitude: 43.2557,
    longitude: -79.8711,
    surface: 'grass'
  },
  'Forge': {
    city: 'Hamilton',
    stadium: 'Tim Hortons Field',
    founded: 2018,
    latitude: 43.2557,
    longitude: -79.8711,
    surface: 'grass'
  },
  'Cavalry FC': {
    city: 'Calgary',
    stadium: 'ATCO Field',
    founded: 2018,
    latitude: 50.9900,
    longitude: -114.0060,
    surface: 'grass'
  },
  'Cavalry': {
    city: 'Calgary',
    stadium: 'ATCO Field',
    founded: 2018,
    latitude: 50.9900,
    longitude: -114.0060,
    surface: 'grass'
  },
  'Pacific FC': {
    city: 'Langford',
    stadium: 'Starlight Stadium',
    founded: 2018,
    latitude: 48.4500,
    longitude: -123.4960,
    surface: 'turf'
  },
  'Pacific': {
    city: 'Langford',
    stadium: 'Starlight Stadium',
    founded: 2018,
    latitude: 48.4500,
    longitude: -123.4960,
    surface: 'turf'
  },
  'Valour FC': {
    city: 'Winnipeg',
    stadium: 'IG Field',
    founded: 2018,
    latitude: 49.8076,
    longitude: -97.1445,
    surface: 'turf',
    status: 'inactive'
  },
  'Valour': {
    city: 'Winnipeg',
    stadium: 'IG Field',
    founded: 2018,
    latitude: 49.8076,
    longitude: -97.1445,
    surface: 'turf',
    status: 'inactive'
  },
  'York United FC': {
    city: 'Toronto',
    stadium: 'York Lions Stadium',
    founded: 2018,
    latitude: 43.7735,
    longitude: -79.4992,
    surface: 'turf',
    status: 'inactive'
  },
  'Inter Toronto FC': {
    city: 'Toronto',
    stadium: 'York Lions Stadium',
    founded: 2018,
    latitude: 43.7735,
    longitude: -79.4992,
    surface: 'turf',
  },
  'HFX Wanderers FC': {
    city: 'Halifax',
    stadium: 'Wanderers Grounds',
    founded: 2018,
    latitude: 44.6488,
    longitude: -63.5752,
    surface: 'grass'
  },
  'HFX Wanderers': {
    city: 'Halifax',
    stadium: 'Wanderers Grounds',
    founded: 2018,
    latitude: 44.6488,
    longitude: -63.5752,
    surface: 'grass'
  },
  'FC Edmonton': {
    city: 'Edmonton',
    stadium: 'Clarke Stadium',
    founded: 2010,
    latitude: 53.5722,
    longitude: -113.4557,
    surface: 'turf',
    status: 'inactive'
  },
  'Atletico Ottawa': {
    city: 'Ottawa',
    stadium: 'TD Place Stadium',
    founded: 2020,
    latitude: 45.3985,
    longitude: -75.6825,
    surface: 'turf'
  },
  'Atlético Ottawa': {
    city: 'Ottawa',
    stadium: 'TD Place Stadium',
    founded: 2020,
    latitude: 45.3985,
    longitude: -75.6825,
    surface: 'turf'
  },
  'Vancouver FC': {
    city: 'Langley',
    stadium: 'Willoughby Community Park',
    founded: 2022,
    latitude: 49.0197,
    longitude: -122.6465,
    surface: 'turf'
  },
  'Inter Toronto': {
    city: 'Toronto',
    stadium: 'York Lions Stadium',
    founded: 2024,
    latitude: 43.7735,
    longitude: -79.4992,
    surface: 'turf'
  },
  'FC Supra': {
    city: 'Laval',
    stadium: 'Stade Boréale',
    founded: 2026,
    latitude: 45.5740,
    longitude: -73.7045,
    surface: 'turf'
  }
};

async function teamsHandler(req, res, { track, errors }) {
  const { active_only } = req.query;

  // Validate active_only parameter
  if (active_only !== undefined && active_only !== 'true' && active_only !== 'false') {
    track(400);
    return errors.badRequest(res, 'active_only must be "true" or "false"');
  }

  // Read matches to get actual team names from data
  const dataPath = join(process.cwd(), 'data', 'matches', 'cpl_all.csv');
  const csvData = readFileSync(dataPath, 'utf-8');

  const lines = csvData.trim().split('\n');
  const headers = lines[0].split(',');

  const matches = lines.slice(1).map(line => {
    const values = line.split(',');
    const obj = {};
    headers.forEach((header, index) => {
      obj[header] = values[index];
    });
    return obj;
  }).filter(m => m.date);

  // Get unique teams from data
  const teamsFromData = new Set();
  matches.forEach(m => {
    teamsFromData.add(m.home_team);
    teamsFromData.add(m.away_team);
  });

  // Build team list with info
  let teams = Array.from(teamsFromData).map(name => {
    const info = TEAM_INFO[name] || {};
    return {
      name,
      ...info,
      status: info.status || 'active'
    };
  });

  // Filter active only if requested
  if (active_only === 'true') {
    teams = teams.filter(t => t.status === 'active');
  }

  // Sort alphabetically
  teams.sort((a, b) => a.name.localeCompare(b.name));

  // Use longer cache for teams (data changes infrequently)
  res.setHeader('Cache-Control', 's-maxage=86400, stale-while-revalidate');

  track(200);
  return res.status(200).json({
    count: teams.length,
    teams
  });
}

module.exports = withMiddleware(teamsHandler, { endpoint: '/api/teams' });
