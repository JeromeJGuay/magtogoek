"""
author: Jérôme Guay
date: Feb. 22, 2021
based in part  on: https://github.com/jeanlucshaw/adcp2nc/
                   https://github.com/hhourston/pycurrents_ADCP_processing


This script contains functions to read adcp files and load them in xarray.Dataset.

RDI data are read using CODAS Multiread reader from the pycurrents package. The Multiread
reader supports .000, .ENX, .ENS, .LTA and .STA binary files.
- sonar: 'wh', 'sv', 'os'.
- Sentinel V encoding is not fully supported by pycurrents.

RTI data re read using Magtogoek rti_reader built from rti_python tools by RoweTech.
- sonar: 'sw'
- Rowetech files can also be exporter directly to Teledyne `PD0` formats and read by pycurrents
using 'sw_pd0' for sonar.

Notes
-----
- Orientation is taken from the first profile of the first file if not no value is pass.
- We assume that the `dep` from OS already is the bin depth below surface.
- pd0 Fixed_Leader are know to have invalid configuration. msb=`11111111` and lsb=`11111111`. The
file will be processed but a warning will be raised. The cause was not investigated.
- This should probably be turned into an object.


See Also
--------
   * pycurrents.adcp.rdiraw.Multiread
   * rti_python

"""
import logging
import sys
import typing as tp
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

import gsw

import magtogoek.logger as l

from magtogoek.exceptions import MagtogoekExit
from magtogoek.adcp.rti_reader import RtiReader
from magtogoek.adcp.tools import dday_to_datetime64
from magtogoek.utils import get_files_from_expression, format_filenames_for_print
from pycurrents.adcp import rdiraw
from pycurrents.adcp.rdiraw import Multiread, rawfile

# This is to prevent pycurrents from printing warnings.
logging.getLogger(rdiraw.__name__).setLevel("CRITICAL")

RDI_SONAR = ["wh", "sv", "os", "sw_pd0"]
RTI_SONAR = ["sw"]

VEL_FILL_VALUE = -32768.0


