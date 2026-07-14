const { test, expect } = require('@playwright/test');

async function loadWorkbench(page) {
  await page.goto('/');
  await expect(page.locator('#browserWorkbenchBar')).toBeVisible();
  await expect(page.locator('#gateCard')).toHaveAttribute('aria-busy', 'false');
}

test('hosted dialog accepts files and states the local-only boundary', async ({ page }) => {
  await loadWorkbench(page);
  await expect(page.locator('#uploadButton')).toHaveText('Analyze files');
  await page.locator('#uploadButton').click();
  await expect(page.locator('#uploadDialog')).toBeVisible();
  await expect(page.locator('#p6Input')).toBeEnabled();
  await expect(page.locator('#costInput')).toBeEnabled();
  await expect(page.locator('#compileButton')).toBeEnabled();
  await expect(page.locator('#apiStatus')).toContainText('Browser engine ready');
  await expect(page.locator('#uploadDescription')).toContainText('Nothing is uploaded');
  await expect(page.locator('#browserSampleInputs a')).toHaveCount(3);
});

test('compiles a cost file and creates replayable evidence', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop');
  await loadWorkbench(page);
  await page.locator('#uploadButton').click();
  await page.locator('#costInput').setInputFiles({
    name: 'browser-cost.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from([
      'control_account_id,AC,ETC,EAC,pending_change_exposure,risk_exposure,risk_adjusted_EAC',
      'TEST-1,10,5,12,2,1,15',
    ].join('\n')),
  });
  await page.locator('#compileButton').click();

  await expect(page.locator('#uploadDialog')).not.toBeVisible();
  await expect(page.locator('#workspaceTitle')).toHaveText('Browser-compiled monthly close');
  await expect(page.locator('#reportedEac')).toContainText('12');
  await expect(page.locator('#defensibleEac')).toContainText('15');
  await expect(page.locator('#deterministicGap')).toContainText('3');
  await expect(page.locator('#riskAdjustedPosition')).toContainText('18');
  await expect(page.locator('#sourceStrip')).toContainText('browser-cost.csv');

  const manifest = await page.evaluate(() => window.EQProofBrowser.getCurrentPayload().analysis.source_manifest);
  expect(manifest).toHaveLength(1);
  expect(manifest[0].sha256).toMatch(/^[a-f0-9]{64}$/);
  expect(manifest[0].records).toBe(1);

  const [analysis] = await Promise.all([
    page.waitForEvent('download'),
    page.locator('#exportAnalysisButton').click(),
  ]);
  expect(analysis.suggestedFilename()).toBe('eq-proof-control-room.json');

  await page.reload();
  await expect(page.locator('#browserWorkbenchBar')).toBeVisible();
  await expect(page.locator('#workspaceTitle')).toHaveText('Restored browser workspace');
  await expect(page.locator('#reportedEac')).toContainText('12');
});

test('browser equation authoring validates and adds safe controls', async ({ page }) => {
  await loadWorkbench(page);
  await page.locator('#tab-equations').click();
  await expect(page.locator('#addEquationButton')).toHaveText('Validate in browser and add');

  await page.locator('#customExpression').fill('EAC <= delegated_authorization <= ceiling');
  await page.locator('#addEquationButton').click();
  await expect(page.locator('#editorStatus')).toContainText('exactly one comparison');

  await page.locator('#customExpression').fill('EAC <= delegated_authorization');
  await page.locator('#customFields').fill('EAC, delegated_authorization');
  await page.locator('#addEquationButton').click();
  await expect(page.locator('#editorStatus')).toContainText('validated by the browser engine');
  await expect(page.locator('.custom-chip')).toHaveCount(1);
});
