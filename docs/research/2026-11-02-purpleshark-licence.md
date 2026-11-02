# PurpleShark's MakerWorld licences (2026-11-02, #618)

The Mech's mechanism follows PurpleShark's three MakerWorld models: eyes (1718839), pan & tilt (1766064) and mouth
(1861301). #51's survey said MakerWorld's platform licences "forbid sharing". Which licence does each page declare, what
do that licence and MakerWorld's terms say about remodelling, publishing derived CAD/STL/STEP/glTF, renders,
modification, commercial use and attribution, and what does that leave for #51's new neck, jaw and base and for what
the repo publishes today?

All sources read on 2026-11-02. The model pages' HTML is behind a Cloudflare challenge for curl (HTTP 403), so the
licence fields come from MakerWorld's own JSON (`/api/v1/design-service/design/<id>`, the data the page renders) and
were checked against the rendered pages in Chrome. The policy pages were read in Chrome, the wiki with curl. No login,
no download, nothing clicked that changes state. No Creative Commons licence is declared on any of the three, so no CC
legal code applies. Not legal advice: the texts are quoted, and every reading of ours is marked inferred.

## 1. What each page declares

- **All three declare MakerWorld's "Standard Digital File License".** The API returns `"license": "Standard Digital
  File License"` for each, and every page's License panel reads "This user content is licensed under a Standard
  Digital File License." ([1718839](https://makerworld.com/en/models/1718839),
  [1766064](https://makerworld.com/en/models/1766064), [1861301](https://makerworld.com/en/models/1861301);
  API: [1718839](https://makerworld.com/api/v1/design-service/design/1718839),
  [1766064](https://makerworld.com/api/v1/design-service/design/1766064),
  [1861301](https://makerworld.com/api/v1/design-service/design/1861301)).
- **The licence text, identical on all three** (the API's `licenseDescriptionInfo.content`, shown on the page behind
  "more"): "You shall not share, sub-license, sell, rent, host, transfer, or distribute in any way the digital or 3D
  printed versions of this object, nor any other derivative work of this object in its digital or physical format
  (including - but not limited to - remixes of this object, and hosting on other digital platforms). The objects may
  not be used without permission in any way whatsoever in which you charge money, or collect fees." (same API URLs).
- **All three are in MakerWorld's Exclusive Model Program.** The API says `"isExclusive": true`, `"isPaid": false`,
  `"originals": []` (none is itself a remix) and `"allowReCreation": false` on each (same API URLs). Inferred:
  `allowReCreation` is the platform switch for remixes of the model; its meaning is not documented anywhere we read.
- **The designer's own words, the same on all three pages.** Under the licence: "If you want to use this model
  commercially, please join my membership." In the description: "Membership / One tier for all, allowing unlimited
  use." and a copyright line in which the designer, naming herself, says she owns "the copyright to my designs & the
  moral right of the designer has been asserted." Nothing else in the descriptions grants or restricts use
  ([1718839](https://makerworld.com/en/models/1718839), [1766064](https://makerworld.com/en/models/1766064),
  [1861301](https://makerworld.com/en/models/1861301)).

## 2. MakerWorld's own terms around the licence

- **MakerWorld grants nothing in the content itself.** Terms of Use §5 (updated and effective Nov 2nd, 2026):
  "MakerWorld does not grant any licence to the Users for the User Content"; the uploader picks a licence, and "Other
  Users of the Services can access and use the User Content per the Free License selected by you"; the licences "are
  irrevocable after publication" ([Terms of Use](https://makerworld.com/en/user-agreement)). The creator keeps
  copyright: "The User retains any and all IP Rights in the User Content" (same).
- **Exclusive models must use the Standard Digital File License or the MakerWorld Exclusive License.** The Exclusive
  Model Program Agreement §3.4.2 repeats the licence word for word ("Users shall not share, ... "), adds "The creator
  acknowledges that the Standard Digital File Licenses are irrevocably granted to the other users", and says the
  licence "ensures that the Exclusive Model ... [is] protected from unauthorized use by third parties"
  ([Exclusive Model Program Agreement](https://makerworld.com/en/exclusive-model-policy)). The alternative it offers,
  the MakerWorld Exclusive License, would allow "non-commercial derivative works ... published, displayed, shared, and
  distributed exclusively on the MakerWorld Platform", with attribution; these three do not use it (same, §3.4.2(b)).
- **Exclusive models may not appear elsewhere.** "Exclusive Program Models may not be uploaded, shared, or made
  available on any other 3D model platform or channel for the duration of its participation in a Program" (§2.2), and
  a model "directly or indirectly published on other platforms or websites" loses its status and points (§5.5.1).
  MakerWorld may send notices "if a third party 3D model platform is found to be distributing your Exclusive Program
  Model" (§5.3.5) ([Exclusive Model Program Agreement](https://makerworld.com/en/exclusive-model-policy)). The
  exclusive model guideline tells creators to "report any possible theft swiftly"
  ([exclusive model guideline](https://wiki.bambulab.com/en/makerworld/tutorials/exclusive-model-guideline)).
- **The paid membership cannot unlock digital redistribution of an Exclusive model.** The Commercial License
  Membership Agreement §4.2.1 lets creators "modify the Standard Digital File License to permit certain uses ... by
  Subscribers", but "Creators may not authorize Subscribers to sub-license, sell, rent, host, transfer, or distribute
  on or through any third party platform or service ... the Exclusive Program Model, or any derivative work of the
  Exclusive Program Model other than Subscribers' physical 3D printed works"; "Subscribers are free to sell 3D printed
  works" ([Membership Agreement](https://makerworld.com/en/creator-membership-agreement)). The licence period follows
  the subscriber's billing cycle (§5.3.4, same), so it is a paid, time-limited licence.
- **Community rules name the same thing.** Community Guidelines (updated April 27th, 2026) list "Unauthorized
  distribution or sale of others' work" under Intellectual Property
  ([Community Guidelines](https://makerworld.com/en/community-guidelines)); the model upload guidelines forbid
  "Modifying or publishing derivative versions of works released under licenses that prohibit derivatives or
  adaptations" ([model upload guidelines](https://wiki.bambulab.com/en/makerworld/tutorials/model-upload-guidelines)).
- **Scraping.** Terms of Use §9 bars any "robot, spider or other automatic device ... or by any means of artificial
  intelligence service" to "access, acquire, copy, reproduce ... any content" by means "not purposely made available
  through the site" ([Terms of Use](https://makerworld.com/en/user-agreement)). This note read three pages and their
  JSON once each; inferred: the repo should not script against MakerWorld (no fetch of the designer's pages or files in
  CI or tooling).

## 3. Topic by topic

- **Remodelling and modifying.** The licence restricts what you do with the object and its derivatives (share,
  sub-license, sell, rent, host, transfer, distribute, charge money); it does not say "you shall not modify" or "you
  shall not make". Inferred: making a modified or remodelled copy for one's own use is not what the text forbids; what
  is forbidden is passing it on in any form.
- **Publishing derived CAD, STL, STEP, glTF.** Forbidden by the text: no sharing, hosting or distributing "any other
  derivative work of this object in its digital or physical format (including - but not limited to - remixes of this
  object, and hosting on other digital platforms)". Source code that generates the geometry is a digital format of it
  (inferred).
- **Renders on a public website.** Not named in the licence. Inferred: a render or an interactive glTF of the object or
  of a derivative is a "digital ... version" of it shown to the public, so it falls under "share" and "host"; the safe
  reading is that it needs the designer's permission. The Exclusive Agreement's Model Branding License grants MakerWorld
  (not other users) the right to use "photos, drawings, videos, renderings" of the model (§3.4.1), so the platform
  treats renderings as content tied to the model
  ([Exclusive Model Program Agreement](https://makerworld.com/en/exclusive-model-policy)).
- **Commercial and non-commercial.** Commercial use needs permission ("may not be used without permission in any way
  whatsoever in which you charge money, or collect fees"); the designer offers it through her paid membership, which
  for an Exclusive model can cover selling printed parts but never digital redistribution (section 2). Non-commercial
  sharing is not allowed either: the sharing ban does not depend on money.
- **Attribution.** The licence says nothing about attribution (it grants no share right that attribution could be a
  condition of). The designer asserts her moral right (section 1); inferred: keep crediting her wherever the work shows
  up (docs/credits.md already does).

## 4. Do our parametric remodels count as derivatives?

- **No text defines "derivative work".** The licence, the Terms of Use, the Exclusive Model Program Agreement and the
  Membership Agreement use the term without defining it; the licence only gives examples: "including - but not limited
  to - remixes of this object". No Creative Commons licence is declared, so CC's "Adapted Material" definition does not
  apply.
- **The nearest statements.** The Exclusive Agreement treats as "non-original" a "remix or other derivative work of
  existing designs or models with only limited changes made" (§8.2.1(b),
  [Exclusive Model Program Agreement](https://makerworld.com/en/exclusive-model-policy)). The upload guidelines call
  "simplification, scaling, cutting, recoloring, fixing non-manifold geometry, low-poly adjustments, adding or removing
  logos or text, or other minor edits" too minor to be published as a derivative
  ([model upload guidelines](https://wiki.bambulab.com/en/makerworld/tutorials/model-upload-guidelines)). Both speak
  to how little change makes a copy, not to how much change makes something no longer derived.
- **Inferred reading.** model/printed/*.py are written from scratch in CadQuery but to match the designer's parts, part
  for part and dimension for dimension (docs/research/2026-10-31-model.md measures her STLs). Being redrawn rather than
  converted does not appear in any of the texts as an exception; in the licence's plain words such a part is a
  derivative of "this object" in a digital format. Where the line falls in law is copyright law's question, which the
  texts leave open (the Terms of Use choose Singapore law between MakerWorld and its users; the licence itself names
  none).
- **Facts versus form, inferred.** Measurements, ideas and functions (a servo-driven jaw, a pan-tilt stage, an eye on a
  ball joint) are not "this object"; a new part that reaches the same function with its own geometry and its own
  numbers is the furthest from a derivative. A part that reproduces her shapes and sizes is the nearest.

## 5. Verdict per model

SDFL is the Standard Digital File License; "Exclusive" is the Exclusive Model Program. Remodel means for one's own
use; publish means the derived CAD, STL, STEP or glTF; commercial permission comes through the paid membership, which
never covers digital redistribution of an Exclusive model.

| Model | Id | Licence | Remodel | Publish derived files | Renders, public site | Commercial |
| --- | --- | --- | --- | --- | --- | --- |
| Eyes | 1718839 | SDFL, Exclusive | Not forbidden (inferred) | No | Needs permission (inferred) | Permission only |
| Pan-tilt | 1766064 | SDFL, Exclusive | Not forbidden (inferred) | No | Needs permission (inferred) | Permission only |
| Mouth | 1861301 | SDFL, Exclusive | Not forbidden (inferred) | No | Needs permission (inferred) | Permission only |

#51's survey is right for these three: the declared licence forbids sharing the object and any derivative, digital or
printed, commercial or not.

## 6. What this means for #51 and for the repo today

- **Fine as is.** The designer's PDFs and STLs in docs/references/ (gitignored, local only) and the build from her
  files on Cansin's printer: no sharing, no distributing. docs/credits.md links to her pages and redistributes nothing.
  The repo's own licence (PolyForm Noncommercial 1.0.0) covers only what the repo owns; it cannot license her design to
  anyone (inferred).
- **In conflict with the licence's plain words (inferred).** What the repo publishes publicly that reproduces her
  parts: model/printed/*.py (CadQuery parts written to match her eyeball, lids, brackets, jaws, pan turntable, base
  plate and the rest), the GLBs on the site's /viewer, the Blender pictures in the README and on the site, and the
  STLs, GLBs and pictures CI uploads as workflow artefacts (`ours`, `convex-*`, `viewer`, `images-*`, `preview` in
  checks.yml; inferred: downloadable from a public repo's runs). Each is a "digital ... version" or "derivative work of this object", shared or hosted on a
  platform other than MakerWorld.
- **Dimensions in research notes (inferred).** docs/research/2026-10-31-model.md and others quote numbers measured from
  her STLs. Numbers are facts, not the object, and quoting them shares no file; lower risk than the parts, but together
  with the parts' code they are the recipe for the same shapes.
- **#51's new neck, jaw and base (inferred).** New parts of our own design sit outside "this object" to the degree they
  do not copy it: start from our own requirements (servo, loads, the build's measured clearances), our own geometry and
  our own numbers, and use her parts only as the reference for what has to fit. Where a new part must mate with one of
  hers (her eye bracket, say), the interface sizes are facts; the rest of her part should not be reproduced. A new
  neck, jaw and base drawn this way is the strongest position the texts allow; it leaves the other reproduced parts
  (eyes, lids, brackets) in the conflict above until one of the ways out below settles them.
- **Ways out, by the texts.** (a) Ask the designer in writing for permission to publish the remodels, renders and
  viewer; the licence's own wording ("without permission") contemplates permission, but for an Exclusive model her
  agreement with MakerWorld bars "directly or indirectly" publishing elsewhere (§5.5.1), so she may not be able to say
  yes without leaving the programme (inferred). (b) Replace every reproduced part with our own design (#51's
  direction, extended to the eyes). (c) Stop publishing the reproductions (make the parts' code, GLBs, renders and STL
  artefacts non-public). The paid membership is no way out: it cannot cover digital redistribution of an Exclusive
  model, and noggin takes no paid tier.

## Sources not reached

- None of the primary sources failed. The model pages' HTML returned 403 (Cloudflare) to curl; their content was read
  from MakerWorld's JSON API and in Chrome instead. The Exclusive Agreement refers to a "MakerWorld license page" that
  describes the Standard Digital File License (§2.11); no such standalone page was found, and the agreement and the
  model pages quote the text in full.
