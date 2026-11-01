# Eyelid kinematics for the lid servos

Researched 2026-11-01. Background only: the gestures keep toon timing (#258, `2026-11-01-toon-eyes.md`).

Builds on `docs/research/2026-10-31-natural-eye-motion.md` §1, which already covers Kwon, Sforza and Trutoiu.

Sources:
- [V] VanderWerf 2003, J Neurophysiol 89:2784, search coil. https://doi.org/10.1152/jn.00557.2002
- [E] Evinger, Manning & Sibony 1991, IOVS 32:387. https://pubmed.ncbi.nlm.nih.gov/1993591/ Full text unreachable; numbers come via [V] and [W].
- [K] Kwon 2013, 600 fps, voluntary blinks. https://doi.org/10.1098/rsif.2013.0227
- [N] Nakamura 2008, 1 kHz, 109 spontaneous blinks. https://pubmed.ncbi.nlm.nih.gov/19157026/
- [W] Willett 2023 review, citing Doane 1980. https://doi.org/10.3389/fnsys.2023.1242654
- [S] Sanchis-Jurado 2020. https://doi.org/10.1007/s00417-020-04782-w
- [P] PNAS 2025. https://doi.org/10.1073/pnas.2508058122

## 1. Spontaneous blink

- **Down phase:** 92±17 ms [V]. Other figures: 75 ms [E via V], ~100 ms [N].
- **Peak velocity:** 565±297 °/s of lid rotation over a 21±6° amplitude [V], so ~27 amplitudes/s. [N]: ~180 mm/s on full blinks, 120 mm/s on partial ones. Peak velocity scales linearly with amplitude [E via W; N].
- **Where the peak falls:** slow start, peak as the lid crosses the visual line, slowing before the lower lid [Doane via W]; [K] calls it parabolic. So a bell, peaking at ~40–50% of closing time (inferred; no source gives time-to-peak), not an early peak.
- **Closed hold:** 10–50 ms [Ousler via W].
- **Up phase (to 95% open):** 242±55 ms [V]. Other figures: 140–225 ms [E via V], ~220 ms [N].
- **Down:up ratio:** ~1:2.5 in duration; peak speed 180 vs 60 mm/s, ~3:1 [N]. Opening starts fast, then a long decelerating tail [K].
- **Amplitude:** often partial. 70 of 109 blinks were incomplete in [N]; spontaneous blinks stayed under 100% in [P].

## 2. Voluntary blink, wink

- **Voluntary blink** [V]:
  - Total 275±37 ms: down 88±13 ms, up 187±34 ms.
  - Amplitude 38±10°, about twice a spontaneous blink.
  - Peak 1402±159 °/s.
  - Less variable than spontaneous blinks.
- **Also:** [S] 1.7× more full closures, faster; [K] close 76, hold 58±4, open 438 ms. Baker 2005 (abstract) found them ~18% longer, conflicting with [V]. All agree: faster, fully closed, longer hold.
- **Both eyes:** in voluntary blinks one lid consistently starts earlier and moves further, and the asymmetry is stable per person (Kassem & Evinger 2006, https://pubmed.ncbi.nlm.nih.gov/16384962/).
- **Wink:** I found no kinematic study. Primary work on winks is neural:
  - Winking recruits more frontal-eye-field and parietal cortex than blinking (https://pmc.ncbi.nlm.nih.gov/articles/PMC5294255/).
  - 41 of 63 subjects could wink only one eye (Lin 2019, https://pmc.ncbi.nlm.nih.gov/articles/PMC6908889/).
- **Wink, inferred:** voluntary-blink speed, full closure, deliberate 200–400 ms hold; other lid narrows 10–30% in step. No source covers gaze or brow; a glance toward the winking side is style.

## 3. Profiles for 20 ms steps

Symbols: `A` = closure amplitude, `Tc` = closing time, `Th` = hold time, `τ` = opening time constant.

```
closure(t) = A·(1 − cos(π t/Tc))/2      t < Tc          (bell curve, peak mid-closure)
           = A                          t < Tc + Th
           = A·exp(−(t − Tc − Th)/τ)    after; snap to 0 below 0.05·A
```

| | Tc | Th | τ (95% open at 3τ) | A |
|---|---|---|---|---|
| spontaneous | 80 | 40 | 80 [V] | random 0.8–1.0 [N] |
| voluntary | 80 | 60 [K] | 60 [V] | 1.0 |
| wink (inferred) | 120 | 300 | 100 | 1.0; other lid 0.2 |

Closure at each 20 ms step:
- **Spontaneous:** 0:0, 20:.15, 40:.50, 60:.85, 80–120:1, 140:.78, 160:.61, 180:.47, 200:.37, 220:.29, 240:.22, 260:.17, 280:.14, 300:.11, 320:.08, 340:.06, 360:0
- **Voluntary:** 0:0, 20:.15, 40:.50, 60:.85, 80–140:1, 160:.72, 180:.51, 200:.37, 220:.26, 240:.19, 260:.14, 280:.10, 300:.07, 320:0
- **Wink:** 0:0, 20:.07, 40:.25, 60:.50, 80:.75, 100:.93, 120–420:1, 440:.82, 460:.67, 480:.55, 500:.45, 520:.37, 540:.30, 560:.25, 580:.20, 600:.17, 620:.14, 640:.11, 660:.09, 680:.07, 700:.06, 720:0

Lid position = `level + (shut − level)·closure`. These fractions are of servo travel. The lid bars make lid travel non-linear in servo angle (build-notes, #213).

## 4. Servo constraint (428 °/s, 22° rest to shut)

**The servo can match the human closing time, but not the human peak speed.**

- **Peak speed:** scaled to 22° of servo travel, a spontaneous peak needs 27 × 22 ≈ 580 °/s and a voluntary one 36 × 22 ≈ 800 °/s. Both exceed 428 °/s.
- **Duration:** the human close averages 22/0.092 ≈ 240 °/s. The servo covers 22° in 51 ms, ~60–75 ms with a PWM frame and acceleration: inside the human 75–92 ms. Its flat speed replaces the bell, invisible at this length.
- **The 80 ms bell is at the limit:** its peak is π/2 × 22/0.08 ≈ 430 °/s, and at 20 ms steps it is only 4 points.

**What to do:**
- **Close as a step,** as `blink()` already does. If it looks harsh, send 0.5 and then 1.0 one frame later.
- **Interpolate only the opening and slow closes.** The wink's 120 ms bell peaks at ~290 °/s, which is fine.
- **Opening:** τ = 60 starts at ≤370 °/s, within rating. The current `(1−f)²` over 300 ms is close to [V]; an exponential adds [K]'s long tail.
- **Time a real close on the Mech:** the rating is no-load; lid friction and the slip clutch slow it.

Unverified: Evinger 1991 and Doane 1980 are cited second-hand, Baker 2005 from its abstract only, and I found no wink kinematics.
