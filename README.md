# Sound-Source-Localization-in-a-Reverberant Environment

Sound Source Localization in a Reverberant Environment was originally a
project for a master's degree at Johns Hopkins, aimed at locating S1/S2
heart sounds recorded by a microphone array (e.g. for automated heart-murmur
detection). I decided to expand this repository to estimate any sound
source's 3-D position by:

1. Computing a direction-of-arrival (DOA) bearing (azimuth + colatitude)
   from each of several small microphone clusters, using pyroomacoustics's
   DOA algorithms (SRP-PHAT by default; MUSIC/TOPS/CSSM/WAVES also
   supported).
2. Converting each cluster's bearing into a 3-D ray anchored at that
   cluster's centroid.
3. Triangulating all the resulting rays into a single 3-D position
   estimate (least-squares, Huber-robust, or RANSAC).

## Setup

```bash
git clone <this repo>
cd Sound-Source-Localization
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -e .          # installs `src`/`tools` as importable packages
```

Requires Python >= 3.8. See `requirements.txt` for pinned dependency ranges
(numpy, scipy, matplotlib, pyroomacoustics, pytest).

## Usage

Run the self-contained demo (generates a synthetic broadband test signal,
simulates a reverberant room, estimates the source location, and prints the
real measured error against the known, simulated source position):

```bash
python -m src.main
```

Run the full test suite:

```bash
pytest test/
```

Run the honest end-to-end validation (both the pure-geometry triangulation
check and the full acoustic pipeline, across several source positions and
reverberation levels -- see "Accuracy" below for what it reports):

```bash
python -m validation.run_validation
```

## Algorithm

Estimating a sound source's 3-D position works like this: get a direction
estimate from each microphone cluster, turn each direction into a 3-D ray,
and triangulate the rays into a position -- using pyroomacoustics for both
the underlying room/acoustic simulation and the DOA search itself.

### 1. Direction-of-arrival (DOA) per microphone cluster

A microphone array estimates direction from time differences of arrival:
the same sound reaches each microphone at a very slightly different time,
and that pattern of delays encodes the direction it came from. Given a
small set of nearby microphones (a "cluster"), pyroomacoustics's DOA
algorithms search over a grid of candidate directions and pick the one whose
predicted inter-microphone delays best match the recorded signals'
cross-correlation (SRP-PHAT) or spatial-covariance structure (MUSIC and
others). We use `src/sound_source_localization.py`'s
`get_difference_of_arrivals()` for this, wrapping
`pyroomacoustics.doa.algorithms`.

One coherent DOA cluster on its own only produces a bearing (an
azimuth/colatitude direction, i.e. a ray) -- not a unique 3-D position.
Turning a bearing into a position fix requires combining it with other,
independent bearings (step 2).

### 2. Ray triangulation (`src/triangulation.py`)

Each cluster's (centroid, direction) pair defines a 3-D ray. With multiple
rays from spatially separated clusters, the source is (in principle) at
their common intersection point -- but real DOA estimates are noisy, so the
rays generally do not intersect exactly, and geometry matters: rays from
clusters that are too close together or too co-planar constrain the
estimate weakly even when there are several of them. `src/triangulation.py`
finds the point minimizing (a robust function of) the sum of squared
perpendicular distances to every ray:

- `triangulate_rays()` -- ordinary linear least squares (closed-form).
- `huber_weighted_triangulate()` -- iteratively re-weighted least squares
  with a Huber loss, down-weighting rays with unusually large residuals
  (default; robust to a modest fraction of bad/reflected rays).
- `ransac_triangulate()` -- RANSAC over ray subsets, for cases where many
  rays may be corrupted (e.g. strong reverberation).

This is real geometry, not a placeholder: given exact bearings, it recovers
the true source position to floating-point precision (see "Accuracy").

### 3. Reverberation makes this harder, not solved

pyroomacoustics is used both to simulate the room/reverberation (for
benchmarking, `src/experiment.py`, `experiments/real_world_benchmark.py`)
and to run the DOA search itself (step 1). Higher reverberation --
more and stronger reflections -- meaningfully degrades both the bearing
and the final triangulated position: reflections corrupt the direct-path
timing information DOA algorithms depend on. This is a genuine
physical/algorithmic limitation (see "Accuracy" below for measured
numbers), not something this project claims to have solved.

### 4. Why microphone clusters must be small AND non-planar

Two real acoustic/geometric constraints drove this fork's array design
(both verified empirically while building this fix, not just asserted):

