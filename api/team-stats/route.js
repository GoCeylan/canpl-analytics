const { withMiddleware } = require('../lib/middleware.js');
const { includes } = require('../lib/data.js');
const { CURRENT_SEASON, getOfficialTeamStats } = require('../lib/sdp.js');

async function teamStatsHandler(req, res, { track, errors, validateNumber }) {
  const seasonCheck = validateNumber(req.query.season, 'season', 2019, 2030);
  if (!seasonCheck.valid) return errors.badRequest(res, seasonCheck.error);
  const season = seasonCheck.value || CURRENT_SEASON;
  if (season !== CURRENT_SEASON) return errors.badRequest(res, `advanced team stats are currently available for ${CURRENT_SEASON}`);
  let teams = await getOfficialTeamStats(season, req.query.raw === 'true');
  if (req.query.team) teams = teams.filter((team) => includes(team.team, req.query.team));
  const sort = req.query.sort || 'points';
  if (teams.length && !(sort in teams[0])) return errors.badRequest(res, `unknown sort field: ${sort}`);
  const order = String(req.query.order || 'desc').toLowerCase();
  if (!['asc', 'desc'].includes(order)) return errors.badRequest(res, 'order must be asc or desc');
  teams.sort((a, b) => (order === 'asc' ? 1 : -1) * ((a[sort] || 0) - (b[sort] || 0)));
  track(200);
  return res.status(200).json({ season, count: teams.length, sort, order, teams, source: 'official-cpl-live' });
}

module.exports = withMiddleware(teamStatsHandler, { endpoint: '/api/team-stats', cache: 's-maxage=60, stale-while-revalidate=120' });
