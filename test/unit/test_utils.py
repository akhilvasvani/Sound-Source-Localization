import unittest
import numpy as np

from scripts.validations import convert_to_one_list, \
    check_list_of_lists_are_same_length

from scripts.utils import MultiProcessingWithReturnValue


def target_function(sample_name, *args):
    """Test Function. Outside the class because multiprocessing class
       cannot inherit nested functions."""
    return sample_name, np.add(*args)

class MultiProcessingWithReturnValueTestCase(unittest.TestCase):
    """
    Test that a Multiprocess can return a value
    """

    def test_process_returns_value(self):

        test_mic_loc = [[i, i + 1, i + 2] for i in range(3)]
        test_sound_data = np.array([[i, 2 * i + 1, i - 1] for i in range(3)])
        test_mic_list = ['mic'+str(i+1) for i in range(3)]

        test_mic_loc_and_sound_data = list(zip(test_mic_loc, test_sound_data))

        test_mic_loc_and_sound_data_dict = zip(test_mic_list, test_mic_loc_and_sound_data)

        test_sam = MultiProcessingWithReturnValue(target_function,
                                                  *test_mic_loc_and_sound_data_dict).pooled()

        result = [('mic1', np.array([0, 2, 1])),
                  ('mic2', np.array([2, 5, 3])),
                  ('mic3', np.array([4, 8, 5]))]

        self.assertEqual([a[0] for a in test_sam], [b[0] for b in result])
        self.assertTrue(np.allclose([a[1] for a in test_sam], [b[1] for b in result]))


class ConvertToOneListTestCase(unittest.TestCase):
    """
    Test that lists inside a list are converted to one list
    """

    def setUp(self):
        self.function = convert_to_one_list

    def test_empty_list(self):
        test_list = []
        with self.assertRaises(ValueError):
            self.function(test_list)

    def test_one_list(self):
        test_list = [5]
        test_result = [5]
        self.assertEqual(self.function(test_list), test_result)

    def test_two_lists(self):
        test_list = [[5]]
        test_result = [5]
        self.assertEqual(self.function(test_list), test_result)

    def test_two_lists_multiple_values(self):
        test_list = [[5], [6]]
        test_result = [5, 6]
        self.assertEqual(self.function(test_list), test_result)

    def test_three_lists_multiple_values(self):
        test_list = [[5], [6], [[[4, 2, 1]]]]
        test_result = [5, 6, 4, 2, 1]
        self.assertEqual(self.function(test_list), test_result)


class CheckListOfListsAreSameLengthCase(unittest.TestCase):
    """
    Test that lists within a list are of the same length
    """

    def setUp(self):
        self.function = check_list_of_lists_are_same_length

    def test_empty_list(self):
        test_list = []
        with self.assertRaises(ValueError):
            self.function(test_list)

    def test_single_list(self):
        test_list = [[1]]
        self.assertEqual(self.function(test_list), True)

    def test_small_multiple_list(self):
        test_list = [[1], ['7']]
        self.assertEqual(self.function(test_list), True)

    def test_large_multiple_list(self):
        test_list = [[1], ['7'], [3], [9], [8.0, 1, 3.8]]
        self.assertEqual(self.function(test_list), False)

    def test_large_multiple_values_list(self):
        test_list = [[1, 1, 1], ['7', 'a', 'c'], [3, 7, 8], [9, 8, 9], [8.0, 1, 3.8], ['y2k', 8, 8, 8]]
        self.assertEqual(self.function(test_list), False)


if __name__ == '__main__':
    unittest.main()
