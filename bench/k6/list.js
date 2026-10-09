// Deep-page listing of questions for one course, optionally filtered by topic.
// Env: BASE_URL, COURSE, TOPIC, PAGINATION=offset|cursor, VUS, DURATION
import http from 'k6/http';
import { check } from 'k6';

const BASE = __ENV.BASE_URL || 'http://localhost:8000';
const COURSE = __ENV.COURSE || 'COURSE001';
const TOPIC = __ENV.TOPIC || '';
const MODE = __ENV.PAGINATION || 'offset';
const DEEP_OFFSET = Number(__ENV.DEEP_OFFSET || 10000);

export const options = {
  scenarios: {
    load: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS || 20),
      duration: __ENV.DURATION || '30s',
    },
  },
  summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

function url(extra, limit) {
  let u = `${BASE}/api/questions?course_code=${COURSE}&limit=${limit || 20}${extra}`;
  if (TOPIC) u += `&topic=${TOPIC}`;
  return u;
}

// Find the id that sits DEEP_OFFSET rows into the result set, so cursor mode
// asks for the same logical page as offset mode. Every version of the API
// accepts `offset`, so this works for all tags.
export function setup() {
  const res = http.get(url(`&offset=${DEEP_OFFSET - 1}`, 1));
  const items = res.json('items') || [];
  return { cursor: items.length ? items[0].id : 0 };
}

export default function (data) {
  const res = MODE === 'cursor' ? http.get(url(`&after=${data.cursor}`)) : http.get(url(`&offset=${DEEP_OFFSET}`));
  check(res, { 'status 200': (r) => r.status === 200, 'has 20 items': (r) => (r.json('items') || []).length === 20 });
}
