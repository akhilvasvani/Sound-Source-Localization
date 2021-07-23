# !/usr/bin/env python
"""In this script, validations will contain wrappers used to check validations
for all the functions and classes."""

import functools
import warnings
import numpy as np

# TODO:
#  1) Clean up repeatedly used functions. Why can't class decorators inherit from other decorators?


class ValidateList:
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


@ValidateList
def convert_to_one_list(sample_list):
    """Converts a list of a list into a single list.

    Args:
        sample_list: the input list to convert

    Returns:
        output_list: a single list
    """

    output_list = []
    for item in sample_list:
        if isinstance(item, list):

            # Call this function on it and append its each value separately.
            # If it has more lists in it this function will call itself again
            for i in convert_to_one_list(item):
                output_list.append(i)
        else:
            output_list.append(item)
    return output_list


@ValidateList
def check_list_of_lists_are_same_length(sample_list):
    it = iter(sample_list)
    the_len = len(next(it))
    return False if not all(len(small_list) == the_len for small_list in it) else True


def validate_instance_type(sample_object, sample_type):
    return isinstance(sample_object, sample_type)


def validate_empty_list(sample_list):
    return True if not sample_list else False


def validate_splits(sample_splits):
    if 0 < sample_splits < 4:
        warnings.warn("Warning: Not enough splits for multiprocessing. "
                      "Expect execution time to be significantly increased.")
        return sample_splits
    elif sample_splits == 0:
        raise ZeroDivisionError('Cannot create splits with no splits.')
    else:
        return sample_splits


def validate_file_path(func):
    """Validates file_name type and if a .mat file."""

    @functools.wraps(func)
    def validated(*args, **kwargs):
        file_name = args[1]
        if not validate_instance_type(file_name, str):
            raise TypeError("Filename is not a string type.")
        # if not file_name.endswith(".mat"): ## NOT YET
        #     raise ValueError("Error. Filename is not a MAT file. Require "
        #                      "specific form to perform sound source "
        #                      "localization.")
        result = func(*args, **kwargs)
        return result
    return validated


def validate_room_source_dim_and_mic_loc(func):
    """Validates that the room dimension, source dimensions and
       microphone locations are set."""

    @functools.wraps(func)
    def validated(*args, **kwargs):
        if not kwargs.get('room_dim'):
            raise ValueError("Error. Need room dimensions.")
        if not kwargs.get('source_dim'):
            raise ValueError("Error. Need source dimensions.")
        if not kwargs.get('mic_location'):
            raise ValueError("Error. Need microphone locations.")
        result = func(*args, **kwargs)
        return result
    return validated


def validate_signal_data(func):
    """Validates the signal data for a numpy array, an empty numpy array,
       None in the array, an empty string, or if the list is empty."""

    @functools.wraps(func)
    def validated(*args):
        for sample_array in args[-1]:
            if not validate_instance_type(sample_array, np.ndarray):
                raise TypeError("Error. Signal data is not a numpy array.")
            if None in sample_array.tolist():
                raise ValueError("Error. The signal contains None.")
            if "" in sample_array.tolist():
                raise ValueError("Error. The signal contains an empty string.")
            if not sample_array.tolist():
                raise ValueError("Error. The signal is empty.")
        result = func(*args)
        return result
    return validated


class ValidateCentroid:
    """Class decorator which checks if the microphone location list is empty,
       if it contains None, if not all the microphones in list are the
       same length type, or if microphone is not a float.
       and if the list is None.

       Attributes:
           func: the input function
    """

    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func

    def __call__(self, *args, **kwargs):

        if validate_empty_list(*args):
            raise ValueError('Error. Microphone location list is empty.')

        if None in convert_to_one_list(*args):
            raise ValueError('Error. Microphone location list contains None.')

        if not check_list_of_lists_are_same_length(*args):
            raise ValueError('Error. Not all microphone locations have '
                             'same length!')

        if not all([isinstance(mic_loc, float) for mic_loc in convert_to_one_list(*args)]):
            raise TypeError('Error. Microphone location list '
                            'does not contain a float type.')
        return self.func(*args, **kwargs)


def validate_get_mic_with_sound_data(func):
    @functools.wraps(func)
    def validated(*args):
        mic_loc_dict, mic_list = args[0], args[-1]
        if not mic_loc_dict:
            raise ValueError('Error. Microphone_Location dictionary is empty.')
        if not mic_list:
            raise ValueError('Error. Microphone list is empty.')
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

        # Check for signal lists with 1 element (None in them) or
        # iterate through a list looking for None
        if (np.array(signal_list).shape[0] == 1 and None in signal_list) or any([True for signal in signal_list if None in signal]):
            raise ValueError('Error. None in signal list.')
        if validate_empty_list(mic_location):
            raise ValueError('Error. Microphone location list is empty.')
        if None in mic_location or None in convert_to_one_list(mic_location):
            raise ValueError('Error. None in microphone location list.')
        result = func(*args)
        return result
    return validated
