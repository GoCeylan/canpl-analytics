import { readFileSync } from 'fs';
import { join } from 'path';

export const config = {
  runtime: 'nodejs18.x',
};

export default function handler(req, res) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    const { season } = req.query;

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

    // Calculate standings
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

    // Get available seasons
    const seasons = [...new Set(matches.map(m => m.season))].sort();

    if (season) {
      // Return standings for specific season
      const seasonNum = parseInt(season, 10);
      const seasonMatches = matches.filter(m => m.season === seasonNum);
      const standings = calculateStandings(seasonMatches);

      return res.status(200).json({
        season: seasonNum,
        standings
      });
    } else {
      // Return standings for all seasons
      const allStandings = {};
      seasons.forEach(s => {
        const seasonMatches = matches.filter(m => m.season === s);
        allStandings[s] = calculateStandings(seasonMatches);
      });

      return res.status(200).json({
        seasons,
        standings: allStandings
      });
    }
  } catch (error) {
    console.error('Error calculating standings:', error);
    return res.status(500).json({ error: 'Failed to calculate standings' });
  }
}
