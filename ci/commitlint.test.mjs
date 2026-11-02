// commitlint.config.mjs through commitlint's own CLI, on sample PR titles, as the PR check runs it (docs/adr/0010).
// Run: npm ci --prefix ci && node --test ci/commitlint.test.mjs (Checks' Code job)
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const ci = fileURLToPath(new URL('.', import.meta.url));
const lint = (title, { cwd = join(ci, '..'), env = {} } = {}) =>
  spawnSync(join(ci, 'node_modules/.bin/commitlint'), ['--config', join(ci, 'commitlint.config.mjs')], {
    input: title,
    cwd,
    env: { ...process.env, PR_AUTHOR_TYPE: 'User', ...env },
    encoding: 'utf8',
  });
const passes = (title, options) => lint(title, options).status === 0;

test('the type is one of config-conventional\'s', () => {
  assert.ok(passes('feat(eyes): a wink'));
  assert.ok(!passes('feature(eyes): a wink'));
  assert.ok(!passes('eyes: a wink'));
});

test('a title names exactly one scope, from the list', () => {
  assert.ok(passes('ci(deps-dev): bump x'));
  assert.ok(!passes('feat: a wink'));
  assert.ok(!passes('feat(nowhere): a wink'));
  for (const list of ['feat(eyes,web): a wink', 'feat(eyes, web): a wink', 'feat(eyes/web): a wink']) {
    const result = lint(list);
    assert.notEqual(result.status, 0, list);
    assert.match(result.stdout, /one scope/);
  }
});

test('the scopes are the tracked top-level folders, docs/ folders and the bots\'', () => {
  const repo = mkdtempSync(join(tmpdir(), 'scopes-'));
  const tracked = ['eyes/eyes.py', 'docs/adr/0001.md', 'docs/index.md', '.github/workflows/x.yml', 'README.md'];
  for (const f of [...tracked, 'untracked/x', 'docs/drafts/x.md']) {
    mkdirSync(join(repo, f, '..'), { recursive: true });
    writeFileSync(join(repo, f), '');
  }
  spawnSync('git', ['init', '-q'], { cwd: repo });
  spawnSync('git', ['add', ...tracked], { cwd: repo });
  for (const scope of ['adr', 'deps', 'deps-dev', 'docs', 'eyes']) assert.ok(passes(`docs(${scope}): x`, { cwd: repo }));
  for (const scope of ['untracked', 'drafts', 'workflows', 'github', '.github', 'web'])
    assert.ok(!passes(`docs(${scope}): x`, { cwd: repo }), scope);
});

test('the header is at most 100 characters, except a bot\'s', () => {
  const head = 'feat(eyes): ';
  assert.ok(passes(head + 'b'.repeat(100 - head.length)));
  assert.ok(!passes(head + 'b'.repeat(101 - head.length)));
  assert.ok(passes(head + 'b'.repeat(101 - head.length), { env: { PR_AUTHOR_TYPE: 'Bot' } }));
});

test('the issues Default Branch Failure files have valid titles (#767, #791)', () => {
  const flow = readFileSync(join(ci, '../.github/workflows/default-branch-failure.yml'), 'utf8');
  const [title, ...more] = [...flow.matchAll(/title="(fix[^"]+)"/g)].map((m) => m[1]);
  assert.equal(more.length, 0);
  for (const scope of ['model', 'site', 'ci'])
    for (const workflow of ['Checks', 'CI Images'])
      for (const job of ['', ' (Model)']) {
        const filed = title.replace('$scope', scope).replace('$WORKFLOW', workflow).replaceAll('\\`', '`')
          .replace('${SHA:0:7}', '0a1b2c3') + job; // a sha may start with a digit
        assert.ok(!filed.includes('$'), filed);
        assert.ok(passes(filed, { env: { PR_AUTHOR_TYPE: 'Bot' } }), filed);
      }
});

// subject-case fails a subject whose first letter is a capital, acronym or not; backticked text is skipped (#509)
const subjects = {
  'OpenSSF Scorecard weekly': false,
  'SECURITY.md points at x': false,
  'PR titles take any scope': false,
  'Add a thing': false,
  'Add A Thing': false,
  'ADD A THING': false,
  'add a thing.': false,
  'add a thing': true,
  '`OpenSSF` Scorecard weekly': true,
  '`SECURITY.md` points at x': true,
  '`PR` titles take any scope': true,
  '1 more thing': true,
  'Blender 5.2.3 in the CI image, without its bundled requests, pip and setuptools': false, // #545 (#548)
};
for (const [subject, ok] of Object.entries(subjects))
  test(`the subject "${subject}" ${ok ? 'passes' : 'fails'}`, () => {
    for (const title of [`docs(docs): ${subject}`, `docs(docs)!: ${subject}`]) assert.equal(passes(title), ok, title);
  });
