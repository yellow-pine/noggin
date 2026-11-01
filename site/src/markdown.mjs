// The Markdown plugins (Sätteri's mdast visitors) that let a page read the same on GitHub and on the site
// (docs/adr/0012): its H1 is the title Starlight draws, links between docs go to their pages, and the numbers the code
// owns fill the comments GitHub hides.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
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

// shortcut: read once per build; `make site` writes it first (python -m macros), a dev server needs a restart after
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

export const markdown = [h1, links, macros];
