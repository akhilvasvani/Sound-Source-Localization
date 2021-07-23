import unittest
import numpy as np

from scripts.sound_source_localization import SoundSourceLocation

# TODO:
#   1) Test one Real case in DifferenceOfArrivalsTestCase


class SoundSourceLocationTestCase(unittest.TestCase):
    def setUp(self):
        sample_filepath, sample_method = '/home/akhil/Sound-Source-Localization/data/heart sound/raw/', 'SRP'
        self.src = SoundSourceLocation(sample_filepath, sample_method)

        self.test_get_centroid = self.src.get_centroid

        self.test_get_mic_match_with_sound_data = self.src.get_mic_match_with_sound_data
        self.test_difference_of_arrivals = self.src.get_difference_of_arrivals
        self.test_get_estimates = self.src.get_estimates
        self.test_process_potential_estimates = self.src.process_potential_estimates

    def create_loc_and_sound_data_list(self):
        self.test_mic_loc = [[i, i + 1, i + 2] for i in range(3)]
        self.test_sound_data = np.array([[i, 2 * i + 1, i - 1] for i in range(3)])

        return list(zip(self.test_mic_loc, self.test_sound_data))

    def create_mic_loc_and_sound_data_dict(self):
        self.test_mic_list = ['mic1', 'mic2', 'mic3']
        self.test_mic_loc_and_sound_data = self.create_loc_and_sound_data_list()
        return dict(zip(self.test_mic_list, self.test_mic_loc_and_sound_data))


class InitTestCase(SoundSourceLocationTestCase):
    """
    Test that the initial attributes are set up correctly
    """

    def test_sound_speed(self):
        self.assertEqual(self.src.sound_speed, 30)

    def test_combinations_number(self):
        self.assertEqual(self.src.mic_combinations_number, 3)

    def test_sampling_frequency(self):
        self.assertEqual(self.src.fs, 16000)

    def test_fast_fourier_transform_size(self):
        self.assertEqual(self.src.fft_size, 256)

    def test_frequency_range(self):
        self.assertEqual(self.src.freq_range, [0, 250])

    def test_tolerance(self):
        self.assertEqual(self.src.tol, 1e-3)

    def test_radius(self):
        test_radius = np.arange(0, 0.5, self.src.tol)[:, np.newaxis]
        self.assertTrue(np.allclose(self.src.radius, test_radius, rtol=1e-05, atol=1e-08))


class GetCentroidTestCase(SoundSourceLocationTestCase):
    """
    Test to generate Centroids
    """

    def test_mic_list_empty(self):
        test_list = []
        with self.assertRaises(ValueError):
            self.test_get_centroid(test_list)

    def test_mic_list_None(self):
        test_list = [None]
        with self.assertRaises(ValueError):
            self.test_get_centroid(test_list)

    def test_mic_list_with_None(self):
        test_list = [[5, 7, 3, None]]
        with self.assertRaises(ValueError):
            self.test_get_centroid(test_list)

    def test_mic_lists_not_same_length(self):
        test_list = [[5.0, 7.0], [7.9, -0.56], [7.0, -4.5, 6.0]]
        with self.assertRaises(ValueError):
            self.test_get_centroid(test_list)

    def test_mic_list_not_all_float_types(self):
        test_list = [[5.0, 7.0], [7.9, -0.56], ['5', 8.0]]
        with self.assertRaises(TypeError):
            self.test_get_centroid(test_list)

    def test_small_mic_list(self):
        test_list = [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]
        test_result_list = np.array([2.0, 2.0])
        self.assertTrue(np.allclose(self.test_get_centroid(test_list), test_result_list,
                                    rtol=1e-05, atol=1e-08))

    def test_large_mic_list(self):
        test_list = [[1.0, 2.0, 3.0, 4.0], [2.0, 3.0, 4.0, 5.0],
                     [3.0, 4.0, 5.0, 6.0], [4.0, 5.0, 6.0, 7.0]]
        test_result_list = np.array([2.5, 3.5, 4.5, 5.5])
        self.assertTrue(np.allclose(self.test_get_centroid(test_list), test_result_list,
                                    rtol=1e-05, atol=1e-08))


