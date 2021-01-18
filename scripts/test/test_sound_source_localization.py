import unittest
import numpy as np

from scripts.sound_source_localization import SoundSourceLocation


class SoundSourceLocationTestCase(unittest.TestCase):
    def setUp(self):
        sample_filepath, sample_method = '/home/akhil/Sound-Source-Localization/data/raw/', 'SRP'
        self.src = SoundSourceLocation(sample_filepath, sample_method)

        self.test_get_centroid = self.src.get_centroid
        self.test_get_sound_data = self.src.get_sound_data
        self.test_get_mic_match_with_sound_data = self.src.get_mic_match_with_sound_data
        self.test_difference_of_arrivals = self.src.difference_of_arrivals
        self.test_get_estimates = self.src.get_estimates
        self.test_process_potential_estimates = self.src.process_potential_estimates


class InitTestCase(SoundSourceLocationTestCase):
    """
    Test that the initial attributes are set up correctly
    """

    def test_sound_speed(self):
        self.assertEqual(self.src.sound_speed, 30)

    def test_combinations_number(self):
        self.assertEqual(self.src.combinations_number, 3)

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

    def test_mic_lists_not_same_length(self):
        test_list = [[5.0, 7.0], [7.9, -0.56], [7.0, -4.5, 6.0]]
        with self.assertRaises(TypeError):
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


class GetSoundDataTestCase(SoundSourceLocationTestCase):
    """
    Test to gather sound data
    """

    def test_recovered(self):
        self.src.recovered = 'RS'
        test_name_of_source = 'S1_Cycle1'
        with self.assertRaises(TypeError):
            self.test_get_sound_data(test_name_of_source)

    def test_incorrect_name_of_source(self):
        test_name_of_source = 'Aloha'
        with self.assertRaises(NameError):
            self.test_get_sound_data(test_name_of_source)

    def test_incorrect_name_of_source_different_type(self):
        test_name_of_source = 5
        with self.assertRaises(NameError):
            self.test_get_sound_data(test_name_of_source)


class GetMicMatchWithSoundDataTestCase(SoundSourceLocationTestCase):
    """
    Test to see microphone associated signal data
    """

    def test_sound_data_empty(self):
        test_sound_data = np.array([])
        test_mic_list = ['mic1, mic2, mic3']
        with self.assertRaises(ValueError):
            self.test_get_mic_match_with_sound_data(test_sound_data, test_mic_list)

    def test_sound_data_single_none(self):
        test_sound_data = np.array([None])
        test_mic_list = ['mic1, mic2, mic3']
        with self.assertRaises(ValueError):
            self.test_get_mic_match_with_sound_data(test_sound_data, test_mic_list)

    def test_none_in_sound_data(self):
        test_sound_data = np.array([5, 7, None])
        test_mic_list = ['mic1, mic2, mic3']
        with self.assertRaises(ValueError):
            self.test_get_mic_match_with_sound_data(test_sound_data, test_mic_list)

    def test_sound_data_empty_string(self):
        test_sound_data = np.array([""])
        test_mic_list = ['mic1, mic2, mic3']
        with self.assertRaises(ValueError):
            self.test_get_mic_match_with_sound_data(test_sound_data, test_mic_list)

    def test_sound_data_empty_mic_list(self):
        test_sound_data = np.array([4.700, 4.9966, 4.7770])
        test_mic_list = []
        with self.assertRaises(ValueError):
            self.test_get_mic_match_with_sound_data(test_sound_data, test_mic_list)

    def test_sound_data(self):
        test_sound_data = np.array([[i, i + 1, i + 2] for i in range(12)])
        test_mic_list = ['mic1', 'mic2', 'mic3']
        result_signal_list = [np.array([0, 1, 2]), np.array([1, 2, 3]),
                              np.array([2, 3, 4])]
        result_mic_loc_list = [[-0.102235, -0.109982, 0.056388],
                               [-0.102235, -0.109982, 0.001524],
                               [-0.102235, -0.109982, -0.05334]]
        test_result_signal_list, test_result_mic_loc_list = self.test_get_mic_match_with_sound_data(test_sound_data,
                                                                                                    *test_mic_list)
        self.assertTrue(np.allclose(result_signal_list, test_result_signal_list, rtol=1e-05, atol=1e-08))
        self.assertEqual(result_mic_loc_list, test_result_mic_loc_list)

    def test_mismatch_sound_data_and_mic_loc_list(self):
        test_sound_data = np.array([[i, i + 1, i + 2] for i in range(11)])
        test_mic_list = ['mic1', 'mic2', 'mic3']
        self.assertTrue(self.test_get_mic_match_with_sound_data(test_sound_data, *test_mic_list),
                        f"Error. Mismatch in length of microphone location list "
                        f"and length of signal list.")


# TODO: Test for Real Case
class DifferenceOfArrivalsTestCase(SoundSourceLocationTestCase):
    """
    Test difference of arrival method
    """
    def test_signal_list_emtpy(self):
        test_signal_list = []
        test_mic_list = [['mic1', 'mic2', 'mic3']]
        with self.assertRaises(ValueError):
            self.test_difference_of_arrivals(test_signal_list, *test_mic_list)

    def test_signal_list_None(self):
        test_signal_list = [None]
        test_mic_list = [['mic1', 'mic2', 'mic3']]
        with self.assertRaises(ValueError):
            self.test_difference_of_arrivals(test_signal_list, *test_mic_list)

    def test_mic_list_emtpy(self):
        test_signal_list = [[5, 6, 7]]
        test_mic_list = []
        with self.assertRaises(ValueError):
            self.test_difference_of_arrivals(test_signal_list, *test_mic_list)

    def test_mic_list_none(self):
        test_signal_list = [[5, 6, 7]]
        test_mic_list = [None]
        with self.assertRaises(ValueError):
            self.test_difference_of_arrivals(test_signal_list, *test_mic_list)

#
# # TODO: TEST THIS
# class GetEstimatesTestCase(SoundSourceLocationTestCase):
#     """
#     Test get estimates
#     """


if __name__ == '__main__':
    unittest.main()
