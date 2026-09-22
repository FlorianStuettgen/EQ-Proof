const { test, expect } = require('@playwright/test');
const fs = require('node:fs/promises');
const crypto = require('node:crypto');
const AxeBuilder = require('@axe-core/playwright').default;
const bundle = require('../../src/eq_proof/web/showcase-cases.json');

async function openExamples(page) {
  await page.goto('/');
  await page.locator('#showcaseCasesButton').click();
  await expect(page.getByLabel('Example case')).toBeEnabled();
}

async function runExample(page, id) {
  await page.getByLabel('Example case').selectOption(id);
  await page.getByRole('button', { name: 'Run example', exact: true }).click();
  await expect(page.locator('#uploadDialog')).not.toBeVisible();
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.removeItem('eq-proof/browser-workspace@1');
    localStorage.removeItem('eq-proof/browser-persistence@1');
  });
});

for (const example of bundle.cases) {
  test(`${example.id} example compiles source files into its demonstrated result`, async ({ page }) => {
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await openExamples(page);
    await runExample(page, example.id);
    await expect(page.locator('#workspaceTitle')).toContainText(`${example.title} · synthetic`);
    await expect(page.locator('#gateLabel')).toHaveText(example.control_room.gate.label);
    await expect(page.locator('.preview-gate strong')).toHaveText(example.control_room.gate.label);
    const state = await page.evaluate(() => ({
      payload: window.EQProofBrowser.getCurrentPayload(),
      stored: localStorage.getItem('eq-proof/browser-workspace@1'),
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    }));
    expect(state.payload.gate).toEqual(example.control_room.gate);
    expect(state.payload.portfolio).toEqual(example.control_room.portfolio);
    expect(state.payload.analysis.source_manifest).toEqual(example.control_room.analysis.source_manifest);
    expect(state.payload.analysis.equations_executed).toBe(example.expected.equations_executed);
    expect(state.payload.analysis.summary.not_applicable).toBe(example.expected.not_applicable);
    expect(state.payload.runtime.persisted_locally).toBe(false);
    expect(state.payload.demo.synthetic).toBe(true);
    expect(state.stored).toBeNull();
    expect(state.overflow).toBeLessThanOrEqual(1);
    expect(errors).toEqual([]);

    await page.locator('#workspaceTourButton').click();
    await page.locator('#tourNext').click();
    if (example.id !== 'blocked') {
      await expect(page.locator('#tourBody')).toContainText('The forecast reconciles');
      await expect(page.locator('#tourBody')).not.toContainText('direct deterministic contradiction');
    }
    await page.locator('#tourNext').click();
    await page.locator('#tourNext').click();
    await page.locator('#tourNext').click();
    await expect(page.locator('#exceptionFilterCount')).toContainText(`${example.expected.blockers || example.expected.failures} of ${example.expected.failures}`);
    await page.locator('#tourNext').click();
    await expect(page.locator('#workspaceTourButton')).toBeFocused();
  });
}

test('examples ignore draft inputs and export verified sources and current results', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop');
  await openExamples(page);
  await page.evaluate(() => {
    state.customEquations = [{ id: 'custom.unrelated', title: 'Unrelated draft', domain: 'custom', expression: 'EAC <= 0', severity: 'blocker', required_fields: ['EAC'] }];
    state.selectedCatalogueIds = new Set();
  });
  await page.locator('#costInput').setInputFiles({ name: 'unrelated.csv', mimeType: 'text/csv', buffer: Buffer.from('EAC,AC,ETC\n1,5,5\n') });
  const example = bundle.cases.find((item) => item.id === 'ready');
  await page.getByLabel('Example case').selectOption('ready');
  for (const source of example.source_files) {
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: `Download ${source.name}`, exact: true }).click(),
    ]);
    const content = await fs.readFile(await download.path());
    expect(download.suggestedFilename()).toBe(source.name);
    expect(crypto.createHash('sha256').update(content).digest('hex')).toBe(source.sha256);
  }
  await runExample(page, 'ready');
  const [analysisDownload] = await Promise.all([page.waitForEvent('download'), page.locator('#exportAnalysisButton').click()]);
  const analysis = JSON.parse(await fs.readFile(await analysisDownload.path(), 'utf8'));
  expect(analysis.analysis.equations).toHaveLength(example.control_room.analysis.equations.length);
  expect(analysis.analysis.equations.some((item) => item.id === 'custom.unrelated')).toBe(false);
  expect(analysis.analysis.source_manifest).toEqual(example.control_room.analysis.source_manifest);
  const [briefDownload] = await Promise.all([page.waitForEvent('download'), page.locator('#downloadBriefButton').click()]);
  const brief = await fs.readFile(await briefDownload.path(), 'utf8');
  expect(brief).toContain('CLOSE READY');
  expect(brief).toContain('Detail-reconstructed EAC (AC + ETC)');
  expect(brief).toContain('Control severity index:');
  expect(brief).toContain(`Synthetic showcase example: **${example.title}**`);
  expect(brief).toContain('Not-applicable checks: **1**');
  expect(brief).toContain('Review applicability, source completeness and approval boundary');
  expect(brief).not.toContain('No action required');
  expect(brief).not.toContain('Defensible EAC');
  await page.locator('[data-inspect="defensible_eac"]').click();
  await expect(page.locator('#inspectorTitle')).toHaveText('Detail-reconstructed EAC');
  await page.locator('#inspectorClose').click();
  await page.locator('#openAnalysisInput').setInputFiles(require.resolve('../../evidence/close-walkthrough/ready/control-room.json'));
  await expect(page.locator('#workspaceTitle')).toContainText('Opened session-only');
  const [reopenedBrief] = await Promise.all([page.waitForEvent('download'), page.locator('#downloadBriefButton').click()]);
  expect(await fs.readFile(await reopenedBrief.path(), 'utf8')).toContain(`Synthetic showcase example: **${example.title}**`);
});

