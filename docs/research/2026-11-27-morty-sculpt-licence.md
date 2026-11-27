# The Morty sculpt's licence, before we adopt it (2026-11-27)

We are about to commit a decimated copy of ChelsCCT's "Morty Smith [Rick and Morty]" (`morty-fixed.stl`) and publish
printable parts cut from it. Which licence does the author's page state today, what does that licence ask of someone
sharing an adaptation, and what does it not cover?

All sources read on 2026-11-27 with curl, anonymously. Printables' page HTML and Thingiverse both answered HTTP 403
with a Cloudflare challenge ("Just a moment..."); neither was pushed further. The Printables facts come from its own
public GraphQL API, `print(id: "13460")`. Inferred: the API is the data the page renders. Not legal advice: the texts
are quoted, and every reading of ours is marked inferred.

## 1. What the host states

- **Licence: "Creative Commons — Attribution", abbreviation "CC-BY", version 4.0 International.** The API's
  `license` is `{id: "1", name: "Creative Commons — Attribution", abbreviation: "CC-BY", disallowRemixing: false}`;
  its `content` (the licence panel's HTML) reads "This work is licensed under a Creative Commons (4.0 International
  License) Attribution" and links <http://creativecommons.org/licenses/by/4.0/>. So Printables states the version; it
  is not inferred (<https://api.printables.com/graphql/>).
- **The panel's own summary:** "✖ Sharing without ATTRIBUTION", "✔ Remix Culture allowed", "✔ Commercial Use",
  "✔ Free Cultural Works", "✔ Meets Open Definition" (same API field).
- **Author:** `publicUsername` "ChelsCCT (Chelsey Creates Things)", `handle` "ChelsCCT", `authorship: "author"`.
  **Published:** `datePublished` and `firstPublish` 2019-12-05T22:04:32Z; `modified` 2022-04-12T14:26:50Z (same API).
- **Files:** `morty-fixed.stl`, 45,485,984 bytes, and `rm_stand.stl` (same API). The byte count matches our local
  copy, whose 80-byte STL header is all zeros: the file carries no notice of its own.
- **Thingiverse (<https://www.thingiverse.com/thing:2442056>): not read**, HTTP 403. The earlier note's "CC BY 4.0"
  for it came from a third-party mirror, so it stays unverified at the source. The Printables entry lists that URL as
  its `remixParents` and carries the tag "thingiverse" (inferred: the author's import of her own design).

## 2. What CC BY 4.0 asks of someone sharing an adaptation

Legal code: <https://creativecommons.org/licenses/by/4.0/legalcode.en>. Deed:
<https://creativecommons.org/licenses/by/4.0/deed.en>.

- **Grant (2(a)(1)):** "worldwide, royalty-free, non-sublicensable, non-exclusive, irrevocable", to "reproduce and
  Share the Licensed Material, in whole or in part" and "produce, reproduce, and Share Adapted Material".
- **Commercial use is allowed:** "for any purpose, even commercially" (deed); the legal code has no NonCommercial term.
- **Attribution (3(a)(1)(A)):** "retain the following if it is supplied by the Licensor": "identification of the
  creator(s) ... (including by pseudonym if designated)"; "a copyright notice"; "a notice that refers to this Public
  License"; "a notice that refers to the disclaimer of warranties"; "a URI or hyperlink to the Licensed Material to the
  extent reasonably practicable".
- **Changes (3(a)(1)(B)):** "indicate if You modified the Licensed Material and retain an indication of any previous
  modifications".
- **Licence notice (3(a)(1)(C)):** "indicate the Licensed Material is licensed under this Public License, and include
  the text of, or the URI or hyperlink to, this Public License".
- **Manner (3(a)(2)):** "in any reasonable manner based on the medium, means, and context"; a "URI or hyperlink to a
  resource that includes the required information" may do. On the licensor's request the credit comes off (3(a)(3)).
- **Another licence for the adaptation (3(a)(4)):** allowed for our own contributions: "the Adapter's License You
  apply must not prevent recipients of the Adapted Material from complying with this Public License". No ShareAlike.
- **The sculpt itself stays CC BY 4.0 (2(a)(5)(A), (B)):** "Every recipient of the Licensed Material automatically
  receives an offer from the Licensor"; "You may not offer or impose any additional or different terms or conditions
  on ... the Licensed Material if doing so restricts exercise of the Licensed Rights". Creative Commons' FAQ, "If I
  derive or adapt material ...": "the original CC license always applies to the material you are adapting even once
  adapted" (<https://creativecommons.org/faq/>).
- **No endorsement (2(a)(6));** rights end on a breach and return if it is cured within 30 days (6(a), 6(b)).
- Inferred: the page supplies a creator name and a URI, and no copyright or disclaimer notice. A credit beside the
  committed file and on `docs/credits.md` meets 3(a)(1): the title, "ChelsCCT (Chelsey Creates Things)", the Printables
  URL, "CC BY 4.0" with <https://creativecommons.org/licenses/by/4.0/>, and "modified: decimated, cut into parts".
- Inferred: the repo's PolyForm Noncommercial licence can cover our own changes (3(a)(4)) but cannot narrow the
  sculpt's geometry (2(a)(5)(B)); the credit should say the sculpt-derived mesh is CC BY 4.0, not the repo's licence.

## 3. What the licence does not cover

- **Only the licensor's own rights.** "Licensed Rights" are "limited to all Copyright and Similar Rights that apply to
  Your use of the Licensed Material and that the Licensor has authority to license" (section 1).
- **2(b)(1):** "Moral rights ... are not licensed under this Public License, nor are publicity, privacy, and/or other
  similar personality rights". **2(b)(2):** "Patent and trademark rights are not licensed under this Public License."
- **No warranty of title (section 5):** "as-is and as-available", no warranties of "title, ... non-infringement".
- **The deed's Notices:** "The license may not give you all of the permissions necessary for your intended use."
- **The character is not the sculptor's.** The page names the model "Morty Smith [Rick and Morty]" and the author
  made it for "fans of Rick and Morty" (API `name`, `description`). Adult Swim's Rick and Morty page ends "TM & ©
  2026 The Cartoon Network, Inc. All Rights Reserved." (<https://www.adultswim.com/videos/rick-and-morty>); its terms
  link resolves to Warner Bros.' Terms of Use, where content is "protected by copyrights, trademarks ... owned by
  Warner or its licensors" (<https://www.adultswim.com/terms>); Warner Bros. Discovery lists Adult Swim among its
  brands (<https://www.wbd.com/our-brands>).
- Inferred: that notice covers the show's characters; no first-party page we read names Morty Smith's owner in so many
  words. Inferred: the sculpt is fan art; CC BY 4.0 clears the sculptor's own rights in the mesh and nothing else, so
  it cannot grant rights in the character or its name. Committing and publishing Morty-shaped parts rests on a
  judgement about the character's owner that this licence does not settle.

## 4. Anything else on the page

- **No added conditions.** The description tells how the model was sculpted, printed and painted, and links a video;
  it grants and restricts nothing. `remixDescription` is null (API `description`, `summary`, `remixDescription`).
- **Flags:** `excludeCommercialUsage: false`, `license.disallowRemixing: false`, `aiGenerated: false`, `nsfw: false`.
- **Tags:** character, toy, stand, cartoon, figurine, figure, morty, thingiverse; no "fan art" tag. Category "Action
  Figures & Statues". The description ends "Unassociated tags: Adult Swim, Morty Smith, Rick and Morty".
- Not read: the rendered page (comments, any banner) and the author's profile page, both HTTP 403.

## Sources

- Printables GraphQL API, `print(id: "13460")`: <https://api.printables.com/graphql/>; the page it backs, HTTP 403 to
  curl: <https://www.printables.com/model/13460-morty-smith-rick-and-morty>.
- CC BY 4.0 legal code, deed and FAQ: <https://creativecommons.org/licenses/by/4.0/legalcode.en>,
  <https://creativecommons.org/licenses/by/4.0/deed.en>, <https://creativecommons.org/faq/>.
- Adult Swim and Warner Bros. Discovery: <https://www.adultswim.com/videos/rick-and-morty>,
  <https://www.adultswim.com/terms> (redirects to `policies.warnerbros.com`), <https://www.wbd.com/our-brands>.
- Thingiverse, not read (HTTP 403, Cloudflare challenge): <https://www.thingiverse.com/thing:2442056>.
- Earlier local note (never committed): `2026-11-03-morty-3d-model.md`.
