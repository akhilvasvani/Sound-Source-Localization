import numpy as np
import threading


def read_csv(filename):
    return np.genfromtxt(filename, delimiter=',')


class ThreadWithReturnValue(threading.Thread):
    """Created a Thread subclass. It is a workable do around,
       but it accesses "private" data structures that are specific
       to Thread implementation.
    """

    def __init__(self, *args, **kwargs):
        """Initializes the thread object."""
        super().__init__(*args, **kwargs)
        self._return = None

    def run(self):
        """Runs the function if specified for the thread."""
        target = getattr(self, '_target')
        if target is not None:
            self._return = target(*getattr(self, '_args'), **getattr(self,
                                                                     '_kwargs'))

    def join(self, *args, **kwargs):
        """Returns the value of target function running in the thread."""
        super().join(*args, **kwargs)
        return self._return


def run_multithreading(self, splits, number_of_splits, all_sound_data, mic_split_list):
    """Run multi-threading for all microphone combinations."""
    threads = []

    # Go through all the chunks in the multi-thread
    for j in range(splits):
        for i in range(number_of_splits):
            thread = ThreadWithReturnValue(target=self.get_estimates,
                                           args=(all_sound_data,
                                                 *mic_split_list[i][j]))
            threads.append(thread)
            thread.start()

    all_estimates = np.array([thread.join() for thread in threads])
    return all_estimates