- **Coplanar elevation ambiguity.** Any microphone cluster whose mics all
  share one height (e.g. a flat circular or linear array) cannot
  distinguish a source at colatitude θ from one at (180° − θ): both produce
  identical inter-mic delays. A single flat 6-mic array in this project's
  own test scenario, e.g., returned an estimate of 111.08° colatitude for a
  true colatitude of 68.86° (68.86° and 180° − 68.86° = 111.14° are a
  near-exact mirror pair). The fix: give each physical cluster its own
  small amount of vertical extent (a compact tetrahedron of 4 mics, not a
  flat polygon), so a single cluster's own microphones can resolve
  elevation without needing help from any other cluster.
- **Spatial aliasing across widely-separated microphones.** DOA algorithms
  like SRP-PHAT require inter-microphone spacing well under half the
  wavelength of the highest analyzed frequency (≈17 cm at 1000 Hz; ≈4.9 cm
  at 3500 Hz). Mixing microphones from clusters that are *meters* apart
  into a single DOA computation causes severe phase aliasing and produces
  effectively random angle estimates -- measured directly in this project:
  doing so collapsed the triangulated estimate to roughly the centroid of
  the cluster centers, with ~1.27 m of error. The fix: compute DOA using
  *only* each cluster's own (few-cm-spaced) microphones -- never mixing
  microphones across clusters -- and let triangulation, which only cares
  about ray geometry and is unaffected by how far apart the ray origins
  are, combine the resulting one-ray-per-cluster bearings.

`src/main.py` and `validation/run_validation.py` place four such compact,
non-planar 4-mic tetrahedral clusters (`ExperimentalMicData`'s
`mic_clusters=[{'center': [...], 'positions': [...]}]` form) at different
corners and heights of the simulated room, and pass each cluster's own mic
names to `SoundSourceLocation.run_estimates(..., mic_groups=...)` so exactly
one DOA ray is computed per physical cluster.

## Accuracy

These are **real, measured** numbers from `python -m validation.run_validation`
(also runnable via `python -m src.main` for a single case), not targets or
estimates. Two fundamentally different things are being measured:

| Mode | What it isolates | Measured error |
|---|---|---|
| Geometric / oracle-angle triangulation | The triangulation math alone, given exact (non-estimated) bearings from each cluster to the source | ~10⁻¹⁵ m (machine precision) across 5 test source positions |
| Full acoustic pipeline, near-anechoic best case (absorption 0.99, no reflections) | Real pyroomacoustics audio simulation + real SRP-PHAT DOA estimation + triangulation | mean 0.031 m, range 0.010–0.044 m across 5 test positions |
| Full acoustic pipeline, lightly-furnished room (absorption 0.97, 1 reflection order) | Same, moderate realistic reverberation | mean 0.121 m, range 0.016–0.183 m |
| Full acoustic pipeline, heavily reverberant room (absorption 0.25, order-10 reflections) | Same, strong realistic reverberation (the room this project originally, silently, never actually simulated -- see below) | mean 1.033 m, range 0.332–1.773 m |

**Honest bottom line on the requested <1 cm / <1 mm target:** the
triangulation algorithm itself achieves it exactly (and provably -- see
`test/unit/test_triangulation.py`, 13 tests all passing at machine
precision). The full, real-audio acoustic pipeline gets close in the best
case (single-digit centimeters under near-anechoic conditions) but does
**not** reliably achieve sub-centimeter accuracy once any realistic
reverberation is present. This is a genuine physical/algorithmic limit of
DOA estimation from a small (few-cm aperture) microphone array in a
reverberant room -- reflections corrupt the direct-path timing information
DOA algorithms depend on -- not a remaining bug in this codebase. Reaching
sub-cm accuracy in real reverberant rooms in general would require a
fundamentally different approach (e.g. many more, larger-aperture arrays;
time-of-flight/TDOA methods with synchronized clocks and known emission
time; or reverberation-robust deep-learning DOA models), which is out of
scope for this fix.

## Known limitations

- Single-source only. Multiple simultaneous sources would require
  clustering per-cluster DOA rays into per-source groups before
  triangulating each group separately; not implemented.
