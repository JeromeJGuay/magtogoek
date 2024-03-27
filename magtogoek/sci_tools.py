"""
Date: February 2023
Made by jeromejguay

This module contains general mathematical and scientific functions.
"""
from typing import List

import numpy as np
import typing as tp

import pandas as pd
import pygeodesy.errors
import xarray as xr
from nptyping import NDArray
from pygeodesy.ellipsoidalVincenty import LatLon


def cartesian2north_polar(x: NDArray, y: NDArray) -> tp.Tuple[NDArray, NDArray]:
    """Compute the azimut (north clockwise)  and the radius from x, y vector.

    ```
    azimut = (arctan2(x, y) + 360) % 360
    radius = sqrt(x**2 + y**2)
    ```

    Parameters
    ----------
    x:
        Vector x component
    y:
        Vector y component

    Returns
    -------
    azimut (north clockwise), radius
    """
    return (np.rad2deg(np.arctan2(x, y)) + 360) % 360, np.hypot(x, y)


def north_polar2cartesian(radius: NDArray, azimut: NDArray) -> tp.Tuple[NDArray, NDArray]:
    """ Compute x and y from radius and azimut (degree) (north clockwise)

    Parameters
    ----------
    radius:
        Vector norm
    azimut: (degree)
        Vector direction (north clockwise)

    Returns
    -------
    x, y

    """
    return radius * np.sin(np.deg2rad(azimut)), radius * np.cos(np.deg2rad(azimut))


def circular_distance(a1, a2, units="rad"):
    """
    Function circdist usage:
        d   =   circdist(a1,a2,units='rad')

    Returns to 'd' the distance between angles a1 and a2
    expected to be radians by default, or degrees if units
    is specified to 'deg'.
    Parameters
    ----------
    a1, a2 : float
        Input angle.
    units : str
        Units of input angles ('deg', 'rad')
    Returns
    -------
    float
        Angular distance between `a1` and `a2`.

    Notes
    -----
    Taken from jeanlucshaw adcp2nc: https://github.com/jeanlucshaw/adcp2nc/
    """
    if units == "deg":
        a1 = np.deg2rad(a1)
        a2 = np.deg2rad(a2)
        #a1 = np.pi * a1 / 180
        #a2 = np.pi * a2 / 180

    if np.isscalar(a1) and np.isscalar(a2):
        v1 = np.array([np.cos(a1), np.sin(a1)])
        v2 = np.array([np.cos(a2), np.sin(a2)])
        dot = np.dot(v1, v2)
    elif not np.isscalar(a1) and np.isscalar(a2):
        a2 = np.tile(a2, a1.size)
        v1 = np.array([np.cos(a1), np.sin(a1)]).T
        v2 = np.array([np.cos(a2), np.sin(a2)]).T
        dot = (v1 * v2).sum(-1)
    else:
        v1 = np.array([np.cos(a1), np.sin(a1)]).T
        v2 = np.array([np.cos(a2), np.sin(a2)]).T
        dot = (v1 * v2).sum(-1)

    res = np.arccos(np.clip(dot, -1.0, 1.0))

    if units == "deg":
        res = np.rad2deg(res)
        #res = 180 * res / np.pi

    return res


def vincenty(p0: tp.Tuple[float, float], p1: tp.Tuple[float, float]) -> float:
    """Calculate the distance between 2 coordinates with pygeodesy.ellipsoidalVincenty.LatLon

    Great Circle Distance with Datum = WGS84

    Parameters
    ----------
    p0 :
       (longitude, latitude) of the first points in decimal degrees
    p1 :
       (longitude, latitude) of the second points in decimal degrees

    Returns
    -------
    distance :
        distance between the two points in meters.
    """
    try:
        return LatLon(p0[1], p0[0]).distanceTo(LatLon(p1[1], p1[0]))
    except pygeodesy.errors.RangeError:
        return np.nan


def get_gps_bearing(p0: tp.Tuple[float, float], p1: tp.Tuple[float, float]) -> float:
    """Calculate the bearing between two coordinates with pygeodesy.ellipsoidalVincenty.LatLon

    Datum = WGS84

    Parameters
    ----------
    p0 :
       (longitude, latitude) of the first points in decimal degrees
    p1 :
       (longitude, latitude) of the second points in decimal degrees

    Returns
    -------
    bearing in degrees [0, 360]
    """
    try:
        return LatLon(p0[1], p0[0]).initialBearingTo(LatLon(p1[1], p1[0]))
    except pygeodesy.errors.RangeError:
        return np.nan


