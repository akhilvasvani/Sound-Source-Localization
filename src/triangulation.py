#!/usr/bin/env python
"""Least-squares / robust ray-triangulation utilities.

This module is the piece that was MISSING from the original codebase: given
a set of rays R_i = {origin: o_i, direction: d_i} -- each representing a
"microphone-array-to-source" direction estimate with an unknown radial
distance -- it finds the single 3-D point x* that best explains all of them
simultaneously.

Background / math
------------------
For a ray through origin o_i with a UNIT direction d_i, the perpendicular
(orthogonal-projector) matrix onto the plane orthogonal to d_i is:

    P_i = I - d_i @ d_i^T                    (3x3, symmetric, rank 2)

The squared perpendicular distance from any point x to ray i is:

    dist_i(x)^2 = || P_i @ (x - o_i) ||^2

Summing over all rays and minimizing with respect to x gives a plain linear
least-squares problem (setting the gradient to zero):

    ( sum_i P_i ) @ x = sum_i P_i @ o_i
             A    @ x  =        b

This is solved with `numpy.linalg.lstsq`. With EXACT (noise-free) ray data
and >= 2 non-parallel rays, this recovers the true intersection point to
floating-point (machine) precision -- there is no sampling, no fixed radius
grid, and no "guess and check": it is a closed-form solve.

Weighted least squares, RANSAC, and Huber-loss IRLS variants are provided
below to handle noisy/outlier-corrupted angle estimates (e.g. from
reverberant reflections being mistaken for the direct-path arrival).
"""

import numpy as np


def unit(vector):
    """Normalizes a vector to unit length.

    Raises:
        ValueError: if the vector has (numerically) zero length.
    """
    vector = np.asarray(vector, dtype=float)
    norm = np.linalg.norm(vector)
    if norm < 1e-15:
        raise ValueError("Error. Zero-length direction vector cannot be normalized.")
    return vector / norm


def spherical_to_cartesian(azimuth, colatitude):
    """Converts azimuth/colatitude (physics convention, radians) to a unit
       Cartesian direction vector.

       Convention (matches the project's stated physics convention, and
       matches `docs/misc.md` / README):
           colatitude (theta): angle from the +z axis, in [0, pi]
           azimuth (phi): angle from +x axis toward +y axis, in (-pi, pi]

           x = cos(azimuth) * sin(colatitude)
           y = sin(azimuth) * sin(colatitude)
           z = cos(colatitude)

    Args:
        azimuth: scalar or array-like, radians.
        colatitude: scalar or array-like, radians, expected in [0, pi].

    Returns:
        numpy array of shape (..., 3): unit direction vector(s). Note this
        function does NOT wrap/clip out-of-range colatitude for you --
        validate upstream with `np.arctan2`-based formulas (never
        `np.arctan`, which only returns (-pi/2, pi/2) and cannot represent
        colatitude > 90 degrees).
    """
    azimuth = np.asarray(azimuth, dtype=float)
    colatitude = np.asarray(colatitude, dtype=float)
    x = np.cos(azimuth) * np.sin(colatitude)
    y = np.sin(azimuth) * np.sin(colatitude)
    z = np.cos(colatitude)
    return np.stack([x, y, z], axis=-1)


def _closest_point_to_rays(origins, directions, weights=None):
    """Core (weighted) linear least-squares ray-intersection solve.

    Args:
        origins: (n, 3) array of ray origins.
        directions: (n, 3) array of (not necessarily unit) directions.
        weights: optional (n,) array of non-negative weights.

    Returns:
        (3,) numpy array: the least-squares closest point to all rays.

    Raises:
        ValueError: on malformed input or fewer than 2 rays.
        numpy.linalg.LinAlgError: if the rays are (near-)parallel/degenerate,
            i.e. the 3x3 normal-equations matrix is rank-deficient, so no
            unique intersection point exists.
    """
    origins = np.asarray(origins, dtype=float)
    directions = np.asarray(directions, dtype=float)

    if origins.ndim != 2 or origins.shape[1] != 3 or origins.shape != directions.shape:
        raise ValueError("Error. origins and directions must both be (n, 3) arrays "
                         f"of matching shape (got {origins.shape} and {directions.shape}).")

    n_rays = origins.shape[0]
    if n_rays < 2:
        raise ValueError("Error. Need at least 2 rays to triangulate a 3-D point "
                         "(a single ray/direction constrains only a line, not a point).")

    if weights is None:
        weights = np.ones(n_rays)
    weights = np.asarray(weights, dtype=float)

    eye3 = np.eye(3)
    unit_dirs = np.array([unit(d) for d in directions])

    # Vectorized accumulation of A = sum_i w_i * P_i and b = sum_i w_i * P_i @ o_i
    # P_i = I - d_i d_i^T  for every ray, stacked as (n, 3, 3)
    outer = np.einsum('ij,ik->ijk', unit_dirs, unit_dirs)
    projectors = eye3[None, :, :] - outer
    a_matrix = np.einsum('i,ijk->jk', weights, projectors)
    b_vector = np.einsum('i,ijk,ik->j', weights, projectors, origins)

    rank = np.linalg.matrix_rank(a_matrix, tol=1e-9)
    if rank < 3:
        raise np.linalg.LinAlgError(
            "Error. Rays are (near-)parallel or otherwise geometrically "
            "degenerate: the 3x3 normal-equations matrix is rank-deficient "
            f"(rank={rank}), so there is no unique closest-point solution. "
            "Use direction estimates from microphone (sub-)arrays that are "
            "not colinear, or add more geometrically diverse rays."
        )

    estimate, *_ = np.linalg.lstsq(a_matrix, b_vector, rcond=None)
    return estimate


