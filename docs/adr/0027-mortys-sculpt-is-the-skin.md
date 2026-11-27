# Morty's sculpt is the Skin

> Decided by Cansin on 2026-11-27, spec #893 (its comment "Directive from Cansin (2026-11-27): Morty's actual skin is
> the Skin"), ticket #850. Amends ADR 0023 (a further mesh of another author joins), ADR 0025 (the sculpt was a local
> fit reference, the head's box the skull's limit) and ADR 0026 (the sculpt is no longer a private input). Where this
> ADR and an older one disagree, this one holds.

Spec #893 is a mechanical system fitted inside, and alongside, a morphologically convincing skeleton, inside Morty's
actual skin. The work had drifted from that: the printable Skin stayed Shells we drew by hand in CadQuery, and the
skull was sized to a compact box that came from those Shells. So Morty's Skin is his Sculpt (GLOSSARY): ChelsCCT's
"Morty Smith [Rick and Morty]" (Printables 13460, CC BY 4.0).

- **The Skin is cut from the Sculpt.** The Sculpt's surface is the Skin's outside from the crown to the base plane:
  head, neck, shirt, shoulders and upper arms. The printed wall grows 1.6 mm inward from it, with 0.5 mm of clearance
  behind the wall, so bone and mechanism stay at least 2.1 mm under Morty's surface. His silhouette is the Sculpt's,
  exactly.
- **No Shell is drawn by hand.** Morty's, Bart's and Cansin's CadQuery Shells are deleted (#850), with their tests and
  the lists of known meetings kept for them. Bart (#913) and Cansin (#917) return when each has a Sculpt to be cut
  from.
- **Every limit is measured from the Sculpt.** The skull's limit is the Sculpt's surface less 2.1 mm; the mechanism's
  is that less the bone. The compact head's box (160 x 176 x 175 mm) is retired as a gate, and the skull grows into
  Morty's real crown and back (#874). Where the mechanism does not fit inside his skin, the mechanism moves (#967);
  the skin keeps its shape.
- **The seams are cut once, on the Sculpt** (#992): the same cuts colour the review and split the printed Shells,
  along the Motion regions (#969). The hairline follows the Sculpt's own hair boundary, the whole eye dome is the eye
  white, and the jaw's Shell is the chin and lower lip under the mouth line. Where the Sculpt shows a form, the Sculpt
  sets the boundary; the model sheet supplies only what it does not show (pupils, the mouth line, the collar).
- **The Sculpt is public.** Its licence allows sharing and adapting with credit, so it joins the repo ADR 0023's way:
  its own folder, `model/morty`, with a `LICENSE.md` naming the author, the page, the licence and our changes, and a
  line on docs/credits.md. CI builds the Shells from it, and the Site, the Web viewer and the pictures may show them.
  The licence covers the mesh alone: Morty Smith is Adult Swim's character, and Cansin accepts that risk, for Morty
  and for a later Bart. ADR 0025's coarse hull of our own is not needed.
- **What git holds** is the whole Sculpt in its own frame and millimetres, decimated in Blender and nothing else
  (`model/morty/adopt.py`, which also measures how far the copy strays from the original; `LICENSE.md` records the
  numbers), under a size cap that a test holds, with no LFS. The Model scales and places it on the Mech's eyes.

## Considered Options

- Keep refitting our own Shells to the Sculpt (#850 until today): two shapes to keep in agreement, each refit left
  known meetings behind, and the silhouette was ours, not Morty's.
- Keep the Sculpt local and commit a coarse hull (ADR 0025): CI builds every output from sources in git (ADR 0009), so
  it could check a fit against the hull but never build his Skin.
- Sculpt our own Morty, clean-room: the character question stays the same, and no sculpt of ours would read as him as
  one made for that does (ADR 0023's reason for the skull).
- Git LFS for the full-resolution Sculpt: past the free tier's bandwidth for a public repo's clones (ADR 0025).