def rotate_xy_vector(
    x: NDArray, y: NDArray, angle: float
) -> tp.Tuple[NDArray, NDArray]:
    """Rotate Vector anti-clockwise by `angle` degrees.

    (Rotates the frame of reference clockwise)

    [x_r]  = [cos(angle), -sin(angle)][x]
    [y_r]  = [sin(angle),  cos(angle)][y]

    Parameters
    ----------
    x:
       Vector component along x

    y:
       Vector component along y

    angle:
        Angle of rotation in decimal degree

    Returns
    -------
    x_r :
        Rotated velocity components along x_r.
    y_r :
        Rotated velocity components along y_r.
    """

    angle_rad = np.deg2rad(angle)

    x_r = np.cos(angle_rad) * x - np.sin(angle_rad) * y
    y_r = np.sin(angle_rad) * x + np.cos(angle_rad) * y

    return x_r, y_r


def xy_vector_magnetic_correction(x: NDArray, y: NDArray , magnetic_declination: float):
    """Rotate vector clockwise by `magnetic_declination` degree

    Parameters
    ----------
    x:
       Vector component along x

    y:
       Vector component along y

    magnetic_declination:
       Angle between the True North and the Magnetic North. (positive east)

    Returns
    -------
        x_r :
            Rotated velocity components along x_r.
        y_r :
            Rotated velocity components along y_r.
    """
    return rotate_xy_vector(x, y, -magnetic_declination)



def rotate_heading(heading: NDArray, angle: tp.Union[NDArray, float]) -> NDArray:
    """
    Equation for the heading: (heading + 180 + angle) % 360 - 180
        1. [-180, 180[ -> [0, 360[ -> [angle, 360+angle[
        2. [angle, 360+angle[ -> [0, 360[ -> [-180, 180[

    Parameters
    ----------
    heading :
        heading (-180 to 180) | North = 0, East = 90
    angle :
        Clockwise angle to rotate.

    Returns
    -------
    Rotated Heading
    """
    return (heading + 180 + angle) % 360 - 180


def data_spike_detection(data: np.ndarray, threshold: float, window: int = 3):
    """ Spike detection in time series.

    ```
    d : `data`
    d': Rolling average of the `data`
    spike = |d' - d| >= threshold
    ```
    The rolling average window is centered and has a window of size `window`.
    The minimum number of points in the window is set 1.

    Parameters
    ----------
    data :
        Time series to check for spikes.
    threshold :
        Threshold for spike detection.
    window : Default = 3
        Size of the rolling window.

    Returns
    -------
    Boolean array of the same shape as data where True values are data spikes.

    """

    if window is None:
        window = 3

    data_rolled = pd.DataFrame(data).interpolate().rolling(window=window, min_periods=1, center=True).mean()[0].values

    spikes = np.abs(data - data_rolled) >= threshold

    return spikes


def time_drift_correction(
        data: np.ndarray,
        data_time: pd.DatetimeIndex,
        drift: float,
        start_time: List[str] = None
) -> np.ndarray:
    """Apply a linear correction for drift over time.

    Subtracts the drift from the data as a linear regression

    drift_array[0] = 0 and drift_array[-1] = drift

    ```
    data_corrected(time) = data(time) - drift_array(time)
    ```

    Parameters
    ----------
    data :
    data_time :
    drift :
        Total drift. Amount of drift by the end of the time series.
    start_time : (Optional) TimeStamp %Y-%m-%dT%H:%M:%S
        Timestamp that the drift started. If not provided, the correction will start at
        the initial time (time[0]).

    Returns
    -------
    Corrected data
    """

    drift = [0, drift]
    drift_time = data_time[[0,-1]]

    if start_time is not None:
        drift_time[0] = start_time

    _data = xr.DataArray(data, coords={'time': data_time})
    _drift = xr.DataArray(drift, coords={'time': drift_time})

    _drift_correction = _drift.interp(time=_data.time, kwargs={'fill_value': 0}).data

    return data - _drift_correction


def data_calibration_correction(data: np.ndarray, slope: float, offset: float) -> np.ndarray:
    """Apply a linear correction using linear regression coefficient.

    ```
    data_calibrated = slope * data + offset
    ```
    """

    return slope * data + offset


def celsius_to_kelvin(celsius: float) -> float:
    return celsius + 273.15