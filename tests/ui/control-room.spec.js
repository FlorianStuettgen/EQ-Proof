const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

async function loadControlRoom(page) {
  const consoleErrors = [];
  const pageErrors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => pageErrors.push(error.message));

  await page.goto('/');
  await expect(page.locator('#gateCard')).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('#gateLabel')).toHaveText('CLOSE BLOCKED');
  await expect(page.locator('#reportedEac')).toContainText('407');
  await expect(page.locator('#browserWorkbenchBar')).toBeVisible();
  await page.waitForFunction(() => document.querySelector('.tab')?.dataset.keyboardReady === 'true');
  return { consoleErrors, pageErrors };
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.removeItem('eq-proof/browser-workspace@1');
    localStorage.removeItem('eq-proof/browser-persistence@1');
  });
});

test('loads the decision without runtime or layout failures', async ({ page }) => {
  const errors = await loadControlRoom(page);
  await expect(page.locator('#defensibleEac')).toContainText('418');
  await expect(page.locator('[data-inspect="defensible_eac"]').locator('..')).toContainText('Detail-reconstructed EAC');
  await expect(page.locator('#assuranceRing small')).toHaveText('severity index');
  await expect(page.locator('#assuranceNote')).toContainText('not a probability');
  await expect(page.locator('#deterministicGap')).toContainText('11');
  await expect(page.locator('#riskAdjustedPosition')).toContainText('483');
  const overflow = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1);
  expect(errors.pageErrors).toEqual([]);
  expect(errors.consoleErrors).toEqual([]);
});

test('tabs expose state and support roving keyboard navigation', async ({ page }) => {
  await loadControlRoom(page);
  const overview = page.locator('#tab-overview');
  const graph = page.locator('#tab-graph');
  await overview.focus();
  await page.keyboard.press('ArrowRight');
  await expect(graph).toBeFocused();
  await expect(graph).toHaveAttribute('aria-selected', 'true');
  await expect(overview).toHaveAttribute('aria-selected', 'false');
  await expect(page.locator('#panel-graph')).toBeVisible();
  await expect(page.locator('#panel-overview')).toBeHidden();
  await page.keyboard.press('End');
  await expect(page.locator('#tab-equations')).toBeFocused();
  await expect(page.locator('#panel-equations')).toBeVisible();
});

test('inspector restores focus after closing', async ({ page }) => {
  await loadControlRoom(page);
  const trigger = page.locator('[data-inspect="reported_eac"]');
  await trigger.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#inspector')).toHaveClass(/open/);
  await expect(page.locator('#inspector')).not.toHaveAttribute('inert', '');
  await expect(page.locator('#inspectorClose')).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.locator('#inspector')).not.toHaveClass(/open/);
  await expect(page.locator('#inspector')).toHaveAttribute('inert', '');
  await expect(trigger).toBeFocused();
});

test('guided review completes and returns focus', async ({ page }) => {
  await loadControlRoom(page);
  const launcher = page.locator('#guidedDemoButton');
  await launcher.click();
  await expect(page.locator('#tourCard')).toBeVisible();
  await expect(page.locator('#tourClose')).toBeFocused();
  for (let step = 0; step < 5; step += 1) await page.locator('#tourNext').click();
  await expect(page.locator('#tourCard')).toBeHidden();
  await expect(launcher).toBeFocused();
});

test('cards and action rows are keyboard operable', async ({ page }) => {
  await loadControlRoom(page);
  const contribution = page.locator('.contribution').first();
  await expect(contribution).toHaveAttribute('role', 'button');
  await contribution.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#inspector')).toHaveClass(/open/);
  await page.keyboard.press('Escape');
  await page.locator('#tab-exceptions').click();
  const row = page.locator('#exceptionRows tr:not(.empty-row)').first();
  await expect(row).toHaveAttribute('tabindex', '0');
  await row.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#inspector')).toHaveClass(/open/);
});

test('empty exception filters explain the result', async ({ page }) => {
  await loadControlRoom(page);
  await page.locator('#tab-exceptions').click();
  await page.locator('#exceptionSearch').fill('no-such-record-or-equation');
  await expect(page.locator('#exceptionRows .empty-row')).toHaveCount(1);
  await expect(page.locator('#exceptionRows .empty-row')).toContainText('No exceptions match');
  await expect(page.locator('#exceptionFilterCount')).toContainText('0 of');
});

test('executive brief and exception register download', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop');
  await loadControlRoom(page);
  const [brief] = await Promise.all([
    page.waitForEvent('download'),
    page.locator('#downloadBriefButton').click(),
  ]);
  expect(brief.suggestedFilename()).toMatch(/^eq-proof-.*-executive-brief\.md$/);
  await page.locator('#tab-exceptions').click();
  const [csv] = await Promise.all([
    page.waitForEvent('download'),
    page.locator('#downloadExceptions').click(),
  ]);
  expect(csv.suggestedFilename()).toBe('eq-proof-exceptions.csv');
});

test('desktop has no serious or critical accessibility findings', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop');
  await loadControlRoom(page);
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
    .analyze();
  const material = results.violations.filter((item) => ['serious', 'critical'].includes(item.impact));
  expect(material, JSON.stringify(material, null, 2)).toEqual([]);
});

test('reduced-motion mode removes smooth scrolling and animation', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'reduced-motion');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await loadControlRoom(page);
  const motion = await page.evaluate(() => ({
    reduced: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior,
    animationName: getComputedStyle(document.querySelector('.preview-window')).animationName,
  }));
  expect(motion.reduced).toBe(true);
  expect(motion.scrollBehavior).toBe('auto');
  expect(motion.animationName).toBe('none');
});
