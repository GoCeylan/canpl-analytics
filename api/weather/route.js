const { withMiddleware } = require('../lib/middleware.js');
const { includes, paginate, readCsv } = require('../lib/data.js');

async function weatherHandler(req, res, { track, errors }) {
  let observations = readCsv('data/matches/cpl_weather_history.csv');
  if (req.query.team) observations = observations.filter((row) => includes(`${row.home_team} ${row.away_team}`, req.query.team));
  if (req.query.date) observations = observations.filter((row) => row.date === req.query.date);
  if (req.query.from) observations = observations.filter((row) => row.date >= req.query.from);
  if (req.query.to) observations = observations.filter((row) => row.date <= req.query.to);
  if (req.query.from && req.query.to && req.query.from > req.query.to) return errors.badRequest(res, 'from must be before to');
  observations.sort((a, b) => String(b.date).localeCompare(String(a.date)));
  const page = paginate(observations, req.query);
  track(200);
  return res.status(200).json({
    total: page.total, count: page.count, limit: page.limit, offset: page.offset,
    has_more: page.has_more, observations: page.items,
    units: { temperature: 'celsius', wind: 'km/h', precipitation: 'mm' },
    source: 'historical weather archive',
  });
}

module.exports = withMiddleware(weatherHandler, { endpoint: '/api/weather', cache: 's-maxage=86400, stale-while-revalidate=604800' });
