// Generate a 20-question practice exam, optionally filtered by topic.
// Env: BASE_URL, COURSE, TOPIC, VUS, DURATION
import http from 'k6/http';
import { check } from 'k6';

const BASE = __ENV.BASE_URL || 'http://localhost:8000';
const COURSE = __ENV.COURSE || 'COURSE001';
const TOPIC = __ENV.TOPIC || '';

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

export default function () {
  const body = { course_code: COURSE, num_questions: 20 };
  if (TOPIC) body.topics = [TOPIC];
  const res = http.post(`${BASE}/api/exams`, JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } });
  check(res, { 'status 200': (r) => r.status === 200, 'has 20 questions': (r) => (r.json('questions') || []).length === 20 });
}
