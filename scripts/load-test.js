/**
 * OrthoFlow Load Test — k6 Script
 * Tests critical API paths under simulated multi-user load.
 *
 * Run: k6 run scripts/load-test.js
 * Or with Docker: docker run --rm -i --network orthoflow_orthoflow grafana/k6 run - < scripts/load-test.js
 *
 * Stages:
 *   1. Ramp up to 50 users over 1 min
 *   2. Hold 50 users for 3 min (steady state)
 *   3. Spike to 150 users for 1 min (burst traffic)
 *   4. Ramp down over 1 min
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const loginDuration = new Trend('login_duration');
const scheduleDuration = new Trend('schedule_duration');
const patientsDuration = new Trend('patients_duration');

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://backend:8000';
const DEMO_EMAIL = 'demo@orthoflowsolutions.com';
const DEMO_PASSWORD = 'Demo2026!';

export const options = {
  stages: [
    { duration: '1m', target: 50 },    // Ramp up
    { duration: '3m', target: 50 },    // Steady state
    { duration: '1m', target: 150 },   // Spike
    { duration: '1m', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'],  // 95% of requests under 2s
    errors: ['rate<0.05'],              // Less than 5% error rate
    login_duration: ['p(95)<3000'],     // Login under 3s at p95
    schedule_duration: ['p(95)<1500'],  // Schedule load under 1.5s
    patients_duration: ['p(95)<1500'],  // Patient list under 1.5s
  },
};

// Shared token store (set during setup)
let authToken = '';

export function setup() {
  // Get a valid token for all VUs
  const loginRes = http.post(`${BASE_URL}/api/v1/auth/login`, JSON.stringify({
    email: DEMO_EMAIL,
    password: DEMO_PASSWORD,
  }), { headers: { 'Content-Type': 'application/json' } });

  if (loginRes.status === 200) {
    const data = JSON.parse(loginRes.body);
    return { token: data.access_token };
  }
  return { token: '' };
}

export default function (data) {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${data.token}`,
  };

  // ── Auth Flow ────────────────────────────────────────────────────────────
  group('Authentication', () => {
    const start = Date.now();
    const res = http.post(`${BASE_URL}/api/v1/auth/login`, JSON.stringify({
      email: DEMO_EMAIL,
      password: DEMO_PASSWORD,
    }), { headers: { 'Content-Type': 'application/json' } });

    loginDuration.add(Date.now() - start);
    const success = check(res, { 'login success': (r) => r.status === 200 });
    errorRate.add(!success);
  });

  sleep(0.5);

  // ── Schedule (heaviest page — joins appointments, patients, DAs) ─────────
  group('Schedule', () => {
    const today = new Date().toISOString().split('T')[0];
    const start = Date.now();
    const res = http.get(`${BASE_URL}/api/v1/schedule?schedule_date=${today}`, { headers });

    scheduleDuration.add(Date.now() - start);
    const success = check(res, {
      'schedule 200': (r) => r.status === 200,
      'schedule has data': (r) => r.body.includes('appointments') || r.body.includes('chairs'),
    });
    errorRate.add(!success);
  });

  sleep(0.3);

  // ── Patient List (paginated) ─────────────────────────────────────────────
  group('Patients', () => {
    const start = Date.now();
    const res = http.get(`${BASE_URL}/api/v1/patients?page=1&size=20`, { headers });

    patientsDuration.add(Date.now() - start);
    const success = check(res, {
      'patients 200': (r) => r.status === 200,
    });
    errorRate.add(!success);
  });

  sleep(0.3);

  // ── Dashboard (visit tracker + schedule) ─────────────────────────────────
  group('Dashboard', () => {
    const res = http.get(`${BASE_URL}/api/v1/visit-tracker`, { headers });
    check(res, { 'visit-tracker 200': (r) => r.status === 200 || r.status === 404 });

    const today = new Date().toISOString().split('T')[0];
    const schedRes = http.get(`${BASE_URL}/api/v1/schedule?schedule_date=${today}`, { headers });
    check(schedRes, { 'dashboard schedule 200': (r) => r.status === 200 });
  });

  sleep(0.3);

  // ── Clinical (charting endpoints) ────────────────────────────────────────
  group('Clinical', () => {
    // CDT codes catalog (read-heavy, should be fast)
    const cdtRes = http.get(`${BASE_URL}/api/v1/catalog/cdt-codes?limit=20`, { headers });
    check(cdtRes, { 'cdt-codes 200': (r) => r.status === 200 });

    // Recall stats
    const recallRes = http.get(`${BASE_URL}/api/v1/recall/stats`, { headers });
    check(recallRes, { 'recall-stats 200': (r) => r.status === 200 || r.status === 404 });
  });

  sleep(1);
}

export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
    'load-test-results.json': JSON.stringify(data, null, 2),
  };
}

function textSummary(data, opts) {
  // k6 built-in summary
  return '';
}
