/**
 * Shared middleware for all API routes
 * Provides CORS, rate limiting, analytics, and error handling
 */

import { getClientIP, checkRateLimit, setRateLimitHeaders, sendRateLimitExceeded } from './rateLimit.js';
import { createTracker } from './analytics.js';

/**
 * Standard CORS headers for public API
 */
export function setCorsHeaders(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Access-Control-Max-Age', '86400'); // 24 hours
}

/**
 * Handle OPTIONS preflight request
 */
export function handlePreflight(req, res) {
  if (req.method === 'OPTIONS') {
    setCorsHeaders(res);
    res.status(200).end();
    return true;
  }
  return false;
}

/**
 * Standard error responses
 */
export const errors = {
  badRequest: (res, message = 'Bad request') => {
    return res.status(400).json({
      error: 'Bad Request',
      message,
      status: 400,
    });
  },

  notFound: (res, message = 'Resource not found') => {
    return res.status(404).json({
      error: 'Not Found',
      message,
      status: 404,
    });
  },

  methodNotAllowed: (res, allowed = ['GET']) => {
    res.setHeader('Allow', allowed.join(', '));
    return res.status(405).json({
      error: 'Method Not Allowed',
      message: `Only ${allowed.join(', ')} methods are allowed`,
      status: 405,
    });
  },

  serverError: (res, message = 'Internal server error') => {
    return res.status(500).json({
      error: 'Internal Server Error',
      message,
      status: 500,
    });
  },
};

/**
 * Validate numeric parameter
 */
export function validateNumber(value, name, min = 0, max = Infinity) {
  if (value === undefined || value === '') return { valid: true, value: undefined };

  const num = parseInt(value, 10);
  if (isNaN(num)) {
    return { valid: false, error: `${name} must be a valid number` };
  }
  if (num < min) {
    return { valid: false, error: `${name} must be at least ${min}` };
  }
  if (num > max) {
    return { valid: false, error: `${name} must be at most ${max}` };
  }
  return { valid: true, value: num };
}

/**
 * Wrap an API handler with middleware
 * @param {Function} handler - The API handler function
 * @param {Object} options - Middleware options
 * @param {string} options.endpoint - Endpoint name for analytics
 * @param {boolean} options.rateLimit - Whether to apply rate limiting (default: true)
 * @returns {Function} Wrapped handler
 */
export function withMiddleware(handler, options = {}) {
  const { endpoint = '/api/unknown', rateLimit = true } = options;

  return async (req, res) => {
    // Set CORS headers
    setCorsHeaders(res);

    // Handle preflight
    if (handlePreflight(req, res)) {
      return;
    }

    // Only allow GET requests for data endpoints
    if (req.method !== 'GET') {
      return errors.methodNotAllowed(res, ['GET']);
    }

    // Create analytics tracker
    const track = createTracker(req, endpoint);

    // Apply rate limiting
    if (rateLimit) {
      const ip = getClientIP(req);
      const rateLimitInfo = checkRateLimit(ip);
      setRateLimitHeaders(res, rateLimitInfo);

      if (!rateLimitInfo.allowed) {
        track(429);
        return sendRateLimitExceeded(res, rateLimitInfo);
      }
    }

    // Set cache headers
    res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate');

    try {
      // Call the actual handler
      const result = await handler(req, res, { track, errors, validateNumber });

      // If handler didn't send response, track success
      if (!res.headersSent) {
        track(200);
      }

      return result;
    } catch (error) {
      console.error(`Error in ${endpoint}:`, error);
      track(500);
      return errors.serverError(res, 'An unexpected error occurred');
    }
  };
}
