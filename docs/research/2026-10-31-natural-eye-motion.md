# Natural eye and eyelid motion for a 4-servo eye pair

Researched 2026-10-31. Target: two eyeballs (pan only), two lids (open/close). Servo limit: ~60 deg in ~100 ms at best.
Claims are tagged with the source URL. Numbers I could not verify against a primary source are marked "unverified".

## 1. Blink kinematics

- Closing is much faster than opening. High-speed (600 fps) video of voluntary blinks, 25 adults: closing phase 76 +/- 2 ms,
  closed phase 58 +/- 4 ms, opening phase 438 +/- 24 ms (early opening ~165 ms, late opening 273 +/- 23 ms), total 572 +/- 25 ms;
  97% reopened at 299 +/- 8 ms after onset. Peak closing speed 243 mm/s vs peak opening 157 mm/s; average closing speed ~5x average opening.
  Kwon et al. 2013, J R Soc Interface. https://pmc.ncbi.nlm.nih.gov/articles/PMC4043155
- Spontaneous blinks, 8 volunteers: opening 0.21 +/- 0.04 s vs closing 0.10 +/- 0.02 s. https://link.springer.com/doi/10.1007/s00417-007-0611-8
- Optoelectronic study, 44 adults: closing 40-47% faster than opening; rate 19/min women vs 11/min men; young men close fully
  only ~44% of the time, i.e. many blinks are incomplete. Sforza et al. 2008. https://pubmed.ncbi.nlm.nih.gov/18565090/
- Spontaneous blinks are longer and more variable than reflex ones; blink duration depends on vertical gaze (shortest at 30 deg up,
  longest at 30 deg down). VanderWerf et al. 2003, J Neurophysiol 89:2784. https://pubmed.ncbi.nlm.nih.gov/12612044/
  (Abstract has no ms figures; full text not reached.)
- Animation reference: natural blinks are asymmetric in time and amplitude (fast close, slow asymptotic open); viewers rate the
  asymmetric, fully-closing model as more natural than symmetric linear or ease-in/out blinks. Three actors at 300 fps: blink rates
  8.2, 27.0 and 6.6/min; example blink duration 101 frames = ~337 ms. Trutoiu et al. 2011, ACM TAP.
  https://la.disneyresearch.com/wp-content/uploads/Modeling-and-Animating-Eye-Blinks-Paper.pdf
- Rates by activity (150 healthy volunteers, video): ~17/min at rest, ~26/min conversation (+99.7%), ~4.5/min reading (-55%).
  Bentivoglio et al. 1997, Mov Disord. https://pubmed.ncbi.nlm.nih.gov/9399231/
  Review ranges: conversation 11-36/min, reading 4-14/min, rest 5-26/min. https://pmc.ncbi.nlm.nih.gov/articles/PMC7281572/table/life-10-00061-t001
