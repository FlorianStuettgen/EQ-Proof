'use strict';

((global) => {
  const STORAGE_KEY = 'eq-proof/browser-workspace@1';
  const CONTROL_ROOM_SCHEMA = 'eq-proof/control-room@2';
  const MAX_CSV_ROWS = 500000;
  const MAX_XER_ROWS = 1000000;
  const MAX_EQUATIONS = 500;
  const SEVERITIES = ['blocker', 'major', 'minor', 'info'];
  const SEVERITY_RANK = new Map(SEVERITIES.map((name, index) => [name, index]));
  const RECORD_TYPES = new Set(['control_account', 'activity']);
  const ALLOWED_FUNCTIONS = new Set(['abs', 'min', 'max', 'round']);

  const ALIASES = {
    record_id: ['record_id', 'control_account_id', 'ca_id', 'wbs_code', 'task_code', 'activity_id'],
    BAC: ['BAC', 'bac', 'budget_at_completion'],
    AC: ['AC', 'ac', 'actual_cost', 'actuals'],
    ETC: ['ETC', 'etc', 'estimate_to_complete', 'remaining_cost'],
    EAC: ['EAC', 'eac', 'estimate_at_completion', 'forecast_at_completion'],
    PV: ['PV', 'pv', 'planned_value', 'bcws'],
    EV: ['EV', 'ev', 'earned_value', 'bcwp'],
    CV: ['CV', 'cv', 'cost_variance'],
    SV: ['SV', 'sv', 'schedule_variance'],
    VAC: ['VAC', 'vac', 'variance_at_completion'],
    CPI: ['CPI', 'cpi', 'cost_performance_index'],
    SPI: ['SPI', 'spi', 'schedule_performance_index'],
    baseline_budget: ['baseline_budget', 'original_budget'],
    approved_changes: ['approved_changes', 'approved_change'],
    current_budget: ['current_budget', 'revised_budget'],
    pending_change_exposure: ['pending_change_exposure', 'pending_changes', 'unapproved_changes'],
    risk_exposure: ['risk_exposure', 'quantified_risk', 'emv', 'configured_risk_uplift'],
    risk_adjusted_EAC: ['risk_adjusted_EAC', 'risk_adjusted_eac', 'P80_EAC', 'p80_eac'],
    actual_start: ['actual_start', 'act_start_date'],
    actual_finish: ['actual_finish', 'act_end_date'],
    early_start: ['early_start', 'early_start_date'],
    early_finish: ['early_finish', 'early_end_date'],
    late_finish: ['late_finish', 'late_end_date'],
    original_duration_hours: ['original_duration_hours', 'target_drtn_hr_cnt'],
    remaining_duration_hours: ['remaining_duration_hours', 'remain_drtn_hr_cnt'],
    total_float_hours: ['total_float_hours', 'total_float_hr_cnt'],
    physical_percent_complete: ['physical_percent_complete', 'phys_complete_pct'],
    status_code: ['status_code', 'task_status'],
  };

  const CATALOGUE = [
    {
      id: 'cost.eac_identity', title: 'EAC equals actual cost plus ETC', domain: 'cost',
      expression: 'EAC == AC + ETC', severity: 'blocker',
      description: 'The forecast at completion must reconcile to actual cost plus remaining forecast.',
      remediation: 'Reconcile the cost ledger and forecast detail; do not post the close until the identity holds.',
      required_fields: ['EAC', 'AC', 'ETC'], tolerance: 1e-6, record_type: 'control_account',
    },
    {
      id: 'cost.vac_identity', title: 'VAC equals BAC minus EAC', domain: 'cost',
      expression: 'VAC == BAC - EAC', severity: 'major',
      description: 'Variance at completion must agree with the approved budget and current EAC.',
      remediation: 'Recalculate VAC from governed BAC and EAC.',
      required_fields: ['VAC', 'BAC', 'EAC'], tolerance: 1e-6, record_type: 'control_account',
    },
    {
      id: 'evm.cv_identity', title: 'Cost variance equals EV minus AC', domain: 'earned_value',
      expression: 'CV == EV - AC', severity: 'major',
      description: 'Reported cost variance must reconcile to earned value and actual cost.',
      remediation: 'Recalculate CV and investigate source-period or currency mismatches.',
      required_fields: ['CV', 'EV', 'AC'], tolerance: 1e-6, record_type: 'control_account',
    },
    {
      id: 'evm.sv_identity', title: 'Schedule variance equals EV minus PV', domain: 'earned_value',
      expression: 'SV == EV - PV', severity: 'major',
      description: 'Reported schedule variance must reconcile to earned and planned value.',
      remediation: 'Recalculate SV and verify the status date and baseline time-phasing.',
      required_fields: ['SV', 'EV', 'PV'], tolerance: 1e-6, record_type: 'control_account',
    },
    {
      id: 'evm.cpi_identity', title: 'CPI equals EV divided by AC', domain: 'earned_value',
      expression: 'CPI == EV / AC', severity: 'major',
      description: 'The cost performance index must be derived from the same EV and AC basis.',
      remediation: 'Recalculate CPI; verify zero-value, currency and accounting-period handling.',
      required_fields: ['CPI', 'EV', 'AC'], tolerance: 1e-4, record_type: 'control_account',
    },
    {
      id: 'evm.spi_identity', title: 'SPI equals EV divided by PV', domain: 'earned_value',
      expression: 'SPI == EV / PV', severity: 'major',
      description: 'The schedule performance index must be derived from the same EV and PV basis.',
      remediation: 'Recalculate SPI and verify baseline and status-period alignment.',
      required_fields: ['SPI', 'EV', 'PV'], tolerance: 1e-4, record_type: 'control_account',
    },
    {
      id: 'change.budget_bridge', title: 'Current budget bridges baseline and approved change', domain: 'change',
      expression: 'current_budget == baseline_budget + approved_changes', severity: 'blocker',
      description: 'Current budget must be traceable to the baseline plus approved change.',
      remediation: 'Locate unauthorized budget movement or missing approved change records.',
      required_fields: ['current_budget', 'baseline_budget', 'approved_changes'], tolerance: 1e-6, record_type: 'control_account',
    },
    {
      id: 'risk.adjusted_bridge', title: 'Risk-adjusted EAC bridges forecast, pending change and configured risk uplift', domain: 'risk',
      expression: 'risk_adjusted_EAC == EAC + pending_change_exposure + risk_exposure', severity: 'major',
      description: 'The supplied risk-adjusted summary must reconcile to deterministic EAC, pending change and the configured risk uplift. This validates a declared bridge; it does not calculate a statistical P80.',
      remediation: 'Reconcile the risk register and pending-change log to the submitted risk-adjusted summary.',
      required_fields: ['risk_adjusted_EAC', 'EAC', 'pending_change_exposure', 'risk_exposure'], tolerance: 1e-6, record_type: 'control_account',
    },
    {
      id: 'schedule.progress_duration', title: 'In-progress activity retains remaining duration', domain: 'schedule',
      expression: 'remaining_duration_hours > 0', severity: 'major',
      description: 'An in-progress activity should retain positive remaining duration.',
      remediation: 'Correct activity status, actual finish or remaining duration in P6.',
      required_fields: ['remaining_duration_hours'], tolerance: 1e-6, record_type: 'activity',
      applicability_field: 'status_code', applicability_values: ['progress', 'active', 'tk_active'],
    },
    {
      id: 'schedule.extreme_negative_float', title: 'Total float remains above the starter review threshold', domain: 'schedule',
      expression: 'total_float_hours >= -800', severity: 'minor',
      description: 'The built-in -800 hour threshold is a conservative starter control for extreme negative float, not a contractual limit.',
      remediation: 'Replace the starter threshold with a project-specific equation, then review constraints, calendars and driving relationships.',
      required_fields: ['total_float_hours'], tolerance: 1e-6, record_type: 'activity',
    },
  ];

  let currentPayload = null;

  function browserError(message) {
    const error = new Error(message);
    error.name = 'EQProofBrowserError';
    return error;
  }

  function finiteNumber(value) {
    if (value === null || value === undefined || value === '' || typeof value === 'boolean') return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  }

  function normalizeRow(row) {
    const normalized = { ...row };
    const casefolded = new Map(Object.entries(row).map(([key, value]) => [String(key).toLowerCase(), value]));
    Object.entries(ALIASES).forEach(([canonical, aliases]) => {
      for (const alias of aliases) {
        if (Object.prototype.hasOwnProperty.call(row, alias)) {
          normalized[canonical] = row[alias];
          break;
        }
        const lower = alias.toLowerCase();
        if (casefolded.has(lower)) {
          normalized[canonical] = casefolded.get(lower);
          break;
        }
      }
    });
    if (Object.prototype.hasOwnProperty.call(normalized, 'risk_adjusted_EAC')) {
      if (!Object.prototype.hasOwnProperty.call(normalized, 'P80_EAC')) normalized.P80_EAC = normalized.risk_adjusted_EAC;
    } else if (Object.prototype.hasOwnProperty.call(normalized, 'P80_EAC')) {
      normalized.risk_adjusted_EAC = normalized.P80_EAC;
    }
    return normalized;
  }

  function parseCsvText(text) {
    const rows = [];
    let row = [];
    let field = '';
    let quoted = false;
    for (let index = 0; index < text.length; index += 1) {
      const char = text[index];
      if (quoted) {
        if (char === '"') {
          if (text[index + 1] === '"') {
            field += '"';
            index += 1;
          } else {
            quoted = false;
          }
        } else {
          field += char;
        }
        continue;
      }
      if (char === '"' && field === '') {
        quoted = true;
      } else if (char === ',') {
        row.push(field);
        field = '';
      } else if (char === '\n') {
        row.push(field.replace(/\r$/, ''));
        rows.push(row);
        row = [];
        field = '';
      } else {
        field += char;
      }
    }
    if (quoted) throw browserError('CSV contains an unterminated quoted field.');
    if (field !== '' || row.length) {
      row.push(field.replace(/\r$/, ''));
      rows.push(row);
    }
    while (rows.length && rows[rows.length - 1].every((value) => value === '')) rows.pop();
    if (!rows.length) throw browserError('CSV does not contain a header.');
    const headers = rows.shift().map((value, index) => index === 0 ? value.replace(/^\uFEFF/, '').trim() : value.trim());
    if (!headers.length || headers.some((value) => !value)) throw browserError('CSV header contains an empty column name.');
    const duplicates = headers.filter((value, index) => headers.indexOf(value) !== index);
    if (duplicates.length) throw browserError(`CSV contains duplicate columns: ${[...new Set(duplicates)].join(', ')}`);
    if (rows.length > MAX_CSV_ROWS) throw browserError(`CSV exceeds the ${MAX_CSV_ROWS.toLocaleString()}-row browser safety limit.`);
    return rows.filter((values) => values.some((value) => value !== '')).map((values, rowIndex) => {
      const output = {};
      headers.forEach((header, columnIndex) => { output[header] = values[columnIndex] ?? ''; });
      output._row = rowIndex + 2;
      return output;
    });
  }

  function parseXerText(text) {
    let table = '';
    let fields = [];
    const activities = [];
    text.replace(/^\uFEFF/, '').split(/\r?\n/).forEach((line) => {
      const parts = line.split('\t');
      const marker = parts[0] || '';
      if (marker === '%T') {
        table = parts[1] || '';
        fields = [];
      } else if (marker === '%F') {
        fields = parts.slice(1);
      } else if (marker === '%R' && table === 'TASK' && fields.length) {
        if (activities.length >= MAX_XER_ROWS) throw browserError(`XER exceeds the ${MAX_XER_ROWS.toLocaleString()}-activity browser safety limit.`);
        const values = parts.slice(1);
        const row = {};
        fields.forEach((field, index) => { row[field] = values[index] ?? ''; });
        const normalized = normalizeRow(row);
        normalized.record_id = row.task_code || row.task_id || 'unknown';
        normalized.activity_name = row.task_name || '';
        normalized.wbs_id = row.wbs_id || '';
        activities.push(normalized);
      }
    });
    if (!activities.length) throw browserError('No TASK records were found in the P6 XER.');
    return activities;
  }

  async function sha256File(file) {
    if (!global.crypto?.subtle) throw browserError('This browser does not provide the Web Crypto API required for source hashing.');
    const digest = await global.crypto.subtle.digest('SHA-256', await file.arrayBuffer());
    return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, '0')).join('');
  }

  function tokenize(expression) {
    if (typeof expression !== 'string' || !expression.trim()) throw browserError('Equation expression must be a non-empty string.');
    if (expression.length > 4096) throw browserError('Equation exceeds the 4,096-character browser limit.');
    const tokens = [];
    let index = 0;
    while (index < expression.length) {
      const rest = expression.slice(index);
      const whitespace = rest.match(/^\s+/);
      if (whitespace) { index += whitespace[0].length; continue; }
      const number = rest.match(/^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/);
      if (number) { tokens.push({ type: 'number', value: Number(number[0]) }); index += number[0].length; continue; }
      const identifier = rest.match(/^[A-Za-z_][A-Za-z0-9_]*/);
      if (identifier) { tokens.push({ type: 'identifier', value: identifier[0] }); index += identifier[0].length; continue; }
      const operator = ['==', '<=', '>=', '+', '-', '*', '/', '(', ')', ',', '<', '>'].find((item) => rest.startsWith(item));
      if (operator) { tokens.push({ type: 'operator', value: operator }); index += operator.length; continue; }
      throw browserError(`Unsupported equation token near “${rest.slice(0, 12)}”.`);
    }
    return tokens;
  }

  function parseExpression(expression) {
    const tokens = tokenize(expression);
    let cursor = 0;
    const peek = () => tokens[cursor];
    const consume = (value = null) => {
      const token = tokens[cursor];
      if (!token || (value !== null && token.value !== value)) throw browserError(value ? `Expected “${value}” in equation.` : 'Unexpected end of equation.');
      cursor += 1;
      return token;
    };
    const parsePrimary = () => {
      const token = peek();
      if (!token) throw browserError('Unexpected end of equation.');
      if (token.type === 'number') { consume(); return { type: 'number', value: token.value }; }
      if (token.type === 'identifier') {
        consume();
        if (peek()?.value !== '(') return { type: 'identifier', name: token.value };
        if (!ALLOWED_FUNCTIONS.has(token.value)) throw browserError(`Unsupported equation function: ${token.value}`);
        consume('(');
        const args = [];
        if (peek()?.value !== ')') {
          while (true) {
            args.push(parseAdditive());
            if (peek()?.value !== ',') break;
            consume(',');
          }
        }
        consume(')');
        if (token.value === 'abs' && args.length !== 1) throw browserError('abs() requires exactly one argument.');
        if (token.value === 'round' && ![1, 2].includes(args.length)) throw browserError('round() requires one or two arguments.');
        if (['min', 'max'].includes(token.value) && args.length < 1) throw browserError(`${token.value}() requires at least one argument.`);
        return { type: 'call', name: token.value, args };
      }
      if (token.value === '(') {
        consume('(');
        const node = parseAdditive();
        consume(')');
        return node;
      }
      throw browserError(`Unexpected token “${token.value}” in equation.`);
    };
    const parseUnary = () => {
      if (peek()?.value === '+' || peek()?.value === '-') {
        const operator = consume().value;
        return { type: 'unary', operator, operand: parseUnary() };
      }
      return parsePrimary();
    };
    const parseMultiplicative = () => {
      let node = parseUnary();
      while (peek()?.value === '*' || peek()?.value === '/') {
        const operator = consume().value;
        node = { type: 'binary', operator, left: node, right: parseUnary() };
      }
      return node;
    };
    const parseAdditive = () => {
      let node = parseMultiplicative();
      while (peek()?.value === '+' || peek()?.value === '-') {
        const operator = consume().value;
        node = { type: 'binary', operator, left: node, right: parseMultiplicative() };
      }
      return node;
    };
    const left = parseAdditive();
    const comparison = peek();
    if (!comparison || !['==', '<=', '>=', '<', '>'].includes(comparison.value)) throw browserError('Equation must contain exactly one comparison.');
    consume();
    const right = parseAdditive();
    if (cursor !== tokens.length) throw browserError('Equation must contain exactly one comparison.');
    return { type: 'comparison', operator: comparison.value, left, right };
  }

  function expressionFields(ast, output = new Set()) {
    if (!ast) return output;
    if (ast.type === 'identifier') output.add(ast.name);
    if (ast.left) expressionFields(ast.left, output);
    if (ast.right) expressionFields(ast.right, output);
    if (ast.operand) expressionFields(ast.operand, output);
    (ast.args || []).forEach((arg) => expressionFields(arg, output));
    return output;
  }

  function bankersRound(value, digits = 0) {
    const places = Number.isFinite(digits) ? Math.trunc(digits) : 0;
    const factor = 10 ** places;
    const scaled = value * factor;
    const lower = Math.floor(scaled);
    const fraction = scaled - lower;
    const rounded = Math.abs(fraction - 0.5) < 1e-12 ? (lower % 2 === 0 ? lower : lower + 1) : Math.round(scaled);
    return rounded / factor;
  }

  function evaluateAst(node, values) {
    if (node.type === 'number') return node.value;
    if (node.type === 'identifier') {
      if (!Object.prototype.hasOwnProperty.call(values, node.name)) throw browserError(`Missing equation field: ${node.name}`);
      return values[node.name];
    }
    if (node.type === 'unary') {
      const value = evaluateAst(node.operand, values);
      return node.operator === '-' ? -value : value;
    }
    if (node.type === 'binary') {
      const left = evaluateAst(node.left, values);
      const right = evaluateAst(node.right, values);
      if (node.operator === '+') return left + right;
      if (node.operator === '-') return left - right;
      if (node.operator === '*') return left * right;
      if (right === 0) throw browserError('Equation divided by zero.');
      return left / right;
    }
    if (node.type === 'call') {
      const args = node.args.map((arg) => evaluateAst(arg, values));
      if (node.name === 'abs') return Math.abs(args[0]);
      if (node.name === 'min') return Math.min(...args);
      if (node.name === 'max') return Math.max(...args);
      return bankersRound(args[0], args[1] ?? 0);
    }
    throw browserError('Unsupported equation syntax.');
  }

  function evaluateEquation(expression, values, tolerance = 1e-6) {
    const ast = parseExpression(expression);
    const left = evaluateAst(ast.left, values);
    const right = evaluateAst(ast.right, values);
    if (!Number.isFinite(left) || !Number.isFinite(right)) return { passed: false, residual: null, residual_state: 'non_finite' };
    const residual = left - right;
    let passed;
    let normalizedResidual = residual;
    if (ast.operator === '==') passed = Math.abs(residual) <= tolerance;
    if (ast.operator === '<=') { passed = residual <= tolerance; normalizedResidual = Math.max(0, residual); }
    if (ast.operator === '>=') { passed = residual >= -tolerance; normalizedResidual = Math.max(0, -residual); }
    if (ast.operator === '<') { passed = residual < 0; normalizedResidual = Math.max(0, residual); }
    if (ast.operator === '>') { passed = residual > 0; normalizedResidual = Math.max(0, -residual); }
    return { passed, residual: normalizedResidual, residual_state: 'finite' };
  }

  function validateEquation(raw) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw browserError('Equation must be a JSON object.');
    const equation = {
      id: String(raw.id || '').trim(),
      title: String(raw.title || raw.id || '').trim(),
      domain: String(raw.domain || 'custom').trim() || 'custom',
      expression: String(raw.expression || '').trim(),
      severity: String(raw.severity || 'major'),
      description: String(raw.description || '').trim(),
      remediation: String(raw.remediation || 'Review the source data and equation.').trim(),
      required_fields: Array.isArray(raw.required_fields) ? raw.required_fields.map(String) : [],
      tolerance: raw.tolerance === undefined ? 1e-6 : Number(raw.tolerance),
      record_type: String(raw.record_type || 'control_account'),
      applicability_field: raw.applicability_field || raw.applies_when?.field || null,
      applicability_values: raw.applicability_values || raw.applies_when?.contains_any || [],
    };
    if (!/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(equation.id)) throw browserError('Equation id must be a stable identifier of at most 128 characters.');
    if (!equation.title) throw browserError(`${equation.id}.title must be a non-empty string.`);
    if (!SEVERITIES.includes(equation.severity)) throw browserError(`${equation.id}.severity must be one of: ${SEVERITIES.join(', ')}.`);
    if (!RECORD_TYPES.has(equation.record_type)) throw browserError(`${equation.id}.record_type must be control_account or activity.`);
    if (!equation.required_fields.length) throw browserError(`${equation.id}.required_fields must be a non-empty string array.`);
    const unique = new Set();
    equation.required_fields.forEach((field) => {
      if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(field)) throw browserError(`${equation.id} contains an invalid field name: ${field}`);
      if (unique.has(field)) throw browserError(`${equation.id}.required_fields contains duplicates.`);
      unique.add(field);
    });
    if (!Number.isFinite(equation.tolerance) || equation.tolerance < 0) throw browserError(`${equation.id}.tolerance must be a non-negative number.`);
    const ast = parseExpression(equation.expression);
    const missing = [...expressionFields(ast)].filter((field) => !unique.has(field));
    if (missing.length) throw browserError(`${equation.id}.required_fields is missing expression fields: ${missing.join(', ')}.`);
    if (equation.applicability_field && !/^[A-Za-z_][A-Za-z0-9_]*$/.test(equation.applicability_field)) throw browserError(`${equation.id}.applies_when.field must be a valid identifier.`);
    if (!Array.isArray(equation.applicability_values)) throw browserError(`${equation.id}.applies_when.contains_any must be an array.`);
    equation.applicability_values = equation.applicability_values.map((value) => String(value).toLowerCase());
    return equation;
  }

  function validateEquationSet(rawEquations) {
    if (!Array.isArray(rawEquations)) throw browserError('Equation pack must be a JSON array.');
    if (rawEquations.length > MAX_EQUATIONS) throw browserError(`Analysis exceeds the ${MAX_EQUATIONS}-equation browser limit.`);
    const seen = new Set();
    return rawEquations.map((raw) => {
      const equation = validateEquation(raw);
      if (seen.has(equation.id)) throw browserError(`Duplicate equation id: ${equation.id}`);
      seen.add(equation.id);
      return equation;
    });
  }

  function coerceValues(row, fields) {
    const output = {};
    for (const field of fields) {
      const value = finiteNumber(row[field]);
      if (value === null) return null;
      output[field] = value;
    }
    return output;
  }

  function sourceManifest(records) {
    const counts = new Map();
    records.forEach((row) => {
      const key = JSON.stringify([row._source || 'supplied-records', row._source_sha256 || '', row._record_type || 'control_account']);
      counts.set(key, (counts.get(key) || 0) + 1);
    });
    return [...counts.entries()].map(([key, recordsCount]) => {
      const [name, digest, recordType] = JSON.parse(key);
      return { name, sha256: digest || null, record_type: recordType, records: recordsCount };
    }).sort((a, b) => `${a.name}|${a.record_type}`.localeCompare(`${b.name}|${b.record_type}`));
  }

  function analyzeRecords(records, equations, sources) {
    const findings = [];
    let executed = 0;
    records.forEach((raw) => {
      const row = normalizeRow(raw);
      const recordType = String(row._record_type || 'control_account');
      const recordId = String(row.record_id || row.task_code || row._row || 'unknown');
      equations.forEach((equation) => {
        if (equation.record_type !== recordType) return;
        if (equation.applicability_field) {
          const observed = String(row[equation.applicability_field] || '').toLowerCase();
          if (!equation.applicability_values.some((token) => observed.includes(token))) {
            findings.push({ ...equation, equation_id: equation.id, record_type: recordType, record_id: recordId, status: 'not_applicable', residual: 0, residual_state: 'finite', values: {} });
            return;
          }
        }
        const values = coerceValues(row, equation.required_fields);
        if (!values) {
          findings.push({ ...equation, equation_id: equation.id, record_type: recordType, record_id: recordId, status: 'not_applicable', residual: 0, residual_state: 'finite', values: {} });
          return;
        }
        executed += 1;
        let result;
        try {
          result = evaluateEquation(equation.expression, values, equation.tolerance);
        } catch (error) {
          result = { passed: false, residual: null, residual_state: 'non_finite' };
        }
        findings.push({
          equation_id: equation.id, title: equation.title, domain: equation.domain, severity: equation.severity,
          record_type: recordType, record_id: recordId, status: result.passed ? 'pass' : 'fail',
          residual: result.residual, residual_state: result.residual_state,
          expression: equation.expression, description: equation.description, remediation: equation.remediation, values,
        });
      });
    });
    findings.sort((a, b) => {
      const statusRank = (item) => item.status === 'fail' ? 0 : item.status === 'pass' ? 1 : 2;
      return statusRank(a) - statusRank(b)
        || (SEVERITY_RANK.get(a.severity) ?? 9) - (SEVERITY_RANK.get(b.severity) ?? 9)
        || ((b.residual === null ? Infinity : Math.abs(b.residual)) - (a.residual === null ? Infinity : Math.abs(a.residual)))
        || a.record_id.localeCompare(b.record_id)
        || a.equation_id.localeCompare(b.equation_id);
    });
    const failures = findings.filter((item) => item.status === 'fail');
    const blockers = failures.filter((item) => item.severity === 'blocker');
    const manifest = sourceManifest(records);
    const sourceNames = [...new Set((sources.length ? sources : manifest.map((item) => item.name)).map((value) => String(value).split(/[\\/]/).pop()))];
    const gateStatus = blockers.length ? 'blocked' : failures.length ? 'review' : 'ready';
    return {
      sources: sourceNames,
      source_manifest: manifest,
      records_analyzed: records.length,
      equations_considered: equations.length,
      equations_executed: executed,
      close_ready: blockers.length === 0,
      gate_status: gateStatus,
      summary: {
        blockers: blockers.length,
        failures: failures.length,
        passes: findings.filter((item) => item.status === 'pass').length,
        not_applicable: findings.filter((item) => item.status === 'not_applicable').length,
      },
      equations,
      findings,
      failures,
      blockers,
    };
  }

  function buildPortfolio(records) {
    let reportedEac = 0;
    let defensibleEac = 0;
    let reconstructedRiskAdjusted = 0;
    let submittedRiskAdjusted = 0;
    let submittedCount = 0;
    let configuredChangeAndRisk = 0;
    let accounts = 0;
    const contributions = [];
    records.forEach((raw) => {
      const row = normalizeRow(raw);
      if (String(row._record_type || 'control_account') !== 'control_account') return;
      const reported = finiteNumber(row.EAC);
      const actual = finiteNumber(row.AC);
      const remaining = finiteNumber(row.ETC);
      const pending = finiteNumber(row.pending_change_exposure) || 0;
      const risk = finiteNumber(row.risk_exposure) || 0;
      const submittedAdjusted = finiteNumber(row.risk_adjusted_EAC);
      if (reported === null && (actual === null || remaining === null)) return;
      accounts += 1;
      const governed = actual !== null && remaining !== null ? actual + remaining : reported;
      const reportedValue = reported === null ? governed : reported;
      const reconstructedAdjusted = governed + pending + risk;
      const deterministicGap = governed - reportedValue;
      const exposureAboveReported = reconstructedAdjusted - reportedValue;
      const reconciliationGap = submittedAdjusted === null ? null : reconstructedAdjusted - submittedAdjusted;
      if (submittedAdjusted !== null) { submittedCount += 1; submittedRiskAdjusted += submittedAdjusted; }
      contributions.push({
        record_id: String(row.record_id || row._row || 'unknown'),
        reported_eac: reportedValue, defensible_eac: governed,
        deterministic_forecast_gap: deterministicGap, pending_change: pending,
        configured_risk_uplift: risk, submitted_risk_adjusted_eac: submittedAdjusted,
        reconstructed_risk_adjusted_eac: reconstructedAdjusted,
        risk_adjusted_reconciliation_gap: reconciliationGap,
        exposure_above_reported_eac: exposureAboveReported,
        source: String(row._source || 'uploaded data').split(/[\\/]/).pop(),
      });
      reportedEac += reportedValue;
      defensibleEac += governed;
      configuredChangeAndRisk += pending + risk;
      reconstructedRiskAdjusted += reconstructedAdjusted;
    });
    contributions.sort((a, b) => Math.abs(b.deterministic_forecast_gap) - Math.abs(a.deterministic_forecast_gap)
      || Math.abs(b.exposure_above_reported_eac) - Math.abs(a.exposure_above_reported_eac)
      || a.record_id.localeCompare(b.record_id));
    const complete = accounts > 0 && submittedCount === accounts;
    return {
      portfolio: {
        accounts_reconstructed: accounts,
        reported_eac: reportedEac,
        defensible_eac: defensibleEac,
        deterministic_forecast_gap: defensibleEac - reportedEac,
        configured_change_and_risk: configuredChangeAndRisk,
        submitted_risk_adjusted_eac: complete ? submittedRiskAdjusted : null,
        reconstructed_risk_adjusted_eac: reconstructedRiskAdjusted,
        risk_adjusted_reconciliation_gap: complete ? reconstructedRiskAdjusted - submittedRiskAdjusted : null,
        risk_adjusted_summary_coverage: { submitted_accounts: submittedCount, reconstructed_accounts: accounts, complete },
        exposure_above_reported_eac: reconstructedRiskAdjusted - reportedEac,
      },
      contributions,
    };
  }

  function impactMetric(finding) {
    if (finding.domain === 'cost') return 'deterministic_forecast_gap';
    if (finding.domain === 'risk') return 'risk_adjusted_reconciliation';
    if (finding.domain === 'change') return 'baseline_governance';
    if (finding.domain === 'earned_value') return 'earned_value_assurance';
    if (finding.domain === 'schedule') return 'schedule_assurance';
    return 'close_gate';
  }

  function buildGraph(contributions, failures) {
    const nodes = [
      { id: 'metric:reported', kind: 'metric', label: 'Reported EAC', metric: 'reported_eac' },
      { id: 'metric:defensible', kind: 'metric', label: 'Defensible EAC', metric: 'defensible_eac' },
      { id: 'metric:deterministic_gap', kind: 'metric', label: 'Deterministic forecast gap', metric: 'deterministic_forecast_gap' },
      { id: 'metric:risk_adjusted', kind: 'metric', label: 'Risk-adjusted position', metric: 'reconstructed_risk_adjusted_eac' },
      { id: 'metric:risk_reconciliation', kind: 'metric', label: 'Risk-adjusted reconciliation', metric: 'risk_adjusted_reconciliation_gap' },
      { id: 'assurance:baseline', kind: 'assurance', label: 'Baseline governance', metric: 'baseline_governance' },
      { id: 'assurance:earned_value', kind: 'assurance', label: 'Earned-value assurance', metric: 'earned_value_assurance' },
      { id: 'assurance:schedule', kind: 'assurance', label: 'Schedule assurance', metric: 'schedule_assurance' },
      { id: 'decision:gate', kind: 'decision', label: 'Close gate', metric: 'close_gate' },
    ];
    const edges = [
      { source: 'metric:reported', target: 'metric:deterministic_gap', relation: 'compared_with' },
      { source: 'metric:defensible', target: 'metric:deterministic_gap', relation: 'compared_with' },
      { source: 'metric:defensible', target: 'metric:risk_adjusted', relation: 'adjusted_by_declared_exposure' },
      { source: 'metric:risk_adjusted', target: 'decision:gate', relation: 'informs' },
    ];
    const accountIds = new Set();
    contributions.slice(0, 40).forEach((item) => {
      const nodeId = `account:${item.record_id}`;
      accountIds.add(item.record_id);
      nodes.push({ id: nodeId, kind: 'account', label: item.record_id, deterministic_forecast_gap: item.deterministic_forecast_gap, exposure_above_reported_eac: item.exposure_above_reported_eac });
      edges.push(
        { source: nodeId, target: 'metric:reported', relation: 'reports' },
        { source: nodeId, target: 'metric:defensible', relation: 'reconstructs' },
        { source: nodeId, target: 'metric:risk_adjusted', relation: 'risk_adjusts' },
      );
    });
    const targets = {
      deterministic_forecast_gap: 'metric:deterministic_gap', risk_adjusted_reconciliation: 'metric:risk_reconciliation',
      baseline_governance: 'assurance:baseline', earned_value_assurance: 'assurance:earned_value',
      schedule_assurance: 'assurance:schedule', close_gate: 'decision:gate',
    };
    failures.slice(0, 60).forEach((finding, index) => {
      const findingId = `finding:${index}:${finding.equation_id}:${finding.record_id}`;
      nodes.push({ id: findingId, kind: 'finding', label: finding.title, severity: finding.severity, record_id: finding.record_id, equation_id: finding.equation_id, residual: finding.residual });
      const accountId = `account:${finding.record_id}`;
      if (!accountIds.has(finding.record_id)) {
        nodes.push({ id: accountId, kind: finding.record_type, label: finding.record_id });
        accountIds.add(finding.record_id);
      }
      const impact = impactMetric(finding);
      edges.push(
        { source: accountId, target: findingId, relation: 'violates' },
        { source: findingId, target: targets[impact], relation: 'affects' },
        { source: findingId, target: 'decision:gate', relation: 'gates' },
      );
    });
    return {
      nodes, edges,
      limits: {
        accounts_shown: Math.min(contributions.length, 40), accounts_total: contributions.length,
        findings_shown: Math.min(failures.length, 60), findings_total: failures.length,
        truncated: contributions.length > 40 || failures.length > 60,
      },
    };
  }

  function headline(portfolio, status) {
    const deterministic = portfolio.deterministic_forecast_gap;
    const exposure = portfolio.exposure_above_reported_eac;
    const reconciliation = portfolio.risk_adjusted_reconciliation_gap;
    if (status === 'ready' && Math.abs(deterministic) <= 1e-6 && (reconciliation === null || Math.abs(reconciliation) <= 1e-6)) {
      return 'The submitted close reconciles to the declared deterministic and risk-adjusted controls.';
    }
    const parts = [];
    if (Math.abs(deterministic) > 1e-6) parts.push(`Reported EAC is ${Math.abs(deterministic).toLocaleString('en-US', { maximumFractionDigits: 0 })} ${deterministic > 0 ? 'below' : 'above'} governed AC + ETC`);
    if (Math.abs(exposure) > 1e-6) parts.push(`the configured risk-adjusted position is ${Math.abs(exposure).toLocaleString('en-US', { maximumFractionDigits: 0 })} ${exposure > 0 ? 'above' : 'below'} reported EAC`);
    if (reconciliation !== null && Math.abs(reconciliation) > 1e-6) parts.push(`the submitted risk-adjusted summary is ${Math.abs(reconciliation).toLocaleString('en-US', { maximumFractionDigits: 0 })} ${reconciliation > 0 ? 'below' : 'above'} the reconstructed bridge`);
    const text = parts.join('; ');
    return `${text ? text[0].toUpperCase() + text.slice(1) : 'Close requires review'}.`;
  }

  function buildControlRoom(records, analysis, currency, equations) {
    const { portfolio, contributions } = buildPortfolio(records);
    const failures = analysis.failures;
    const domainCounts = new Map();
    const blockerCounts = new Map();
    failures.forEach((item) => domainCounts.set(item.domain, (domainCounts.get(item.domain) || 0) + 1));
    analysis.blockers.forEach((item) => blockerCounts.set(item.domain, (blockerCounts.get(item.domain) || 0) + 1));
    const domains = [...domainCounts.entries()].map(([domain, count]) => ({ domain, failures: count, blockers: blockerCounts.get(domain) || 0 }))
      .sort((a, b) => b.failures - a.failures || a.domain.localeCompare(b.domain));
    const penalty = failures.reduce((total, item) => total + ({ blocker: 18, major: 7, minor: 2, info: 1 }[item.severity] || 4), 0);
    const score = Math.max(0, Math.min(100, 100 - penalty));
    const gateStatus = analysis.gate_status;
    const summaryHeadline = headline(portfolio, gateStatus);
    return {
      schema_version: CONTROL_ROOM_SCHEMA,
      units: { currency: currency.toUpperCase(), duration: 'hours' },
      gate: {
        status: gateStatus,
        label: { blocked: 'CLOSE BLOCKED', review: 'REVIEW REQUIRED', ready: 'CLOSE READY' }[gateStatus],
        blockers: analysis.blockers.length,
        failures: failures.length,
        headline: summaryHeadline,
      },
      assurance: {
        score,
        label: score >= 85 ? 'high' : score >= 65 ? 'moderate' : 'low',
        method: 'deterministic severity penalty heuristic v1',
        calibrated_probability: false,
        note: 'This is a transparent triage indicator, not a statistical confidence interval.',
      },
      portfolio,
      surprise: { headline: summaryHeadline, contributions },
      domain_summary: domains,
      exceptions: failures.map((finding) => ({ ...finding, impact_metric: impactMetric(finding), materiality: finding.residual === null ? null : Math.abs(finding.residual) })),
      graph: buildGraph(contributions, failures),
      analysis: {
        sources: analysis.sources,
        source_manifest: analysis.source_manifest,
        records_analyzed: analysis.records_analyzed,
        equations_considered: analysis.equations_considered,
        equations_executed: analysis.equations_executed,
        close_ready: analysis.close_ready,
        gate_status: analysis.gate_status,
        summary: analysis.summary,
        equations,
        findings: analysis.findings,
      },
      catalogue: CATALOGUE.map((item) => ({ ...item })),
      demo: { name: 'Browser-compiled monthly close', description: 'Local files parsed, hashed and evaluated entirely in the browser.' },
      runtime: { engine: 'browser', data_left_device: false, persisted_locally: true },
    };
  }

  async function parseCostFile(file) {
    const digest = await sha256File(file);
    const rows = parseCsvText(await file.text());
    if (!rows.length) throw browserError(`${file.name} does not contain any data rows.`);
    return rows.map((row) => ({ ...normalizeRow(row), _record_type: 'control_account', _source: file.name, _source_sha256: digest }));
  }

  async function parseXerFile(file) {
    const digest = await sha256File(file);
    return parseXerText(await file.text()).map((row) => ({ ...row, _record_type: 'activity', _source: file.name, _source_sha256: digest }));
  }

  async function parseEquationFile(file) {
    let document;
    try { document = JSON.parse(await file.text()); } catch (error) { throw browserError(`${file.name} is not valid JSON.`); }
    return validateEquationSet(document);
  }

  async function analyzeForm(formData) {
    if (!(formData instanceof FormData)) throw browserError('Browser analysis requires form data.');
    const p6Files = formData.getAll('p6_xer').filter((item) => item instanceof File && item.size > 0);
    const costFiles = formData.getAll('cost_csv').filter((item) => item instanceof File && item.size > 0);
    const equationFiles = formData.getAll('equation_pack').filter((item) => item instanceof File && item.size > 0);
    if (!p6Files.length && !costFiles.length) throw browserError('Select at least one P6 XER or cost CSV export.');
    const currency = String(formData.get('currency') || 'USD').trim().toUpperCase();
    if (!/^[A-Z]{3}$/.test(currency)) throw browserError('Enter a three-letter currency code such as USD or CAD.');
    const records = [];
    for (const file of costFiles) records.push(...await parseCostFile(file));
    for (const file of p6Files) records.push(...await parseXerFile(file));
    const selectedIds = new Set(String(formData.get('catalogue_ids') || '').split(',').map((item) => item.trim()).filter(Boolean));
    const equations = CATALOGUE.filter((item) => selectedIds.has(item.id));
    for (const file of equationFiles) equations.push(...await parseEquationFile(file));
    let custom = [];
    try { custom = JSON.parse(String(formData.get('custom_equations') || '[]')); } catch (error) { throw browserError('Custom equations are not valid JSON.'); }
    equations.push(...validateEquationSet(custom));
    const validated = validateEquationSet(equations);
    const sources = [...p6Files, ...costFiles, ...equationFiles].map((file) => file.name);
    const analysis = analyzeRecords(records, validated, sources);
    const payload = buildControlRoom(records, analysis, currency, validated);
    setCurrentPayload(payload, true);
    global.dispatchEvent?.(new CustomEvent('eq-proof:analysis-complete', { detail: payload }));
    return payload;
  }

  function validatePayload(payload) {
    if (!payload || typeof payload !== 'object' || payload.schema_version !== CONTROL_ROOM_SCHEMA) throw browserError(`Analysis JSON must use ${CONTROL_ROOM_SCHEMA}.`);
    if (!payload.gate || !payload.analysis || !payload.portfolio) throw browserError('Analysis JSON is missing required Control Room sections.');
    return payload;
  }

  function setCurrentPayload(payload, persist = false) {
    currentPayload = validatePayload(payload);
    if (persist) {
      try {
        global.localStorage?.setItem(STORAGE_KEY, JSON.stringify({ saved_at: new Date().toISOString(), payload: currentPayload }));
      } catch (error) {
        console.warn('EQ-Proof could not persist the browser workspace:', error);
      }
    }
    return currentPayload;
  }

  function restoreWorkspace() {
    try {
      const raw = global.localStorage?.getItem(STORAGE_KEY);
      if (!raw) return null;
      const document = JSON.parse(raw);
      return setCurrentPayload(document.payload, false);
    } catch (error) {
      global.localStorage?.removeItem(STORAGE_KEY);
      return null;
    }
  }

  function clearWorkspace() {
    global.localStorage?.removeItem(STORAGE_KEY);
    currentPayload = null;
  }

  function download(content, type, filename) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.hidden = true;
    document.body.append(link);
    link.click();
    link.remove();
    global.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function applyBrowserCopy() {
    const mappings = [
      ['uploadDescription', 'Files are parsed, hashed and evaluated entirely in this browser. Nothing is uploaded.'],
      ['uploadButton', 'Analyze files'],
      ['heroUploadButton', 'Analyze files in browser'],
    ];
    mappings.forEach(([id, text]) => {
      const element = document.getElementById(id);
      if (element && element.textContent !== text) element.textContent = text;
    });
    const status = document.getElementById('apiStatus');
    if (status && (/Local analysis service ready|Public demo mode|Checking local analysis service/.test(status.textContent))) {
      status.textContent = 'Browser engine ready. Files stay on this device and are never uploaded.';
    }
    const addButton = document.getElementById('addEquationButton');
    if (addButton && ['Validate and add', 'Add to draft pack'].includes(addButton.textContent)) addButton.textContent = 'Validate in browser and add';
    const editorStatus = document.getElementById('editorStatus');
    if (editorStatus && /Safe expression mode|Public draft mode/.test(editorStatus.textContent)) {
      editorStatus.textContent = 'Browser engine validation: safe arithmetic, one comparison, declared fields and allow-listed functions.';
    } else if (editorStatus && editorStatus.textContent.includes('validated by the local engine')) {
      editorStatus.textContent = editorStatus.textContent.replace('validated by the local engine', 'validated by the browser engine');
    }
  }

  function installBrowserUi() {
    if (!global.document || document.getElementById('browserWorkbenchBar')) return;
    const workspace = document.getElementById('workspace');
    const heading = workspace?.querySelector('.workspace-heading');
    if (workspace && heading) {
      const bar = document.createElement('section');
      bar.className = 'browser-workbench-bar';
      bar.id = 'browserWorkbenchBar';
      bar.setAttribute('aria-label', 'Browser workspace controls');
      bar.innerHTML = `
        <div>
          <strong>Functional browser engine</strong>
          <span id="browserWorkspaceStatus">Parse CSV and P6 XER, execute equations, save the result locally and export evidence. No upload occurs.</span>
        </div>
        <div class="browser-workbench-actions">
          <button class="button button-secondary" id="openAnalysisButton" type="button">Open analysis JSON</button>
          <input id="openAnalysisInput" type="file" accept="application/json,.json" hidden>
          <button class="button button-secondary" id="exportAnalysisButton" type="button">Export analysis JSON</button>
          <button class="button button-quiet" id="resetWorkspaceButton" type="button">Reset to demo</button>
        </div>`;
      heading.insertAdjacentElement('afterend', bar);
      const openInput = document.getElementById('openAnalysisInput');
      document.getElementById('openAnalysisButton').addEventListener('click', () => openInput.click());
      openInput.addEventListener('change', async () => {
        const file = openInput.files?.[0];
        if (!file) return;
        const status = document.getElementById('browserWorkspaceStatus');
        try {
          const payload = validatePayload(JSON.parse(await file.text()));
          setCurrentPayload(payload, true);
          status.textContent = `${file.name} saved as the active local workspace. Reloading…`;
          global.location.reload();
        } catch (error) {
          status.textContent = error.message;
          openInput.value = '';
        }
      });
      document.getElementById('exportAnalysisButton').addEventListener('click', () => {
        const payload = currentPayload || restoreWorkspace();
        const status = document.getElementById('browserWorkspaceStatus');
        if (!payload) { status.textContent = 'Compile files or load an analysis before exporting.'; return; }
        download(`${JSON.stringify(payload, null, 2)}\n`, 'application/json', 'eq-proof-control-room.json');
        status.textContent = 'Exported the complete replayable Control Room analysis.';
      });
      document.getElementById('resetWorkspaceButton').addEventListener('click', () => {
        clearWorkspace();
        global.location.reload();
      });
    }

    const dialog = document.getElementById('analysisForm');
    const selected = document.getElementById('selectedFiles');
    if (dialog && selected && !document.getElementById('browserSampleInputs')) {
      const samples = document.createElement('div');
      samples.className = 'browser-sample-inputs';
      samples.id = 'browserSampleInputs';
      samples.innerHTML = '<strong>Download test inputs:</strong> <a href="./samples/cost.csv" download>cost CSV</a><a href="./samples/schedule.xer" download>P6 XER</a><a href="./samples/equations.json" download>equation pack</a>';
      selected.insertAdjacentElement('afterend', samples);
    }
    applyBrowserCopy();
    const observer = new MutationObserver(() => applyBrowserCopy());
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    global.addEventListener('eq-proof:analysis-complete', () => {
      const status = document.getElementById('browserWorkspaceStatus');
      if (status) status.textContent = 'Analysis complete and saved in this browser. Export the full JSON or continue inspecting the evidence.';
    });
  }

  const api = {
    schemaVersion: CONTROL_ROOM_SCHEMA,
    catalogue: CATALOGUE.map((item) => ({ ...item })),
    normalizeRow,
    parseCsvText,
    parseXerText,
    parseExpression,
    evaluateEquation,
    validateEquation,
    validateEquationSet,
    analyzeRecords,
    buildControlRoom,
    analyzeForm,
    setCurrentPayload,
    restoreWorkspace,
    clearWorkspace,
    getCurrentPayload: () => currentPayload,
    installBrowserUi,
  };

  global.EQProofBrowser = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (global.document) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', installBrowserUi, { once: true });
    else installBrowserUi();
  }
})(typeof window !== 'undefined' ? window : globalThis);
