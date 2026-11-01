// The built site in Chrome: the viewer plays a gesture and switches Stage, search finds a page, the diagrams draw, the
// Docs version switcher opens the same page in another version, and nothing breaks the CSP or asks another host than
// api.github.com (the header's stars and forks).
import { existsSync } from 'node:fs';
import { expect, test } from '@playwright/test';

let violations, errors, requests;
test.beforeEach(async ({ page }) => {
  [violations, errors, requests] = [[], [], []];
  await page.exposeFunction('cspViolation', (v) => violations.push(v));
  await page.addInitScript(() =>
    document.addEventListener('securitypolicyviolation', (e) => window.cspViolation(`${e.effectiveDirective} ${e.blockedURI}`)),
  );
  page.on('pageerror', (e) => errors.push(String(e)));
  // GitHub's answer for the header's stars and forks (a rate limit, say) is not ours; its message has no URL, its location has
  const github = (m) => m.location().url.startsWith('https://api.github.com/');
  page.on('console', (m) => m.type() === 'error' && !github(m) && errors.push(m.text()));
  page.on('request', (r) => requests.push(r.url()));
});
test.afterEach(async ({ baseURL }) => {
  const origin = new URL(baseURL).origin;
  expect(violations).toEqual([]);
  expect(errors).toEqual([]);
  // the pictures are the live site's (docs/adr/0009), which a local build shows too
  const ours = [origin, `blob:${origin}`, 'data:', 'https://api.github.com/', 'https://yellowpine.com/noggin/images/'];
  const elsewhere = requests.filter((u) => !ours.some((o) => u.startsWith(o)));
  expect(elsewhere).toEqual([]);
});

test('the viewer plays a gesture, back to the hero, and switches Stage', async ({ page }) => {
  const glbs = existsSync(new URL('dist/viewer/stage3.glb', import.meta.url));
  test.skip(!glbs && !process.env.CI, 'no GLBs in dist/viewer (make web, then make site)'); // CI always has them
  await page.goto('viewer/');
  const button = (name) => page.getByRole('button', { name, exact: true });
  await expect(button('Stage 3')).toHaveAttribute('aria-pressed', 'true');
  await expect(button('hero')).toHaveAttribute('aria-pressed', 'true', { timeout: 30_000 }); // Stage 3 loaded
  // see-through, so the Mech sits on the page's own background in either theme
  expect(await page.evaluate(() => document.querySelector('canvas').getContext('webgl2').getContextAttributes().alpha)).toBe(true);
  // every button pressed from here on, in order: a slow software-drawn frame can play the whole wink at once
  await page.evaluate(() => {
    window.pressed = [];
    new MutationObserver((ms) => ms.forEach((m) => m.target.ariaPressed === 'true' && window.pressed.push(m.target.textContent)))
      .observe(document.querySelector('.noggin-viewer'), { subtree: true, attributeFilter: ['aria-pressed'] });
  });
  await button('wink').click();
  await page.waitForFunction(() => window.pressed.join() === 'wink,hero', null, { timeout: 30_000 });
  await button('Stage 1').click();
  await expect(button('wink')).toBeEnabled({ timeout: 30_000 });
  await expect(button('hero')).toHaveCount(0); // Stage 1 has no neck
});

test('search finds the servo pages', async ({ page }) => {
  await page.goto('./');
  await page.getByRole('button', { name: 'Search' }).first().click();
  await page.getByRole('dialog', { name: 'Search' }).getByRole('textbox').fill('servo');
  await expect(page.locator('.pagefind-ui__result').first()).toBeVisible({ timeout: 15_000 });
});

test('every diagram draws', async ({ page }) => {
  await page.goto('docs/how-it-works/');
  const diagrams = page.locator('pre.mermaid');
  await expect(diagrams.first().locator('svg')).toBeVisible({ timeout: 15_000 });
  for (const d of await diagrams.all()) await expect(d.locator('svg')).toBeVisible();
});

test('the Docs version switcher opens the same page in the chosen version', async ({ page }) => {
  // a deploy's versions.json with one Release's docs (scripts/docs_versions.py), and its page (docs/adr/0014)
  await page.route('**/noggin/versions.json', (r) =>
    r.fulfill({ json: [{ version: 'latest', title: 'latest', aliases: [] }, { version: 'v0.1', title: 'v0.1.2', aliases: [] }] }),
  );
  await page.route('**/noggin/v0.1/glossary/', (r) => r.fulfill({ contentType: 'text/html', body: '<title>v0.1</title>' }));
  await page.goto('glossary/');
  const select = page.getByRole('combobox', { name: 'Docs version' }).first();
  await expect(select).toHaveValue('latest');
  await select.selectOption('v0.1.2');
  await expect(page).toHaveURL(/\/noggin\/v0\.1\/glossary\/$/);
});