def load_adcp_binary(
    filenames: tp.Union[str, tp.List[str]],
    sonar: str,
    yearbase: int = None,
    orientation: str = None,
    start_trim: int = None,
    end_trim: int = None,
    sensor_depth: float = None,
    bad_pressure: bool = False,
    start_time: str = None,
    time_step: float = None,
    magnetic_declination_preset: float = None,
) -> xr.Dataset:
    """Load RDI and RTI adcp data.

    Return a dataset with the ADCP data loaded.

    Notes:
    -----
    The adcp orientation is taken from the first profile of the first file
    if no orientation is given.

    Parameters
    ----------
    filenames:
        Path/to/files
    sonar:
        Type of sonar (`os`, `wh`, `sv`, `sw`, `sw_pd0`)
    yearbase: Optional
        year that the sampling begun.
    orientation: Optional
        Adcp orientation. Either `up` or `down`. Will overwrite the value
        of the binary file.
    start_trim: Optional
        Number of ensemble to cut from the start.
    end_trim: Optional
        Number of ensemble to cut from the end.
    sensor_depth: Optional
        If provided, the adcp depth (meter) will be adjusted so that its median equal `sensor_depth`.
    bad_pressure: Optional
        If True, XducerDepth is set to 0 or to `sensor_depth` if provided.
    start_time: Optional
        Format 'YYYY-MM-DDThh:mm:ss.ssss'.
        If provided, a new time coordinate vector, starting at `start_time`, is used instead of the
        one found in the raw adcp file.
        Use the parameter `time_step` to use a different time step than the one found in the adcp raw adcp file.
    time_step: Optional
        Time step in seconds. Only use if a `start_time` value is provided.
    magnetic_declination_preset: Optional
        RTI binaries do not contain the magnetic declination set in the ADCPs
        program before deployment, so the value read is always null. Overwrite
        this (e.g., with the value from the program commands) by setting this
        parameter.

    Returns
    -------
        Dataset with the loaded adcp data

    """

    l.section("Loading adcp data", t=True)

    filenames = get_files_from_expression(filenames)

    if sonar == "sv":
        l.warning(
            """(from pycurrents)
- The SV support is under development.  Missing features:
- The 0x7000-0x7004 IDs are not being parsed and stored.
- See pycurrents.adcp.rdiraw module for for information"""
        )

    # ------------------------ #
    # Reading the data file(s) #
    # ------------------------ #
    if sonar in RTI_SONAR:
        l.log(format_filenames_for_print("RTI ENS", filenames))

        data = RtiReader(filenames=filenames).read(
            start_trim=start_trim, end_trim=end_trim
        )
        if magnetic_declination_preset is not None:
            data.FL['EV'] = magnetic_declination_preset * 100

    elif sonar in RDI_SONAR:
        if sonar == "sw_pd0":
            sonar = "wh"
            l.log(format_filenames_for_print("RTI pd0", filenames))
        else:
            l.log(format_filenames_for_print("RDI pd0", filenames))

        try:
            data = Multiread(fnames=filenames, sonar=sonar, yearbase=yearbase).read(
                start=start_trim, stop=-end_trim if end_trim else None
            )
            if not data:
                raise MagtogoekExit("The sum of the trim values is greater than the number of ensemble. Exiting")
            data.vel = np.asarray(data.vel)
            if "vbvel" in data:
                data.vbvel = np.asarray(data.vbvel)
            if "bt_vel" in data:
                data.bt_vel = np.asarray(data.bt_vel)
        except RuntimeError:
            raise MagtogoekExit(f"ERROR: The input_files are not in a RDI pd0 format. RDI sonar : {RDI_SONAR}. Exiting")

        # Reading the files FixedLeaders to check for invalid config.
        # noinspection PyTupleAssignmentBalance
        data.sysconfig["up"], invalid_config_count = check_pd0_fixed_leader(
            filenames=filenames,
            sonar=sonar,
            yearbase=yearbase,
            start_trim=start_trim,
            end_trim=end_trim,
        )

        if invalid_config_count:
            l.warning(
                f"Invalid configuration, msb=`11111111` and lsb=`11111111`, found in the SysCfg of {invalid_config_count} FixedLeader. "
            )

    else:
        raise MagtogoekExit(f"{sonar} is not a valid. Valid sonar:(`os`, `wh`, `sv`, `sw`, `sw_pd0`)")

    if start_trim is not None or end_trim is not None:
        l.log(f"Number of points removed from the start: `{start_trim or 0}`, from the end: `{end_trim or 0}`")


    # -------------------- #
    # Compares orientation #
    # -------------------- #
    sysconfig_orientation = "up" if data.sysconfig["up"] else "down"
    if not orientation:
        orientation = sysconfig_orientation
    else:
        if orientation != sysconfig_orientation:
            l.warning(
                f"The user input adcp orientation is {orientation} but the one found in the file was {sysconfig_orientation}."
            )

    l.log(f"Adcp orientation is set to {orientation}.")

    # ---------------------------- #
    # Convert `dday` to datetime64 #
    # ---------------------------- #

    time, time_string, bad_dday = _get_time(data.dday, data.yearbase, start_time, time_step)

    # ----------------------------------------------------------- #
    # Convert depth relative to the ADCP to depth below surface   #
    # ----------------------------------------------------------- #

    average_xducer_depth = np.round(np.median(data.XducerDepth), 3)
    l.log(f"Sensor depth (XducerDepth) in raw file : {average_xducer_depth} m")
    if bad_pressure:
        l.log("XducerDepth were discarded by the user.")
        if sensor_depth:
            average_xducer_depth = sensor_depth
            l.log(f"XducerDepth set to {sensor_depth} m.")
        else:
            average_xducer_depth = 0
            l.log("XducerDepth set to 0 m.")
        data.XducerDepth[:] = average_xducer_depth
    xducer_depth = data.XducerDepth

    depth_difference = 0
    pressure_difference = 0
    if sensor_depth is not None:
        depth_difference = round(average_xducer_depth - sensor_depth, 3)
        if abs(depth_difference) > 0:
            l.log(
                [
                    f"The difference between the raw file sensor depth and the user "
                    f"provided `sensor_depth` ({sensor_depth} m) is {depth_difference} m",
                ]
            )

            l.log(
                f"{-depth_difference} m was added to the depths measured by the instrument."
            )

        average_xducer_depth = sensor_depth
        xducer_depth -= depth_difference

        pressure_difference = round(np.sign(depth_difference) * gsw.p_from_z(z=-abs(depth_difference), lat=0), 3)

    if sonar == "os":
        depth = data.dep - depth_difference
    else:
        if orientation == "down":
            depth = average_xducer_depth + data.dep
        else:
            depth = average_xducer_depth - data.dep

    if (depth < 0).all():
        l.warning("Bin depths are all negative, ADCP orientation is probably wrong.")

    # ------------------------ #
    # Initializing the dataset #
    # ------------------------ #
    dataset = xr.Dataset(coords={"depth": depth, "time": time})

    # --------------------------- #
    # Loading the transducer data #
    # --------------------------- #

    l.log(f"The velocity data are in {data.trans['coordsystem']} coordinate")

    # Water Velocities
    data.vel[data.vel == VEL_FILL_VALUE] = np.nan
    if data.trans["coordsystem"] in ['earth', 'xyz']:
        velocities_name = ("u", "v", "w", "e")
    else:
        velocities_name = ("v1", "v2", "v3", "v4")

    for i, v in enumerate(velocities_name):
        dataset[v] = (["depth", "time"], data.vel[:, :, i].T)
    l.log("Velocity data loaded")

    if sonar == "sv":
        data.vbvel[data.vbvel == VEL_FILL_VALUE] = np.nan
        dataset["vb_vel"] = (["depth", "time"], data.vbvel.T)
        dataset["vb_corr"] = (["depth", "time"], np.asarray(data.VBCorrelation.T))
        dataset["vb_amp"] = (["depth", "time"], np.asarray(data.VBIntensity.T))
        if "VBPercentGood" in data:
            dataset["vb_pg"] = (["depth", "time"], np.asarray(data.VBPercentGood.T))
        l.log("Data from the Sentinel V fifth beam loaded.")

    # BOTTOM VELOCITIES
    if "bt_vel" in data:
        if (data.bt_vel == 0).all():
            l.log("Bottom track values were all `0`, therefore they were dropped from the output.")
        elif not np.isfinite(data.bt_vel).all():
            l.log("Bottom track values were all `nan`, therefore they were dropped from the output.")

        else:
            data.bt_vel[data.bt_vel == VEL_FILL_VALUE] = np.nan
            for i, v in enumerate(velocities_name):
                dataset["bt_"+v] = (["time"], data.bt_vel[:, i].T)
            l.log("Bottom track data loaded")

    # BOTTOM DEPTH
    if "bt_depth" in data:
        if (data.bt_depth == 0).all():
            l.log("Bottom depth values were all `0`, therefore they were dropped from the output.")
        elif not np.isfinite(data.bt_depth).all():
            l.log("Bottom depth values were all `nan`, therefore they were dropped from the output.")
        else:
            dataset["bt_depth"] = (
                ["time"],
                np.asarray(np.nanmean(data.bt_depth, axis=-1)),
            )
            if orientation == "up":
                l.log(
                    "In a `up` orientation, bottom_depth corresponds to the water height above adcp, thus should "
                    "correspond to the xducer_depth measurements and bottom velocities correspond to the water surface "
                    "velocity. "
                )
                l.log(
                    f"The averaged xducer_depth computed from the bottom tracking is {np.median(data.bt_depth)}."
                )
            elif sensor_depth:
                if abs(depth_difference) > 0 and sonar == "os":
                    dataset["bt_depth"] -= depth_difference
            else:
                dataset["bt_depth"] += xducer_depth

            l.log("Bottom depth  data loaded")

    # QUALITY
    if "pg" in data:
        if data.trans["coordsystem"] == "beam":
            for i in range(4):
                dataset[f'pg{i+1}'] = (["depth", "time"], data.pg[:, :, i].T)
            l.log("Beams Percent Good data were loaded.")
        else:
            dataset["pg"] = (["depth", "time"], np.asarray(data.pg4.T))
        l.log('PercentGood data loaded.')
    else:
        l.warning("Percent good was not retrieve from the dataset.")

    if "cor1" in data:
        for i in range(1, 5):
            dataset[f"corr{i}"] = (["depth", "time"], np.asarray(data[f"cor{i}"].T))
        l.log('Correlation data loaded.')
    if "amp1" in data:
        for i in range(1, 5):
            dataset[f"amp{i}"] = (["depth", "time"], np.asarray(data[f"amp{i}"].T))
        l.log('Amplitude data loaded.')

    # ------------------ #
    # Loading depth data #
    # ------------------ #

    # For `wh`, `sv` and `sw` XducerDepth varies over times but is constant for `os`.
    if sonar != "os" and len(np.unique(xducer_depth)) > 1:
        dataset["xducer_depth"] = (["time"], np.asarray(xducer_depth))

    # --------------------------- #
    # Loading the navigation data #
    # --------------------------- #
    if "rawnav" in data:
        dataset["lon"] = (
            ["time"],
            np.array(data["rawnav"]["Lon1_BAM4"] * 180.0 / 2 ** 31),
        )
        dataset["lat"] = (
            ["time"],
            np.array(data["rawnav"]["Lat1_BAM4"] * 180.0 / 2 ** 31),
        )
        l.log("Navigation (GPS) data loaded.")

    # -------------------------------------------- #
    # Quick checkup and loading of other variables #
    # -------------------------------------------- #
    # For `wh`, `sv` and `sw` the pressure is added if available.
    if "Pressure" in data.VL.dtype.names:
        if not (data.VL["Pressure"] == 0).all():
            pressure = data.VL["Pressure"] / 1000  # decapascal to decibar
            if abs(pressure_difference) > 0:
                l.log(f"{-pressure_difference} dbar was added to the pressure measured by the instrument.")
                pressure -= pressure_difference
            dataset["pres"] = (["time"], pressure)
        else:
            l.log("Pressure data unavailable")

    if "heading" in data:
        if (data.heading == 0).all() or (np.diff(data.heading) == 0).all():
            l.warning("Adcp heading data are either all 0, or not varying.")
            if "nav_heading" in data:
                if (data.nav_heading == 0).all() or (np.diff(data.nav_heading) == 0).all():
                    l.warning("Navigation heading data are either all 0, or not varying.")
                else:
                    l.warning("Heading loaded from navigation data.")
                    dataset["heading"] = (["time"], np.asarray(data.heading))
        else:
            dataset["heading"] = (["time"], np.asarray(data.heading))
    if "roll" in data:
        if (data.roll == 0).all() or (np.diff(data.roll) == 0).all():
            l.warning("Roll data are either all 0, or not varying.")
        else:
            dataset["roll_"] = (["time"], np.asarray(data.roll))
    if "pitch" in data:
        if (data.pitch == 0).all() or (np.diff(data.pitch) == 0).all():
            l.warning("Pitch data are either all 0, or not varying.")
        else:
            dataset["pitch"] = (["time"], np.asarray(data.pitch))
    if "temperature" in data:
        if (data.temperature == 0).all() or (np.diff(data.temperature) == 0).all():
            l.warning("Temperature data are either all 0, or not varying.")
        else:
            dataset["temperature"] = (["time"], np.asarray(data.temperature))

    # ------------------------------- #
    # Load time string or dday if bad #
    # ------------------------------- #
    if bad_dday:
        dataset["dday"] = (["time"], np.asarray(data.dday))
    else:
        dataset["time_string"] = (["time"], time_string)

    if orientation == "up":
        dataset = dataset.sortby("depth")

    # -------------- #
    # Add attributes #
    # -------------- #
    sonar_names = dict(
        wh="WorkHorse", sv="Sentinel V", os="Ocean Surveyor", sw="SeaWATCH"
    )
    dataset.attrs["sonar"] = sonar_names[sonar]
    dataset.attrs["manufacturer"] = (
        "Teledyne RD Instruments Inc."
        if sonar in ["wh", "sv", "os"]
        else "Rowe Technologies Inc. (RTI)"
    )
    if "xducer_depth" not in dataset:
        dataset.attrs["xducer_depth"] = round(average_xducer_depth, 2)
    dataset.attrs["coord_system"] = data.trans["coordsystem"]
    dataset.attrs["beam_angle"] = data.sysconfig["angle"]
    dataset.attrs["frequency_Hz"] = int(data.sysconfig["kHz"]) * 1000  # kHz to hz
    dataset.attrs["bin_size_m"] = data.CellSize
    dataset.attrs["ping_per_ensemble"] = data.NPings
    dataset.attrs["ping_type"] = data.pingtype
    dataset.attrs["blank_m"] = data.Blank  # cm to m
    dataset.attrs["bin1dist_m"] = data.Bin1Dist

    dataset.attrs["firmware_version"] = ".".join(
        list(str(data.FL["FWV"])) + list(str(data.FL["FWR"]))
    )
    dataset.attrs["transmit_pulse_length_m"] = data.FL["Pulse"] / 100  # cm to m

    dataset.attrs["delta_t_sec"] = np.round(
        np.mean((np.diff(dataset.time).astype("timedelta64[s]"))).astype(float), 2
    )
    dataset.attrs["sampling_interval"] = str(dataset.attrs["delta_t_sec"]) + " seconds"

    dataset.attrs["beam_pattern"] = "convex" if data.sysconfig["convex"] else "concave"

    dataset.attrs["janus"] = "5-Beam" if sonar == "sv" else "4-Beam"

    dataset.attrs["magnetic_declination"] = "NA"
    if "FL" in data:
        if "EV" in data.FL:
            dataset.attrs["magnetic_declination"] = data.FL["EV"] / 100
    dataset.attrs["magnetic_declination_units"] = "degree east"

    dataset.attrs["orientation"] = orientation
    dataset.attrs["serial_number"] = (
        data.SerialNumber if "SerialNumber" in data else "NA"
    )
    l.log(f"File(s) loaded with {l.w_count} warnings")

    return dataset


