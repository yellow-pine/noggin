# Changelog

## [0.2.1](https://github.com/yellow-pine/noggin/compare/v0.2.0...v0.2.1) (2026-11-02)


### Features

* **site:** the viewer is the landing page's hero, and the gesture GIFs go ([#480](https://github.com/yellow-pine/noggin/issues/480)) ([68b83c2](https://github.com/yellow-pine/noggin/commit/68b83c29fc1f0eb6363fd537c2445cd3da068768))


### Bug Fixes

* **ci:** an over-budget PR run warns instead of failing ([#460](https://github.com/yellow-pine/noggin/issues/460)) ([6f1fc9b](https://github.com/yellow-pine/noggin/commit/6f1fc9b2b022aa7ad7d9e8709f35ccc8eff6f6b7))
* **scripts:** worktrees-clean keeps an open PR's worktree and never removes by ancestry ([#466](https://github.com/yellow-pine/noggin/issues/466)) ([ffca312](https://github.com/yellow-pine/noggin/commit/ffca3120d93f3d4aea1ac605259567cdf0426018))


### Documentation

* **docs:** a PR's title is its whole squash commit, with no body ([#461](https://github.com/yellow-pine/noggin/issues/461)) ([ad50a44](https://github.com/yellow-pine/noggin/commit/ad50a44737e88ec9827cce9b513da798ca2a2723))
* **docs:** implementers run ponytail-review locally; CI's Review runs code-review ([#483](https://github.com/yellow-pine/noggin/issues/483)) ([0049dee](https://github.com/yellow-pine/noggin/commit/0049dee47e88683db530c2825682b478fcca7b7b))
* **docs:** the implementer checks its title first and waits on CI to a terminal state ([#434](https://github.com/yellow-pine/noggin/issues/434)) ([57749bd](https://github.com/yellow-pine/noggin/commit/57749bd79f7fce89d0de0d58508e139bd9ee98e8))
* **docs:** the main session only coordinates; PR fixes go to the PR's implementer ([#458](https://github.com/yellow-pine/noggin/issues/458)) ([b6b6d87](https://github.com/yellow-pine/noggin/commit/b6b6d87589779a6f01356365826579d3acb590d4))
* **research:** retro of the 2026-11-02 session ([#485](https://github.com/yellow-pine/noggin/issues/485)) ([b4eba2d](https://github.com/yellow-pine/noggin/commit/b4eba2d25f1f5e39b664dfb6ed7f87fd26a6947e))

## [0.2.0](https://github.com/yellow-pine/noggin/compare/v0.1.1...v0.2.0) (2026-11-02)


### Features

* **release:** /release releases whatever is pending ([#413](https://github.com/yellow-pine/noggin/issues/413)) ([303d69c](https://github.com/yellow-pine/noggin/commit/303d69c16bbf7d1caf401a885a8d6eb8351028ba))


### Documentation

* **adr:** a taken ADR number fails Code, and one command renumbers the draft ([#410](https://github.com/yellow-pine/noggin/issues/410)) ([ae61acb](https://github.com/yellow-pine/noggin/commit/ae61acbec3124b47994d9589458472f67f9057cb))
* **docs:** rebase a PR only when it needs main ([#406](https://github.com/yellow-pine/noggin/issues/406)) ([002f18c](https://github.com/yellow-pine/noggin/commit/002f18cb4fc739b5bf8fbe674953f2b753550b9d))
* **docs:** regenerate the README's CI/CD table after [#417](https://github.com/yellow-pine/noggin/issues/417) and [#419](https://github.com/yellow-pine/noggin/issues/419) ([#423](https://github.com/yellow-pine/noggin/issues/423)) ([9024d40](https://github.com/yellow-pine/noggin/commit/9024d4082d3ce7d2a81d3013016a7b4082e661f0))
* **docs:** the README's CI/CD table is generated from the workflows ([#408](https://github.com/yellow-pine/noggin/issues/408)) ([e6320fc](https://github.com/yellow-pine/noggin/commit/e6320fc726ccb3c40f39ea56b210a2affaed2bc2))

## [0.1.1](https://github.com/yellow-pine/noggin/compare/v0.1.0...v0.1.1) (2026-11-01)


### Features

* an implementer agent type carrying the standing rules ([#387](https://github.com/yellow-pine/noggin/issues/387)) ([35cb7b9](https://github.com/yellow-pine/noggin/commit/35cb7b94b22cef257a0326adfac805083a5c0499))
* **model:** the hero GIF at 64 colours, like every GIF ([#378](https://github.com/yellow-pine/noggin/issues/378)) ([be95550](https://github.com/yellow-pine/noggin/commit/be955501850f8835df23677ea770e72baf336585))
* **site:** each release's docs under /noggin/vX.Y/ with a version switcher ([#383](https://github.com/yellow-pine/noggin/issues/383)) ([3830ee0](https://github.com/yellow-pine/noggin/commit/3830ee0aa1b4037840b47f3682c2536f645735fa))
* **site:** footer and /version.json show the version and deployed commit ([#380](https://github.com/yellow-pine/noggin/issues/380)) ([d012071](https://github.com/yellow-pine/noggin/commit/d0120716ac90ba692849c919bc45ee455064f13b))

## 0.1.0 (2026-11-01)


### ⚠ BREAKING CHANGES

* **noggin:** the Core's beacon reports its program's version and commit ([#366](https://github.com/yellow-pine/noggin/issues/366))

### Features

* **noggin:** the Core's beacon reports its program's version and commit ([#366](https://github.com/yellow-pine/noggin/issues/366)) ([1ed224d](https://github.com/yellow-pine/noggin/commit/1ed224d66b4a89a0e4bb510043562a3f187e9a4a))
* one version, noggin vX.Y.Z, released by release-please ([#311](https://github.com/yellow-pine/noggin/issues/311)) ([c6d250c](https://github.com/yellow-pine/noggin/commit/c6d250c2fdda45b635b7e9c1aa840d3290758098))
* **site:** Astro Starlight replaces MkDocs Material ([#347](https://github.com/yellow-pine/noggin/issues/347)) ([4e02013](https://github.com/yellow-pine/noggin/commit/4e0201361d6ae21e263615b614d2c799e86549ac))


### Documentation

* keep everything current, the Core's firmware through the vendor's tools (ADR 0012) ([#339](https://github.com/yellow-pine/noggin/issues/339)) ([b879954](https://github.com/yellow-pine/noggin/commit/b8799540ded1058f738bb3d2a30860ebe2c15bd2))
* record the no-paid-services directive ([#324](https://github.com/yellow-pine/noggin/issues/324)) ([d3ea59c](https://github.com/yellow-pine/noggin/commit/d3ea59c943358dfc275b25cd5039a04982fd8d60))
* research GIF encoding: ffmpeg, gifski, animated WebP ([#346](https://github.com/yellow-pine/noggin/issues/346)) ([a56befb](https://github.com/yellow-pine/noggin/commit/a56befbf2573fd20441de895e96054d70ffc5852))
* research the stack and the best free alternative for each piece ([#334](https://github.com/yellow-pine/noggin/issues/334)) ([55227be](https://github.com/yellow-pine/noggin/commit/55227be90a5ec53a890c3c83d58038d8a4ee05f7))
* review never rejects an update for being early ([#362](https://github.com/yellow-pine/noggin/issues/362)) ([613b8bd](https://github.com/yellow-pine/noggin/commit/613b8bdd5604ba95d9ff2778d3f15941763dd400))
* what the eyes Core reports ([#349](https://github.com/yellow-pine/noggin/issues/349)) ([48661fe](https://github.com/yellow-pine/noggin/commit/48661fe84ebe40005e2cccfeec782818bed66074))
* wiring table and viewer Stage buttons from the code; tests from imports ([#306](https://github.com/yellow-pine/noggin/issues/306)) ([#312](https://github.com/yellow-pine/noggin/issues/312)) ([b3acd68](https://github.com/yellow-pine/noggin/commit/b3acd68e3bee270a8744e2e1aec9a7cb5d1e0204))
