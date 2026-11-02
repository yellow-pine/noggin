// The built site in Chrome (#513): the diagrams draw, search finds a page, the Docs version switcher opens the same
// page in another version, the wordmark's eye looks at the pointer (#603), and nothing breaks the CSP, logs an error or
// asks another host than api.github.com (the header's stars and forks). The viewer loads the next Mech (#649), the only
// one the site serves (docs/adr/0019), and plays its gestures (#664).
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
  const ours = [origin, `blob:${origin}`, 'data:', 'https://api.github.com/'];
  const elsewhere = requests.filter((u) => !ours.some((o) => u.startsWith(o)));
  expect(elsewhere).toEqual([]);
});

test('the viewer loads the next Mech, plays it, explodes it, see-through, and the wheel zooms it', async ({ page }) => {
  // CI always has the GLBs; a local build has them once just web next ran before just site
  test.skip(!existsSync(new URL('dist/viewer/next-mech-back.glb', import.meta.url)) && !process.env.CI, 'no GLB: just web');
  await page.goto('viewer/');
  const viewer = page.locator('.noggin-viewer'); // one, a button per head variant (#664, #686)
  await expect(viewer).toHaveAttribute('aria-busy', 'false', { timeout: 45_000 });
  await expect(viewer.getByRole('button', { name: 'Tour' })).toHaveAttribute('aria-pressed', 'true'); // the clips (#669)
  await viewer.getByRole('navigation', { name: 'Head' }).getByRole('button').nth(1).click(); // its labels follow the ranking
  await expect(page).toHaveURL(/\?stage=2$/);
  await expect(viewer).toHaveAttribute('aria-busy', 'false', { timeout: 45_000 });
  await viewer.getByRole('button', { name: 'Explode' }).click();
  await expect(page).toHaveURL(/\?stage=2&explode=1$/);
  // see-through, so the Mech sits on the page's own background in either theme
  expect(await page.evaluate(() => document.querySelector('canvas').getContext('webgl2').getContextAttributes().alpha)).toBe(true);
  await page.evaluate(() => addEventListener('wheel', (e) => (window.zoomed = e.defaultPrevented), { once: true }));
  await viewer.locator('canvas').hover();
  await page.mouse.wheel(0, 200);
  await expect.poll(() => page.evaluate(() => window.zoomed)).toBe(true); // OrbitControls takes it from the page
});

// the wordmark's o is the Mech's eye (#603): its pupil looks at the pointer, unless the reader asks for less motion
test("the wordmark's eye looks at the pointer, and holds still for reduced motion", async ({ page }) => {
  const pupil = page.locator('header .noggin-pupil');
  const centre = async () => (await pupil.boundingBox()).x;
  for (const reducedMotion of ['no-preference', 'reduce']) {
    await page.emulateMedia({ reducedMotion });
    await page.goto('docs/build/parts/');
    await page.mouse.move(0, 0);
    const before = await centre();
    await page.mouse.move(1200, 600);
    if (reducedMotion === 'reduce') {
      await page.waitForTimeout(300);
      expect(await centre()).toBe(before);
    } else await expect.poll(centre).toBeGreaterThan(before);
  }
});

// Expressive Code draws a code block in a <figure>; the centred picture figures leave it left-aligned (#719)
test('a code block reads left-aligned', async ({ page }) => {
  await page.goto('docs/build/flashing/');
  await expect(page.locator('.expressive-code .ec-line').first()).toHaveCSS('text-align', 'start');
});

test('the diagrams draw, search finds a page, the version switcher switches', async ({ page }) => {
  // a deploy's versions.json with one Release's docs (scripts/docs_versions.py), and its page (docs/adr/0014)
  await page.route('**/noggin/versions.json', (r) =>
    r.fulfill({ json: [{ version: 'latest', title: 'latest', aliases: [] }, { version: 'v0.1', title: 'v0.1.2', aliases: [] }] }),
  );
  await page.route('**/noggin/v0.1/docs/how-it-works/', (r) => r.fulfill({ contentType: 'text/html', body: '<title>v0.1</title>' }));
  // drawn in the page by the site's Mermaid, under its CSP
  await page.goto('docs/how-it-works/');
  const diagrams = page.locator('pre.mermaid');
  await expect(diagrams.first().locator('svg')).toBeVisible({ timeout: 15_000 });
  for (const d of await diagrams.all()) await expect(d.locator('svg')).toBeVisible();
  await page.getByRole('button', { name: 'Search' }).first().click();
  await page.getByRole('dialog', { name: 'Search' }).getByRole('textbox').fill('servo');
  await expect(page.locator('.pagefind-ui__result').first()).toBeVisible({ timeout: 15_000 });
  await page.keyboard.press('Escape');
  const select = page.getByRole('combobox', { name: 'Docs version' }).first();
  await expect(select).toHaveValue('latest');
  await select.selectOption('v0.1.2');
  await expect(page).toHaveURL(/\/noggin\/v0\.1\/docs\/how-it-works\/$/);
});
