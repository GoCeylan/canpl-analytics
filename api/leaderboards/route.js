const { withMiddleware } = require('../lib/middleware.js');
const { applySeasonRatings } = require('../lib/ratings.js');
const { CURRENT_SEASON, getOfficialPlayers } = require('../lib/sdp.js');

const BOARDS = {
  rating: { label: 'Season rating', field: 'rating', eligible: true },
  goals: { label: 'Goals', field: 'goals' },
  assists: { label: 'Assists', field: 'assists' },
  goal_involvements: { label: 'Goal involvements', field: 'goal_involvements' },
  xg: { label: 'Expected goals', field: 'xg' },
  shots: { label: 'Shots', field: 'shots' },
  shots_on_target: { label: 'Shots on target', field: 'shots_on_target' },
  key_passes: { label: 'Key passes', field: 'key_passes' },
  successful_dribbles: { label: 'Successful dribbles', field: 'successful_dribbles' },
  tackles: { label: 'Tackles', field: 'tackles' },
  interceptions: { label: 'Interceptions', field: 'interceptions' },
  recoveries: { label: 'Recoveries', field: 'recoveries' },
  clearances: { label: 'Clearances', field: 'clearances' },
  saves: { label: 'Saves', field: 'saves' },
  pass_accuracy: { label: 'Pass accuracy', field: 'pass_accuracy' },
};

function buildBoard(players, name, limit, team, position) {
  const config = BOARDS[name];
  let rows = players;
  if (config.eligible) rows = rows.filter((player) => player.rating_eligible);
  if (team) rows = rows.filter((player) => player.team.toLowerCase().includes(team.toLowerCase()));
  if (position) rows = rows.filter((player) => player.position.toLowerCase().includes(position.toLowerCase()));
  rows = rows
    .filter((player) => Number(player[config.field]) > 0)
    .sort((a, b) => b[config.field] - a[config.field] || b.minutes - a.minutes)
    .slice(0, limit)
    .map((player, index) => ({
      rank: index + 1,
      player_id: player.player_id,
      name: player.name,
      team: player.team,
      position: player.position,
      value: player[config.field],
      minutes: player.minutes,
      appearances: player.appearances,
      rating: player.rating,
    }));
  return { metric: name, label: config.label, field: config.field, rows };
}

async function leaderboardsHandler(req, res, { track, errors, validateNumber }) {
  const limitCheck = validateNumber(req.query.limit || '10', 'limit', 1, 100);
  if (!limitCheck.valid) return errors.badRequest(res, limitCheck.error);
  const requested = String(req.query.metric || 'rating,goals,assists,goal_involvements').split(',').filter(Boolean);
  const invalid = requested.filter((name) => !BOARDS[name]);
  if (invalid.length) return errors.badRequest(res, `unknown metric(s): ${invalid.join(', ')}. Available: ${Object.keys(BOARDS).join(', ')}`);
  const players = applySeasonRatings(await getOfficialPlayers(CURRENT_SEASON));
  const boards = requested.map((name) => buildBoard(players, name, limitCheck.value, req.query.team, req.query.position));
  res.setHeader('Cache-Control', 's-maxage=60, stale-while-revalidate=120');
  track(200);
  return res.status(200).json({
    season: CURRENT_SEASON,
    count: boards.length,
    available_metrics: Object.keys(BOARDS),
    leaderboards: boards,
    source: 'official-cpl-live + CanadaSoccerAPI rating model',
  });
}

module.exports = withMiddleware(leaderboardsHandler, { endpoint: '/api/leaderboards', cache: 's-maxage=60, stale-while-revalidate=120' });
