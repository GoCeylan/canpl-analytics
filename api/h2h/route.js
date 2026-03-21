/**
 * GET /api/h2h
 * Returns head-to-head record between two teams.
 *
 * Query params:
 *   home   - first team (required)
 *   away   - second team (required)
 *   season - filter to season (optional)
 *   limit  - max matches to return (default: 20)
 *
 * Response:
 *   { home, away, record: { home_wins, draws, away_wins }, matches[] }
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
      headers.forEach((h, i) => { obj[h] = vals[i] ?? ''; });
      obj.season = parseInt(obj.season, 10);
      obj.home_goals = parseInt(obj.home_goals, 10);
      obj.away_goals = parseInt(obj.away_goals, 10);
      return obj;
    })
    .filter(m => m.date && m.match_id && m.status === 'FINISHED');
}

async function h2hHandler(req, res, { track, errors, validateNumber }) {
  const { home, away, season, limit = '20' } = req.query;

  if (!home || !away) {
    track(400);
    return errors.badRequest(res, 'Both "home" and "away" team parameters are required');
  }

  const limitValidation = validateNumber(limit, 'limit', 1, 100);
  if (!limitValidation.valid) {
    track(400);
    return errors.badRequest(res, limitValidation.error);
  }

  const seasonValidation = validateNumber(season, 'season', 2019, 2030);
  if (!seasonValidation.valid) {
    track(400);
    return errors.badRequest(res, seasonValidation.error);
  }

  let matches = loadMatches();

  if (seasonValidation.value !== undefined) {
    matches = matches.filter(m => m.season === seasonValidation.value);
  }

  const homeLower = home.toLowerCase();
  const awayLower = away.toLowerCase();

  // Find all meetings between these two teams (in either direction)
  const h2hMatches = matches.filter(m => {
    const hName = m.home_team.toLowerCase();
    const aName = m.away_team.toLowerCase();
    return (
      (hName.includes(homeLower) && aName.includes(awayLower)) ||
      (hName.includes(awayLower) && aName.includes(homeLower))
    );
  });

  h2hMatches.sort((a, b) => b.date.localeCompare(a.date));

  // For the record, treat "home" param as team1 and "away" as team2
  let team1Wins = 0, draws = 0, team2Wins = 0;
  let team1Goals = 0, team2Goals = 0;

  const matchDetails = h2hMatches.slice(0, limitValidation.value ?? 20).map(m => {
    const hLower = m.home_team.toLowerCase();
    const isTeam1Home = hLower.includes(homeLower);

    const t1Goals = isTeam1Home ? m.home_goals : m.away_goals;
    const t2Goals = isTeam1Home ? m.away_goals : m.home_goals;
    team1Goals += t1Goals;
    team2Goals += t2Goals;

    let winner;
    if (t1Goals > t2Goals)      { team1Wins++; winner = 'team1'; }
    else if (t1Goals < t2Goals) { team2Wins++; winner = 'team2'; }
    else                         { draws++;     winner = 'draw'; }

    return {
      date: m.date,
      season: m.season,
      venue: m.venue,
      home_team: m.home_team,
      away_team: m.away_team,
      home_goals: m.home_goals,
      away_goals: m.away_goals,
      winner,
    };
  });

  // Find canonical team names from matches
  const team1Name = h2hMatches.length > 0
    ? (h2hMatches[0].home_team.toLowerCase().includes(homeLower)
        ? h2hMatches[0].home_team
        : h2hMatches[0].away_team)
    : home;

  const team2Name = h2hMatches.length > 0
    ? (h2hMatches[0].home_team.toLowerCase().includes(awayLower)
        ? h2hMatches[0].home_team
        : h2hMatches[0].away_team)
    : away;

  track(200);
  res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate');
  return res.status(200).json({
    team1: team1Name,
    team2: team2Name,
    total_meetings: h2hMatches.length,
    record: {
      team1_wins: team1Wins,
      draws,
      team2_wins: team2Wins,
      team1_goals: team1Goals,
      team2_goals: team2Goals,
    },
    matches: matchDetails,
  });
}

module.exports = withMiddleware(h2hHandler, { endpoint: '/api/h2h' });
