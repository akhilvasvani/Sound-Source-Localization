#!/usr/bin/env python
"""Single-page Streamlit demo for the Sound Source Localization pipeline.

Calls src/service.py directly, in-process -- there is no separate
backend server to start, monitor, or keep alive. This is the only
process that runs in the deployed architecture (single Render Web
Service, single Docker container, one `streamlit run` command).

Run locally:
    streamlit run demo/app.py
"""

import math

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from src.service import list_presets, run_preset, run_upload

# Stable GitHub links used in the footer. The branch name matches
# render.yaml's `branch:` (i.e. what the deployed Render app is actually
# built from) so "How this works" resolves to the exact README version
# backing this running instance. Update if/when the default branch changes.
_REPO_URL = "https://github.com/akhilvasvani/Sound-Source-Localization"
_README_ALGORITHM_URL = (
    "https://github.com/akhilvasvani/Sound-Source-Localization/blob/"
    "feature/real-world-benchmark-and-demo/README.md#algorithm"
)

st.set_page_config(page_title="Sound Source Localization Demo", layout="wide")

# --------------------------------------------------------------------------
# Title -- sized with clamp() rather than Streamlit's fixed st.title() font
# so it stays on one or two short lines on a narrow (~375px) phone
# viewport instead of wrapping across many lines.
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .doa-title { font-size: clamp(1.55rem, 6vw, 2.4rem); font-weight: 700;
                 line-height: 1.15; margin-bottom: 0.1rem; }
    .doa-subtitle { font-size: clamp(0.85rem, 2.6vw, 1.05rem); opacity: 0.7;
                     margin-top: 0; margin-bottom: 0.75rem; }
    </style>
    <div class="doa-title">Where is that sound coming from?</div>
    <div class="doa-subtitle">Direction-of-arrival estimation with a 4-mic array</div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "On a phone, tap **\u00bb** in the top-left corner to open the controls "
    "(preset, algorithm, reverb level) if they aren't already visible."
)

st.markdown(
    "Four microphones, a few centimeters apart, hear the same sound at "
    "slightly different times. That tiny delay is enough to work out "
    "which direction the sound came from, and with enough mic pairs, "
    "where it is in the room."
)
st.markdown("Pick a sound below and run it. The demo shows the estimated position against the true one.")


@st.cache_data(ttl=30)
def fetch_presets():
    return list_presets()


try:
    catalog = fetch_presets()
except Exception as exc:
    st.error(f"Could not load the preset catalog: {exc}")
    st.stop()

ALGORITHMS = catalog["algorithms"]
RT60_LEVELS = catalog["rt60_levels"]
PRESETS = catalog["presets"]

# --------------------------------------------------------------------------
# Sidebar: mode + parameters
# --------------------------------------------------------------------------
st.sidebar.header("Input")
mode = st.sidebar.radio("Source", ["Preset example", "Upload my own recording"])

if mode == "Preset example":
    preset_labels = [p["label"] for p in PRESETS]
    chosen_label = st.sidebar.selectbox("Preset", preset_labels)
    preset = next(p for p in PRESETS if p["label"] == chosen_label)

    algorithm = st.sidebar.selectbox("DOA algorithm", ALGORITHMS, index=0)
    st.sidebar.caption("Different ways of scanning for the direction the sound came from.")

    rt60_level = st.sidebar.selectbox("Reverberation (RT60) level", RT60_LEVELS, index=1)
    st.sidebar.caption("How echoey the simulated room is. More echo, harder problem.")

    run_clicked = st.sidebar.button("Run DOA pipeline", type="primary")

    if run_clicked:
        with st.spinner(f"Simulating room + running {algorithm} DOA + triangulation..."):
            try:
                report = run_preset(preset["id"], algorithm=algorithm,
                                     rt60_level=rt60_level, n_grid=4000)
            except KeyError as exc:
                st.error(f"Invalid input: {str(exc).strip(chr(39))}")
                st.stop()
            except Exception as exc:
                st.error(f"DOA pipeline failed: {exc}")
                st.stop()
        st.session_state["report"] = report

