const { SEASONS } = require('./cplStats.js');

const BASE_URL = 'https://api-sdp.cplsoccer.com/v1/cpl/football/seasons';
const CURRENT_SEASON = Math.max(...Object.keys(SEASONS).map(Number));
const HEADERS = {
  Accept: 'application/json',
  Origin: 'https://www.cplsoccer.com',
  Referer: 'https://www.cplsoccer.com/',
  'User-Agent': 'CanadaSoccerAPI/2.0 (+https://canadasoccerapi.com)',
};
const memoryCache = new Map();

function normalizeTeam(name) {
  const aliases = {
    Forge: 'Forge FC',
    Cavalry: 'Cavalry FC',
    Pacific: 'Pacific FC',
    Wanderers: 'HFX Wanderers FC',
    'HFX Wanderers': 'HFX Wanderers FC',
    Atletico: 'Atlético Ottawa',
    'Atlético': 'Atlético Ottawa',
    'Atletico Ottawa': 'Atlético Ottawa',
    'York United': 'York United FC',
    York9: 'York United FC',
    Vancouver: 'Vancouver FC',
    Valour: 'Valour FC',
    Supra: 'Supra du Québec',
    'FC Supra': 'Supra du Québec',
  };
  return aliases[name] || name || '';
}

async function fetchJson(path, ttlSeconds = 60) {
  const cached = memoryCache.get(path);
  if (cached && cached.expires > Date.now()) return cached.value;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(path, { headers: HEADERS, signal: controller.signal });
    if (!response.ok) throw new Error(`Official CPL feed returned ${response.status}`);
    const value = await response.json();
    memoryCache.set(path, { value, expires: Date.now() + ttlSeconds * 1000 });
    return value;
  } finally {
    clearTimeout(timeout);
  }
}

function seasonUrl(season, resource) {
  const seasonId = SEASONS[season];
  if (!seasonId) throw new Error(`No official feed configured for season ${season}`);
  return `${BASE_URL}/${seasonId}/${resource}?locale=en-US`;
}

function statValue(entity, ...ids) {
  const stats = Array.isArray(entity?.stats) ? entity.stats : [];
  for (const id of ids) {
    const stat = stats.find((item) => item.statsId === id);
    if (typeof stat?.statsValue === 'number') return stat.statsValue;
  }
  return 0;
}

function statMap(entity) {
  return Object.fromEntries((entity?.stats || []).map((stat) => [stat.statsId, stat.statsValue]));
}

async function getOfficialMatches(season = CURRENT_SEASON) {
  const data = await fetchJson(seasonUrl(season, 'matches'));
  return (data.matches || []).map((match) => ({
    match_id: match.matchId,
    provider_id: match.providerId || null,
    season_id: match.seasonId,
    season: Number(season),
    date: match.matchDateUtc?.slice(0, 10) || null,
    kickoff_utc: match.matchDateUtc || null,
    kickoff_local: match.matchDateLocal || null,
    utc_offset: match.localTimeUtcOffset || null,
    status: match.status || null,
    phase: match.phase || null,
    clock: match.time ? Number(match.time) : null,
    additional_time: match.additionalTime ? Number(match.additionalTime) : null,
    home_team: normalizeTeam(match.home?.officialName),
    away_team: normalizeTeam(match.away?.officialName),
    home_team_id: match.home?.teamId || null,
    away_team_id: match.away?.teamId || null,
    home_goals: match.providerHomeScore ?? match.homeScorePush ?? null,
    away_goals: match.providerAwayScore ?? match.awayScorePush ?? null,
    stadium: match.stadiumName || null,
    city: match.cityName || null,
    win_reason: match.winReason || null,
    matchday: match.matchSet?.name || null,
    broadcasters: Object.entries(match.editorial?.broadcasters || {})
      .filter(([, value]) => value)
      .map(([slot, value]) => {
        const [name, url] = String(value).split('|');
        return { slot, name, url: url || null };
      }),
    highlights_url: match.editorial?.highlightsUrl || match.editorial?.highlightsNationalUrl || null,
    tickets_url: match.editorial?.ticketsUrl || null,
  }));
}

async function getOfficialStandings(season = CURRENT_SEASON) {
  const data = await fetchJson(seasonUrl(season, 'standings'));
  return (data.teams || []).map((team) => {
    const stats = statMap(team);
    return {
      position: Number(stats.rank) || null,
      team_id: team.teamId,
      team: normalizeTeam(team.officialName),
      acronym: team.acronymName || null,
      played: Number(stats['matches-played']) || 0,
      wins: Number(stats.win) || 0,
      draws: Number(stats.draw) || 0,
      losses: Number(stats.lose) || 0,
      goals_for: Number(stats['goals-for']) || 0,
      goals_against: Number(stats['goals-against']) || 0,
      goal_difference: Number(stats['goal-difference']) || 0,
      points: Number(stats.points) || 0,
      movement: stats.movement || 'stable',
      form: Array.isArray(stats.form) ? stats.form.map((item) => item.formType) : [],
      qualification: team.qualification?.qualificationLabel || null,
    };
  }).sort((a, b) => a.position - b.position);
}

