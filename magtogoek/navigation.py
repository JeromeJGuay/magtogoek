"""
author: jerome.guay@protonmail.com

Module to load GPS data and compute navigation data from `nmea`, `gpx` or `netcdf` file format


Notes
-----
compute_navigation:
    After testing, the u_ship, v_ship computation need more work, using a large value for the rolling
    average window could do the trick.
"""
import sys
import typing as tp
import warnings
from pathlib import Path

import gpxpy
import numpy as np
import pynmea2
import xarray as xr
import matplotlib.pyplot as plt
from magtogoek.tools import get_gps_bearing, vincenty
from magtogoek.utils import get_files_from_expression

FILE_FORMATS = (".log", ".gpx", ".nc")
NAVIGATION_VARIABLES_NAME = ("lon", "lat", "time",'u_ship', 'v_ship')
VARIABLE_NAME_MAPPING = dict(
    time=("Time", "TIME", "T", "t"),
    lon=("LON", "Lon", "longitude", "LONGITUDE", "Longitude", "X", "x"),
    lat=("LAT", "Lat", "latitude", "LATITUDE", "Latitude", "Y", "y"),
    u_ship=(),
    v_ship=(),
)


def load_navigation(filenames):
    """Load gps data from  `nmea`, `gpx` or `netcdf` file format.
    Returns a xarray.Dataset with the loaded data.
    """

    filenames = get_files_from_expression(filenames)

    datasets = []

    for filename in filenames:
        ext = Path(filename).suffix
        if ext not in FILE_FORMATS:
            with open(filename) as unkown_format:
                first_char = unkown_format.read(1)
                # some XML first char are order mark, \ufeef, for big- and little-endian.
                if first_char == "\ufeff":
                    first_char = unkown_format.read(1)
                if first_char == "<":
                    ext = ".gpx"
                if first_char == "$":
                    ext = ".log"

        if ext == ".nc":
            _dataset = xr.open_dataset(filename)
            _dataset = _check_variables_names(_dataset)
        elif ext == ".gpx":
            _dataset = _load_gps(filename, file_type="gpx")
        elif ext == ".log":
            _dataset = _load_gps(filename, file_type="nmea")
        else:
            _dataset = None

        if _dataset is not None:
            datasets.append(_dataset)

    if len(datasets) > 0:
        flags = {'time_flag': False, 'lonlat_flag': False, 'uv_ship_flag': False}
        for key in flags.keys():
            flags[key] = all([ds.attrs[key] for ds in datasets])
        dataset = xr.merge(datasets)
        dataset.attrs.update(flags)
        return dataset
    else:
        return None


def _load_gps(filename: str, file_type: str) -> xr.Dataset:
    """Load navigation data `lon`, `lat` and `time` from a gpx or nmea file format."""
    reader = {"gpx": _read_gpx, "nmea":_read_nmea}[file_type]
    gps_data = reader(filename)

    dataset = xr.Dataset(
        {"lon": (["time"], gps_data["lon"]), "lat": (["time"], gps_data["lat"])},
        coords={"time": gps_data["time"]},
        attrs={'time_flag': True, 'lonlat_flag': True, 'uv_ship_flag': False},
    )
    return dataset.sortby("time")


def _read_gpx(filename: str) -> tp.Dict:
    """Load navigation data `lon`, `lat` and `time` from a gpx file.
    Returns a dictionary with the loaded data."""
    gps_data = dict(time=[], lon=[], lat=[])
    with open(filename, "r") as f:
        gps = gpxpy.parse(f)
        for track in gps.tracks:
            for segment in track.segments:
                for point in segment.points:
                    gps_data["time"].append(
                        np.datetime64(point.time.replace(tzinfo=None))
                    )
                    gps_data["lon"].append(point.longitude)
                    gps_data["lat"].append(point.latitude)

    return gps_data


def _read_nmea(filename: str) -> tp.Dict:
    """Load navigation data `lon`, `lat` and `time` from a NMEA file.
    Returns a dictionary with the loaded data.
    """
    gps_data = dict(time=[], lon=[], lat=[])
    with open(filename, "r") as f:
        for line in f.readlines():
            m = pynmea2.parse(line)
            if m.sentence_type == "GGA":
                gps_data["lon"].append(m.longitude)
                gps_data["lat"].append(m.latitude)
            if m.sentence_type == "ZDA":
                gps_data["time"].append(np.datetime64(m.datetime.replace(tzinfo=None)))
    return gps_data


