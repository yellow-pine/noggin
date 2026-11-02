// A PR or issue title's rules (docs/adr/0010, #767): config-conventional's, plus exactly one scope, derived from the repo (ADR 0011):
// each tracked top-level folder (no dot-folders), each tracked folder in docs/, and Dependabot's deps and deps-dev.
// The scopes come from git in the working directory, so run it at the repo's root. A bot's title is its own
// (Dependabot, the weekly bumps): it can't shorten it, so PR_AUTHOR_TYPE=Bot lifts the length limit.
// Run: npm ci --prefix ci && ci/node_modules/.bin/commitlint --config ci/commitlint.config.mjs <<<"<title>"
import { execFileSync } from 'node:child_process';

const folders = execFileSync('git', ['ls-files'], { encoding: 'utf8' })
  .split('\n')
  .map((f) => f.split('/').slice(0, -1))
  .filter((p) => p.length);
const scopes = new Set(folders.map((p) => (p[0] === 'docs' && p.length > 1 ? p[1] : p[0])).filter((s) => !s.startsWith('.')));

export default {
  extends: ['@commitlint/config-conventional'],
  plugins: [{ rules: { 'scope-single': ({ scope }) => [!/[,/\\]/.test(scope ?? ''), 'name one scope, not a list'] } }],
  rules: {
    'scope-empty': [2, 'never'],
    'scope-single': [2, 'always'],
    'scope-enum': [2, 'always', [...scopes, 'deps', 'deps-dev'].sort()],
    'header-max-length': [process.env.PR_AUTHOR_TYPE === 'Bot' ? 0 : 2, 'always', 100],
  },
};
