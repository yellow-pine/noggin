# Realistic printable human skull models with teeth (#838)

2026-11-03. The goal is a realistic skull with a separate mandible, teeth and ideally the atlas and axis, under a licence a PolyForm Noncommercial repo can adopt and modify. CC0 and CC BY are preferred. SA and NC are acceptable. ND is not.

The licences and file lists come from each host's own record: the Printables GraphQL API (`api.printables.com/graphql/`, `print(id)`) and the Sketchfab Data API (`api.sketchfab.com/v3/models/{uid}`). Face counts and watertightness come from trimesh 5.2 on the downloaded files.

## Ranked candidates

| # | Model | Licence (host's label) | Parts | Teeth | Size | Downloaded |
|---|---|---|---|---|---|---|
| 1 | [Anatomically Correct Human Skull (Homo Sapiens Sapiens)](https://www.printables.com/model/777324-anatomically-correct-human-skull-homo-sapiens-sapi), 3Demon | CC BY-SA | cranium (cut in 2) + separate mandible | yes, upper and lower | 1.96 M faces, 73 MB OBJ, 13 watertight bodies | yes |
| 2 | [Human Skull and Neck](https://sketchfab.com/3d-models/human-skull-and-neck-a47ef69ff3a4402783cff0f841bc5e0a), Lassi Kaukonen (thesidekick) | CC BY | photogrammetry of a teaching skeleton's top: skull + cervical spine, likely one fused mesh | yes | 1.32 M faces | no (Sketchfab download needs a login) |
| 3 | [The Anatomy of the Human Skull](https://sketchfab.com/3d-models/the-anatomy-of-the-human-skull-baf6ac7b781a46218dca2b59dee58817), Hannah Newey | none listed by the API; not downloadable on Sketchfab today | CT-derived; teeth remodelled so the mandible detaches | yes | 1.98 M faces | no |
| 4 | [Human skull, anatomically correct](https://www.printables.com/model/2770-human-skull-anatomically-correct), Peter from Belgium | marked CC Public Domain, **provenance doubtful** (see below) | skull + `jaw_top` (upper teeth) + `jaw_lower` (mandible with teeth) | yes, as separate bodies | 330 k faces, 16 MB STL, watertight | yes |
| 5 | [Human Male Skull](https://sketchfab.com/3d-models/human-male-skull-f1eaaef50e5845c796d6834fd1b702e5), ruslangadzhiev | CC BY | unknown until downloaded | yes (thumbnail) | 137 k faces | no (login) |
| neck | [Atlas and Axis (C1 and C2) Cervical Vertebrae](https://www.printables.com/model/1087469-atlas-and-axis-c1-and-c2-cervical-vertebrae), Isopropyl Alcohol | CC BY-NC-SA | atlas and axis as separate STLs (+ vertebral artery) | n/a | 0.62 M + 1.51 M faces, watertight, unitless (needs scaling) | yes |

The following were also seen and rejected:
- [Human skull, anatomically correct and printer friendly](https://www.thingiverse.com/thing:819046) by dantana is CC BY-SA. Its description says it started from "a 3D model of the individual bones of the skull", which is likely BodyParts3D, the source Cansin is replacing.
- The Printables remixes of #4 inherit its provenance: [Gage's re-cut](https://www.printables.com/model/293680) (PD), [EDGeProjects' hinged version](https://www.printables.com/model/538715) (BY-NC-SA) and [Nina Máčová's vertical cut](https://www.printables.com/model/1092299) (BY-SA).
- The witmerlab "Visible Interactive Human - Exploding skull" is CC BY-NC-ND, so ND rules it out.
- Sketchfab's "Realistic Human Skull Bone Model" (s8819296) is CC BY, but its description reads like an AI-generated asset.

## Provenance flag on #4

The skull mesh splits into 35 watertight bodies, one per bone, and each tooth is its own body. That is the structure of an atlas of segmented bones such as BodyParts3D, not of "a scan" as the page says. It matches dantana's 2015 Thingiverse model (CC BY-SA, built from individual bones), so its Public Domain label may be a relicensing the uploader had no right to make. This is inferred: neither page names the source. Treat it as CC BY-SA at best.

## Gaps

- **Not checked:** MyMiniFactory, Cults3D, Thangs, MorphoSource and the Smithsonian (its Open Access API returned no human-skull 3D packages for a DEMO_KEY query). The NIH 3D search found only pathology or animal skulls.
- **Atlas and axis:** no skull model ships with them. They come from the separate CC BY-NC-SA model.
