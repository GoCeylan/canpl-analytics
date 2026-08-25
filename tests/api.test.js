const assert = require('node:assert/strict');
const test = require('node:test');

function stats(values) {
  return Object.entries(values).map(([statsId, statsValue]) => ({ statsId, statsValue }));
}

const fakePlayers = [
  ['p1', 'Ari', 'Striker', 'Forward', 'Forge', { 'games-played': 10, 'minutes-played': 800, goals: 8, assists: 2, 'goal-involvements': 10, 'total-scoring-attempts': 30, 'on-target-scoring-attempts': 17, 'total-attacking-assist': 12, 'accurate-pass-percentage': 81, 'total-pass': 260, 'accurate-pass': 210, tackle: 8, interception: 2, Recoveries: 20, Duels: 40, 'Duels won': 23 }],
  ['p2', 'Bea', 'Maker', 'Midfielder', 'Cavalry', { 'games-played': 11, 'minutes-played': 850, goals: 3, assists: 7, 'goal-involvements': 10, 'total-scoring-attempts': 18, 'on-target-scoring-attempts': 8, 'total-attacking-assist': 30, 'accurate-pass-percentage': 89, 'total-pass': 540, 'accurate-pass': 480, tackle: 30, interception: 20, Recoveries: 60, Duels: 70, 'Duels won': 45 }],
  ['p3', 'Cam', 'Back', 'Defender', 'Pacific', { 'games-played': 12, 'minutes-played': 940, goals: 1, assists: 1, 'goal-involvements': 2, 'accurate-pass-percentage': 91, 'total-pass': 650, 'accurate-pass': 590, tackle: 40, interception: 35, Recoveries: 75, Duels: 90, 'Duels won': 62, 'Total Clearances': 50 }],
  ['p4', 'Dee', 'Keeper', 'Goalkeeper', 'Vancouver FC', { 'games-played': 12, 'minutes-played': 1080, saves: 55, 'goals-conceded': 12, 'accurate-pass-percentage': 76, 'total-pass': 300, 'accurate-pass': 228 }],
].map(([id, first, last, roleLabel, team, values]) => ({
  playerId: `cpl::Football_Player::${id}`,
  mediaFirstName: first,
  mediaLastName: last,
  roleLabel,
  team: { teamId: `team-${team}`, officialName: team },
  stats: stats(values),
}));

const fakeMatches = [{
  matchId: 'match-live-1', seasonId: 'season-2026', matchDateUtc: '2026-08-25T23:00:00Z',
  matchDateLocal: '2026-08-25T19:00:00', localTimeUtcOffset: '-04:00', status: 'UPCOMING', phase: 'PRE_MATCH',
  home: { teamId: 'forge', officialName: 'Forge' }, away: { teamId: 'cavalry', officialName: 'Cavalry' },
  stadiumName: 'Hamilton Stadium', cityName: 'Hamilton', editorial: { broadcasters: {} },
}];

const fakeStandings = [{
  teamId: 'forge', officialName: 'Forge', acronymName: 'FOR', qualification: { qualificationLabel: 'Final Series' },
  stats: stats({ rank: 1, points: 40, 'matches-played': 18, win: 12, draw: 4, lose: 2, 'goals-for': 30, 'goals-against': 12, 'goal-difference': 18, movement: 'stable' }),
}];

const fakeTeams = [{
  teamId: 'forge', officialName: 'Forge', acronymName: 'FOR',
  stats: stats({ 'games-played': 18, 'total-points': 40, 'total-wins': 12, 'total-draws': 4, 'total-losses': 2, goals: 30, 'goals-against': 12, 'total-scoring-attempts': 200, 'passes-accuracy': 86 }),
}];

global.fetch = async (url) => {
  let body;
  if (url.includes('/stats/players')) body = { players: fakePlayers, pagination: { totalPages: 1 } };
  else if (url.includes('/stats/teams')) body = { teams: fakeTeams, pagination: { totalPages: 1 } };
  else if (url.includes('/standings')) body = { teams: fakeStandings };
  else if (url.includes('/matches')) body = { matches: fakeMatches };
  else body = {};
  return { ok: true, status: 200, json: async () => body };
};

function response() {
  return {
    statusCode: 200,
    headers: {},
    headersSent: false,
    setHeader(name, value) { this.headers[name] = value; },
    status(code) { this.statusCode = code; return this; },
    json(body) { this.body = body; this.headersSent = true; return this; },
    end() { this.headersSent = true; return this; },
  };
}

async function call(path, query = {}) {
  const handler = require(`../api/${path}/route.js`);
  const req = { method: 'GET', query, headers: {}, socket: { remoteAddress: 'test' } };
  const res = response();
  await handler(req, res);
  return res;
}

test('discovery exposes the complete v1 surface', async () => {
  const res = await call('index');
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.version, '2.0.0');
  assert.ok(res.body.endpoints['/api/v1/players']);
  assert.ok(res.body.endpoints['/api/v1/odds-quotes']);
});

test('single serverless router dispatches v1 resources', async () => {
  const router = require('../api/router.js');
  const req = { method: 'GET', url: '/api/router.js?resource=seasons', query: { resource: 'seasons' }, headers: {}, socket: { remoteAddress: 'router-test' } };
  const res = response();
  await router(req, res);
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.count, 8);
});

test('historical match archive and pagination work', async () => {
  const res = await call('matches', { season: '2019', limit: '2' });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.total, 100);
  assert.equal(res.body.matches.length, 2);
  assert.equal(res.body.has_more, true);
});

test('current standings use the official feed model', async () => {
  const res = await call('standings', { season: '2026' });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.source, 'official-cpl-live');
  assert.equal(res.body.standings[0].team, 'Forge FC');
  assert.equal(res.body.standings[0].points, 40);
});

test('player endpoint rates, filters, and sorts players', async () => {
  const res = await call('players', { eligible: 'true', sort: 'rating', limit: '3' });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.count, 3);
  assert.ok(res.body.players.every((player) => player.rating_eligible));
  assert.ok(res.body.players[0].rating >= res.body.players[1].rating);
  assert.equal(typeof res.body.players[0].rating_breakdown.attack, 'number');
});

test('leaderboards provide multiple requested boards', async () => {
  const res = await call('leaderboards', { metric: 'rating,goals,assists', limit: '3' });
  assert.equal(res.statusCode, 200);
  assert.deepEqual(res.body.leaderboards.map((board) => board.metric), ['rating', 'goals', 'assists']);
});

test('context datasets are queryable', async () => {
  const [venues, weather, referees, quotes] = await Promise.all([
    call('venues', { active_only: 'true' }),
    call('weather', { team: 'Forge', limit: '1' }),
    call('referees', { season: '2025', summary: 'true' }),
    call('odds-quotes', { season: '2026', limit: '2' }),
  ]);
  assert.ok(venues.body.count >= 1);
  assert.equal(weather.body.count, 1);
  assert.ok(referees.body.count >= 1);
  assert.equal(quotes.body.count, 2);
});

test('bulk match stats preserve ISO dates and advanced fields', async () => {
  const res = await call('match-stats', { season: '2025' });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.count, 117);
  assert.match(res.body.matches[0].date, /^2025-\d{2}-\d{2}$/);
  assert.ok(res.body.matches.some((match) => match.has_data));
});

test('bad query values return a stable error', async () => {
  const res = await call('players', { order: 'sideways' });
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.status, 400);
  assert.match(res.body.message, /asc or desc/);
});
