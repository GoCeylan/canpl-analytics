const { existsSync } = require('fs');
const { join } = require('path');
const { setCorsHeaders, handlePreflight } = require('../lib/middleware.js');

/**
 * Health check endpoint for monitoring
 * Returns API status and basic diagnostics
 */
function handler(req, res) {
  // Set CORS headers
  setCorsHeaders(res);

  // Handle preflight
  if (handlePreflight(req, res)) {
    return;
  }

  // Only allow GET requests
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({
      error: 'Method Not Allowed',
      message: 'Only GET method is allowed',
      status: 405,
    });
  }

  // Don't cache health checks
  res.setHeader('Cache-Control', 'no-store, max-age=0');

  try {
    // Check if data files exist
    const requiredFiles = [
      'data/matches/cpl_all_with_ids.csv',
      'data/matches/match_teamstats_history.csv',
      'data/matches/cpl_referees_2019_2025.csv',
      'data/venues/stadium_info.csv',
    ];
    const fileChecks = Object.fromEntries(requiredFiles.map((file) => [file, existsSync(join(process.cwd(), file))]));
    const dataExists = Object.values(fileChecks).every(Boolean);

    const health = {
      status: dataExists ? 'healthy' : 'degraded',
      timestamp: new Date().toISOString(),
      version: '2.0.0',
      checks: {
        data: {
          status: dataExists ? 'ok' : 'error',
          message: dataExists ? 'Data files accessible' : 'Data files not found',
          files: fileChecks,
        },
        api: {
          status: 'ok',
          message: 'API responding',
        },
      },
      endpoints: [
        '/api/v1/matches', '/api/v1/live', '/api/v1/standings', '/api/v1/players',
        '/api/v1/leaderboards', '/api/v1/team-stats', '/api/v1/teams', '/api/v1/match-stats',
        '/api/v1/referees', '/api/v1/venues', '/api/v1/weather', '/api/v1/odds',
        '/api/v1/odds-quotes', '/api/v1/seasons', '/api/v1/health',
      ],
      rateLimit: {
        limit: 300,
        window: '1 hour',
        scope: 'per IP',
      },
    };

    const statusCode = health.status === 'healthy' ? 200 : 503;
    return res.status(statusCode).json(health);
  } catch (error) {
    console.error('Health check error:', error);
    return res.status(503).json({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      error: 'Health check failed',
    });
  }
}

module.exports = handler;
