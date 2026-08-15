# Repository hygiene audit

Final pre-merge cleanup pass on `feature/real-world-benchmark-and-demo`
(PR [#3](https://github.com/akhilvasvani/Sound-Source-Localization/pull/3),
target `main`). This audit documents the inspection performed, the
documentation and dead-code fixes made, and the deletions being proposed
for separate, explicit approval before anything is removed.

No secrets were found, introduced, or documented anywhere in this pass.

## Repository overview and detected stack

- **Language/runtime:** Python >= 3.8 (Dockerfile pins `python:3.11-slim`).
- **Package manager:** `pip`, with `requirements.txt` for dependencies and
  `setup.py` (`pip install -e .`) to make `src`/`tools` importable.
- **Core libraries:** `numpy`, `scipy`, `matplotlib`, `pyroomacoustics`
  (DOA + room acoustics simulation), `soundfile`.
- **Demo/app layer:** `streamlit` + `plotly` (the deployed app,
  `demo/app.py`), plus an optional, non-deployed `fastapi` + `uvicorn`
  wrapper (`api/app.py`) kept for local `curl`/scripting convenience and
  for `test/unit/test_api.py`.
- **Testing:** `pytest` (config: `pytest.ini`, `pythonpath = .`). No
  formatter, linter, or type checker is configured anywhere in the repo
  (no `.flake8`, `pyproject.toml`, `mypy.ini`, `.pylintrc`, or
  `.pre-commit-config.yaml` exist) -- `pytest` is the only automated
  check that currently exists.
- **CI:** none. There is no `.github/workflows` directory and no other CI
  configuration anywhere in the repository.
- **Deployment:** single Dockerized Render Web Service
  (`Dockerfile`, `docker-entrypoint.sh`, `render.yaml`) running
  `streamlit run demo/app.py`. No Vercel, GCP, or other cloud config
  remains (previously removed; verified below).
- **Environment variables:** `APP_DATA_DIR` (runtime-writable scratch
  directory for uploads/generated `.mat` files, see `src/paths.py`;
  defaults to `./app_data` locally, set to `/var/data` in `render.yaml`)
  and `PORT` (injected by Render, optional locally). Documented in
  `.env.example`. The app has no API keys, tokens, or secrets of any kind.

## Commands discovered and run

All commands below are documented in `README.md` and were verified to
actually exist and run successfully against the current codebase:

| Command | Purpose | Result |
|---|---|---|
| `pip install -r requirements.txt && pip install -e .` | Install dependencies + editable package | Succeeds (`pip show sound-source-localization` confirms the editable install) |
| `python -m src.main` | Self-contained single-case demo | Runs; prints a real measured position/error (e.g. `error_m=0.0101`) |
| `pytest test/` | Full unit test suite | **111 passed** (both before and after every change in this pass) |
| `python -m validation.run_validation` | Full accuracy validation (unchanged from prior pass; not re-run here since no algorithm code was touched) | Not re-run in this pass -- no code affecting its output was modified |
| `docker build -t doa-demo .` / `docker run ...` | Container build/run | Not re-run in this sandbox (no Docker daemon available here); Dockerfile/entrypoint were reviewed for accuracy instead of executed |
| `streamlit run demo/app.py` | Local demo | Started successfully on a local port; smoke-tested with Playwright (see Part 1 validation below) |

No lint, format, or typecheck command exists to run -- none is configured
in this repository, so none is claimed in the README.

## Documentation files reviewed

- `README.md`
- `demo/README.md`
- `docs/misc.md`
- `reports/part1_results.md`
- `reports/deployment_status.md`
- `data/heart_proxy_samples/README.md`
- `.env.example`
- `render.yaml` (header comments)
- `Dockerfile`, `docker-entrypoint.sh` (header comments)

No `CONTRIBUTING.md` exists.

## Documentation updates made

1. **README.md -- removed a stale bullet** referencing a `heart_sound`
   audio-loading mode in `src/audio_source.py` that no longer exists in
   the code (`grep -rn "heart_sound" src/ test/` returns nothing). This
   was one of the requested Part 1 copy edits.
2. **README.md -- added the missing "Deploying to Render" section.**
   Three other files (`render.yaml`'s own header comment,
   `demo/README.md`, and `reports/deployment_status.md`) all pointed
   readers to a `README.md` "Deploying to Render" section that did not
   exist -- the README jumped straight from "Running with Docker
   locally" to nothing. Added a section with the Blueprint flow and the
   exact manual-equivalent settings/env vars, matching `render.yaml`
   verbatim (no new information invented; every value is copied from
   the existing config).
3. **reports/deployment_status.md -- fixed a dangling self-reference.**
   It said "see `README.md`'s 'Vercel' section" -- no such section
   exists (Vercel support was already fully removed in an earlier pass).
   Reworded to point at the real "Deploying to Render" section instead.

All three are pure documentation accuracy fixes with no behavior change.

## Dead code removed

| Path | What it did | Why it was demonstrably unused | Validation |
|---|---|---|---|
| `src/pipeline.py` -- `_run_doa_and_report()`'s `mic_locations_room_centered` parameter | A positional parameter accepted by this private (`_`-prefixed) helper function | Confirmed via `vulture` (100% confidence) and manual read of the full function body: the parameter is never referenced anywhere inside the function. Confirmed via `grep` that no test, demo, API, or other module references it by name or calls `_run_doa_and_report` directly (it's only called from two sites within `pipeline.py` itself, both updated). | `pytest test/` -- 111 passed, before and after |

