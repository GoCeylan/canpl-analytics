/**
 * GET /api/form
 * Returns recent form (last N matches) for all teams or a specific team.
 *
 * Query params:
 *   season   - filter to season (default: most recent)
 *   team     - filter to specific team (optional)
 *   n        - number of matches (default: 6, max: 20)
 *
 * Response:
 *   { teams: [{ team, form, w, d, l, gf, ga, gd, pts, matches[] }] }
 */

const { readFileSync } = require('fs');
const { join } = require('path');
const { withMiddleware } = require('../lib/middleware.js');

function parseCSVLine(line) {
  const values = [];
  let current = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') { inQuotes = !inQuotes; }
    else if (char === ',' && !inQuotes) { values.push(current); current = ''; }
    else { current += char; }
  }
  values.push(current);
  return values;
}

function loadMatches() {
  const dataPath = join(process.cwd(), 'data', 'matches', 'cpl_all_with_ids.csv');
  const csv = readFileSync(dataPath, 'utf-8').trim().replace(/\r/g, '').split('\n');
  const headers = csv[0].split(',');
  return csv.slice(1)
    .map(line => {
      const vals = parseCSVLine(line);
      const obj = {};
      headers.forEach((h, i) => {
        obj[h] = vals[i] ?? '';
      });
      obj.season = parseInt(obj.season, 10);
      obj.home_goals = parseInt(obj.home_goals, 10);
      obj.away_goals = parseInt(obj.away_goals, 10);
      return obj;
    })
    .filter(m => m.date && m.match_id && m.status === 'FINISHED');
}

async function formHandler(req, res, { track, errors, validateNumber }) {
  const { season, team, n = '6' } = req.query;

  const nValidation = validateNumber(n, 'n', 1, 20);
  if (!nValidation.valid) {
    track(400);
    return errors.badRequest(res, nValidation.error);
  }

  const seasonValidation = validateNumber(season, 'season', 2019, 2030);
  if (!seasonValidation.valid) {
    track(400);
    return errors.badRequest(res, seasonValidation.error);
  }

  let matches = loadMatches();

  // Filter by season if provided
  if (seasonValidation.value !== undefined) {
    matches = matches.filter(m => m.season === seasonValidation.value);
  }

  // Sort by date ascending
  matches.sort((a, b) => a.date.localeCompare(b.date));

  // Collect all teams
  const teamSet = new Set();
  for (const m of matches) {
    teamSet.add(m.home_team);
    teamSet.add(m.away_team);
  }

  const numMatches = nValidation.value ?? 6;

  // Build form for each team
  const formData = [];
  for (const teamName of teamSet) {
    if (team && !teamName.toLowerCase().includes(team.toLowerCase())) continue;

    // Get all matches for this team, in chronological order
    const teamMatches = matches.filter(
      m => m.home_team === teamName || m.away_team === teamName
    );

    // Take last N
    const recent = teamMatches.slice(-numMatches);

    let w = 0, d = 0, l = 0, gf = 0, ga = 0;
    const formChars = [];
    const matchDetails = [];

    for (const m of recent) {
      const isHome = m.home_team === teamName;
      const myGoals = isHome ? m.home_goals : m.away_goals;
      const oppGoals = isHome ? m.away_goals : m.home_goals;
      const opp = isHome ? m.away_team : m.home_team;

      gf += myGoals;
      ga += oppGoals;

      let result;
      if (myGoals > oppGoals)  { w++; result = 'W'; }
      else if (myGoals < oppGoals) { l++; result = 'L'; }
      else                     { d++; result = 'D'; }

      formChars.push(result);
      matchDetails.push({
        date: m.date,
        opponent: opp,
        home_away: isHome ? 'H' : 'A',
        goals_for: myGoals,
        goals_against: oppGoals,
        result,
        score: isHome ? `${m.home_goals}-${m.away_goals}` : `${m.away_goals}-${m.home_goals}`,
      });
    }

    formData.push({
      team: teamName,
      form: formChars.join(''),           // e.g. "WWDLW"
      played: recent.length,
      w, d, l, gf, ga,
      gd: gf - ga,
      pts: w * 3 + d,
      matches: matchDetails,
    });
  }

  // Sort by pts desc, then gd desc
  formData.sort((a, b) => b.pts - a.pts || b.gd - a.gd);

  track(200);
  res.setHeader('Cache-Control', 's-maxage=1800, stale-while-revalidate');
  return res.status(200).json({
    n: numMatches,
    season: seasonValidation.value ?? 'all',
    teams: formData,
  });
}

module.exports = withMiddleware(formHandler, { endpoint: '/api/form' });
