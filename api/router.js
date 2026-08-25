const { setCorsHeaders } = require('./lib/middleware.js');

const handlers = {
  '': require('./index/route.js'),
  matches: require('./matches/route.js'),
  live: require('./live/route.js'),
  standings: require('./standings/route.js'),
  players: require('./players/route.js'),
  leaderboards: require('./leaderboards/route.js'),
  'team-stats': require('./team-stats/route.js'),
  teams: require('./teams/route.js'),
  'match-stats': require('./match-stats/route.js'),
  referees: require('./referees/route.js'),
  venues: require('./venues/route.js'),
  weather: require('./weather/route.js'),
  odds: require('./odds/route.js'),
  'odds-quotes': require('./odds-quotes/route.js'),
  seasons: require('./seasons/route.js'),
  health: require('./health/route.js'),
  analytics: require('./analytics/route.js'),
};

module.exports = async function router(req, res) {
  const queryResource = Array.isArray(req.query?.resource) ? req.query.resource[0] : req.query?.resource;
  const pathResource = String(req.url || '')
    .split('?')[0]
    .replace(/^\/api(?:\/v1)?\/?/, '')
    .replace(/^router\.js\/?/, '');
  const resource = String(queryResource ?? pathResource).replace(/^\/+|\/+$/g, '');
  const handler = handlers[resource];

  if (!handler) {
    setCorsHeaders(res);
    return res.status(404).json({
      error: 'Not Found',
      message: `Unknown API resource: ${resource || '(root)'}`,
      status: 404,
      discovery: '/api/v1',
    });
  }
  return handler(req, res);
};
