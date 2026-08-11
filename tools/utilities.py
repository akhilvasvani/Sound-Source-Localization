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
    """Generates a microphone sub-array using one of pyroomacoustics'
       pre-arranged 2-D layouts (linear/circular/square/poisson/spiral),
       placed at a requested 3-D center, and validated against the actual
       room bounds.

       IMPORTANT (bug fix): earlier versions of this class (a) accepted
       only the room's dimensionality (an integer, e.g. 3) instead of its
       physical bounds, so out-of-room microphone placements could never be
       detected, and (b) forced every generated microphone's z-coordinate
       to 0.0, silently discarding the z requested in `center`. Both are
       fixed here: `room_dimension` is now the actual [x, y, z] extent of
       the room (in meters), used to validate every generated microphone
       position, and every 3-D microphone keeps the requested `center[-1]`
       z-coordinate (pyroomacoustics' 2-D array generators only vary x/y,
       so a shared z-height for the sub-array is the correct behavior, not
       an arbitrary 0).

       Attributes:
           custom: (string) one of 'linear', 'circular', 'square',
                   'poisson', 'spiral'
           center: (list) [x, y, z] center of the sub-array, in meters
           number_of_microphones_to_use: (int) microphones in this sub-array
           room_dimension: (list) [x, y, z] physical room bounds, in
                           meters, used to bounds-check generated positions
           kwargs: layout-specific parameters (phi, d, n, r, radius, ...)
    """

    def __init__(self, custom, center, number_of_microphones_to_use,
                 room_dimension, **kwargs):

        self.custom = custom
        self.center = center
        self.number_of_microphones = number_of_microphones_to_use

        if isinstance(room_dimension, (int, np.integer)):
            raise TypeError(
                "Error. `room_dimension` must be the room's physical "
                "[x, y, z] bounds (e.g. [4.0, 3.0, 2.5]), not a bare "
                "dimensionality count. This is required to bounds-check "
                "generated microphone positions against the actual room."
            )
        self.room_dimension = np.asarray(room_dimension, dtype=float)
        self.n_dims = len(self.room_dimension)
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

    def _validate_within_room(self, mic_array):
        """Raises ValueError if any generated microphone falls outside the
           room's physical bounds. This is the fix for the original bug
           where an invalid (partially or fully out-of-room) microphone
           array would be silently handed to pyroomacoustics, which then
           failed deep inside its image-source reflection computation with
           an opaque error instead of a clear, actionable one.

           Args:
               mic_array: (n_dims, n_mics) numpy array of mic coordinates.
        """
        mics = np.asarray(mic_array, dtype=float).T  # -> (n_mics, n_dims)
        lower_ok = mics >= 0.0
        upper_ok = mics <= self.room_dimension[np.newaxis, :]
        bad_rows = ~(lower_ok & upper_ok).all(axis=1)

        if np.any(bad_rows):
            bad_positions = mics[bad_rows].tolist()
            raise ValueError(
                f"Error. {int(np.sum(bad_rows))} of {mics.shape[0]} generated "
                f"microphone(s) fall outside the room bounds "
                f"{self.room_dimension.tolist()}: {bad_positions}. Reduce the "
                "array spacing/aperture (e.g. 'd', 'phi', 'radius') or move "
                "'center' further from the room walls."
            )

    def run(self):
        self.microphones = self.generate_custom_microphone_locations()

        if self.n_dims == 3:  # 3-D
            # Bug fix: previously every 3-D microphone's z-coordinate was
            # forced to 0.0 regardless of the requested `center`. The 2-D
            # array generators (linear/circular/square/poisson/spiral) only
            # ever vary x and y, so lifting the whole sub-array to the
            # requested z-height (center[-1]) is the correct behavior.
            z_height = float(self.center[-1])
            n_mics_generated = (self.microphones.shape[-1] if self.custom == 'square'
                                else self.number_of_microphones)
            mic_array = np.array(list(self.microphones) +
                                 [np.full(n_mics_generated, z_height)])
        elif 0 < self.n_dims < 3:  # 2-D and 1-D
            mic_array = self.microphones
        else:
            raise ValueError("Error. Need a microphone location to use")

        self._validate_within_room(mic_array)
        return mic_array
