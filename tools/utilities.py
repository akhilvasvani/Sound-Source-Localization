#!/usr/bin/env python
"""This script contains utility functions that are helpful
for the sound source localization script."""

import multiprocessing
import numpy as np
import pyroomacoustics as pra


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


class CustomMicrophoneSetUp:

    def __init__(self, custom, center, number_of_microphones_to_use,
                 room_dimension, **kwargs):

        self.custom = custom
        self.center = center
        self.number_of_microphones = number_of_microphones_to_use
        self.room_dimension = room_dimension
        self.kwargs = kwargs

        self.pre_arranged_microphone_setup = {
            'linear': [pra.linear_2D_array, ['phi', 'd']],
            'circular': [pra.circular_2D_array, ['phi', 'r']],
            'square': [pra.square_2D_array, ['n', 'phi', 'd']],
            'poisson': [pra.poisson_2D_array, ['d']],
            'spiral': [pra.spiral_2D_array, ['radius', 'divi', 'angle']]
        }

        self.microphones = 0

    def generate_custom_microphone_locations(self):

        if self.custom not in self.pre_arranged_microphone_setup.keys():
            raise ValueError('Error. Pre-arranged microphone setup is '
                             'not configurable at this time.')

        necessary_func_args = self.pre_arranged_microphone_setup.get(self.custom)[1]
        inputted_args = [key for key in self.kwargs.keys()]

        if necessary_func_args != inputted_args:
            missing_argument = set(necessary_func_args).difference(set(inputted_args))
            raise ValueError(f"Error. Missing {missing_argument} for "
                             "method arguments.")

        func = self.pre_arranged_microphone_setup.get(self.custom)[0]
        *argument_values, = (self.kwargs.get(i)
                             for i in (necessary_func_args[idx]
                                       for idx, value in enumerate(necessary_func_args)))

        if self.custom == 'spiral':
            spiral_argument_values = *argument_values,
            return func(self.center, self.number_of_microphones,
                        radius=spiral_argument_values[0],
                        divi=spiral_argument_values[1],
                        angle=spiral_argument_values[2])
        elif self.custom == 'poisson':
            return func(self.center[:-1], self.number_of_microphones,
                        argument_values[0])
        elif self.custom == 'square':
            return func(self.center[:-1], self.number_of_microphones,
                        argument_values[0], argument_values[1],
                        argument_values[2])
        else:
            return func(self.center[:-1], self.number_of_microphones,
                        argument_values[0], argument_values[1])

    def run(self):
        self.microphones = self.generate_custom_microphone_locations()

        if self.room_dimension == 3:  # 3-D
            if self.custom == 'square':
                return np.array(list(self.microphones) + [np.zeros(self.microphones.shape[-1])])
            return np.array(list(self.microphones) + [np.zeros(self.number_of_microphones)])
        elif 0 < self.room_dimension < 3:  # 2-D and 1-D
            return self.microphones
        else:
            raise ValueError("Error. Need a microphone location to use")
