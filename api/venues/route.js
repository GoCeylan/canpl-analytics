const { withMiddleware } = require('../lib/middleware.js');
const { includes, readCsv } = require('../lib/data.js');

async function venuesHandler(req, res, { track, errors }) {
  if (req.query.active_only !== undefined && !['true', 'false'].includes(req.query.active_only)) {
    return errors.badRequest(res, 'active_only must be true or false');
  }
  let venues = readCsv('data/venues/stadium_info.csv');
  if (req.query.active_only === 'true') venues = venues.filter((venue) => venue.status === 'active');
  if (req.query.team) venues = venues.filter((venue) => includes(venue.team, req.query.team));
  if (req.query.city) venues = venues.filter((venue) => includes(venue.city, req.query.city));
  if (req.query.surface) venues = venues.filter((venue) => includes(venue.surface, req.query.surface));
  venues.sort((a, b) => a.team.localeCompare(b.team));
  track(200);
  return res.status(200).json({ count: venues.length, venues, source: 'curated' });
}

module.exports = withMiddleware(venuesHandler, { endpoint: '/api/venues', cache: 's-maxage=86400, stale-while-revalidate=604800' });
