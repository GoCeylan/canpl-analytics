/**
 * Simple analytics tracking for API usage
 * Stores analytics in memory with periodic aggregation
 * Note: Data is lost on cold starts. For persistence, use Vercel KV or external DB.
 */

/**
 * Get the start of the current week (Monday)
 */
function getWeekStart() {
  const now = new Date();
  const day = now.getDay();
  const diff = now.getDate() - day + (day === 0 ? -6 : 1);
  const weekStart = new Date(now);
  weekStart.setDate(diff);
  return weekStart.toISOString().split('T')[0];
}

// In-memory analytics store
const analyticsStore = {
  // Endpoint statistics
  endpoints: {
    '/api/matches': { calls: 0, totalTime: 0, errors: 0 },
    '/api/standings': { calls: 0, totalTime: 0, errors: 0 },
    '/api/teams': { calls: 0, totalTime: 0, errors: 0 },
  },

  // Time-series data (hourly buckets)
  hourly: new Map(), // { [hourKey]: { calls: number, uniqueIPs: Set } }

  // Unique IPs tracking
  uniqueIPs: new Set(),

  // Recent requests (last 100)
  recentRequests: [],

  // Daily/weekly/monthly counters
  counters: {
    today: { calls: 0, date: new Date().toISOString().split('T')[0] },
    week: { calls: 0, weekStart: getWeekStart() },
    month: { calls: 0, month: new Date().toISOString().slice(0, 7) },
    allTime: { calls: 0, startTime: Date.now() },
  },

  // Geographic distribution (if available)
  countries: new Map(),
};

/**
 * Get current hour key for time-series data
 */
function getHourKey() {
  const now = new Date();
  return `${now.toISOString().slice(0, 13)}:00`;
}

/**
 * Reset daily/weekly/monthly counters if needed
 */
function resetCountersIfNeeded() {
  const today = new Date().toISOString().split('T')[0];
  const weekStart = getWeekStart();
  const month = new Date().toISOString().slice(0, 7);

  if (analyticsStore.counters.today.date !== today) {
    analyticsStore.counters.today = { calls: 0, date: today };
  }

  if (analyticsStore.counters.week.weekStart !== weekStart) {
    analyticsStore.counters.week = { calls: 0, weekStart };
  }

  if (analyticsStore.counters.month.month !== month) {
    analyticsStore.counters.month = { calls: 0, month };
  }
}

/**
 * Track an API request
 * @param {Object} params - Request parameters
 * @param {string} params.endpoint - The API endpoint called
 * @param {string} params.ip - Client IP address
 * @param {number} params.responseTime - Response time in ms
 * @param {number} params.statusCode - HTTP status code
 * @param {string} params.country - Country code (if available)
 * @param {Object} params.query - Query parameters
 */
function trackRequest({ endpoint, ip, responseTime, statusCode, country, query }) {
  resetCountersIfNeeded();

  // Update endpoint stats
  if (analyticsStore.endpoints[endpoint]) {
    analyticsStore.endpoints[endpoint].calls += 1;
    analyticsStore.endpoints[endpoint].totalTime += responseTime;
    if (statusCode >= 400) {
      analyticsStore.endpoints[endpoint].errors += 1;
    }
  }

  // Update counters
  analyticsStore.counters.today.calls += 1;
  analyticsStore.counters.week.calls += 1;
  analyticsStore.counters.month.calls += 1;
  analyticsStore.counters.allTime.calls += 1;

  // Track unique IPs
  analyticsStore.uniqueIPs.add(ip);

  // Update hourly data
  const hourKey = getHourKey();
  if (!analyticsStore.hourly.has(hourKey)) {
    analyticsStore.hourly.set(hourKey, { calls: 0, uniqueIPs: new Set() });
  }
  const hourData = analyticsStore.hourly.get(hourKey);
  hourData.calls += 1;
  hourData.uniqueIPs.add(ip);

  // Track country if available
  if (country && country !== 'unknown') {
    const count = analyticsStore.countries.get(country) || 0;
    analyticsStore.countries.set(country, count + 1);
  }

  // Add to recent requests (keep last 100)
  analyticsStore.recentRequests.unshift({
    endpoint,
    ip: ip.substring(0, 8) + '***', // Partially anonymize
    responseTime,
    statusCode,
    timestamp: new Date().toISOString(),
    query,
  });
  if (analyticsStore.recentRequests.length > 100) {
    analyticsStore.recentRequests.pop();
  }

  // Clean up old hourly data (keep last 24 hours)
  const cutoff = Date.now() - (24 * 60 * 60 * 1000);
  for (const [key] of analyticsStore.hourly) {
    if (new Date(key).getTime() < cutoff) {
      analyticsStore.hourly.delete(key);
    }
  }
}

/**
 * Get analytics summary
 * @returns {Object} Analytics data
 */
function getAnalytics() {
  resetCountersIfNeeded();

  // Calculate endpoint statistics
  const endpointStats = {};
  for (const [endpoint, stats] of Object.entries(analyticsStore.endpoints)) {
    endpointStats[endpoint] = {
      calls: stats.calls,
      avgResponseTime: stats.calls > 0 ? Math.round(stats.totalTime / stats.calls) : 0,
      errors: stats.errors,
      errorRate: stats.calls > 0 ? ((stats.errors / stats.calls) * 100).toFixed(2) + '%' : '0%',
    };
  }

  // Get hourly data for chart
  const hourlyData = [];
  const sortedHours = Array.from(analyticsStore.hourly.keys()).sort();
  for (const hour of sortedHours.slice(-24)) {
    const data = analyticsStore.hourly.get(hour);
    hourlyData.push({
      hour,
      calls: data.calls,
      uniqueIPs: data.uniqueIPs.size,
    });
  }

  // Get top countries
  const topCountries = Array.from(analyticsStore.countries.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([country, count]) => ({ country, count }));

  return {
    summary: {
      today: analyticsStore.counters.today.calls,
      thisWeek: analyticsStore.counters.week.calls,
      thisMonth: analyticsStore.counters.month.calls,
      allTime: analyticsStore.counters.allTime.calls,
      uniqueIPs: analyticsStore.uniqueIPs.size,
      uptime: Math.round((Date.now() - analyticsStore.counters.allTime.startTime) / 1000 / 60), // minutes
    },
    endpoints: endpointStats,
    hourly: hourlyData,
    countries: topCountries,
    recentRequests: analyticsStore.recentRequests.slice(0, 20),
    generatedAt: new Date().toISOString(),
  };
}

/**
 * Middleware to track requests
 * @param {Object} req - Request object
 * @param {string} endpoint - Endpoint name
 * @returns {Function} Function to call after response is sent
 */
function createTracker(req, endpoint) {
  const startTime = Date.now();

  return (statusCode) => {
    const responseTime = Date.now() - startTime;
    const forwarded = req.headers['x-forwarded-for'];
    const ip = (forwarded && forwarded.split(',')[0].trim()) ||
               req.headers['x-real-ip'] ||
               'unknown';
    const country = req.headers['x-vercel-ip-country'] || 'unknown';

    trackRequest({
      endpoint,
      ip,
      responseTime,
      statusCode,
      country,
      query: req.query || {},
    });
  };
}

module.exports = {
  trackRequest,
  getAnalytics,
  createTracker,
};
