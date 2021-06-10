"""This script will find the most likely location of the sound source."""

from scripts.sound_source_localization import SoundSourceLocation
from scipy import spatial
# from mpl_toolkits.mplot3d import Axes3D

import numpy as np
import matplotlib.pyplot as plt
import csv


class DetermineSourceLocation(SoundSourceLocation):

    def __init__(self, algo_name, source_name, all_source_estimates,
                 room_dimensions=[0.34925, 0.219964, 0.2413]):
        super().__init__(self, algo_name)
        self.source_name = source_name
        self.all_source_estimates = all_source_estimates

        self.center_of_room = np.array(room_dimensions)/2

        self.filename = "_".join(['mic', str(self.combinations_number), str(self.source_name),
                             "".join(['sound_source_localization_c',
                                      str(self.sound_speed)]), str(self.algo_name),
                             'CLUSTER_multithread', str(self.num_sources)])

    def room_filter_out(self):
        room_dim = self.center_of_room * 2
        filter_list = self.all_source_estimates[(self.all_source_estimates[:, 0] >= 0)
                                                & (self.all_source_estimates[:, 0] <= room_dim[0])
                                                & (self.all_source_estimates[:, 1] >= 0)
                                                & (self.all_source_estimates[:, 1] <= room_dim[1])
                                                & (self.all_source_estimates[:, 2] >= 0)
                                                & (self.all_source_estimates[:, 2] <= room_dim[2])]
        return filter_list

    def full_filter(self):

        # TODO: Test out S1_Bool?
        if self.s1_bool:
            # Set the boundaries on where we think S1 lies
            # Second line is room_dim[1]
            source = self.all_source_estimates[(self.all_source_estimates[:, 0] >= 0.07)
                                               & (self.all_source_estimates[:, 0] < 0.15)
                                               & (self.all_source_estimates[:, 1] > 8e-2)
                                               & (self.all_source_estimates[:, 1] <= 0.10)
                                               & (self.all_source_estimates[:, 2] >= 0.06)
                                               & (self.all_source_estimates[:, 2] < 0.12)]

            # Recenter the S1 source
            s_source = np.add(self.center_of_room, np.array([-0.0639405,
                                                             -0.01994509,
                                                             -0.02030148]))
            return source, s_source

        # Set the boundaries on where we think S2 lies
        source = self.all_source_estimates[(self.all_source_estimates[:, 0] >= 0.07)
                                           & (self.all_source_estimates[:, 0] < 0.15)
                                           & (self.all_source_estimates[:, 1] > 0.065)
                                           & (self.all_source_estimates[:, 1] <= 0.095)
                                           & (self.all_source_estimates[:, 2] >= 0.12)
                                           & (self.all_source_estimates[:, 2] < 0.18)]

        # Recenter the S2 Source
        s_source = np.add(self.center_of_room, np.array([-0.09080822,
                                                         -0.03022343,
                                                         0.02206185]))

        return source, s_source

    def use_kd_tree(self):
        """ Optional: Use the KD Tree Structure to find S1 and S2 sources.

            Runtime Complexity:
                Best Case: O(log(n))
                Worst Case: O(n)
        """

        # Put the whole list into a tree data data structure
        tree = spatial.KDTree(self.all_source_estimates)

        if self.s1_bool:
            # Find the points closest to where S1 sound is
            s1_indices = tree.query_ball_point(np.add(self.center_of_room,
                                                      np.array([-0.0639405, -0.01994509, -0.02030148])), 2.5e-2)
            source = np.array([self.all_source_estimates[s1_indices][j] for j in range(len(s1_indices))])

            # Recenter the S1 source
            s_source = np.add(self.center_of_room, np.array([-0.0639405, -0.01994509, -0.02030148]))

            # return the potential S1 source and the S1 source
            return source, s_source

        # Find the point closest to where S2 sound is
        s2_indices = tree.query_ball_point(np.add(self.center_of_room,
                                                  np.array([-0.09080822, -0.03022343, 0.02206185])), 2.5e-2)
        source = np.array([self.all_source_estimates[s2_indices][j] for j in range(len(s2_indices))])

        # Recenter the S2 Source
        s_source = np.add(self.center_of_room, np.array([-0.09080822, -0.03022343, 0.02206185]))

        # return the potential S2 source and the S2 source
        return source, s_source

    def plot(self, source, s_source):
        # Are there are more than 1 sources?
        if source.size > 0:

            microphone_locations = self.create_microphone_locations_list()

            # Add the locations
            microphone_source_locations = np.add(self.center_of_room,
                                                 np.array(microphone_locations))

            # Create a Figure, label the axis, Title the plot, and set the limits
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
            ax.set_xlabel('Width (X axis)')
            ax.set_ylabel('Depth (Z axis)')
            ax.set_zlabel('Length (Y axis)')
            ax.set_title("All the Clusters")
            ax.set_xlim(0, 0.35)
            ax.set_ylim(0, 0.25)
            ax.set_zlim(0, 0.22)  # for 3-d

            # Plot the microphones
            ax.scatter(microphone_source_locations[:, 0],
                       microphone_source_locations[:, 1],
                       microphone_source_locations[:, 2],
                       label='Microphones 1-12')

            # Plot the S1 or S2 location
            ax.scatter(s_source[0], s_source[1], s_source[2], 'b',
                       label='Source Location')

            # Plot all the possible S1 or S2 sources
            ax.scatter(source[:, 0], source[:, 1], source[:, 2], 'y',
                       label='Potential Source Location')

            ax.legend()

            # Save the file
            fig.savefig(".".join([self.filename, 'png']))
            plt.close(fig)

            # self.write_to_csv(source)

        else:
            print(f"Nothing to convert. Points do not exist inside the "
                  f"boundaries of the environment for {str(self.source_name)}_{str(self.algo_name)}")

    def write_to_csv(self, source):
        """Write to a csv file to save the data"""
        with open(".".join([self.filename, 'csv']), mode='w') as sound_source_file:
            writer = csv.writer(sound_source_file, delimiter=',')

            # First Row of Data, names of the columns
            writer.writerow(['Width', 'Depth', 'Length'])

            # Write the rest of the results
            writer.writerows(source)

        print('Done')


# ts1 = TrueSourceLocation('S1_Source')
# print(ts1)
# ts1.plot(np.array([4, 5]), np.array([9, 0]))
