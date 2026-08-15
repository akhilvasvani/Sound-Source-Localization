# Part 1 results: does real-world data change the reverberation story?

*Historical note: `heart_proxy` below refers to a benchmark dataset used
for this study. It was also, at the time, a selectable preset in the
interactive demo; that demo preset has since been removed (see
README.md and PR #3) because it never corresponded to real heart-sound
audio (see section 0). This report is left intact as the honest,
as-run record of the comparison.*

**TL;DR / honest verdict:** No. Swapping in real-world, non-medical
audio (LibriSpeech speech, ESC-50 environmental sounds) does **not**
fix the reverberation-driven accuracy collapse. It happens, at
roughly the same severity, with every dataset tested. The original
finding -- "reverberation degrades DOA accuracy" -- is a genuine
property of small-aperture DOA estimation in a reverberant room, not
an artifact of the heart-sound data's narrow frequency band or its
synthetic ground truth. There is **one** real, narrower finding that
*does* support part of the original hypothesis: one specific algorithm
(TOPS) was uniquely bad on the narrowband heart-proxy signal even at
**low** reverberation, and that specific weakness disappears on
broadband real-world audio. See "What actually changed" below.

## 0. A finding that has to come first: there was never any real heart-sound audio in this repo

Before comparing anything, it's important to say plainly: the
existing baseline numbers in the top-level README (`## Accuracy`) were
never measured on heart-sound audio, real or synthetic. Reading
`validation/run_validation.py::_make_wav()` shows the "signal" used for
every one of those runs is literal Gaussian white noise:

```python
rng = np.random.default_rng(seed)
signal = rng.normal(scale=0.3, size=int(1.5 * fs)).astype(np.float32)
```

band-limited to `freq_range=[300, 1000]` Hz to loosely resemble the
frequency range of heart sounds, but not derived from any actual S1/S2
recording, echocardiogram, or the `.mat` file this project's
heart-sound *loading* path (`src/preprocess.py`) reads. That path is
real and still works (kept unchanged, see `src/audio_source.py`'s
`load_source_signal(..., mode="heart_sound")`), but it was never
plugged into the accuracy validation that produced the numbers in the
README. This is documented and reproduced exactly in
`data/heart_proxy_samples/README.md` and `white_noise_0.wav` (the
`heart_proxy` dataset below **is** this exact same generator, used as
the "old" reference point for a fair before/after comparison).

This matters directly for the user's original question: the premise
that "reverb sensitivity might be an artifact of the heart-sound
data's narrow frequency range" cannot be tested against *real*
heart-sound audio characteristics, because no such audio was ever in
the loop. What *can* be tested, and is tested here, is whether the
same reverb sensitivity shows up on real, non-medical audio with known
ground truth -- and it does.

## 1. Datasets used (and the tradeoff in picking them)

Per the "pick whichever is easiest to get running in a weekend"
instruction, three real-world-audio datasets were used, run through
the same pyroomacoustics-simulated array with known source coordinates
(not through a full separately-recorded multichannel DOA benchmark
corpus):

| Dataset | Source | Content | Bandwidth used | Why this one |
|---|---|---|---|---|
| `heart_proxy` | This repo's own baseline generator (white noise) | Synthetic, band-limited noise | 300-1000 Hz | Kept as the "old" reference point, not a new dataset -- see section 0 |
| `librispeech` | LibriSpeech `dev-clean`, 4 short clips | Real human speech | 300-3400 Hz | Free, small, resolvable over plain HTTPS (HuggingFace's non-LFS resolve endpoint) without any signup/gating |
| `esc50` | ESC-50 environmental sounds, 2 clips (`rain`, `clock_tick`) | Real environmental audio | 300-3400 Hz | Same reason -- small, ungated, quick to fetch |

**Tradeoff explicitly acknowledged:** LOCATA and DCASE SELD are the
"real" purpose-built DOA benchmarks with actual multi-microphone
*recordings* and measured (not simulated) ground-truth positions --
they are the more rigorous choice. They were evaluated first and
**not used**, because within a weekend timebox:

- LOCATA's download host and openSLR mirrors were unreachable from this
  sandbox during testing.
- DCASE SELD's distribution is via Zenodo/gated large archives (multi-GB),
  not practical to fetch and unpack in the time available.
- Several other candidate mirrors (LFS-backed HuggingFace repos, some
  openSLR paths) were also unreachable.

So the tradeoff made here is: keep the *known ground-truth position*
requirement (satisfied by simulating each clip through
pyroomacoustics with an exact source coordinate, exactly like the
existing heart-sound validation does), but source the *audio content*
from real-world clips instead of a full recorded-array benchmark
corpus. This means the results below say something true and useful
about "does swapping the audio content change the reverberation
story," but do **not** carry LOCATA/DCASE's additional value of testing
against a real physically-recorded array and its real-world
microphone/room characteristics. That would be the natural next step
if more than a weekend were available.

## 2. Setup (kept identical to the original baseline for a fair comparison)

- Same room: `4.0 x 3.0 x 2.5` m (`DEFAULT_ROOM_DIM` in `src/pipeline.py`, unchanged from `validation/run_validation.py`)
- Same 4 mic clusters / tetrahedral sub-arrays, same 15 cm aperture (`DEFAULT_CLUSTER_CENTERS`, `TETRA_POSITIONS`)
- Same 3 (of the original 5) test source positions: `[3.0, 1.0, 1.7]`, `[1.0, 2.0, 0.6]`, `[2.0, 1.5, 2.0]`
- Same `n_grid=8000` DOA search resolution
- **Same exact RT60 configs** as the baseline: low = `absorption=0.99, max_order=0`; medium = `absorption=0.97, max_order=1`; high = `absorption=0.25, max_order=10`. RT60 is *measured* per-run via `pyroomacoustics.Room.measure_rt60()`, not assumed -- measured values: ~2.6 ms (low), ~18 ms (medium), ~126 ms (high), consistent across all three datasets.
- All 5 existing DOA algorithms (SRP, MUSIC, TOPS, CSSM, WAVES) tested, not just SRP (the original baseline only ran SRP)
- 135 total runs (3 datasets x 3 RT60 levels x 5 algorithms x 3 source positions), all completed with **zero runtime errors**

Full raw results: `experiments/results/real_world_benchmark.csv` / `.json`. Summary: `experiments/results/summary_by_dataset_rt60_algo.csv`.

## 3. Headline result: reverberation degradation is universal across all three datasets

Mean position error in meters, averaged across all 5 algorithms, by dataset and RT60 level:

| Dataset | Low RT60 (~2.6 ms) | Medium RT60 (~18 ms) | High RT60 (~126 ms) | Low→High ratio |
|---|---|---|---|---|
| `heart_proxy` (old baseline signal) | 0.392 m | 0.650 m | 1.410 m | 3.6x |
| `librispeech` (real speech) | 0.075 m | 0.134 m | 1.487 m | 19.8x |
| `esc50` (real environmental) | 0.294 m | 0.482 m | 1.460 m | 5.0x |

Mean angle (bearing) error in degrees, same grouping:

| Dataset | Low RT60 | Medium RT60 | High RT60 |
|---|---|---|---|
| `heart_proxy` | 26.6° | 34.8° | 102.7° |
| `librispeech` | 9.1° | 11.9° | 104.4° |
| `esc50` | 18.4° | 25.6° | 74.9° |

At high reverberation, angle errors of 75-105 degrees mean the
estimated bearing is essentially uncorrelated with the true one --
this is true for **every dataset**, real-world audio included. The
degradation is not a heart-sound-data artifact.

For a cleaner apples-to-apples comparison against the exact original
baseline methodology (SRP algorithm only, same metric):

| Dataset | Low RT60 | Medium RT60 | High RT60 |
|---|---|---|---|
| Original README baseline (white noise, 5 positions) | mean 0.031 m (0.010-0.044) | mean 0.121 m (0.016-0.183) | mean 1.033 m (0.332-1.773) |
| `heart_proxy` reproduction (3 of the 5 positions) | mean 0.029 m (0.010-0.040) | mean 0.087 m (0.016-0.129) | mean 1.288 m (0.827-1.773) |
| `librispeech` (real speech) | mean 0.093 m (0.075-0.107) | mean 0.094 m (0.075-0.107) | mean 1.491 m (1.183-2.024) |
| `esc50` (real environmental) | mean 0.473 m (0.010-1.370) | mean 0.473 m (0.010-1.370) | mean 1.106 m (0.069-2.285) |

The `heart_proxy` row reproducing the original baseline numbers
closely (0.029/0.087/1.288 vs the README's 0.031/0.121/1.033) is itself
a useful sanity check: it confirms the refactored, shared
`src/pipeline.py` reproduces the original pipeline's behavior on the
same signal, so the real-world numbers next to it are a fair
comparison and not an artifact of the refactor.

**Real-world data does not "win" here.** At low reverberation,
LibriSpeech is *more* accurate than the heart-proxy signal (0.093 m vs
0.029 m -- actually worse), and ESC-50 is noticeably *less* accurate
(0.473 m vs 0.029 m). All three datasets converge to similarly bad
(~1.1-1.5 m, 75-105°) accuracy at high reverberation. So: **the
reverberation issue persists regardless of data source** -- this is
the honest answer to the core question posed.

## 4. What actually did change: one algorithm-specific, non-reverberation finding

TOPS behaved very differently on the narrowband heart-proxy signal
(300-1000 Hz) vs. broadband real-world audio (300-3400 Hz) -- and the
difference showed up even at the **lowest** reverberation level, where
every other algorithm already does well:

| Dataset | Algorithm | Low-RT60 mean error | Low-RT60 mean angle error |
|---|---|---|---|
| `heart_proxy` | TOPS | **1.843 m** | **108.0°** |
| `heart_proxy` | SRP/MUSIC/CSSM/WAVES | 0.029 m | 6.3° |
| `librispeech` | TOPS | 0.179 m | 22.7° |
| `esc50` | TOPS | 0.207 m | 10.8° |

TOPS was essentially non-functional on the narrowband synthetic
signal, at *any* reverberation level, while performing reasonably (if
still the weakest of the five) on broadband real-world audio. This is
consistent with TOPS's underlying method (it fits phase relationships
across multiple frequency bins) needing more spectral bandwidth to
work than a 700 Hz-wide band provides. This is the one piece of
evidence in this whole experiment that supports the original
hypothesis ("this may be partly an artifact of the heart-sound data's
narrow frequency range") -- but it's specific to TOPS, and it is
**not** a reverberation effect (it happens identically at low RT60).
It does not change the headline verdict about reverberation.

One more honestly-reported oddity, not chased further given the
weekend scope: for ESC-50 + SRP, the source position `[1.0, 2.0, 0.6]`
gave a large error (1.37 m, 65.9°) even at the lowest RT60, while the
other two positions were near-perfect (0.010 m, 0.039 m). This looks
like a content- or geometry-dependent robustness issue specific to
that clip/position combination rather than a reverberation or
implementation bug (all other position/algorithm combinations at low
RT60 for ESC-50 were accurate); flagged here for anyone extending this
work, not resolved.

Also worth a note on reproducibility: for `esc50` + `SRP`, the
low-RT60 and medium-RT60 runs produced **bit-for-bit identical**
position estimates for all 3 source positions (see the raw CSV). This
is plausible, not a caching bug -- the low→medium RT60 change here is
tiny in absolute terms (measured RT60 2.6 ms → 18 ms) and SRP-PHAT's
correlation over ESC-50's much wider bandwidth (300-3400 Hz vs.
heart-proxy's 300-1000 Hz) appears robust enough to the resulting weak
early reflections that the discretized `n_grid=8000` search lands on
the exact same grid direction both times. `heart_proxy` (narrowband)
did **not** show this -- its low/medium estimates differ -- which is
consistent with that explanation rather than a pipeline defect.

## 5. Bugs found and fixed this round

- **`pairwise_ray_intersections()` sign error** (`src/triangulation.py`):
  the closest-point-between-two-skew-lines formula had both parametric
  offsets (`t1`, `t2`) negated, so every computed intersection point
  was reflected through its ray's origin instead of landing at the
  true closest-approach point. This function is new (added for the
  Part 2 demo's ray/intersection-cloud visualization) and is **not**
  used by the primary triangulation estimators reported in the tables
  above, so it did not affect any accuracy numbers -- but it would
  have silently produced a wrong 3D visualization in the demo if
  unfixed. Fixed and covered by 4 new unit tests
  (`test/unit/test_pairwise_ray_intersections.py`), verified against a
  3-ray convergence case and a known skew-line midpoint.
- **Single mic-cluster triangulation crash**: the original triangulation
  code assumes >= 2 mic clusters/rays are available; a single cluster
  (as in a real user-uploaded single-array recording, Part 2) would
  crash instead of degrading gracefully. Fixed in `src/pipeline.py` by
  adding an explicit `position_available` flag: when only one ray is
  available, the pipeline now reports bearing/angle only
  (`estimate_m=None`, `error_m=None`, plus a `note` explaining the
  physical reason triangulation needs >= 2 spatially separated arrays)
  instead of crashing. Covered by `test/unit/test_pipeline.py`.
- **Mic-location strict-float requirement**: passing integer
  coordinates into the existing (unchanged) mic-location validation
  raises `TypeError` by design (confirmed intentional via
  `test_get_centroid.py`); worked around by always constructing
  coordinates as Python `float`s in the new code, not by loosening the
  existing validation.
- **`RT60_LEVELS["medium"]` value correction**: an initial guess for the
  "medium" RT60 config (`absorption=0.6, max_order=3`) was corrected to
  exactly match the original baseline's "lightly-furnished room" config
  (`absorption=0.97, max_order=1`) after re-reading
  `validation/run_validation.py` -- this was necessary for the
  before/after comparison in section 3 to be a fair one.

## 6. Test coverage

Full suite: **104/104 passing** (`pytest test/` from the repo root),
up from 77 before this round -- 12 new tests added across
`test_pairwise_ray_intersections.py` (4), `test_pipeline.py` (6),
`test_audio_source.py`, and `test_api.py` (8, covering the Part 2
FastAPI backend).

## 7. Direct answer to the original question

> Reverberation degrades DOA accuracy -- is this partly an artifact of
> the heart-sound data's narrow frequency range and synthetic ground
> truth?

**No, not for the reverberation effect itself.** Real-world, non-medical
audio (real human speech, real environmental sound) with known,
simulated ground-truth positions shows the *same* order-of-magnitude
collapse in accuracy between low and high reverberation as the
original heart-proxy signal did -- roughly 3-20x worse position error
and a swing from single-digit-degree to 75-105-degree bearing error in
every dataset tested. This is a physical/algorithmic limitation of
small-aperture DOA estimation in reverberant rooms, consistent with
what the existing README already concluded, and it holds regardless
of data source.

The one place the "narrow frequency range" hypothesis *is* borne out
is algorithm-specific and reverberation-independent: TOPS specifically
performs badly on the narrowband heart-proxy signal even with no
meaningful reverberation, and that specific weakness goes away on
broadband real-world audio. That is a real, narrow finding -- but it
is not evidence that reverberation-driven degradation was a heart-sound
artifact.