function mapPlayer(player) {
  const value = (...ids) => statValue(player, ...ids);
  return {
    player_id: String(player.playerId || '').split('::').pop(),
    full_player_id: player.playerId || null,
    provider_id: player.providerId || null,
    name: player.displayName || [player.mediaFirstName, player.mediaLastName].filter(Boolean).join(' ') || player.shortName || '',
    short_name: player.shortName || null,
    team: normalizeTeam(player.team?.officialName),
    team_id: player.team?.teamId || null,
    position: player.roleLabel || null,
    shirt_number: player.bibNumber ? Number(player.bibNumber) : null,
    nationality: player.nationality || null,
    nationality_code: player.nationalityIsoCode || null,
    appearances: value('games-played', 'Games Played', 'Appearances'),
    starts: value('Starts'),
    minutes: value('minutes-played', 'Time Played'),
    goals: value('goals', 'Goals'),
    assists: value('assists', 'Goal Assists'),
    goal_involvements: value('goal-involvements', 'goals-plus-assists'),
    xg: value('Xg', 'Expected Goals'),
    shots: value('total-scoring-attempts', 'Total Shots'),
    shots_on_target: value('on-target-scoring-attempts', 'Shots On Target ( inc goals )'),
    key_passes: value('total-attacking-assist', 'Key Passes (Attempt Assists)'),
    big_chances_created: value('Total Big Chances Created'),
    big_chances_scored: value('Total Big Chances Scored'),
    successful_dribbles: value('successful-dribble', 'Successful Dribbles'),
    progressive_carries: value('Progressive Carries'),
    touches_opposition_box: value('Total Touches In Opposition Box'),
    accurate_passes: value('accurate-pass', 'Total Successful Passes ( Excl Crosses & Corners ) '),
    total_passes: value('total-pass', 'Total Passes'),
    pass_accuracy: value('accurate-pass-percentage', 'passes-accuracy'),
    turnovers: value('Total Losses Of Possession', 'turnover'),
    tackles: value('tackle', 'tackles-won', 'Total Tackles'),
    interceptions: value('interception', 'Interceptions'),
    recoveries: value('Recoveries'),
    clearances: value('total-cleareance', 'Total Clearances'),
    duels_won: value('Duels won'),
    duels_total: value('Duels'),
    aerials_won: value('Aerial Duels won'),
    aerials_total: value('Aerial Duels', 'headed-duel'),
    fouls_won: value('Total Fouls Won', 'fouls-suffered'),
    fouls_committed: value('Total Fouls Conceded', 'fouls-committed'),
    saves: value('saves', 'goalkeeper-saves'),
    goals_conceded: value('goals-conceded', 'Goals Conceded'),
    yellow_cards: value('yellow-cards'),
    red_cards: value('red-cards'),
  };
}

async function getOfficialPlayers(season = CURRENT_SEASON) {
  const first = await fetchJson(`${seasonUrl(season, 'stats/players')}&page=1`);
  const totalPages = Math.max(1, Number(first.pagination?.totalPages) || 1);
  const remaining = await Promise.all(Array.from({ length: totalPages - 1 }, (_, index) => (
    fetchJson(`${seasonUrl(season, 'stats/players')}&page=${index + 2}`)
  )));
  return [first, ...remaining].flatMap((page) => page.players || []).map(mapPlayer);
}

async function getOfficialTeamStats(season = CURRENT_SEASON, includeRaw = false) {
  const data = await fetchJson(seasonUrl(season, 'stats/teams'));
  return (data.teams || []).map((team) => {
    const value = (...ids) => statValue(team, ...ids);
    const result = {
      team_id: team.teamId,
      team: normalizeTeam(team.officialName),
      acronym: team.acronymName || null,
      played: value('games-played'),
      points: value('total-points'),
      wins: value('total-wins'),
      draws: value('total-draws'),
      losses: value('total-losses'),
      goals: value('goals'),
      goals_against: value('goals-against'),
      shots: value('total-scoring-attempts', 'Total Shots'),
      shots_on_target: value('on-target-scoring-attempts', 'Shots On Target ( inc goals )'),
      chances_created: value('chances-created', 'Key Passes (Attempt Assists)'),
      corners: value('corners', 'Corners Won'),
      pass_accuracy: value('passes-accuracy', 'accurate-pass-percentage'),
      possession: value('possession-percentage', 'Possession Percentage'),
      total_passes: value('total-pass', 'Total Passes'),
      crosses: value('cross', 'Successful Crosses & Corners'),
      clean_sheets: value('clean-sheets', 'Clean Sheets'),
      xg: value('Xg', 'Expected Goals'),
      duels_won_percentage: value('duels-won-perc'),
      yellow_cards: value('yellow-cards', 'Yellow Cards'),
      red_cards: value('red-cards', 'Red Cards'),
      tackles: value('tackle', 'Total Tackles'),
      interceptions: value('interception', 'Interceptions'),
      saves: value('goalkeeper-saves', 'saves', 'Saves'),
    };
    if (includeRaw) result.raw_stats = statMap(team);
    return result;
  });
}

module.exports = {
  CURRENT_SEASON,
  HEADERS,
  getOfficialMatches,
  getOfficialPlayers,
  getOfficialStandings,
  getOfficialTeamStats,
  normalizeTeam,
  statMap,
  statValue,
};
