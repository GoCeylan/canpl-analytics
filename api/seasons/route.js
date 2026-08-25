const { withMiddleware } = require('../lib/middleware.js');
const { SEASONS } = require('../lib/cplStats.js');
const { readCsv } = require('../lib/data.js');
const { CURRENT_SEASON } = require('../lib/sdp.js');

async function seasonsHandler(req, res, { track }) {
  const results = [...new Map(readCsv('data/matches/match_teamstats_history.csv')
    .filter((match) => match.match_id && match.season)
    .map((match) => [match.match_id, match])).values()];
  const schedules = readCsv('data/matches/cpl_all_with_ids.csv');
  const seasons = Object.keys(SEASONS).map(Number).sort().map((year) => {
    const finished = results.filter((match) => Number(match.season) === year).length;
    const scheduled = schedules.filter((match) => Number(match.season) === year).length;
    return {
      season: year,
      season_id: SEASONS[year],
      current: year === CURRENT_SEASON,
      matches_finished: finished,
      matches_scheduled: scheduled || finished,
      live_official_feeds: year === CURRENT_SEASON,
      coverage: {
        results: finished > 0,
        standings: true,
        match_stats: true,
        referees: year <= 2025,
        weather: year <= 2025,
        players: year === CURRENT_SEASON,
        team_stats: year === CURRENT_SEASON,
      },
    };
  });
  track(200);
  return res.status(200).json({ count: seasons.length, seasons });
}

module.exports = withMiddleware(seasonsHandler, { endpoint: '/api/seasons' });
