// The site as `just site` builds it into dist/ (docs/adr/0009, 0013), checked at its HTML: every doc is a page titled
// by its H1, every link lands, the numbers are the code's (macros.json), each page's footer and /version.json give the
// version and the commit, each page's CSP lets only the site's own scripts run, and the marks (docs/adr/0024) are in
// their format, on the Roadmap and name open issues. Run after just site: npm test (Site Checks; GITHUB_TOKEN set for
// the issues' check).
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, globSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'node-html-parser';
import { expect, test } from 'vitest';
import { HOME, PAGES, REPO, ROOT, SITE, route } from './src/pages.mjs';

const DIST = fileURLToPath(new URL('dist/', import.meta.url));
const read = (f) => readFileSync(path.join(ROOT, f), 'utf8');
const numbers = JSON.parse(readFileSync(new URL('src/macros.json', import.meta.url), 'utf8'));
/** The built file a site path (under the base) is served from, or undefined off the site. */
const fileOf = (url) => {
  const p = url.replace(SITE, '').split(/[?#]/)[0];
  if (p !== HOME && !p.startsWith(`${HOME}/`)) return undefined;
  const rel = decodeURIComponent(p.slice(HOME.length + 1));
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
  const links = page(`${HOME}/`).querySelectorAll('a').map((a) => a.getAttribute('href'));
  for (const target of [route('docs/build/parts.md'), route('docs/use/noggin-service.md')])
    expect(links).toContain(target);
});

test('the landing page has the sidebar every page has, itself first (#740)', () => {
  const sidebar = (url) => page(url).querySelectorAll('#starlight__sidebar a').map((a) => a.getAttribute('href'));
  expect(sidebar(`${HOME}/`)).toEqual(sidebar(route('docs/build/parts.md')));
  expect(sidebar(`${HOME}/`)[0]).toBe(`${HOME}/`);
});

test('the sidebar reaches every decision, the pictures and the viewer', () => {
  const links = page(route('docs/build/parts.md')).querySelectorAll('nav a').map((a) => a.getAttribute('href'));
  const adrs = docs.filter((d) => d.startsWith('docs/adr/'));
  expect(adrs.length).toBeGreaterThan(10);
  for (const target of [...adrs.map(route), route('docs/pictures.md'), `${HOME}/viewer/`]) expect(links).toContain(target);
});

// what CI adds beside the build when it was built (the pictures, the sim reports): a link there is checked when it is
const ADDED = ['images', 'reports'];
const built = (file) => !ADDED.some((d) => file.startsWith(path.join(DIST, d)) && !existsSync(path.join(DIST, d)));
const pages = html; // every one Astro's, the reports' page too (#603)

test('every link on the site lands on a page or file of it, at its heading, and no .md link is left', () => {
  const broken = [], ids = new Map();
  const idsOf = (file) => ids.get(file) ?? ids.set(file, new Set(parse(readFileSync(file, 'utf8')).querySelectorAll('[id]').map((e) => e.id))).get(file);
  for (const f of html.filter((f) => f !== '404.html')) {
    // (the 404 page's canonical link is to /404/, which GitHub Pages serves from 404.html)
    for (const el of parse(readFileSync(path.join(DIST, f), 'utf8')).querySelectorAll('[href], [src]')) {
      const url = el.getAttribute('href') ?? el.getAttribute('src');
      if (/\.md(#|$)/.test(url) && !/^[a-z]+:/.test(url)) broken.push(`${f}: ${url}`);
      const file = fileOf(url);
      if (file && built(file) && !existsSync(file)) broken.push(`${f}: ${url}`);
      // a heading it names is on that page (#900: Gestures' link to the home's #gestures)
      const anchor = url.match(/^[^#]*#([\w-]+)$/)?.[1];
      if (anchor && file?.endsWith('.html') && existsSync(file) && !idsOf(file).has(anchor)) broken.push(`${f}: ${url}`);
    }
  }
  expect(broken).toEqual([]);
});

test("every site URL the repo's Markdown links to is a page with that heading", () => {
  for (const doc of ['README.md', ...docs]) {
    const links = read(doc).matchAll(/(?:\]\(|src=")(https:\/\/yellowpine\.com\/noggin\/[^)\s"#]*(?:#[\w-]+)?)/g);
    for (const [, url] of links) {
      const file = fileOf(url), anchor = url.split('#')[1];
      if (!file || !built(file)) continue;
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
    .map((l) => l.slice(1, -1).split('|').map((c) => c.trim().replaceAll('`', '').replace(/<[^>]+>/g, ''))); // a cell's text

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
      if (src) expect(src.startsWith(`${HOME}/`), `${f}: ${src}`).toBe(true);
      else expect(scripts, f).toContain(`'sha256-${createHash('sha256').update(s.rawText).digest('base64')}'`);
    }
    for (const l of doc.querySelectorAll('link[rel="stylesheet"]')) expect(l.getAttribute('href')).toMatch(`${HOME}/`);
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
    expect(mark.getAttribute('href'), f).toBe(`${HOME}/`);
    expect(mark.querySelectorAll('.noggin-o .noggin-eye').length, f).toBe(1);
  }
  expect(page(`${HOME}/`).querySelectorAll('h1 .noggin-o .noggin-eye').length).toBe(1); // and the landing page's title
});

test("every page's header has the Theme bar: one labelled select of the model's Presets, in order (#819)", () => {
  for (const f of html.filter((f) => !f.startsWith('reports/'))) {
    const doc = parse(readFileSync(path.join(DIST, f), 'utf8'));
    // in the header, and in the mobile menu where the page has one (not the 404's)
    const bars = [doc.querySelector('header .sl-hidden .noggin-theme'), ...doc.querySelectorAll('.mobile-preferences .noggin-theme')];
    expect(bars.length, f).toBe(doc.querySelector('.mobile-preferences') ? 2 : 1);
    for (const bar of bars) {
      expect(bar?.getAttribute('aria-label'), f).toBe('Theme');
      const selects = bar.querySelectorAll('label > select');
      expect(selects.map((s) => s.parentNode.querySelector('span').text), f).toEqual(['Preset']);
      expect(selects[0].querySelectorAll('option').map((o) => [o.getAttribute('value'), o.text])).toEqual([
        ['default-build', "Default build"], ['morty', 'Morty'], ['bart', 'Bart'],
      ]);
    }
    expect(doc.toString(), f).toContain(':root[data-preset="morty"] [data-presets]:not([data-presets~="morty"])');
  }
});

test("each Preset's pictures and filaments are marked with it, the default's shown with no pick (#806, #819)", () => {
  const home = page(`${HOME}/`), parts = page(route('docs/build/parts.md'));
  // #843: the front doors are the default's bare mechanism, one three for every Preset
  expect(home.querySelectorAll('.noggin-front figure').map((f) => f.hasAttribute('data-presets'))).toEqual([
    false, false, false,
  ]);
  const pictures = page(route('docs/pictures.md'));
  expect(home.querySelector('p[data-presets="default-build"] em')).toBeNull();  // #843: no Skin on the home
  expect(pictures.querySelector('p[data-presets="bart"] em')?.text).toContain("in Morty's Shape");  // stand-in (#813)
  expect(parts.querySelectorAll('li[data-presets]').map((l) => l.text.split(':')[0])).toEqual([
    "Default build", 'Morty', 'Bart',
  ]);
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
    expect(icons.map((l) => l.getAttribute('href')), f).toEqual([`${HOME}/favicon.svg`]);
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
  const reports = page(`${HOME}/reports/`);
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
// draws pictures and GLBs of the Mech alone, the ones the code publishes (macros.py published), and no photo.
// CI's Site job runs it with the pictures and the GLB in (#732)
test("every picture and GLB the site ships, links or draws is one of the Mech's it publishes", () => {
  const { images, viewer } = numbers.published, ours = [...images, ...viewer];
  const mech = /\.(jpe?g|heic|webp|gif|glb|stl|step)$/i, name = (url) => path.basename(url.split(/[?#]/)[0]);
  const shipped = globSync('**/*', { cwd: DIST }).filter((f) => mech.test(f) || f.startsWith('images/'));
  const expected = [...images.map((f) => `images/${f}`), ...viewer.map((f) => `viewer/${f}`)];
  expect(shipped.filter((f) => !expected.includes(f))).toEqual([]);
  if (existsSync(path.join(DIST, 'images'))) expect(shipped.sort()).toEqual(expected.sort()); // as CI's just site adds them
  for (const f of html) {
    const doc = parse(readFileSync(path.join(DIST, f), 'utf8'));
    for (const v of doc.querySelectorAll('.noggin-viewer')) expect(viewer, f).toContain(`${v.getAttribute('data-stage')}.glb`);
    for (const el of doc.querySelectorAll('[href], [src]')) {
      const url = el.getAttribute('href') ?? el.getAttribute('src');
      if (new URL(url, SITE).origin !== new URL(SITE).origin) continue; // a research note's external link is not ours (#868)
      if (mech.test(url.split(/[?#]/)[0]) || url.includes(`${HOME}/images/`)) expect(ours, `${f}: ${url}`).toContain(name(url));
    }
  }
});

test("Pictures shows the front doors' stills at full size and every other picture in the viewer (#898)", () => {
  const pictures = page(route('docs/pictures.md'));
  const stills = pictures.querySelectorAll('.noggin-views figure > a');
  expect(stills.map((a) => a.getAttribute('href').split('/').at(-1))).toEqual(numbers.published.images.slice(0, 3));
  for (const a of stills) expect(a.querySelector('img').getAttribute('src')).toBe(a.getAttribute('href'));
  const links = pictures.querySelectorAll('.noggin-views .noggin-viewer').map((v) => v.getAttribute('data-link'));
  for (const each of ['view=side', 'view=isometric', 'explode=2']) expect(links.filter((l) => l === each)).toHaveLength(3);
  expect(links.filter((l) => l.startsWith('part=')).length).toBeGreaterThan(40); // each part alone, the rest ghosted
});

test("Pictures plays each motion of Stage 1 in a viewer of its own, the Stage's poster its still until then (#839)", () => {
  const viewers = page(route('docs/pictures.md')).querySelectorAll('.noggin-motions .noggin-viewer');
  const links = viewers.map((v) => v.getAttribute('data-link')).sort();
  expect(links).toEqual([...Object.keys(numbers.moments), 'rest'].map((g) => `gesture=${g}`).sort()); // its gestures and Rest
  for (const v of viewers) expect(v.querySelector('figure img').getAttribute('src')).toMatch(/\/stage1-isometric\.webp$/);
});

test("every viewer in a page holds a plain link to what it plays in the viewer page, which GitHub shows (#889)", () => {
  const stages = numbers.published.stages.buttons.map((b) => b.glb);
  for (const f of html) {
    for (const v of parse(readFileSync(path.join(DIST, f), 'utf8')).querySelectorAll('.noggin-viewer:not([data-zoom])')) {
      const link = v.querySelector('.noggin-open a'), stage = stages.indexOf(v.getAttribute('data-stage')) + 1;
      const own = v.getAttribute('data-link');
      expect(link?.getAttribute('href'), f).toBe(`https://yellowpine.com/noggin/viewer/?stage=${stage}${own ? `&${own}` : ''}`);
      expect(link.text, f).toBe(`Open Stage ${stage} in the viewer`);
    }
  }
});

test("the home opens on a large Stage 3 viewer on its hero loop, from the view of its poster, the Stage 3 still", () => {
  const hero = page(`${HOME}/`).querySelector('.sl-markdown-content > .noggin-viewer.hero');
  expect(hero.getAttribute('data-stage')).toBe(numbers.published.stages.buttons.at(-1).glb);
  expect(hero.getAttribute('data-link')).toBe('view=isometric'); // no gesture: the hero loop
  expect(hero.hasAttribute('data-tap')).toBe(true); // a phone loads it on a tap
  const still = hero.querySelector('figure img').getAttribute('src').split('/').at(-1);
  expect(numbers.published.images).toContain(still);
  expect(still).toMatch(/-isometric\.webp$/);
});

// a page's embeds (a paragraph of nothing but "Open Stage N in the viewer" links, src/markdown.mjs): each one's Stage
// number and link
const embedsOf = (doc) =>
  page(route(doc)).querySelectorAll('.sl-markdown-content .noggin-viewer').map((v) => [
    numbers.published.stages.buttons.findIndex((b) => b.glb === v.getAttribute('data-stage')) + 1,
    v.getAttribute('data-link'),
  ]);

test("each Stage's guide opens on its Stage's viewer, a view or a part of it in its steps (#914, #900)", () => {
  expect(embedsOf('docs/build/stage-1.md')).toEqual([[1, ''], [1, 'part=L+upper+lid'], [1, 'view=front']]);
  expect(embedsOf('docs/build/stage-2.md')).toEqual([[2, ''], [2, 'view=side']]);
  expect(embedsOf('docs/build/stage-3.md')).toEqual([[3, ''], [3, 'part=jaw'], [3, 'explode=1']]);
  for (const doc of ['docs/build/stage-1.md', 'docs/build/stage-2.md', 'docs/build/stage-3.md']) {
    const [, first] = page(route(doc)).querySelector('.sl-markdown-content').children; // under the warning, before a word
    expect(first.getAttribute('class'), doc).toBe('noggin-viewer');
  }
});

test('the sidebar runs Home, Start here, Build, Use, How it works, Model, Reference, Model from the Viewer (#914)', () => {
  const nav = page(route('docs/build/parts.md')).querySelector('#starlight__sidebar');
  const top = nav.querySelectorAll(':scope ul.top-level > li').map((li) => plain(li.querySelector('a, summary').text).trim());
  expect(top).toEqual(['Home', 'Start here', 'Build', 'Use', 'How it works', 'Model', 'Reference']);
  const model = nav.querySelectorAll(':scope ul.top-level > li').find((li) => li.querySelector('summary')?.text.includes('Model'));
  expect(model.querySelectorAll('a').map((a) => plain(a.text).trim())).toEqual(['Viewer', 'Pictures', 'Roadmap', 'Reports', 'Notes']);
  expect(nav.querySelector('a[href$="/docs/start-here/"]')).not.toBeNull();
});

test("Stage 2's Torso and Stage 1's test stand carry their marks, which the Roadmap lists (#914)", () => {
  const on = (n) => roadmap().filter(([i]) => i === String(n)).map(([, href]) => href.split('#')[0]);
  expect(on(879)).toContain(route('docs/build/stage-2.md'));
  expect(on(877)).toContain(route('docs/build/stage-1.md'));
});

test("the viewer's page draws the Mech and a Stage switch, the Preset its Shapes, and serves three's Draco decoder", () => {
  const viewers = page(`${HOME}/viewer/`).querySelectorAll('.noggin-viewer'); // one, its buttons switching (#664, #720)
  expect(viewers).toHaveLength(1);
  const { buttons, skeletons, skins } = numbers.published.stages;
  const stages = viewers[0].querySelectorAll('nav[aria-label="Stage"] button[data-stage]');
  expect(stages.map((b) => b.getAttribute('data-stage'))).toEqual(buttons.map((b) => b.glb));
  expect(stages.map((b) => b.text.trim())).toEqual(buttons.map((b) => b.label)); // a failing Stage's with its mark (#705)
  expect(stages.map((b) => b.text.split(':')[0].trim())).toEqual(['1', '2', '3']);
  expect(viewers[0].querySelectorAll('select')).toHaveLength(0); // the bar's Preset, then the mix the viewer adds (#819)
  // every Stage in every Skeleton shape is a GLB the site serves, Stage 3 bare in each too (#876)
  const shapes = Object.values(skeletons), whole = buttons.at(-1).glb;
  const glbs = [
    ...buttons.flatMap((b) => shapes.map((s) => `${b.glb}${s}.glb`)),
    ...shapes.flatMap((s) => Object.values(skins).map((k) => `${whole}${s}${k}.glb`)),
  ];
  expect(glbs.sort()).toEqual([...numbers.published.viewer].sort());
  for (const f of ['draco_wasm_wrapper.js', 'draco_decoder.wasm']) {
    const npm = path.join(ROOT, 'site/node_modules/three/examples/jsm/libs/draco/gltf', f);
    expect(readFileSync(path.join(DIST, 'viewer/draco', f)).equals(readFileSync(npm)), f).toBe(true);
  }
});

// The marks (docs/adr/0024): ~~is~~ *will be (#N)*, *Upcoming (#N): …* and a NOTE opening **Upcoming (#N):**, each
// linking its issue, and nothing else struck through (a stray pair of single ~ strikes the text between them)
const issue = (n) => `${REPO}/issues/${n}`;
const marksOf = (doc) => [
  ...doc.querySelectorAll('del').map((del) => [del.nextElementSibling, del]),
  ...doc.querySelectorAll('em, strong').filter((e) => /^Upcoming \(#/.test(e.text)).map((e) => [e, e]),
];
test("every mark is in the one format, linking its issue, and nothing else is struck through", () => {
  let found = 0;
  for (const f of html) {
    const doc = parse(readFileSync(path.join(DIST, f), 'utf8'));
    for (const [mark, at] of marksOf(doc)) {
      const where = `${f}: ${at.toString().slice(0, 80)}`;
      if (at.tagName === 'DEL') expect(mark?.tagName, where).toBe('EM');
      const [, n] = mark.text.match(at.tagName === 'DEL' ? /\(#(\d+)\)$/ : /^Upcoming \(#(\d+)\):/) ?? [];
      expect(n, where).toBeDefined();
      expect(mark.querySelector('a')?.getAttribute('href'), where).toBe(issue(n));
      if (mark.tagName === 'STRONG') expect(mark.closest('aside.starlight-aside--note'), where).not.toBeNull();
      found++;
    }
  }
  expect(found).toBeGreaterThan(0);
});

const roadmap = () =>
  page(`${HOME}/roadmap/`).querySelectorAll('main [data-issue] li a').map((a) => {
    const n = a.closest('[data-issue]').getAttribute('data-issue');
    return [n, a.getAttribute('href')];
  });

test('the Roadmap, under Model, lists every mark by its issue, each linking the page and heading it sits on', () => {
  const marks = [];
  for (const f of html.filter((f) => f !== 'roadmap/index.html')) {
    for (const [mark] of marksOf(parse(readFileSync(path.join(DIST, f), 'utf8'))))
      marks.push([mark.querySelector('a').text.slice(1), `${HOME}/${f.replace(/index\.html$/, '')}`]);
  }
  const listed = roadmap();
  expect(listed.map(([n, href]) => [n, href.split('#')[0]]).sort()).toEqual(marks.sort());
  expect(listed.map(([n]) => Number(n))).toEqual(listed.map(([n]) => Number(n)).sort((a, b) => a - b)); // by issue
  for (const [, href] of listed) {
    const anchor = href.split('#')[1];
    if (anchor) expect(page(href).getElementById(anchor), href).not.toBeNull();
  }
  const nav = page(route('docs/build/parts.md')).querySelectorAll('nav a').map((a) => a.getAttribute('href'));
  expect(nav.indexOf(`${HOME}/roadmap/`)).toBe(nav.indexOf(`${HOME}/reports/`) - 1);
});

// main's Checks alone, with the workflow's token (checks.yml's Site): a PR closing #N clears #N's marks (ADR 0024)
const token = process.env.GITHUB_TOKEN;
test.skipIf(!token)("every mark's issue is open on GitHub", async () => {
  const issues = [...new Set(roadmap().map(([n]) => n))];
  const closed = [];
  for (const n of issues) {
    const r = await fetch(`https://api.github.com/repos/yellow-pine/noggin/issues/${n}`, {
      headers: { authorization: `Bearer ${token}`, accept: 'application/vnd.github+json' },
    });
    expect(r.ok, `#${n}: ${r.status}`).toBe(true);
    if ((await r.json()).state !== 'open') closed.push(`#${n}`);
  }
  expect(closed, 'marks naming a closed issue: clear them (docs/adr/0024)').toEqual([]);
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
