// The site as `just site` builds it into dist/ (docs/adr/0009, 0013), checked at its HTML: every doc is a page titled
// by its H1, every link lands, the numbers are the code's (macros.json), each page's footer and /version.json give the
// version and the commit, and each page's CSP lets only the site's own scripts run. Run after just site: npm test (Site
// Checks), and on a Docs version's build with SITE_BASE (docs/adr/0014).
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, globSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'node-html-parser';
import { expect, test } from 'vitest';
import { BASE, HOME, PAGES, REPO, ROOT, SITE, route } from './src/pages.mjs';

const DIST = fileURLToPath(new URL('dist/', import.meta.url));
const read = (f) => readFileSync(path.join(ROOT, f), 'utf8');
const numbers = JSON.parse(readFileSync(new URL('src/macros.json', import.meta.url), 'utf8'));
/** The built file a site path (under the base) is served from, or undefined off the site. */
const fileOf = (url) => {
  const p = url.replace(SITE, '').split(/[?#]/)[0];
  if (p !== BASE && !p.startsWith(`${BASE}/`)) return undefined;
  const rel = decodeURIComponent(p.slice(BASE.length + 1));
  return path.join(DIST, rel === '' || rel.endsWith('/') ? `${rel}index.html` : rel);
};
const html = globSync('**/*.html', { cwd: DIST });
const page = (url) => parse(readFileSync(fileOf(url), 'utf8'));
const docs = [...PAGES];

test('every doc is a page, titled by its own H1, drawn once', () => {
  expect(docs).toContain('docs/adr/0013-astro-starlight.md');
  for (const doc of docs) {
    const h1 = read(doc).match(/^# (.+)$/m)?.[1];
    expect(h1, doc).toBeDefined();
    expect(page(route(doc)).querySelectorAll('h1').map((h) => h.text.trim()), doc).toEqual([h1]);
  }
});

test('the README, CLAUDE.md and the references never ship', () => {
  for (const f of ['readme', 'claude', 'docs/references']) expect(existsSync(path.join(DIST, f)), f).toBe(false);
});

test('the landing page leads into Build and Use', () => {
  const links = page(`${BASE}/`).querySelectorAll('a').map((a) => a.getAttribute('href'));
  for (const target of [route('docs/build/parts.md'), route('docs/use/noggin-service.md')])
    expect(links).toContain(target);
});

test('the landing page has the sidebar every page has, itself first (#740)', () => {
  const sidebar = (url) => page(url).querySelectorAll('#starlight__sidebar a').map((a) => a.getAttribute('href'));
  expect(sidebar(`${BASE}/`)).toEqual(sidebar(route('docs/build/parts.md')));
  expect(sidebar(`${BASE}/`)[0]).toBe(`${BASE}/`);
});

test('the sidebar reaches every decision, the pictures and the viewer', () => {
  const links = page(route('docs/build/parts.md')).querySelectorAll('nav a').map((a) => a.getAttribute('href'));
  const adrs = docs.filter((d) => d.startsWith('docs/adr/'));
  expect(adrs.length).toBeGreaterThan(10);
  for (const target of [...adrs.map(route), route('docs/pictures.md'), `${BASE}/viewer/`]) expect(links).toContain(target);
});

// what CI adds beside the build when it was built (the pictures, the sim reports): a link there is checked when it is,
// and always in a Docs version, which never has them (docs/adr/0014)
const ADDED = ['images', 'reports'];
const built = (file) =>
  BASE !== HOME || !ADDED.some((d) => file.startsWith(path.join(DIST, d)) && !existsSync(path.join(DIST, d)));
const pages = html; // every one Astro's, the reports' page too (#603)

test('every link on the site lands on a page or file of it, and no .md link is left', () => {
  const broken = [];
  for (const f of html.filter((f) => f !== '404.html')) {
    // (the 404 page's canonical link is to /404/, which GitHub Pages serves from 404.html)
    for (const el of parse(readFileSync(path.join(DIST, f), 'utf8')).querySelectorAll('[href], [src]')) {
      const url = el.getAttribute('href') ?? el.getAttribute('src');
      if (/\.md(#|$)/.test(url) && !/^[a-z]+:/.test(url)) broken.push(`${f}: ${url}`);
      const file = fileOf(url);
      if (file && built(file) && !existsSync(file)) broken.push(`${f}: ${url}`);
    }
  }
  expect(broken).toEqual([]);
});

test("every site URL the repo's Markdown links to is a page with that heading", () => {
  for (const doc of ['README.md', ...docs]) {
    const links = read(doc).matchAll(/(?:\]\(|src=")(https:\/\/yellowpine\.com\/noggin\/[^)\s"#]*(?:#[\w-]+)?)/g);
    for (const [, url] of links) {
      const file = fileOf(url), anchor = url.split('#')[1];
      if (!file || !built(file)) continue; // a Docs version's: the live site's pictures, viewer and sim reports
      expect(existsSync(file), `${doc}: ${url}`).toBe(true);
      if (anchor) expect(parse(readFileSync(file, 'utf8')).getElementById(anchor), `${doc}: ${url}`).not.toBeNull();
    }
  }
});

// a Docs version (docs/adr/0014) is the same site under /noggin/vX.Y/: what it links outside itself is the live site's
test("a page links outside its version only to the live site's pictures, viewer and sim reports", () => {
  const out = [];
  for (const f of html)
    for (const el of parse(readFileSync(path.join(DIST, f), 'utf8')).querySelectorAll('[href], [src]')) {
      const p = (el.getAttribute('href') ?? el.getAttribute('src')).replace(SITE, '');
      const live = ['images', 'viewer', 'reports'].some((d) => p.startsWith(`${HOME}/${d}/`));
      if (p.startsWith(`${HOME}/`) && !p.startsWith(`${BASE}/`) && !live) out.push(`${f}: ${p}`);
    }
  expect(out).toEqual([]);
});

/** Text as written, before Astro's smart punctuation. */
const plain = (s) => s.trim().replace(/[‘’]/g, "'").replace(/[“”]/g, '"');
/** A Markdown table's rows as their cells' text (header and body, not the |---| line). */
const rows = (md) =>
  md
    .split('\n')
    .filter((l) => l.startsWith('|') && !/^\|[-|\s]+\|$/.test(l))
    .map((l) => l.slice(1, -1).split('|').map((c) => c.trim().replaceAll('`', '')));

test("each number a doc asks for is the code's, and what GitHub shows in its place is not on the site", () => {
  let used = 0;
  for (const doc of docs) {
    const source = read(doc);
    const shown = page(route(doc)).querySelectorAll('tr').map((tr) => tr.querySelectorAll('th, td').map((c) => plain(c.text)));
    for (const [, name, key] of source.matchAll(/^<!--\{\{\s*(\w+)(?:\[(\w+)\])?\s*\}\}-->$/gm)) {
      used++;
      const value = key === undefined ? numbers[name] : numbers[name][key];
      if (value.startsWith('<')) continue; // HTML, not a table: the panels' grid, its own test below
      const table = rows(value);
      expect(table.length, `${doc}: ${name}`).toBeGreaterThan(1);
      for (const row of table) expect(shown, `${doc}: ${name}`).toContainEqual(row);
    }
    const text = page(route(doc)).text;
    for (const [, github] of source.matchAll(/^<!--\{#.*-->\n(.{20})/gm)) expect(text, doc).not.toContain(github);
  }
  expect(used).toBeGreaterThanOrEqual(9);
});

test('the CI/CD page lists every workflow file, under Reference beside Contributing', () => {
  const files = globSync('*.yml', { cwd: path.join(ROOT, '.github/workflows') });
  expect(files.length).toBeGreaterThan(5);
  const cells = page(route('docs/ci-cd.md')).querySelectorAll('td').map((td) => td.text.trim());
  for (const f of files) expect(cells, f).toContain(f);
  const nav = page(route('docs/build/parts.md')).querySelectorAll('nav a').map((a) => a.getAttribute('href'));
  expect(nav.indexOf(route('docs/ci-cd.md'))).toBe(nav.indexOf(route('CONTRIBUTING.md')) + 1);
});

test("every page's CSP lets only the site's scripts run: each inline one by its hash, no 'unsafe-inline'", () => {
  for (const f of pages) {
    const doc = parse(readFileSync(path.join(DIST, f), 'utf8'));
    const csp = doc.querySelector('meta[http-equiv="content-security-policy"]')?.getAttribute('content');
    const scripts = csp?.match(/script-src ([^;]*)/)?.[1].split(/\s+/);
    expect(scripts, f).toBeDefined();
    expect(scripts).not.toContain("'unsafe-inline'");
    expect(csp).toContain("default-src 'self'");
    for (const s of doc.querySelectorAll('script')) {
      const src = s.getAttribute('src');
      if (src) expect(src.startsWith(`${BASE}/`), `${f}: ${src}`).toBe(true);
      else expect(scripts, f).toContain(`'sha256-${createHash('sha256').update(s.rawText).digest('base64')}'`);
    }
    for (const l of doc.querySelectorAll('link[rel="stylesheet"]')) expect(l.getAttribute('href')).toMatch(`${BASE}/`);
  }
});

const commit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: ROOT, encoding: 'utf8' }).trim();
const { version } = numbers.build; // git describe's, as macros.py read it where the site was built (docs/adr/0017)

test('/version.json is the version (the git tag), the commit built and when', () => {
  const built = JSON.parse(readFileSync(path.join(DIST, 'version.json'), 'utf8'));
  expect(Object.keys(built)).toEqual(['version', 'commit', 'built_at']);
  expect([built.version, built.commit]).toEqual([version, commit]);
  expect(new Date(built.built_at).toISOString()).toBe(built.built_at);
});

test("every page's footer links the version to its release (the releases before it) and the commit to GitHub", () => {
  const release = numbers.released ? `${REPO}/releases/tag/v${version}` : `${REPO}/releases`; // macros.released, test_site.py
  for (const f of pages) {
    const links = parse(readFileSync(path.join(DIST, f), 'utf8')).querySelectorAll('.noggin-version a');
    expect(links.map((a) => [a.text.trim(), a.getAttribute('href')]), f).toEqual([
      [`v${version}`, release],
      [commit.slice(0, 7), `${REPO}/commit/${commit}`],
    ]);
  }
});

// the look (#603): Yellow Pine's base, the Mech's filament accents, Rubik headings
test("every page's header names the site with its wordmark, whose o is the Mech's eye", () => {
  for (const f of pages) {
    const mark = parse(readFileSync(path.join(DIST, f), 'utf8')).querySelector('header a.site-title');
    expect(mark?.text.trim(), f).toBe('noggin');
    expect(mark.getAttribute('href'), f).toBe(`${BASE}/`);
    expect(mark.querySelectorAll('.noggin-o .noggin-eye').length, f).toBe(1);
  }
  expect(page(`${BASE}/`).querySelectorAll('h1 .noggin-o .noggin-eye').length).toBe(1); // and the landing page's title
});

test("every page's footer credits Yellow Pine with its logo, for the light theme and the dark", () => {
  for (const f of pages) {
    const credit = parse(readFileSync(path.join(DIST, f), 'utf8')).querySelector('footer .noggin-credit, .noggin-credit');
    expect(credit?.getAttribute('href'), f).toBe('https://yellowpine.com/');
    const logos = credit.querySelectorAll('img');
    expect(logos.map((i) => i.getAttribute('alt')), f).toEqual(['Yellow Pine', 'Yellow Pine']);
    for (const i of logos) expect(existsSync(fileOf(i.getAttribute('src'))), f).toBe(true);
  }
});

test("every page's icon is Yellow Pine's pine, no render of the Mech (#640)", () => {
  for (const f of pages) {
    const icons = parse(readFileSync(path.join(DIST, f), 'utf8')).querySelectorAll('link[rel~="icon"]');
    expect(icons.map((l) => l.getAttribute('href')), f).toEqual([`${BASE}/favicon.svg`]);
  }
  expect(existsSync(path.join(DIST, 'favicon.svg'))).toBe(true);
});

test("the headings' Rubik is the site's own file, never another host's", () => {
  const css = globSync('**/*.css', { cwd: DIST }).map((f) => readFileSync(path.join(DIST, f), 'utf8')).join('\n');
  const faces = [...css.matchAll(/@font-face\s*{[^}]*}/g)].map(([f]) => f).filter((f) => /font-family:\s*["']?Rubik/.test(f));
  expect(faces.length).toBeGreaterThan(0);
  for (const face of faces) {
    const [, weight] = face.match(/font-weight:\s*(\d+)/);
    expect(weight).toBe('700');
    for (const [, url] of face.matchAll(/url\(([^)]+)\)/g)) expect(existsSync(fileOf(url.replace(/["']/g, ''))), url).toBe(true);
  }
});

test("the sim reports' page is the site's own, listing each report the build has, or saying there is none", () => {
  const reports = page(`${BASE}/reports/`);
  expect(reports.querySelector('h1').text.trim()).toBe('Reports');
  const links = reports.querySelectorAll('main li a').map((a) => a.getAttribute('href'));
  const files = existsSync(path.join(DIST, 'reports'))
    ? globSync('*.{json,xml}', { cwd: path.join(DIST, 'reports') }).sort()
    : [];
  expect(links).toEqual(files);
  expect(reports.querySelectorAll('[data-reports]').length).toBe(files.length ? 0 : 1);
});

test("each Stage's guide opens with the Stages in order, by their titles, its own marked", () => {
  const guides = docs.filter((d) => d.startsWith('docs/build/stage-')).sort();
  expect(guides.length).toBeGreaterThan(1);
  for (const guide of guides) {
    const rail = page(route(guide)).querySelectorAll('nav[aria-label="Stages"] a');
    expect(rail.map((a) => [plain(a.text).replace(/\s+/g, ' '), a.getAttribute('href')]), guide).toEqual(
      guides.map((g) => [read(g).match(/^# (.+)$/m)[1].replace(': ', ' '), route(g)]),
    );
    expect(rail.map((a) => a.getAttribute('aria-current')), guide).toEqual(guides.map((g) => (g === guide ? 'page' : undefined)));
  }
});

// #640, #649 (docs/adr/0019): today's printed parts derive from the designer's models, so the site ships, links and
// draws pictures and GLBs of the next Mech alone, the ones the code publishes (macros.py published), and no photo.
// Checks runs it again once it has added the pictures and the GLB (-t picture)
test("every picture and GLB the site ships, links or draws is one of the next Mech's it publishes", () => {
  const { images, viewer } = numbers.published, ours = [...images, ...viewer];
  const mech = /\.(jpe?g|heic|webp|gif|glb|stl|step)$/i, name = (url) => path.basename(url.split(/[?#]/)[0]);
  const shipped = globSync('**/*', { cwd: DIST }).filter((f) => mech.test(f) || f.startsWith('images/'));
  const expected = [...images.map((f) => `images/${f}`), ...viewer.map((f) => `viewer/${f}`)];
  expect(shipped.filter((f) => !expected.includes(f))).toEqual([]);
  if (existsSync(path.join(DIST, 'images'))) expect(shipped.sort()).toEqual(expected.sort()); // as Checks adds them
  for (const f of html) {
    const doc = parse(readFileSync(path.join(DIST, f), 'utf8'));
    for (const v of doc.querySelectorAll('.noggin-viewer')) expect(viewer, f).toContain(`${v.getAttribute('data-stage')}.glb`);
    for (const el of doc.querySelectorAll('[href], [src]')) {
      const url = el.getAttribute('href') ?? el.getAttribute('src');
      if (mech.test(url.split(/[?#]/)[0]) || url.includes(`${HOME}/images/`)) expect(ours, `${f}: ${url}`).toContain(name(url));
    }
  }
});

test('Pictures shows the next Mech, it in motion and each of its parts, each linking to its full size', () => {
  const links = page(route('docs/pictures.md')).querySelectorAll('.noggin-panels a, .noggin-motions a, .noggin-parts a');
  expect(links.map((a) => a.getAttribute('href').split('/').at(-1))).toEqual(numbers.published.images);
  for (const a of links) expect(a.querySelector('img').getAttribute('src')).toBe(a.getAttribute('href'));
});

test("the viewer's page draws the next Mech, a Stage switch and a look switch, and serves three's Draco decoder", () => {
  const viewers = page(`${BASE}/viewer/`).querySelectorAll('.noggin-viewer'); // one, its buttons switching (#664, #720)
  expect(viewers).toHaveLength(1);
  const { buttons, looks } = numbers.published.stages;
  const stages = viewers[0].querySelectorAll('nav[aria-label="Stage"] button[data-stage]');
  expect(stages.map((b) => b.getAttribute('data-stage'))).toEqual(buttons.map((b) => b.glb));
  expect(stages.map((b) => b.text.trim())).toEqual(buttons.map((b) => b.label)); // a failing Stage's with its mark (#705)
  expect(stages.map((b) => b.text.split(':')[0].trim())).toEqual(['1', '2', '3']);
  const switches = viewers[0].querySelectorAll('nav[aria-label="Look"] button[data-look]');
  expect(switches.map((b) => [b.text.trim(), b.getAttribute('data-look')])).toEqual([['Bony', ''], ['Plain', '-plain']]);
  // every Stage in every look is a GLB the site serves
  const glbs = buttons.flatMap((b) => looks.map((l) => `${b.glb}${l.suffix}.glb`));
  expect(glbs.sort()).toEqual([...numbers.published.viewer].sort());
  for (const f of ['draco_wasm_wrapper.js', 'draco_decoder.wasm']) {
    const npm = path.join(ROOT, 'site/node_modules/three/examples/jsm/libs/draco/gltf', f);
    expect(readFileSync(path.join(DIST, 'viewer/draco', f)).equals(readFileSync(npm)), f).toBe(true);
  }
});

test("every diagram renders with the site's Mermaid (mermaid-cli in the installed Chrome)", { timeout: 120_000 }, () => {
  const tmp = mkdtempSync(path.join(tmpdir(), 'mmdc-'));
  // the installed Chrome; CI's image names its no-sandbox wrapper (ci/base.Dockerfile)
  const chrome = process.env.PUPPETEER_EXECUTABLE_PATH;
  writeFileSync(path.join(tmp, 'puppeteer.json'), JSON.stringify(chrome ? { executablePath: chrome } : { channel: 'chrome' }));
  const diagrams = docs.filter((d) => read(d).includes('```mermaid'));
  expect(diagrams).toContain('docs/how-it-works.md');
  for (const d of diagrams) {
    const out = path.join(tmp, path.basename(d));
    execFileSync(path.join(ROOT, 'site/node_modules/.bin/mmdc'), ['-q', '-p', path.join(tmp, 'puppeteer.json'), '-i', path.join(ROOT, d), '-o', out]);
  }
});
