"""Unit tests for src.triangulation.pairwise_ray_intersections.

Note: an earlier draft of this function had a sign error in the
two-line closest-point formula (both `t1`/`t2` parametric offsets were
negated), which silently reflected every computed intersection point
through its ray's origin. These tests pin down the corrected formula.
"""

import numpy as np

from src.triangulation import pairwise_ray_intersections


def test_three_rays_through_common_point_recovered_exactly():
    origins = np.array([[0, 0, 0], [2, 0, 0], [0, 2, 0]], dtype=float)
    directions = np.array([[1, 1, 1], [-1, 1, 1], [1, -1, 1]], dtype=float)

    points = pairwise_ray_intersections(origins, directions)

    assert points.shape == (3, 3)
    for p in points:
        assert np.allclose(p, [1.0, 1.0, 1.0], atol=1e-9)


def test_skew_non_intersecting_rays_midpoint_is_reasonable():
    # Two rays offset along z that would intersect at (0,0,*) in the
    # xy-plane if not for a 1-unit vertical (z) offset between them --
    # the pairwise "intersection" should be the midpoint of their
    # closest approach, at z = 0.5 (halfway between the two lines).
    origins = np.array([[-1, 0, 0], [-1, 0, 1]], dtype=float)
    directions = np.array([[1, 0, 0], [1, 0, 0]], dtype=float)
    # Directions are parallel here (both along +x) -- use non-parallel
    # skew lines instead:
    origins = np.array([[-1, 0, 0], [0, -1, 1]], dtype=float)
    directions = np.array([[1, 0, 0], [0, 1, 0]], dtype=float)

    points = pairwise_ray_intersections(origins, directions)
    assert points.shape == (1, 3)
    # Ray 1 passes through (0, 0, 0); ray 2 passes through (0, 0, 1).
    # Closest approach midpoint should be (0, 0, 0.5).
    assert np.allclose(points[0], [0.0, 0.0, 0.5], atol=1e-9)


def test_parallel_rays_are_skipped():
    origins = np.array([[0, 0, 0], [1, 1, 0]], dtype=float)
    directions = np.array([[1, 0, 0], [1, 0, 0]], dtype=float)

    points = pairwise_ray_intersections(origins, directions)
    assert points.shape == (0, 3)


def test_empty_for_single_ray():
    origins = np.array([[0, 0, 0]], dtype=float)
    directions = np.array([[1, 0, 0]], dtype=float)

    points = pairwise_ray_intersections(origins, directions)
    assert points.shape == (0, 3)
