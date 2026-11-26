# Bambu filament colours for the theme dropdowns (2026-11-03)

> [!NOTE]
> **Superseded picks.** Cansin picked the Themes' filaments on 2026-11-03 (#805, docs/adr/0022); they replace §3's
> proposals and live in the model (model/geometry.py `THEMES`, the Themes page). Where they differ: realistic's Linkages
> are PETG Basic Red (30201), not PETG-CF Brick Red; mechanical is PETG Matte Gray Bones, Basic Black Joints, Basic Gray
> Linkages and Basic Black Mounts, no PETG-CF; morty's face is PLA Basic Beige (10201) and his eye whites PLA Basic
> Jade White (10100); bart's face is PLA Basic Sunflower Yellow (10402), his shirt PLA Matte Scarlet Red (11200), his
> eye whites PLA Matte Ivory White (11100) and his pupils PLA Matte Charcoal (11101). The catalogue (§1, §2) stands.

The Mech's docs, Viewer and pictures get theme dropdowns. A theme is one **Skeleton** (realistic | mechanical,
PETG) and one **Skin** (morty | bart, PLA Shells). Each Skeleton uses up to 4 PETG colours and each Skin up to 4 PLA
colours. Which real Bambu Lab filaments come closest to each, which are sold in the US store, and which does Cansin
already own?

The mapping, confirmed in the repo: "realistic" is the Skeleton drawn as Bones (GLOSSARY "Bone", ADR 0020,
`mech-back`), "mechanical" the same parts drawn plain (`mech-back-plain`), so the colours below suit organic
Bones and boxy plain parts respectively.

Read on 2026-11-03. Every hex comes from Bambu: its colour-code file in BambuStudio and the "Hex Code" tables linked
from each store product page; the two agree everywhere checked. Distances are CIEDE2000 (ΔE00; about 2 is barely
visible side by side, above about 10 the colours read as different), computed by us from the hexes (sRGB, D65). A
filament's hex is Bambu's own nominal, not a measured print.

## 0. How the sources were reached, and the US gap

