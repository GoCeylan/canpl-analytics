const { getAnalytics } = require('../lib/analytics.js');
const { setCorsHeaders, handlePreflight } = require('../lib/middleware.js');

/**
 * Analytics endpoint - returns API usage statistics
 * This endpoint is not rate limited to allow monitoring
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

  // Optional: Add basic auth for admin access
  // For now, analytics are public but anonymized
  const authHeader = req.headers.authorization;
  const expectedAuth = process.env.ANALYTICS_BASIC_AUTH;
  const isAdmin = expectedAuth && authHeader === `Basic ${Buffer.from(expectedAuth).toString('base64')}`;

  try {
    const analytics = getAnalytics();

    // If not admin, redact sensitive data
    if (!isAdmin) {
      // Remove detailed request logs for non-admin users
      analytics.recentRequests = analytics.recentRequests.slice(0, 5);
    }

    // Don't cache analytics
    res.setHeader('Cache-Control', 'no-store, max-age=0');

    return res.status(200).json(analytics);
  } catch (error) {
    console.error('Error fetching analytics:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: 'Failed to fetch analytics',
      status: 500,
    });
  }
}

module.exports = handler;
