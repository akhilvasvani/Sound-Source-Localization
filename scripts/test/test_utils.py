import unittest

from scripts.validations import convert_to_one_list, \
    check_list_of_lists_are_same_length


# TODO: Test Mult-processing

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
