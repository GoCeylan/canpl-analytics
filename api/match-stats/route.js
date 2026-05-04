const { readFileSync, existsSync } = require('fs');
const { join } = require('path');
const { withMiddleware } = require('../lib/middleware.js');
const { fetchTeamStats, calculateXG, SEASONS } = require('../lib/cplStats.js');

const DATA_DIR = join(process.cwd(), 'data', 'matches');

// ---------------------------------------------------------------------------
// CSV loaders — called once at startup, results cached in module scope
// ---------------------------------------------------------------------------

let _teamstatsCache = null;   // map: match_id -> row object
let _headerCache    = null;   // map: match_id -> row object

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

function parseCsvToMap(filePath, keyField) {
  if (!existsSync(filePath)) return {};
  const lines = readFileSync(filePath, 'utf-8').trim().replace(/\r/g, '').split('\n');
  const headers = lines[0].split(',');
  const map = {};
  for (let i = 1; i < lines.length; i++) {
    const values = parseCSVLine(lines[i]);
    const obj = {};
    headers.forEach((h, idx) => {
      const v = values[idx];
      // Coerce numeric fields
      const num = parseFloat(v);
      obj[h] = (v !== '' && v !== undefined && !isNaN(num)) ? num : (v || null);
    });
    if (obj[keyField]) map[obj[keyField]] = obj;
  }
  return map;
}

function getTeamstatsCache() {
  if (!_teamstatsCache) {
    _teamstatsCache = parseCsvToMap(join(DATA_DIR, 'match_teamstats_history.csv'), 'match_id');
  }
  return _teamstatsCache;
}

function getHeaderCache() {
  if (!_headerCache) {
    _headerCache = parseCsvToMap(join(DATA_DIR, 'match_header_history.csv'), 'match_id');
  }
  return _headerCache;
}

// ---------------------------------------------------------------------------
// Shape CSV row into clean API response
// ---------------------------------------------------------------------------

function buildStatsResponse(tsRow, hdRow) {
  const response = {
    match_id:   tsRow.match_id,
    season:     tsRow.season,
    date:       tsRow.date,
    home_team:  tsRow.home_team,
    away_team:  tsRow.away_team,
    home_goals: tsRow.home_goals,
    away_goals: tsRow.away_goals,
    has_data:   tsRow.has_data === 1 || tsRow.has_data === '1',
    source:     'csv',
  };

  if (response.has_data) {
    response.team_stats = {
      home: extractTeamStats(tsRow, 'home'),
      away: extractTeamStats(tsRow, 'away'),
    };
  }

  if (hdRow) {
    response.attendance  = hdRow.attendance   ? parseInt(hdRow.attendance, 10)   : null;
    response.phase       = hdRow.phase        || null;
    response.win_reason  = hdRow.win_reason   || null;
    response.home_scorers = hdRow.home_scorers || null;
    response.away_scorers = hdRow.away_scorers || null;
  }

  return response;
}

const STAT_FIELDS = [
  'possession_pct', 'shots', 'shots_on_target', 'shots_inside_box',
  'shots_outside_box', 'blocked_shots', 'big_chances', 'chances_created',
  'xg_api', 'xg_calc', 'passes', 'pass_accuracy_pct', 'corners', 'crosses',
  'fouls', 'yellow_cards', 'red_cards', 'offsides', 'saves', 'clearances',
  'duels_won', 'tackles', 'tackles_successful', 'key_passes', 'penalty_goals',
  'own_goals', 'touches_opp_box', 'aerial_duels_won_pct', 'counter_attacks',
  'goals',
];

function extractTeamStats(row, side) {
  const stats = {};
  STAT_FIELDS.forEach(field => {
    const key = `${side}_${field}`;
    if (row[key] !== undefined && row[key] !== null) {
      stats[field] = row[key];
    }
  });
  return stats;
}

// ---------------------------------------------------------------------------
// Live API fallback (for 2026+ matches not yet in CSV)
// ---------------------------------------------------------------------------

