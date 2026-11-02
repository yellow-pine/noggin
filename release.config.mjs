// semantic-release's config (docs/adr/0017), its default plugins alone; ci/release.test.mjs runs its rules.
// RELEASE_BUMP is Release's manual run's bump (#802): patch, minor or major matches every commit at least at that
// bump, ahead of the rules (commit-analyzer takes a commit's highest match, so a break still bumps the minor); auto,
// or unset on main's push, leaves the commits to decide. With no commit since the last tag nothing releases.
const BUMPS = ['patch', 'minor', 'major'];

export const config = (bump) => {
  if (bump && bump !== 'auto' && !BUMPS.includes(bump)) throw new Error(`RELEASE_BUMP ${bump}: auto, ${BUMPS}`);
  const forced = BUMPS.includes(bump) ? [{ release: bump }] : [];
  return {
    branches: ['main'],
    preset: 'conventionalcommits',
    plugins: [
      [
        '@semantic-release/commit-analyzer',
        {
          releaseRules: [
            ...forced,
            { breaking: true, release: 'minor' },
            { type: 'feat', release: 'patch' },
            { type: 'fix', release: 'patch' },
            { type: 'perf', release: 'patch' },
            { type: 'revert', release: 'patch' },
          ],
        },
      ],
      '@semantic-release/release-notes-generator',
      [
        '@semantic-release/github',
        { successCommentCondition: false, failCommentCondition: false, releasedLabels: false },
      ],
    ],
  };
};

export default config(process.env.RELEASE_BUMP);
