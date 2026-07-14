'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const engine = require('../src/eq_proof/web/browser-engine.js');

test('parses quoted CSV and normalizes project-control aliases', () => {
  const [row] = engine.parseCsvText(
    'control_account_id,AC,ETC,EAC,comment\r\n'
    + 'CA-1,10,5,14,"line one, line two"\r\n',
  );
  const normalized = engine.normalizeRow(row);
  assert.equal(normalized.record_id, 'CA-1');
  assert.equal(normalized.AC, '10');
  assert.equal(row.comment, 'line one, line two');
});

test('parses Primavera TASK records into activity rows', () => {
  const rows = engine.parseXerText([
    'ERMHDR\t23.12\t2026-07-13',
    '%T\tTASK',
    '%F\ttask_id\ttask_code\ttask_name\tstatus_code\tremain_drtn_hr_cnt\ttotal_float_hr_cnt',
    '%R\t1\tA100\tFoundations\tTK_Active\t0\t-960',
  ].join('\n'));
  assert.equal(rows.length, 1);
  assert.equal(rows[0].record_id, 'A100');
  assert.equal(rows[0].remaining_duration_hours, '0');
  assert.equal(rows[0].total_float_hours, '-960');
});

test('evaluates the safe expression language without executable JavaScript', () => {
  assert.deepEqual(
    engine.evaluateEquation('EAC == AC + ETC', { EAC: 15, AC: 10, ETC: 5 }, 1e-6),
    { passed: true, residual: 0, residual_state: 'finite' },
  );
  assert.deepEqual(
    engine.evaluateEquation('total_float_hours >= -800', { total_float_hours: -960 }, 1e-6),
    { passed: false, residual: 160, residual_state: 'finite' },
  );
  assert.throws(
    () => engine.parseExpression('constructor.constructor("return globalThis")() == 1'),
    /Unsupported equation token|Unexpected token|Unsupported equation function/,
  );
});

test('validates equation packs and rejects undeclared fields', () => {
  const equation = engine.validateEquation({
    id: 'custom.authorization',
    title: 'EAC remains inside delegated authorization',
    domain: 'governance',
    expression: 'EAC <= delegated_authorization',
    severity: 'blocker',
    required_fields: ['EAC', 'delegated_authorization'],
    record_type: 'control_account',
  });
  assert.equal(equation.id, 'custom.authorization');
  assert.throws(
    () => engine.validateEquation({
      ...equation,
      id: 'custom.invalid',
      expression: 'EAC <= undeclared',
    }),
    /missing expression fields: undeclared/,
  );
});

test('builds a blocked Control Room payload from supplied records', () => {
  const records = [
    {
      record_id: 'CA-1',
      AC: 10,
      ETC: 5,
      EAC: 12,
      pending_change_exposure: 2,
      risk_exposure: 1,
      risk_adjusted_EAC: 15,
      _record_type: 'control_account',
      _source: 'cost.csv',
      _source_sha256: 'a'.repeat(64),
    },
    {
      record_id: 'A-1',
      remaining_duration_hours: 0,
      total_float_hours: -960,
      status_code: 'TK_Active',
      _record_type: 'activity',
      _source: 'schedule.xer',
      _source_sha256: 'b'.repeat(64),
    },
  ];
  const equations = engine.validateEquationSet(engine.catalogue);
  const analysis = engine.analyzeRecords(records, equations, ['cost.csv', 'schedule.xer']);
  const payload = engine.buildControlRoom(records, analysis, 'CAD', equations);

  assert.equal(payload.schema_version, 'eq-proof/control-room@2');
  assert.equal(payload.units.currency, 'CAD');
  assert.equal(payload.gate.status, 'blocked');
  assert.equal(payload.portfolio.reported_eac, 12);
  assert.equal(payload.portfolio.defensible_eac, 15);
  assert.equal(payload.portfolio.deterministic_forecast_gap, 3);
  assert.equal(payload.portfolio.reconstructed_risk_adjusted_eac, 18);
  assert.equal(payload.portfolio.exposure_above_reported_eac, 6);
  assert.equal(payload.analysis.source_manifest.length, 2);
  assert.ok(payload.exceptions.some((item) => item.equation_id === 'cost.eac_identity'));
  assert.ok(payload.exceptions.some((item) => item.equation_id === 'schedule.progress_duration'));
});
