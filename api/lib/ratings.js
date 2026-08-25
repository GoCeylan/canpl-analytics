const RATING_MINUTES = 270;

const per90 = (value, minutes) => (minutes > 0 ? (value * 90) / minutes : 0);
const percentage = (part, total) => (total > 0 ? (part / total) * 100 : 0);

function percentile(value, values, lowerIsBetter = false) {
  if (values.length <= 1) return 50;
  const lower = values.filter((candidate) => candidate < value).length;
  const equal = values.filter((candidate) => candidate === value).length;
  const result = ((lower + equal * 0.5) / values.length) * 100;
  return lowerIsBetter ? 100 - result : result;
}

function weightedArea(player, peers, metrics) {
  const totalWeight = metrics.reduce((sum, metric) => sum + metric.weight, 0);
  return metrics.reduce((score, metric) => (
    score + percentile(metric.value(player), peers.map(metric.value), metric.lowerIsBetter) * metric.weight
  ), 0) / totalWeight;
}

const areas = {
  attack: [
    { value: (p) => per90(p.goals, p.minutes), weight: 0.32 },
    { value: (p) => per90(p.shots_on_target, p.minutes), weight: 0.20 },
    { value: (p) => per90(p.shots, p.minutes), weight: 0.13 },
    { value: (p) => per90(p.successful_dribbles, p.minutes), weight: 0.13 },
    { value: (p) => per90(p.touches_opposition_box, p.minutes), weight: 0.12 },
    { value: (p) => per90(p.big_chances_scored, p.minutes), weight: 0.10 },
  ],
  creativity: [
    { value: (p) => per90(p.assists, p.minutes), weight: 0.30 },
    { value: (p) => per90(p.key_passes, p.minutes), weight: 0.28 },
    { value: (p) => per90(p.big_chances_created, p.minutes), weight: 0.20 },
    { value: (p) => per90(p.progressive_carries, p.minutes), weight: 0.14 },
    { value: (p) => per90(p.fouls_won, p.minutes), weight: 0.08 },
  ],
  possession: [
    { value: (p) => p.pass_accuracy, weight: 0.42 },
    { value: (p) => per90(p.accurate_passes, p.minutes), weight: 0.28 },
    { value: (p) => per90(p.progressive_carries, p.minutes), weight: 0.16 },
    { value: (p) => per90(p.turnovers, p.minutes), weight: 0.14, lowerIsBetter: true },
  ],
  defending: [
    { value: (p) => per90(p.tackles, p.minutes), weight: 0.22 },
    { value: (p) => per90(p.interceptions, p.minutes), weight: 0.20 },
    { value: (p) => per90(p.recoveries, p.minutes), weight: 0.18 },
    { value: (p) => per90(p.clearances, p.minutes), weight: 0.13 },
    { value: (p) => percentage(p.duels_won, p.duels_total), weight: 0.17 },
    { value: (p) => percentage(p.aerials_won, p.aerials_total), weight: 0.10 },
  ],
  discipline: [
    { value: (p) => per90(p.fouls_committed, p.minutes), weight: 0.45, lowerIsBetter: true },
    { value: (p) => per90(p.yellow_cards + p.red_cards * 3, p.minutes), weight: 0.55, lowerIsBetter: true },
  ],
};

const roleWeights = {
  Forward: { attack: 38, creativity: 27, possession: 12, defending: 10, discipline: 13 },
  Midfielder: { attack: 20, creativity: 28, possession: 22, defending: 18, discipline: 12 },
  Defender: { attack: 10, creativity: 12, possession: 26, defending: 40, discipline: 12 },
};

function calculateRating(player, allPlayers) {
  const role = player.position === 'Goalkeeper' ? 'Goalkeeper' : (roleWeights[player.position] ? player.position : 'Midfielder');
  const sameRole = allPlayers.filter((candidate) => candidate.position === role && candidate.minutes >= 90);
  const peers = sameRole.length >= 3 ? sameRole : allPlayers.filter((candidate) => candidate.minutes >= 90);
  let breakdown;
  let raw;

  if (role === 'Goalkeeper') {
    const defending = weightedArea(player, peers, [
      { value: (p) => per90(p.saves, p.minutes), weight: 0.38 },
      { value: (p) => percentage(p.saves, p.saves + p.goals_conceded), weight: 0.34 },
      { value: (p) => per90(p.goals_conceded, p.minutes), weight: 0.28, lowerIsBetter: true },
    ]);
    breakdown = {
      attack: 50,
      creativity: 50,
      possession: Math.round(weightedArea(player, peers, areas.possession)),
      defending: Math.round(defending),
      discipline: Math.round(weightedArea(player, peers, areas.discipline)),
    };
    raw = breakdown.defending * 0.62 + breakdown.possession * 0.23 + breakdown.discipline * 0.15;
  } else {
    breakdown = Object.fromEntries(Object.entries(areas).map(([name, metrics]) => [
      name,
      Math.round(weightedArea(player, peers, metrics)),
    ]));
    raw = Object.entries(roleWeights[role]).reduce((score, [area, weight]) => (
      score + breakdown[area] * weight / 100
    ), 0);
  }

  const reliability = Math.min(1, Math.max(0.25, player.minutes / 720));
  const adjusted = 50 + (raw - 50) * reliability;
  return {
    rating: Math.round((5.5 + adjusted * 0.04) * 10) / 10,
    rating_breakdown: breakdown,
  };
}

function applySeasonRatings(players) {
  const rated = players.map((player) => ({
    ...player,
    ...calculateRating(player, players),
    rating_eligible: player.minutes >= RATING_MINUTES,
  }));
  const eligible = rated
    .filter((player) => player.rating_eligible)
    .sort((a, b) => b.rating - a.rating || b.minutes - a.minutes || a.name.localeCompare(b.name));
  const ranks = new Map(eligible.map((player, index) => [player.player_id, index + 1]));
  return rated.map((player) => ({ ...player, rating_rank: ranks.get(player.player_id) || null }));
}

module.exports = { RATING_MINUTES, applySeasonRatings, per90 };
