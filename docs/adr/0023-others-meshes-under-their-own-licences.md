# Others' meshes under their own licences: the realistic skull

> Decided by Cansin on 2026-11-03, #838. Amends ADR 0020 (the realistic Skeleton gains bones of its own, not carved
> from a mechanical part).

The realistic Skeleton's skull and mandible are 3Demon's Anatomically Correct Human Skull (Printables 777324, CC BY-SA
4.0) and its atlas and axis Isopropyl Alcohol's C1 and C2 (Printables 1087469, CC BY-NC-SA 4.0): an anatomical skull
reads as one only when it is one, and no clean-room drawing of ours would. Each source sits in its own folder under
`model/skull/`, decimated for git, with a `LICENSE.md` naming its author, its page, its licence, that it is not under
the repo's PolyForm Noncommercial licence, and our changes; docs/credits.md credits both. The model adapts them
(`model/printed/skull.py`: scaled to the head, the orbits opened, carved for the mechanism and remeshed), and every
adaptation, the carved STLs, pictures and GLBs drawn from them, is shared under its source's licence, ShareAlike.
The skull and mandible print twice, bare and worn (carved round a Skin's Shells too). They ride the realistic
documents alone; the mechanical Skeleton, where physics runs, has none. A further third-party mesh joins the same way,
after its licence is checked (CLAUDE.md).

## Considered Options

- Our own clean-room skull (#51's rule for the rest of the Mech): no licence of others' in the repo, but no
  anatomy we could draw to the standard a printed skull is judged by.
- Keep the sources local only, like the designer's files (`docs/references/`): CI builds every output from sources in
  git (ADR 0009), so the carved bones could not be built.
