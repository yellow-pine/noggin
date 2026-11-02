// .releaserc.json's rules through semantic-release's own commit-analyzer, on sample PR titles (docs/adr/0017): before
// 1.0 a break bumps the minor, never the major; feat, fix, perf and revert the patch; the other types release nothing.
// Run: npm ci --prefix ci && node --test ci/release.test.mjs (Checks' Code job)
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { analyzeCommits } from '@semantic-release/commit-analyzer';

const { plugins, branches, ...shared } = JSON.parse(readFileSync(new URL('../.releaserc.json', import.meta.url)));
const [, own] = plugins.find((p) => p[0] === '@semantic-release/commit-analyzer');
const logger = { log() {} };
// what semantic-release hands the plugin: the shared options under its own
const bump = (...titles) =>
  analyzeCommits(
    { ...shared, ...own },
    { commits: titles.map((message, i) => ({ hash: `${i}`, message })), logger, cwd: process.cwd() },
  );

const cases = {
  'feat(eyes): a wink': 'patch',
  'fix(noggin): the beacon again': 'patch',
  'perf(model): a faster sweep': 'patch',
  'revert(eyes): a wink': 'patch',
  'feat(eyes)!: a new Link protocol': 'minor',
  'fix(noggin)!: calibration in degrees': 'minor',
  'docs(adr)!: a break in a docs title': 'minor',
  'docs(docs): a page': null,
  'ci(ci): a job': null,
  'chore(deps): a bump': null,
  'build(ci): a recipe': null,
  'test(eyes): a case': null,
  'style(site): a colour': null,
  'refactor(model): a module': null,
};

for (const [title, release] of Object.entries(cases))
  test(`${title} releases ${release ?? 'nothing'}`, async () => assert.equal(await bump(title), release));

test('a break among features is still the minor, never the major', async () => {
  assert.equal(await bump('feat(eyes): a wink', 'feat(eyes)!: a new Link protocol', 'fix(eyes): a blink'), 'minor');
});
