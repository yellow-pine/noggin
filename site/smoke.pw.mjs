// The built site in Chrome (#513): the diagrams draw, search finds a page, the header names the newest release and an
// old Docs version's URL lands on the docs (docs/adr/0021), the wordmark's eye looks at the pointer (#603), and nothing
// breaks the CSP, logs an error or asks another host than api.github.com (the header's release, stars and forks). The viewer loads the next Mech (#649), the only
// one the site serves (docs/adr/0019), and plays its gestures (#664). The header's Theme bar (#806, #819) shows each page
// in the Preset picked, kept in the address and across pages, the viewer's Shapes and Palettes too, and its own mix,
// the bare anatomical Skeleton while none is picked; a viewer in a page has no control (#883).
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
  test.slow(); // three GLB loads in CI's software GL, each allowed 45 s: 54 s of the default 60 before the mix (#819)
  await page.goto('viewer/');
  const viewer = page.locator('.noggin-viewer'); // one, its Stage switch (#720), its Shapes the bar's Preset's (#819)
  await expect(viewer).toHaveAttribute('aria-busy', 'false', { timeout: 45_000 });
  await expect(viewer.getByRole('button', { name: 'Tour' })).toHaveAttribute('aria-pressed', 'true'); // the clips (#669)
  const mix = viewer.getByRole('navigation', { name: 'Mix' }); // any Shape in any Palette (#819)
  // no Preset picked: its own mix, Stage 3's bare anatomical Skeleton, a Skin switched on Morty's (#883)
  const own = { 'Skeleton shape': 'realistic', 'Skeleton palette': 'anatomical', 'Skin shape': 'none', 'Skin palette': 'morty' };
  for (const [axis, value] of Object.entries(own)) await expect(mix.getByRole('combobox', { name: axis })).toHaveValue(value);
  expect(requests.filter((u) => u.endsWith('.glb')).map((u) => u.split('/').at(-1))).toEqual(['next-mech-back-bare.glb']);
  await viewer.getByRole('navigation', { name: 'Stage' }).getByRole('button').first().click();
  await expect(page).toHaveURL(/\/viewer\/\?stage=1$/);
  await expect(viewer).toHaveAttribute('aria-busy', 'false', { timeout: 45_000 });
  await mix.getByRole('combobox', { name: 'Skeleton palette' }).selectOption('robot'); // a repaint, no load
  await expect(page).toHaveURL(/\/viewer\/\?stage=1&skeleton-palette=robot$/);
  await page.locator('header').getByRole('combobox', { name: 'Preset' }).selectOption('morty');
  await expect(page).toHaveURL(/\?stage=1&preset=morty$/); // the Preset's own mix
  await expect(mix.getByRole('combobox', { name: 'Skin shape' })).toHaveValue('morty');
  await expect(viewer).toHaveAttribute('aria-busy', 'false', { timeout: 45_000 });
  const explode = viewer.getByRole('navigation', { name: 'Explode' }); // Explode's levels (#811)
  await explode.getByRole('button', { name: 'Sub-assemblies' }).click();
  await expect(page).toHaveURL(/\?preset=morty&stage=1&explode=1$/);
  await explode.getByRole('button', { name: 'Parts' }).click();
  await expect(page).toHaveURL(/\?preset=morty&stage=1&explode=2$/);
  await expect(explode.getByRole('button', { name: 'Parts' })).toHaveAttribute('aria-pressed', 'true');
  // see-through, so the Mech sits on the page's own background in either theme: its canvas' corner (the one renderer
  // draws every viewer, each copied into its own canvas, #839)
  expect(await page.evaluate(() => document.querySelector('.noggin-viewer canvas').getContext('2d').getImageData(0, 0, 1, 1).data[3])).toBe(0);
  await page.evaluate(() => addEventListener('wheel', (e) => (window.zoomed = e.defaultPrevented), { once: true }));
  await viewer.locator('canvas').hover();
  await page.mouse.wheel(0, 200);
  await expect.poll(() => page.evaluate(() => window.zoomed)).toBe(true); // OrbitControls takes it from the page
});

test("the Theme bar shows the page in the Preset picked, by keyboard too, kept in the address and across pages", async ({ page }) => {
  await page.goto('docs/build/parts/'); // its buy list's filaments (#806, #819); Pictures' pictures are the live site's
  await expect(page).toHaveURL(/\/parts\/$/); // none picked: the default's, the address untouched (#883)
  const item = (p) => page.locator(`li[data-presets="${p}"]`);
  const bar = page.locator('header').getByRole('combobox', { name: 'Preset' });
  await expect(item('cansins-build')).toBeVisible();
  await expect(item('morty')).toBeHidden();
  await bar.focus();
  await page.keyboard.press('m'); // a closed select picks the option its letter starts
  await expect(page).toHaveURL(/\?preset=morty$/);
  await expect(item('morty')).toBeVisible();
  await expect(item('cansins-build')).toBeHidden();
  await page.goto('docs/build/stage-1/'); // another page, no address: what was picked last
  await expect(bar).toHaveValue('morty');
  await page.goto('docs/build/parts/?preset=bart'); // the address first
  await expect(item('bart')).toBeVisible();
  await expect(item('morty')).toBeHidden();
});

test('a viewer in a page shows its Mech and its motion, with no control (#883)', async ({ page }) => {
  // Pictures' stills are the live site's: a blank PNG each, and no request of ours
  const PNG = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';
  await page.route('https://yellowpine.com/**', (r) => r.fulfill({ contentType: 'image/png', body: Buffer.from(PNG, 'base64') }));
  await page.goto('docs/pictures/');
  const viewers = page.locator('.noggin-motions .noggin-viewer'); // one per motion of Stage 1 (#839)
  await viewers.first().scrollIntoViewIfNeeded(); // the viewer's module loads once one is in view (Footer.astro)
  await expect(viewers.first().locator('.noggin-caption')).toBeAttached(); // mounted
  await expect(viewers.locator('button, select, nav')).toHaveCount(0);
  requests = requests.filter((u) => !u.startsWith('https://yellowpine.com/'));
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
  await expect(page).toHaveURL(/\/noggin\/docs\/how-it-works\/$/); // no Preset picked (#883)
  // the home stubbed: its pictures are the live site's
  await page.route(/\/noggin\/$/, (r) => r.fulfill({ contentType: 'text/html', body: '<title>home</title>' }));
  await page.goto('v0.2.19/docs/gone/');
  await expect(page).toHaveURL(/\/noggin\/$/); // the stub has no bar
  errors = errors.filter((e) => !e.includes('status of 404')); // the old URL, and the page it lacks, answer 404
});
