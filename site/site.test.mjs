// The site as `make site` builds it into dist/ (docs/adr/0009, 0012), checked at its HTML: every doc is a page titled
// by its H1, every link lands, the numbers are the code's (macros.json), and each page's CSP lets only the site's own
// scripts run. Run after make site: npm test (Site Checks).
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, globSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'node-html-parser';
import { expect, test } from 'vitest';
import { BASE, PAGES, ROOT, SITE, route } from './src/pages.mjs';

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
  expect(docs).toContain('docs/adr/0012-astro-starlight.md');
  for (const doc of docs) {
    const h1 = read(doc).match(/^# (.+)$/m)?.[1];
    expect(h1, doc).toBeDefined();
    expect(page(route(doc)).querySelectorAll('h1').map((h) => h.text.trim()), doc).toEqual([h1]);
  }
});

test('the README, CLAUDE.md and the references never ship', () => {
  for (const f of ['readme', 'claude', 'docs/references']) expect(existsSync(path.join(DIST, f)), f).toBe(false);
});

test('the home page leads into Build, Use and the viewer', () => {
  const links = page(`${BASE}/`).querySelectorAll('a').map((a) => a.getAttribute('href'));
  for (const target of [route('docs/build/parts.md'), route('docs/use/noggin-service.md'), `${SITE}${BASE}/viewer/`])
    expect(links).toContain(target);
});

test('the sidebar reaches every decision and the viewer', () => {
  const links = page(route('docs/build/parts.md')).querySelectorAll('nav a').map((a) => a.getAttribute('href'));
  const adrs = docs.filter((d) => d.startsWith('docs/adr/'));
  expect(adrs.length).toBeGreaterThan(10);
  for (const target of [...adrs.map(route), `${BASE}/viewer/`]) expect(links).toContain(target);
});

// what make site adds beside the build when it was built (pictures, sim reports): a link there is checked when it is
const ADDED = ['images', 'reports'];
const built = (file) => !ADDED.some((d) => file.startsWith(path.join(DIST, d)) && !existsSync(path.join(DIST, d)));

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
    const links = read(doc).matchAll(/(?:\]\(|src=")(https:\/\/yellowpine\.com\/noggin\/[^)\s"#]*(?:#([\w-]+))?)/g);
    for (const [, url, anchor] of links) {
      const file = fileOf(url);
      if (!built(file)) continue;
      expect(existsSync(file), `${doc}: ${url}`).toBe(true);
      if (anchor) expect(parse(readFileSync(file, 'utf8')).getElementById(anchor), `${doc}: ${url}`).not.toBeNull();
    }
  }
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
      const table = rows(key === undefined ? numbers[name] : numbers[name][key]);
      expect(table.length, `${doc}: ${name}`).toBeGreaterThan(1);
      for (const row of table) expect(shown, `${doc}: ${name}`).toContainEqual(row);
    }
    const text = page(route(doc)).text;
    for (const [, github] of source.matchAll(/^<!--\{#.*-->\n(.{20})/gm)) expect(text, doc).not.toContain(github);
  }
  expect(used).toBeGreaterThanOrEqual(8);
});

test("every page's CSP lets only the site's scripts run: each inline one by its hash, no 'unsafe-inline'", () => {
  for (const f of html) {
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

test('the hero shows at its size in a figure on the home page and Pictures', () => {
  for (const url of [`${BASE}/`, route('docs/pictures.md')]) {
    const img = page(url).querySelector(`figure img[src="${SITE}${BASE}/images/hero.gif"]`);
    expect([img?.getAttribute('width'), img?.getAttribute('height')], url).toEqual(['800', '400']);
  }
});

test("the viewer's page has a button per Stage and serves the Draco decoder from three's npm package", () => {
  const viewer = page(`${BASE}/viewer/`).querySelector('.noggin-viewer');
  expect(viewer.querySelectorAll('nav button').map((b) => b.getAttribute('data-stage'))).toEqual(numbers.stages);
  expect(viewer.getAttribute('data-stage')).toBe(numbers.stages.at(-1));
  for (const f of ['draco_wasm_wrapper.js', 'draco_decoder.wasm']) {
    const npm = path.join(ROOT, 'site/node_modules/three/examples/jsm/libs/draco/gltf', f);
    expect(readFileSync(path.join(DIST, 'viewer/draco', f)).equals(readFileSync(npm)), f).toBe(true);
  }
});

test('no real photo ships or is linked: every picture is one CI renders, at /images', () => {
  const photo = /\.(jpe?g|heic)$/i;
  const files = globSync('**/*', { cwd: DIST }).filter((f) => photo.test(f) && !f.startsWith('images/'));
  expect(files).toEqual([]);
  for (const f of html)
    for (const el of parse(readFileSync(path.join(DIST, f), 'utf8')).querySelectorAll('[href], [src]')) {
      const url = el.getAttribute('href') ?? el.getAttribute('src');
      if (photo.test(url.split(/[?#]/)[0])) expect(url, f).toMatch(`${SITE}${BASE}/images/`);
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
