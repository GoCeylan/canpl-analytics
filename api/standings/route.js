const { withMiddleware } = require('../lib/middleware.js');
const { readCsv } = require('../lib/data.js');
const { CURRENT_SEASON, getOfficialStandings } = require('../lib/sdp.js');

function calculateSnapshot(season) {
  const teams = new Map();
  const matches = readCsv('data/matches/cpl_all.csv').filter((row) => row.season === season);
  const get = (name) => {
    if (!teams.has(name)) teams.set(name, { team: name, played: 0, wins: 0, draws: 0, losses: 0, goals_for: 0, goals_against: 0, points: 0 });
    return teams.get(name);
  };
  matches.forEach((match) => {
    const home = get(match.home_team); const away = get(match.away_team);
    home.played += 1; away.played += 1;
    home.goals_for += match.home_goals; home.goals_against += match.away_goals;
    away.goals_for += match.away_goals; away.goals_against += match.home_goals;
    if (match.home_goals > match.away_goals) { home.wins += 1; home.points += 3; away.losses += 1; }
    else if (match.home_goals < match.away_goals) { away.wins += 1; away.points += 3; home.losses += 1; }
    else { home.draws += 1; away.draws += 1; home.points += 1; away.points += 1; }
  });
  return [...teams.values()]
    .map((team) => ({ ...team, goal_difference: team.goals_for - team.goals_against }))
    .sort((a, b) => b.points - a.points || b.goal_difference - a.goal_difference || b.goals_for - a.goals_for)
    .map((team, index) => ({ position: index + 1, ...team }));
}

async function standingsFor(season) {
  if (season === CURRENT_SEASON) {
    try {
      return { rows: await getOfficialStandings(season), source: 'official-cpl-live' };
    } catch (error) {
      const fallback = calculateSnapshot(season);
      if (fallback.length) return { rows: fallback, source: 'repository-snapshot' };
      throw error;
    }
  }
  return { rows: readCsv(`data/standings_${season}_api.csv`), source: 'official-cpl-archive' };
}

async function standingsHandler(req, res, { track, errors, validateNumber }) {
  const seasonCheck = validateNumber(req.query.season, 'season', 2019, CURRENT_SEASON);
  if (!seasonCheck.valid) return errors.badRequest(res, seasonCheck.error);
  if (seasonCheck.value) {
    const result = await standingsFor(seasonCheck.value);
    if (!result.rows.length) return errors.notFound(res, `No standings available for season ${seasonCheck.value}`);
    track(200);
    return res.status(200).json({ season: seasonCheck.value, standings: result.rows, source: result.source });
  }
  const seasons = Array.from({ length: CURRENT_SEASON - 2019 + 1 }, (_, index) => 2019 + index);
  const entries = await Promise.all(seasons.map(async (season) => [season, await standingsFor(season)]));
  const standings = Object.fromEntries(entries.map(([season, result]) => [season, result.rows]));
  track(200);
  return res.status(200).json({ seasons, standings, current_season_live: true });
}

module.exports = withMiddleware(standingsHandler, { endpoint: '/api/standings', cache: 's-maxage=60, stale-while-revalidate=120' });
