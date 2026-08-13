# heart_proxy_samples

This directory holds the "heart_proxy" dataset used in Part 1's
real-world benchmark (`experiments/real_world_benchmark.py`).

**Important, honest note discovered while extending this repo:** no
actual heart-sound `.mat` file (S1/S2 recordings, real or synthetic)
exists anywhere in this repository's history -- `find . -iname "*.mat"`
returns nothing, and no `.mat` file is checked in. The existing
`README.md` accuracy table and `validation/run_validation.py` are
**not** run against real (or even heart-sound-*shaped*) audio at all.
They are run against **band-limited Gaussian white noise**, generated
inline by `validation/run_validation.py::_make_wav()`
(`np.random.default_rng(seed).normal(scale=0.3, ...)`), filtered only
by the DOA estimator's `freq_range=[300, 1000]` Hz parameter (which
happens to overlap typical heart-sound frequency content, but the
*signal itself* carries no heart-sound structure -- no periodicity, no
S1/S2 waveform shape, nothing).

`white_noise_0.wav` in this directory is that exact same generator
(same seed, duration, sample rate, scale) saved to disk as a real file,
so the "heart_proxy" condition in the new benchmark is a byte-for-byte
faithful reproduction of the *existing* baseline methodology -- not a
new, differently-tuned white-noise generator that would make the
"before vs after" comparison unfair.

This matters for Part 1's central question ("is reverberation error an
artifact of the heart-sound data, or does it persist regardless of data
source?") -- there never was heart-sound *audio* in the first
comparison, only a heart-sound-*range* frequency filter applied to
noise. See `reports/part1_results.md` for the full discussion.
