from threading import Thread
from scipy import spatial

import numpy as np


class ThreadWithReturnValue(Thread):
    """
    Created a Thread subclass. It is a workable doaround,
    but it accesses "private" data structures that are specific to Thread implementation, so
    things will get a little hairy. """

    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}, Verbose=None):
        """ Initializes the thread object. """

        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        """ Runs the function if specified for the thread. """
        # If the target function is specified
        if self._target is not None:
            # Run the function
            self._return = self._target(*self._args, **self._kwargs)

    def join(self, *args):
        """ Returns the value of target function running in the thread. """

        Thread.join(self, *args)
        return self._return


def centroid(*args):
    """ Returns the center of n number of microphones.
    Keyword Arguments:
        args -- location of each n microphone
    """

    # Initiate
    microphone_array = np.zeros((len(args), len(args[1])))

    # Converts microphone locations into an array
    # for i in range(len(args)):
    for i, item in enumerate(args):
        microphone_array[i, :] = np.array(args[i])

    # Finds the centroid
    return np.sum(microphone_array, axis=0) / len(args)


def create_microphone_locations_array():
    """ Helper function designed to create microphone locations array. """

    # Microphone x,y,z locations
    x_locations = [-0.102235, -0.052197, -0.027304]
    y_locations = [-0.109982]
    z_locations = [0.056388, 0.001524, -0.053340, -0.108204]

    # Create the microphone array
    microphone_locations = [[x, y, z] for x in x_locations for y in y_locations for z in z_locations]

    return microphone_locations


def split_and_conquer(radius, the_centroid, arr, num_sources):
    """ Helper function used when looking for multiple sources. Breaks up the cartesian array into smaller bits
        in order to help multiply the radius and recenter.
        Keyword arguments:
            radius -- set of points we are using for our radius
            the_centroid -- the specific centroid associated with each coordinate
            arr -- the cartesian array before the multiplication of the radius
            num_sources -- number of sources we are looking for
        """

    # Check if the cartesian array is a numpy array
    if isinstance(arr, np.ndarray):

        # Split up the array into the separate parts based on how many sources there are
        array_split = np.vsplit(arr.T, num_sources)

        # Multiply each respective part by the radius and recenter it with the centroid
        for i in range(num_sources):
            array_split[i] = radius * array_split[i] + np.array(the_centroid)[np.newaxis, :]

    return np.vstack((array_split))


def use_kd_tree(s1_bool, centerlist, total_array):
    """ Optional: Use the KD Tree Structure to find S1 and S2 sources.
        Keyword:
            s1_bool -- boolean to determine whether to track for S1 or S2 sound source
            centerlist -- center of the room
            total_array -- the array of the possible sources.
        Runtime Complexity:
            Best Case: O(log(n))
            Worst Case: O(n)
    """

    # Put the whole list into a tree data data structure
    tree = spatial.KDTree(total_array)

    if s1_bool:
        # Find the points closest to where S1 sound is
        s1_indices = tree.query_ball_point([-0.0639405, -0.01994509, -0.02030148], 2.5e-2)
        potential_sources = np.array([total_array[s1_indices][j] for j in range(len(s1_indices))])

        # Reconvert all the potential source points
        source = np.add(centerlist, potential_sources)  # Width, Depth, Length

        # Recenter the S1 source
        s_source = np.add(centerlist, np.array([-0.0639405, -0.01994509, -0.02030148]))

        # return the potential S1 source and the S1 source
        return source, s_source

    # Find the point closest to where S2 sound is
    s2_indices = tree.query_ball_point([-0.09080822, -0.03022343, 0.02206185], 2.5e-2)
    potential_sources = np.array([total_array[s2_indices][j] for j in range(len(s2_indices))])

    # Reconvert all the potential source points
    source = np.add(centerlist, potential_sources)  # Width, Depth, Length

    # Recenter the S2 Source
    s_source = np.add(centerlist, np.array([-0.09080822, -0.03022343, 0.02206185]))

    # return the potential S2 source and the S2 source
    return source, s_source
