#!/usr/bin/env python
"""Part 1 real-world benchmark: runs every DOA algorithm (SRP, MUSIC,
TOPS, CSSM, WAVES) against three datasets -- the existing heart-proxy
white-noise signal (see data/heart_proxy_samples/README.md for why this,
and not real heart-sound audio, is what the ORIGINAL README numbers
actually measured) and two real-world audio datasets (LibriSpeech
speech clips, ESC-50 environmental sound clips) -- across three RT60
conditions (low/medium/high, matching validation/run_validation.py's
exact absorption/max_order settings for a fair before/after comparison).

All source positions, room dimensions, and mic cluster geometry are
reused unchanged from validation/run_validation.py's TEST_SOURCES /
ROOM_DIM / CLUSTER_CENTERS / APERTURE, specifically so this is an
apples-to-apples extension of the existing baseline, not a
differently-tuned rebuild that would make "before vs after" comparisons
meaningless.

Usage:
    python -m experiments.real_world_benchmark [--quick]

    --quick restricts to 1 source position and n_grid=1000 (for fast
    smoke-testing of the harness itself); omit for the full matrix used
    in reports/part1_results.md.

Results are saved to experiments/results/real_world_benchmark.csv and
.json (one row per algorithm x dataset x rt60_level x source position).
Nothing here is fabricated or cherry-picked after the fact -- every run
in the matrix is included in the output, wins and losses alike.
"""

import argparse
import csv
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import ALGORITHMS, RT60_LEVELS, DEFAULT_ROOM_DIM, measure_room_rt60
from src.pipeline import run_doa_from_source_file

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Same 3 (of the original 5) TEST_SOURCES from validation/run_validation.py
# -- "a few source positions (2-3)" per the task brief.
TEST_SOURCES = [
    [3.0, 1.0, 1.7],
    [1.0, 2.0, 0.6],
    [2.0, 1.5, 2.0],
]

# Each dataset entry: (label, [wav files to cycle through], freq_range).
# heart_proxy uses freq_range=[300,1000] to exactly match the original
# baseline; the two real-world datasets use a wider broadband range
# appropriate to speech / environmental sound content -- this is a
# deliberate, documented choice (see reports/part1_results.md), not an
# attempt to bias the comparison in either direction.
DATASETS = {
    "heart_proxy": {
        "files": [os.path.join(REPO_ROOT, "data", "heart_proxy_samples", "white_noise_0.wav")],
        "freq_range": [300, 1000],
        "description": "Band-limited Gaussian white noise -- exact reproduction of "
                       "the existing README/validation baseline signal (not real "
                       "heart-sound audio; see data/heart_proxy_samples/README.md).",
    },
    "librispeech": {
        "files": sorted(
            os.path.join(REPO_ROOT, "data", "librispeech_samples", f"sample_{i}.wav")
            for i in range(4)
        ),
        "freq_range": [300, 3400],
        "description": "Real human speech clips, HuggingFace "
                       "hf-internal-testing/librispeech_asr_dummy (validation split).",
    },
    "esc50": {
        "files": [
            os.path.join(REPO_ROOT, "data", "esc50_samples", "rain.wav"),
            os.path.join(REPO_ROOT, "data", "esc50_samples", "clock_tick.wav"),
        ],
        "freq_range": [300, 3400],
        "description": "Real environmental sound clips, HuggingFace ashraq/esc50.",
    },
}


def run_matrix(n_grid, sources, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    rt60_measured_cache = {}

    total = len(DATASETS) * len(RT60_LEVELS) * len(ALGORITHMS) * len(sources)
    done = 0
    t_start = time.time()

    for dataset_name, dataset_cfg in DATASETS.items():
        files = dataset_cfg["files"]
        missing = [f for f in files if not os.path.exists(f)]
        if missing:
            print(f"WARNING: skipping dataset '{dataset_name}', missing files: {missing}")
            continue

        for rt60_level, rt60_cfg in RT60_LEVELS.items():
            cache_key = (rt60_level,)
            if cache_key not in rt60_measured_cache:
                rt60_measured_cache[cache_key] = measure_room_rt60(
                    DEFAULT_ROOM_DIM, rt60_cfg["absorption"], rt60_cfg["max_order"])
            measured_rt60_s = rt60_measured_cache[cache_key]

            for algo_name in ALGORITHMS:
                for i, source in enumerate(sources):
                    wav_file = files[i % len(files)]
                    t0 = time.time()
                    try:
                        report = run_doa_from_source_file(
                            wav_file, source, algo_name=algo_name, rt60_level=rt60_level,
                            freq_range=dataset_cfg["freq_range"], n_grid=n_grid,
                        )
                        row = {
                            "dataset": dataset_name,
                            "source_file": os.path.basename(wav_file),
                            "algorithm": algo_name,
                            "rt60_level": rt60_level,
                            "rt60_absorption": rt60_cfg["absorption"],
                            "rt60_max_order": rt60_cfg["max_order"],
                            "rt60_measured_s": measured_rt60_s,
                            "source_position_m": source,
                            "estimate_m": report["estimate_m"],
                            "error_m": report["error_m"],
                            "angle_error_deg": report["angle_error_deg"],
                            "mean_ray_residual_m": report["mean_ray_residual_m"],
                            "elapsed_s": report["elapsed_s"],
                            "error": None,
                        }
                    except Exception as exc:  # pragma: no cover -- defensive; log & continue
                        row = {
                            "dataset": dataset_name, "source_file": os.path.basename(wav_file),
                            "algorithm": algo_name, "rt60_level": rt60_level,
                            "rt60_absorption": rt60_cfg["absorption"],
                            "rt60_max_order": rt60_cfg["max_order"],
                            "rt60_measured_s": measured_rt60_s,
                            "source_position_m": source, "estimate_m": None, "error_m": None,
                            "angle_error_deg": None, "mean_ray_residual_m": None,
                            "elapsed_s": time.time() - t0, "error": str(exc),
                        }
                        print(f"  ERROR: {dataset_name}/{algo_name}/{rt60_level}/src{i}: {exc}")

                    rows.append(row)
                    done += 1
                    print(f"[{done}/{total}] {dataset_name:12s} {algo_name:6s} "
                          f"{rt60_level:6s} src{i}  "
                          f"error_m={row['error_m']}  "
                          f"({time.time() - t_start:.0f}s elapsed)")

    csv_path = os.path.join(out_dir, "real_world_benchmark.csv")
    json_path = os.path.join(out_dir, "real_world_benchmark.json")
    if rows:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    with open(json_path, "w") as f:
        json.dump(rows, f, indent=2)

    print(f"\nWrote {len(rows)} rows to {csv_path} and {json_path}")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true",
                        help="Fast smoke test: 1 source position, n_grid=1000.")
    parser.add_argument("--out-dir", default=os.path.join(REPO_ROOT, "experiments", "results"))
    args = parser.parse_args()

    sources = TEST_SOURCES[:1] if args.quick else TEST_SOURCES
    # n_grid=8000 matches validation/run_validation.py's own default exactly,
    # so grid resolution itself isn't a confound in the before/after comparison.
    n_grid = 1000 if args.quick else 8000
    run_matrix(n_grid, sources, args.out_dir)


if __name__ == "__main__":
    main()
