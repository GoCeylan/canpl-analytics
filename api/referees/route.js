const { withMiddleware } = require('../lib/middleware.js');
const { includes, paginate, readCsv } = require('../lib/data.js');

async function refereesHandler(req, res, { track, errors, validateNumber }) {
  const seasonCheck = validateNumber(req.query.season, 'season', 2019, 2030);
  if (!seasonCheck.valid) return errors.badRequest(res, seasonCheck.error);
  let assignments = [...new Map(readCsv('data/matches/cpl_referees_2019_2025.csv')
    .filter((row) => row.match_id)
    .map((row) => [row.match_id, row])).values()];
  if (seasonCheck.value) assignments = assignments.filter((row) => row.season === seasonCheck.value);
  if (req.query.referee) assignments = assignments.filter((row) => includes(row.referee_name, req.query.referee));
  if (req.query.team) assignments = assignments.filter((row) => includes(`${row.home_team} ${row.away_team}`, req.query.team));
  if (req.query.match_id) assignments = assignments.filter((row) => row.match_id === req.query.match_id);

  if (req.query.summary === 'true') {
    const map = new Map();
    assignments.forEach((row) => {
      const current = map.get(row.referee_id) || {
        referee_id: row.referee_id,
        name: row.referee_name,
        short_name: row.referee_short_name,
        matches: 0,
        seasons: new Set(),
      };
      current.matches += 1;
      current.seasons.add(row.season);
      map.set(row.referee_id, current);
    });
    const referees = [...map.values()]
      .map((row) => ({ ...row, seasons: [...row.seasons].sort() }))
      .sort((a, b) => b.matches - a.matches || a.name.localeCompare(b.name));
    track(200);
    return res.status(200).json({ count: referees.length, referees });
  }

  assignments.sort((a, b) => String(b.date).localeCompare(String(a.date)));
  const page = paginate(assignments, req.query);
  track(200);
  return res.status(200).json({
    total: page.total, count: page.count, limit: page.limit, offset: page.offset,
    has_more: page.has_more, assignments: page.items,
  });
}

module.exports = withMiddleware(refereesHandler, { endpoint: '/api/referees', cache: 's-maxage=86400, stale-while-revalidate=604800' });
