/**
 * Simple in-memory rate limiting for Vercel serverless functions
 * Note: This uses in-memory storage which resets on cold starts.
 * For production, consider using Vercel KV, Upstash Redis, or Edge Config.
 */

// In-memory store for rate limiting
// Structure: { [ip]: { count: number, resetTime: number } }
const rateLimitStore = new Map();

// Clean up expired entries periodically
const CLEANUP_INTERVAL = 5 * 60 * 1000; // 5 minutes
let lastCleanup = Date.now();

function cleanupExpiredEntries() {
  const now = Date.now();
  if (now - lastCleanup < CLEANUP_INTERVAL) return;

  lastCleanup = now;
  for (const [ip, data] of rateLimitStore.entries()) {
    if (now > data.resetTime) {
      rateLimitStore.delete(ip);
    }
  }
}

/**
 * Rate limit configuration
 */
export const RATE_LIMIT = {
  windowMs: 60 * 60 * 1000, // 1 hour
  maxRequests: 20,          // 20 requests per hour
};

/**
 * Get client IP from request
 */
export function getClientIP(req) {
  // Vercel provides the real IP in x-forwarded-for or x-real-ip
  const forwarded = req.headers['x-forwarded-for'];
  if (forwarded) {
    return forwarded.split(',')[0].trim();
  }
  return req.headers['x-real-ip'] ||
         req.socket?.remoteAddress ||
         'unknown';
}

/**
 * Check rate limit and return status
 * @param {string} ip - Client IP address
 * @returns {{ allowed: boolean, remaining: number, resetTime: number, limit: number }}
 */
export function checkRateLimit(ip) {
  cleanupExpiredEntries();

  const now = Date.now();
  const windowEnd = now + RATE_LIMIT.windowMs;

  let record = rateLimitStore.get(ip);

  if (!record || now > record.resetTime) {
    // New window or expired - create fresh record
    record = {
      count: 1,
      resetTime: windowEnd,
    };
    rateLimitStore.set(ip, record);

    return {
      allowed: true,
      remaining: RATE_LIMIT.maxRequests - 1,
      resetTime: windowEnd,
      limit: RATE_LIMIT.maxRequests,
    };
  }

  // Existing window - check count
  if (record.count >= RATE_LIMIT.maxRequests) {
    return {
      allowed: false,
      remaining: 0,
      resetTime: record.resetTime,
      limit: RATE_LIMIT.maxRequests,
    };
  }

  // Increment and allow
  record.count += 1;
  rateLimitStore.set(ip, record);

  return {
    allowed: true,
    remaining: RATE_LIMIT.maxRequests - record.count,
    resetTime: record.resetTime,
    limit: RATE_LIMIT.maxRequests,
  };
}

/**
 * Apply rate limit headers to response
 * @param {Object} res - Response object
 * @param {Object} rateLimitInfo - Rate limit status from checkRateLimit
 */
export function setRateLimitHeaders(res, rateLimitInfo) {
  res.setHeader('X-RateLimit-Limit', rateLimitInfo.limit);
  res.setHeader('X-RateLimit-Remaining', rateLimitInfo.remaining);
  res.setHeader('X-RateLimit-Reset', Math.ceil(rateLimitInfo.resetTime / 1000));
}

/**
 * Send rate limit exceeded response
 * @param {Object} res - Response object
 * @param {Object} rateLimitInfo - Rate limit status
 */
export function sendRateLimitExceeded(res, rateLimitInfo) {
  const resetDate = new Date(rateLimitInfo.resetTime);
  const retryAfter = Math.ceil((rateLimitInfo.resetTime - Date.now()) / 1000);

  res.setHeader('Retry-After', retryAfter);
  setRateLimitHeaders(res, rateLimitInfo);

  return res.status(429).json({
    error: 'Rate limit exceeded',
    message: `You have exceeded the rate limit of ${rateLimitInfo.limit} requests per hour. Please try again later.`,
    retryAfter: retryAfter,
    resetTime: resetDate.toISOString(),
  });
}
