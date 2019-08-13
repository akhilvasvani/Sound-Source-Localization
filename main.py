#!/usr/bin/env python
# coding: utf-8

# In[1]:


# Packages to Import
from threading import Thread

import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve
import IPython
import pyroomacoustics as pra
import csv
from itertools import combinations
import scipy.io as sio
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

import sys
sys.path.append('misc')

from utils import ThreadWithReturnValue, centroid, create_microphone_locations_array, split_and_conquer


def get_data(name_of_source):
    
    """ Returns the data depending on the cycle number related and the specific sound source.
    
        Keyword arguments:
        
            name_of_source -- specifies each sound cycle
            
    """
    # Create a dictionary with all cycles: Regular S1 and S1 (top) Recovered S1 and S2 (bottom)
    source_name_dict = {f'S{x}_Cycle{y}': [f'S{x}/S{x}_Cycle{y}', f'S{x}'] for x in range(1, 3) for y in range(24)}
    # source_name_dict = {f'S{x}_Cycle{y}': [f'Recovered_S{x}/S{x}_Cycle{y}',
    #                                        f'S{x}'] for x in range(1, 3) for y in range(24)}
    
    # Match the correct data with the name
    for key in source_name_dict.keys():
        if name_of_source == key:
            data = sio.loadmat(source_name_dict[key][0])
            sound_data = data[source_name_dict[key][1]]
    
    # Return the sound data
    return sound_data


def mic_run(data, *args):
    
    """ Returns each of the n microphone locations and the signals list corresponding to the specific microphone.
        Note: The microphone locations are under a new coordinate system in relation to the center of the box
              (whose center = [(0.34925/2),(0.219964/2),(0.2413/2)] is the origin)
    
        Keyword arguments:
        
            data -- the signal associated with each microphone
            args -- list of the microphones 
    """
    
    # Empty Lists
    signal_list = []
    mic_location = []
    
    # Get the microphone locations array
    microphone_locations = create_microphone_locations_array()
    
    # List of Microphone array and data
    microphone_locations_and_data = list(zip(microphone_locations, (row for row in data)))
    
    # Dictionary of the microphone locations and their respective signals
    # Note: order is #mic number (from 1 -12), followed by location of channel (to get actual signal)
    microphones_locations_dict = {'mic'+str(j+1): 
                                  microphone_locations_and_data[j] for j in range(len(microphone_locations_and_data))}
    
    # Look for a match between the dictionary of microphone locations and the microphone in the list
    for arg in args:
        for key in microphones_locations_dict.keys():
            if arg == key:
                # Record the location
                mic_location.append(microphones_locations_dict[key][0])
                
                # Record the signal
                signal_list.append(microphones_locations_dict[key][1])
    
    # Return the whole signal list as well all the specific microphone locations
    return signal_list, mic_location


