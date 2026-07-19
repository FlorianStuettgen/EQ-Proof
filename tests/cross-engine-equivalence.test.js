'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const engine = require('../src/eq_proof/web/browser-engine.js');

const ROOT = path.resolve(__dirname, '..');
const FIXTURE = path.join(ROOT, 'examples', 'hyperscale_close');
const EXPECTED = path.join(ROOT, 'src', 'eq_proof', 'web', 'demo-data.json');

function readFixture(name) {
  return fs.readFileSync(path.join(FIXTURE, name));
}

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function compactException(item) {
  return {
    equation_id: item.equation_id,
    record_type: item.record_type,
    record_id: item.record_id,
    status: item.status,
    severity: item.severity,
    residual: item.residual,
    residual_state: item.residual_state,
    impact_metric: item.impact_metric,
    materiality: item.materiality,
  };
}

function compactNode(item) {
  return {
    id: item.id,
    kind: item.kind,
    metric: item.metric || null,
    record_id: item.record_id || null,
    equation_id: item.equation_id || null,
    severity: item.severity || null,
  };
}

function compactEdge(item) {
  return `${item.source}|${item.relation}|${item.target}`;
}

test('browser engine matches the Python-generated Control Room semantics', () => {
  const scheduleBuffer = readFixture('schedule.xer');
  const costBuffer = readFixture('cost.csv');
  const equationsBuffer = readFixture('custom_equations.json');

  const scheduleRecords = engine.parseXerText(scheduleBuffer.toString('utf8')).map((row) => ({
    ...row,
    _record_type: 'activity',
    _source: 'schedule.xer',
    _source_sha256: sha256(scheduleBuffer),
  }));
  const costRecords = engine.parseCsvText(costBuffer.toString('utf8')).map((row) => ({
    ...engine.normalizeRow(row),
    _record_type: 'control_account',
    _source: 'cost.csv',
    _source_sha256: sha256(costBuffer),
  }));
  const customEquations = JSON.parse(equationsBuffer.toString('utf8'));
  const equations = engine.validateEquationSet([
    ...engine.catalogue,
    ...customEquations,
  ]);
  const records = [...scheduleRecords, ...costRecords];
  const analysis = engine.analyzeRecords(
    records,
    equations,
    ['schedule.xer', 'cost.csv', 'custom_equations.json'],
  );
  const actual = engine.buildControlRoom(records, analysis, 'USD', equations);
  const expected = JSON.parse(fs.readFileSync(EXPECTED, 'utf8'));

  assert.equal(actual.schema_version, expected.schema_version);
  assert.deepEqual(actual.units, expected.units);
  assert.deepEqual(actual.gate, expected.gate);
  assert.deepEqual(actual.assurance, expected.assurance);
  assert.deepEqual(actual.portfolio, expected.portfolio);
  assert.deepEqual(actual.domain_summary, expected.domain_summary);
  assert.deepEqual(actual.analysis.sources, expected.analysis.sources);
  assert.deepEqual(actual.analysis.source_manifest, expected.analysis.source_manifest);
  assert.equal(actual.analysis.records_analyzed, expected.analysis.records_analyzed);
  assert.equal(actual.analysis.equations_considered, expected.analysis.equations_considered);
  assert.equal(actual.analysis.equations_executed, expected.analysis.equations_executed);
  assert.equal(actual.analysis.close_ready, expected.analysis.close_ready);
  assert.equal(actual.analysis.gate_status, expected.analysis.gate_status);
  assert.deepEqual(actual.analysis.summary, expected.analysis.summary);

  assert.deepEqual(
    actual.exceptions.map(compactException),
    expected.exceptions.map(compactException),
  );
  assert.deepEqual(actual.graph.limits, expected.graph.limits);
  assert.deepEqual(
    actual.graph.nodes.map(compactNode).sort((a, b) => a.id.localeCompare(b.id)),
    expected.graph.nodes.map(compactNode).sort((a, b) => a.id.localeCompare(b.id)),
  );
  assert.deepEqual(
    actual.graph.edges.map(compactEdge).sort(),
    expected.graph.edges.map(compactEdge).sort(),
  );
});
