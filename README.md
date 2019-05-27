## Sound-Source-Localization-in-a-Reverberant Environment

Sound-Source-Localization-in-a-Reverberant Environment was a project I did for my master's degree at Johns Hopkins. In this project, we perform sound source localization in the human heart to detect S1 and S2 sounds. 

## Motivation

The aim of this project is to helps quickly find and detect heart murmurs or other heart-related issues in a short period of time. In order to accurately diagnosis heart murmurs, the S1 and S2 hearts sounds need to known. Once found, one can listen and classify a heart murmur by its signals collected.


## Background

# DOA

Imagine two antennas a distance d apart. The antennas both receive a radio wave from a far away source. Assuming that the front of the radio wave is a flat plane, then the angle between each antenna’s normal and the vector of the radio wave is the Direction of arrival (DOA) (θ). Now, over N snapshots, an algorithm can be implemented to estimate the value of multiple signals DOA angles.

For generally far and wide signals, a difference in wavelength exists when the  same  signal reaches different array elements. This difference leads to a phase difference between the arrival array elements (τ). Using the phase difference between the array elements of the signal one can estimate the signal azimuth as well as the signal co-latitude, which is the basic principle of DOA estimation.

# Methods

Multiple signal classification (MUSIC) is versatile because it provides asymptotically unbiased estimates of signal parameters that approach the Cramer-Rao accuracy bound. Instead of maximizing the probability---assuming that the data is normally distributed (Gaussian), MUSIC models the data as the sum of point source emissions and noise. Geometrically speaking, MUSIC minimizes the angle θ between the signal subspace and the microphone. Unlike the maximum likelihood method, which would minimize some type of weighted combination for all component distances.

SRP uses a steered-beamformer approach to search over a predefined spatial region looking for either a peak or peaks in the power of its output signal. Although computationally expensive, SRP combines the signals from multiple microphones rather than using data from each pair and their respective time-delay difference between the pair. By using the data from all microphones, this approach compensates for the short duration of each data segment used for localization in a reverberant environment.

Test of orthogonality of projected subspaces, (TOPS), is another direction-of-arrival (DOA) estimation algorithm for wideband sources. This technique estimates DOAs by measuring multifrequency orthogonal relations of the sources between the signal and the noise subspaces. Unlike other coherent wideband methods, such as CSSM and WAVES, the new method does not need to preprocess for initial values. TOPS performs best in medium signal-to-noise environment while coherent methods work well in a low signal-to-noise environment and incoherent methods work well in high signal-to-noise environment.


CSSM constructs a single signal subspace for high-resolution estimation of the angles of arrival of multiple wide-band plane waves. "The technique relies on an approximately coherent combination of the spatial signal spaces of the temporally narrow-band decomposition of the received signal vector from an array of sensors". Unlike CSSM, a new approach to wideband direction finding, called the weighted average of signal subspaces (WAVES), combines a robust near-optimal data-adaptive statistic and focuses matrices to ensure a statistically robust preprocessing of wideband data.

# Angles

We use the physics approach to thinking of ths spherical coordinate system:

	radial distance r 
	polar (colatitude) angle θ (theta)--between z axis and r 
	azimuthal angle φ (phi)--between x and y axis

## How to Use

So, in the first script, ICA, the data, in a .mat file (MATLAB file), is read in and split up into 24 cycles each labeled in a Folder S1 and S2. 

Next, in the main script, we used the distance of arrival (DOA) algorithms to calculate the azimuth and colatitude angles from the center of the microphones. Once all angles are found, we convert them into a cartesian coordiates (x,y,z) and place them in a K-Dimensional Tree structure to find the S1 and S2 sources. Those cartesian coordinates are saved into a csv file. 

Finally, last of all, all those coordinates are graphed and displayed into a png image. 

# Time to Run

SRP ~ 1 minute

~TOPS ~ 3 minutes

MUSIC ~ 5 minutes


## Requirements

Python 3.x
pyroomacoustics
SciPy
NumPy
itertools
Thread



# JADE Algorithm Reference

[JADE in Python](https://github.com/bregmanstudio/cseparate/blob/master/cjade.py)

# Thread References

[Return a value with Threads](https://stackoverflow.com/questions/6893968/how-to-get-the-return-value-from-a-thread-in-python/6894023#6894023)

[MultiThreading vs. Multiprocessing](https://stackoverflow.com/questions/3044580/multiprocessing-vs-threading-python)

[MutliThreading in General](https://www.geeksforgeeks.org/multithreading-python-set-1/)

# KD Tree References

[Fastest way to find the closest point to a given point in 3D, in Python](https://stackoverflow.com/questions/2641206/fastest-way-to-find-the-closest-point-to-a-given-point-in-3d-in-python?rq=1)

[KD TREE EXAMPLE WITH CUSTOM EUCLIDEAN DISTANCE BALL QUERY](http://code.activestate.com/recipes/578434-a-simple-kd-tree-example-with-custom-euclidean-dis/)

[Getting rid of double brackets](https://www.quora.com/How-can-I-convert-the-list-1-2-3-into-1-2-3-in-Python-Basically-I-want-the-list-to-be-flattened)

[Python/Scipy: KDTree Query Ball Point performance issue](https://stackoverflow.com/questions/43136142/python-scipy-kdtree-query-ball-point-performance-issue)

[Using k-d trees to efficiently calculate nearest neighbors in 3D vector space](https://blog.krum.io/k-d-trees/)

[scipy.spatial.KDTree](https://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.spatial.KDTree.html#scipy.spatial.KDTree) 

# Tricks

[Saving and Loading Python Dictionary with savemat results in error](https://stackoverflow.com/questions/9232751/saving-and-loading-python-dict-with-savemat-results-in-error)

[Optimal way to Append to Numpy array](https://stackoverflow.com/questions/25649788/optimal-way-to-append-to-numpy-array)

[Matrix from Python to Matlab](https://stackoverflow.com/questions/1095265/matrix-from-python-to-matlab)

[Create a Folder in Python](https://gist.github.com/keithweaver/562d3caa8650eefe7f84fa074e9ca949)

## Credits

Thank you [Pyroomacoustics](https://github.com/LCAV/pyroomacoustics) for the open-source library containing the differnt DOA methods. 