def difference_of_arrivals(speed_of_sound, signal_list, algorithm_name, num_sources, *mic_location):

    """ Returns an azimuth and co-latitude for each pair of microphones. 

        Keyword arguments:

            speed_of_sound -- specific speed of sound
            signal_list -- the microphone signals
            algorithm_name -- specific distance of arrival (DOA) method
            num_sources -- number of sources to find
            mic_location -- location of each microphone
    """
    
    # Constants 
    fs = 16000  # sampling frequency
    nfft = 256  # FFT size
    
    # Add n-microphone array in [x,y,z] order
    m = np.vstack(list(zip(*mic_location)))
    
    # Create an array of a short fourier transformed frequency signal
    x = np.array([pra.stft(signal, nfft, nfft//2, transform=np.fft.rfft).T for signal in signal_list])
    
    # Frequency Range
    freq_range = [0, 250]
    
    # Construct the new DOA object
    doa = pra.doa.algorithms[algorithm_name](L=m, fs=fs, nfft=nfft, c=speed_of_sound, num_src=num_sources, max_four=4,
                                             dim=3, azimuth=np.linspace(-180., 180., 360)*np.pi/180,
                                             colatitude=np.linspace(-90., 90., 180)*np.pi/180)
    
    # Locate the sources
    doa.locate_sources(x, freq_range=freq_range)
    
    # Return all in radians
    return doa.azimuth_recon, doa.colatitude_recon


def main(sound_speed, algo_name, sound_data, combinations_number, s1_bool, source_name, num_sources=2):
    
    """ Returns list of points that are either close to the point or the exact point itself.
    
        Keyword arguments:
        
            sound_speed -- specific speed of sound
            algo_name -- specific distance of arrival (DOA) method to call
            sound_data -- specific data to perform the localizing
            combinations_number -- number of microphone to use
            s1_bool -- flag to indicate whether to find S1 or S2 sound source
            source_name -- indicates S1 or S2 and what specific cycle
            num_source -- number of sources to find. Default is 1
    """
    
    # Optimization:
    if s1_bool:
        # List of specific microphones to quickly find S1 (where M and T are located)
        mics = ['mic'+str(i) for i in [2, 3, 6, 7, 10, 11]]
        
    else:
        # List of specific microphones to quickly find S2 (where P and A are located)
        mics = ['mic'+str(i) for i in [1, 2, 5, 6, 9, 10]]
  
    # Creates a list of N microphone-combinations
    mic_list = list(combinations(mics, combinations_number))
    
    # number of mic pair splits to run 
    splits = len(mic_list)//5
    
    # Split up the mic list into chunks of the same size
    mic_split_list = [mic_list[i*splits:(i+1)*splits] for i in range((len(mic_list)+splits-1)//splits)]
    
    # Store the final output
    outputs_list = []

    # Constants: Tolerance and Radius
    tol = 3e-3
    r = np.arange(0, 0.5, tol)[:, np.newaxis]

    # Go through all the chunks in the multi-thread
    for j in range(splits):
              
        # Pick the signal array and the associated pair of n microphone combinations
        # Note: Multi-threaded the mic_run function for faster use
        twrv1 = ThreadWithReturnValue(target=mic_run, args=(sound_data, *mic_split_list[0][j]))
        twrv2 = ThreadWithReturnValue(target=mic_run, args=(sound_data, *mic_split_list[1][j]))
        twrv3 = ThreadWithReturnValue(target=mic_run, args=(sound_data, *mic_split_list[2][j]))
        twrv4 = ThreadWithReturnValue(target=mic_run, args=(sound_data, *mic_split_list[3][j]))
        twrv5 = ThreadWithReturnValue(target=mic_run, args=(sound_data, *mic_split_list[4][j]))
    
        # Start the multi-thread
        twrv1.start()
        twrv2.start()
        twrv3.start()
        twrv4.start()
        twrv5.start()
        
        # Return signal and microphone locations
        [signal_1, mic_locations_1] = twrv1.join()
        [signal_2, mic_locations_2] = twrv2.join()
        [signal_3, mic_locations_3] = twrv3.join()
        [signal_4, mic_locations_4] = twrv4.join()
        [signal_5, mic_locations_5] = twrv5.join()
   
        # Find the centroids of the pairs of n microphone combinations
        twrv7 = ThreadWithReturnValue(target=centroid, args=(mic_locations_1))
        twrv8 = ThreadWithReturnValue(target=centroid, args=(mic_locations_2))
        twrv9 = ThreadWithReturnValue(target=centroid, args=(mic_locations_3))
        twrv10 = ThreadWithReturnValue(target=centroid, args=(mic_locations_4))
        twrv11 = ThreadWithReturnValue(target=centroid, args=(mic_locations_5))

        twrv7.start()
        twrv8.start()
        twrv9.start()
        twrv10.start()
        twrv11.start()
        
        # Return the centroids
        centroid_1 = twrv7.join()
        centroid_2 = twrv8.join()
        centroid_3 = twrv9.join()
        centroid_4 = twrv10.join()
        centroid_5 = twrv11.join()
        
        # Perform the distance of arrival methods to find closest azimuth and co-latitude angles
        twrv13 = ThreadWithReturnValue(target=difference_of_arrivals, 
                                       args=(sound_speed, signal_1, algo_name, num_sources, *mic_locations_1))
        twrv14 = ThreadWithReturnValue(target=difference_of_arrivals, 
                                       args=(sound_speed, signal_2, algo_name, num_sources, *mic_locations_2))
        twrv15 = ThreadWithReturnValue(target=difference_of_arrivals, 
                                       args=(sound_speed, signal_3, algo_name, num_sources, *mic_locations_3))
        twrv16 = ThreadWithReturnValue(target=difference_of_arrivals, 
                                       args=(sound_speed, signal_4, algo_name, num_sources, *mic_locations_4))
        twrv17 = ThreadWithReturnValue(target=difference_of_arrivals, 
                                       args=(sound_speed, signal_5, algo_name, num_sources, *mic_locations_5))
                
        twrv13.start()
        twrv14.start()
        twrv15.start()
        twrv16.start()
        twrv17.start()

        # Desired angles 
        azimuth_recon_1, colatitude_recon_1 = twrv13.join()
        azimuth_recon_2, colatitude_recon_2 = twrv14.join()
        azimuth_recon_3, colatitude_recon_3 = twrv15.join()
        azimuth_recon_4, colatitude_recon_4 = twrv16.join()
        azimuth_recon_5, colatitude_recon_5 = twrv17.join()
               
        # Desired cartesian coordinates
        cartesian_1 = np.array([np.cos(azimuth_recon_1)*np.sin(colatitude_recon_1),
                                np.sin(azimuth_recon_1)*np.sin(colatitude_recon_1), np.cos(colatitude_recon_1)])
        cartesian_2 = np.array([np.cos(azimuth_recon_2)*np.sin(colatitude_recon_2),
                                np.sin(azimuth_recon_2)*np.sin(colatitude_recon_2), np.cos(colatitude_recon_2)])
        cartesian_3 = np.array([np.cos(azimuth_recon_3)*np.sin(colatitude_recon_3),
                                np.sin(azimuth_recon_3)*np.sin(colatitude_recon_3), np.cos(colatitude_recon_3)])
        cartesian_4 = np.array([np.cos(azimuth_recon_4)*np.sin(colatitude_recon_4),
                                np.sin(azimuth_recon_4)*np.sin(colatitude_recon_4), np.cos(colatitude_recon_4)])
        cartesian_5 = np.array([np.cos(azimuth_recon_5)*np.sin(colatitude_recon_5),
                                np.sin(azimuth_recon_5)*np.sin(colatitude_recon_5), np.cos(colatitude_recon_5)])
        
        if num_sources > 1:
            # Get the estimates 
            estimate_1 = split_and_conquer(r, centroid_1, cartesian_1, num_sources)
            estimate_2 = split_and_conquer(r, centroid_2, cartesian_2, num_sources)
            estimate_3 = split_and_conquer(r, centroid_3, cartesian_3, num_sources)
            estimate_4 = split_and_conquer(r, centroid_4, cartesian_4, num_sources)
            estimate_5 = split_and_conquer(r, centroid_5, cartesian_5, num_sources)
        else:
            # Re-center them via adding the centroid        
            estimate_1 = r*cartesian_1.T + np.array(centroid_1)[np.newaxis, :]
            estimate_2 = r*cartesian_2.T + np.array(centroid_2)[np.newaxis, :]
            estimate_3 = r*cartesian_3.T + np.array(centroid_3)[np.newaxis, :]
            estimate_4 = r*cartesian_4.T + np.array(centroid_4)[np.newaxis, :]
            estimate_5 = r*cartesian_5.T + np.array(centroid_5)[np.newaxis, :]
                
        # Add to an output list
        outputs_list.extend((estimate_1, estimate_2, estimate_3, estimate_4, estimate_5))
    
    # Make a numpy array of them 
    all_estimates = np.array(outputs_list)
        
    # Reshape them to (_, 3) which is proper format for the tree
    total_array = np.reshape(all_estimates, (all_estimates.shape[0]*all_estimates.shape[1], all_estimates.shape[2]))
    
    # Re-center the points, add the x,y,z location of the center of the room to the obtained point
    room_dim = np.array([0.34925, 0.219964, 0.2413])  # [13.75,8.66,9.5] # Width, Depth, Length
    centerlist = room_dim/2
    
    # Reconvert all the potential source points
    potential_sources = np.add(centerlist, total_array)  # Width, Depth, Length
    
    if s1_bool:
        # Set the boundaries on where we think S1 lies
        source = potential_sources[(potential_sources[:, 0] >= 0.07) & (potential_sources[:, 0] < 0.15)
                                   & (potential_sources[:, 1] > 8e-2) & (potential_sources[:, 1] <= 0.10)  # room_dim[1]
                                   & (potential_sources[:, 2] >= 0.06) & (potential_sources[:, 2] < 0.12)]

        # Recenter the S1 source
        s_source = np.add(centerlist, np.array([-0.0639405, -0.01994509, -0.02030148]))
        
    else:
        # Set the boundaries on where we think S2 lies
        source = potential_sources[(potential_sources[:, 0] >= 0.07) & (potential_sources[:, 0] < 0.15) &
                                   (potential_sources[:, 1] > 0.065) & (potential_sources[:, 1] <= 0.095) &
                                   (potential_sources[:, 2] >= 0.12) & (potential_sources[:, 2] < 0.18)]
        
        # Recenter the S2 Source
        s_source = np.add(centerlist, np.array([-0.09080822, -0.03022343,  0.02206185]))
    
    # Are there are more than 1 sources?
    if source.size > 0:                      

        microphone_locations = create_microphone_locations_array()

        # Add the locations
        microphone_source_locations = np.add(centerlist, np.array(microphone_locations))

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
        ax.scatter(microphone_source_locations[:, 0], microphone_source_locations[:, 1],
                   microphone_source_locations[:, 2], label='Microphones 1-12')

        # Plot the S1 or S2 location
        ax.scatter(s_source[0], s_source[1], s_source[2], 'b', label='Predicted Source Location')

        # Plot all the possible S1 or S2 sources
        ax.scatter(source[:, 0], source[:, 1], source[:, 2], 'y', label='Sources')

        ax.legend()

        # Write to a csv file to save the data
        filename = 'mic_'+str(combinations_number)+'_'+str(source_name)+'_sound_source_localization_c'+str(sound_speed)\
                   + '_'+str(algo_name)+'_CLUSTER_multithread_DEBUG_'+str(num_sources)

        # Save the file
        plt.savefig(filename+'.png')
        plt.close()

        with open(filename+'.csv', mode='w') as sound_source_file:
            writer = csv.writer(sound_source_file, delimiter=',')

            # First Row of Data, names of the columns
            writer.writerow(['Width', 'Depth', 'Length'])

            # Write the rest of the results
            # Note they have not been converted back into correct x,y,z coordinates
            writer.writerows(source) 

        sound_source_file.close()
        
    else:
        print("Nothing to convert. Points do not exist inside the boundaries of the environment for "+str(source_name) +
              "_"+str(algo_name))


if __name__ == '__main__':
    """ Performs the main script using all the sound data, specific speed of sound, 
        the names of the distance of arrival methods, and number of combinations of microphone pairs. """
    
    # Speed of sound
    sound_speed = 30
    
    # Number of Pairs of Microphone Combinations
    combinations_number = 3
    
    # Data: Number of Cycles for each Sound Source
    # DEBUG:
    cycles = ['Cycle'+str(i) for i in range(2)]  # for i in range(24)
    soundSources = ['S'+str(i) for i in range(1, 3)]
    sound_list = [soundSource+'_'+cycle for soundSource in soundSources for cycle in cycles]
    
    # When to find S1 and S2
    s1_bool = True

    # List of all the DOA methods
    algorithm_names = ['SRP', 'MUSIC', 'TOPS']
    
    for source_name in sound_list:
        for algorithm in algorithm_names:

            # Check if name is S2
            if source_name in ['S'+str(i)+'_'+'Cycle'+str(j) for i in range(2, 3) for j in range(24)]:
                s1_bool = False

            # Get the Sound Data
            sound_data = get_data(source_name)

            # Run main function with each DOA method
            main(sound_speed, algorithm, sound_data, combinations_number, s1_bool, source_name)

    print("done")
