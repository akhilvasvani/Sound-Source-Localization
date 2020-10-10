#!/usr/bin/env python

from scripts.utils import ThreadWithReturnValue

import time
import random
import unittest


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


if __name__ == '__main__':
    unittest.main()