Removing the parameter did not change what either caller computes or
passes elsewhere -- both callers already had the value on hand for other
purposes; only the now-unused hand-off into this specific function was
removed.

**Reviewed and intentionally kept (false positives / required side effects):**

- `from mpl_toolkits.mplot3d import Axes3D` in `src/determine_source.py`
  and `src/experiment.py` -- `vulture` flags these as unused imports
  (90% confidence) because the `Axes3D` name itself is never referenced.
  Both files do use `fig.add_subplot(111, projection='3d')`, and this
  import's *side effect* (registering the `'3d'` projection with
  matplotlib) is what makes that call work. Removing it risks silently
  breaking 3-D plotting. Kept as-is.
- `api/app.py`'s route handler functions (`presets_endpoint`,
  `upload_mic_geometry`, `run_preset_endpoint`, `run_upload_endpoint`,
  `health`) -- flagged as "unused" at low confidence because `vulture`
  doesn't resolve FastAPI's `@app.get(...)`/`@app.post(...)` decorator
  wiring. They're exercised by `test/unit/test_api.py` and documented in
  `demo/README.md`. Kept as-is.
- `distance`, `true_azimuth_local`, `true_colatitude_local` in
  `src/pipeline.py::run_doa_from_source_file` -- unpacked from
  `ExperimentalMicData(...).run(plot=False)`'s return tuple but not read
  afterward (the function computes its own azimuth/colatitude via
  `_angle_from_reference` instead). This is unused-variable style noise,
  not dead code -- the call that produces the tuple has necessary side
  effects (writing the scratch `.mat` file) and must still run
  regardless of which of its return values are used. Left unchanged as
  out of scope for a "remove dead code" pass (no dead code path here,
  only unused bindings).

## Files deleted (approved and removed)

Both candidates below were presented to the repository owner with full
evidence, explicitly approved, and then deleted.

### 1. `results/` (entire directory -- 601 tracked files, ~11 MB)

- **What it is:** `results/Possible S1 Location/`, `results/Possible S2
  Location/`, `results/Possible Recovered S1 Location/`, `results/Possible
  Recovered S2 Location/` -- CSV/PNG dumps and `tl;dr.txt`/`statistics.txt`
  notes from the original (pre-fork) master's-thesis heart-sound
  localization study, predating this fork's DOA + triangulation rewrite.
- **Evidence it is unused:**
  - `grep -rn "results/Possible"` across every `.py`, `.md`, `.yaml`,
    `.yml`, `.sh`, and `.txt` file in the repo returns zero hits.
  - No source file, test, script, or CI config imports, opens, or
    otherwise references any path under `results/`.
  - `.dockerignore` already explicitly excludes `results/` from the
    Docker build context -- it was already being kept out of the
    deployed image before this audit.
  - The README's own "Real-world data benchmark & interactive demo"
    section (and the removed heart-sound bullet from Part 1 of this
    pass) confirms the current project no longer documents or ships any
    heart-sound-specific results; this directory is the leftover
    artifact output from that retired workflow.
- **Validation performed:** confirmed via `git ls-files results/ | wc -l`
  (601) and `du -sh results/` (11 MB); confirmed zero references via
  repo-wide `grep`; confirmed exclusion from the Docker build context via
  `.dockerignore`. Presented to the repository owner with this evidence,
  approved, then deleted with `git rm -r results/`. `pytest test/`
  still passes 111/111 after removal.

### 2. `test/unit/test_no_transform.csv` and `test/unit/test_transform.csv` (2 files, ~1.1 MB combined)

- **What they are:** two ~550 KB CSV files (mic-position coordinate
  dumps: `Width (cm), Depth (cm), Length (cm)`) sitting directly inside
  `test/unit/`, alongside the actual `test_*.py` files.
- **Evidence they are unused:**
  - `grep -rn "no_transform\|test_transform"` across `test/`, `src/`,
    `tools/`, `demo/`, `api/`, `experiments/`, `validation/` returns zero
    hits -- no test opens either file by name.
  - No test file in `test/unit/` uses `glob`, `os.listdir`, or `os.walk`
    to discover CSV fixtures dynamically (the only `os.listdir` calls in
    the test suite, in `test/unit/test_app_data_dir.py`, assert a
    directory is *empty* -- unrelated).
  - `git log --follow` on both files traces them back to the same very
    early, pre-fork commits (`c8aa4b1`, `87edebd`, `799fedd`) that
    restructured the original thesis code into modules -- they appear to
    be output artifacts from a manual run at that time, not fixtures a
    test was ever written against.