def perpendicular_residuals(estimate, origins, directions):
    """Returns the perpendicular distance (meters) from `estimate` to each
       ray -- useful for scoring/robustness and for reporting fit quality.
    """
    origins = np.asarray(origins, dtype=float)
    unit_dirs = np.array([unit(d) for d in directions])
    diffs = origins - np.asarray(estimate, dtype=float)
    proj_len = np.einsum('ij,ij->i', diffs, unit_dirs)
    perp = diffs - proj_len[:, None] * unit_dirs
    return np.linalg.norm(perp, axis=1)


def triangulate_rays(origins, directions, weights=None):
    """Plain (optionally weighted) least-squares closest point to N rays.

    This is the direct fix for the missing-radius / ray-convergence problem
    described in the project's goal: each direction estimate becomes a ray
    (origin = array centroid, direction = unit vector from azimuth/
    colatitude), and this function finds where they best converge.

    Args:
        origins: (n, 3) array-like -- one ray origin per direction estimate.
        directions: (n, 3) array-like -- direction vectors (need not be
                    pre-normalized).
        weights: optional (n,) array-like of non-negative weights (e.g.
                 inverse-variance of each angle estimate). Equal weights
                 (ordinary least squares) if omitted.

    Returns:
        (3,) numpy array: the estimated 3-D source location.
    """
    return _closest_point_to_rays(origins, directions, weights)


def ransac_triangulate(origins, directions, min_samples=3, residual_threshold=0.03,
                        max_trials=500, random_state=None):
    """RANSAC-robust ray triangulation.

    Repeatedly fits a candidate point from a random minimal subset of rays,
    scores it by counting how many OTHER rays are consistent with it
    (perpendicular residual below `residual_threshold`), keeps the largest
    inlier set found across trials, and returns the ordinary least-squares
    refit over that inlier set. This guards against a minority of grossly
    corrupted direction estimates (e.g. a reflection mistaken for the
    direct-path arrival), which would otherwise pull a plain least-squares
    fit far from the true source.

    Args:
        origins: (n, 3) array-like of ray origins.
        directions: (n, 3) array-like of ray directions.
        min_samples: rays drawn per random trial (>= 2; 3+ recommended so a
                     single trial is already reasonably well-conditioned).
        residual_threshold: (float, meters) perpendicular-distance cutoff
                            below which a ray counts as an inlier for a
                            given candidate point.
        max_trials: number of random minimal-subset trials.
        random_state: optional int seed or `numpy.random.Generator`, for
                      reproducibility.

    Returns:
        estimate: (3,) numpy array -- least-squares refit over the best
                  inlier set.
        inlier_mask: (n,) boolean numpy array marking which input rays were
                     classified as inliers to the returned estimate.

    Raises:
        ValueError: fewer rays supplied than `min_samples`.
        RuntimeError: no trial produced a valid (>= min_samples) inlier set,
            e.g. because `residual_threshold` is too tight for the data's
            actual noise level.
    """
    origins = np.asarray(origins, dtype=float)
    directions = np.asarray(directions, dtype=float)
    n_rays = origins.shape[0]
    if n_rays < min_samples:
        raise ValueError(f"Error. Need at least {min_samples} rays for RANSAC "
                         f"(got {n_rays}).")

    rng = np.random.default_rng(random_state)
    unit_dirs = np.array([unit(d) for d in directions])

    best_inliers, best_count = None, -1

    for _ in range(max_trials):
        idx = rng.choice(n_rays, size=min_samples, replace=False)
        try:
            candidate = _closest_point_to_rays(origins[idx], unit_dirs[idx])
        except np.linalg.LinAlgError:
            continue

        residuals = perpendicular_residuals(candidate, origins, unit_dirs)
        inliers = residuals < residual_threshold
        count = int(np.sum(inliers))
        if count > best_count:
            best_count, best_inliers = count, inliers

    if best_inliers is None or best_count < min_samples:
        raise RuntimeError(
            "Error. RANSAC failed to find a consistent inlier set of size "
            f">= {min_samples} across {max_trials} trials. Consider "
            "relaxing `residual_threshold` or increasing `max_trials`."
        )

    refined = _closest_point_to_rays(origins[best_inliers], unit_dirs[best_inliers])
    return refined, best_inliers