async function fetchLiveStats(matchId, seasonId) {
  const data = await fetchTeamStats(matchId, seasonId);
  if (!data) return null;

  const statsById = {};
  (data.stats || []).forEach(s => { statsById[s.statsId] = s; });

  function val(id, side) {
    const s = statsById[id];
    return s ? (side === 'home' ? s.statsValueHome : s.statsValueAway) : null;
  }

  return {
    source: 'live',
    has_data: true,
    team_stats: {
      home: {
        possession_pct:       val('possession-perc', 'home'),
        shots:                val('shots', 'home'),
        shots_on_target:      val('shots-on-goal', 'home'),
        shots_inside_box:     val('shots-at-goal-inside-box', 'home'),
        shots_outside_box:    val('shots-at-goal-outside-box', 'home'),
        blocked_shots:        val('blocked-shots', 'home'),
        big_chances:          val('big-chances', 'home'),
        chances_created:      val('chances-created', 'home'),
        xg_api:               val('expected-goals', 'home'),
        xg_calc:              calculateXG(statsById).home,
        passes:               val('total-passes', 'home'),
        pass_accuracy_pct:    val('passing-accuracy-perc', 'home'),
        corners:              val('corners', 'home'),
        crosses:              val('crosses', 'home'),
        fouls:                val('fouls', 'home'),
        yellow_cards:         val('yellow-cards', 'home'),
        red_cards:            val('red-cards', 'home'),
        offsides:             val('offsides', 'home'),
        saves:                val('saves', 'home'),
        clearances:           val('clearences', 'home'),
        duels_won:            val('duels-won', 'home'),
        tackles:              val('tackles-total', 'home'),
        tackles_successful:   val('tackles-successful', 'home'),
        key_passes:           val('key-passes', 'home'),
        penalty_goals:        val('penalty-goals', 'home'),
        own_goals:            val('own-goals', 'home'),
        touches_opp_box:      val('touches-opponent-box', 'home'),
        aerial_duels_won_pct: val('aerial-duels-won-perc', 'home'),
        counter_attacks:      val('counter-attacks', 'home'),
        goals:                val('goals-scored', 'home'),
      },
      away: {
        possession_pct:       val('possession-perc', 'away'),
        shots:                val('shots', 'away'),
        shots_on_target:      val('shots-on-goal', 'away'),
        shots_inside_box:     val('shots-at-goal-inside-box', 'away'),
        shots_outside_box:    val('shots-at-goal-outside-box', 'away'),
        blocked_shots:        val('blocked-shots', 'away'),
        big_chances:          val('big-chances', 'away'),
        chances_created:      val('chances-created', 'away'),
        xg_api:               val('expected-goals', 'away'),
        xg_calc:              calculateXG(statsById).away,
        passes:               val('total-passes', 'away'),
        pass_accuracy_pct:    val('passing-accuracy-perc', 'away'),
        corners:              val('corners', 'away'),
        crosses:              val('crosses', 'away'),
        fouls:                val('fouls', 'away'),
        yellow_cards:         val('yellow-cards', 'away'),
        red_cards:            val('red-cards', 'away'),
        offsides:             val('offsides', 'away'),
        saves:                val('saves', 'away'),
        clearances:           val('clearences', 'away'),
        duels_won:            val('duels-won', 'away'),
        tackles:              val('tackles-total', 'away'),
        tackles_successful:   val('tackles-successful', 'away'),
        key_passes:           val('key-passes', 'away'),
        penalty_goals:        val('penalty-goals', 'away'),
        own_goals:            val('own-goals', 'away'),
        touches_opp_box:      val('touches-opponent-box', 'away'),
        aerial_duels_won_pct: val('aerial-duels-won-perc', 'away'),
        counter_attacks:      val('counter-attacks', 'away'),
        goals:                val('goals-scored', 'away'),
      },
    },
  };
}

// ---------------------------------------------------------------------------
// Route handler
// ---------------------------------------------------------------------------

async function matchStatsHandler(req, res, { track, errors, validateNumber }) {
  const { match_id, season } = req.query;

  const tsCache = getTeamstatsCache();
  const hdCache = getHeaderCache();

  // ------------------------------------------------------------------
  // BULK mode: ?season=2024  → returns all matches for that season
  // ------------------------------------------------------------------
  if (!match_id && season) {
    const seasonValidation = validateNumber(season, 'season', 2019, 2030);
    if (!seasonValidation.valid) {
      track(400);
      return errors.badRequest(res, seasonValidation.error);
    }

    const seasonNum = seasonValidation.value;
    const rows = Object.values(tsCache).filter(r => r.season === seasonNum || r.season === String(seasonNum));

    if (rows.length === 0) {
      track(404);
      return errors.notFound(res, `No match stats found for season ${seasonNum}`);
    }

    const results = rows.map(tsRow => buildStatsResponse(tsRow, hdCache[tsRow.match_id]));
    results.sort((a, b) => (a.date || '').localeCompare(b.date || ''));

    track(200);
    return res.status(200).json({
      season: seasonNum,
      count: results.length,
      matches: results,
    });
  }

  // ------------------------------------------------------------------
  // SINGLE match mode: ?match_id=cpl::Football_Match::...
  // ------------------------------------------------------------------
  if (!match_id) {
    track(400);
    return errors.badRequest(res, 'match_id or season parameter is required');
  }

  // Try CSV cache first
  const tsRow = tsCache[match_id];
  const hdRow = hdCache[match_id];

  if (tsRow) {
    const response = buildStatsResponse(tsRow, hdRow);
    track(200);
    return res.status(200).json(response);
  }

  // Not in CSV → try live API (covers 2026 in-season matches)
  // Resolve season_id from match_id via matches CSV
  const matchesPath = join(DATA_DIR, 'cpl_all_with_ids.csv');
  if (!existsSync(matchesPath)) {
    track(404);
    return errors.notFound(res, `Match ${match_id} not found`);
  }

  const matchLines = readFileSync(matchesPath, 'utf-8').trim().replace(/\r/g, '').split('\n');
  const matchHeaders = matchLines[0].split(',');
  let seasonId = null;
  let matchStatus = null;

  for (let i = 1; i < matchLines.length; i++) {
    const vals = parseCSVLine(matchLines[i]);
    if (vals[0] === match_id) {
      const row = {};
      matchHeaders.forEach((h, idx) => { row[h] = vals[idx]; });
      seasonId = row.season_id;
      matchStatus = row.status;
      break;
    }
  }

  if (!seasonId) {
    track(404);
    return errors.notFound(res, `Match ${match_id} not found`);
  }

  if (matchStatus !== 'FINISHED') {
    track(200);
    return res.status(200).json({
      match_id,
      source: 'csv',
      has_data: false,
      message: 'Match not yet played',
    });
  }

  const liveStats = await fetchLiveStats(match_id, seasonId);
  if (!liveStats) {
    track(404);
    return errors.notFound(res, `Stats not available for match ${match_id}`);
  }

  track(200);
  return res.status(200).json({ match_id, source: 'live', ...liveStats });
}

module.exports = withMiddleware(matchStatsHandler, { endpoint: '/api/match-stats' });
