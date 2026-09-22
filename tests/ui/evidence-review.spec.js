const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

async function loadEvidence(page) {
  await page.goto('/');
  await expect(page.locator('#browserWorkbenchBar')).toBeVisible();
  await expect(page.locator('#gateCard')).toHaveAttribute('aria-busy', 'false');
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.removeItem('eq-proof/browser-workspace@1');
    localStorage.removeItem('eq-proof/browser-persistence@1');
  });
});

test('finding and account drilldowns expose the actual EAC input values', async ({ page }) => {
  await loadEvidence(page);
  await page.locator('.contribution[data-record-id="MEP-200"]').click();
  await expect(page.locator('#inspectorBody')).toContainText('Actual cost (AC)');
  await expect(page.locator('#inspectorBody')).toContainText('91,000,000');
  await expect(page.locator('#inspectorBody')).toContainText('104,000,000');
  await expect(page.locator('#inspectorBody')).toContainText('does not calculate or certify a Monte Carlo percentile');
  await page.locator('#inspectorClose').click();
  await page.locator('#tab-exceptions').click();
  await page.locator('#exceptionRows tr').filter({ hasText: 'MEP-200' }).filter({ hasText: 'cost.eac_identity' }).click();
  await expect(page.locator('#inspectorBody')).toContainText('cost.eac_identity');
  await expect(page.locator('#inspectorBody .source-values')).toContainText('188,000,000');
  await expect(page.locator('#inspectorBody .source-values')).toContainText('91,000,000');
  await expect(page.locator('#inspectorBody .source-values')).toContainText('104,000,000');
});

test('control coverage exposes skipped checks without presenting them as passed', async ({ page }) => {
  await loadEvidence(page);
  await page.locator('#tab-equations').click();
  await expect(page.locator('#controlCoverageSummary')).toContainText('24 passed · 5 failed · 4 not applicable');
  await expect(page.locator('#controlCoverageDetails')).not.toHaveAttribute('open');
  await page.locator('#controlCoverageDetails summary').click();
  await page.getByLabel('Result status', { exact: true }).selectOption('not_applicable');
  await expect(page.locator('#controlResultSelect option')).toHaveCount(4);
  const result = await page.locator('#controlResultSelect option').filter({ hasText: 'CIV-100 · portfolio.board_authorization' }).getAttribute('value');
  await page.locator('#controlResultSelect').selectOption(result);
  await page.locator('#inspectControlResult').click();
  await expect(page.locator('#inspectorBody')).toContainText('Not applicable');
  await expect(page.locator('#inspectorBody')).toContainText('Not executed');
  await expect(page.locator('#inspectorBody')).toContainText('EAC, delegated_authorization');
  await expect(page.locator('#inspectorBody')).not.toContainText('Required action');
  await page.locator('#inspectorClose').click();
  await expect(page.locator('#inspectControlResult')).toBeFocused();
});

test('ready showcase exposes passing custom authorization independently of draft controls', async ({ page }) => {
  await loadEvidence(page);
  await page.locator('#showcaseCasesButton').click();
  await page.getByLabel('Example case').selectOption('ready');
  await page.locator('#runShowcaseCase').click();
  await expect(page.locator('#uploadDialog')).not.toBeVisible();
  await page.locator('#tab-equations').click();
  await expect(page.locator('#controlCoverageSummary')).toContainText('32 passed · 0 failed · 1 not applicable');
  await page.locator('#controlCoverageDetails summary').click();
  await page.getByLabel('Result status', { exact: true }).selectOption('pass');
  const result = await page.locator('#controlResultSelect option').filter({ hasText: 'MEP-200 · portfolio.board_authorization' }).getAttribute('value');
  await page.locator('#controlResultSelect').selectOption(result);
  await page.locator('#inspectControlResult').click();
  await expect(page.locator('#inspectorBody')).toContainText('Passed within scope');
  await expect(page.locator('#inspectorBody .source-values')).toContainText('195,000,000');
  await expect(page.locator('#inspectorBody .source-values')).toContainText('200,000,000');
  await expect(page.locator('#inspectorBody')).not.toContainText('Required action');
  await page.locator('#inspectorClose').click();
  await page.getByLabel('Result status', { exact: true }).selectOption('fail');
  await expect(page.locator('#inspectControlResult')).toBeDisabled();
  await expect(page.locator('#controlResultCount')).toContainText('0 of 33');
});

test('compact artifacts and missing AC/ETC keep missing evidence visible', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop');
  await loadEvidence(page);
  const compact = await page.evaluate(() => {
    const copy = structuredClone(state.data);
    delete copy.analysis.findings;
    return copy;
  });
  await page.locator('#openAnalysisInput').setInputFiles({ name: 'compact.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(compact)) });
  await page.locator('#tab-equations').click();
  await expect(page.locator('#controlCoverageSummary')).toContainText('not included in this artifact');
  await expect(page.locator('#controlCoverageDetails')).toBeHidden();
  await page.locator('#tab-overview').click();
  await page.locator('.contribution[data-record-id="MEP-200"]').click();
  await expect(page.locator('#inspectorBody')).toContainText('Not evidenced');
  await expect(page.locator('#inspectorBody')).not.toContainText('91,000,000');
  await page.locator('#inspectorClose').click();
  const partial = await page.evaluate(() => {
    const engine = window.EQProofBrowser;
    const records = [{ record_id: 'ONLY-EAC', EAC: 100, _record_type: 'control_account' }];
    const equations = engine.validateEquationSet(engine.catalogue);
    return engine.buildControlRoom(records, engine.analyzeRecords(records, equations, []), 'USD', equations);
  });
  await page.locator('#openAnalysisInput').setInputFiles({ name: 'partial.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(partial)) });
  await expect(page.locator('#riskAdjustedPosition')).toHaveText('Unavailable');
  await expect(page.locator('#contributionList')).toContainText('forecast gap not established');
  await expect(page.locator('#contributionList')).not.toContainText('forecast gap $0');
  await expect(page.locator('#reconstructionBridge')).toContainText('Unavailable');
  for (const metric of ['defensible_eac', 'deterministic_forecast_gap', 'risk_adjusted_position']) {
    await page.locator(`[data-inspect="${metric}"]`).click();
    await expect(page.locator('#inspectorBody .inspector-action strong')).toHaveText('Unavailable — AC and ETC not evidenced');
    await page.locator('#inspectorClose').click();
  }
  await page.locator('.contribution[data-record-id="ONLY-EAC"]').click();
  await expect(page.locator('#inspectorBody')).toContainText('Its detail reconstruction cannot be confirmed');
  await expect(page.locator('#inspectorBody dt').filter({ hasText: 'Deterministic forecast gap' }).locator('xpath=following-sibling::dd[1]')).toHaveText('Not evidenced');
});

test('expanded control review remains accessible and within the viewport', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === 'reduced-motion');
  await loadEvidence(page);
  await page.locator('#tab-equations').click();
  await page.locator('#controlCoverageDetails summary').click();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  const result = await new AxeBuilder({ page }).include('#controlCoverage').withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(result.violations.filter((item) => ['serious', 'critical'].includes(item.impact))).toEqual([]);
});
