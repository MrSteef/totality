import assert from 'node:assert/strict';
import { eclipseAt } from './eclipse.mjs';
const fixtures = [
  ['Sana (Timeanddate nominal location)', 15.35, 44.216667, 148, 15],
  ['Luxor', 25.6872, 32.6396, 382, 8],
  ['Jeddah', 21.5433, 39.1728, 355, 8],
  ['Tarifa', 36.013, -5.605, 280, 8],
  ['Cairo (outside totality)', 30.0444, 31.2357, 0, 0],
  // NASA's 10:46 UT table gives geographic limits and central duration.
  ['NASA south path limit at 10:46', 15 + 7.1 / 60, 44 + 20.3 / 60, 0, 25],
  ['NASA north path limit at 10:46', 16 + 42 / 60, 46 + 7.6 / 60, 0, 25],
  ['NASA centerline at 10:46', 15 + 54.7 / 60, 45 + 13.5 / 60, 353.8, 8],
  ['NASA greatest duration point', 26 + 49 / 60, 31 + 8 / 60, 383.2, 5],
];
for (const [name, lat, lon, expected, tolerance] of fixtures) {
  const actual = eclipseAt(lat, lon).durationSeconds;
  assert.ok(Math.abs(actual - expected) <= tolerance, `${name}: ${actual.toFixed(1)}s vs ${expected}s`);
  console.log(`${name}: ${actual.toFixed(1)}s (reference ${expected}s)`);
}
console.log('All regression checks passed');
