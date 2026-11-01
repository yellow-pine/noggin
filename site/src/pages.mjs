// Which of the repo's Markdown files are pages, and each one's route: shared by the content loader, the Markdown
// plugins (links between docs) and the tests.
import { globSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

export const ROOT = fileURLToPath(new URL('../..', import.meta.url));
export const SITE = 'https://yellowpine.com';
export const BASE = '/noggin';
export const REPO = 'https://github.com/yellow-pine/noggin';
// the root's Markdown and docs/, but not the README and CLAUDE.md (for contributors and agents, on GitHub), the
// generated changelog nor the designer's files (docs/references, local only)
const INCLUDE = ['*.md', 'docs/**/*.md'];
const EXCLUDE = ['README.md', 'CLAUDE.md', 'CHANGELOG.md', 'docs/references/**'];
export const PATTERN = [...INCLUDE, ...EXCLUDE.map((p) => `!${p}`)];
export const PAGES = new Set(globSync(INCLUDE, { cwd: ROOT, exclude: EXCLUDE }));

/** A page's id, its route under the base, from its path in the repo: docs/index.md is the landing page, at the root. */
export const id = (path) => (path === 'docs/index.md' ? 'index' : path.replace(/\.md$/, '').toLowerCase());

/** The site's URL path of a page. */
export const route = (path) => `${BASE}/${id(path) === 'index' ? '' : `${id(path)}/`}`;