- **Bambu's colour data.** `filaments_color_codes.json` in BambuStudio gives each colour code (e.g. 17300), line,
  English name and hex ([file at 804d93b, 2026-09-22](https://github.com/bambulab/BambuStudio/blob/804d93bb5de142c48c0dabedba87736ea9553206/resources/profiles/BBL/filament/filaments_color_codes.json)).
  It also lists lines no longer sold (PLA Lite, PLA Tough, PLA Silk, PLA Dynamic, PETG HF), so what is on sale comes
  from the store.
- **The store's hex tables, read for the picked lines:**
  [PETG Basic](https://store.bblcdn.com/s7/default/7260019fb4b243ce9b1963d51fc24e83/PETG_Basic_Hex_Code_Table.pdf),
  [PETG Matte](https://store.bblcdn.com/s7/default/9b109944ad61471eb35d46e6263a28ff/Bambu_PETG_Matte_Hex_Code_Table.pdf),
  [PETG-CF](https://store.bblcdn.com/s7/default/2b5c536e5f824b6d80484c3bcfdfbb17/PETG-CF_Hex_Code_Table.pdf),
  [PLA Basic](https://store.bblcdn.com/s7/default/1084369ef84345bbaa5d704a492954e0/Bambu_PLA_Basic_Hex_Code.pdf),
  [PLA Matte](https://cdn.shopify.com/s/files/1/0584/7236/6216/files/Bambu_PLA_Matte_Hex_Code.pdf?v=1745547424),
  [PLA Tough+](https://store.bblcdn.com/s1/default/3d989ddc07694c378496784834947125/Bambu_PLA_Tough_Hex_Code_Table.pdf).
  Every hex in them matches the JSON.
- **The line-up, stock and prices** come from the EU store: its listing
  ([PETG](https://eu.store.bambulab.com/collections/bambu-lab-3d-printer-filament?By+Material=PETG&page=1), one page;
  [PLA](https://eu.store.bambulab.com/collections/bambu-lab-3d-printer-filament?By+Material=PLA&page=1), two pages)
  and the schema.org `ProductGroup` data on each product page (`/products/<handle>`, linked per line below). Every
  EU page names the US twin as its `hreflang="en-US"` alternate (`us.store.bambulab.com/products/<handle>`).
- **The US store could not be read live.** `us.store.bambulab.com` answers every page, collection and sitemap with a
  Cloudflare `302` to `eu.store.bambulab.com` for this machine's location, from curl, from Chrome and from WebFetch
  alike (only `/robots.txt` and `/sitemap.xml` load). The Internet Archive was offline. So **US availability and
  USD prices below come from US search-index snapshots of the US product pages (marked "US snapshot"), not from a
  live page**: their dates vary and some are months old. **Unverified until someone opens the US links from a US
  connection.** Where the snapshots say nothing, the cell reads "unverified".

## 1. PETG catalogue (EU listing: Basic, Matte, Translucent, CF; HF only in the US)

Prices per 1 kg; EU stock as on 2026-11-03.

| Line | Colour (code): hex | EU | US snapshot |
|---|---|---|---|
| [PETG Basic](https://eu.store.bambulab.com/products/petg-basic) | Black (30105) #000000, White (30106) #FFFFFF, Gray (30107) #7F7E83, Red (30201) #D6001C, Yellow (30402) #FCE300, Reflex Blue (30603) #001489, Navy Blue (30604) #0086D6, Misty Blue (30108) #688197, Dark Brown (30800) #4F2C1D, Orange (30301) #FF671F, Green (30502) #009639, Pine Green (30503) #034638, Dark Beige (30403) #DBC8B6 | all 13 in stock, €15.99 refill / €18.99 spool | [listed](https://us.store.bambulab.com/products/petg-basic), MSRP $13.99, 13 colours; Dark Beige (30403) $16.99 spool / $13.99 refill on the [bulk-sale page](https://us.store.bambulab.com/pages/promotions/filament-bulk-sale?tab=PETG+Basic); one older snapshot calls PETG Basic discontinued with old codes (30101 Black, 30102 Gray), a newer one lists Gray as 30107 (the current code), so the old generation was replaced: unverified |
| [PETG Matte](https://eu.store.bambulab.com/products/petg-matte) | White (35100) #FFFFFF, Black (35101) #000000, Gray (35102) #7F7E83, Lime (35500) #C0DF16, Avocado Green (35501) #BCE194, Pink (35700) #FABBCB, Baby Blue (35600) #B9D9EB, Violet (35702) #A7A4E0 | all in stock (Pink refill out), €15.99 / €18.99 | [listed](https://us.store.bambulab.com/products/petg-matte), $13.99 refill / $16.99 spool, 8 colours; White (35100) on the printer pages |
| [PETG Translucent](https://eu.store.bambulab.com/products/petg-translucent) | Clear (32101), Gray (32100) #8E8E8E, Light Blue (32600) #61B0FF, Teal (32501) #77EDD7, Olive (32500) #748C45, Orange (32300) #FF911A, Purple (32700) #D6ABFF, Brown (32800) #C9A381, Pink (32200) #F9C1BD (all at 50% alpha in the JSON) | in stock, €16.99 / €19.99 | [listed](https://us.store.bambulab.com/products/petg-translucent), $15.99 / $18.99, 8 colours |
| [PETG-CF](https://eu.store.bambulab.com/products/petg-cf) | Black (31100) #000000, Titan Gray (31101) #565656, Brick Red (31200) #9F332A, Indigo Blue (31600) #324585, Malachite Green (31500) #16B08E, Violet Purple (31700) #583061 | Black, Violet Purple, Brick Red in stock; Indigo, Malachite, Titan Gray out; €35.99 spool | [listed](https://us.store.bambulab.com/products/petg-cf), all six colours, $34.99 spool, Titan Gray $31.99 refill |
| PETG HF (not on the EU listing; `/products/petg-hf` redirects to PETG Matte) | Orange #F75403, Blue #002E96, Lake Blue #1F79E5, Gray #ADB1B2, Dark Gray #515151, Green #00AE42, Lime Green #6EE53C, Forest Green #39541A, Black #000000, Peanut Brown #875718, Red #BC0900, White #FFFFFF, Yellow #FFD00B, Cream #F9DFB9 (JSON) | not sold | [listed](https://us.store.bambulab.com/products/petg-hf) but "discontinued", not restocked once sold out, many colours out of stock |

The PETG-CF page: "PETG-CF requires a more wear-resistant hardened steel nozzle", 0.6 mm recommended, no AMS lite
([PETG-CF](https://eu.store.bambulab.com/products/petg-cf)). PETG Basic: "Compatible with all printers, AMS, build
plate, and nozzles" ([PETG Basic](https://eu.store.bambulab.com/products/petg-basic)).

**PETG has no metallic.** No PETG line sold has a silk, metal or sparkle finish; the metallic finishes are PLA only
(PLA Metal, Silk+, Sparkle below). The nearest PETG to chrome is the discontinued PETG HF Gray (#ADB1B2, ΔE 4.7 from
silver #C0C0C0); the lightest neutral grey still sold is PETG Basic/Matte Gray #7F7E83 (ΔE 20.4 from silver: it
reads as steel, not chrome).

## 2. PLA catalogue (every line on the EU listing)

Single-colour lines; prices per 1 kg spool (refill where sold). Hexes from the JSON, cross-checked against the hex
tables listed in §0 for Basic, Matte and Tough+.

| Line | Colours (code) hex; EU stock |
|---|---|
| [PLA Basic](https://eu.store.bambulab.com/products/pla-basic-filament) (€16.99 refill / €19.99 spool) | Jade White (10100) #FFFFFF, Beige (10201) #F7E6DE, Light Gray (10104) #D1D3D5, Silver (10102) #A6A9AA, Gray (10103) #8E9089, Dark Gray (10105) #545454, Black (10101) #000000, Magenta (10202) #EC008C, Pink (10203) #F55A74, Hot Pink (10204) #F5547C, Orange (10300) #FF6A13, Pumpkin Orange (10301) #FF9016, Gold (10401) #E4BD68, Sunflower Yellow (10402) #FEC600, Yellow (10400) #F4EE2A, Bright Green (10503) #BECF00 (out), Bambu Green (10501) #00AE42, Mistletoe Green (10502) #3F8E43, Bronze (10801) #847D48, Cocoa Brown (10802) #6F5034 (spool out, refill in), Brown (10800) #9D432C, Maroon Red (10205) #9D2235, Red (10200) #C12E1F, Turquoise (10605) #00B1B7, Cyan (10603) #0086D6, Blue (10601) #0A2989, Cobalt Blue (10604) #0056B8, Purple (10700) #5E43B7, Indigo Purple (10701) #482960, Blue Grey (10602) #5B6579 |
| [PLA Matte](https://eu.store.bambulab.com/products/pla-matte) (€16.99 / €19.99) | Ivory White (11100) #FFFFFF, Bone White (11103) #CBC6B8, Desert Tan (11401) #E8DBB7, Latte Brown (11800) #D3B7A7 (out), Caramel (11803) #AE835B (out), Terracotta (11203) #B15533, Dark Brown (11801) #7D6556, Dark Chocolate (11802) #4D3324, Lilac Purple (11700) #AE96D4, Sakura Pink (11201) #E8AFCF, Mandarin Orange (11300) #F99963, Lemon Yellow (11400) #F7D959 (out), Plum (11204) #950051 (out), Scarlet Red (11200) #DE4343, Dark Red (11202) #BB3D43, Dark Green (11501) #68724D, Grass Green (11500) #61C680, Apple Green (11502) #C2E189, Ice Blue (11601) #A3D8E1, Sky Blue (11603) #56B7E6 (out), Marine Blue (11600) #0078BF, Dark Blue (11602) #042F56, Ash Gray (11102) #9B9EA0, Nardo Gray (11104) #757575, Charcoal (11101) #000000 |
| [PLA Pure](https://eu.store.bambulab.com/products/pla-pure) (€18.99 / €21.99) | Pure White (17100) #FFFFFF, Absolute Black (17101) #000000, Milky Pink (17200) #F7CED7, Apricot (17300) #FFB673, Baby Blue (17600) #A4DBE8; all in stock |
| [PLA Tough+](https://eu.store.bambulab.com/products/pla-tough-upgrade) (€23.99 / €26.99) | White (12107) #FFFFFF, Gray (12105) #AFB1AE, Silver (12106) #959698, Black (12104) #000000, Yellow (12401) #F4D53F, Orange (12301) #DC3A27, Cyan (12601) #009BD8 |
| [PLA Silk+](https://eu.store.bambulab.com/products/pla-silk-upgrade) (€19.99) | White (13110) #FFFFFF, Silver (13109) #C8C8C8, Titan Gray (13108) #5F6367, Gold (13405) #F4A925, Champagne (13404) #F3CFB2, Rose Gold (13206) #BA9594, Pink (13207) #F7ADA6, Candy Red (13205) #D02727, Candy Green (13506) #018814, Mint (13507) #96DCB9, Blue (13604) #008BDA, Baby Blue (13603) #A8C6EE, Purple (13702) #8671CB |
| [PLA Metal](https://eu.store.bambulab.com/products/pla-metal) (€27.99) | Iron Gray Metallic (13100) #43403D, Iridium Gold Metallic (13400) #B39B84 (the only one in stock), Copper Brown Metallic (13800) #AA6443, Cobalt Blue Metallic (13600) #39699E, Oxide Green Metallic (13500) #1D7C6A |
| [PLA Sparkle](https://eu.store.bambulab.com/products/pla-sparkle) (€27.99) | Onyx Black (13101) #2D2B28, Slate Gray (13102) #8E9089, Classic Gold (13402) #CEA629 in stock; Alpine Green #3F5443, Crimson Red #792B36, Royal Purple #483D8B out |
| [PLA Translucent](https://eu.store.bambulab.com/products/pla-translucent) (€19.99) | Red #B50011, Cherry Pink #F5B6CD, Orange #F74E02, Mellow Yellow #F5DBAB, Light Jade #96D8AF, Ice Blue #B8CDE9, Blue #0047BB, Teal #009FA1, Purple #8344B0, Lavender #B8ACD6 (all 50% alpha) |
| [PLA Wood](https://eu.store.bambulab.com/products/pla-wood) (€27.99) | Black Walnut #4F3F24, Rosewood #4C241C, Clay Brown #995F11, Classic Birch #918669, White Oak #D6CCA3, Ochre Yellow #C98935 |
| [PLA Marble](https://eu.store.bambulab.com/products/pla-marble) (€27.99) | White Marble #F7F3F0, Red Granite #AD4E38 (out) |
| [PLA Galaxy](https://eu.store.bambulab.com/products/pla-galaxy) (€27.99) | Purple #594177, Green #3B665E, Nebulae #424379, Brown #684A43 (out) |
| [PLA Glow](https://eu.store.bambulab.com/products/pla-glow) (€27.99) | Glow Orange #FF9D5B, Blue #7AC0E9, Green #A1FFAC, Pink #F17B8F, Yellow #F8FF80 (out) |
| [PLA-CF](https://eu.store.bambulab.com/products/pla-cf) (€29.99) | Black #000000, Lava Gray #4D5054, Burgundy Red #951E23, Jeans Blue #6E88BC, Royal Blue #2842AD, Matcha Green #5C9748, Iris Purple #69398E |
| [PLA Aero](https://eu.store.bambulab.com/products/pla-aero) (€28.79) | White #FFFFFF, Gray #CDCECA |
| Multi-colour: [Basic Gradient](https://eu.store.bambulab.com/products/pla-basic-gradient), [Silk Multi Color](https://eu.store.bambulab.com/products/pla-silk-multi-color) (€27.99) | two- to four-hue spools; none fits a flat cartoon colour, so left out of the matching |

US: every line above has a US product page in the search index (e.g. [PLA Pure](https://us.store.bambulab.com/products/pla-pure),
[PLA Matte](https://us.store.bambulab.com/products/pla-matte), [PLA Tough+](https://us.store.bambulab.com/products/pla-tough-upgrade),
[PLA Basic](https://us.store.bambulab.com/products/pla-basic-filament)); per-colour US stock only for the picks, §3.

## 3. Proposals

### Character references

No studio style guide or official hex was found for either character; fan palettes disagree (the often-quoted
"Simpsons yellow" #FFD90F has no official source). So we sampled the flat fills of each character's lead image on
English Wikipedia, read pixel by pixel in the browser, most frequent exact colour per region:

- **Bart**: [File:Bart_Simpson_200px.png](https://en.wikipedia.org/wiki/File:Bart_Simpson_200px.png), credited to
  Twentieth Century Fox (official art). Face #FED41D, shirt #F14E28, shorts #009DDC, eye whites #FFFFFF, pupils
  #000000.
- **Morty**: [File:Morty_Smith.png](https://en.wikipedia.org/wiki/File:Morty_Smith.png), credited to Adult Swim's
  character, sourced via fanart.tv, so **unverified as official art**. Face #E6B794, hair #845628, shirt #E9DB68 (a
  plain yellow T-shirt; its neckline is the same yellow), trousers #354868, eye whites #FFFFFF, pupils #000000
  (small dots).

The anatomical and robot targets for the Skeletons have no primary source: they are our own picks (silver #C0C0C0
and brown #A52A2A are the CSS named colours; bone #E3DAC9, cartilage #D8E4E8, gunmetal #2C3539 and steel #71797E are
inferred) and serve only to rank candidates.

### Skeleton part types (shared by both Skeletons)

From `model/printed/__init__.py`, four groups by role:

1. **Bones (structure)**: Torso, gimbal frame, head mount, neck mount, jaw, test stand.
2. **Joints (the turning cradles and balls)**: yaw yokes, pan yoke, eyeball cores, bail.
3. **Linkages (tendons and muscles that pull)**: tie-bar, push-rods, pitch bar, lid bar, lid link, upper and lower
   lids, pan bar, tilt bar, jaw bar.
4. **Mounts (electronics)**: board rack.

### a. Skeleton "realistic" (Bones), 4 PETG

| Group | Pick | Hex | ΔE00 to target | Why | US snapshot |
|---|---|---|---|---|---|
| Bones | PETG Basic Dark Beige (30403) | #DBC8B6 | 5.9 from bone ivory | the only warm off-white PETG on sale; PETG HF Cream #F9DFB9 is 8.0 off and discontinued | $16.99 spool / $13.99 refill (bulk-sale page) |
| Joints (cartilage) | PETG Matte White (35100) | #FFFFFF | 8.0 from cartilage | the matte finish reads as cartilage, not plastic; Matte Baby Blue #B9D9EB (7.7) is the alternative for bluish cartilage | listed (printer pages, $16.99) |
| Linkages (muscle) | PETG-CF Brick Red (31200) | #9F332A | 2.2 from muscle red | closest by far, and CF is stiffer for rods; it needs a hardened-steel nozzle (0.6 mm recommended). Without one: PETG Basic Red #D6001C, 9.4 off, brighter | $34.99 spool |
| Mounts | black PETG (owned) | #000000 | n/a | hidden behind the head; costs nothing | n/a |

### b. Skeleton "mechanical" (plain), 4 PETG (3 used)

The plain boxes and cylinders suit a robot-film endoskeleton (T-800 chrome and gunmetal). PETG cannot do chrome (§1),
so the look leans gunmetal with steel moving parts:

| Group | Pick | Hex | ΔE00 to target | Why | US snapshot |
|---|---|---|---|---|---|
| Bones | PETG-CF Titan Gray (31101) | #565656 | 12.5 from gunmetal | nothing closer is sold (PETG HF Dark Gray #515151, 11.0, is discontinued); the CF's matte, slightly sparkly finish reads as machined metal. Hardened nozzle. EU out of stock today | $34.99 spool / $31.99 refill |
| Linkages (piston rods) | PETG Basic Gray (30107) | #7F7E83 | 5.5 from steel; 20.4 from chrome | the lightest neutral grey PETG on sale; Basic's gloss over Matte's (same hex) for a little sheen (inferred) | listed as 30107 on printer pages; price unverified |
| Joints, mounts | black PETG (owned) | #000000 | n/a | dark bearings and hydraulics between the grey parts | n/a |

A fourth colour isn't needed. If chrome matters more than availability, PETG HF Gray #ADB1B2 (4.7 from silver) is
the only near-chrome PETG, US only and discontinued.

### c. Skin "morty", 4 PLA

Morty's six Shell parts in four colours: the lids take the face colour, and the pupils take the hair brown.

| Group (parts) | Pick | Hex | ΔE00 to reference | US snapshot |
|---|---|---|---|---|
| Face (head, ears, nose, lids) | PLA Pure Apricot (17300), owned | #FFB673 | 8.1 | listed, $16.99 refill / $19.99 spool |
| Hair and pupils | PLA Basic Cocoa Brown (10802) | #6F5034 | hair 6.7; pupils 29.7 from black | $18.99 spool / $15.99 refill (bulk-sale page, older) |
| Shirt and collar | PLA Matte Lemon Yellow (11400) | #F7D959 | 4.4 | refill $15.99, in stock; EU out of stock |
| Eye whites | PLA Pure Pure White (17100), owned | #FFFFFF | 0.0 | owned |

- Closer face colours exist but aren't worth it: PLA Silk+ Champagne #F3CFB2 (6.2, glossy, not a cartoon finish) and
  PLA Matte Latte Brown #D3B7A7 (7.2, EU out of stock). Owned Apricot is 8.1.
- The pupils' alternative is Absolute Black (owned) for both hair and pupils: exact pupils, but hair 35.1 off.
  PLA Matte Dark Chocolate #4D3324 splits the difference (hair 16.5, pupils 20.7).
- Other shirt yellows: PLA Tough+ Yellow #F4D53F (5.7).

### d. Skin "bart", 4 PLA

His hair spikes are part of the head, and the lids take the face colour.

| Group (parts) | Pick | Hex | ΔE00 to reference | US snapshot |
|---|---|---|---|---|
| Face (head with spikes, ears, nose, lids) | PLA Matte Lemon Yellow (11400) | #F7D959 | 4.8 | as above |
| Shirt and collar | PLA Tough+ Orange (12301) | #DC3A27 | 7.0 | $23.99 spool, stock unclear |
| Eye whites | PLA Pure Pure White, owned | #FFFFFF | 0.0 | owned |
| Pupils | PLA Pure Absolute Black, owned | #000000 | 0.0 | owned |

- **One yellow spool serves both Skins.** Matte Lemon Yellow is 4.4 from Morty's shirt and 4.8 from Bart's face.
  PLA Tough+ Yellow #F4D53F is closer for Bart (3.2) but farther for Morty (5.7) and dearer (US MSRP $20.99 vs
  $15.99). PLA Basic Sunflower Yellow #FEC600 suits Bart only (4.5; Morty 12.0).
- Other shirt colours: PLA Translucent Orange #F74E02 is closer (4.7) but see-through; PLA Basic Orange #FF6A13 is
  9.8 off.
- If his shorts ever get a Shell, PLA Tough+ Cyan #009BD8 is 0.8 from #009DDC.

### e. What Cansin owns

- **Owned and used:** PLA Pure Apricot (Morty's face), Pure White (both Skins' eye whites), Absolute Black (Bart's
  pupils), and black PETG (both Skeletons' mounts, and the mechanical joints).
- **Owned but unused:** PLA Pure Milky Pink. It is 18.5 from Morty's face, so Apricot beats it.
- **To buy:** PETG Basic Dark Beige, PETG Matte White, PETG-CF Brick Red, PETG-CF Titan Gray, PETG Basic Gray, PLA
  Basic Cocoa Brown, PLA Matte Lemon Yellow and PLA Tough+ Orange. The two PETG-CF colours also need a hardened-steel
  nozzle.

**Conflicts with `docs/face-design.md`**, both sources kept:

- Its Morty is Milky Pink face, Absolute Black hair and a Pure White collar. The reference image shows a light tan
  face (closer to Apricot, 8.1 vs 18.5), brown hair and a yellow T-shirt with no white collar.
- Its Bart has an Apricot face and an "Absolute Black and Milky Pink pattern" shirt. The reference shows a yellow face
  (Apricot is 19.5 off) and a plain red-orange shirt.
- It calls Morty's pupils "jagged". The reference shows dots.
