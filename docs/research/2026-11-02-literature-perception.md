# Perception and appeal for the next Mech's face

Researched 2026-11-02. Purpose: test #51's face choices against perception research. The choices are linked eyes, a big head on a small base, Pure White eyes with black pupils, separate lids, and gestures timed for a few servos. Builds on `2026-10-31-natural-eye-motion.md`, `2026-11-01-blink-kinematics.md` and `2026-11-01-toon-eyes.md`. Their timing numbers (Williams, Thomas & Johnston, Lasseter, blink kinematics) are not repeated here.

Tags: [A] = abstract only (paywalled or not reached), [P] = preprint or conference abstract, [I] = my inference or arithmetic.
Geometry used: eye centres 59 mm apart (model/geometry.py `EYE_R`), viewer 0.5–1 m away at a desk (inferred).

Sources:
- [G] Glocker et al. 2009, Ethology 115:257, full text (UPenn author copy). https://doi.org/10.1111/j.1439-0310.2008.01603.x
- [HB] Hinde & Barden 1985, Anim Behav 33:1371 (OCR'd scan). https://doi.org/10.1016/S0003-3472(85)80205-0
- [Al] Alley 1981, Dev Psychol 17:650 [A]. https://doi.org/10.1037/0012-1649.17.5.650
- [GH] Gamer & Hecht 2007, J Exp Psychol HPP 33:705, full text. https://doi.org/10.1037/0096-1523.33.3.705
- [LH22] Linke & Horstmann 2022, Perception 51:789 [A]. https://doi.org/10.1177/03010066221122359
- [LH24] Linke & Horstmann 2024, Perception 53:93 [A]. https://doi.org/10.1177/03010066231212156
- [N] Nguyen et al. 2018, J Exp Psychol Gen 147:1125 [A]. https://doi.org/10.1037/xge0000398
- [Ot] Otsuka et al. 2014, J Exp Psychol HPP 40:1425 [A]. https://doi.org/10.1037/a0036151
- [La] Larson, Keech & Verdick 2003, J AAPOS 7:418 [A]. https://doi.org/10.1016/j.jaapos.2003.09.011
- [KK] Kobayashi & Kohshima 2001, J Hum Evol 40:419 [A]. https://doi.org/10.1006/jhev.2001.0468
- [R] Ricciardelli, Baylis & Driver 2000, Cognition 77:B1 [A]. https://doi.org/10.1016/S0010-0277(00)00092-5
- [Wh] Whalen et al. 2004, Science 306:2061 [A]. https://doi.org/10.1126/science.1103617
- [LA] Lee & Anderson 2017, Psychol Sci 28:494 [A]. https://doi.org/10.1177/0956797616687364
- [Ta] Takashima et al. 2008, Graphics Interface 169–176 [A]. https://dl.acm.org/doi/10.5555/1375714.1375744
- [Hö] Hömke, Holler & Levinson 2018, PLoS ONE 13:e0208030 [A]. https://doi.org/10.1371/journal.pone.0208030
- [M] Mori 1970, authorised translation 2012, IEEE RAM 19(2):98. https://spectrum.ieee.org/the-uncanny-valley
- [MD] MacDorman et al. 2009, Comput Hum Behav 25:695 [A]. https://doi.org/10.1016/j.chb.2008.12.026
- [SN] Seyama & Nagayama 2007, Presence 16:337 [A]. https://doi.org/10.1162/pres.16.4.337
- [K] Kätsyri et al. 2015, Front Psychol 6:390 [A]. https://doi.org/10.3389/fpsyg.2015.00390
- [MR] Mathur & Reichling 2016, Cognition 146:22 [A]. https://doi.org/10.1016/j.cognition.2015.09.008
- [TDJ] Takayama, Dooley & Ju 2011, HRI '11 69–76, full text. https://doi.org/10.1145/1957656.1957674
- [L] Lasseter 1987 and [TJ] Thomas & Johnston 1981: as cited in `2026-11-01-toon-eyes.md`.

## 1. Appeal: head, eyes, pupils, lids

- **Baby schema raises cuteness and the urge to care [G].** High schema means a round face, high forehead, large eyes and a small nose and mouth.
  - Manipulations stayed within ±2 SD of 40 real infant faces.
  - Eye width / face width averaged 18.5% (SD 0.9), so the high-schema end is at most ~20.3%.
  - Cuteness: F(2,59) = 137.3, p < .001, with high > unmanipulated > low; no sex difference in cuteness ratings.
  - [G] did not test values past the natural range, so it says nothing about cartoon proportions.
- **Head:** perceived cuteness falls as head shape ages (cardioidal strain) [Al]. Teddy bears changed over 1903–1985 toward a larger forehead and shorter snout [HB], from only 15 bears.
- **Mech, inferred:** two caps "up to touching" on 59 mm centres give eyes ~59 mm wide each. On a ~150 mm head that is ~40% of face width per eye, twice the infant extreme [I]. That is a supernormal cartoon value: it works on a stylised face and turns eerie on a realistic one (§4).
- **White sclera exists to signal gaze [KK].** Humans have the largest ratio of exposed sclera among primates, and it is unpigmented. Gaze reading treats the darker region as the part doing the looking [R]: dark on light reads accurately, reversed polarity reads poorly.
  - Morty and Bart's black pupils on Pure White fit this.
  - Their small pupils leave a lot of white showing. A large visible white is a fear and alarm signal [Wh, amygdala response to fearful (larger) eye whites].
- **Lid position is the strongest single eye cue [LA].** Eye widening against narrowing explained 61.7% of the variance in perceived mental states, and the eyes still carried it against conflicting lower-face cues.
  - Widening reads as sensitivity: awe, interest, fear. Narrowing reads as discrimination: suspicion, disgust.
  - FACS surprise is sclera showing above the iris (natural-eye-motion §4).
- **Pupil shape (Morty jagged, Bart dots):** I found no perception study. It is style.

## 2. Gaze: where a two-eye face looks

- **The cone of direct gaze is wide and stable [GH].** People feel looked at across ~8–9° at 1 m (virtual head 9.3°, real head 8.1°), which is about ±4°. A real head at 5 m gave 3.9°.
  - The cone is far wider than acuity, whose difference thresholds are ~1°.
  - A 10° head turn pulled the real head's cone only 0.74° toward the head direction.
  - [Ot]: the head acts on perceived gaze in two ways. It repels gaze through the eye region and attracts it as a coarse direction cue; together they combine linearly.
- **Vergence tolerance [LH22]:** observers accepted ~3.5–4.5° of convergence and 2.5–3.5° of divergence as still "looking at me". The exact point of being looked at was 0°, which the abstract calls "parallel eyes".
  - I could not check whether 0° means truly parallel or converged on the observer.
- **Two-eye readings [LH24]:** the more rotated, inward-turned eye sets the judgement. Its direct-gaze area is ~4°, against ~6° for the outward-turned eye.
- **Bias toward convergence [N]:** observers see others' gaze as more convergent and nearer than it is, especially downward gaze or under uncertainty.
- **Misalignment detection [La]:** lay observers reliably detect a horizontal misalignment of 12.5 prism dioptres (PD), about 7.2°.
- **What linked eyes cost [I]:**
  - Converging on a viewer at 0.6 m needs 5.6° (9.8 PD), at 0.45 m 7.5° (13.1 PD), at 1 m 3.4°.
  - Parallel linked eyes are therefore inside the vergence tolerance from ~0.8 m out. They sit below the misalignment threshold down to ~0.5 m.
  - The real loss is near targets: the Mech cannot convincingly fixate anything closer than ~0.5 m, such as its own base or a phone beside it.
  - It also loses the cross-eyed gag.
- **Fixed toe-in [I]:** set the linkage to converge at ~1 m, 1.7° per eye toward the nose. Then 0.5–2 m stays within ±3.5° of the needed vergence, and it is also within [LH22]'s tolerance if their 0° means parallel.
  - At a 25 mm cap radius this is a 0.74 mm inward pupil offset. It can live in the pupil seats of the caps, with no gimbal change.
- **Pupil placement error [I]:** 1 mm of pupil slip on a 25 mm cap is 2.3° of gaze, half the cone. A magnet-held pupil that can slide or seat loosely moves where the eyes look.

## 3. Animation principles on position servos

- **Anticipation and reaction, tested on a robot [TDJ]** (PR2 videos, N = 273, 1–7 scales):
  - A visible "forethought" before acting raised appeal from 4.27 to 4.83, approachability from 4.54 to 5.05, and viewers' sureness of their reading from 5.20 to 5.69.
  - It did not raise the accuracy of that reading (keyword match, p = .37).
  - A reaction to the outcome made the robot seem smarter: 3.86 against 4.72.
  - So anticipation buys likability and confidence, not legibility. The legibility comes from the gesture's main pose.
- **Mapping each principle to a position servo [I, on TJ/L]:**
  - **Anticipation:** a small commanded counter-move before the main move.
  - **Overshoot and settle:** command past the target, then back. Do not rely on the servo's own overshoot, which is load-dependent.
  - **Slow in/out:** interpolated targets at 20 ms; lost on moves under ~3 ticks.
  - **Arcs:** start the two axes of a pair (eyes L/R + U/D, or pan + tilt) together but with offset easing, so the path curves instead of running straight.
  - **Secondary action:** lids follow vertical eye moves (Becker & Fuchs, natural-eye-motion §3), and the mouth follows head accents.
  - **Overlap:** the eyes start before the head on a turn. This is common animation practice; I found no primary source in scope.
  - **Timing and holds:** see toon-eyes §3–4 (the 1.67 s still limit, the 250 ms accent).
- **Motion can deepen the valley [M]:** Mori's smile slowed by half "turns creepy" and motion amplifies the peaks and valleys. [K] found that movement's modulating effect is not consistently supported.
  - [I]: scale Intensity by amplitude and keep the timing. Slowed-down gestures are the risky knob.

## 4. Uncanny valley and aliveness

- **The valley comes from mismatch, not from being a robot [K, SN, MD]:**
  - Mismatch between realistic and unrealistic features is the best-supported road into the valley. The naive "more human = eerie near the top" curve is not consistently supported [K].
  - Abnormal eyes are eerie only on faces that are otherwise realistic [SN].
  - Atypical proportions disturb more on photorealistic faces, and a mismatch of eye size or texture with the face is especially eerie [MD].
  - [MR] found the valley in likability across 80 real robot faces.
- **Mori's advice: aim for the first peak**, moderate human likeness such as toy robots and bunraku puppets [M]. A flat-colour cartoon head on a visibly mechanical neck sits there [I].
  - Its risk is internal mismatch: a realistic eye (glossy, textured iris, lashes) in a matte toon face [I from MD].
- **Blink rate shapes impressions [Ta]:** avatars were shown at 9, 12, 18, 24 and 36 blinks/min.
  - 18/min was friendliest, 9/min read as intelligent, 36/min as inactive.
  - The effect was larger on human-style avatars than on cartoon humans or animals.
  - The current thinking rate, one blink per 5–8 s (7.5–12/min), sits at the "intelligent" end.
- **Long blinks read as "got it" [Hö]:** a 607 ms listener blink, against 208 ms, made speakers give shorter answers, though none noticed the difference. It works as an acknowledgement.

## Practices for #51

1. Keep both characters fully stylised and consistent: flat matte PLA, no realistic iris texture, gloss or lashes on a toon face [MD, SN, K, M].
2. Black pupils on Pure White eyes, never reversed or low-contrast [R, KK].
3. Make the pupils keyed, not just magnet-held, to within ~0.5 mm, which is ~1° of gaze. A 1 mm slip costs half the 8° gaze cone [GH, I].
4. Converge the linked eyes at ~1 m: 1.7° per eye, or a ~0.7 mm inward pupil offset on 25 mm caps [LH22, N, La, I].
5. Hold the linked eye gimbal's play to ≤ ~2° (half the gaze cone) where it sets eye contact [GH, I].
6. Don't stage gestures that fixate within ~0.5 m (the base, a phone). Look at the user or far away [I from LH22].
7. Rest lid at or just over the top of the pupil, so no white shows above it. Show white above the pupil only for eureka and attention (widening = interest or awe), and narrow for thinking and wince [LA, Wh].
8. Big head, high forehead, small nose and mouth. The cranium electronics should push the forehead up, not the eyes down [G, Al, HB].
9. Anticipate before main moves and react after outcomes; expect appeal, not legibility, from it. Legibility needs a clear main pose [TDJ].
10. Scale Intensity by amplitude, not by slowing the gesture [M, I].
11. Blink near 18/min when engaged and ~9/min when thinking. Avoid ≥ 36/min except in flutter gags [Ta].
12. End attention and eureka with one long blink (~600 ms) as the "got it" beat [Hö].

## Conflicts with #51

- **No #51 decision is beaten by this evidence.** Linked eyes, the big head on a small base, white eyes with black pupils, separate lids and caps up to touching are all supported or neutral.
- **Linked eyes, cost bounded:** gaze reads as direct from ~0.5–0.8 m out (§2), and linkage only loses near targets and cross-eye gags.
  - Proposed addition (no servo or limit change): a fixed ~1 m toe-in, either in the gimbal's link geometry or in the caps' pupil seats (practice 4).
- **Gap:** #51 ranks gimbal candidates on simplicity, torque, fit, leads, tip-over and pack access, with no perceptual criterion.
  - Proposed: add "gaze error ≤ 2°, including play and pupil seating" as a pass/fail before the ranking (practices 3, 5).
- **Outside #51:** the glossary's Rest ("servos holding so the mech is still") conflicts with Thomas & Johnston's 1.67 s still limit (toon-eyes §1) and with [Ta]'s blink effect.
  - Proposed: a blink every 3–6 s at Rest, if servo noise and power allow. That is Cansin's call.

Unverified: [A] items rest on abstracts only.
- [LH22]'s "0° = parallel" geometry is unchecked.
- The "50% enlarged eyes" in [MD] came via a press summary, so I left it out.
- No source tests cuteness past natural proportions, or perception of pupil shape.
