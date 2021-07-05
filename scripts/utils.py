#!/usr/bin/env python
"""This script contains utility functions that are helpful
for the sound source localization script."""

import multiprocessing


class MultiProcessingWithReturnValue(object):
    def __init__(self, func, *args):
        """Define the function and function arguments to be multi-processed."""
        self.func = func
        self.args = args

    def run(self, *args):
        """Run the function, with its correct function arguments."""
        return self.func(args[0][0], *args[0][1])

    def pooled(self):
        """Multi-process the function"""

        with multiprocessing.Pool() as pool:
            *a, = pool.map(self.run, self.args)
        return a
