import numpy as np
import hyperspy.utils.markers as hm


def _get_4d_points_marker_list(peaks_list, signal_axes=None, color='red',
                               size=20):
    """Get a list of 4 dimensional point markers.

    The markers will be displayed on the signal dimensions.

    Parameters
    ----------
    peaks_list : 4D NumPy array
    signal_axes : HyperSpy axes_manager object
    color : string, optional
        Color of point marker. Default 'red'.
    size : scalar, optional
        Size of the point marker. Default 20.

    Returns
    -------
    marker_list : list of HyperSpy marker objects

    Example
    -------
    >>> s = ps.dummy_data.get_cbed_signal()
    >>> peak_array = s.find_peaks(lazy_result=False, show_progressbar=False)
    >>> import pixstem.marker_tools as mt
    >>> marker_list = mt._get_4d_points_marker_list(
    ...     peak_array, s.axes_manager.signal_axes)

    """
    max_peaks = 0
    for ix, iy in np.ndindex(peaks_list.shape[:2]):
        peak_list = peaks_list[ix, iy]
        if peak_list is not None:
            n_peaks = len(peak_list)
            if n_peaks > max_peaks:
                max_peaks = n_peaks

    marker_array_shape = (peaks_list.shape[0], peaks_list.shape[1], max_peaks)
    marker_x_array = np.ones(marker_array_shape) * -1000
    marker_y_array = np.ones(marker_array_shape) * -1000
    for ix, iy in np.ndindex(marker_x_array.shape[:2]):
        peak_list = peaks_list[ix, iy]
        if peak_list is not None:
            for i_p, peak in enumerate(peak_list):
                if signal_axes is None:
                    marker_x_array[ix, iy, i_p] = peak[1]
                    marker_y_array[ix, iy, i_p] = peak[0]
                else:
                    marker_x_array[ix, iy, i_p] = signal_axes[0].index2value(
                            int(peak[1]))
                    marker_y_array[ix, iy, i_p] = signal_axes[1].index2value(
                            int(peak[0]))

    marker_list = []
    for i_p in range(max_peaks):
        marker = hm.point(
                marker_x_array[..., i_p], marker_y_array[..., i_p],
                color=color, size=size)
        marker_list.append(marker)
    return marker_list


def _get_4d_line_segment_list(lines_array, signal_axes=None, color='red',
                              linewidth=1, linestyle='solid'):
    """Get a list of 4 dimensional line segments markers.

    The markers will be displayed on the signal dimensions.

    Parameters
    ----------
    lines_array : 4D NumPy array
    signal_axes : HyperSpy axes_manager object
    color : string, optional
        Color of point marker. Default 'red'.
    linewidth : scalar, optional
        Default 2
    linestyle : string, optional
        Default 'solid'

    Returns
    -------
    marker_list : list of HyperSpy marker objects

    """
    max_lines = 0
    for ix, iy in np.ndindex(lines_array.shape[:2]):
        lines_list = lines_array[ix, iy]
        if lines_list is not None:
            n_lines = len(lines_list)
            if n_lines > max_lines:
                max_lines = n_lines

    marker_array_shape = (lines_array.shape[0], lines_array.shape[1],
                          max_lines)
    marker_x1_array = np.ones(marker_array_shape) * -1000
    marker_y1_array = np.ones(marker_array_shape) * -1000
    marker_x2_array = np.ones(marker_array_shape) * -1000
    marker_y2_array = np.ones(marker_array_shape) * -1000
    for ix, iy in np.ndindex(marker_x1_array.shape[:2]):
        lines_list = lines_array[ix, iy]
        if lines_list is not None:
            for i_p, line in enumerate(lines_list):
                if signal_axes is None:
                    marker_x1_array[ix, iy, i_p] = line[1]
                    marker_y1_array[ix, iy, i_p] = line[0]
                    marker_x2_array[ix, iy, i_p] = line[3]
                    marker_y2_array[ix, iy, i_p] = line[2]
                else:
                    sa0iv = signal_axes[0].index2value
                    sa1iv = signal_axes[1].index2value
                    marker_x1_array[ix, iy, i_p] = sa0iv(int(line[1]))
                    marker_y1_array[ix, iy, i_p] = sa1iv(int(line[0]))
                    marker_x2_array[ix, iy, i_p] = sa0iv(int(line[3]))
                    marker_y2_array[ix, iy, i_p] = sa1iv(int(line[2]))

    marker_list = []
    for i_p in range(max_lines):
        marker = hm.line_segment(
                marker_x1_array[..., i_p], marker_y1_array[..., i_p],
                marker_x2_array[..., i_p], marker_y2_array[..., i_p],
                color=color, linewidth=linewidth, linestyle=linestyle)
        marker_list.append(marker)
    return marker_list


def _get_2d_line_segment_list(lines_list, signal_axes=None, color='red',
                              linewidth=1, linestyle='solid'):
    """Get a list of 2d dimensional line segments markers.

    The markers will be displayed on the signal dimensions.

    Parameters
    ----------
    lines_list : list
        In form [[x01, y01, x02, y02], [x11, y11, x12, y12], ...]
    signal_axes : HyperSpy axes_manager object
    color : string, optional
        Color of point marker. Default 'red'.
    linewidth : scalar, optional
        Default 2
    linestyle : string, optional
        Default 'solid'

    Returns
    -------
    marker_list : list of HyperSpy marker objects

    """
    marker_list = []
    for x1, y1, x2, y2 in lines_list:
        marker = hm.line_segment(x1, y1, x2, y2, color=color,
                                 linewidth=linewidth, linestyle=linestyle)
        marker_list.append(marker)
    return marker_list


def _add_permanent_markers_to_signal(signal, marker_list):
    """Add a list of markers to a signal.

    Parameters
    ----------
    signal : PixelatedSTEM or Signal2D
    marker_list : list of markers

    Example
    -------
    >>> s = ps.dummy_data.get_cbed_signal()
    >>> peak_array = s.find_peaks(lazy_result=False, show_progressbar=False)
    >>> import pixstem.marker_tools as mt
    >>> marker_list = mt._get_4d_points_marker_list(
    ...     peak_array, s.axes_manager.signal_axes)
    >>> mt._add_permanent_markers_to_signal(s, marker_list)
    >>> s.plot()

    """
    if not hasattr(signal.metadata, 'Markers'):
        signal.metadata.add_node('Markers')
    marker_extra = len(signal.metadata.Markers)
    for imarker, marker in enumerate(marker_list):
        marker_name = 'marker{0}'.format(imarker + marker_extra)
        signal.metadata.Markers[marker_name] = marker


def add_peak_array_to_signal_as_markers(
        signal, peak_array, color='red', size=20):
    """Add an array of points to a signal as HyperSpy markers.

    Parameters
    ----------
    signal : PixelatedSTEM or Signal2D
    peak_array : 4D NumPy array

    Example
    -------
    >>> s = ps.dummy_data.get_cbed_signal()
    >>> peak_array = s.find_peaks(lazy_result=False, show_progressbar=False)
    >>> import pixstem.marker_tools as mt
    >>> mt.add_peak_array_to_signal_as_markers(s, peak_array)
    >>> s.plot()

    """
    marker_list = _get_4d_points_marker_list(
            peak_array, signal.axes_manager.signal_axes, color=color,
            size=size)
    _add_permanent_markers_to_signal(signal, marker_list)
