const { existsSync, readdirSync } = require('fs');
const { join } = require('path');
const { withMiddleware } = require('../lib/middleware.js');
const { includes, paginate, readCsv } = require('../lib/data.js');

function availableSeasons() {
  const directory = join(process.cwd(), 'data', 'odds_quotes');
  if (!existsSync(directory)) return [];
  return readdirSync(directory)
    .map((name) => name.match(/^cpl_(\d{4})_odds_quotes\.csv$/))
    .filter(Boolean)
    .map((match) => Number(match[1]))
    .sort();
}

async function oddsQuotesHandler(req, res, { track, errors, validateNumber }) {
  const seasons = availableSeasons();
  const seasonCheck = validateNumber(req.query.season, 'season', 2019, 2030);
  if (!seasonCheck.valid) return errors.badRequest(res, seasonCheck.error);
  const season = seasonCheck.value || seasons.at(-1);
  if (!seasons.includes(season)) return errors.notFound(res, `No odds quotes for season ${season}. Available: ${seasons.join(', ')}`);
  let quotes = readCsv(`data/odds_quotes/cpl_${season}_odds_quotes.csv`);
  if (req.query.team) quotes = quotes.filter((row) => includes(`${row.home_team} ${row.away_team}`, req.query.team));
  if (req.query.bookmaker) quotes = quotes.filter((row) => includes(row.bookmaker, req.query.bookmaker));
  if (req.query.market) quotes = quotes.filter((row) => includes(row.market, req.query.market));
  if (req.query.date) quotes = quotes.filter((row) => row.date === req.query.date);
  quotes.sort((a, b) => String(b.captured_at).localeCompare(String(a.captured_at)));
  const page = paginate(quotes, req.query);
  track(200);
  return res.status(200).json({
    season, available_seasons: seasons, total: page.total, count: page.count,
    limit: page.limit, offset: page.offset, has_more: page.has_more, quotes: page.items,
  });
}

module.exports = withMiddleware(oddsQuotesHandler, { endpoint: '/api/odds-quotes', cache: 's-maxage=300, stale-while-revalidate=900' });
