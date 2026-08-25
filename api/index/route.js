const { withMiddleware } = require('../lib/middleware.js');
const { CURRENT_SEASON } = require('../lib/sdp.js');

const ENDPOINTS = [
  ['matches', 'Historical results plus the complete live 2026 schedule'],
  ['live', 'Live, recently finished, and upcoming CPL fixtures'],
  ['standings', 'Official live table and historical standings'],
  ['players', 'Season player profiles, 30+ statistics, ratings, filtering, and sorting'],
  ['leaderboards', 'Rating and statistical leaderboards'],
  ['team-stats', 'Official season-long team performance metrics'],
  ['teams', 'Current and historical clubs'],
  ['match-stats', 'Match-level advanced team statistics and xG'],
  ['referees', 'Match officials and referee summaries'],
  ['venues', 'Stadium capacity, surface, city, and coordinates'],
  ['weather', 'Historical match weather observations'],
  ['odds', 'Closing match odds'],
  ['odds-quotes', 'Timestamped bookmaker price snapshots'],
  ['seasons', 'Coverage and season identifiers'],
  ['health', 'Service health and dataset checks'],
];

async function discoveryHandler(req, res, { track }) {
  track(200);
  return res.status(200).json({
    name: 'Canada Soccer API',
    description: 'Open Canadian Premier League data from 2019 through the live season.',
    version: '2.0.0',
    current_season: CURRENT_SEASON,
    authentication: 'none',
    rate_limit: { requests: 300, window: '1 hour', scope: 'per IP (best effort)' },
    formats: ['application/json'],
    documentation: 'https://canadasoccerapi.com/docs/api-reference.html',
    openapi: 'https://canadasoccerapi.com/openapi.json',
    endpoints: Object.fromEntries(ENDPOINTS.map(([path, description]) => [
      `/api/v1/${path}`,
      { method: 'GET', description, legacy_alias: `/api/${path}` },
    ])),
    generated_at: new Date().toISOString(),
  });
}

module.exports = withMiddleware(discoveryHandler, { endpoint: '/api' });
