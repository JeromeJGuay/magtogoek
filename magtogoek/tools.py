"""
This module contains general functions to manipulate data.
"""
import sys

import pandas as pd
import typing as tp

import numpy as np
import xarray as xr
import warnings

from magtogoek import logger as l
from magtogoek.exceptions import MagtogoekExit
from magtogoek.sci_tools import cartesian2north_polar


def nans(shape: tp.Union[list, tuple, np.ndarray]) -> np.ndarray:
    """return array of nan of shape `shape`"""
    return np.full(shape, np.nan)


def get_flagged_data(dataset: xr.Dataset, var: str, flag_value: int, ancillary_variables: str = None) -> xr.DataArray:
    """
    Set value to nan where the flags are not equal to the `flag_value`.

    Parameters
    ----------
    dataset :
        The variable `var` must be in the dataset along with `var+'_QC'`.
    var :
    flag_value:
        flag value of the data to keep.
    ancillary_variables : Optional
        Name of the flag variable. If not provided, the name must be defined as
        the variable attributes `ancillary_variables`.
    Returns
    -------
    data with nan values where the flags are not equal to `flag_value`.
    """
    if ancillary_variables is None:
        ancillary_variables = dataset[var].attrs["ancillary_variables"]

    return dataset[var].where(dataset[ancillary_variables].data == flag_value)


def filter_flagged_data(dataset: xr.Dataset, var: str, flag_min: int = 0, flag_max: int = 9, ancillary_variables: str = None) -> xr.DataArray:
    """
    Set value to nan where the flags are outside `flag_min` and `flag_max`.

    Parameters
    ----------
    dataset :
        The variable `var` must be in the dataset along with `var+'_QC'`.
    var :
    flag_min :
        min flag value to include.
    flag_max :
        max flag value to include.
    ancillary_variables : Optional
        Name of the flag variable. If not provided, the name must be defined as
        the variable attributes `ancillary_variables`.
    Returns
    -------
    data with nan values where the flags are outside `flag_min` and `flag_max`.
    """
    if ancillary_variables is None:
        ancillary_variables = dataset[var].attrs["ancillary_variables"]

    return dataset[var].where(
        (dataset[ancillary_variables].data >= flag_min)
        & (dataset[ancillary_variables].data <= flag_max)
    )


def round_up(x: tp.Any, scale: float = 1):
    return np.ceil(np.asarray(x) * 1 / scale) * scale


def polar_histo_from_cartesian(dataset: xr.Dataset, x_vel: str, y_vel: str, r_max: float, flag_thres: int):
    """Return a polar histogram from data in cartesian coordinates

    Parameters
    ----------
    dataset
    x_vel
    y_vel
    r_max
    flag_thres

    Returns
    -------

    """
    u = filter_flagged_data(dataset=dataset, var=x_vel, flag_max=flag_thres).data.flatten()
    v = filter_flagged_data(dataset=dataset, var=y_vel, flag_max=flag_thres).data.flatten()
    ii = np.isfinite(u) & np.isfinite(v)

    azimut, radius = cartesian2north_polar(u[ii], v[ii])

    azimut = np.deg2rad(azimut)

    rN, aN = 30, 180
    rbins, abins = np.linspace(0, r_max, rN), np.linspace(0, 2 * np.pi, aN)

    return np.histogram2d(azimut, radius, bins=(abins, rbins))


def regrid_dataset(dataset: xr.Dataset,
                   grid: tp.Union[str, list, np.ndarray],
                   method: str = 'interp',
                   dim: str = 'depth') -> xr.Dataset:
    """
    Regrid data to predefined depths.

    Parameters
    ----------
    dataset :
        Input data.
    grid :
        Path to a column text file or array-like of depths in meters.
    method :
        One of [`interp`, `bin`]. Regrid by bin-averaging or interpolation.
    dim :
        Name of the coordinate along which to regrid `dataset`.

    Returns
    -------
    regridded :
        The input data regridded on `grid` along `dim`.

    Note
    ----
    The `interp` method performs linear interpolation. The `bin` method
    performs averaging of input data strictly within the bin boundaries
    and with equal weights for all data inside each bin.
    """
    # Read grid file
    if isinstance(grid, str):
        z = np.loadtxt(grid)
    elif isinstance(grid, (list, np.ndarray)):
        z = np.array(grid)
    else:
        raise ValueError('Grid must be path or array-like, not: %s' % type(grid))

    # Regrid by interpolation
    if method == 'interp':
        regridded = dataset.interp({dim: z})

    # Regrid by bin averaging
    elif method == 'bin':
        regridded = _xr_bin(dataset, dim, z)

    # Error handling
    else:
        raise ValueError('Unrecognized regrid method: %s' % method)

    # Change data extent for the depth coordinate
    regridded[dim].attrs['data_min'] = z.min()
    regridded[dim].attrs['data_max'] = z.max()

    return regridded