def compute_navigation(
    filenames: str, output_name: str = None, window: int = 1,
):
    """Compute the `bearing`, `speed`, `u_ship` and `v_ship` from gps data in nmea text format or gpx xml format.

    Returns an xarray.dataset object with the compute data and gps data.

    Parameters
    ----------
    output_name
    filenames
    window :
        Size of the centered averaging window for u_ship, v_ship and bearing computation.

    Notes
    -----
    WARNINGS:
        After testing, the u_ship, v_ship computation need more works.

    """
    filenames = get_files_from_expression(filenames)
    print('Loading files ...', end='\r')
    dataset = load_navigation(filenames)
    if dataset is None:
        print('Could not load navigation data from file(s).')
        'Loading files ... [Error]'
    elif dataset.attrs['time_flag'] is False:
        'Loading files ... [Error]'
        print(f"`time` in the coordinates. Valid time name {VARIABLE_NAME_MAPPING['time']}")
        sys.exit()
    elif dataset.attrs['lonlat_flag'] is False:
        print('Loading files ... [Error]')
        print(f"Either `lon` and/or `lat` variable not found the dataset. Valid `lon` name {VARIABLE_NAME_MAPPING['lon']}, Valid `lat` name {VARIABLE_NAME_MAPPING['lon']}")
        sys.exit()
    else:
        print('Loading files ... [Done]')

    print('Computing navigation ...', end='\r')
    dataset = _compute_navigation(dataset, window=window)
    print('Computing navigation ... [Done]')

    dataset.attrs["input_files"] = filenames

    if not output_name:
        output_name = filenames[0]
        if Path(output_name).suffix == ".nc":
            p = Path(output_name)
            output_name = str(p.with_name(p.stem + "_nav.nc"))

    _plot_navigation(dataset)
    dataset.attrs = {'filenames': filenames, 'averaging_window_size': window}
    output_path = Path(output_name).with_suffix(".nc").absolute()
    dataset.to_netcdf(output_path)
    print(f'Files saved at {output_path}')

    return dataset


def _compute_navigation(
    dataset: xr.Dataset, window: tp.Union[int, None] = None,
) -> xr.Dataset:
    """compute bearing, speed, u_ship and v_ship

    Computes the distance between each GPS coordinates with Vincenty and
    WGS84 and speed = distance / time_delta.

    Parameters
    ----------
    window :
        Size of the centered averaging window.
    """
    centered_time, course, speed = _compute_speed_and_course(dataset.time, dataset.lon.values, dataset.lat.values)

    u_ship = speed * np.sin(np.deg2rad(course))
    v_ship = speed * np.cos(np.deg2rad(course))

    nav_dataset = xr.Dataset(
        {
            "course": (["time"], course),
            "speed": (["time"], speed),
            "u_ship": (["time"], u_ship),
            "v_ship": (["time"], v_ship),
        },
        coords={"time": centered_time},
        attrs={'history': []}
    )

    if window is not None:
        window = int(window)
        nav_dataset = nav_dataset.rolling(time=window, center=True).mean()
        nav_dataset.attrs['history'].append(f'A rolling average of length {window} was applied to the data.')

    nav_dataset = nav_dataset.interp(time=dataset.time)

    dataset = xr.merge((nav_dataset, dataset), compat='override')
    dataset.attrs.update({'uv_ship_flag': True})

    return dataset


def _compute_speed_and_course(time: tp.Union[list, np.ndarray],
                              longitude: tp.Union[list, np.ndarray],
                              latitude: tp.Union[list, np.ndarray]) -> tp.Tuple[np.ndarray, np.ndarray, np.ndarray]:

    position0 = np.array((longitude[:-1], latitude[:-1])).T.tolist()
    position1 = np.array((longitude[1:], latitude[1:])).T.tolist()

    distances = np.array(list(map(vincenty, position0, position1)))  # meter

    course = np.array(list(map(get_gps_bearing, position0, position1)))  # degree

    time_delta = np.diff(time).astype("timedelta64[s]")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        speed = distances / time_delta.astype("float64")  # meter per seconds

    centered_time = time[:-1] + time_delta / 2

    return centered_time, course, speed


def _plot_navigation(dataset: xr.Dataset):
    """plots bearing, speed, u_ship and v_ship from a dataset"""

    fig = plt.figure(figsize=(12, 8))
    ax_course = plt.subplot(411)
    ax_course.set_ylabel("course [degree]")
    ax_speed = plt.subplot(412, sharex=ax_course)
    ax_speed.set_ylabel("speed [m/s]")
    ax_uship = plt.subplot(413, sharex=ax_course)
    ax_uship.set_ylabel("uship [m/s]")
    ax_vship = plt.subplot(414, sharex=ax_course)
    ax_vship.set_ylabel("vship [m/s]")

    dataset.course.plot(ax=ax_course)
    dataset.speed.plot(ax=ax_speed)
    dataset.u_ship.plot(ax=ax_uship)
    dataset.v_ship.plot(ax=ax_vship)

    ax_course.get_xaxis().set_visible(False)
    ax_speed.get_xaxis().set_visible(False)
    ax_uship.get_xaxis().set_visible(False)

    plt.subplots_adjust(hspace=0.05)

    plt.show()


def _check_variables_names(dataset):
    """Check what variables are int he dataset.

    Converts variables name if needed.

    Return None if:
     - neither ( (lon and lat) or (u_ship and v_ship)) are not found.
     - time is not a coordinates.
    """
    found_variables = []
    for var, varnames in VARIABLE_NAME_MAPPING.items():
        if var in dataset:
            found_variables.append(var)
        else:
            for name in varnames:
                if name in dataset:
                    dataset = dataset.rename({name: var})
                    found_variables.append(var)

    dataset.attrs.update({'time_flag': False, 'lonlat_flag': False, 'uv_ship_flag': False})
    if 'time' not in dataset.coords:
        return dataset
    else:
        dataset.attrs['time_flag'] = True
    if all([var in dataset for var in ('lon', 'lat')]):
        dataset.attrs['lonlat_flag'] = True
    if all([var in dataset for var in ('u_ship', 'v_ship')]):
        dataset.attrs['uv_ship_flag'] = True

    return dataset

