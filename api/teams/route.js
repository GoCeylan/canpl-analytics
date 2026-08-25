const { withMiddleware } = require('../lib/middleware.js');
const { includes, readCsv } = require('../lib/data.js');
const { CURRENT_SEASON, getOfficialTeamStats, normalizeTeam } = require('../lib/sdp.js');

async function teamsHandler(req, res, { track, errors }) {
  if (req.query.active_only !== undefined && !['true', 'false'].includes(req.query.active_only)) {
    return errors.badRequest(res, 'active_only must be true or false');
  }
  const venues = readCsv('data/venues/stadium_info.csv');
  let liveStats = [];
  try { liveStats = await getOfficialTeamStats(CURRENT_SEASON); } catch (error) { console.error(error.message); }
  const liveIndex = new Map(liveStats.map((team) => [normalizeTeam(team.team), team]));
  let teams = venues.map((venue) => {
    const live = liveIndex.get(normalizeTeam(venue.team));
    return {
      team_id: live?.team_id || null,
      name: normalizeTeam(venue.team),
      acronym: live?.acronym || null,
      city: venue.city, stadium: venue.stadium, capacity: venue.capacity,
      latitude: venue.latitude, longitude: venue.longitude, surface: venue.surface,
      founded: venue.founded, status: venue.status, current_season: !!live, notes: venue.notes,
    };
  });
  liveStats.forEach((live) => {
    if (!teams.some((team) => team.name === normalizeTeam(live.team))) {
      teams.push({ team_id: live.team_id, name: normalizeTeam(live.team), acronym: live.acronym, status: 'active', current_season: true });
    }
  });
  if (req.query.active_only === 'true') teams = teams.filter((team) => team.status === 'active' && team.current_season);
  if (req.query.search) teams = teams.filter((team) => includes(`${team.name} ${team.city} ${team.stadium}`, req.query.search));
  teams.sort((a, b) => a.name.localeCompare(b.name));
  track(200);
  return res.status(200).json({ count: teams.length, season: CURRENT_SEASON, teams });
}

module.exports = withMiddleware(teamsHandler, { endpoint: '/api/teams', cache: 's-maxage=3600, stale-while-revalidate=86400' });