def _bin_centers_to_edges(centers: tp.Union[list, np.ndarray]) -> np.ndarray:
    """
    Get bin edges from bin centers.

    Bin centers can be irregularly spaced. Edges are halfway between
    one point and the next.

    Parameters
    ----------
    centers :
        Bin centers.

    Returns
    -------
    edges :
        Bin edges.

    """
    z = np.array(centers)
    dz = np.diff(centers)
    return np.r_[z[0]-dz[0]/2, z[1:]-dz/2, z[-1] + dz[-1]/2]


def _bin_edges_to_centers(edges: tp.Union[list, np.ndarray]) -> np.ndarray:
    """
    Get bin centers from bin edges.

    Bin centers can be irregularly spaced. Edges are halfway between
    one point and the next.

    Parameters
    ----------
    edges : 1D array
        Bin edges.

    Returns
    -------
    centers :
        Bin centers.

    """
    edges = np.array(edges)
    return edges[:-1] + np.diff(edges) / 2


def _xr_bin(dataset: tp.Union[xr.Dataset, xr.DataArray],
            dim: str,
            bins: np.ndarray,
            centers: bool = True) -> tp.Union[xr.Dataset, xr.DataArray]:
    """
    Bin dataset along `dim`.

    Convenience wrapper for the groupby_bins xarray method. Meant for
    simply binning xarray `dataset` to the values of dimension `dim`, and
    return values at bin centers (or edges) `bins`.

    Parameters
    ----------
    dataset :
        Dataset to operate on.
    dim :
        Name of dimension along which to bin.
    bins :
        Bin centers or edges if `centers` is False.
    centers :
        Parameter `bins` is the centers, otherwise it is the edges.

    Returns
    -------
    binned :
        Dataset binned at `bin` along `dim`.

    """
    # Bin type management
    if centers:
        edge = _bin_centers_to_edges(bins)
        labels = bins
    else:
        edge = bins
        labels = _bin_edges_to_centers(bins)

    # Skip for compatibility with DataArray
    if isinstance(dataset, xr.Dataset):
        # Save dimension orders for each variable
        dim_dict = dict()
        for key in dataset.keys():
            dim_dict[key] = dataset[key].dims

    # Avoids printing mean of empty slice warning
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)

        # Bin reduction 
        output = (dataset.groupby_bins(dataset[dim], bins=edge, labels=labels)
                  .mean(dim=dim, keep_attrs=True)
                  .rename({dim+'_bins': dim}))

    # Skip for compatibility with DataArray
    if isinstance(dataset, xr.Dataset):
        # Restore dataset attributes
        output.attrs = dataset.attrs

        # Restore dimension order to each variable
        for key, dim_tuple in dim_dict.items():
            if dim not in dim_tuple:
                output[key] = dataset[key]
            else:
                output[key] = output[key].transpose(*dim_tuple)

    return output


def _isin_any(array: tp.Union[np.ndarray, xr.DataArray],
              element: tp.Union[int, float, str],
              dim) -> tp.Union[np.ndarray, xr.DataArray]:
    """
    Check if `elements` are in `array` along `axis`.

    Parameters
    ----------
    array :
        In which to look for elements.
    element :
        Element to look for.
    dim :
        Name of the dimension along which look for `elements` in `array`.

    Returns
    -------
    bool_array :
        True if element was found, False otherwise.
    """
    return (array == element).any(dim=dim)


def _new_flags_bin_regrid(flags: xr.DataArray,
                          bin_depths: np.ndarray,
                          dim: str = 'depth') -> xr.DataArray:
    """
    Quality flag transfer function for bin average regridding.

    Parameters
    ----------
    flags :
        Flags prepared for regridding (5, 8, 9).
    bin_depths :
        Center of the regridding averaging bins (meters).
    dim :
        Name of the dimension along which the binning is done.

    Returns
    -------
    new_flags :
        Quality flags for the regridded data.

    """
    bin_edges = _bin_centers_to_edges(bin_depths)

    # Determine if original bins contained 5 or 8 flags
    grouped = flags.groupby_bins(dim, bin_edges, labels=bin_depths)
    good = grouped.map(_isin_any, args=(8, dim,)).rename({f"{dim}_bins": dim})  # contains 8 flags
    changed = grouped.map(_isin_any, args=(5, dim,)).rename({f"{dim}_bins": dim})  # contains 5 flags

    # Set bins outside data from NaN to False (-> missing)
    good = good.where(np.isfinite(good), False).astype(bool)
    changed = changed.where(np.isfinite(changed), False).astype(bool)

    return good*8 + (changed & ~good)*5 + (~changed & ~good)*9


def _new_flags_interp_regrid(dataset: xr.Dataset, variable: str) -> xr.DataArray:
    """
    Quality flag transfer function for interpolation regridding.

    Parameters
    ----------
    variable :
        Name of the variable for which flags are being transfered.

    Returns
    -------
    new_flags :
        Quality flags for the regridded data variable.

    """
    good = ~dataset[f"{variable}"].isnull()
    changed = dataset[f"{variable}_QC"] == 5
  
    return good*8 + changed*5 + (~good & ~changed)*9