class GetMicMatchWithSoundDataTestCase(SoundSourceLocationTestCase):
    """
    Test to see microphone associated signal data
    """

    def test_sound_data_empty(self):
        test_mic_loc = [[i, i + 1, i + 2] for i in range(3)]
        test_sound_data = []
        test_mic_list = ['mic1', 'mic2', 'mic3']

        test_mic_loc_sound_data = dict(zip(test_mic_list, list(zip(test_mic_loc, test_sound_data))))
        with self.assertRaises(ValueError):
            self.test_get_mic_match_with_sound_data(test_mic_loc_sound_data, test_mic_list)

    def test_sound_data_single_none(self):
        test_sound_data = np.array([None])
        test_mic_list = ['mic1', 'mic2', 'mic3']
        with self.assertRaises(ValueError):
            self.test_get_mic_match_with_sound_data(test_sound_data, test_mic_list)

    def test_none_in_sound_data(self):
        test_sound_data = np.array([5, 7, None])
        test_mic_list = ['mic1', 'mic2', 'mic3']
        with self.assertRaises(ValueError):
            self.test_get_mic_match_with_sound_data(test_sound_data, test_mic_list)

    def test_sound_data_empty_string(self):
        test_sound_data = np.array([""])
        test_mic_list = ['mic1', 'mic2', 'mic3']
        with self.assertRaises(ValueError):
            self.test_get_mic_match_with_sound_data(test_sound_data, test_mic_list)

    def test_sound_data_empty_mic_list(self):
        test_sound_data = np.array([4.700, 4.9966, 4.7770])
        test_mic_list = []
        with self.assertRaises(ValueError):
            self.test_get_mic_match_with_sound_data(test_sound_data, test_mic_list)

    def test_sound_data(self):
        test_mic_loc = [[i, i + 1, i + 2] for i in range(3)]
        test_sound_data = np.array([[i, 2 * i + 1, i - 1] for i in range(3)])

        test_mic_list = ['mic1', 'mic2', 'mic3']
        test_mic_loc_and_sound_data = list(zip(test_mic_loc, test_sound_data))

        test_mic_loc_and_sound_data_dict = dict(zip(test_mic_list, test_mic_loc_and_sound_data))

        result_signal_list = [np.array([0,  1, -1]), np.array([1, 3, 0]),
                              np.array([2, 5, 1])]
        result_mic_loc_list = [[0, 1, 2],
                               [1, 2, 3],
                               [2, 3, 4]]
        test_result_signal_list, test_result_mic_loc_list = self.test_get_mic_match_with_sound_data(test_mic_loc_and_sound_data_dict,
                                                                                                    *test_mic_list)
        self.assertTrue(np.allclose(result_signal_list, test_result_signal_list, rtol=1e-05, atol=1e-08))
        self.assertEqual(result_mic_loc_list, test_result_mic_loc_list)


class DifferenceOfArrivalsTestCase(SoundSourceLocationTestCase):
    """
    Test difference of arrival method
    """
    def test_signal_list_empty(self):
        test_signal_list = []
        test_mic_location = ([[0, 1, 2], [1, 2, 3], [2, 3, 4]],)
        with self.assertRaises(ValueError):
            self.test_difference_of_arrivals(test_signal_list, *test_mic_location)

    def test_signal_list_small_with_none(self):
        test_signal_list = [None]
        test_mic_location = ([[0, 1, 2], [1, 2, 3], [2, 3, 4]],)
        with self.assertRaises(ValueError):
            self.test_difference_of_arrivals(test_signal_list, *test_mic_location)

    def test_signal_list_large_with_None(self):
        test_signal_list = [np.array([5]), [None], np.array([10])]
        test_mic_location = ([[0, 1, 2], [1, 2, 3], [2, 3, 4]],)
        with self.assertRaises(ValueError):
            self.test_difference_of_arrivals(test_signal_list, *test_mic_location)

    def test_mic_list_empty(self):
        test_signal_list = [np.array([5]), np.array([6]), np.array([7])]
        test_mic_location = ([],)
        with self.assertRaises(ValueError):
            self.test_difference_of_arrivals(test_signal_list, *test_mic_location)

    def test_mic_list_none(self):
        test_signal_list = [np.array([5]), np.array([6]), np.array([7])]
        test_mic_location = ([[None, None, None]],)
        with self.assertRaises(ValueError):
            self.test_difference_of_arrivals(test_signal_list, *test_mic_location)

    def test_mic_list_large_with_none(self):
        test_signal_list = [np.array([5]), np.array([6]), np.array([7])]
        test_mic_location = ([[3, 9, 10], [None, 5, 4.0]],)
        with self.assertRaises(ValueError):
            self.test_difference_of_arrivals(test_signal_list, *test_mic_location)

    # # TODO: Test for Real Case
    # def test_difference_of_arrivals(self):
    #     test_signal_list = [np.array([i, 2 * i + 1, i - 1]) for i in range(3)]
    #     test_mic_location = ([[0, 1, 2], [1, 2, 3], [2, 3, 4]],)
    #
    #     self.test_difference_of_arrivals(test_signal_list, *test_mic_location)


if __name__ == '__main__':
    unittest.main()
