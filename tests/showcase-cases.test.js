'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const engine = require('../src/eq_proof/web/browser-engine.js');

const root = path.resolve(__dirname, '..');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'src/eq_proof/web/showcase-cases.json'), 'utf8'));

for (const example of manifest.cases) {
  test(`showcase ${example.id}: browser compiles real files to the Python known answer`, () => {
    const records = [];
    const equations = [...engine.catalogue];
    for (const source of example.source_files) {
      const raw = fs.readFileSync(path.join(root, 'examples/close_walkthrough', example.id, source.name));
      assert.equal(source.content, raw.toString('utf8'));
      assert.equal(source.sha256, crypto.createHash('sha256').update(raw).digest('hex'));
      if (source.kind === 'equation_pack') {
        equations.push(...JSON.parse(source.content));
        continue;
      }
      const rows = source.kind === 'p6_xer'
        ? engine.parseXerText(source.content)
        : engine.parseCsvText(source.content).map(engine.normalizeRow);
      records.push(...rows.map((row) => ({
        ...row,
        _record_type: source.kind === 'p6_xer' ? 'activity' : 'control_account',
        _source: source.name,
        _source_sha256: source.sha256,
      })));
    }
    const validated = engine.validateEquationSet(equations);
    const analysis = engine.analyzeRecords(records, validated, example.source_files.map((source) => source.name));
    const actual = engine.buildControlRoom(records, analysis, example.currency, validated);
    const expected = example.control_room;
    assert.deepEqual(actual.gate, expected.gate);
    assert.deepEqual(actual.portfolio, expected.portfolio);
    assert.deepEqual(actual.analysis.source_manifest, expected.analysis.source_manifest);
    assert.deepEqual(actual.analysis.summary, expected.analysis.summary);
    assert.equal(actual.analysis.equations_executed, 32);
    assert.equal(actual.gate.status, example.expected.gate_status);
    assert.equal(actual.gate.blockers, example.expected.blockers);
    assert.equal(actual.gate.failures, example.expected.failures);
    assert.equal(actual.analysis.summary.not_applicable, 1);
    for (const [key, value] of Object.entries(example.expected.portfolio)) {
      assert.equal(actual.portfolio[key], value, key);
    }
    const compact = (item) => [item.equation_id, item.record_id, item.status, item.severity, item.residual];
    assert.deepEqual(actual.analysis.findings.map(compact), expected.analysis.findings.map(compact));
    const authorization = actual.analysis.findings.filter((item) => item.equation_id === 'portfolio.board_authorization');
    assert.equal(authorization.length, 3);
    assert.ok(authorization.every((item) => item.status === 'pass'));
    const published = JSON.parse(fs.readFileSync(path.join(root, 'evidence/close-walkthrough', example.id, 'control-room.json'), 'utf8'));
    assert.deepEqual(published, expected);
    engine.setCurrentPayload(published, false);
    assert.deepEqual(engine.getCurrentPayload().demo, {
      name: example.title,
      description: example.description,
      synthetic: true,
      showcase_case: example.id,
    });
  });
}
