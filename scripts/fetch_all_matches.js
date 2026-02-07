/**
 * Fetch all CPL, Canadian Championship, and CCL matches with match_ids from the CPL API
 * Outputs: data/matches/cpl_all_with_ids.csv
 */

const fs = require('fs');
const path = require('path');

// Competition definitions with per-year season IDs
// Season IDs discovered from API exploration (discovered_canpl_endpoints.json)
const COMPETITIONS = {
  cpl: {
    name: 'Canadian Premier League',
    seasons: {
      2019: 'c8c9bdc288f34aa89073a8bd89d2da3e',
      2020: '11aa5cc094d0481fa8e73d326763584f',
      2021: '2f07c39671b84933ad7bb1e1958a7427',
      2022: '046f0ab31ba641c7b7bf27eb0dda4b9d',
      2023: 'fc0855108c9044218a84fc5d2bee0000',
      2024: '6fb9e6fae4f24ce9bf4fa3172616a762',
      2025: 'fd43e1d61dfe4396a7356bc432de0007',
      2026: 'c479ab0916a24c3390f1ce2c021ace54',
    },
  },
  'canadian-championship': {
    name: 'Canadian Championship',
    seasons: {
      2025: 'fec9d91ba01c4d57999feac75f3b23d1',
    },
  },
  ccl: {
    name: 'Concacaf Champions Cup',
    seasons: {
      2025: '0ba5ca8a4f664c76a1ee9639c4adc04e',
    },
  },
};

/**
 * Fetch all matches for a given season from CPL API
 * @param {string} competition - Competition key (cpl, canadian-championship, ccl)
 * @param {number} year - Season year
 * @param {string} seasonId - CPL API season ID (UUID portion)
 * @returns {Promise<Array>} Array of match objects
 */
async function fetchSeasonMatches(competition, year, seasonId) {
  const fullSeasonId = `cpl::Football_Season::${seasonId}`;
  const url = `https://api-sdp.canpl.ca/v1/cpl/football/seasons/${fullSeasonId}/matches?locale=en-US`;

  console.log(`Fetching ${competition} ${year} matches...`);

  try {
    const res = await fetch(url);
    if (!res.ok) {
      console.error(`Failed to fetch ${competition} ${year}: ${res.status}`);
      return [];
    }

    const data = await res.json();
    if (!data.matches || !Array.isArray(data.matches)) {
      console.error(`No matches found for ${competition} ${year}`);
      return [];
    }

    const matches = data.matches.map(m => ({
      match_id: m.matchId || '',
      season_id: fullSeasonId,
      competition,
      date: m.matchDateLocal ? m.matchDateLocal.substring(0, 10) : (m.matchDateUtc ? m.matchDateUtc.substring(0, 10) : ''),
      season: year,
      matchday: m.matchdayName || '',
      home_team: m.home?.officialName || m.home?.shortName || '',
      away_team: m.away?.officialName || m.away?.shortName || '',
      home_goals: m.homeScorePush ?? '',
      away_goals: m.awayScorePush ?? '',
      venue: m.stadiumName || '',
      status: m.status || '',
    }));

    console.log(`  Found ${matches.length} matches for ${competition} ${year}`);
    return matches;
  } catch (err) {
    console.error(`Error fetching ${competition} ${year}:`, err.message);
    return [];
  }
}

/**
 * Escape CSV value (handle commas and quotes)
 */
function escapeCSV(value) {
  if (value === null || value === undefined) return '';
  const str = String(value);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return '"' + str.replace(/"/g, '""') + '"';
  }
  return str;
}

/**
 * Main function to fetch all seasons and write CSV
 */
async function main() {
  const allMatches = [];

  // Fetch each competition and season sequentially to avoid rate limiting
  for (const [competition, config] of Object.entries(COMPETITIONS)) {
    for (const [year, seasonId] of Object.entries(config.seasons)) {
      const yearNum = parseInt(year, 10);
      // Skip 2026 which may not have data yet
      if (yearNum > 2025) continue;

      const matches = await fetchSeasonMatches(competition, yearNum, seasonId);
      allMatches.push(...matches);

      // Small delay between requests
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }

  // Sort by date
  allMatches.sort((a, b) => a.date.localeCompare(b.date));

  // Write CSV
  const headers = ['match_id', 'season_id', 'competition', 'date', 'season', 'matchday', 'home_team', 'away_team', 'home_goals', 'away_goals', 'venue', 'status'];
  const csvLines = [headers.join(',')];

  for (const match of allMatches) {
    const row = headers.map(h => escapeCSV(match[h]));
    csvLines.push(row.join(','));
  }

  const outputPath = path.join(__dirname, '..', 'data', 'matches', 'cpl_all_with_ids.csv');
  fs.writeFileSync(outputPath, csvLines.join('\n'), 'utf-8');

  console.log(`\nWrote ${allMatches.length} matches to ${outputPath}`);
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
