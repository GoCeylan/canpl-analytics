/**
 * CPL Team Stats Fetcher and xG Calculator
 * Fetches detailed match stats from CPL API and estimates xG from shot location data
 */

const SEASON_ID = 'cpl::Football_Season::c479ab0916a24c3390f1ce2c021ace54'; // 2025

/**
 * Fetch team stats from CPL API for a given match
 * @param {string} matchId - Full CPL match ID
 * @returns {Object|null} Parsed stats or null if fetch failed
 */
async function fetchTeamStats(matchId) {
  const url = `https://api-sdp.canpl.ca/v1/cpl/football/seasons/${SEASON_ID}/match/${matchId}/teamstats?locale=en-US`;

  try {
    const res = await fetch(url);
    if (!res.ok) {
      console.error(`Failed to fetch team stats: ${res.status}`);
      return null;
    }

    const data = await res.json();
    if (!data.stats || !Array.isArray(data.stats)) {
      return null;
    }

    return parseStats(data.stats);
  } catch (err) {
    console.error('Error fetching team stats:', err);
    return null;
  }
}

/**
 * Parse stats array into a keyed object
 * @param {Array} statsArray - Raw stats from CPL API
 * @returns {Object} Stats keyed by statsId
 */
function parseStats(statsArray) {
  const stats = {};
  for (const s of statsArray) {
    // Handle both string and numeric values from API
    const homeVal = typeof s.statsValueHome === 'number' ? s.statsValueHome : parseInt(s.statsValueHome, 10);
    const awayVal = typeof s.statsValueAway === 'number' ? s.statsValueAway : parseInt(s.statsValueAway, 10);
    stats[s.statsId] = {
      home: isNaN(homeVal) ? 0 : homeVal,
      away: isNaN(awayVal) ? 0 : awayVal
    };
  }
  return stats;
}

/**
 * Calculate estimated xG from shot location data
 *
 * Formula:
 * - Shots inside box: ~12% conversion rate
 * - Shots outside box: ~3% conversion rate
 * - Shots on target bonus: ~5% per shot
 *
 * @param {Object} stats - Parsed stats object
 * @returns {Object} xG estimates { home, away }
 */
function calculateXG(stats) {
  const insideBox = stats['shots-at-goal-inside-box'] || { home: 0, away: 0 };
  const outsideBox = stats['shots-at-goal-outside-box'] || { home: 0, away: 0 };
  const onTarget = stats['shots-on-goal'] || { home: 0, away: 0 };

  const homeXG = (insideBox.home * 0.12) + (outsideBox.home * 0.03) + (onTarget.home * 0.05);
  const awayXG = (insideBox.away * 0.12) + (outsideBox.away * 0.03) + (onTarget.away * 0.05);

  return {
    home: Math.round(homeXG * 100) / 100,
    away: Math.round(awayXG * 100) / 100
  };
}

module.exports = { fetchTeamStats, calculateXG, parseStats };