test('showcase chooser has no material accessibility findings and restores focus', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop');
  await openExamples(page);
  const results = await new AxeBuilder({ page }).include('#uploadDialog')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
  expect(results.violations.filter((item) => ['serious', 'critical'].includes(item.impact))).toEqual([]);
  await page.keyboard.press('Escape');
  await expect(page.locator('#showcaseCasesButton')).toBeFocused();
});

test('unavailable examples leave manual file analysis usable', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop');
  await page.route('**/showcase-cases.json', (route) => route.fulfill({ status: 503, body: 'Unavailable' }));
  await page.goto('/');
  await page.locator('#showcaseCasesButton').click();
  await expect(page.locator('#showcaseCaseStatus')).toContainText('You can still analyze your own files below');
  await expect(page.locator('#runShowcaseCase')).toBeDisabled();
  await expect(page.locator('#costInput')).toBeEnabled();
  await page.locator('#costInput').setInputFiles({ name: 'simple.csv', mimeType: 'text/csv', buffer: Buffer.from('EAC,AC,ETC\n10,5,5\n') });
  await page.locator('#compileButton').click();
  await expect(page.locator('#uploadDialog')).not.toBeVisible();
  await expect(page.locator('#reportedEac')).toContainText('10');
});

test('analysis cannot overlap and restores storage behavior after success and failure', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop');
  await openExamples(page);
  await page.locator('#costInput').setInputFiles({ name: 'simple.csv', mimeType: 'text/csv', buffer: Buffer.from('EAC,AC,ETC\n10,5,5\n') });
  await page.evaluate(() => {
    window.originalAnalysis = EQProofBrowser.analyzeForm;
    window.originalStorageWrite = Storage.prototype.setItem;
    window.analysisCalls = 0;
    EQProofBrowser.analyzeForm = async (form) => {
      window.analysisCalls += 1;
      await new Promise((resolve) => { window.releaseAnalysis = resolve; });
      return window.originalAnalysis(form);
    };
  });
  await page.locator('#compileButton').click();
  await expect(page.locator('#compileButton')).toBeDisabled();
  await expect(page.locator('#runShowcaseCase')).toBeDisabled();
  await page.locator('#runShowcaseCase').dispatchEvent('click');
  await expect(page.locator('#showcaseCaseStatus')).toContainText('Wait for the current analysis');
  expect(await page.evaluate(() => window.analysisCalls)).toBe(1);
  await page.evaluate(() => window.releaseAnalysis());
  await expect(page.locator('#uploadDialog')).not.toBeVisible();
  expect(await page.evaluate(() => Storage.prototype.setItem === window.originalStorageWrite)).toBe(true);
  expect(await page.evaluate(() => localStorage.getItem('eq-proof/browser-workspace@1'))).toBeNull();

  await page.locator('#showcaseCasesButton').click();
  await page.evaluate(() => { EQProofBrowser.analyzeForm = async () => { throw new Error('Test input failure'); }; });
  await page.locator('#runShowcaseCase').click();
  await expect(page.locator('#showcaseCaseStatus')).toHaveText('Test input failure');
  await expect(page.locator('#runShowcaseCase')).toBeEnabled();
  await expect(page.locator('#compileButton')).toBeEnabled();
  expect(await page.evaluate(() => Storage.prototype.setItem === window.originalStorageWrite)).toBe(true);
  await page.locator('#dialogClose').click();
  await page.locator('#rememberWorkspaceInput').check();
  await page.evaluate(() => { EQProofBrowser.analyzeForm = window.originalAnalysis; });
  await page.locator('#showcaseCasesButton').click();
  await runExample(page, 'ready');
  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('eq-proof/browser-workspace@1')).payload);
  expect(saved.gate.status).toBe('ready');
  expect(saved.demo.showcase_case).toBe('ready');
  expect(saved.runtime.persisted_locally).toBe(true);
});

test('tour does not claim reconciliation when AC and ETC are absent', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop');
  await openExamples(page);
  await page.locator('#costInput').setInputFiles({ name: 'partial.csv', mimeType: 'text/csv', buffer: Buffer.from('control_account_id,EAC\nONLY-EAC,100\n') });
  await page.locator('#compileButton').click();
  await expect(page.locator('#uploadDialog')).not.toBeVisible();
  await page.locator('#workspaceTourButton').click();
  await page.locator('#tourNext').click();
  await expect(page.locator('#tourBody')).toContainText('do not establish complete AC + ETC coverage');
  await expect(page.locator('#tourBody')).not.toContainText('The forecast reconciles');
  await page.locator('#tourNext').click();
  await expect(page.locator('#tourBody')).toContainText('Complete AC + ETC coverage has not been established');
  await page.locator('#tourClose').click();
  await expect(page.locator('#assuranceNote')).toContainText('No controls executed');
  const [brief] = await Promise.all([page.waitForEvent('download'), page.locator('#downloadBriefButton').click()]);
  const content = await fs.readFile(await brief.path(), 'utf8');
  expect(content).toContain('Forecast reconciliation is unavailable');
  expect(content).toContain('Detail-reconstructed EAC (AC + ETC) | Unavailable');
});
