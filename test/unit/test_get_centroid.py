import unittest
import numpy as np

from scripts.sound_source_localization import SoundSourceLocation


class GetCentroidTestCase(unittest.TestCase):
    """
    Test to generate Centriods
    """

    def setUp(self):
        sample_filepath, sample_method = 'blah', 'SRP'
        self.test_src = SoundSourceLocation(sample_filepath, sample_method)
        self.function = self.test_src.get_centroid

    def test_mic_list_empty(self):
        test_list = []
        with self.assertRaises(ValueError):
            self.function(test_list)

    def test_mic_list_None(self):
        test_list = [None]
        with self.assertRaises(ValueError):
            self.function(test_list)

    def test_mic_lists_not_same_length(self):
        test_list = [[5.0, 7.0], [7.9, -0.56], [7.0, -4.5, 6.0]]
        with self.assertRaises(TypeError):
            self.function(test_list)

    def test_mic_list_not_all_float_types(self):
        test_list = [[5.0, 7.0], [7.9, -0.56], ['5', 8.0]]
        with self.assertRaises(TypeError):
            self.function(test_list)

    def test_small_mic_list(self):
        test_list = [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]
        test_result_list = np.array([2.0, 2.0])
        self.assertTrue(np.allclose(self.function(test_list), test_result_list,
                                    rtol=1e-05, atol=1e-08))

    def test_large_mic_list(self):
        test_list = [[1.0, 2.0, 3.0, 4.0], [2.0, 3.0, 4.0, 5.0],
                     [3.0, 4.0, 5.0, 6.0], [4.0, 5.0, 6.0, 7.0]]
        test_result_list = np.array([2.5, 3.5, 4.5, 5.5])
        self.assertTrue(np.allclose(self.function(test_list), test_result_list,
                                    rtol=1e-05, atol=1e-08))


if __name__ == '__main__':
    unittest.main()
