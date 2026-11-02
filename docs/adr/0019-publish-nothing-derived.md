# Publish nothing derived from today's printed parts

> Decided with Cansin on 2026-11-02, #640, on #618's licence research (its 2026-11-02 note in docs/research).
> Amends ADR 0008 (the viewer is off the site) and ADR 0009 (CI
> builds the pictures and GLBs no more).
> Amended 2026-11-02 (#649, Cansin): the Next Mech, clean-room, is published as soon as its pieces exist. CI's
> `Blender` job renders its panels and a picture per part (`just pictures next`) and bakes its GLB (`just web
> next-mech`) when what they are made from changed; the site serves them at /images and /viewer (Model > Pictures,
> Viewer), updated on every merge to main; a PR that changes them gets a before/after panel, the live site's above its
> own, as the `preview` artifact (`just preview <pr>`). Every name published starts `next-`, and tests hold what is
> rendered, baked, uploaded and served to the Next Mech's documents, which carry none of today's printed parts
> (test_workflows.py, test_site.py, site.test.mjs). Today's Mech stays unpublished.
> Amended 2026-11-02 (#656, Cansin): the Next Mech in motion too, its eye gimbal's sweep, blink and wink as looping
> WebPs (`next-eyes-<motion>.webp`, `just pictures next`) on Pictures, and a PR's preview stacks each motion it changed,
> the live one above its own.
> Amended 2026-11-02 (#673, Cansin): no PR preview any more, it arrived too late to be useful: no before/after, no
> `preview` artifact or `just preview`, no sticky comment and no `pr-previews` pre-release (deleted). A PR still
> renders and bakes the next Mech when its inputs changed, for Checks to test the site with; main publishes them.
> Amended 2026-11-02 (#663, Cansin): the motions the Next Mech plays in MuJoCo, its gestures and Rest, join the sweep
> as `next-eyes-<motion>.webp` (Rest's blink and the wink gesture in place of the keyed blink and wink) and as clips of
> its GLB.
> Amended 2026-11-02 (#642): the Next Mech's documents are its two Base candidates, `next-mech-a` and `next-mech-b`
> (`just web next`), each published as `next-mech` was.
> Amended 2026-11-02 (#686): its three head variants, `next-mech-back`, `next-mech-crown` and `next-mech-split`, in
> place of the Base candidates.

Today's printed parts follow the designer's three models, whose licence forbids sharing or hosting "any other
derivative work of this object in its digital or physical format". So nothing public shows or carries their geometry
until the clean-room Mech (#51) replaces them: the site has no pictures, hero, panels or viewer (its page, its GLBs, the
favicon render), the README no hero, a release's docs no GLBs, and CI uploads no artifact with a mesh, an STL, a
picture or a GLB (the parts' cut passes between jobs in the Actions cache, which nobody outside the repo's workflows
can read). CI still builds and tests the model, the sim and its reports; the reports are numbers and MJCF that names
mesh files without carrying them, so /reports stays. The render and viewer code stays in the repo and runs locally
(`just render`, `just hero`, `just web`); CI no longer runs Blender. The parts' source in model/printed stays public
until #51 deletes it, and history is not rewritten.

## Considered options

- Ask the designer for permission: her Exclusive programme bars her from allowing it elsewhere (the research, section 6).
- Keep rendering in CI without publishing: on a public repo every artifact is downloadable, and pictures nobody can
  see only cost CI minutes.
