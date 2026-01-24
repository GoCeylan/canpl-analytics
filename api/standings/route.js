import { readFileSync, existsSync } from 'fs';
import { join } from 'path';
import { withMiddleware } from '../lib/middleware.js';

export const config = {
  runtime: 'nodejs',
};

// Load pre-computed standings from official API (regular season only)
function loadOfficialStandings(season) {
  const standingsPath = join(process.cwd(), 'data', `standings_${season}_api.csv`);
  if (!existsSync(standingsPath)) {
    return null;
  }

  const csvData = readFileSync(standingsPath, 'utf-8');
  const lines = csvData.trim().split('\n');
  const headers = lines[0].split(',');

  return lines.slice(1).map(line => {
    const values = line.split(',');
    const obj = {};
    headers.forEach((header, index) => {
      const value = values[index];
      if (['position', 'played', 'wins', 'draws', 'losses', 'goals_for', 'goals_against', 'goal_difference', 'points'].includes(header)) {
        obj[header] = parseInt(value, 10);
      } else {
        obj[header] = value;
      }
    });
    return obj;
  });
}

// Calculate standings from match results
function calculateStandings(matchList) {
  const teamStats = {};

  matchList.forEach(match => {
    const { home_team, away_team, home_goals, away_goals } = match;

    // Initialize teams if not exists
    [home_team, away_team].forEach(team => {
      if (!teamStats[team]) {
        teamStats[team] = {
          team,
          played: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goals_for: 0,
          goals_against: 0,
          goal_difference: 0,
          points: 0
        };
      }
    });

    // Update home team stats
    teamStats[home_team].played++;
    teamStats[home_team].goals_for += home_goals;
    teamStats[home_team].goals_against += away_goals;

    // Update away team stats
    teamStats[away_team].played++;
    teamStats[away_team].goals_for += away_goals;
    teamStats[away_team].goals_against += home_goals;

    // Determine result
    if (home_goals > away_goals) {
      teamStats[home_team].wins++;
      teamStats[home_team].points += 3;
      teamStats[away_team].losses++;
    } else if (home_goals < away_goals) {
      teamStats[away_team].wins++;
      teamStats[away_team].points += 3;
      teamStats[home_team].losses++;
    } else {
      teamStats[home_team].draws++;
      teamStats[away_team].draws++;
      teamStats[home_team].points += 1;
      teamStats[away_team].points += 1;
    }
  });

  // Calculate goal difference and sort
  const standings = Object.values(teamStats).map(team => ({
    ...team,
    goal_difference: team.goals_for - team.goals_against
  }));

  standings.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.goal_difference !== a.goal_difference) return b.goal_difference - a.goal_difference;
    return b.goals_for - a.goals_for;
  });

  return standings.map((team, index) => ({
    position: index + 1,
    ...team
  }));
}

async function standingsHandler(req, res, { track, errors, validateNumber }) {
  const { season } = req.query;

  // Validate season parameter
  const seasonValidation = validateNumber(season, 'season', 2019, 2030);
  if (!seasonValidation.valid) {
    track(400);
    return errors.badRequest(res, seasonValidation.error);
  }

  // Read the matches data
  const dataPath = join(process.cwd(), 'data', 'matches', 'cpl_all.csv');
  const csvData = readFileSync(dataPath, 'utf-8');

  // Parse CSV
  const lines = csvData.trim().split('\n');
  const headers = lines[0].split(',');

  const matches = lines.slice(1).map(line => {
    const values = line.split(',');
    const obj = {};
    headers.forEach((header, index) => {
      const value = values[index];
      if (['home_goals', 'away_goals', 'season'].includes(header)) {
        obj[header] = parseInt(value, 10);
      } else {
        obj[header] = value;
      }
    });
    return obj;
  }).filter(m => m.date);

  // Get available seasons
  const seasons = [...new Set(matches.map(m => m.season))].sort();

  if (seasonValidation.value !== undefined) {
    // Return standings for specific season
    const seasonNum = seasonValidation.value;

    // Check if season exists
    if (!seasons.includes(seasonNum)) {
      track(404);
      return errors.notFound(res, `No data available for season ${seasonNum}`);
    }

    // Try to use official standings from API (excludes playoffs)
    const officialStandings = loadOfficialStandings(seasonNum);
    if (officialStandings) {
      track(200);
      return res.status(200).json({
        season: seasonNum,
        standings: officialStandings,
        source: 'official'
      });
    }

    // Fall back to calculating from matches
    const seasonMatches = matches.filter(m => m.season === seasonNum);
    const standings = calculateStandings(seasonMatches);

    track(200);
    return res.status(200).json({
      season: seasonNum,
      standings,
      source: 'calculated'
    });
  } else {
    // Return standings for all seasons
    const allStandings = {};
    seasons.forEach(s => {
      // Try official standings first
      const officialStandings = loadOfficialStandings(s);
      if (officialStandings) {
        allStandings[s] = officialStandings;
      } else {
        const seasonMatches = matches.filter(m => m.season === s);
        allStandings[s] = calculateStandings(seasonMatches);
      }
    });

    track(200);
    return res.status(200).json({
      seasons,
      standings: allStandings
    });
  }
}

export default withMiddleware(standingsHandler, { endpoint: '/api/standings' });