- The 15 cm cluster aperture used by default is a deliberately tuned
  tradeoff (see `src/main.py`'s comments): its worst-case pairwise spacing
  is slightly *above* the strict half-wavelength anti-aliasing bound at
  1000 Hz, but empirically outperformed smaller, fully alias-safe
  apertures at this frequency band and array-count -- a real engineering
  tradeoff, not a guarantee that holds at all frequencies/geometries.
- Accuracy numbers above are for one specific room size, cluster layout,
  and source-position sample (5 positions); results will vary with room
  geometry, reverberation time, and array placement, and have not been
  validated against real (non-simulated) audio hardware.
- `freq_range` defaults to `[0, 250]` Hz (matched to the original heart-sound
  use case) and must be overridden for other signal types, as `src/main.py`
  does for its broadband synthetic-noise demo.

## Real-world data benchmark & interactive demo

A follow-up round tested whether the reverberation-driven accuracy
degradation described above is specific to the (synthetic, narrowband)
signal used in the original validation, by running the same DOA
algorithms against real-world, non-medical audio (LibriSpeech speech,
ESC-50 environmental sound) with known simulated ground-truth positions.

- **Full results and honest verdict:** [`reports/part1_results.md`](reports/part1_results.md).
  Short version: no -- the reverberation-driven degradation happens just
  as badly with real-world audio, across every dataset tested. One
  narrower, algorithm-specific finding (the TOPS algorithm specifically
  struggling with the narrowband signal, independent of reverberation)
  did support part of the original hypothesis; see the report for detail.
- **Benchmark harness:** `experiments/real_world_benchmark.py` (135 runs
  across 3 datasets x 3 RT60 levels x 5 algorithms x 3 positions); raw
  output in `experiments/results/`.
- **Interactive demo:** a single-page Streamlit app (`demo/app.py`)
  letting you pick a preset (LibriSpeech speech or ESC-50 environmental
  sound) or upload your own multi-channel recording, run the DOA
  pipeline, and see the estimated vs. true position in 3D. See
  [`demo/README.md`](demo/README.md) for local run instructions and
  "Architecture" below for how it's deployed.
- **Deployment status (honest report):** [`reports/deployment_status.md`](reports/deployment_status.md).

## Architecture

The demo is a **single Python process**: `demo/app.py` (Streamlit) calls
`src/service.py`, which calls `src/pipeline.py` directly, in-process --
no HTTP hop, no second server, no queue. This is deliberate, not a
simplification that skips a "real" architecture:

- Every DOA run is synchronous and takes well under 30 seconds (0.3-27s
  measured across the full benchmark matrix, see
  [`reports/part1_results.md`](reports/part1_results.md)) -- short enough
  that a request can simply wait for the result inline. There is no
  background job, no schedule, and no work that must survive a process
  restart.
- There's no database and no multi-user shared write state -- each
  request's uploaded file and generated `.mat` scratch file are staged
  under `APP_DATA_DIR` (see `src/paths.py`), consumed once, and deleted
  immediately after, all within that same request.
- An optional FastAPI wrapper still exists at `api/app.py` purely for
  local `curl`/scripting convenience and for `test/unit/test_api.py`'s
  endpoint-contract tests -- it is **not started in the deployed
  container** and is not required for the demo to work.

This is why the deployed architecture is one Dockerized Render Web
Service running `streamlit run demo/app.py`, with no separate backend
service. If a future feature needs a genuinely long-running or
scheduled job (e.g. batch-processing a large uploaded dataset, or a
recurring re-benchmark), that would need a separate worker -- nothing
in the current app requires one.

### Storage & persistence

All runtime-writable paths (uploads, generated `.mat` scratch files)
derive from a single `APP_DATA_DIR` environment variable (`src/paths.py`):

- **Local development:** unset -> falls back to `./app_data` at the repo
  root (already gitignored).
- **Production (Render):** set to `/var/data` via `render.yaml`.

**No persistent disk is attached in `render.yaml`.** Every file under
`APP_DATA_DIR` is per-request scratch data -- an uploaded recording or a
generated `.mat` file that's read back once and deleted within the same
request -- and nothing needs to survive a container restart or be shared
across instances. If Render's ephemeral local disk is wiped on restart
or redeploy, nothing is lost. `/var/data` is used as the path anyway
(rather than e.g. `/tmp`) purely so a persistent disk could be attached
later at that exact mount point without any code changes, if a future
feature ever needs durable storage.

There is no database anywhere in this app (no SQLite, no external DB) --
none of the existing functionality needed one, so none was introduced.

### Health checks

Render's **default TCP health check** against `$PORT` is used (no
`healthCheckPath` is set in `render.yaml`). Streamlit's root `/` returns
a full HTML page (not a small JSON payload), and on first load it can
take a few seconds to render while Python/pyroomacoustics import --
treating that HTML response as a health signal is more fragile than a
plain TCP accept-connection check. Streamlit does expose an internal
`/_stcore/health` path that returns `200 ok` quickly and reliably (this
was used during local Docker-equivalent testing, see
[`reports/deployment_status.md`](reports/deployment_status.md)); it's a
reasonable alternative `healthCheckPath` if you want a stricter check
than bare TCP, but plain TCP is what `render.yaml` ships with by default.

## Running with Docker locally

```bash
docker build -t doa-demo .
docker run -p 8080:8080 -e PORT=8080 -e APP_DATA_DIR=/app/app_data doa-demo
```

Then open http://localhost:8080. To use a `.env` file instead of `-e`
flags: copy [`.env.example`](.env.example) to `.env` and run with
`docker run -p 8080:8080 -e PORT=8080 --env-file .env doa-demo`.