- Cognitive load: blink rate falls when a task taxes cognitive resources; blinks cluster at the end of a sentence, after a decision,
  during saccades, after a manual response. Stern, Walrath & Goldstein 1984, Psychophysiology 21:22-33 (cited via
  https://dspace.lib.cranfield.ac.uk/bitstream/1826/12547/1/Blink_counts_can_differentiate_between_task_type_and_load-2017.pdf
  and https://pmc.ncbi.nlm.nih.gov/articles/PMC4849103).
- Inter-blink interval is log-normal / strongly right-skewed; mean interblink time 5.2 +/- 3.1 s in a 1 h recording of controls;
  resting rates 13-14/min. https://www.pubmed.gov/21345986/ and https://www.sidalc.net/search/Record/oai:scielo:S0004-27492010000400005
- Double blinks: I found no primary source giving the proportion of spontaneous blinks that are doublets. Treat as a stylistic choice.
- Doane 1980 (Am J Ophthalmol 89:507) is the classic high-speed film study; I could not reach its numbers. https://scilit.net/publications/167171113ab3643b5ab0c4f1ea9e3f8a

## 2. Saccades

- Main sequence: duration rises roughly linearly with amplitude; peak velocity saturates. Commonly quoted D = 21 + 2.2*A ms is attributed
  to Carpenter 1988, while Bahill's own regression was closer to D = 37 + 2.7*A (Collewijn: 23 + 2.7*A).
  https://www.mdpi.com/1995-8692/10/3/17 and https://link.springer.com/10.3758/s13428-020-01388-2
  Linear up to ~80 deg but most natural saccades are <= 15-20 deg. https://iris.unige.it/retrieve/e268c4ce-65fa-a6b7-e053-3a05fe0adea1/Main_Sequence_BRM%20%28revised%29.pdf
  Example: a 10 deg horizontal saccade ~300 deg/s peak, ~50 ms. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8960849/
  Using D = 21 + 2.2*A: 10 deg = 43 ms, 20 deg = 65 ms, 30 deg = 87 ms (Bahill form: 64 / 91 / 118 ms).
- Saccades reach peak velocity after a roughly fixed ~20-25 ms acceleration phase regardless of amplitude. https://pmc.ncbi.nlm.nih.gov/articles/PMC2323107
- Gaze shifts are usually a primary saccade that slightly undershoots, then one small corrective saccade when the target lands off-fovea;
  without a visual error the probability of a corrective saccade is low but rises with eccentricity. Hypometria minimises total flight
  time. https://springerlink.bibliotecabuap.elogim.com/content/pdf/10.1007/BF00344150.pdf and https://pmc.ncbi.nlm.nih.gov/articles/PMC3784029
  (No primary source reached for glissade/post-saccadic drift magnitudes.)
- Fixation durations in free viewing: mean ~240 ms, quartiles ~100 and ~300 ms. https://www.nature.com/articles/s41598-022-10605-1.pdf
- "Thinking" eye movements: people move their eyes about twice as often while searching long-term memory as in tasks without such search;
  the movements are non-visual and probably epiphenomenal. Ehrlichman & Micic 2012, Curr Dir Psychol Sci 21:96.
  https://www.psychologicalscience.org/journals/current-directions/0963721412436810/
- Animation model: Eyes Alive (Lee, Badler & Badler 2002) fits saccade magnitude, direction, duration and inter-saccadic interval
  separately for talking and listening; a secondary source gives its duration model as dt = d*theta + D0 with d in [2, 2.7] ms/deg,
  D0 in [20, 30] ms. https://history.siggraph.org/?p=118454 and https://arxiv.org/pdf/1804.00970

## 3. Eye-lid coupling

- Vertical: lid "saccades" replicate eye saccades in time course; they start ~5 ms after the eye, peak at the same time; downward lid and
  eye saccades match, upward lid saccades are smaller and slower. At steady fixation the lid can drift idiosyncratically up to 5 deg.
  Becker & Fuchs 1988, J Neurophysiol 60:1227. https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=%22Lid-eye%20coordination%20during%20vertical%20gaze%20changes%22&resultType=core&format=json
- Horizontal: no primary source found that reports systematic upper-lid displacement with purely horizontal gaze; lid-eye coordination
  literature is vertical. For horizontal-only eyes, the lid behaviour that accompanies a large gaze shift is the gaze-evoked blink, not a
  lid position change. https://core.ac.uk/download/18513071.pdf
- Gaze-evoked blinks: orbicularis oculi activity occurred with 97% of saccadic gaze shifts > 33 deg, starting with the eye/head movement;
  with eyes closed, all head turns > 17 deg produced it, ~39 ms before head onset. Evinger et al. 1994, Exp Brain Res.
  https://pubmed.ncbi.nlm.nih.gov/7813670/
  Frequency rises with gaze amplitude and falls when the target matters (task relevance suppresses it).
  https://sites.pitt.edu/~neg8/rajimages/pdf/EBR-11-0590R1.pdf and https://pubmed.ncbi.nlm.nih.gov/15342723
- Animation rule of thumb (Williams-derived, secondary): blink whenever the eyes change direction or on a head turn; a standard blink
  ~2 frames close, 1 hold, 3 open at 24 fps (~83 / 42 / 125 ms); longer blink for a change of thought, fast blink for anxious/angry.
  https://www.bloopanimation.com/blinking-animation/ and https://animationapprentice.blogspot.com/2020/09/do-animated-characters-need-to-blink.html

## 4. Behaviours

- Thinking / gaze aversion: adults and children avert gaze from the questioner while thinking; aversion increases with question
  difficulty and improves answer accuracy; primary function is managing cognitive load. Doherty-Sneddon & Phelps 2005; Doherty-Sneddon
  et al. 2012. https://researchportal.northumbria.ac.uk/en/publications/gaze-aversion-a-response-to-cognitive-or-social-difficulty/
  and https://researchportal.northumbria.ac.uk/en/publications/gaze-aversion-as-a-cognitive-load-management-strategy-in-autism-s/
  Glenberg, Schroeder & Robertson 1998 is cited for the same claim; I could not reach its abstract.
- Direction: left/right does not reliably code question type; difficulty predicts movement/stare more than direction; handedness mirrors
  the pattern. Verbal questions elicited more eye movements than spatial ones; difficult-question reflection latencies ~14-17 s.
  https://link.springer.com/article/10.3758/BF03196967 and https://www.thenakedscientists.com/node/170432
  Takeaway: pick a side randomly, hold it, do not encode meaning in direction.
- Surprise / "aha": FACS surprise = AU1+2+5(+25/26): brows up, upper lid raised so sclera shows above the iris; surprise is the
  briefest of the basic expressions. https://facsref.ucsd.edu/ and https://arxiv.org/pdf/2307.06396
  No primary source found for an "insight" expression distinct from surprise; use widened lids + a held stare.
- Bored / drowsy: blink duration and reopening time rise reliably with drowsiness, as does the proportion of long-closure blinks
  (60 adults). Caffier et al. 2003; blinks valid 50-500 ms, closing < 150 ms. https://link.springer.com/doi/10.1007/s00421-003-0807-5
  Blink duration typically 0.1-0.5 s but 2-3 s when falling asleep. https://research.usq.edu.au/download/061ee5f254074a2db3f35720d30aaeaf5868b2f4db973765de29df44d2d13d6f/374449/Watling%26Smith%202013%20In%20the%20blink%20of%20an%20eye.pdf
  PERCLOS: drowsiness scored as time the lid covers > 80% of the pupil; episodes get more frequent and longer with sleep loss.
  https://trid.trb.org/View/498744 and https://pmc.ncbi.nlm.nih.gov/articles/PMC4957187
- Attention / alert: FACS AU5 (lid raise) is the wide-eyed component; cognitive load lowers blink rate (section 1), so "alert" = wide
  lids + rare blinks.
- Wince: the blink literature describes reflex/air-puff blinks as the shortest and least variable closures (VanderWerf 2003 above);
  a wince is a held closure, for which I found no kinematic primary source. Use closing-phase speed then hold.

## 5. Datasets (replay candidates)

| Dataset | Records | Rate | Gaze time series? | License | Source |
|---|---|---|---|---|---|
| GazeBase | fixation, horizontal saccade, random saccade, reading, 2 free-viewing videos, game; 322 people | 1000 Hz, deg of visual angle | yes, raw | not stated on pages I could reach (figshare returned 403) | https://pymovements.readthedocs.io/en/v0.26.2/datasets/GazeBase.html , https://arxiv.org/abs/2009.06171 |
| Hollywood-clip free viewing (Schepens, OSF) | gaze x/y, sample times, pupil | 1000 Hz | yes, MATLAB | "without restriction for research and education" with citation | https://pmc.ncbi.nlm.nih.gov/articles/PMC6693682 |
| EYEDIAP | RGB-D video, frame-by-frame head pose, 3D eye pos, target | 30 fps | yes but coarse | EULA, non-commercial, academic staff request | https://idiap.ch/dataset/eyediap |
| MPIIGaze | laptop images + gaze labels | sparse snapshots | no | CC BY-NC-SA 4.0 | https://arxiv.org/pdf/1711.09017 |
| GazeCapture | phone/tablet frames + gaze point | ~frames, no continuous | no | research-only license, registration | https://github.com/saswat0/GazeCapture |
| RT-BENE | per-image blink labels | n/a | blink labels only, no timing series | CC BY-NC-SA 4.0 | https://zenodo.org/records/3685316 |
| Eyeblink8 / ZJU / TalkingFace | 353 / ~? / 616 blinks, frame-annotated video | 30 fps | blink events only | license not found | https://arxiv.org/pdf/1902.07891 |

Assessment: GazeBase's horizontal-saccade and video tasks are the only thing that would replay cleanly (1 kHz horizontal angle).
Everything else is per-frame classification or gaze-point data meant for appearance models, not kinematics. Replay is not worth it:
the behaviours we need (eureka, bored, wince) are not in any corpus, the servos cannot reproduce sub-50 ms saccade dynamics anyway,
and the kinematic parameters below reconstruct natural-looking motion with a few dozen lines. If a "random natural idle" is ever
wanted, sample GazeBase saccade amplitudes and fixation durations offline and bake a short table; do not ship the dataset.

## Parameters for noggin

Servo note: 60 deg in ~100 ms means lid close (~75-100 ms over ~45 deg of lid travel) is at the edge of what the servo does; command
it as a step and let the servo's own slew provide the close. Opening must be glided over 200-400 ms in software. Eye saccades of
10-30 deg at 43-90 ms are also roughly servo slew speed; step them, then glide the tail.

- Blink: close 80-100 ms (step), hold 50-60 ms, open 250-400 ms with ease-out (fast first ~40% then asymptotic). Total ~400-550 ms.
  Partial blinks (60-80% closure) for ~40% of blinks is realistic but optional.
- Rest blink interval: log-normal, median ~3.5 s, mean ~4-5 s (12-17/min), clamp 1-12 s. "Conversation" mode ~2.3 s mean (26/min).
  Never re-trigger inside 1 s except as a deliberate double blink.
- Double blink: no primary evidence for a natural rate; use it as a stylised "eureka" punctuation only, second blink 150-250 ms after
  the first reopens.
- Saccade duration: D_ms = 21 + 2.2 * A_deg (10 deg 43 ms, 20 deg 65 ms, 30 deg 87 ms). Land 5-10% short, then a corrective
  saccade of the remainder after a 100-150 ms pause (optional at this scale).
- Thinking drift: avert 15-25 deg to one side (random side, keep it for the gesture), optionally a small "up" cue is unavailable so
  add 2-5 deg of lid narrowing instead. Fixations 250-600 ms between 3-8 deg micro-shifts, 1-3 shifts per second; blink rate low
  (one blink per 5-8 s), hold 2-4 s then return.
- Gaze-evoked blink: p = 0.9 for shifts >= 30 deg, p ~ 0.3 for 15-30 deg, none below 15 deg. Start the blink with the saccade onset,
  not after.
- Bored / drowsy: blink close 150-250 ms, hold 300-800 ms, open 600-1200 ms; between blinks lids rest at 60-70% open; every 3rd-4th
  blink a 1.5-3 s closure with a slow reopen; eyes centred or slightly drifted, no saccades.
- Attention / alert: lids to 100% (past normal rest), eyes snap to centre, blink suppressed for 3-5 s, then one fast blink.
- Wince: close in the fastest step the servos give, hold 300-600 ms (both lids), reopen 200 ms to ~80% then settle; eyes centred.

Order of operations per gesture:
- eureka: lids wide (step) -> saccade 20-25 deg up/aside (step; gaze-evoked blink with p=0.9 at this amplitude, but skip it so the
  widened eyes read) -> hold 500-600 ms -> saccade back to centre with corrective tail -> blink, blink (double, 200 ms gap) ->
  lids ease to rest over 300 ms. ~2 s.
- attention: lids half (glide 200 ms) -> slow sweep L->R->L at ~20 deg/s (pursuit-like, not saccadic), two passes -> centre ->
  lids open to rest, one blink. ~3 s.
- bored: lids to 65% over 500 ms -> drowsy blink cycle as above for the gesture length -> optional one long 2 s closure -> settle.
- wince: both lids snap shut -> hold 400 ms -> reopen to 80% in 200 ms -> rest.
- thinking: gaze-evoked blink + saccade to side (one event) -> micro-fixation drift 2-4 s with sparse blinks -> saccade back + blink.
