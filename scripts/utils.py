#!/usr/bin/env python
"""This script contains utility functions that are helpful
for the sound source localization script."""

import multiprocessing


class MultiProcessingWithReturnValue:
    """MultiProcessingWithReturnValue receives a function and its corresponding
       arguments, as in input, and runs the function on multiple cores.
       Each output is saved into a list and returned.

       Attributes:
           func: the function to run
           args: the function's arguments
    """
    def __init__(self, func, *args):
        """Initializes MultiProcessingWithReturnValue with func and *args."""
        self.func = func
        self.args = args

    def run(self, *args):
        """Run the function, with its correct function arguments."""
        return self.func(args[0][0], *args[0][1])

    def pooled(self):
        """Multi-process the function"""

        with multiprocessing.Pool() as pool:
            *sample_output, = pool.map(self.run, self.args)
        return sample_output
