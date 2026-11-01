// Astro hashes the scripts it bundles into each page's CSP, but not the `is:inline` ones (Starlight's theme, menu and
// sidebar scripts): this adds every inline script's hash the page lacks once the site is built, so none is ever listed
// by hand (docs/adr/0011, 0013) and a Starlight upgrade that changes one needs no edit. site.test.mjs checks the result.
import { createHash } from 'node:crypto';
import { globSync, readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { parse } from 'node-html-parser';

/** The page's HTML with every inline script's sha256 in its CSP's script-src. */
export function hashInlineScripts(html) {
  const page = parse(html);
  const meta = page.querySelector('meta[http-equiv="content-security-policy"]');
  if (!meta) throw new Error('a page without its CSP meta');
  const csp = meta.getAttribute('content');
  const hashes = page
    .querySelectorAll('script:not([src])')
    .map((s) => `'sha256-${createHash('sha256').update(s.rawText).digest('base64')}'`)
    .filter((h) => !csp.includes(h));
  if (!hashes.length) return html;
  const policy = csp.replace(/script-src [^;]*/, (d) => [d.trimEnd(), ...new Set(hashes)].join(' '));
  const out = html.replace(`content="${csp}"`, `content="${policy}"`);
  if (out === html) throw new Error('the CSP meta is not where its content says');
  return out;
}

export const inlineScriptHashes = {
  name: 'inline-script-hashes',
  hooks: {
    'astro:build:done': ({ dir }) => {
      for (const f of globSync('**/*.html', { cwd: fileURLToPath(dir) })) {
        const file = new URL(f, dir);
        writeFileSync(file, hashInlineScripts(readFileSync(file, 'utf8')));
      }
    },
  },
};
