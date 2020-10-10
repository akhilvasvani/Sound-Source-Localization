from scripts.utils import convert_to_one_list

import unittest


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


if __name__ == '__main__':
    unittest.main()
