#!/usr/bin/env python
"""Single-page Streamlit demo for the Sound Source Localization pipeline.

Calls src/service.py directly, in-process -- there is no separate
backend server to start, monitor, or keep alive. This is the only
process that runs in the deployed architecture (single Render Web
Service, single Docker container, one `streamlit run` command).

Run locally:
    streamlit run demo/app.py
"""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from src.service import list_presets, run_preset, run_upload

st.set_page_config(page_title="Sound Source Localization Demo", layout="wide")
st.title("Sound Source Localization -- Interactive Demo")
st.caption(
    "Wraps the pyroomacoustics DOA/triangulation pipeline from "
    "[akhilvasvani/Sound-Source-Localization](https://github.com/akhilvasvani/Sound-Source-Localization) "
    "as an interactive demo. Pick a preset (mix of a heart-proxy signal and real-world audio) or upload your own "
    "multi-channel recording, then compare the estimated source position/bearing against the true one."
)


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
    st.sidebar.caption(preset["description"])

    algorithm = st.sidebar.selectbox("DOA algorithm", ALGORITHMS, index=0)
    rt60_level = st.sidebar.selectbox("Reverberation (RT60) level", RT60_LEVELS, index=1)
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

col_viz, col_panel = st.columns([2, 1])

with col_panel:
    st.subheader("Results")
    st.metric("Algorithm", report["algorithm"])
    st.metric("Runtime", f"{report['elapsed_s']:.2f} s")

    if report.get("note"):
        st.warning(report["note"])

    st.markdown("**Angle (from array centroid)**")
    angle_rows = {
        "": ["Azimuth (deg)", "Colatitude (deg)"],
        "Estimated": [f"{report['estimated_azimuth_deg']:.1f}", f"{report['estimated_colatitude_deg']:.1f}"],
    }
    if "true_azimuth_deg" in report:
        angle_rows["True"] = [f"{report['true_azimuth_deg']:.1f}", f"{report['true_colatitude_deg']:.1f}"]
    st.table(angle_rows)

    if "angle_error_deg" in report:
        st.metric("Angle error", f"{report['angle_error_deg']:.1f} deg")

    if report["position_available"]:
        st.markdown("**Position (meters, room-absolute)**")
        st.write(f"Estimated: `{np.round(report['estimate_m'], 3).tolist()}`")
        if report.get("true_source_m"):
            st.write(f"True: `{report['true_source_m']}`")
            st.metric("Position error", f"{report['error_m']:.3f} m")
    else:
        st.markdown(
            "**No 3-D position fix** -- only one microphone cluster was used, "
            "which constrains a bearing, not a point (see note above)."
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
