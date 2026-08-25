const { withMiddleware } = require('../lib/middleware.js');
const { CURRENT_SEASON, getOfficialMatches } = require('../lib/sdp.js');

async function liveHandler(req, res, { track, errors, validateNumber }) {
  const seasonCheck = validateNumber(req.query.season, 'season', 2019, 2030);
  if (!seasonCheck.valid) return errors.badRequest(res, seasonCheck.error);
  const season = seasonCheck.value || CURRENT_SEASON;
  if (season !== CURRENT_SEASON) return errors.badRequest(res, 'live is available for the current season only');

  const matches = await getOfficialMatches(season);
  const now = Date.now();
  const windowHours = Number.parseInt(req.query.window_hours, 10) || 48;
  const windowMs = Math.min(Math.max(windowHours, 1), 168) * 60 * 60 * 1000;
  const activeStatuses = new Set(['LIVE', 'IN_PLAY', 'HALF_TIME', 'PAUSED', 'SUSPENDED']);
  let selected = matches.filter((match) => {
    const kickoff = new Date(match.kickoff_utc).getTime();
    return activeStatuses.has(match.status) || Math.abs(kickoff - now) <= windowMs;
  });
  if (req.query.all === 'true') selected = matches;
  if (req.query.team) {
    const query = req.query.team.toLowerCase();
    selected = selected.filter((match) => `${match.home_team} ${match.away_team}`.toLowerCase().includes(query));
  }

  const liveCount = selected.filter((match) => activeStatuses.has(match.status)).length;
  res.setHeader('Cache-Control', 's-maxage=15, stale-while-revalidate=30');
  track(200);
  return res.status(200).json({
    season,
    live_count: liveCount,
    count: selected.length,
    window_hours: req.query.all === 'true' ? null : Math.min(Math.max(windowHours, 1), 168),
    matches: selected,
    source: 'official-cpl-live',
    updated_at: new Date().toISOString(),
  });
}

module.exports = withMiddleware(liveHandler, { endpoint: '/api/live', cache: 's-maxage=15, stale-while-revalidate=30' });
