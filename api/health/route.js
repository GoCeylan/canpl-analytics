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
    const dataPath = join(process.cwd(), 'data', 'matches', 'cpl_all.csv');
    const dataExists = existsSync(dataPath);

    const health = {
      status: dataExists ? 'healthy' : 'degraded',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
      checks: {
        data: {
          status: dataExists ? 'ok' : 'error',
          message: dataExists ? 'Data files accessible' : 'Data files not found',
        },
        api: {
          status: 'ok',
          message: 'API responding',
        },
      },
      endpoints: [
        '/api/matches',
        '/api/standings',
        '/api/teams',
        '/api/analytics',
        '/api/health',
      ],
      rateLimit: {
        limit: 20,
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
