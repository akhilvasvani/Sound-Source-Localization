import unittest

from scripts.preprocess import PrepareData


class PrepareDataTestCase(unittest.TestCase):
    def setUp(self):
        sample_filepath = '/home/akhil/Sound-Source-Localization/data/raw/'

        self.src1 = PrepareData(sample_filepath)

        self.test_read_mat_file = self.src1._read_mat_file
        self.test_get_signal = self.src1.get_signal
        self.test_get_mic_signal_location = self.src1._get_mic_signal_location


class InitTestCase(PrepareDataTestCase):
    """
    Test that the initial attributes are set up correctly
    """

    def test_filepath_type(self):
        test_case = 56
        with self.assertRaises(TypeError):
            self.test_read_mat_file(test_case)


### MIGHT BE USEFUL?
# class GetSoundDataTestCase(SoundSourceLocationTestCase):
#     """
#     Test to gather sound data
#     """
#
#     def test_recovered(self):
#         self.src.recovered = 'RS'
#         test_name_of_source = 'S1_Cycle1'
#         with self.assertRaises(TypeError):
#             self.test_get_sound_data(test_name_of_source)
#
#     def test_incorrect_name_of_source(self):
#         test_name_of_source = 'Aloha'
#         with self.assertRaises(NameError):
#             self.test_get_sound_data(test_name_of_source)
#
#     def test_incorrect_name_of_source_different_type(self):
#         test_name_of_source = 5
#         with self.assertRaises(NameError):
#             self.test_get_sound_data(test_name_of_source)

# TODO: Write these test cases out
# class GetSignalTestCase(PrepareDataTestCase):
#
#     def test

# TODO: Write these test cases out
# class GetMicSignalLocationTestCase(PrepareDataTestCase):
#
#     def test


if __name__ == '__main__':
    unittest.main()