- **Validation performed:** confirmed via repo-wide `grep` that no
  current test references them by filename or via dynamic directory
  scanning. Presented to the repository owner with this evidence,
  approved, then deleted with `git rm`. `pytest test/` still passes
  111/111 after removal.

No other files met the evidence bar for a deletion proposal in this pass.

## Items intentionally not changed because usage or safety was uncertain

("Manual review needed" -- kept, not proposed for deletion.)

| Item | Why it looked suspicious | Why it was kept |
|---|---|---|
| `api/app.py` | Not started in the deployed container (`docker-entrypoint.sh` only runs Streamlit); could look like dead weight | Actively imported and exercised by `test/unit/test_api.py`'s endpoint-contract tests, and explicitly documented as an intentional local `curl`/scripting convenience in both `README.md`'s "Architecture" section and `demo/README.md`. Removing it would break passing tests and remove documented functionality. |
| `scripts/check_app_data_dir.sh` | A small, easily-overlooked shell script | Directly invoked by `docker-entrypoint.sh` as a fail-fast startup check, and directly exercised as a subprocess by `test/unit/test_app_data_dir.py`. Both are real, current usages. |
| `data/heart_proxy_samples/` (incl. `white_noise_0.wav`) | The name suggests obsolete heart-sound data, and the heart-sound `.mat` loading mode was removed from `README.md` in Part 1 | Its own `README.md` clarifies it's actually a checked-in white-noise generator baseline (not real or synthetic heart-sound audio), and it's actively read by `experiments/real_world_benchmark.py` and discussed in `reports/part1_results.md`. Confusing name, but genuinely in use. |
| Vercel-related config | Part 3 explicitly called out "any old Vercel-related config remnants" to inspect | None exist. No `vercel.json`, no `.vercel/` directory, no Vercel references in any `.py`/`.json`/`.yaml`/`.toml` file -- already fully removed in an earlier pass (per `reports/deployment_status.md`'s own account). The `.dockerignore` still lists a `.vercel` ignore pattern with nothing left to match; harmless residue, not worth a special-purpose commit to touch a single ignore-pattern line for a file that doesn't exist. |
| `docs/misc.md` | Reads like personal Python-learning reference links (multiprocessing, decorators, closures, etc.), unrelated to this project's docs | Directly referenced from a code comment in `src/triangulation.py` ("matches `docs/misc.md` / README"). Kept. |
| `reports/deployment_status.md`, `reports/part1_results.md` | Part 3 called out "unused reports or docs" to inspect | Both are actively linked from `README.md`'s "Real-world data benchmark & interactive demo" section and read as point-in-time incident/finding reports, not stale docs. Kept (one dangling internal cross-reference inside `deployment_status.md` was fixed above). |
| Unused local variables (`distance`, `true_azimuth_local`, `true_colatitude_local` in `src/pipeline.py`) | Flagged by `vulture` | Not dead code -- see "Dead code removed" section above for the distinction (the producing call has required side effects). Left unchanged; noted here only for completeness. |
| `src/main.py`, `src/experiment.py`, `src/determine_source.py`, `src/preprocess.py`, `src/sound_source_localization.py`, `tools/utilities.py`, `tools/validations.py`, `validation/run_validation.py` | Part 3 asked to check for "duplicate/dead modules after the Streamlit migration" | Traced the full import graph: every one of these modules is imported by at least one of `src/pipeline.py`, `src/experiment.py`, `validation/run_validation.py`, or a test in `test/unit/`, and `validation.run_validation` is still the documented way to reproduce the README's "Accuracy" numbers. These are the original algorithm implementation that the newer `pipeline.py`/`service.py` layer wraps for the demo -- not duplicates, not dead. |

## Known failing checks that predated this work

None. `pytest test/` passed (111/111) both before this pass began and
after every change made in it. No pre-existing failures were observed.

## Validation summary (exact commands and outcomes)

| Command | Outcome |
|---|---|
| `python -m py_compile demo/app.py` | OK (after Part 1 demo edits) |
| `pytest test/ -q` | 111 passed (run after Part 1 edits, after the `src/pipeline.py` dead-parameter removal, and again as a final check -- identical result each time) |
| Playwright smoke test against `streamlit run demo/app.py` | Confirmed updated intro copy renders, the removed "far wall" line and old footer prose are gone, and the "How this works · Source" footer links remain -- see Part 1 validation notes |
| `python -m src.main` | Runs; prints a real measured triangulated position and error (e.g. `error_m=0.0101`) |
| `vulture src/ tools/ demo/ api/ experiments/ validation/ --min-confidence 60` | Findings reviewed individually above; one genuine dead parameter removed, remainder are false positives or non-dead unused-variable style noise |
| Repo-wide `grep` reference search for `results/`, `test_no_transform.csv`, `test_transform.csv` | Zero references found for any of the deletion targets |
| `pytest test/ -q` after `git rm -r results/` and `git rm test/unit/test_no_transform.csv test/unit/test_transform.csv` | 111 passed -- both approved deletions confirmed safe post-removal |
| Broken-link scan across all `.md` files (file + anchor targets) | No broken links found after the README/`deployment_status.md` fixes |