def _prepare_flags_for_regrid(flags: tp.Union[np.ndarray, xr.DataArray]) -> tp.Union[np.ndarray, xr.DataArray]:
    """
    Format quality control flags for input to regridding transfer schemes.

    Parameters
    ----------
    flags :
        Quality control flags [0, 1, 2, 3, 4, 5, 9].

    Returns
    -------
    new_flags :
        Quality control flags [5, 8, 9].

    Notes
    -----
    The rationale for this transformation is that after interpolation or
    averaging missing values should remain flagged as `missing`, good values
    should be flagged as `interpolated` and questionable values should be
    flagged as `modified`. All flag values are therefore funneled into
    these three types before regridding to simplify the transfer algorithms.
    """
    return (flags < 9)*5 + (flags < 3)*3 + (flags==9)*9


def cut_bin_depths(
        dataset: xr.Dataset, depth_range: tp.Union[int, float, list] = None
) -> xr.Dataset:
    """
    Return dataset with cut bin depths if the depth_range are not outside the depth span.
    Parameters
    ----------
    dataset :
    depth_range :
        min or (min, max) to be included in the dataset.
        Bin depths outside this range will be cut.

    Returns
    -------
    dataset with depths cut.

    """
    if depth_range:
        if not isinstance(depth_range, (list, tuple)):
            if depth_range > dataset.depth.max():
                l.log("depth_range value is greater than the maximum bin depth. Depth slicing aborted.")
            else:
                dataset = dataset.sel(depth=slice(depth_range, None))
                l.log(f"Bin of depth inferior to {depth_range} m were cut.")

        elif len(depth_range) == 2:
            if dataset.depth[0] > dataset.depth[-1]:
                depth_range.reverse()

            if depth_range[0] > dataset.depth.max() or depth_range[1] < dataset.depth.min():
                l.log("depth_range values are outside the actual depth range. Depth slicing aborted.")
            else:
                dataset = dataset.sel(depth=slice(*depth_range))
                l.log(f"Bin of depth inferior to {depth_range[0]} m and superior to {depth_range[1]} m were cut.")
        else:
            l.log(f"depth_range expects a maximum of 2 values but {len(depth_range)} were given. Depth slicing aborted.")
    return dataset


def cut_times(
        dataset: xr.Dataset, start_time: str = None, end_time: pd.Timestamp = None
) -> xr.Dataset:
    """
    Return a dataset with time cut if they are not outside the dataset time span.

    Parameters
    ----------
    dataset
    start_time :
        minimum time to be included in the dataset.
    end_time :
        maximum time to be included in the dataset.
    Returns
    -------
    dataset with times cut.

    """
    msg = []
    out_off_bound_time = False
    if start_time is not None:
        if pd.Timestamp(start_time) > dataset.time.max():
            out_off_bound_time = True
        else:
            msg.append(f"Start={start_time} [UTC]") #.strftime('%Y-%m-%dT%H:%M:%S')
    if end_time is not None:
        if pd.Timestamp(end_time) < dataset.time.min():
            out_off_bound_time = True
        else:
            msg.append(f"end={end_time} [UTC]") #.strftime('%Y-%m-%dT%H:%M:%S')
    if out_off_bound_time is True:
        l.warning("Trimming datetimes out of bounds. Time slicing aborted.")
    else:
        dataset = dataset.sel(time=slice(start_time, end_time))
        if len(msg) > 0:
            l.log('Time slicing: ' + ', '.join(msg) + '.')

    return dataset

def cut_index(
        dataset: xr.Dataset, dim: str, start_index:int = None, end_index: int = None
) -> xr.Dataset:
    """
    Return a dataset with data cut along dims.

    Parameters
    ----------
    dataset :
    dim :
    start_index : Number of point removed from the start.
    end_index : Number of point removed from the end

    Returns
    -------
    dataset with index cut.

    """
    if start_index is None and end_index is None:
        return dataset

    stop_index = None
    total_trim = 0
    msg = []


    if start_index is not None:
        total_trim += start_index

    if end_index is not None:
        total_trim += end_index
        stop_index = dataset.dims[dim] - end_index if end_index is not None else None

    if total_trim < dataset.dims[dim]:
        l.log(f"Number of points removed from the start: `{start_index or 0}`, from the end: `{end_index or 0}`")

        dataset = dataset.isel({dim: slice(start_index, stop_index)})
    else:
        l.warning("Trimming indices out of bounds. Index slicing aborted.")

    return dataset

def is_unique(array: np.ndarray):
    """Return True if array is single valued (Omits nan)."""
    return len(nan_unique(array)) == 1

def nan_unique(array: np.array) -> tp.Any:
    """np.unique() with np.nan omitted"""
    return np.unique(array[np.isfinite(array)])