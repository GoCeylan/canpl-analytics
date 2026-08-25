const { withMiddleware } = require('../lib/middleware.js');
const { includes, paginate, readCsv } = require('../lib/data.js');
const { CURRENT_SEASON, getOfficialMatches, normalizeTeam } = require('../lib/sdp.js');

const VALID_STATUSES = ['FINISHED', 'UPCOMING', 'LIVE', 'IN_PLAY', 'HALF_TIME', 'POSTPONED', 'CANCELLED', 'SUSPENDED'];

function historicalMatches() {
  const headerIndex = new Map();
  readCsv('data/matches/match_header_history.csv').forEach((row) => {
    if (row.match_id) headerIndex.set(row.match_id, row);
  });
  const unique = new Map();
  readCsv('data/matches/match_teamstats_history.csv').forEach((row) => {
    if (row.match_id && row.season) unique.set(row.match_id, row);
  });
  return [...unique.values()].map((row) => {
    const header = headerIndex.get(row.match_id);
    return {
      match_id: row.match_id,
      season_id: row.season_id,
      season: Number(row.season),
      date: row.date,
      kickoff_utc: null,
      status: 'FINISHED',
      phase: header?.phase || 'FULL_TIME',
      home_team: normalizeTeam(row.home_team),
      away_team: normalizeTeam(row.away_team),
      home_goals: Number(row.home_goals),
      away_goals: Number(row.away_goals),
      stadium: null,
      attendance: header?.attendance || null,
      win_reason: header?.win_reason || null,
      competition: 'cpl',
      source: 'archive',
      advanced_stats_available: row.has_data === 1,
    };
  });
}

function fallbackCurrentSchedule() {
  return readCsv('data/matches/cpl_all_with_ids.csv').map((row) => ({
    ...row,
    season: Number(row.season),
    home_team: normalizeTeam(row.home_team),
    away_team: normalizeTeam(row.away_team),
    competition: 'cpl',
    source: 'repository-snapshot',
  }));
}

async function loadMatches(requestedSeason) {
  const archive = historicalMatches();
  if (requestedSeason && requestedSeason !== CURRENT_SEASON) return archive;
  let current;
  try {
    current = (await getOfficialMatches(CURRENT_SEASON)).map((match) => ({ ...match, competition: 'cpl', source: 'official-cpl-live' }));
  } catch (error) {
    console.error('Official schedule unavailable; using repository snapshot:', error.message);
    current = fallbackCurrentSchedule();
  }
  return [...archive.filter((match) => match.season !== CURRENT_SEASON), ...current];
}

async function matchesHandler(req, res, { track, errors, validateNumber }) {
  const seasonCheck = validateNumber(req.query.season, 'season', 2019, 2030);
  if (!seasonCheck.valid) return errors.badRequest(res, seasonCheck.error);
  const status = req.query.status ? String(req.query.status).toUpperCase() : null;
  if (status && !VALID_STATUSES.includes(status)) return errors.badRequest(res, `status must be one of: ${VALID_STATUSES.join(', ')}`);
  if (req.query.from && req.query.to && req.query.from > req.query.to) return errors.badRequest(res, 'from must be before to');
  const order = String(req.query.order || 'asc').toLowerCase();
  if (!['asc', 'desc'].includes(order)) return errors.badRequest(res, 'order must be asc or desc');

  let matches = await loadMatches(seasonCheck.value);
  if (seasonCheck.value) matches = matches.filter((match) => match.season === seasonCheck.value);
  if (req.query.team) matches = matches.filter((match) => includes(`${match.home_team} ${match.away_team}`, req.query.team));
  if (req.query.match_id) matches = matches.filter((match) => match.match_id === req.query.match_id || includes(match.match_id, req.query.match_id));
  if (status) matches = matches.filter((match) => match.status === status);
  if (req.query.date) matches = matches.filter((match) => match.date === req.query.date);
  if (req.query.from) matches = matches.filter((match) => match.date >= req.query.from);
  if (req.query.to) matches = matches.filter((match) => match.date <= req.query.to);
  matches.sort((a, b) => (order === 'asc' ? 1 : -1) * (`${a.date}${a.kickoff_utc || ''}`.localeCompare(`${b.date}${b.kickoff_utc || ''}`)));

  const page = paginate(matches, req.query);
  track(200);
  return res.status(200).json({
    total: page.total, count: page.count, limit: page.limit, offset: page.offset,
    has_more: page.has_more, matches: page.items,
    coverage: { from: '2019-04-27', through: CURRENT_SEASON, current_season_live: true },
  });
}

module.exports = withMiddleware(matchesHandler, { endpoint: '/api/matches', cache: 's-maxage=60, stale-while-revalidate=120' });
