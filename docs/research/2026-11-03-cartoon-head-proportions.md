# Average head proportions of American adult-animation characters (2026-11-03)

A realistic skeleton warped to "average cartoon" proportions needs target ratios: how tall a cartoon head is for its
width, where its eyes, mouth and jaw sit, how big the eyes are, and how much neck and torso shows. This note measures 14
characters from The Simpsons, Rick and Morty, American Dad!, Futurama and Family Guy, averages them, and turns the
average into millimetres for a bust head limited to 140 W × 120 D × 150 H.

All images read on 2026-11-03. Nothing was copied into the repo; each image is cited by URL. Every number here is
**estimated**: read by eye from a pixel grid laid over the image (lines every 5 to 50 source pixels), so each ratio is
good to about ±0.03. The licence of the art is the studios'; this is measurement for research only.

## 0. Sources, and how primary they are

No studio or creator site publishes front-view model sheets for these shows (searched: Fox, Adult Swim, the shows'
own sites, the studios). What exists, best first:

- **Model sheets (Rick and Morty).** Starburns Industries model sheets, with the studio's logo and the show's, front
  view beside the turnaround. Hosted on the Rick and Morty fandom wiki, not on a studio page.
  - Rick: <https://rickandmorty.fandom.com/wiki/File:Rick_model_sheet.jpg>
    (image <https://static.wikia.nocookie.net/rickandmorty/images/5/5e/Rick_model_sheet.jpg>)
  - Morty: <https://rickandmorty.fandom.com/wiki/File:Morty_model_sheet.jpg>
    (image <https://static.wikia.nocookie.net/rickandmorty/images/9/9e/Morty_model_sheet.jpg>)
- **Screen frames (The Simpsons).** The show almost never draws its characters face-on (they live in three-quarter
  view); the Simpsons wiki keeps the rare front-facing frames. These are broadcast frames, so primary for the look, but
  each is one drawing, not a model.
  - Homer, season 35 episode 7: <https://simpsons.fandom.com/wiki/File:35x7_Front_face_Homer.png>
  - Marge, 35x2: <https://simpsons.fandom.com/wiki/File:35x2_Front_face_Marge.png>
  - Lisa, 32x4: <https://simpsons.fandom.com/wiki/File:32x4_Front_face_Lisa.png>
  - Bart (low resolution, titled "odd", so off-model): <https://simpsons.fandom.com/wiki/File:An_Odd_Front_Facing_Bart_Simpson.jpg>
  - Homer three-quarter, for the protruding eye: <https://simpsons.fandom.com/wiki/File:Turnaround.jpg>
  - Marge and Bart three-quarter, same: <https://simpsons.fandom.com/wiki/File:24x20_Bart_front_face.png>
- **Publicity art (American Dad!, Family Guy).** The infobox images on the wikis carry Fox press-kit file names
  (`AmericanDad_09_Stan_v1F.jpg`, `FamilyGuy_Single_PeterDrink_R7.jpg`); inferred to be Fox publicity art. All are
  three-quarter views, so widths are foreshortened (vertical ratios hold).
  - Stan: <https://static.wikia.nocookie.net/americandad/images/0/0d/AmericanDad_09_Stan_v1F.jpg>
  - Steve: <https://static.wikia.nocookie.net/americandad/images/1/17/AmericanDad_09_Steve_v1F.jpg>
  - Roger: <https://static.wikia.nocookie.net/americandad/images/b/b9/AmericanDad_09_Roger_v1F.jpg>
  - Peter: <https://static.wikia.nocookie.net/familyguy/images/a/aa/FamilyGuy_Single_PeterDrink_R7.jpg>
  - Stewie: <https://static.wikia.nocookie.net/familyguy/images/9/90/FamilyGuy_Single_StewieBackpack_R7.jpg>
- **Character art (Futurama).** The Futurama wiki's character-page art, origin unstated, three-quarter view, low
  resolution (about 160 × 490 px).
  - Fry: <https://static.wikia.nocookie.net/enfuturama/images/4/4c/Character_Fry.png>
  - Leela: <https://static.wikia.nocookie.net/enfuturama/images/3/3d/Character_Leela.png>
  - Bender: <https://static.wikia.nocookie.net/enfuturama/images/3/3d/Character_Bender.png>

Gaps: no front view was found for any American Dad!, Futurama or Family Guy character, and no Simpsons model sheet.
A front-view pass from the shows' art books (e.g. *The Art of Futurama*) would tighten those rows.

## 1. Definitions

- **H**: head height, top of the skull to the bottom of the chin. Hair is left out (Rick's spikes, Lisa's star points,
  Fry's quiff); where hair hides the skull (Marge, Lisa, Fry, Leela) the hairline or the base of the hair stands in,
  marked inferred.
- **W**: head width at its widest, ears left out. In three-quarter views it is the visible width (foreshortened).
- **Eye centre**: height of the eye's centre above the chin, as a fraction of H.
- **Eye D/W**: one eye's outer diameter (the white plus its outline) over W. Rick's and Bender's eyes are wider than
  tall; the width is used.
- **Gap/W**: the clear gap between the two eyes' inner edges, over W (0 = the eyes touch).
- **Mouth**: height of the mouth line (closed mouth) or the opening's centre above the chin, over H.
- **Cranium**: H above the eye centre, over H (so eye centre + cranium = 1).
- **Neck W, neck L**: visible neck width over W, visible neck length (chin to collar) over H.
- **Torso**: shoulder line to waist (belt), over H.
- **Ear**: ear centre above the chin, over H; the stand-in for the jaw hinge (section 4).

## 2. Per character (all estimated)

| Character | View | H/W | Eye centre | Eye D/W | Gap/W | Mouth | Cranium | Neck W | Neck L | Torso | Ear |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Bart | front, low-res, off-model | 1.56 | 0.43 | 0.38 | 0.26 | 0.18 | 0.57 | – | 0 | 0.61 | – |
| Homer | front frame | 1.79 | 0.54 | 0.42 | 0.13 | 0.18 | 0.46 | 0.71 | 0.10 | – | 0.43 |
| Lisa | front frame | 1.07 (inferred skull) | 0.46 | 0.30 | 0.10 | 0.11 | 0.54 | 0.54 | 0.12 | – | 0.29 |
| Marge | front frame | – (skull under hair) | 0.63 | 0.45 | 0.06 | 0.08 | 0.37 (to hairline) | 0.62 | 0.29 | – | 0.34 |
| Rick | model sheet front | 1.49 | 0.61 | 0.47 | 0 | 0.28 | 0.39 | 0.45 | 0.05 | 1.40 | – |
| Morty | model sheet front | 1.09 | 0.51 | 0.32 | 0.09 | 0.17 | 0.49 | 0.55 | 0 | 1.17 | 0.33 |
| Stan | press art, ¾ | 1.2 | 0.67 | 0.25 | 0 | 0.42 | 0.33 | – (collar) | – | 1.40 | 0.53 |
| Steve | press art, ¾ | 1.1 | 0.57 | 0.38 (lens) | 0.05 | 0.28 | 0.43 | 0.29 | 0.07 | 0.83 | 0.37 |
| Roger | press art, ¾ | 1.08 | 0.42 | 0.29 | 0.06 | 0.06 | 0.58 | 0.25 | 0.09 | – | – |
| Fry | wiki art, ¾ | 1.24 | 0.48 | 0.32 | 0 | 0.14 | 0.52 | 0.44 | 0.14 | 1.30 | 0.43 |
| Leela | wiki art, ¾ | 1.2 | 0.59 | one eye, 0.6 | – | 0.15 | 0.41 | 0.49 | 0.18 | 1.00 | 0.35 |
| Bender | wiki art, ¾ | 1.62 | 0.43 | 0.36 | 0 | 0.14 | 0.57 | – | 0.12 | 1.20 | – |
| Peter | press art, ¾ | 1.46 | 0.77 | 0.25 | 0.09 | 0.34 | 0.23 | 0 | 0 | 1.36 | 0.83 |
| Stewie | press art, ¾ | 0.63 | 0.43 | 0.19 | 0.24 | 0.21 | 0.57 | 0 | 0 | 0.45 (inferred) | 0.32 |

Whole-figure heights, for scale: Rick 5.1 heads, Leela 5.2, Fry 4.4, Stan 3.7, Morty 3.6, Bender 3.5, Peter 3.3,
Steve 2.7, Roger 2, Stewie 1.6.

## 3. Average and range

Over the rows above with a value (Leela's single eye left out of eye size and gap):

| Ratio | Mean | Median | Range | n |
|---|---|---|---|---|
| H/W | 1.27 | **1.20** | 0.63 (Stewie) to 1.79 (Homer) | 13 |
| Eye centre above chin, /H | 0.54 | **0.53** | 0.42 (Roger) to 0.77 (Peter) | 14 |
| Eye D/W | 0.34 | **0.32** | 0.19 (Stewie) to 0.47 (Rick) | 13 |
| Gap between eyes /W | 0.08 | **0.06** | 0 (Rick, Stan, Fry, Bender) to 0.26 (Bart, off-model) | 13 |
| Mouth above chin, /H | 0.20 | **0.17** | 0.06 (Roger) to 0.42 (Stan) | 14 |
| Cranium above eye centre, /H | 0.46 | **0.47** | 0.23 (Peter) to 0.58 (Roger) | 14 |
| Neck W /W | 0.48 | **0.49** | 0.25 (Roger) to 0.71 (Homer) | 9 |
| Neck L /H | 0.09 | **0.09** | 0 (Morty, Peter, Stewie, Bart) to 0.29 (Marge) | 13 |
| Torso (shoulder to waist) /H | 1.07 | **1.19** | 0.45 (Stewie) to 1.40 (Rick, Stan) | 10 |
| Ear centre above chin, /H | 0.42 | **0.36** | 0.29 (Lisa) to 0.83 (Peter) | 10 |

The median is the better "average" here: Stewie, Peter and the off-model Bart pull the means. Against a real adult
(artists' canon, uncited: H/W about 1.3, eyes at half the head, eye about 0.2 W, one eye's width between them, mouth
about 0.3 H above the chin) the cartoon average keeps the head shape and the eye line, but **the eyes grow to about
1.6× and close up to a third of the gap, the mouth drops to a sixth of the head, and the neck all but disappears**.

## 4. Eyes, overbite and chin, by show

- **The Simpsons.** Eyes are large discs set on the head's outline; in three-quarter view the far eye **protrudes past
  the head outline** (Homer in `Turnaround.jpg`, Marge and Bart in `24x20_Bart_front_face.png`), and face-on they sit
  flush with it (Homer's outer eye edge is within 4 px of the cranium). Mouths sit very low (0.08 to 0.18 H) with an
  **overbite**: the upper lip or muzzle overhangs and there is next to no chin (Marge, Lisa, Bart). Homer's mouth sits
  in a stubbled muzzle 0.41 H tall and 0.85 W wide that stands in for the whole jaw.
- **Futurama.** Same Groening family: eyes are discs that **protrude past the outline** in three-quarter (Fry's near
  eye pokes past the brow line; Leela's single eye breaks the face outline; Bender's eyes sit in a visor that juts out
  of his cylinder). Fry has a long **jutting chin** with the mouth well above it; Leela has full lips and a short chin;
  Bender's jaw is a grille the full head width.
- **Rick and Morty.** Eyes stay inside the outline. Rick's eyes touch and fill nearly half the head's width; Morty's
  are round, a tenth of W apart. Chins are rounded, no overbite; the mouth sits higher on Rick (0.28 H).
- **American Dad!** Stan: a **huge square chin**, the jaw 0.57 H tall and wider than the cranium, eyes high (0.67) and
  touching. Steve: a small, stubbled chin under a wide grin. Roger: a long snout, mouth almost at the chin (0.06).
- **Family Guy.** Peter: a pear-shaped head with the eyes very high (0.77), a **cleft "butt" chin**, no neck.
  Stewie: a rugby-ball head wider than tall (H/W 0.63), eyes far apart, no neck.

## 5. The average head in millimetres (140 W × 120 D × 150 H)

H governs: at the median H/W of 1.2, a 150 mm head is **125 mm wide**, inside the 140 mm limit (filling 140 W would
need 168 H). Measured from the chin, at the medians:

| Feature | Ratio | mm |
|---|---|---|
| Head | H 150, W 150 / 1.2 | **150 H × 125 W** (inside 120 D) |
| Eye centre | 0.53 H | **80 mm above the chin**, 70 mm below the crown |
| Eye diameter, each | 0.32 W | **40 mm** (range 0.19 to 0.47 W: 24 to 59 mm) |
| Gap between the eyes | 0.06 W | **7.5 mm**, so the eye centres sit **47.5 mm apart** and the pair spans 87.5 mm |
| Eye top and bottom | | 100 mm and 60 mm above the chin |
| Mouth line | 0.17 H | **26 mm above the chin** |
| Jaw hinge | ear height, 0.36 H | **about 54 mm above the chin**, at the back of the head (inferred, below) |
| Neck | 0.49 W, 0.09 H | **61 mm wide, about 14 mm visible** |
| Visible torso, shoulder to waist | 1.19 H | about 178 mm (outside the head envelope) |

The jaw hinge is inferred: none of the drawings shows a hinge. A real temporomandibular joint sits just in front of
the ear, so the ear's height (median 0.36 H) stands in for it. At 54 mm it falls between the mouth (26 mm) and the
eyes' lower edge (60 mm), which leaves a 6 mm band under the eyes for the hinge axle. A jaw that drops from there
moves everything below 54 mm, mouth and chin, the way Homer's muzzle or Stan's chin moves as one block.

Two 40 mm eyeballs in a 120 mm deep head leave 80 mm of depth behind their front faces; sitting them so they stand
proud of the face outline by a few millimetres gives the Simpsons and Futurama look (section 4).

## 6. Confidence

- Rick and Morty: front-view model sheets, best data.
- Simpsons: single broadcast frames, front view; Bart's is low resolution and off-model, so his gap (0.26) is an
  outlier; Marge's and Lisa's skulls are hidden by hair.
- American Dad!, Futurama, Family Guy: three-quarter views. Heights and vertical positions hold; widths (H/W, eye D/W,
  gap) are foreshortened, so their H/W reads high and eye sizes read low. Futurama images are about 160 px wide, so
  each pixel is about 1 % of the head.
