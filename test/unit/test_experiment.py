import unittest

from scripts.experiment import ExperimentalMicData


class ExperimentalMicDataTestCase(unittest.TestCase):
    def setUp(self):
        head = '/home/akhil/Sound-Source-Localization/data/'
        self.sample_filename = "".join([head, 'CMU_ARCTIC/cmu_us_bdl_arctic/wav/',
                                        'arctic_a0001.wav'])

        self.sample_room_dimensions = [50/100, 50/100, 50/100]
        self.sample_microphone_location = [15 / 100, 0 / 100, 3 / 100]
        self.sample_source_location = [2.5 / 100, 4.5 / 100, 7.8 / 100]


class InitTestCase(ExperimentalMicDataTestCase):
    """
    Test that the initial attributes are set up correctly.
    """

    def test_no_keyword_arguments(self):
        with self.assertRaises(ValueError):
            self.src1_no_args = ExperimentalMicData(self.sample_filename)

    def test_no_source_dimensions(self):
        with self.assertRaises(ValueError):
            self.src1_no_args = ExperimentalMicData(self.sample_filename,
                                                    room_dim=self.sample_room_dimensions)

    def test_no_microphone_location(self):
        with self.assertRaises(ValueError):
            self.src1_no_args = ExperimentalMicData(self.sample_filename,
                                                    room_dim=self.sample_room_dimensions,
                                                    source_dim=self.sample_source_location)

    def test_file_type(self):
        test_case = 56
        with self.assertRaises(TypeError):
            self.src1 = ExperimentalMicData(test_case,
                                            room_dim=self.sample_room_dimensions,
                                            source_dim=self.sample_source_location,
                                            mic_location=self.sample_microphone_location)


class ReadWavFileTestCase(ExperimentalMicDataTestCase):
    """
    Test that the .wav file is read in correctly.
    """

    def test_incorrect_file_name(self):
        self.sample_wrong_filename = "".join(['/home/akhil/Sound-Source-Localization/data/',
                                              'CMU_ARCTIC/cmu_us_bdl_arctic/wav/',
                                               'arctic.wav'])
        with self.assertRaises(FileNotFoundError):
            self.src1 = ExperimentalMicData(self.sample_wrong_filename,
                                            room_dim=self.sample_room_dimensions,
                                            source_dim=self.sample_source_location,
                                            mic_location=self.sample_microphone_location)._read_wav_file()


if __name__ == '__main__':
    unittest.main()
