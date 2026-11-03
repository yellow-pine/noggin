// The built site in Chrome (#513): the diagrams draw, search finds a page, the header names the newest release and an
// old Docs version's URL lands on the docs (docs/adr/0021), the wordmark's eye looks at the pointer (#603), and nothing
// breaks the CSP, logs an error or asks another host than api.github.com (the header's release, stars and forks). The viewer loads the next Mech (#649), the only
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
  test.skip(!existsSync(new URL('dist/viewer/next-stage1.glb', import.meta.url)) && !process.env.CI, 'no GLB: just web');
  await page.goto('viewer/');
  const viewer = page.locator('.noggin-viewer'); // one, its Stage and Skeleton switches (#720, #805)
  await expect(viewer).toHaveAttribute('aria-busy', 'false', { timeout: 45_000 });
  await expect(viewer.getByRole('button', { name: 'Tour' })).toHaveAttribute('aria-pressed', 'true'); // the clips (#669)
  await viewer.getByRole('navigation', { name: 'Stage' }).getByRole('button').first().click();
  await expect(page).toHaveURL(/\?stage=1$/);
  await expect(viewer).toHaveAttribute('aria-busy', 'false', { timeout: 45_000 });
  await viewer.getByRole('navigation', { name: 'Skeleton' }).getByRole('button', { name: 'Mechanical' }).click();
  await expect(page).toHaveURL(/\?stage=1&skeleton=mechanical$/);
  await expect(viewer).toHaveAttribute('aria-busy', 'false', { timeout: 45_000 });
  await viewer.getByRole('button', { name: 'Explode' }).click();
  await expect(page).toHaveURL(/\?stage=1&skeleton=mechanical&explode=1$/);
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

test('the diagrams draw, search finds a page, the header names the newest release', async ({ page }) => {
  // GitHub's newest release (docs/adr/0021), whatever it is when the test runs
  const release = 'https://github.com/yellow-pine/noggin/releases/tag/v0.2.19';
  await page.route('https://api.github.com/repos/yellow-pine/noggin/releases/latest', (r) =>
    r.fulfill({ json: { tag_name: 'v0.2.19', html_url: release } }),
  );
  // drawn in the page by the site's Mermaid, under its CSP
  await page.goto('docs/how-it-works/');
  const diagrams = page.locator('pre.mermaid');
  await expect(diagrams.first().locator('svg')).toBeVisible({ timeout: 15_000 });
  for (const d of await diagrams.all()) await expect(d.locator('svg')).toBeVisible();
  await page.getByRole('button', { name: 'Search' }).first().click();
  await page.getByRole('dialog', { name: 'Search' }).getByRole('textbox').fill('servo');
  await expect(page.locator('.pagefind-ui__result').first()).toBeVisible({ timeout: 15_000 });
  await page.keyboard.press('Escape');
  await expect(page.getByRole('link', { name: 'v0.2.19 (latest)' }).first()).toHaveAttribute('href', release);
});

// the Docs versions are gone (docs/adr/0021): an old one's URL lands on its page in the docs, or on the home
test("an old Docs version's URL lands on the same page, or the home", async ({ page }) => {
  await page.goto('v0.1/docs/how-it-works/');
  await expect(page).toHaveURL(/\/noggin\/docs\/how-it-works\/$/);
  // the home stubbed: its pictures are the live site's
  await page.route(/\/noggin\/$/, (r) => r.fulfill({ contentType: 'text/html', body: '<title>home</title>' }));
  await page.goto('v0.2.19/docs/gone/');
  await expect(page).toHaveURL(/\/noggin\/$/);
  errors = errors.filter((e) => !e.includes('status of 404')); // the old URL, and the page it lacks, answer 404
});
