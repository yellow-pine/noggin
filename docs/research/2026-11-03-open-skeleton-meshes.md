# Freely licensed human skeleton meshes for a cartoon-warped bust (2026-11-03)

A realistic Skeleton could start from a real human skeleton mesh, warped into cartoon proportions the way Hyungkoo
Lee's "Animatus" sculptures stretch real anatomy. The bust needs the skull, mandible, cervical vertebrae, the
ribcage (ribs, sternum, costal cartilage), the clavicles and the scapulae. Which freely licensed meshes cover those,
under which licence, and what does each licence demand of warped copies kept in this repo, which is under PolyForm
Noncommercial 1.0.0 (`LICENSE.md`)?

All sources read on 2026-11-03, from the projects' own sites, licence files and APIs. Not legal advice: licence texts
are quoted or paraphrased from the legal code, and every reading of ours is marked inferred. Nothing was adopted;
Cansin checks the licence before anything is.

## 0. What each licence asks of a warped copy in this repo

- **CC0.** Nothing. The warped mesh can sit under PolyForm Noncommercial like any of our files.
- **CC BY 4.0.** Credit (creator, copyright notice, licence and its URI, a link to the source) and a note that we
  changed it ([legal code §3(a)(1)](https://creativecommons.org/licenses/by/4.0/legalcode)). Our warped mesh is
  "Adapted Material", and §3(a)(4) only asks that "the Adapter's License You apply must not prevent recipients of the
  Adapted Material from complying with this Public License". Inferred: PolyForm Noncommercial on our changes satisfies
  that, so a warped CC BY mesh can live in the repo under PolyForm Noncommercial, with a credit in `docs/credits.md`.
- **CC BY-SA 4.0.** Credit as above, plus share-alike: "The Adapter's License You apply must be a Creative Commons
  license with the same License Elements, this version or later, or a BY-SA Compatible License", and no added terms
  that restrict it ([legal code §3(b)(1) and §3(b)(3)](https://creativecommons.org/licenses/by-sa/4.0/legalcode)).
  Inferred: the warped mesh files (and STLs or glTF made from them) must stay CC BY-SA 4.0, never PolyForm
  Noncommercial, so the repo would carry a second licence on those files, and anyone may then use those parts
  commercially. The rest of the repo is unaffected (it sits beside them, it does not adapt them).
- **CC BY-SA 2.1 Japan** (old BodyParts3D terms). Derivatives only under this licence or a CC licence with the same
  elements, and no added terms restricting recipients
  ([legal code Art. 5(2) and 5(5)](https://creativecommons.org/licenses/by-sa/2.1/jp/legalcode)). Same outcome as
  BY-SA 4.0.
- **CC BY-NC.** Not checked in depth. Inferred: NC on both sides makes it workable, but it is not a free-culture
  licence, so it ranks last.

## 1. Ranked candidates

| # | Source | Licence | Covers the bust? | Format, separate bones |
|---|---|---|---|---|
| 1 | BodyParts3D 4.0 (DBCLS archive) | **CC BY 4.0** (since 2025-02-27; conflict below) | Yes, all of it, except costal cartilages 8 to 10 | OBJ, one file per bone |
| 2 | TotalSegmentator dataset v2 | CC BY 4.0 (CT and masks) | Yes, as voxel masks; mandible not in `total` | NIfTI masks you mesh yourself |
| 3 | HRA 3D Reference Object Library (Visible Human Male) | CC BY 4.0 | Cervical vertebrae only | GLB/FBX, one node per vertebra |
| 4 | NIH 3D 3DPX-016838 "Human Skeleton" | CC BY 4.0 | Whole skeleton (CT) | "Mesh File", split not stated |
| 5 | Sketchfab CC BY skeletons | CC BY 4.0 | Whole skeleton, artist-modelled | glTF etc., mostly one object |
| 6 | Z-Anatomy | CC BY-SA 4.0 (README) vs GPLv3 (one LICENSE file) | Yes, all of it | `.blend` (and FBX) |
| 7 | Wikimedia Commons skull STLs | CC BY-SA 4.0 / 3.0 / 2.1 JP | Skull only | STL |
| — | Sketchfab CC0, Smithsonian, MorphoSource, OpenStax | see §2 | No usable full set found | — |

## 2. Each candidate

### 1. BodyParts3D 4.0 (Database Center for Life Science, Japan): best fit

- **Licence: CC BY 4.0 now.** The archive's licence page, "Last updated : 2025/02/27", says "The license for this
  database is specified in the Creative Commons Attribution 4.0 International" and asks for the credit line
  "BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International"
  ([licence page](https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html); the same text is §3 of the
  [README](https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/README_e.html), whose update history reads
  2025/02/27 "License" is updated, 2013/06/19 "3D data (Release 4.0) is updated").
- **Conflict, both sources recorded.** The project's older site still says CC BY-SA 2.1 Japan, credit
  "BodyParts3D, Copyright© 2008 ライフサイエンス統合データベースセンター licensed by CC表示－継承2.1 日本"
  ([lifesciencedb.jp licence](https://lifesciencedb.jp/bp3d/info/license/index.html)), and so do the copies others
  derived (Z-Anatomy, Wikimedia's `BodyParts3D Skull.stl`). Inferred: the 2025 archive page is the licensor's newer
  statement and covers the same Release 4.0 files (the mesh zip's `Last-Modified` is 2013-05-22), so a copy taken
  from the archive today is CC BY 4.0. Copies made from Z-Anatomy keep Z-Anatomy's BY-SA on its own changes. Worth one
  email to the contact on the licence page before adopting.
- **What it requires here:** the credit line above, a link to CC BY 4.0, and a note that we warped it (§0). No
  share-alike.
- **Coverage, by name in the PART-OF list**
  ([`partof_parts_list_e.txt`](https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/partof_parts_list_e.txt)):
  skull (a compound of its separate cranial bones, e.g. frontal, occipital, sphenoid, parietal), mandible, hyoid bone,
  atlas, axis, third to seventh cervical vertebrae, manubrium, body of sternum, xiphoid process, all 24 ribs,
  right and left clavicle, right and left scapula. Costal cartilages: 1st to 7th on each side only; 8th to 10th are
  not listed.
- **Format and quality:** "multiple files of ELEMENT file ID-specific polygon data in Wavefront OBJ format", one mesh
  per atomic part; compound parts (skull, rib cage) are lists of elements, not meshes (README §2.6 to §2.9). Two zips,
  both at "Polygon reduction rate = 99%": IS-A tree (136 MB) and PART-OF tree (62 MB). One adult male body, so all
  bones share one coordinate frame. Read by us from the PART-OF zip (1,258 OBJs, named `FJ<id>.obj`, mapped to names
  by [`partof_element_parts.txt`](https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/partof_element_parts.txt)):
  each OBJ header gives "Bounds(mm)", so units are millimetres in body coordinates (the mandible spans about 106 mm
  across). Face counts per bone: mandible 5,576; atlas 2,094; axis 2,288; C3 to C7 1,820 to 2,410; manubrium 2,546;
  body of sternum 4,646; xiphoid 922; ribs 2,818 to 10,264; costal cartilages 588 to 2,450; clavicles about 1,150;
  scapulae 26,172 and 28,106; cranial bones e.g. frontal 14,510, occipital 12,450, each parietal about 13,000. The
  `skull` compound is 43 element files. Inferred: dense enough to warp and print at bust scale after smoothing;
  watertightness and self-intersections not checked.
- **A third conflict, inside the files.** Every OBJ header in the 2013 zip still says "The license for this database
  is specified in the Creative Commons Attribution-Share Alike 2.1 Japan" with the matching credit line (e.g.
  `FJ3289.obj`, the mandible). The archive's licence page and README, both dated 2025-02-27, say CC BY 4.0. Inferred:
  the headers predate the 2025 change; the email above should settle which governs.
- **Download:** [PART-OF OBJ zip](https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/partof_BP3D_4.0_obj_99.zip),
  [IS-A OBJ zip](https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/isa_BP3D_4.0_obj_99.zip),
  [download page](https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html).

### 2. TotalSegmentator dataset v2 (University Hospital Basel): CC BY, but voxels

- **Licence:** the dataset (1228 CT images, 117 structures) is CC BY 4.0
  ([Zenodo record 10047292](https://zenodo.org/records/10047292), 23.6 GB zip). The segmentation model's `total`
  task is "Openly available for any usage (Apache-2.0 license)"
  ([README](https://github.com/wasserth/TotalSegmentator)).
- **Coverage:** the `total` classes include `skull`, `vertebrae_C1` to `vertebrae_C7`, `rib_left_1..12`,
  `rib_right_1..12`, `sternum`, `costal_cartilages`, `clavicula_left/right`, `scapula_left/right`. The mandible is
  only in the separate `craniofacial_structures` task (same README).
- **Format and quality:** NIfTI label masks, not meshes. Inferred: meshing them (marching cubes, smoothing) gives
  stair-stepped CT-resolution bones and costal cartilage as one blob; the 23.6 GB download and the meshing are heavy
  work for CI, not a laptop. A fallback if BodyParts3D's licence answer goes the wrong way.

### 3. HRA 3D Reference Object Library (HuBMAP, Visible Human Male): CC BY, neck only

- **Licence:** CC BY 4.0, both on the GitHub repo
  ([hubmapconsortium/ccf-3d-reference-object-library](https://github.com/hubmapconsortium/ccf-3d-reference-object-library),
  `license: CC-BY-4.0`) and on its NIH 3D entries ("CC-BY", e.g.
  [3DPX-021022 "Body, Male"](https://3d.nih.gov/entries/3DPX-021022)). The Visible Human source data sits under NLM's
  terms, which ask for "Courtesy of the U.S. National Library of Medicine" and no implied endorsement
  ([NLM terms](https://www.nlm.nih.gov/databases/download/terms_and_conditions.html);
  [VHP access](https://www.nlm.nih.gov/research/visible/getting_data.html): "the NLM Data License has been replaced by
  Terms and Conditions").
- **Coverage:** no skull, ribs, clavicle or scapula among the male files. `VH_Male/v1.2/VH_M_Vertebrae.glb` (12 MB,
  read by us) has 24 nodes, `VH_M_cervical_vertebra_1` to `_7`, thoracic 1 to 12 and lumbar 1 to 5, about 320k
  triangles in all.
- **Format:** GLB and FBX, one node per vertebra. Useful only as a second source for the neck.

### 4. NIH 3D Print Exchange, 3DPX-016838 "Human Skeleton": CC BY, CT-segmented

- **Licence:** "CC-BY" linked to CC BY 4.0, by "My Segmenter" ([entry](https://3d.nih.gov/entries/3DPX-016838)).
  NIH 3D licences are per entry.
- **Format and quality:** the page shows only "Mesh File"; no description, no source scan named, split not stated.
  A Sketchfab rework of it (CC BY, 568,776 faces) says "I separated the bones, edited the costal cartilage from the
  ribs" ([Terrie Simmons-Ehrhardt, Sketchfab](https://sketchfab.com/models/911b9df7e7834175b69b4840ea15e054)),
  so the original is inferred to be one mesh with cartilage fused to the ribs. Unknown source scan is a provenance gap.

### 5. Sketchfab CC BY skeletons: artist-modelled

From Sketchfab's search API (`license=by`, downloadable; [API](https://api.sketchfab.com/v3/search?type=models&q=human%20skeleton&license=by&downloadable=true)):

- ["Skeleton", Diego Luján García](https://sketchfab.com/models/4de7b96a351a4a35b1b6e5415277ff07), CC BY,
  378,572 faces: "The mesh comes in a single object but its all separated pieces."
- ["Free Pack - Human Skeleton", PolyOne Studio](https://sketchfab.com/models/950d0a46531f492ab8715777e312a5bf),
  CC BY, 51,650 faces, low-poly style.
- ["Human skull and neck", Lassi Kaukonen](https://sketchfab.com/models/a47ef69ff3a4402783cff0f841bc5e0a),
  CC BY, 1,323,241 faces, a photo scan of a teaching skeleton's upper part.

CC BY asks the same as §0. Inferred: an artist's sculpt is less faithful than BodyParts3D or CT, and Sketchfab's
licence field is the uploader's claim, so provenance is weaker.

### 6. Z-Anatomy: BodyParts3D plus share-alike

- **Licence, conflicting within the project.** The template repo's `License.txt` and README: "All the code and
  content shared by 'Z-Anatomy' is under Creative Commons Attribution-ShareAlike 4.0 International License", "You must
  distribute any derivative work ... under the same license", credit "BodyParts3D - The Database Center for Life
  Science - CC-BY-SA 2.1 Japan" and "Z-Anatomy - The libre 3D atlas of anatomy - CC-BY-SA 4.0"
  ([Z-Anatomy/Models-of-human-anatomy](https://github.com/Z-Anatomy/Models-of-human-anatomy/blob/master/License.txt)).
  The app repo's README also says CC BY-SA 4.0, but its `LICENSE` file is GPLv3
  ([LluisV/Z-Anatomy](https://github.com/LluisV/Z-Anatomy), `LICENSE`).
- **Format:** a Blender template (`Z-Anatomy.zip`), "models derived from 'BodyParts3D'", "meant to be used as a
  navigable atlas within Blender" (same README); FBX in the app repo's `Resources/Models/FBX`. Separate objects per
  structure inferred from the atlas use, not checked.
- **Verdict (inferred):** it adds nothing for bones that BodyParts3D's CC BY files lack, and its BY-SA would bind our
  warped files. Take BodyParts3D from the source instead.

### 7. Wikimedia Commons: skull only, share-alike

From Commons' API ([search](https://commons.wikimedia.org/w/index.php?search=skull+stl&ns6=1)):
[`High quality skull.stl`](https://commons.wikimedia.org/w/index.php?title=File:High_quality_skull.stl), CC BY-SA 4.0, 43 MB, a
thesis skull "decomposable ... in 54 anatomically correct elements";
[`BodyParts3D Skull.stl`](https://commons.wikimedia.org/w/index.php?title=File:BodyParts3D_Skull.stl), CC BY-SA 2.1 JP;
[`Skull 3D SR File Nevit Dilmen.stl`](https://commons.wikimedia.org/w/index.php?title=File:Skull_3D_SR_File_Nevit_Dilmen.stl),
CC BY-SA 3.0, "Skull with deformity". All share-alike, skull only.

### Not usable, or not found

- **Sketchfab CC0.** The API (`license=cc0`) returns no human skeleton or ribcage. The only human CC0 hits are two
  archaeological skulls with pathology by Northern Heritage Network
  ([syphilis](https://sketchfab.com/models/2692cc377baf4031b288aeaa58154bba),
  [trauma](https://sketchfab.com/models/a2daa492557d4f408b4e2a97d54028f3)), skull only;
  inferred unsuitable (a real person's remains, lesions).
- **Smithsonian Open Access 3D (CC0).** The Open Access API returns no human skeleton in 3D; the one human cranium
  page found ([Qafzeh 6](https://3d.si.edu/object/3d/homo-sapiens-cranium:52610788-8e81-4b0b-8d3a-8d19828236ec), a
  fossil) answered HTTP 403, and a search snippet says its files are for "non-commercial, educational, and personal
  uses" despite CC0 metadata. Unverified.
- **MorphoSource.** Licences are per media. Its API fields include `license`, `permits_commercial_use`,
  `permits_3d_use` and `visibility`; a 100-item sample of meshes was mostly CC BY-NC or CC BY-NC-ND, many
  `restricted_download` ([API](https://www.morphosource.org/api/media)). Its terms page is behind a bot check, so the
  use agreement was not read. Single bones of single specimens, not a matched set; inferred unsuitable.
- **OpenStax.** Not checked; its textbooks are illustrations, and no 3D mesh set was found.

## 3. Recommendation (inferred)

BodyParts3D 4.0 from the DBCLS archive: it is the only source with every bone the bust needs as separate OBJ meshes
of one body, and its current licence is CC BY 4.0, which lets the warped meshes sit under PolyForm Noncommercial with
a credit line in `docs/credits.md`. Before adopting, settle the lifesciencedb.jp BY-SA 2.1 JP conflict (one email to
DBCLS, or a dated capture of the 2025-02-27 licence page kept with the credit). The 8th to 10th costal cartilages are
missing and would be ours to model. TotalSegmentator (CC BY 4.0) is the fallback.