def pairwise_ray_intersections(origins, directions):
    """Returns, for every pair of rays, the midpoint of their mutual
       closest-approach points -- i.e. a classic "pairwise intersection
       point" for two (generally skew, non-intersecting) 3-D lines.

       This is NOT used by the primary estimator (`triangulate_rays` /
       `huber_weighted_triangulate` / `ransac_triangulate` solve the
       proper global least-squares/robust problem over ALL rays at
       once, which is strictly better-conditioned). It exists purely to
       produce an intuitive point CLOUD for visualization -- e.g. the
       demo's 3-D view plots this cloud ("clustering of intersection
       points from the DOA rays") next to the single robust estimate,
       so a viewer can see how tightly the individual pairwise
       intersections agree (a visual proxy for estimate confidence).

       Args:
           origins: (n, 3) array-like of ray origins.
           directions: (n, 3) array-like of ray directions (need not be
               pre-normalized).

       Returns:
           (n_pairs, 3) numpy array of pairwise closest-approach
           midpoints, one row per unordered pair of input rays
           (n_pairs = n * (n - 1) / 2). Nearly-parallel pairs (which
           have no well-defined closest point) are skipped.
    """
    origins = np.asarray(origins, dtype=float)
    directions = np.asarray(directions, dtype=float)
    n_rays = origins.shape[0]
    unit_dirs = np.array([unit(d) for d in directions])

    points = []
    for i in range(n_rays):
        for j in range(i + 1, n_rays):
            o1, d1 = origins[i], unit_dirs[i]
            o2, d2 = origins[j], unit_dirs[j]
            b = np.dot(d1, d2)
            denom = 1.0 - b ** 2
            if abs(denom) < 1e-9:
                continue  # (near-)parallel rays: no unique closest point
            r = o1 - o2
            c = np.dot(d1, r)
            f = np.dot(d2, r)
            # Standard two-line closest-point formula (d1, d2 unit vectors):
            # t1 = (b*f - c) / denom, t2 = (f - b*c) / denom
            t1 = (b * f - c) / denom
            t2 = (f - b * c) / denom
            p1 = o1 + t1 * d1
            p2 = o2 + t2 * d2
            points.append((p1 + p2) / 2.0)

    return np.array(points) if points else np.empty((0, 3))


def huber_weighted_triangulate(origins, directions, delta=0.03, max_iter=25, tol=1e-9):
    """Iteratively-reweighted least squares (IRLS) triangulation with a
       Huber loss on each ray's perpendicular residual.

       Rays with residual <= delta keep full weight (behaves like ordinary
       least squares); rays with larger residuals are down-weighted
       proportional to delta / residual (linear loss region), which is a
       gentler alternative to RANSAC's hard inlier/outlier cutoff -- useful
       when outliers are moderate rather than gross (e.g. angle noise that
       grows with reverberation, rather than a single wildly wrong ray).

    Args:
        origins: (n, 3) array-like of ray origins.
        directions: (n, 3) array-like of ray directions.
        delta: (float, meters) Huber transition point between the quadratic
               and linear loss regions.
        max_iter: maximum IRLS iterations.
        tol: convergence tolerance (meters) on the change in the estimate
             between iterations.

    Returns:
        estimate: (3,) numpy array.
        weights: (n,) numpy array of final per-ray weights (1.0 = full
                 trust, < 1.0 = down-weighted as a likely outlier).
    """
    origins = np.asarray(origins, dtype=float)
    unit_dirs = np.array([unit(d) for d in directions])
    n_rays = origins.shape[0]

    weights = np.ones(n_rays)
    estimate = _closest_point_to_rays(origins, unit_dirs, weights)

    for _ in range(max_iter):
        residuals = perpendicular_residuals(estimate, origins, unit_dirs)
        with np.errstate(divide='ignore', invalid='ignore'):
            weights = np.where(residuals <= delta, 1.0, delta / np.maximum(residuals, 1e-15))

        new_estimate = _closest_point_to_rays(origins, unit_dirs, weights)
        converged = np.linalg.norm(new_estimate - estimate) < tol
        estimate = new_estimate
        if converged:
            break

    return estimate, weights
