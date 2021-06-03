import numpy as np
from scripts.utils import ThreadWithReturnValue

# def read_csv(filename):
#     import numpy as np
#     return np.genfromtxt(filename, delimiter=',')


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
