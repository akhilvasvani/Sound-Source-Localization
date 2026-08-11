import unittest
import numpy as np

from src.preprocess import PrepareData


class PrepareDataTestCase(unittest.TestCase):
    def setUp(self):
        head = '/home/akhil/Sound-Source-Localization/data/'
        sample_filepath_default = "".join([head, 'raw/'])
        sample_filename_non_default = "".join([head,
                                               'CMU_ARCTIC/cmu_us_bdl_arctic/wav/',
                                               'arctic_a0001.wav'])

        # PrepareData's constructor takes microphone-location positional
        # args (`*args`) and a `recovered` keyword, not a `default` keyword
        # -- there is no such parameter, so `default=True` always raised
        # TypeError before even reaching the tests below.
        self.src_default = PrepareData(sample_filepath_default)
        self.src_non_default = PrepareData(sample_filename_non_default)


class InitTestCase(PrepareDataTestCase):
    """
    Test that the initial attributes are set up correctly for both
    default and non-default cases.
    """

    def test_default_filepath_type(self):
        test_case = 56
        with self.assertRaises(TypeError):
            self.src_default._read_mat_file(test_case)

    def test_non_default_filepath_type(self):
        test_case = -9.0
        with self.assertRaises(TypeError):
            self.src_non_default._read_mat_file(test_case)


class ReadMatFileCase(PrepareDataTestCase):
    """
    Test that the mat file is read in correctly for
    both default and non-default cases.
    """

    def test_default_file_incorrect(self):
        test_case = 'bananas'
        with self.assertRaises(FileNotFoundError):
            self.src_default._read_mat_file(test_case)

    def test_non_default_file_incorrect(self):
        test_case = '1245'
        with self.assertRaises(FileNotFoundError):
            self.src_non_default._read_mat_file(test_case)


class GetMicSignalLocationCase(PrepareDataTestCase):
    """
    Test that the microphone signal arrays are not empty, contain none,
    or any string values for both default and non-default cases.
    """

    def test_default_signal_not_numpy_array(self):
        test_signal = 'ert'
        with self.assertRaises(TypeError):
            self.src_default._get_mic_signal_location(test_signal)

    def test_default_signal_contains_none(self):
        test_signal = np.array([np.array([5]), np.array([None]), np.array([3])])
        with self.assertRaises(ValueError):
            self.src_default._get_mic_signal_location(test_signal)

    def test_default_signal_contains_empty_string(self):
        test_signal = [np.array([5]), np.array([""]), np.array([3])]
        test_numpy_signal = np.array(test_signal)
        with self.assertRaises(ValueError):
            self.src_default._get_mic_signal_location(test_numpy_signal)

    def test_default_signal_empty(self):
        # dtype=object is required here on modern numpy: building a plain
        # np.array() from ragged (different-length) sub-arrays now raises
        # ValueError itself instead of silently creating an object array,
        # which would fail this test before it even reached the method
        # under test.
        test_signal = np.array([np.array([3, 4]), np.array([]), np.array([3])],
                               dtype=object)
        with self.assertRaises(ValueError):
            self.src_default._get_mic_signal_location(test_signal)

    def test_non_default_signal_not_numpy_array(self):
        test_signal = 'wxdfbf'
        with self.assertRaises(TypeError):
            self.src_default._get_mic_signal_location(test_signal)

    def test_non_default_signal_contains_none(self):
        test_signal = np.array([np.array([5]), np.array([None]), np.array([3])])
        with self.assertRaises(ValueError):
            self.src_default._get_mic_signal_location(test_signal)

    def test_non_default_signal_contains_empty_string(self):
        test_signal = [np.array([5]), np.array([""]), np.array([3])]
        test_numpy_signal = np.array(test_signal)
        with self.assertRaises(ValueError):
            self.src_default._get_mic_signal_location(test_numpy_signal)

    def test_non_default_signal_empty(self):
        test_signal = np.array([np.array([3, 4]), np.array([]), np.array([3])],
                               dtype=object)
        with self.assertRaises(ValueError):
            self.src_default._get_mic_signal_location(test_signal)


if __name__ == '__main__':
    unittest.main()