def check_pd0_fixed_leader(
    filenames: tp.Union[str, tp.List[str]],
    sonar: str,
    yearbase: int = None,
    start_trim: int = None,
    end_trim: int = None,
) -> tp.Tuple[bool, int]:
    """Read Teledyne RDI binary FixedLeader.
    Returns the most common orientation and flag for an invalid config.

    Invalid config -> msb=`11111111` and lsb=`11111111`
    Using: rawfile().read() to get the FixedLeader for all  pings.

    Parameters
    ----------
    filenames:  Optional
        File(s) to read.
    sonar:  Optional
        sonar type passed to pycurrents.Multiread.
        ('nb', 'bb', 'wh', 'sv', or 'os')
    yearbase: Optional
        start year of the sampling.
    start_trim:  Optional
        Number of ensemble to cut from the start.
    end_trim:  Optional
        Number of ensemble to cut from the end.

    Returns
    -------
    upward_looking :
        True is the adcp is looking upward
    invalid_config_count :
        number of invalid configuration in the fixed leaders.


    Notes:
    ------
    Although the fixed_leader is supposed to be fixed, there is occurrence
    of change in the fixed_leader of some ping. A check up of some
    the fixed_leader parameters is done in the  processing.
    """
    # uses rawfile() to get the FixedLeader.
    if isinstance(filenames, list):
        fixed_leader = np.concatenate(
            [
                rawfile(fname=fname, sonar=sonar, yearbase=yearbase)
                .read(varlist=["FixedLeader"])
                .raw.FixedLeader
                for fname in filenames
            ]
        )
    else:
        fixed_leader = (
            rawfile(fname=filenames, sonar=sonar, yearbase=yearbase)
            .read(varlist=["FixedLeader"])
            .raw.FixedLeader
        )
    bad_config_value = 2 ** 16 - 1
    _up = int('10000000', 2)

    orientations = fixed_leader["SysCfg"][start_trim:-end_trim if end_trim else None] & _up
    upward_looking = np.mean(orientations) > 63

    invalid_config_count = np.sum(
        (fixed_leader["SysCfg"][start_trim:-end_trim if end_trim else None] == bad_config_value)
    )

    return upward_looking, invalid_config_count


