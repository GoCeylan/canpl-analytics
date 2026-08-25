const { existsSync, readFileSync, readdirSync } = require('fs');
const { join } = require('path');

function parseCsvLine(line) {
  const values = [];
  let current = '';
  let quoted = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];
    if (char === '"' && quoted && next === '"') {
      current += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === ',' && !quoted) {
      values.push(current);
      current = '';
    } else {
      current += char;
    }
  }
  values.push(current);
  return values;
}

function coerce(value) {
  if (value === undefined || value === null || value === '') return null;
  const trimmed = String(value).trim();
  if (/^-?(?:\d+|\d*\.\d+)$/.test(trimmed)) return Number(trimmed);
  if (trimmed.toLowerCase() === 'true') return true;
  if (trimmed.toLowerCase() === 'false') return false;
  return trimmed;
}

function readCsv(relativePath, options = {}) {
  const filePath = join(process.cwd(), relativePath);
  if (!existsSync(filePath)) return [];
  const content = readFileSync(filePath, 'utf8').replace(/^\uFEFF/, '').trim();
  if (!content) return [];
  const lines = content.replace(/\r/g, '').split('\n');
  const headers = parseCsvLine(lines.shift()).map((header) => header.trim());
  return lines
    .filter((line) => line.trim())
    .map((line) => {
      const values = parseCsvLine(line);
      return Object.fromEntries(headers.map((header, index) => [
        header,
        options.strings ? (values[index] ?? '') : coerce(values[index]),
      ]));
    });
}

function paginate(items, query = {}, defaultLimit = 100, maxLimit = 500) {
  const parsedLimit = Number.parseInt(query.limit, 10);
  const parsedOffset = Number.parseInt(query.offset, 10);
  const limit = Number.isFinite(parsedLimit) ? Math.min(Math.max(parsedLimit, 1), maxLimit) : defaultLimit;
  const offset = Number.isFinite(parsedOffset) ? Math.max(parsedOffset, 0) : 0;
  return {
    total: items.length,
    count: Math.max(0, Math.min(limit, items.length - offset)),
    limit,
    offset,
    has_more: offset + limit < items.length,
    items: items.slice(offset, offset + limit),
  };
}

function includes(value, query) {
  return String(value || '').toLocaleLowerCase().includes(String(query || '').toLocaleLowerCase());
}

function availableCsvSeasons(directory, prefix, suffix = '.csv') {
  const fullPath = join(process.cwd(), directory);
  if (!existsSync(fullPath)) return [];
  return readdirSync(fullPath)
    .map((name) => name.match(new RegExp(`^${prefix}(\\d{4})${suffix.replace('.', '\\.')}$`)))
    .filter(Boolean)
    .map((match) => Number(match[1]))
    .sort((a, b) => a - b);
}

module.exports = { availableCsvSeasons, coerce, includes, paginate, parseCsvLine, readCsv };
