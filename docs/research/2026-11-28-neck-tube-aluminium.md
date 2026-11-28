# The neck tube's aluminium, its screws and inserts: cited strengths (#1075)

Researched 2026-11-28. Purpose: replace the figures #1075 recalled from memory (6060-T66 160 MPa, 6061-T6 240 MPa,
class 8.8 640 MPa, A2-70 450 MPa) with cited ones, and redo the hand sums for the 10 x 1 mm tube. Facts and
arithmetic only; no design decision. PETG is left out: the repo already holds it.

Where each number comes from, in order of trust:

- [EC9] BS EN 1999-1-1:2007+A1:2009, Eurocode 9 part 1-1, the standard's own text, as the Public.Resource.Org scan
  mirrored at <https://www.phd.eng.br/wp-content/uploads/2014/11/en.1999.1.1.2007.pdf>. The
  [law.resource.org index](https://law.resource.org/pub/eu/eurocode.html) still lists it, but its archive.org copy now
  answers "Item not available". This edition is superseded (A2:2013, then EN 1999-1-1:2023); neither is free to read.
- [EC3] EN 1993-1-8:2005, Eurocode 3 part 1-8, same kind of scan:
  <https://www.phd.eng.br/wp-content/uploads/2015/12/en.1993.1.8.2005-1.pdf>.
- [ISO898] ISO 898-1:2013 (fifth edition), the 15-page preview sample a standards shop (iTeh) serves, which holds
  Table 3 and the M3 rows of Tables 4 and 5: <https://cdn.standards.iteh.ai/samples/60610/e211f7b6697643f192d041ceceb1f2be/ISO-898-1-2013.pdf>.
- Mill, stockholder and maker sheets that quote a standard, linked at each claim.

EN 755-2 and EN 754-2 themselves are not free: the previews of
[EN 755-2:2016](https://normy.normoff.gov.sk/norma/123208/nahlad) and
[EN 754-2:2016](https://normy.normoff.gov.sk/norma/124747/nahlad) stop at the contents page. Their values below come
through [EC9] Table 3.2b (which quotes EN 755-2:2008 in its footnote 3) and through datasheets that name the edition.
[EN 755-2:2025](https://normy.normoff.gov.sk/norma/141712/nahlad) has since replaced the 2016 edition; its tables
were not read.

## What retail 10 x 1 mm round tube is

- A stockholder's stock list for extruded round tube names it outright: 10 x 1 mm, "EN AW-6060 / Al Mg Si 0,5",
  T66, "gepresst" (extruded), tolerances to EN 755-8, and "EN 755-2 ... T66 ... 215 ... 160"
  ([thyssenkrupp Materials Austria](https://ucpcdn.thyssenkrupp.com/_legacy/UCPthyssenkruppBAMXAustria/assets.files/download/aluminium_datenblatt_en_aw_6060_rundrohr.pdf);
  no edition named).
- An online metal shop sells the same size as "EN AW-6060 T66"
  ([metallshopper.de](https://metallshopper.de/Aluminium-Rundrohr-oe10x1)); it cites no standard.
- A DIY-store brand's own data sheet for its aluminium profiles gives "EN AW - 6060-T66", formerly
  "AlMgSi0,5 F22", material number 3.3206, EN 755-1/-2, 215 N/mm² tensile and 160 N/mm² yield
  ([alfer, PDB 100003, 2017](https://products.alfer.com/files/alfer/catalog/articlegroups-articles/documents/PDB_100003.pdf)).
  That sheet is for tile profiles. Alfer's
  [round tube page](https://products.alfer.com/en/hardware/combitech-system-basis/system-profiles-aluminium/round-tube-uncoated-aluminium.html)
  says only "uncoated aluminium", and that range runs 7.5, 11.5, 15.5 mm and up, not 10 mm. That its tubes share
  the alloy is inferred.
- F22 is the old German name for this state: an enclosure maker's sheet is titled "AlMgSi 0.5 F22 according to
  EN 755" and lists DIN 1748 part 1 and DIN 1725 part 1 beside it
  ([Rolec](https://rolec.com/fileadmin/Media/6d/38/Werkstoffdatenblatt_Strangpressprofile_en.pdf)). That the number is
  a tenth of the minimum tensile strength (22 for 215 N/mm²) is inferred from the pairing; no free source states the
  rule, and DIN 1748-1 (withdrawn) was not read.

So a 10 x 1 tube from a European metal shop is extruded EN AW-6060 T66 where the seller names it. Where the seller
names no temper, taking 6060 T6 (150 MPa, or [EC9]'s 140 MPa) is the cautious reading (inferred).

Not verified: Bauhaus (Kantoflex), Hornbach and GAH Alberts pages refused the fetch or name no alloy. One
distributor's 10 mm x 1 mm tube appears in search results titled "6063-T6"
([RS PRO 918-6374](https://de.rs-online.com/web/p/metallrohre/9186374)); the page refused the fetch, so that is a
title seen, not a datasheet read.

## Minimum Rp0.2 and Rm for a 1 mm wall

MPa, minimum. ET extruded tube, EP extruded profile, DT cold drawn tube; t is the wall.

| Alloy, temper, form | Rp0.2 | Rm | Wall range | Quoted from | Source |
| --- | --- | --- | --- | --- | --- |
| 6060 T6, ET | 150 | 190 | t <= 15 | EN 755-2:2016-10 | [thyssenkrupp 6060][tk] |
| 6060 T6, EP | 150 | 190 | t <= 5 | EN 755-2:2016 | [Hydro 6060][h60] |
| 6060 T6, ET/EP | 140 | 170 | t <= 15 | [EC9] Table 3.2b (bold: lowest of the bands) | [EC9] p. 35 |
| 6060 T66, ET | 160 | 215 | t <= 15 | EN 755-2:2016-10 | [thyssenkrupp 6060][tk] |
| 6060 T66, EP | 160 | 215 | t <= 5 | EN 755-2:2016 | [Hydro 6060][h60] |
| 6060 T66, ET/EP | 160 | 215 | t <= 3 | [EC9] Table 3.2b (EN 755-2:2008) | [EC9] p. 35 |
| 6060 T6, DT | 160 | 215 | t <= 20 | EN 754-2:2017-02; [EC9] Table 3.2b agrees | [thyssenkrupp 6060][tk] |
| 6063 T6, EP | 170 | 215 | t <= 10 | EN 755-2:2016 | [Hydro 6063][h63] |
| 6063 T6, ET | 170 | 215 | t <= 25 | "755-2", no edition | [Alumil][alumil] |
| 6063 T6, ET/EP | 160 | 195 | t <= 25 | [EC9] Table 3.2b (bold: lowest of the bands) | [EC9] p. 35 |
| 6063 T66, EP | 200 | 245 | t <= 10 | EN 755-2:2016; [EC9] Table 3.2b agrees | [Hydro 6063][h63] |
| 6063 T66, ET | 200 | 245 | t <= 25 | "755-2", no edition | [Alumil][alumil] |
| 6063 T6, DT | 190 | 220 | t <= 20 | [EC9] Table 3.2b | [EC9] p. 35 |
| 6063 T66, DT | 195 | 230 | t <= 20 | [EC9] Table 3.2b | [EC9] p. 35 |
| 6061 T6, ET/EP | 240 | 260 | t < 25 | [EC9] Table 3.2b | [EC9] p. 35 |
| 6061 T6, ET | 240 | 260 | t <= 5 | "EN 755-2", no edition | [Bikar 6061][bikar] |
| 6061 T6, DT | 240 | 290 | t <= 20 | [EC9] Table 3.2b; Bikar's "EN 754-2" row agrees | [EC9] p. 35 |

[tk]: https://ucpcdn.thyssenkrupp.com/_binary/UCPthyssenkruppBAMaterialsSchulte/1a557d48-f591-46ee-baba-b1a8047b47d0/6060-03.2020.pdf
[h60]: https://hydro.com/globalassets/08-about-hydro/hydro-worldwide/austria/nenzing/datenblatter-legierungen/hydro-en-aw-6060
[h63]: https://hydro.com/globalassets/08-about-hydro/hydro-worldwide/austria/nenzing/alloy-data-sheets/hydro-en-aw-6063.pdf
[alumil]: https://www.alumil.com/docs/librariesprovider13/extrusion/mechanical-properties-ro.pdf
[bikar]: https://www.bikar.com/fileadmin/user_upload/aluminium/bleche-platten/6061-komplett.pdf

Conflicts, both sides kept:

- 6060 T6 extruded: 150/190 by EN 755-2:2016 against 140/170 in [EC9]. [EC9]'s footnote 1 explains it: bold
  values cover the whole thickness range with the lowest band, and the product standard's higher Rp0.2 and Rm "can
  be taken as fo and fu". For a 1 mm wall the product standard's 150/190 applies.
- 6063 T6 extruded: 170/215 against [EC9]'s 160/195, for the same reason.
- The thin band for 6060 T66 profiles ends at 3 mm in EN 755-2:2008 (as [EC9] quotes it) and at 5 mm in the 2016
  edition. A 1 mm wall is inside both.
- [EC9] footnote 3 (from EN 755-2:2008): where a section spans several thickness bands, the lowest value holds for
  the whole section. A plain tube has one wall, so this does not bite.

American limits, for comparison only. The Aluminum Association's Table 12.1, extruded tube (the table ASTM B221
carries; the file was posted 2022-12 and prints no edition): 6061-T6, wall up through 0.249 in, 38.0 ksi ultimate
and 35.0 ksi yield (262 and 241 MPa); 6063-T6, wall up through 0.124 in, 30.0 and 25.0 ksi (207 and 172 MPa)
([aluminum.org](https://www.aluminum.org/sites/default/files/2022-12/Table_12.1.pdf)). ASTM B221's and B210's own
text is paid and was not read; no free first-party table for drawn tube (B210) was found.

## Elastic constants

- [EC9] clause 3.2.5(1), for every alloy it covers: E = 70 000 N/mm², G = 27 000 N/mm², Poisson's ratio 0.3,
  density 2 700 kg/m³.
- Datasheet values sit just under: 69 500 and 26 100 MPa for 6060 ([thyssenkrupp][tk], "Anhaltsangaben", guide
  values); 69 and 26 GPa for 6060 and 6063 ([Hydro][h60], typical, from MNC Handbok 12, 1989).

## Shear, combined stress and holes in Eurocode 9

- Shear strength is the proof strength over root three: V_Rd = A_v fo / (√3 γM1), with A_v = 0.6 A for a round
  tube ([EC9] 6.2.6, expressions 6.29 and 6.31); torsion likewise, T_Rd = W_T,pl fo / (√3 γM1) (6.2.7.1).
- Combined stress at a point is the von Mises form: (σ/(fo/γM1))² + 3 (τ/(fo/γM1))² <= C for one direct stress,
  C = 1.2 recommended ([EC9] 6.2.1(5), expression 6.15).
- Bending: the lesser of M_o,Rd = α W_el fo / γM1 at each section and M_u,Rd = W_net fu / γM2 in a net section
  ([EC9] 6.2.5.1, expressions 6.24 and 6.25). So the standard checks a section with holes against the tensile
  strength, not the proof strength. Recommended γM1 = 1.10 and γM2 = 1.25 (6.1.3, Table 8.1).
- Net area deducts the hole's cross-section in the plane of its axis ([EC9] 6.2.2.2).
- Bolt bearing on the connected part: F_b,Rd = k1 αb fu d t / γM2, αb the smallest of αd, fub/fu and 1.0, with
  αd = e1/(3 d0) for an end bolt, and k1 the smaller of 2.8 e2/d0 - 1.7 and 2.5 ([EC9] 8.5.5, Table 8.5).
- A pin: bearing F_b,Rd = 1.5 t d fo,min / γM1 and shear F_v,Rd = 0.6 A fup / γMp ([EC9] 8.5.14, Table 8.7).

## M3 screws

| Quantity | Value | Quoted from |
| --- | --- | --- |
| Class 8.8, d <= 16 mm: Rm nominal / minimum | 800 / 800 MPa | [ISO898] Table 3 |
| Class 8.8, d <= 16 mm: Rp0.2 nominal / minimum | 640 / 640 MPa | [ISO898] Table 3 |
| Class 12.9: Rm nominal / minimum | 1 200 / 1 220 MPa | [ISO898] Table 3 |
| Class 12.9: Rp0.2 nominal / minimum | 1 080 / 1 100 MPa | [ISO898] Table 3 |
| M3 coarse, nominal stress area As | 5.03 mm² | [ISO898] Table 4 |
| M3 minimum ultimate tensile load, 8.8 / 12.9 | 4 020 / 6 140 N | [ISO898] Table 4 |
| M3 proof load, 8.8 / 12.9 | 2 920 / 4 880 N | [ISO898] Table 5 |
| A2-70 (and A4-70): Rp0.2 / Rm minimum | 450 / 700 MPa | [EC9] Table 3.4, "grade according to EN ISO 3506-1" |
| M3 plain shank area, π/4 x 3² | 7.07 mm² | arithmetic |

- [EC9] Table 3.4 and [EC3] Table 3.1 repeat 640 and 800 MPa for class 8.8.
- A distributor's extract of ISO 3506-1 gives the same 700 and 450 MPa for class 70, printed for "< M24"
  ([Würth, Tab. 16](https://prueflabor.wuerth-industrie.com/web/media/downloads/brochures/en_wis/dino.pdf); it names
  no edition). ISO 3506-1:2020 itself is paid and was not read.
- Shear is not in ISO 898-1: its scope says it "does not specify requirements for ... resistance to shear stress".
  The design rule is Eurocode's: F_v,Rd = αv fub A / γM2 per shear plane, αv = 0.6 for classes 4.6, 5.6 and 8.8
  through the thread (A = As), 0.5 for 10.9, stainless and aluminium bolts, and 0.6 through the plain shank
  ([EC9] Table 8.5; [EC3] Table 3.4 has the same steel values).
- Neither Eurocode lists class 12.9. A cap-screw maker states "for alloy steel, the shear strength is 60% of its
  tensile strength" and 50 to 55 % for 300-series stainless, and lists its M3 cap screw at 6.54 kN tensile, 5.5 kN
  single shear of the body and 2.1 N·m seating torque, at its own 1 300 MPa
  ([Unbrako Engineering Guide, 1996, a university's copy](https://wp.optics.arizona.edu/optomech/wp-content/uploads/sites/53/2016/08/UnBrako-fasteners.pdf)).
  That is maker's data, not a standard.

## M3 in printed PETG: test data, not a standard

One test series, three samples each, PETG at four perimeters and 100 % infill, M3
([CNC Kitchen, 2020-05-30](https://www.cnckitchen.com/blog/helicoils-threaded-insets-and-embedded-nuts-in-3d-prints-strength-amp-strength-assessment)):

| Fixing | Pull-out, average | Torque-out |
| --- | --- | --- |
| Brass heat-set insert (Ruthex) | 119 kg (1 167 N) | 3 N·m, the insert turned |
| Screw straight into the plastic | 118 kg (1 157 N) | 1 N·m, threads sheared |
| Nut in a side pocket | 86 kg (843 N) | 2 N·m, the PETG crushed |
| Nut in a bottom pocket | about 166 kg (1 628 N) | about 2 N·m |

The same author's later series in PLA puts M3 x 5.7 inserts at about 1 400 N on average at the smaller of the hole
diameters tried (3.6 to 4.6 mm; the packaging recommends 4.0 mm), falling as the hole grows
([CNC Kitchen, 2026-03-28](https://www.cnckitchen.com/blog/are-our-heat-set-insert-datasheets-wrong)). No insert
maker's datasheet with a PETG pull-out figure was found. Against [ISO898]'s 2 920 N proof load for an M3 8.8, the
plastic is the weak link by a factor of about 2.5.

## The tube, by hand

D = 10 mm, d = 8 mm, L = 116 mm, M = 3.44 N·m (taken as a pure couple, the same at every section), T = 0.95 N·m.

- Area A = π/4 (D² - d²) = 28.27 mm².
- Second moment I = π/64 (D⁴ - d⁴) = π/64 x 5 904 = 289.8 mm⁴.
- Section modulus W = I / (D/2) = 57.96 mm³.
- Polar moment J = 2 I = 579.6 mm⁴; polar modulus Wp = J / (D/2) = 115.9 mm³.
- Bending stress σ = M / W = 3 440 / 57.96 = 59.4 MPa.
- Torsional shear τ = T / Wp = 950 / 115.9 = 8.2 MPa.
- Von Mises √(σ² + 3 τ²) = 61.0 MPa.
- Tip slope M L / (E I) = 3 440 x 116 / (70 000 x 289.8) = 0.0197 rad = 1.13°; tip deflection M L² / (2 E I) =
  1.14 mm. With the datasheets' 69 500 MPa: 1.14°.
- Twist T L / (G J) = 950 x 116 / (27 000 x 579.6) = 0.0070 rad = 0.40°. With 26 100 MPa: 0.42°.

Safety factor on Rp0.2, whole section (no partial factors):

| Tube | Rp0.2 | Bending alone | Bending and torsion |
| --- | --- | --- | --- |
| 6060 T6 extruded, [EC9] | 140 | 2.36 | 2.29 |
| 6060 T6 extruded, EN 755-2:2016 | 150 | 2.53 | 2.46 |
| 6060 T66 extruded; 6060 T6 drawn | 160 | 2.70 | 2.62 |
| 6063 T6 extruded, EN 755-2:2016 | 170 | 2.86 | 2.79 |
| 6063 T6 drawn | 190 | 3.20 | 3.11 |
| 6063 T66 drawn | 195 | 3.29 | 3.20 |
| 6063 T66 extruded | 200 | 3.37 | 3.28 |
| 6061 T6 extruded or drawn | 240 | 4.04 | 3.93 |

Torsion alone, against Rp0.2/√3, is 9.9 (140 MPa) to 16.9 (240 MPa). In [EC9]'s own form the bending factors
divide by γM1 = 1.10, shape factor taken as 1.

## The cross hole

A 3.2 mm hole through both walls. Approximation: each wall loses a straight slot the hole's full width, 3.2 mm (the
curved cut is ignored), the lost area is summed numerically over the ring, and the modulus divides by the outermost
fibre left. No stress concentration factor is applied. Hand check with two thin rectangles 3.2 x 1 mm at the mean
radius 4.5 mm: I lost = 2 (3.2 x 1³/12 + 3.2 x 1 x 4.5²) = 130 mm⁴, leaving 160 mm⁴ against the numeric 162.5 mm⁴.

| Hole's axis | I net | Outer fibre | W net | Bending stress | Von Mises |
| --- | --- | --- | --- | --- | --- |
| In the bending plane (the holes sit on the extreme fibres) | 162.5 mm⁴ | 4.74 mm | 34.3 mm³ | 100.3 MPa | 102.0 MPa |
| Along the neutral axis (the holes sit at mid-height) | 284.1 mm⁴ | 5.00 mm | 56.8 mm³ | 60.5 MPa | 63.3 MPa |

Net area is 21.7 mm² either way; the torsional shear rises to about 10.6 MPa (J net 446.6 mm⁴, taken at the outer
radius; inferred, a slotted ring is not a closed tube's ideal).

| Tube | Rp0.2 / Rm | SF, holes on the extreme fibres | SF, holes on the neutral axis | W net x Rm / M, extreme fibres |
| --- | --- | --- | --- | --- |
| 6060 T6 extruded, [EC9] | 140 / 170 | 1.37 | 2.21 | 1.69 |
| 6060 T6 extruded, EN 755-2:2016 | 150 / 190 | 1.47 | 2.37 | 1.89 |
| 6060 T66 extruded | 160 / 215 | 1.57 | 2.53 | 2.14 |
| 6063 T6 extruded | 170 / 215 | 1.67 | 2.69 | 2.14 |
| 6063 T66 extruded | 200 / 245 | 1.96 | 3.16 | 2.44 |
| 6061 T6 extruded | 240 / 260 | 2.35 | 3.79 | 2.59 |

The SF columns are Rp0.2 over the von Mises stress on the net section. The last column is [EC9]'s net-section check
(6.24) without γM2; divide by 1.25 for the design value. With the holes on the extreme fibres at full moment, only
6061 T6 keeps SF 2 on Rp0.2, and that before any stress concentration. With the screw parallel to the axis the
bending turns about, the hole costs about 2 % of the modulus. Inside the socket the moment falls from full at the
mouth to nothing at the tube's end, so a hole near the foot sees less (inferred; no figure, it depends on how the
socket bears).

## The cross screw under the pan's stall

The torque leaves the tube as a couple at its two walls: F = T / D = 950 / 10 = 95 N per shear plane (planes at the
tube's skin, radius 5 mm).

- Screw shear, thread in the plane, characteristic αv fub As: class 8.8, 0.6 x 800 x 5.03 = 2 414 N (SF 25);
  A2-70, 0.5 x 700 x 5.03 = 1 760 N (SF 18). Divide by γM2 = 1.25 for [EC9]'s design value: SF 20 and 15. Class
  12.9 at αv = 0.5, as for 10.9, is 3 068 N (SF 32), inferred since the table stops at 10.9.
- Bearing on the 1 mm wall: 95 / (3 x 1) = 31.7 MPa. As a pin, 1.5 t d fo = 1.5 x 1 x 3 x 160 = 720 N for 6060 T66
  (SF 7.6; 6.9 with γM1), 630 N at 140 MPa (SF 6.6), 1 080 N for 6061 T6 (SF 11.4). As a bolt, k1 αb fu d t =
  2.5 x 1.0 x 215 x 3 x 1 = 1 612 N (SF 17), which needs the hole at least 1.5 d0 = 4.8 mm from the tube's end
  for k1 = 2.5. Applying a plate rule to a curved 1 mm wall is inferred.

## Recalled figures, checked

| Recalled | Verdict |
| --- | --- |
| 6060-T66 yield 160 MPa | Right for a 1 mm wall (Rm 215). Only if the seller names T66; 6060 T6 is 150, or 140 in [EC9]. |
| 6061-T6 yield 240 MPa | Right, extruded or drawn; Rm is 260 extruded, 290 drawn. |
| Class 8.8, 640 MPa | Right for d <= 16 mm, nominal and minimum; Rm 800. |
| Class 12.9, 1 080/1 100 and Rm 1 200 | Rp0.2 nominal 1 080, minimum 1 100: right. Rm 1 200 is nominal; the minimum is 1 220. |
| A2-70, 450 MPa | Right; Rm 700. |
| As = 5.03 mm² | Right. |
| E 70 000, G 27 000 | Right, [EC9] 3.2.5; Poisson's ratio 0.3. |
| Bolt shear about 0.6 Rm | Right for 8.8 only; 0.5 for 10.9 and stainless. ISO 898-1 gives no shear value. |
| #1075: SF 2.7 (6060) to 4.1 (6061), lean 1.2° | Bending alone 2.70 and 4.04; with the twist 2.62 and 3.93; lean 1.13°. No cross hole counted. |

## Not verified from a free source

- EN 755-2 and EN 754-2 in their own text, any edition, and whether EN 755-2:2025 or a newer EN 754-2 changes a
  value above.
- The edition behind Alumil's and Bikar's rows; they carry the 6063 extruded-tube and 6061 thin-wall bands.
- Which alloy the DIY chains' own-brand 10 x 1 tube is; RS PRO's 6063-T6 page.
- The F-number rule (DIN 1748-1).
- ASTM B221 and B210 text; any drawn-tube limit by ASTM.
- ISO 3506-1:2020 in its own text; ISO 724 for the thread's geometry (As is taken from ISO 898-1).
- A stress concentration factor for a cross hole in a tube, fatigue, local buckling of the wall (D/t = 10), and
  the tube's wall tolerance under EN 755-8: none was looked up.
- An insert maker's pull-out figure in PETG.