def _get_time(
    dday: np.ndarray, yearbase: int, start_time: str = None, time_step: float = None
) -> tp.Union[np.ndarray, np.ndarray, bool]:
    """
    Parameters
    ----------
    yearbase :
        Year that the sampling started
    start_time :
        Format: 'YYYY-MM-DDThh:mm:ss.ssss'.
    time_step :
        Time step in seconds.
    """
    bad_dday = False
    if start_time is None:
        if (dday < 0).any():
            bad_dday = True
            l.warning(
                "The `dday` (time in fraction of days) vector in the adcp file had negative values."
            )
        elif (np.diff(dday) < 0).any():
            bad_dday = True
            l.warning(
                "The `dday` (time in fraction of days) was no monotonically increasing."
            )
        if bad_dday is True:
            l.log('`dday` values were added to the dataset.')
            start_time = str(dday_to_datetime64(dday[0], yearbase)[1])
            time_step = _get_time_step(dday)
            time, time_string = _make_time(start_time, len(dday), time_step)
        else:
            time, time_string = dday_to_datetime64(dday, yearbase)
    else:
        if time_step is None:
            time_step = _get_time_step(dday)
        else:
            time_step = pd.Timedelta(time_step,'seconds')
        time, time_string = _make_time(start_time, len(dday), time_step)

    return time, time_string, bad_dday


def _make_time(
    start_time: str, length: int, time_step: pd.Timedelta
) -> tp.Union[np.ndarray, np.ndarray]:
    """
    Parameters
    ----------
    start_time:
        Format 'YYYY-MM-DDThh:mm:ss.ssss'.
    length:
        Length of the time vector.
    time_step:
        Time step in seconds.
    """
    l.warning(
        f"Time vector was replace with a time series starting at {start_time} with {time_step.seconds} seconds time step."
    )
    time = pd.date_range(pd.Timestamp(start_time), periods=length, freq=time_step)
    return time, time.astype(str)


def _get_time_step(dday: np.ndarray) -> pd.Timedelta:
    """
    Parameters
    ----------
    dday
    Returns
    -------
    """
    time = dday * 86400
    deltas, counts = np.unique(np.round(np.diff(time), 4), return_counts=True)

    return pd.Timedelta(deltas[counts.argmax()], "seconds")