else:
    uploaded = st.sidebar.file_uploader("Multi-channel .wav or .flac file", type=["wav", "flac"])
    st.sidebar.caption(
        "Assumed mic geometry: a single small (~15 cm) 4-mic tetrahedral cluster. "
        "A single array/cluster gives a BEARING (direction), not a full 3-D position fix -- "
        "this is a real physical limitation, not a bug."
    )
    algorithm = st.sidebar.selectbox("DOA algorithm", ALGORITHMS, index=0)
    st.sidebar.caption("Different ways of scanning for the direction the sound came from.")

    known_true = st.sidebar.checkbox("I know the true source position (meters)")
    true_source_m = None
    if known_true:
        cols = st.sidebar.columns(3)
        x = cols[0].number_input("x", value=2.0)
        y = cols[1].number_input("y", value=1.5)
        z = cols[2].number_input("z", value=1.0)
        true_source_m = [x, y, z]

    run_clicked = st.sidebar.button("Run DOA pipeline", type="primary", disabled=uploaded is None)

    if run_clicked and uploaded is not None:
        with st.spinner(f"Running {algorithm} DOA on your recording..."):
            try:
                report = run_upload(uploaded.getvalue(), uploaded.name, algorithm=algorithm,
                                     true_source_m=true_source_m)
            except (KeyError, ValueError) as exc:
                st.error(f"Invalid input: {str(exc).strip(chr(39))}")
                st.stop()
            except Exception as exc:
                st.error(f"DOA pipeline failed: {exc}")
                st.stop()
        st.session_state["report"] = report


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------
report = st.session_state.get("report")
if report is None:
    st.info("Choose a preset or upload a recording, then click **Run DOA pipeline**.")
    st.stop()


def _format_angle(angle_deg):
    """Human-readable angle string with precision that scales down as the
    number gets smaller, so a tiny error isn't rounded away to '0.0deg'
    while a large one isn't shown with meaningless extra digits."""
    if angle_deg >= 10:
        return f"{angle_deg:.0f}\u00b0"
    if angle_deg >= 1:
        return f"{angle_deg:.1f}\u00b0"
    return f"{angle_deg:.2f}\u00b0"


def _ray_box_exit_distance(origin_m, direction, room_dim_m):
    """Distance (meters) from `origin_m` to the point where a ray in
    `direction` exits the axis-aligned room box [0, room_dim_m] on each
    axis. Assumes `origin_m` is already inside the box (true here: it is
    the mean of the mic-cluster centroids, which sit inside the simulated
    room by construction). Standard per-axis slab exit calculation: for
    each axis the ray is moving away from the origin, it hits either the
    x=room_dim or x=0 face depending on sign; the ray leaves the box at
    the SMALLEST of those per-axis exit distances.
    """
    direction = np.asarray(direction, dtype=float)
    norm = np.linalg.norm(direction)
    if norm < 1e-9:
        return None
    direction = direction / norm
    exit_candidates = []
    for axis in range(3):
        d = direction[axis]
        if abs(d) < 1e-9:
            continue
        bound = room_dim_m[axis] if d > 0 else 0.0
        t = (bound - origin_m[axis]) / d
        if t > 1e-9:
            exit_candidates.append(t)
    return min(exit_candidates) if exit_candidates else None


col_viz, col_panel = st.columns([2, 1])

with col_panel:
    st.subheader("How close did it get?")

    angle_error_deg = report.get("angle_error_deg")
    if angle_error_deg is not None:
        st.markdown(f"## Off by {_format_angle(angle_error_deg)}")

        # Room-scale translation: converts the angle error into a linear
        # displacement (cm) "at the far wall" -- i.e. how far apart the
        # estimated and true bearings have drifted by the time they reach
        # the room boundary. Only shown when we have real geometry to base
        # it on: a known true source position (to know which direction is
        # "the far wall") and the room dimensions used for the simulation.
        #
        # Formula (small-angle arc-length approximation): given a range r
        # (meters, to the far wall along the true bearing) and an angle
        # error theta (radians), the two rays have diverged by
        # roughly  s = r * theta  meters by the time they reach that wall.
        # This is an approximation (exact only for infinitesimal theta),
        # not an exact chord/triangulated distance -- reasonable for the
        # single-digit-to-tens-of-degrees errors typical at low/medium
        # reverberation, but increasingly approximate as theta grows
        # large (near/above 90 deg, where "the far wall" and the
        # small-angle assumption both become a stretch).
        true_source_m = report.get("true_source_m")
        reference_point_m = report.get("reference_point_m")
        room_dim_m = report.get("room_dim_m")
        if true_source_m and reference_point_m and room_dim_m:
            direction_to_true = np.asarray(true_source_m) - np.asarray(reference_point_m)
            range_m = _ray_box_exit_distance(reference_point_m, direction_to_true, room_dim_m)
            if range_m is not None:
                displacement_cm = range_m * math.radians(angle_error_deg) * 100
                st.caption(f"Roughly {displacement_cm:.0f} cm at the far wall.")
    elif report["position_available"]:
        st.caption("No ground-truth position was supplied, so no error can be measured.")
    else:
        st.warning(report.get("note", "Only a bearing (direction), not a full 3-D fix, is available."))

    with st.expander("Full numbers"):
        st.metric("Algorithm", report["algorithm"])
        st.metric("Runtime", f"{report['elapsed_s']:.2f} s")

        st.markdown("**Angle (from array centroid)**")
        angle_rows = {
            "": ["Azimuth (deg)", "Colatitude (deg)"],
            "Estimated": [f"{report['estimated_azimuth_deg']:.1f}", f"{report['estimated_colatitude_deg']:.1f}"],
        }
        if "true_azimuth_deg" in report:
            angle_rows["True"] = [f"{report['true_azimuth_deg']:.1f}", f"{report['true_colatitude_deg']:.1f}"]
        st.table(angle_rows)

        if angle_error_deg is not None:
            st.metric("Angle error", f"{angle_error_deg:.1f} deg")

        if report["position_available"]:
            st.markdown("**Position (meters, room-absolute)**")
            st.write(f"Estimated: `{np.round(report['estimate_m'], 3).tolist()}`")
            if report.get("true_source_m"):
                st.write(f"True: `{report['true_source_m']}`")
                st.metric("Position error", f"{report['error_m']:.3f} m")
        else:
            st.markdown(
                "**No 3-D position fix** -- only one microphone cluster was used, "
                "which constrains a bearing, not a point."
            )

        if report.get("rt60_s") is not None:
            st.caption(f"Measured room RT60: {report['rt60_s'] * 1000:.1f} ms "
                       f"({report.get('rt60_level', '')} condition)")


