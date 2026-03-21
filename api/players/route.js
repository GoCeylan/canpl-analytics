/**
 * GET /api/players
 * Returns player stats for a CPL season from the official SDP API.
 * Proxies and caches CPL SDP API player stats.
 *
 * Query params:
 *   season - year (default: 2026)
 *   team   - filter by team name (optional)
 *   stat   - sort by stat: goals (default), assists, minutes, shots
 *   limit  - max players to return (default: 20, max: 100)
 *
 * Response:
 *   { season, count, players[] }
 */

const { withMiddleware } = require('../lib/middleware.js');

const SEASONS = {
  2019: 'cpl::Football_Season::c8c9bdc288f34aa89073a8bd89d2da3e',
  2020: 'cpl::Football_Season::11aa5cc094d0481fa8e73d326763584f',
  2021: 'cpl::Football_Season::2f07c39671b84933ad7bb1e1958a7427',
  2022: 'cpl::Football_Season::046f0ab31ba641c7b7bf27eb0dda4b9d',
  2023: 'cpl::Football_Season::fc0855108c9044218a84fc5d2bee0000',
  2024: 'cpl::Football_Season::6fb9e6fae4f24ce9bf4fa3172616a762',
  2025: 'cpl::Football_Season::fd43e1d61dfe4396a7356bc432de0007',
  2026: 'cpl::Football_Season::c479ab0916a24c3390f1ce2c021ace54',
};

const SDP_BASE = 'https://api-sdp.canpl.ca/v1/cpl/football';

// In-memory cache to avoid hitting SDP API too often
const _cache = {};
const CACHE_TTL_MS = 30 * 60 * 1000; // 30 minutes

async function fetchSDPPlayers(seasonId) {
  const now = Date.now();
  if (_cache[seasonId] && now - _cache[seasonId].ts < CACHE_TTL_MS) {
    return _cache[seasonId].data;
  }

  const url = `${SDP_BASE}/seasons/${seasonId}/stats/players?locale=en-US`;
  const res = await fetch(url, {
    headers: {
      Accept: 'application/json',
      Origin: 'https://canpl.ca',
      Referer: 'https://canpl.ca/',
    },
  });

  if (!res.ok) {
    throw new Error(`SDP API error: ${res.status} for season ${seasonId}`);
  }

  const data = await res.json();
  _cache[seasonId] = { ts: now, data };
  return data;
}

function parsePlayerStats(rawData) {
  // SDP player stats format varies but typically includes playerStats array
  const rawPlayers = rawData.playerStats ?? rawData.players ?? rawData.stats ?? [];

  return rawPlayers.map(p => {
    const stats = {};
    if (Array.isArray(p.stats)) {
      for (const s of p.stats) {
        stats[s.statsId] = s.statsValue ?? s.value ?? 0;
      }
    }

    return {
      player_id: p.playerId ?? p.id ?? '',
      name: p.playerName ?? p.name ?? p.fullName ?? 'Unknown',
      team: p.teamName ?? p.team?.officialName ?? p.clubName ?? '',
      position: p.positionName ?? p.position ?? '',
      nationality: p.nationality ?? '',
      goals: parseInt(stats['goals'] ?? stats['goal'] ?? p.goals ?? 0, 10),
      assists: parseInt(stats['assists'] ?? stats['assist'] ?? p.assists ?? 0, 10),
      minutes_played: parseInt(stats['minutes-played'] ?? stats['minutesPlayed'] ?? p.minutesPlayed ?? 0, 10),
      appearances: parseInt(stats['appearances'] ?? p.appearances ?? 0, 10),
      shots: parseInt(stats['shots-at-goal'] ?? stats['shots'] ?? 0, 10),
      shots_on_target: parseInt(stats['shots-on-goal'] ?? 0, 10),
      yellow_cards: parseInt(stats['yellow-cards'] ?? 0, 10),
      red_cards: parseInt(stats['red-cards'] ?? 0, 10),
    };
  });
}

const VALID_SORT_STATS = ['goals', 'assists', 'minutes_played', 'appearances', 'shots'];

async function playersHandler(req, res, { track, errors, validateNumber }) {
  const { season = '2026', team, stat = 'goals', limit = '20' } = req.query;

  const seasonValidation = validateNumber(season, 'season', 2019, 2030);
  if (!seasonValidation.valid) {
    track(400);
    return errors.badRequest(res, seasonValidation.error);
  }

  const limitValidation = validateNumber(limit, 'limit', 1, 100);
  if (!limitValidation.valid) {
    track(400);
    return errors.badRequest(res, limitValidation.error);
  }

  if (!VALID_SORT_STATS.includes(stat)) {
    track(400);
    return errors.badRequest(res, `stat must be one of: ${VALID_SORT_STATS.join(', ')}`);
  }

  const seasonYear = seasonValidation.value ?? 2026;
  const seasonId = SEASONS[seasonYear];
  if (!seasonId) {
    track(400);
    return errors.badRequest(res, `No data available for season ${seasonYear}`);
  }

  let rawData;
  try {
    rawData = await fetchSDPPlayers(seasonId);
  } catch (err) {
    console.error('Failed to fetch player stats:', err.message);
    track(502);
    return res.status(502).json({
      error: 'Bad Gateway',
      message: 'Failed to fetch player stats from CPL API',
      status: 502,
    });
  }

  let players = parsePlayerStats(rawData);

  // Filter by team if provided
  if (team) {
    const teamLower = team.toLowerCase();
    players = players.filter(p => p.team.toLowerCase().includes(teamLower));
  }

  // Sort by requested stat
  players.sort((a, b) => {
    const diff = (b[stat] ?? 0) - (a[stat] ?? 0);
    if (diff !== 0) return diff;
    // Secondary sort by goals if not already sorting by goals
    if (stat !== 'goals') return (b.goals ?? 0) - (a.goals ?? 0);
    return 0;
  });

  // Add rank
  players = players.slice(0, limitValidation.value ?? 20).map((p, i) => ({
    rank: i + 1,
    ...p,
  }));

  track(200);
  // Shorter cache since player stats change after matches
  res.setHeader('Cache-Control', 's-maxage=1800, stale-while-revalidate');
  return res.status(200).json({
    season: seasonYear,
    sort_by: stat,
    count: players.length,
    players,
  });
}

module.exports = withMiddleware(playersHandler, { endpoint: '/api/players' });
