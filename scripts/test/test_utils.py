import time
import random
import unittest

from scripts.utils import ThreadWithReturnValue, convert_to_one_list, \
    check_list_of_lists_are_same_length


class ThreadWithReturnValueTestCase(unittest.TestCase):
    """
    Test that a Thread can returns a value
    """
    def setUp(self):
        def target_function(arg, seconds=None):
            """ Test Function """
            if seconds is not None:
                time.sleep(seconds)
            return arg

        self.function = target_function

    def test_thread_returns_value(self):
        """
        Test that the Thread returns a value if given an argument
        """
        my_thread = ThreadWithReturnValue(target=self.function, args=('bananas',))
        my_thread.start()
        returned = my_thread.join()
        self.assertEqual(returned, 'bananas')

    def test_thread_returns_none(self):
        """
        Test that the Thread can return None
        """
        my_thread = ThreadWithReturnValue(target=self.function, args=(None,))
        my_thread.start()
        returned = my_thread.join()
        self.assertEqual(returned, None)

    def test_thread_that_can_timeout(self):
        """
        Test that the Thread can timeout and returns None
        """
        my_thread = ThreadWithReturnValue(target=self.function, args=('stringy',), kwargs={'seconds': 5})
        my_thread.start()
        returned = my_thread.join(timeout=2)
        self.assertEqual(returned, None)

    def test_thread_that_returns_none_and_timeout(self):
        """
        Test whether the Thread returns None because it timed out or from the function output
        """
        my_thread = ThreadWithReturnValue(target=self.function, args=(None,), kwargs={'seconds': 5})
        my_thread.start()
        returned = my_thread.join(timeout=random.randint(1, 10))

        if my_thread.isAlive():
            # returned is None because join() timed out
            # this also means that self.function is still running in the background
            pass
        else:
            # join() is finished, and so is self.function()
            # But we could also be in a race condition, so we need to update returned, just in case
            returned = my_thread.join()
            self.assertEqual(returned, None)


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
