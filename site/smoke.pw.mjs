// The built site in Chrome: the viewer loads a Stage, search finds a page, the Docs version switcher opens the same
// page in another version, and nothing breaks the CSP, logs an error or asks another host than api.github.com (the
// header's stars and forks). One test, as short as CI's software WebGL allows (#513): the viewer's logic is Vitest's
// (src/viewer/link.test.mjs), the diagrams site.test.mjs's.
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

test('the viewer loads Stage 1, search finds the servo pages, and the Docs version switcher opens another version', async ({ page }) => {
  const glbs = existsSync(new URL('dist/viewer/stage1.glb', import.meta.url));
  test.skip(!glbs && !process.env.CI, 'no GLBs in dist/viewer (make web, then make site)'); // CI always has them
  // the smallest Stage; what the viewer then plays, links and takes apart is link.test.mjs's (#513)
  await page.goto('viewer/?stage=1');
  await expect(page.getByRole('button', { name: 'Tour', exact: true })).toHaveAttribute('aria-pressed', 'true', { timeout: 45_000 });
  // see-through, so the Mech sits on the page's own background in either theme
  expect(await page.evaluate(() => document.querySelector('canvas').getContext('webgl2').getContextAttributes().alpha)).toBe(true);
  // a deploy's versions.json with one Release's docs (scripts/docs_versions.py), and its page (docs/adr/0014)
  await page.route('**/noggin/versions.json', (r) =>
    r.fulfill({ json: [{ version: 'latest', title: 'latest', aliases: [] }, { version: 'v0.1', title: 'v0.1.2', aliases: [] }] }),
  );
  await page.route('**/noggin/v0.1/glossary/', (r) => r.fulfill({ contentType: 'text/html', body: '<title>v0.1</title>' }));
  await page.goto('glossary/'); // a page with no viewer drawing beside the search
  await page.getByRole('button', { name: 'Search' }).first().click();
  await page.getByRole('dialog', { name: 'Search' }).getByRole('textbox').fill('servo');
  await expect(page.locator('.pagefind-ui__result').first()).toBeVisible({ timeout: 15_000 });
  await page.keyboard.press('Escape');
  const select = page.getByRole('combobox', { name: 'Docs version' }).first();
  await expect(select).toHaveValue('latest');
  await select.selectOption('v0.1.2');
  await expect(page).toHaveURL(/\/noggin\/v0\.1\/glossary\/$/);
});
