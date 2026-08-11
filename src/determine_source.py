# !/usr/bin/env python
"""This script reports and visualizes the single triangulated sound-source
location estimate produced by SoundSourceLocation, including a quantitative
error metric (in meters) against a known/simulated ground-truth source
location when one is supplied.

This replaces the original DetermineSourceLocation, whose `sprint()` method
only called `plot_everything()` -- which filtered a raw, un-reduced cloud of
~500-per-ray sampled points down to the room's bounding box and plotted/saved
it, with no clustering, centroid, or intersection step. `use_kd_tree()`
built a KD-tree and then immediately `return None`ed (dead code); both are
removed below in favor of the actual ray-triangulation output from
`src/triangulation.py` (via `SoundSourceLocation`).
"""

import csv
import numpy as np
import matplotlib.pyplot as plt

from mpl_toolkits.mplot3d import Axes3D

from src.sound_source_localization import SoundSourceLocation


class DetermineSourceLocation(SoundSourceLocation):
    """DetermineSourceLocation reports and visualizes the single
       triangulated source-location estimate for one DOA method / signal.

       Attributes:
           source_name: (string) file name
           estimate: (numpy array, shape (3,)) the single triangulated
                     source-location estimate, in absolute room coordinates
           diagnostics: (dict) per-ray residuals/weights from the
                        triangulation step (see SoundSourceLocation)
           true_source: (numpy array, shape (3,), optional) known/simulated
                        ground-truth source location, in absolute room
                        coordinates, used to compute `error_m`
           _microphone_locations: (list) microphone locations (room-centered)
           room_dim: (list) room dimensions
           center_of_room: (numpy array) center of room
           filename: (string) file name to save output file and picture as
    """

    def __init__(self, algo_name, source_name, estimate, diagnostics,
                *args, **kwargs):
        """Initializes DetermineSourceLocation with algo_name, source_name,
           the triangulated estimate, and its diagnostics."""

        SoundSourceLocation.__init__(self, algo_name)
        self.source_name = source_name
        self.estimate = np.asarray(estimate, dtype=float)
        self.diagnostics = diagnostics or {}
        self._microphone_locations = args

        true_source = kwargs.get('true_source')
        self.true_source = np.asarray(true_source, dtype=float) if true_source is not None else None

        *self.room_dim, = iter(kwargs.get('room_dim'))
        self.center_of_room = np.array(self.room_dim) / 2

        self.error_m = (float(np.linalg.norm(self.estimate - self.true_source))
                        if self.true_source is not None else None)

        self.filename = "_".join(['mic', str(self.mic_combinations_number),
                                  str(self.source_name),
                             "".join(['sound_source_localization_c',
                                      str(self.sound_speed)]),
                                  str(self.algo_name),
                             'triangulated', str(self.num_sources)])

    def _set_microphone_locations(self):
        return list(self._microphone_locations)

    def is_inside_room(self):
        """Returns True if the estimate falls within the room's bounds."""
        return bool(np.all(self.estimate >= 0) and
                   np.all(self.estimate <= np.array(self.room_dim)))

    def report(self):
        """Returns a dict summarizing the localization result: the
           estimate, whether it's inside the room, ray-fit diagnostics, and
           (if a ground truth was supplied) the error in meters.
        """
        summary = {
            'algorithm': self.algo_name,
            'estimate_m': self.estimate.tolist(),
            'inside_room': self.is_inside_room(),
            'n_rays': self.diagnostics.get('n_rays'),
            'mean_ray_residual_m': self.diagnostics.get('mean_residual_m'),
            'median_ray_residual_m': self.diagnostics.get('median_residual_m'),
        }
        if self.true_source is not None:
            summary['true_source_m'] = self.true_source.tolist()
            summary['error_m'] = self.error_m
        return summary

    def plot(self, save_plot=False, write_to_file=False, show=False):
        """Plots the microphones, the triangulated estimate, and (if
           available) the true source location on a 3-D plot.

           Args:
               save_plot: (boolean) saves plot to a png. Default: False.
               write_to_file: (boolean) saves the estimate (and true
                              source/error, if available) to a csv file.
                              Default: False.
               show: (boolean) calls plt.show(). Default: False (so this
                     is safe to call in headless/CI environments).
        """
        microphone_locations = self._set_microphone_locations()
        microphone_source_locations = np.add(self.center_of_room,
                                             np.array(microphone_locations))

        fig = plt.figure()
        axes = fig.add_subplot(111, projection='3d')
        axes.set_xlabel('Width (X axis)')
        axes.set_ylabel('Depth (Y axis)')
        axes.set_zlabel('Length (Z axis)')
        axes.set_title(f"Triangulated Source Estimate ({self.algo_name})")
        axes.set_xlim(0, self.room_dim[0])
        axes.set_ylim(0, self.room_dim[1])
        axes.set_zlim(0, self.room_dim[2])

        axes.scatter(microphone_source_locations[:, 0],
                     microphone_source_locations[:, 1],
                     microphone_source_locations[:, 2],
                     label='Microphones 1-{:d}'.format(len(microphone_locations)))

        axes.scatter(*self.estimate, color='y', marker='x', s=100,
                     label='Triangulated Estimate')

        if self.true_source is not None:
            axes.scatter(*self.true_source, color='r', marker='*', s=100,
                         label='True Source Location')

        axes.legend()

        if save_plot:
            fig.savefig(".".join([self.filename, 'png']))
        if show:
            plt.show()
        plt.close(fig)

        if write_to_file:
            self.write_to_csv()

    def write_to_csv(self):
        """Writes the triangulated estimate (and true source/error, if
           available) to a csv file."""
        with open(".".join([self.filename, 'csv']), mode='w') as sound_source_file:
            writer = csv.writer(sound_source_file, delimiter=',')
            if self.true_source is not None:
                writer.writerow(['Width', 'Depth', 'Length', 'Type'])
                writer.writerow(list(self.estimate) + ['estimate'])
                writer.writerow(list(self.true_source) + ['true_source'])
                writer.writerow([self.error_m, '', '', 'error_m'])
            else:
                writer.writerow(['Width', 'Depth', 'Length'])
                writer.writerow(list(self.estimate))

        print('Done')

    def sprint(self, save_plot=False, write_to_file=True, show=False):
        """Runs the full report: prints a summary, optionally plots/saves,
           and returns the summary dict from `report()`.
        """
        summary = self.report()
        print(f"[{self.algo_name}] estimate (m): {summary['estimate_m']}, "
              f"inside_room={summary['inside_room']}, "
              f"mean_ray_residual_m={summary['mean_ray_residual_m']:.4f}")
        if self.true_source is not None:
            print(f"[{self.algo_name}] true source (m): {summary['true_source_m']}, "
                  f"error_m={summary['error_m']:.4f}")

        self.plot(save_plot=save_plot, write_to_file=write_to_file, show=show)
        return summary
