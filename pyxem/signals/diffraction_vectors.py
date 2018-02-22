# -*- coding: utf-8 -*-
# Copyright 2017-2018 The pyXem developers
#
# This file is part of pyXem.
#
# pyXem is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyXem is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyXem.  If not, see <http://www.gnu.org/licenses/>.

from hyperspy.api import roi
from hyperspy.signals import BaseSignal, Signal1D, Signal2D

from scipy.spatial import distance_matrix
from sklearn.cluster import DBSCAN
from tqdm import tqdm
import matplotlib.pyplot as plt

from pyxem.utils.expt_utils import *
from pyxem.utils.vector_utils import *
from pyxem.signals.vdf_image import VDFImage

"""
Signal class for diffraction vectors.
"""


class DiffractionVectors(BaseSignal):
    _signal_type = "diffraction_vectors"

    def __init__(self, *args, **kwargs):
        BaseSignal.__init__(self, *args, **kwargs)

    def plot_diffraction_vectors(self, xlim, ylim):
        """Plot the diffraction vectors.
        """
        #Find the unique gvectors to plot.
        unique_vectors = self.get_unique_vectors()
        #Plot the gvector positions
        plt.plot(unique_vectors.T[1], unique_vectors.T[0], 'ro')
        plt.xlim(-xlim, xlim)
        plt.ylim(-ylim, ylim)
        plt.axes().set_aspect('equal')
        plt.show()

    def get_magnitudes(self, *args, **kwargs):
        """Calculate the magnitude of diffraction vectors.

        Returns
        -------
        magnitudes : BaseSignal
            A signal with navigation dimensions as the original diffraction
            vectors containging an array of gvector magnitudes at each
            navigation position.

        """
        if len(self.axes_manager.signal_axes)==0:
            magnitudes = self.map(calculate_norms_ragged,
                                  inplace=False,
                                  *args, **kwargs)
        else:
            magnitudes = self.map(calculate_norms,
                                  inplace=False,
                                  *args, **kwargs)
        return magnitudes

    def get_magnitude_histogram(self, bins):
        """Obtain a histogram of gvector magnitudes.

        Parameters
        ----------
        bins : numpy array
            The bins to be used to generate the histogram.

        Returns
        -------
        ghist : Signal1D
            Histogram of gvector magnitudes.

        """
        gmags = self.get_magnitudes()

        glist=[]
        for i in gmags._iterate_signal():
            for j in np.arange(len(i[0])):
                glist.append(i[0][j])
        gs = np.asarray(glist)
        gsig = Signal1D(gs)
        ghis = gsig.get_histogram(bins=bins)
        ghis.axes_manager.signal_axes[0].name = 'g-vector magnitude'
        ghis.axes_manager.signal_axes[0].units = '$A^{-1}$'
        return ghis

    def get_unique_vectors(self,
                           distance_threshold=0):
        """Obtain the unique diffraction vectors.

        Parameters
        ----------
        distance_threshold : float
            The minimum distance between diffraction vectors for them to be
            considered unique diffraction vectors.

        Returns
        -------
        unique_vectors : DiffractionVectors
            A DiffractionVectors object containing only the unique diffraction
            vectors in the original object.
        """
        if (self.axes_manager.navigation_dimension == 2):
            gvlist = np.array([self.data[0,0][0]])
        else:
            gvlist = np.array([self.data[0][0]])

        for i in self._iterate_signal():
            vlist = i[0]
            distances = distance_matrix(gvlist, vlist)
            new_indices = get_indices_from_distance_matrix(distances,
                                                           distance_threshold)
            gvlist_new = vlist[new_indices]
            if gvlist_new.any():
                gvlist=np.concatenate((gvlist, gvlist_new),axis=0)
        #An internal check, just to be sure.
        delete_indices = []
        l = np.shape(gvlist)[0]
        distances = distance_matrix(gvlist,gvlist)
        for i in range(np.shape(distances)[1]):
            if (np.sum(distances[:,i] <= distance_threshold) > 1):
                delete_indices = np.append(delete_indices, i)
        gvecs = np.delete(gvlist, delete_indices,axis = 0)
        #Manipulate into DiffractionVectors class
        unique_vectors = pxm.DiffractionVectors(gvecs)
        unique_vectors.axes_manager.set_signal_dimension(1)
        return unique_vectors

    def get_vector_clusters(self, eps=0.01, min_samples=10):
        """Perform DBSCAN clustering on the diffraction vectors.

        Parameters
        ----------
        eps : float
            The maximum distance between two samples for them to be considered
            as in the same neighborhood.

        min_samples : float
            The number of samples (or total weight) in a neighborhood for a
            point to be considered as a core point. This includes the point itself.

        Returns
        -------
        db : clustering
            Results of the DBSCAN clustering.

        See also
        --------
        sklearn.cluster.DBSCAN

        """
        if (self.axes_manager.navigation_dimension == 2):
            gvs = np.array([self.data[0,0][0]])
        else:
            gvs = np.array([self.data[0][0]])

        db = DBSCAN(eps=eps, min_samples=min_samples).fit(gvs)

        return db

    def get_vdf_images(self,
                       electron_diffraction,
                       radius,
                       unique_vectors=None):
        """Obtain the intensity scattered to each diffraction vector at each
        navigation position in an ElectronDiffraction Signal by summation in a
        circular window of specified radius.

        Parameters
        ----------
        unique_vectors : list (optional)
            Unique list of diffracting vectors if pre-calculated. If None the
            unique vectors in self are determined and used.

        electron_diffraction : ElectronDiffraction
            ElectronDiffraction signal from which to extract the reflection
            intensities.

        radius : float
            Radius of the integration window in reciprocal angstroms.

        Returns
        -------
        vdfs : Signal2D
            Signal containing virtual dark field images for all unique vectors.
        """
        if unique_vectors is None:
            unique_vectors = self.get_unique_vectors()
        else:
            unique_vectors = unique_vectors

        vdfs = []
        for v in unique_vectors:
            disk = roi.CircleROI(cx=v[1], cy=v[0], r=radius, r_inner=0)
            vdf = disk(electron_diffraction,
                       axes=electron_diffraction.axes_manager.signal_axes)
            vdfs.append(vdf.sum((2,3)).as_signal2D((0,1)).data)
        return VDFImage(np.asarray(vdfs))

    def get_diffracting_pixels_map(self, binary=False):
        """Map of the number of vectors at each navigation position.

        Parameters
        ----------
        binary : boolean
            If True a binary image with diffracting pixels taking value == 1 is
            returned.

        Returns
        -------
        crystim : Signal2D
            2D map of diffracting pixels.
        """
        crystim = self.map(get_npeaks, inplace=False).as_signal2D((0,1))
        if binary==True:
            crystim = crystim == 1
        return crystim

    def get_gvector_indexation(self,
                               structure,
                               magnitude_threshold,
                               angular_threshold=None,
                               maximum_length=1):
        """Index diffraction vectors based on the magnitude of individual
        vectors and optionally the angles between pairs of vectors.

        Parameters
        ----------
        structure : Structure
            pymatgen structure to be used for indexation

        magnitude_threshold : Float
            Maximum deviation in diffraction vector magnitude from the
            theoretical value for an indexation to be considered possible.

        angular_threshold : float
            Maximum deviation in the measured angle between vector

        maximum_length : float
            Maximum g-vector length to included in indexation.

        Returns
        -------
        gindex : array
            Structured array containing possible indexations
            consistent with the data.

        """
        #TODO: Specify threshold as a fraction of the g-vector magnitude.
        recip_latt = structure.lattice.reciprocal_lattice_crystallographic
        recip_pts = recip_latt.get_points_in_sphere([[0, 0, 0]], [0, 0, 0], maximum_length)
        calc_peaks = np.asarray(sorted(recip_pts, key=lambda i: (i[1], -i[0][0], -i[0][1], -i[0][2])))

        arr_shape = (self.axes_manager._navigation_shape_in_array
                     if self.axes_manager.navigation_size > 0
                     else [1, ])
        gindex = np.zeros(arr_shape, dtype=object)

        for i in self.axes_manager:
            it = (i[1], i[0])
            res = []
            for j in np.arange(len(glengths[it])):
                peak_diff = (calc_peaks.T[1] - glengths[it][j]) * (calc_peaks.T[1] - glengths[it][j])
                res.append((calc_peaks[np.where(peak_diff < magnitude_threshold)],
                            peak_diff[np.where(peak_diff < magnitude_threshold)]))
            gindex[it] = res

        if angular_threshold==None:
            pass
        else:
            pass

        return gindex

    def get_zone_axis_indexation(self):
        """Determine the zone axis consistent with the majority of indexed
        diffraction vectors.

        Parameters
        ----------

        Returns
        -------

        """
        pass