with col_viz:
    st.subheader("3-D visualization")
    fig = go.Figure()

    room_dim = report["room_dim_m"]
    x0, y0, z0 = 0, 0, 0
    x1, y1, z1 = room_dim
    edges = [
        ([x0, x1], [y0, y0], [z0, z0]), ([x0, x1], [y1, y1], [z0, z0]),
        ([x0, x1], [y0, y0], [z1, z1]), ([x0, x1], [y1, y1], [z1, z1]),
        ([x0, x0], [y0, y1], [z0, z0]), ([x1, x1], [y0, y1], [z0, z0]),
        ([x0, x0], [y0, y1], [z1, z1]), ([x1, x1], [y0, y1], [z1, z1]),
        ([x0, x0], [y0, y0], [z0, z1]), ([x1, x1], [y0, y0], [z0, z1]),
        ([x0, x0], [y1, y1], [z0, z1]), ([x1, x1], [y1, y1], [z0, z1]),
    ]
    for ex, ey, ez in edges:
        fig.add_trace(go.Scatter3d(x=ex, y=ey, z=ez, mode="lines",
                                    line=dict(color="lightgray", width=2), showlegend=False))

    # Mic cluster origins + DOA rays
    ray_len = max(room_dim) * 0.6
    for i, ray in enumerate(report["rays"]):
        origin = np.array(ray["origin_m"])
        direction = np.array(ray["direction"])
        end = origin + ray_len * direction
        fig.add_trace(go.Scatter3d(
            x=[origin[0], end[0]], y=[origin[1], end[1]], z=[origin[2], end[2]],
            mode="lines", line=dict(color="rgba(80,120,220,0.6)", width=3 + 3 * ray["weight"]),
            name=f"ray {i}", showlegend=False,
        ))
        fig.add_trace(go.Scatter3d(
            x=[origin[0]], y=[origin[1]], z=[origin[2]], mode="markers",
            marker=dict(size=4, color="steelblue"), name="mic cluster" if i == 0 else None,
            showlegend=(i == 0),
        ))

    # Pairwise intersection point cloud (visual confidence proxy)
    pts = report.get("pairwise_intersection_points_m") or []
    if pts:
        pts = np.array(pts)
        fig.add_trace(go.Scatter3d(
            x=pts[:, 0], y=pts[:, 1], z=pts[:, 2], mode="markers",
            marker=dict(size=3, color="gray", opacity=0.5),
            name="pairwise ray intersections",
        ))

    # Estimated position
    if report["position_available"]:
        est = report["estimate_m"]
        fig.add_trace(go.Scatter3d(
            x=[est[0]], y=[est[1]], z=[est[2]], mode="markers",
            marker=dict(size=9, color="crimson", symbol="diamond"),
            name="estimated position",
        ))

    # True position
    if report.get("true_source_m"):
        true = report["true_source_m"]
        fig.add_trace(go.Scatter3d(
            x=[true[0]], y=[true[1]], z=[true[2]], mode="markers",
            marker=dict(size=9, color="seagreen", symbol="circle"),
            name="true position",
        ))

    fig.update_layout(
        scene=dict(
            xaxis_title="x (m)", yaxis_title="y (m)", zaxis_title="z (m)",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=0.01),
        height=600,
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption(
    "Source: [akhilvasvani/Sound-Source-Localization](https://github.com/akhilvasvani/Sound-Source-Localization). "
    "This demo is a thin UI over the existing DOA + triangulation pipeline -- see reports/part1_results.md "
    "for the accuracy findings behind these numbers."
)
st.caption(f"[How this works]({_README_ALGORITHM_URL}) \u00b7 [Source]({_REPO_URL})")
