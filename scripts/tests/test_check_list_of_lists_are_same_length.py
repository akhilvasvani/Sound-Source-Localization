from scripts.utils import check_list_of_lists_are_same_length

import unittest


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
