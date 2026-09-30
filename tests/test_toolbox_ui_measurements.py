"""Behavioral contract for dependency-free Toolbox measurement helpers."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "evals" / "ui" / "src" / "measurements.ts"


@unittest.skipUnless(shutil.which("bun"), "Bun is required for TypeScript module checks")
class MeasurementTests(unittest.TestCase):
    def run_module(self, body):
        script = """import assert from 'node:assert/strict';
import * as measurements from %s;
%s
""" % (json.dumps(MODULE.as_uri()), body)
        result = subprocess.run(["bun", "--eval", script], text=True, capture_output=True,
                                check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_measurement_values_require_an_observed_v1_envelope(self):
        self.run_module("""
const run = {
  duration_ms: 0, passed: false,
  measurement: {version: 1, available: {duration_ms: true, passed: true}, execution: {validity: 'valid'}},
};
assert.equal(measurements.measurementNumber(run, 'duration_ms'), 0);
assert.equal(measurements.measurementBoolean(run, 'passed'), false);
for (const bad of [
  {},
  {measurement: {}},
  {duration_ms: 2, measurement: {version: 2, available: {duration_ms: true}}},
  {duration_ms: 2, measurement: {version: 1, available: {duration_ms: false}}},
  {duration_ms: 2, measurement: {version: 1, available: {}}},
  {duration_ms: -1, measurement: {version: 1, available: {duration_ms: true}}},
  {duration_ms: NaN, measurement: {version: 1, available: {duration_ms: true}}},
  {duration_ms: Infinity, measurement: {version: 1, available: {duration_ms: true}}},
  {duration_ms: '2', measurement: {version: 1, available: {duration_ms: true}}},
]) assert.equal(measurements.measurementNumber(bad, 'duration_ms'), null);
for (const bad of [
  {passed: false, measurement: {version: 1, available: {passed: false}}},
  {passed: false, measurement: {version: 1, available: {}}},
  {passed: 'false', measurement: {version: 1, available: {passed: true}}},
  {passed: 0, measurement: {version: 1, available: {passed: true}}},
]) assert.equal(measurements.measurementBoolean(bad, 'passed'), null);
""")

    def test_comparison_requires_a_distinct_valid_controlled_pair(self):
        self.run_module("""
const pair = (overrides = {}) => [{
  id: 'base', campaign: 'campaign', candidate: 'candidate', case: 'case', harness: 'harness', model: 'model', config: 'baseline', passed: false,
  measurement: {version: 1, available: {}, execution: {validity: 'valid'}},
}, {
  id: 'with', campaign: 'campaign', candidate: 'candidate', case: 'case', harness: 'harness', model: 'model', config: 'with', passed: false,
  measurement: {version: 1, available: {}, execution: {validity: 'valid'}},
}].map((item, index) => ({...item, ...(overrides[index] || {})}));
let eligible = measurements.comparisonEligibility(pair().reverse());
assert.equal(eligible.reason, null);
assert.equal(eligible.baseline.id, 'base');
assert.equal(eligible.with.id, 'with');
for (const key of ['campaign', 'candidate', 'case', 'harness', 'model']) {
  const changed = pair([{[key]: 'other'}]);
  assert.equal(measurements.comparisonEligibility(changed).reason, `${key}-mismatch`);
  const absent = pair([{[key]: ' '}]);
  assert.equal(measurements.comparisonEligibility(absent).reason, `missing-${key}`);
}
assert.equal(measurements.comparisonEligibility([pair()[0]]).reason, 'select-exactly-two');
assert.equal(measurements.comparisonEligibility(pair([{id: 'with'}])).reason, 'duplicate-record');
assert.equal(measurements.comparisonEligibility(pair([{id: ' '}])).reason, 'duplicate-record');
assert.equal(measurements.comparisonEligibility(pair([{config: 'with'}])).reason, 'configuration-mismatch');
assert.equal(measurements.comparisonEligibility(pair([{measurement: {version: 2, available: {}, execution: {validity: 'valid'}}}])).reason, 'execution-invalid');
assert.equal(measurements.comparisonEligibility(pair([{measurement: {version: 1, execution: {validity: 'valid'}}}])).reason, 'execution-invalid');
assert.equal(measurements.comparisonEligibility(pair([{measurement: {version: 1, available: {}, execution: {validity: 'unknown'}}}])).reason, 'execution-invalid');
assert.equal(measurements.comparisonEligibility(pair([{measurement: {version: 1, available: {}, execution: {validity: 'invalid'}}}])).reason, 'execution-invalid');
assert.equal(measurements.comparisonEligibility(pair([{measurement: {version: 1, available: {}, execution: {validity: 'skipped'}}}])).reason, 'execution-invalid');
assert.equal(measurements.comparisonEligibility(pair([{measurement: {version: 1, available: {}}}])).reason, 'execution-invalid');
""")

    def test_deltas_never_convert_missing_or_zero_denominators_to_numbers(self):
        self.run_module("""
assert.deepEqual(measurements.descriptiveDelta(4, 7), {delta: 3, percent: 75});
assert.deepEqual(measurements.descriptiveDelta(0, 7), {delta: 7, percent: null});
assert.deepEqual(measurements.descriptiveDelta(null, 7), {delta: null, percent: null});
assert.deepEqual(measurements.descriptiveDelta(4, null), {delta: null, percent: null});
assert.deepEqual(measurements.descriptiveDelta(Infinity, 7), {delta: null, percent: null});
assert.deepEqual(measurements.descriptiveDelta(4, NaN), {delta: null, percent: null});
assert.deepEqual(measurements.descriptiveDelta(Number.MIN_VALUE, Number.MAX_VALUE), {delta: Number.MAX_VALUE, percent: null});
assert.deepEqual(measurements.descriptiveDelta(-Number.MAX_VALUE, Number.MAX_VALUE), {delta: null, percent: null});
""")


if __name__ == "__main__":
    unittest.main()
