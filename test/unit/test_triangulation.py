import unittest
import numpy as np

from src.triangulation import (
    unit,
    spherical_to_cartesian,
    triangulate_rays,
    perpendicular_residuals,
    ransac_triangulate,
    huber_weighted_triangulate,
)


def rays_to_exact_point(true_point, origins):
    """Builds exact (noise-free) unit-direction rays from each origin
       toward `true_point`, so the true intersection is known exactly."""
    origins = np.asarray(origins, dtype=float)
    true_point = np.asarray(true_point, dtype=float)
    directions = np.array([unit(true_point - o) for o in origins])
    return origins, directions


class SphericalToCartesianTestCase(unittest.TestCase):
    """The forward direction-vector formula must match the stated physics
       convention (colatitude from +z) and always return a unit vector."""

    def test_pole_is_plus_z(self):
        # colatitude = 0 -> straight up +z, regardless of azimuth
        vec = spherical_to_cartesian(azimuth=1.234, colatitude=0.0)
        self.assertTrue(np.allclose(vec, [0, 0, 1], atol=1e-12))

    def test_equator_azimuth_zero_is_plus_x(self):
        vec = spherical_to_cartesian(azimuth=0.0, colatitude=np.pi / 2)
        self.assertTrue(np.allclose(vec, [1, 0, 0], atol=1e-12))

    def test_equator_azimuth_90_is_plus_y(self):
        vec = spherical_to_cartesian(azimuth=np.pi / 2, colatitude=np.pi / 2)
        self.assertTrue(np.allclose(vec, [0, 1, 0], atol=1e-12))

    def test_colatitude_above_90_degrees_points_below_xy_plane(self):
        # This is the exact case the old `np.arctan`-based ground truth
        # formula got wrong (arctan cannot exceed 90 degrees in magnitude).
        vec = spherical_to_cartesian(azimuth=0.0, colatitude=np.deg2rad(135))
        self.assertLess(vec[2], 0.0)

    def test_output_is_unit_length(self):
        rng = np.random.default_rng(0)
        for _ in range(20):
            az = rng.uniform(-np.pi, np.pi)
            colat = rng.uniform(0, np.pi)
            vec = spherical_to_cartesian(az, colat)
            self.assertAlmostEqual(np.linalg.norm(vec), 1.0, places=10)


class TriangulateExactGeometryTestCase(unittest.TestCase):
    """With noise-free rays, triangulation must recover the true point to
       (near) floating point / machine precision -- this is the core claim
       the repaired triangulation module needs to satisfy."""

    def test_two_orthogonal_rays(self):
        true_point = np.array([1.0, 2.0, 0.5])
        origins = np.array([[0.0, 0.0, 0.0], [2.0, 2.0, 0.0]])
        origins, directions = rays_to_exact_point(true_point, origins)

        estimate = triangulate_rays(origins, directions)
        self.assertTrue(np.allclose(estimate, true_point, atol=1e-9))

    def test_many_random_rays_machine_precision(self):
        rng = np.random.default_rng(42)
        true_point = np.array([0.37, -1.21, 2.05])

        origins = rng.uniform(-5, 5, size=(12, 3))
        origins, directions = rays_to_exact_point(true_point, origins)

        estimate = triangulate_rays(origins, directions)
        error = np.linalg.norm(estimate - true_point)
        # Exact geometry -> should be within float64 numerical noise,
        # many orders of magnitude below 1 mm.
        self.assertLess(error, 1e-9)

    def test_residuals_are_zero_for_exact_rays(self):
        rng = np.random.default_rng(7)
        true_point = np.array([5.0, 5.0, 5.0])
        origins = rng.uniform(0, 10, size=(6, 3))
        origins, directions = rays_to_exact_point(true_point, origins)

        residuals = perpendicular_residuals(true_point, origins, directions)
        self.assertTrue(np.allclose(residuals, 0.0, atol=1e-9))

    def test_needs_at_least_two_rays(self):
        with self.assertRaises(ValueError):
            triangulate_rays(np.zeros((1, 3)), np.array([[1.0, 0.0, 0.0]]))

    def test_parallel_rays_raise_linalg_error(self):
        origins = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
        directions = np.array([[0.0, 0.0, 1.0]] * 3)  # all parallel -> no unique point
        with self.assertRaises(np.linalg.LinAlgError):
            triangulate_rays(origins, directions)


class TriangulateNoisyAndRobustTestCase(unittest.TestCase):
    """Sanity checks for robustness under angle noise and outlier rays."""

    def test_small_angle_noise_degrades_gracefully(self):
        rng = np.random.default_rng(3)
        true_point = np.array([1.0, 1.0, 1.0])
        origins = rng.uniform(-3, 3, size=(10, 3))
        _, exact_directions = rays_to_exact_point(true_point, origins)

        # Perturb each direction by a small random rotation-like jitter.
        noisy_directions = exact_directions + rng.normal(scale=1e-3, size=exact_directions.shape)

        estimate = triangulate_rays(origins, noisy_directions)
        error = np.linalg.norm(estimate - true_point)
        # With ~1e-3 rad-scale direction jitter over a few-meter baseline,
        # error should be small (sub-cm) but not machine-precision.
        self.assertLess(error, 0.05)

    def test_huber_downweights_single_bad_ray(self):
        rng = np.random.default_rng(11)
        true_point = np.array([2.0, -1.0, 0.5])
        origins = rng.uniform(-4, 4, size=(9, 3))
        origins, directions = rays_to_exact_point(true_point, origins)

        # Corrupt one ray's direction badly (simulates a reflection being
        # mistaken for a direct-path arrival).
        directions = directions.copy()
        directions[0] = unit(directions[0] + np.array([3.0, -2.5, 4.0]))

        plain_estimate = triangulate_rays(origins, directions)
        robust_estimate, weights = huber_weighted_triangulate(origins, directions, delta=0.02)

        plain_error = np.linalg.norm(plain_estimate - true_point)
        robust_error = np.linalg.norm(robust_estimate - true_point)

        self.assertLess(robust_error, plain_error)
        self.assertLess(weights[0], 0.5)  # the corrupted ray should be down-weighted

    def test_ransac_rejects_minority_of_outlier_rays(self):
        rng = np.random.default_rng(21)
        true_point = np.array([0.0, 0.0, 1.5])
        origins = rng.uniform(-4, 4, size=(15, 3))
        origins, directions = rays_to_exact_point(true_point, origins)
        directions = directions.copy()

        # Corrupt 4 of 15 rays (~27%) with large, essentially random direction errors.
        outlier_idx = [0, 1, 2, 3]
        for i in outlier_idx:
            directions[i] = unit(rng.uniform(-1, 1, size=3))

        plain_estimate = triangulate_rays(origins, directions)
        robust_estimate, inlier_mask = ransac_triangulate(
            origins, directions, min_samples=3, residual_threshold=0.05,
            max_trials=300, random_state=0)

        plain_error = np.linalg.norm(plain_estimate - true_point)
        robust_error = np.linalg.norm(robust_estimate - true_point)

        self.assertLess(robust_error, 1e-6)
        self.assertLess(robust_error, plain_error)
        # All 4 injected outliers should have been excluded from the winning
        # consensus set.
        for i in outlier_idx:
            self.assertFalse(inlier_mask[i])


if __name__ == '__main__':
    unittest.main()
