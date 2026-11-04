// The Markdown plugins (Sätteri's mdast visitors) that let a page read the same on GitHub and on the site
// (docs/adr/0013): its H1 is the title Starlight draws, links between docs go to their pages, and the numbers the code
// owns fill the comments GitHub hides.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Slugger from 'github-slugger';
import { PAGES, REPO, ROOT, route } from './pages.mjs';

/** The page's H1 is its title (src/content.config.ts), which Starlight draws: the H1 itself goes. */
const h1 = {
  name: 'h1-is-the-title',
  heading(node, ctx) {
    if (node.depth !== 1 || ctx.data.h1) return;
    ctx.data.h1 = true;
    ctx.removeNode(node);
  },
};

/** A relative link to a doc goes to its page, or to GitHub when the doc is not one (the README). */
const links = {
  name: 'links-between-docs',
  link(node, ctx) {
    const m = node.url.match(/^([^/:#?][^:#?]*\.md)(#.*)?$/);
    if (!m) return;
    const from = path.relative(ROOT, path.dirname(fileURLToPath(ctx.fileURL)));
    const doc = path.posix.join(from, m[1]);
    ctx.setProperty(node, 'url', (PAGES.has(doc) ? route(doc) : `${REPO}/blob/main/${doc}`) + (m[2] ?? ''));
  },
};

// shortcut: read once per build; `just site` writes it first (python -m macros), a dev server needs a restart after
let numbers;
/** `<!--{{ name }}-->` (or `name[key]`) becomes that number's Markdown from the code (macros.py); a `<!--{# ... #}-->`
 * span, what GitHub shows in the table's place, goes. An unknown name fails the build. */
const macros = {
  name: 'numbers-from-the-code',
  html(node, ctx) {
    const value = node.value.trim();
    const use = value.match(/^<!--\{\{\s*(\w+)(?:\[(\w+)\])?\s*\}\}-->$/);
    if (use) {
      numbers ??= JSON.parse(readFileSync(path.join(ROOT, 'site/src/macros.json'), 'utf8'));
      const [, name, key] = use;
      const raw = key === undefined ? numbers[name] : numbers[name]?.[key];
      if (typeof raw !== 'string') throw new Error(`${ctx.fileURL}: no number ${value} in macros.json (macros.py)`);
      ctx.replaceNode(node, { raw });
    } else if (value.startsWith('<!--{#')) {
      const siblings = ctx.parent(node).children.slice(ctx.indexOf(node));
      const end = siblings.findIndex((n) => n.type === 'html' && n.value.trim().endsWith('#}-->'));
      if (end < 0) throw new Error(`${ctx.fileURL}: ${value} has no #}-->`);
      siblings.slice(0, end + 1).forEach((n) => ctx.removeNode(n));
    }
  },
};

/** A paragraph of nothing but "Open Stage N in the viewer" links (the viewer page's deep links, as GitHub shows them)
 * becomes their viewers (src/viewer/viewer.mjs, ADR 0008), each holding its link as macros.py embed does; several
 * stand in a row. */
const VIEWER = /^https:\/\/yellowpine\.com\/noggin\/viewer\/\?stage=(\d+)(?:&(.*))?$/;
const attr = (s) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
const embeds = {
  name: 'viewer-embeds',
  paragraph(node, ctx) {
    const kids = node.children.filter((n) => !(n.type === 'text' && /^[\s·]*$/.test(n.value)));
    if (!kids.length || !kids.every((n) => n.type === 'link' && VIEWER.test(n.url))) return;
    numbers ??= JSON.parse(readFileSync(path.join(ROOT, 'site/src/macros.json'), 'utf8'));
    const views = kids.map((n) => {
      const [, stage, link = ''] = n.url.match(VIEWER), glb = numbers.published.stages.buttons[stage - 1]?.glb;
      if (!glb) throw new Error(`${ctx.fileURL}: no Stage ${stage} for ${n.url}`);
      return `<div class="noggin-viewer" data-stage="${glb}" data-link="${attr(link)}"><p class="noggin-open">` +
        `<a href="${attr(n.url)}">${attr(ctx.textContent(n))}</a></p></div>`;
    });
    ctx.replaceNode(node, { raw: views.length > 1 ? `<div class="noggin-row not-content">${views.join('')}</div>` : views[0] });
  },
};

/** A mark's `#N`, in its text node, becomes a link to the issue (GitHub shows the text as written). */
const linkIssue = (node, n, ctx) => {
  const [head, tail] = node.value.split(`(#${n})`, 2);
  const link = { type: 'link', url: `${REPO}/issues/${n}`, children: [{ type: 'text', value: `#${n}` }] };
  ctx.replaceNode(node, [{ type: 'text', value: `${head}(` }, link, { type: 'text', value: `)${tail}` }]);
};

/** The marks (docs/adr/0024), each with its kind, issue, text and the heading it sits under, for the Roadmap page
 * (src/pages/roadmap.astro), which reads them from the page's render; each mark's `#N` links its issue. */
const marks = {
  name: 'marks',
  heading(node, ctx) {
    if (node.depth === 1) return; // the title, which h1-is-the-title drops
    ctx.data.slugger ??= new Slugger(); // as Astro's heading-ids, per page
    ctx.data.heading = { anchor: ctx.data.slugger.slug(ctx.textContent(node)), text: ctx.textContent(node) };
  },
  delete(node, ctx) {
    const siblings = ctx.parent(node).children, i = ctx.indexOf(node);
    const next = siblings[i + 1]?.type === 'text' && siblings[i + 1].value === ' ' ? siblings[i + 2] : siblings[i + 1];
    const last = next?.type === 'emphasis' ? next.children.at(-1) : undefined;
    const n = last?.type === 'text' && last.value.match(/\(#(\d+)\)$/)?.[1];
    if (!n) return; // not a mark: site.test.mjs fails the build's stray strikethrough
    const will = ctx.textContent(next).replace(/\s*\(#\d+\)$/, '');
    collect(ctx, { kind: 'change', issue: Number(n), text: `${ctx.textContent(node)} → ${will}` });
    linkIssue(last, n, ctx);
  },
  emphasis: (node, ctx) => upcoming(node, ctx, 'upcoming'),
  strong: (node, ctx) => upcoming(node, ctx, 'section'),
};
/** `*Upcoming (#N): …*`, or a NOTE's opening `**Upcoming (#N):**` for a whole section. */
function upcoming(node, ctx, kind) {
  const first = node.children[0];
  const n = first?.type === 'text' && first.value.match(/^Upcoming \(#(\d+)\)/)?.[1];
  if (!n) return;
  const rest = ctx.textContent(node).replace(/^Upcoming \(#\d+\):?\s*/, '');
  collect(ctx, { kind, issue: Number(n), text: kind === 'section' ? (ctx.data.heading?.text ?? '') : rest });
  linkIssue(first, n, ctx);
}
const collect = (ctx, mark) => {
  const { frontmatter } = ctx.data.astro;
  const anchor = ctx.data.heading?.anchor ?? '';
  (frontmatter.marks ??= []).push({ ...mark, text: mark.text.replace(/\s+/g, ' '), anchor });
};

export const markdown = [h1, links, macros, embeds, marks];
