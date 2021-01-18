# !/usr/bin/env python
"""In this script, validations will contain wrappers used to check validations
for all the functions and classes."""

import functools
import numpy as np


def validate_instance_type(sample_object, sample_type):
    return isinstance(sample_object, sample_type)


def validate_empty_list(sample_list):
    return True if not sample_list else False


def validate_file_path(func):
    """Validates file_name type and if a .mat file."""

    @functools.wraps(func)
    def validated(*args):
        file_name = args[-1]
        if not validate_instance_type(file_name, str):
            raise TypeError("Filename is not a string type.")
        # if not file_name.endswith(".mat"):
        #     raise ValueError("Error. Filename is not a MAT file. Require "
        #                      "specific form to perform sound source "
        #                      "localization.")
        result = func(*args)
        return result
    return validated


def validate_centroid(func):

    @functools.wraps(func)
    def validated(*args):

        result = func(*args)
        return result
    return validated


def validate_signal_data(func):
    """Validates the signal data for a numpy array, an empty numpy array,
       None in the array, an empty string, or if the list is empty."""

    @functools.wraps(func)
    def validated(*args):
        if not validate_instance_type(args[-1], np.ndarray):
            raise TypeError("Error. Signal data is not a numpy array")
        if not args[-1].tolist() or (args[-1].size == 1 and None in args[-1].tolist()):
            raise ValueError("Error. The signal is empty.")
        if None in args[-1]:
            raise ValueError('Error. The signal contains None.')
        if "" in args[-1].tolist():
            raise ValueError('Error. The signal contains an empty string.')
        result = func(*args)
        return result
    return validated


def validate_difference_of_arrivals(func):
    """Validates the arguments for the difference of arrivals function.
       Check if the signal list is empty or if None in the signal list.
       Check if the microphone list is empty or if None in the microphone
       location list.
    """

    @functools.wraps(func)
    def validated(*args):
        signal_list, *mic_location = args[1], args[-1]

        if validate_empty_list(signal_list):
            raise ValueError('Error. Signal list is empty.')
        if np.array(signal_list).shape[0] == 1 and None in signal_list:
            raise ValueError('Error. None in signal list.')
        if validate_empty_list(mic_location):
            raise ValueError('Error. Microphone location list is empty.')
        if None in mic_location:
            raise ValueError('Error. None in microphone location list is empty.')
        # This works for lists of lists, but not for single list
        if any([True for signal in signal_list if None in signal]):
            raise ValueError('Error. None in signal list.')
        result = func(*args)
        return result
    return validated


class ValidateList(object):
    """Class decorator which checks the list type
       and if the list is None.

       Attributes:
           func: the input function
           type: list type
    """

    def __init__(self, func):
        """Initializes the ValidateList object with argument func."""
        functools.update_wrapper(self, func)
        self.func = func
        self.type = list

    def __call__(self, *args, **kwargs):
        """This dunder method would be called instead of the decorated
           function.

           Args:
               args: (tuple) function arguments to the decorated function
               kwargs: (dict) extra keyword arguments to the decorated function
        """
        if validate_empty_list(*args):
            raise ValueError('Error. Sample list is empty.')
        if not validate_instance_type(*args, self.type):
            raise TypeError('Error. Sample list is not a list type.')
        return self.func(*args, **kwargs)
