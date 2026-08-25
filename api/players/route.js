const { withMiddleware } = require('../lib/middleware.js');
const { paginate, includes } = require('../lib/data.js');
const { applySeasonRatings } = require('../lib/ratings.js');
const { CURRENT_SEASON, getOfficialPlayers } = require('../lib/sdp.js');

const SORT_FIELDS = new Set([
  'rating', 'rating_rank', 'name', 'team', 'position', 'appearances', 'starts', 'minutes',
  'goals', 'assists', 'goal_involvements', 'xg', 'shots', 'shots_on_target', 'key_passes',
  'successful_dribbles', 'tackles', 'interceptions', 'recoveries', 'clearances', 'saves',
  'pass_accuracy', 'yellow_cards', 'red_cards',
]);

async function playersHandler(req, res, { track, errors, validateNumber }) {
  const seasonCheck = validateNumber(req.query.season, 'season', 2019, 2030);
  if (!seasonCheck.valid) return errors.badRequest(res, seasonCheck.error);
  const season = seasonCheck.value || CURRENT_SEASON;
  if (season !== CURRENT_SEASON) return errors.badRequest(res, `player stats are currently available for ${CURRENT_SEASON}`);
  const minMinutesCheck = validateNumber(req.query.min_minutes, 'min_minutes', 0, 10000);
  if (!minMinutesCheck.valid) return errors.badRequest(res, minMinutesCheck.error);
  const sort = req.query.sort || 'rating';
  if (!SORT_FIELDS.has(sort)) return errors.badRequest(res, `sort must be one of: ${[...SORT_FIELDS].join(', ')}`);
  const order = String(req.query.order || (sort === 'name' || sort === 'team' || sort === 'position' ? 'asc' : 'desc')).toLowerCase();
  if (!['asc', 'desc'].includes(order)) return errors.badRequest(res, 'order must be asc or desc');

  let players = applySeasonRatings(await getOfficialPlayers(season));
  if (req.query.team) players = players.filter((player) => includes(player.team, req.query.team));
  if (req.query.position) players = players.filter((player) => includes(player.position, req.query.position));
  if (req.query.search) players = players.filter((player) => includes(`${player.name} ${player.team}`, req.query.search));
  if (minMinutesCheck.value !== undefined) players = players.filter((player) => player.minutes >= minMinutesCheck.value);
  if (req.query.eligible === 'true') players = players.filter((player) => player.rating_eligible);
  players.sort((a, b) => {
    const av = a[sort] ?? (order === 'asc' ? '\uffff' : -Infinity);
    const bv = b[sort] ?? (order === 'asc' ? '\uffff' : -Infinity);
    const comparison = typeof av === 'string' ? av.localeCompare(bv) : av - bv;
    return order === 'asc' ? comparison : -comparison;
  });
  const page = paginate(players, req.query, 50, 250);
  res.setHeader('Cache-Control', 's-maxage=60, stale-while-revalidate=120');
  track(200);
  return res.status(200).json({
    season,
    total: page.total,
    count: page.count,
    limit: page.limit,
    offset: page.offset,
    has_more: page.has_more,
    sort,
    order,
    rating_methodology: {
      scale: '0-10',
      eligible_minutes: 270,
      peer_group: 'position',
      areas: ['attack', 'creativity', 'possession', 'defending', 'discipline'],
      reliability_minutes: 720,
    },
    players: page.items,
    source: 'official-cpl-live',
  });
}

module.exports = withMiddleware(playersHandler, { endpoint: '/api/players', cache: 's-maxage=60, stale-while-revalidate=120' });
