"""
This script has to functions to process and quick process adcp data.
These functions are called by the app command `process` and `quick adcp`.

Script to process adcp data. FIXME
- Load
- Global_attributes
- Quality_Control
- Encoding
- variables attributes
- Make Figure
- Make Logbook
- Export -> .nc or .odf

Notes
-----
-Unspecified attributes fill value is an empty string.
-`magnetic_declination`:
     declination of the magnetic north in `degree east`.

-`sensor_depth`:
     The `sensor_depth` value in the platform file is used to set the netcdf
     global attributes of the same name. However, the `sensor_depth` value in
     the ConfigFile is used to compute the bin depth coordinates.
     If no `sensor_depth` value is set in the Configfile, a value is computed from
     the XducerDepth.
     If no `sensor_depth` value is given in both the ConfigFile and platform file,
     the `sensor_depth` attributes is computed from the adcp `xducer_depth`.

-`chief_scientist`:
      The value in the ConfigFile is used over the one in the platform file.

-`sounding` :
     bt_depth data are used for the `sounding` attributes, taking precedent over the value given in
     the platform file. If the bottom data are shit, set the option keep_bt to False.

-`manufacturer` :
    The manufacturer is automatically added to the dataset by the loader. However, the value given in the platform file will
    overwrite it.

TODO TEST NAVIGATIN FILES !
FIXME DATA_TYPES: Missing for ship adcp
FIXME SOURCE : moored adcp ?

Notes
-----
Should be a class
"""

import getpass
import sys
import typing as tp
import click
import numpy as np
import pandas as pd
import xarray as xr
from magtogoek.adcp.loader import load_adcp_binary
from magtogoek.adcp.odf_exporter import make_odf
from magtogoek.adcp.quality_control import (adcp_quality_control,
                                            no_adcp_quality_control)
from magtogoek.adcp.tools import rotate_2d_vector
from magtogoek.attributes_formatter import (
    compute_global_attrs, format_variables_names_and_attributes)
from magtogoek.navigation import load_navigation
from magtogoek.utils import Logger, json2dict, format_str2list

l = Logger(level=0)

from pathlib import Path

TERMINAL_WIDTH = 80

STANDARD_ADCP_GLOBAL_ATTRIBUTES = {
    "sensor_type": "adcp",
    "featureType": "timeSeriesProfile",
}

GLOBAL_ATTRS_TO_DROP = [
    "sensor_type",
    "platform_type",
    "VAR_TO_ADD_SENSOR_TYPE",
    "P01_CODES",
    "xducer_depth",
    "sonar",
]
CONFIG_GLOBAL_ATTRS_SECTIONS = ["NETCDF_CF", "PROJECT", "CRUISE", "GLOBAL_ATTRIBUTES"]
PLATFORM_TYPES = ["buoy", "mooring", "ship"]
DEFAULT_PLATFORM_TYPE = "buoy"
DATA_TYPES = {"buoy": "MADCP", "mooring": "MADCP", "ship": "MADCP"}
PLATFORM_FILE_DEFAULT_KEYS = [
    "platform_type",
    "platform_subtype",
    "longitude",
    "latitude",
    "sounding",
    "sensor_depth",
    "serial_number",
    "manufacturer",
    "model",
    "firmware_version",
    "chief_scientist",
    "comments",
]
P01_VEL_CODES = dict(
    buoy=dict(
        u="LCEWAP01",
        v="LCNSAP01",
        w="LRZAAP01",
        e="LERRAP01",
        u_QC="LCEWAP01_QC",
        v_QC="LCNSAP01_QC",
        w_QC="LRZAAP01_QC",
    ),
    ship=dict(
        u="LCEWAS01",
        v="LCNSAS01",
        w="LRZAAS01",
        e="LERRAS01",
        u_QC="LCEWAS01_QC",
        v_QC="LCNSAS01_QC",
        w_QC="LRZAAS01_QC",
    ),
)
P01_VEL_CODES["mooring"] = P01_VEL_CODES["buoy"]
P01_CODES = dict(
    time="ELTMEP01",
    depth="PPSAADCP",
    pg="PCGDAP01",
    pg1="PCGDAP00",
    pg2="PCGDAP02",
    pg3="PCGDAP03",
    pg4="PCGDAP04",
    corr1="CMAGZZ01",
    corr2="CMAGZZ02",
    corr3="CMAGZZ03",
    corr4="CMAGZZ04",
    amp1="TNIHCE01",
    amp2="TNIHCE02",
    amp3="TNIHCE03",
    amp4="TNIHCE04",
    bt_u="APEWBT01",
    bt_v="APNSBT01",
    bt_w="APZABT01",
    bt_e="APERBT01",
    vb_vel="LRZUVP01",
    vb_vel_QC="LRZUVP01_QC",
    vb_pg="PCGDAP05",
    vb_cor="CMAGZZ05",
    vb_amp="TNIHCE05",
    lon="ALONZZ01",
    lat="ALATZZ01",
    heading="HEADCM01",
    roll_="ROLLGP01",
    pitch="PTCHGP01",
    u_ship="APEWGP01",
    v_ship="APNSGP01",
    pres="PRESPR01",
    pres_QC="PRESPR01_QC",
    temperature="TEMPPR01",
    temperature_QC="TEMPPR01_QC",
    xducer_depth="ADEPZZ01",
    time_string="DTUT8601",
    bt_depth="BATHDPTH",
)

VAR_TO_ADD_SENSOR_TYPE = ["TEMPPR01", "PRESPR01", "ADEPZZ01", "BATHDPTH"]

TIME_ATTRS = {"cf_role": "profile_id"}

TIME_ENCODING = {
    "units": "seconds since 1970-1-1 00:00:00Z",
    "calendar": "gregorian",
    "_FillValue": None,
}
TIME_STRING_ENCODING = {"dtype": "S1"}
DEPTH_ENCODING = {
    "_FillValue": -9999.0,
    "dtype": "float32",
}

DATE_STRING_FILL_VALUE = "17-NOV-1858 00:00:00.00"  # filled value used by ODF format
QC_FILL_VALUE = 127
QC_ENCODING = {"dtype": "int8", "_FillValue": QC_FILL_VALUE}

DATA_FILL_VALUE = -9999.0
DATA_ENCODING = {"dtype": "float32", "_FillValue": DATA_FILL_VALUE}


def process_adcp(config: dict):
    """Process adcp data with parameters from a ConfigFile.

    Pipes the params to _to_process_adcp_data which in turn pipes
    it to _process_adcp_data.

    Using `platform_id`, `sensor_id`, the sensor metadata are loaded
    into a dictionary and pass to _process_adcp_data.

    Notes
    -----
    missing `platform_type` :
        If the platform_type cannot be found, the function automatically default to
        `mooring` to set BODC P01 parameter codes.

    See Also
    --------
    _process_adcp_data :
        For the processing workflow.

    """
    params, global_attrs = _get_config(config)

    params["input_files"] = format_str2list(params["input_files"])

    if len(params["input_files"]) == 0:
        raise ValueError("No adcp file was provided in the configfile.")

    sensor_metadata = _default_platform()
    if params["platform_file"]:
        if Path(params["platform_file"]).is_file():
            sensor_metadata = _load_platform(params)
        else:
            l.warning(f"platform_file, {params['platform_file']}, not found")

    _pipe_to_process_adcp_data(params, sensor_metadata, global_attrs)


def quick_process_adcp(params: tp.Dict):
    """Process adcp data with quick_process options(params).

    Pipes the params to _to_process_adcp_data which in turn pipes
    it to _process_adcp_data.

    Notes
    -----
    missing `platform_type` :
        If the platform_type cannot be found, the function automatically default to
        `mooring` to set the correct BODC P01 parameter codes.

    See Also
    --------
    _process_adcp_data :
        For the processing workflow."""

    global_attrs = _default_global_attrs()
    sensor_metadata = _default_platform()

    sensor_metadata["platform_type"] = params["platform_type"]

    params["force_platform_metadata"] = False
    if params["odf_output"] in [1, "true", "True"]:
        params["odf_output"] = True

    _pipe_to_process_adcp_data(
        params, sensor_metadata, global_attrs, drop_empty_attrs=True
    )


def _pipe_to_process_adcp_data(
        params, sensor_metadata, global_attrs, drop_empty_attrs=False
):
    """Check if the input_file must be split in multiple output.

        Looks for `merge_output_files` in the ConfigFile and if False,
    each file in `input_files` is process individually and then call _process_adcp_data.
    """

    if not params["merge_output_files"]:
        netcdf_output = params["netcdf_output"]
        input_files = params["input_files"]
        for filename, count in zip(input_files, range(len(input_files))):
            if netcdf_output:
                if isinstance(netcdf_output, bool):
                    params["netcdf_output"] = filename
                else:
                    params["netcdf_output"] = (
                            str(Path(netcdf_output).name) + f"_{count}"
                    )
            params["input_files"] = [filename]

            _process_adcp_data(params, sensor_metadata, global_attrs, drop_empty_attrs)
    else:
        _process_adcp_data(params, sensor_metadata, global_attrs)


def _process_adcp_data(
        params: tp.Dict, sensor_metadata: tp.Dict, global_attrs, drop_empty_attrs=False
):
    """Process adcp data

    FIXME EXPLAIN THE PROCESSING WORKFLOW FIXME

    Meanwhile, the code is pretty explicit. Go check it out if need be.


    Parameters
    ----------
    params :
        Processing parameters from the ConfigFile.

    global_attrs :
        Global attributes parameter from the configFile.

    sensor_metadata :
        Metadata from the platform file.

    Notes
    -----
    `sensor_depth`:
        `sensor_depth` in the platform file is used for the variables attributes. If no
        value is given, it is computed from the XducerDepth. However, the `sensor_depth`
        value in the ConfigFile is used to compute the bin depth coordinates. If no
        `sensor_depth` value is given in both the ConfigFile and platform file, the
        `sensor_depth` attributes is computed from the adcp `Xducer_depth`.
    `fixed_sensor_depth`:
        Set all XducerDepth value to `fixed_sensor_depth`.
    Raises
    ------
    ValueError :
        `platform_type` value in the platform file must be either 'mooring' or 'ship'.

    """
    l.reset()

    _check_platform_type(sensor_metadata)

    # ----------------- #
    # LOADING ADCP DATA #
    # ----------------- #

    dataset = _load_adcp_data(params)

    # ----------------------------------------- #
    # ADDING THE NAVIGATION DATA TO THE DATASET #
    # ----------------------------------------- #
    if params["navigation_file"]:
        l.section("Navigation data")
        dataset = _load_navigation(dataset, params["navigation_file"])

    # ----------------------------- #
    # ADDING SOME GLOBAL ATTRIBUTES #
    # ----------------------------- #

    dataset = dataset.assign_attrs(STANDARD_ADCP_GLOBAL_ATTRIBUTES)

    dataset.attrs["data_type"] = DATA_TYPES[sensor_metadata["platform_type"]]

    if sensor_metadata["longitude"]:
        dataset.attrs["longitude"] = sensor_metadata["longitude"]
    if sensor_metadata["latitude"]:
        dataset.attrs["latitude"] = sensor_metadata["latitude"]

    compute_global_attrs(dataset)

    if sensor_metadata["platform_type"] in ["mooring", "buoy"]:
        if "bt_depth" in dataset:
            dataset.attrs["sounding"] = np.round(np.median(dataset.bt_depth.data), 2)

    # if not params["force_platform_metadata"]: # Note Probably useless.
    _set_xducer_depth_as_sensor_depth(dataset)

    # setting Metadata from the platform_file
    _set_platform_metadata(dataset, sensor_metadata, params["force_platform_metadata"])

    # setting Metadata from the config_files
    dataset = dataset.assign_attrs(global_attrs)

    if not dataset.attrs["source"]:
        dataset.attrs["source"] = sensor_metadata["platform_type"]

    # ----------------------------------- #
    # CORRECTION FOR MAGNETIC DECLINATION #
    # ----------------------------------- #

    l.section("Data transformation")

    dataset.attrs["magnetic_declination"] = 0
    dataset.attrs["magnetic_declination_units"] = "degree east"
    if params["magnetic_declination"]:
        angle = params["magnetic_declination"]
        if dataset.attrs["magnetic_declination"]:
            l.log(f"Magnetic declination found in adcp file: {dataset.attrs['magnetic_declination']} degree east.")
            angle = round((params["magnetic_declination"] - dataset.attrs["magnetic_declination"]), 4)
            l.log(f"An additional correction of {angle} degree east was carried out.")
        _magnetic_correction(dataset, angle)
        dataset.attrs["magnetic_declination"] = params["magnetic_declination"]

    # --------------- #
    # QUALITY CONTROL #
    # --------------- #

    dataset.attrs["logbook"] += l.logbook

    if params["quality_control"]:
        _quality_control(dataset, params)
    else:
        no_adcp_quality_control(dataset, )

    l.reset()

    if any(
            params["drop_" + var] for var in ("percent_good", "correlation", "amplitude")
    ):
        dataset = _drop_beam_data(dataset, params)

    # -------------- #
    # DATA ENCONDING #
    # -------------- #

    _format_data_encoding(dataset)

    # -------------------- #
    # VARIABLES ATTRIBUTES #
    # -------------------- #
    dataset.attrs["VAR_TO_ADD_SENSOR_TYPE"] = VAR_TO_ADD_SENSOR_TYPE
    dataset.attrs["P01_CODES"] = {
        **P01_VEL_CODES[sensor_metadata["platform_type"]],
        **P01_CODES,
    }

    l.section("Variables attributes")
    dataset = format_variables_names_and_attributes(
        dataset, use_bodc_codes=params["bodc_name"]
    )

    dataset["time"].assign_attrs(TIME_ATTRS)

    l.log("Variables attributes added.")

    # ------------------------------------ #
    # FINAL FORMATING OF GLOBAL ATTRIBUTES #
    # ------------------------------------ #

    if "platform_name" in dataset.attrs:
        dataset.attrs["platform"] = dataset.attrs.pop("platform_name")

    if not dataset.attrs["date_created"]:
        dataset.attrs["date_created"] = pd.Timestamp.now().strftime("%Y-%m-%d")

    dataset.attrs["date_modified"] = pd.Timestamp.now().strftime("%Y-%m-%d")

    dataset.attrs["logbook"] += l.logbook

    dataset.attrs["history"] = dataset.attrs["logbook"]
    del dataset.attrs["logbook"]

    for attr in GLOBAL_ATTRS_TO_DROP:
        if attr in dataset.attrs:
            del dataset.attrs[attr]

    for attr in list(dataset.attrs.keys()):
        if not dataset.attrs[attr]:
            if drop_empty_attrs:
                del dataset.attrs[attr]
            else:
                dataset.attrs[attr] = ""

    # ------- #
    # OUTPUTS #
    # ------- #
    l.section("Output")
    log_output = params["input_files"][0]
    if params["odf_output"]:
        if params["bodc_name"]:
            generic_to_p01_name = P01_VEL_CODES[sensor_metadata["platform_type"]]
        else:
            generic_to_p01_name = None

        odf = make_odf(dataset, sensor_metadata, global_attrs, generic_to_p01_name)

        if params["odf_output"] is True:
            odf_output = (
                odf.odf["file_specification"]
                if odf.odf["file_specification"]
                else params["input_files"][0]
            )

        else:
            odf_output = params["odf_output"]

        odf_output = Path(odf_output).with_suffix(".ODF")
        if odf_output.is_dir():
            odf_output.joinpath(Path(odf.odf["file_specification"]))
        else:
            odf.odf["file_specification"] = odf_output.name

        odf.save(odf_output)
        l.log(f"odf file made -> {odf_output}")
        log_output = odf_output

    elif not params["netcdf_output"]:
        params["netcdf_output"] = True

    if params["netcdf_output"]:
        nc_output = params["netcdf_output"]
        if isinstance(params["netcdf_output"], bool):
            nc_output = params["input_files"][0]
        nc_output = Path(nc_output).with_suffix(".nc")
        dataset.to_netcdf(nc_output)
        l.log(f"netcdf file made -> {nc_output}")
        log_output = nc_output

    if params["make_log"]:
        log_output = Path(log_output).with_suffix(".log")
        with open(log_output, "w") as log_file:
            log_file.write(dataset.attrs["history"])
            print(f"log file made -> {log_output}")

    # MAKE_FIG TODO

    click.echo(click.style("=" * TERMINAL_WIDTH, fg="white", bold=True))


def _load_adcp_data(params: tp.Dict) -> xr.Dataset:
    """
    Load and trim the adcp data into a xarray.Dataset.
    Drops bottom track data if params `keep_bt` is False.
    """
    start_time, leading_index = _get_datetime_and_count(params["leading_trim"])
    end_time, trailing_index = _get_datetime_and_count(params["trailing_trim"])

    dataset = load_adcp_binary(
        filenames=params["input_files"],
        yearbase=params["yearbase"],
        sonar=params["sonar"],
        leading_index=leading_index,
        trailing_index=trailing_index,
        orientation=params["adcp_orientation"],
        sensor_depth=params["sensor_depth"],
        depth_range=params["depth_range"],
        bad_pressure=params["bad_pressure"],
    )

    if start_time > dataset.time.max() or end_time < dataset.time.min():
        l.warning("Triming datetimes out of bounds. Time slicing aborted.")
    else:
        dataset = dataset.sel(time=slice(start_time, end_time))

    l.log(
        (
                f"Bins count : {len(dataset.depth.data)}, "
                + f"Min depth : {np.round(dataset.depth.min().data, 3)} m, "
                + f"Max depth : {np.round(dataset.depth.max().data, 3)} m"
        )
    )
    l.log(
        (
                f"Ensembles count : {len(dataset.time.data)}, "
                + f"Start time : {np.datetime_as_string(dataset.time.min().data, unit='s')}, "
                + f"End time : {np.datetime_as_string(dataset.time.max().data, unit='s')}"
        )
    )
    if not params["keep_bt"]:
        dataset = _drop_bottom_track(dataset)

    return dataset


def _get_config(config: dict) -> tp.Tuple[dict, dict]:
    """Split and flattens the config in two untested dictionary"""
    params = dict()
    global_attrs = dict()
    for section, options in config.items():
        if section in CONFIG_GLOBAL_ATTRS_SECTIONS:
            for option in options:
                global_attrs[option] = config[section][option]
        else:
            for option in options:
                params[option] = config[section][option]

    return params, global_attrs


def _load_platform(params: dict) -> tp.Dict:
    """load sensor metadata into dict

    Returns a `flat` dictionary with all the parents metadata
    to `platform.json/platform_id/sensors/sensor_id` and the
    metadata of the `sensor_id.`
    """
    sensor_metadata = dict()
    json_dict = json2dict(params["platform_file"])
    if params["platform_id"] in json_dict:
        platform_dict = json_dict[params["platform_id"]]
        if "sensors" in platform_dict:
            if params["sensor_id"] in platform_dict["sensors"]:
                sensor_metadata = platform_dict["sensors"][params["sensor_id"]]
            else:
                l.warning(
                    f"{params['sensor_id']} not found in {params['platform_id']}['sensor'] of the platform file."
                )
        else:
            l.warning("`sensors` section missing from the platform file")
        for key in platform_dict.keys():
            if key != "sensors":
                sensor_metadata[key] = platform_dict[key]
    else:
        l.warning(f"{params['platform_id']} not found in platform file.")
        sensor_metadata = None
    return sensor_metadata


def _default_platform() -> dict:
    """Return an empty platform data dictionnary"""
    sensor_metadata = dict()
    for key in PLATFORM_FILE_DEFAULT_KEYS:  # FIXME make in from paltform.p y
        sensor_metadata[key] = None
    sensor_metadata["buoy_specs"] = dict()
    sensor_metadata["platform_type"] = DEFAULT_PLATFORM_TYPE
    return sensor_metadata


def _default_global_attrs():
    """Return default global_attrs()"""
    return {
        "date_created": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "publisher_name": getpass.getuser(),
        "source": "adcp",
    }


def _check_platform_type(sensor_metadata: dict):
    """DEFINED BELOW"""
    if sensor_metadata["platform_type"] not in PLATFORM_TYPES:
        sensor_metadata["platform_type"] = DEFAULT_PLATFORM_TYPE
        l.warning(
            f"platform_file missing or invalid, defaulting to `{DEFAULT_PLATFORM_TYPE}` for platform_type."
        )
        l.warning(f"platform_type invalid. Must be one of {PLATFORM_TYPES}")


_check_platform_type.__doc__ = f"""Check if the `platform_type` is valid.
    `platform _type` must be one of {PLATFORM_TYPES}.
    `platform_type` defaults to {DEFAULT_PLATFORM_TYPE} if the one given is invalid."""


def _set_xducer_depth_as_sensor_depth(dataset: xr.Dataset):
    """Set xducer_depth value to dataset attributes sensor_depth"""
    if "xducer_depth" in dataset.attrs:  # OCEAN SURVEYOR
        dataset.attrs["sensor_depth"] = dataset.attrs["xducer_depth"]

    if "xducer_depth" in dataset:
        dataset.attrs["sensor_depth"] = np.round(
            np.median(dataset["xducer_depth"].data), 2
        )


def _set_platform_metadata(
        dataset: xr.Dataset,
        sensor_metadata: dict,
        force_platform_metadata: bool = False,
):
    """Add metadata from platform_metadata files to dataset.attrs.

    Values that are dictionary instances are not added.

    Parameters
    ----------
    dataset :
        Dataset to which add the navigation data.
    sensor_metadata :
        metadata returned by  _load_platform
    force_platform_metadata :
        If `True`, metadata from sensor_metadata overwrite those already present in dataset.attrs
    """
    metadata_key = []
    for key, value in sensor_metadata.items():
        if value and not isinstance(value, dict):
            metadata_key.append(key)

    if force_platform_metadata:
        for key in metadata_key:
            dataset.attrs[key] = sensor_metadata[key]
        if "sensor_depth" in metadata_key:
            l.log(
                f"`sensor_depth` value ({sensor_metadata['sensor_depth']} was set by the user."
            )

    else:
        for key in metadata_key:
            if key in dataset.attrs:
                if not dataset.attrs[key]:
                    dataset.attrs[key] = sensor_metadata[key]
            else:
                dataset.attrs[key] = sensor_metadata[key]


def _load_navigation(dataset: xr.Dataset, navigation_files: str):
    """Load navigation data from nmea, gpx or netcdf files.

    Returns the dataset with the added navigation data. Data from the navigation file
    are interpolated on the dataset time vector.

    Parameters
    ----------
    dataset :
        Dataset to which add the navigation data.

    navigation_files :
        nmea(ascii), gpx(xml) or netcdf files containing the navigation data. For the
        netcdf file, variable must be `lon`, `lat` and the coordinates `time`.

    Notes
    -----
        Using the magtogoek function `mtgk compute nav`, u_ship, v_ship can be computed from `lon`, `lat`
    data to correct the data for the platform motion by setting the config parameter `m_corr` to `nav`.
    """
    nav_ds = load_navigation(navigation_files).interp(time=dataset.time)
    dataset = xr.merge((dataset, nav_ds), combine_attrs="no_conflicts")
    return dataset


def _quality_control(dataset: xr.Dataset, params: tp.Dict):
    """Carries quality control.

    Wrapper for adcp_quality_control"""

    adcp_quality_control(dataset=dataset, amp_th=params["amplitude_threshold"], corr_th=params["correlation_threshold"],
                         pg_th=params["percentgood_threshold"], roll_th=params["roll_threshold"],
                         pitch_th=params["pitch_threshold"], horizontal_vel_th=params["horizontal_velocity_threshold"],
                         vertical_vel_th=params["vertical_velocity_threshold"],
                         error_vel_th=params["error_velocity_threshold"],
                         motion_correction_mode=params["motion_correction_mode"],
                         sidelobes_correction=params["sidelobes_correction"], bottom_depth=params["bottom_depth"])


def _magnetic_correction(dataset: xr.Dataset, magnetic_declination: float):
    """Transform velocities and heading to true north and east.

    Rotates velocities and heading by the given `magnetic_declination` angle.

    Parameters
    ----------
    dataset :
      dataset containing variables (u, v) (required) and (bt_u, bt_v) (optional).
    magnetic_declination :
        angle in decimal degrees measured in the geographic frame of reference.
    """

    dataset.u.values, dataset.v.values = rotate_2d_vector(
        dataset.u, dataset.v, magnetic_declination
    )
    l.log(f"Velocities transformed to true north and true east.")
    if all(v in dataset for v in ['bt_u', 'bt_v']):
        dataset.bt_u.values, dataset.bt_v.values = rotate_2d_vector(
            dataset.bt_u, dataset.bt_v, magnetic_declination
        )
        l.log(f"Bottom velocities transformed to true north and true east.")

    # heading goes from -180 to 180
    if "heading" in dataset:
        dataset.heading.values = (
                                         dataset.heading.data + 360 + magnetic_declination
                                 ) % 360 - 180
        l.log(f"Heading transformed to true north.")


def _get_datetime_and_count(trim_arg: str):
    """Get datetime and count from trim_arg.

    If `trim_arg` is None, returns (None, None)
    If 'T' is a datetime or a count returns (Timestamp(trim_arg), None)
    Else returns (None, int(trim_arg))

    Returns:
    --------
    datetime:
        None or pandas.Timestamp
    count:
        None or int

    """
    if trim_arg:
        if not trim_arg.isdecimal():
            try:
                return pd.Timestamp(trim_arg), None
            except ValueError:
                print("Bad datetime format for trim. Use YYYY-MM-DDTHH:MM:SS.ssss")
                print("Process aborted")
                sys.exit()
        else:
            return None, int(trim_arg)
    else:
        return None, None


def _drop_beam_data(dataset: xr.Dataset, params: tp.Dict):
    """check in params if pg, corr and amp are to be dropped
    (drop_pg, drop_corr, drop_amp)

    """
    for var in [
        ("pg", "percent_good"),
        ("corr", "correlation"),
        ("amp", "amplitude"),
    ]:
        if params[f"drop_{var[1]}"]:
            for i in ["", "1", "2", "3", "4"]:
                if var[0] + i in dataset:
                    dataset = dataset.drop_vars([var[0] + i])
            l.log(f"{var[1]} data dropped.")

    return dataset


def _format_data_encoding(dataset: xr.Dataset):
    """Format data encoding with default value in module."""
    l.section("Data Encoding")
    for var in dataset.variables:
        if var == "time":
            dataset.time.encoding = TIME_ENCODING
        elif var == "depth":
            dataset.depth.encoding = DEPTH_ENCODING
        elif "_QC" in var:
            dataset[var].values = dataset[var].values.astype("int8")
            dataset[var].encoding = QC_ENCODING
        elif var == "time_string":
            dataset[var].encoding = TIME_STRING_ENCODING
        else:
            dataset[var].encoding = DATA_ENCODING

    l.log(f"Data _FillValue: {DATA_FILL_VALUE}")
    l.log(f"Ancillary Data _FillValue: {QC_FILL_VALUE}")


def _drop_bottom_track(dataset):
    "Drop `bt_u`, `bt_v`, `bt_w`, `bt_e`, `bt_depth`"
    for var in ["bt_u", "bt_v", "bt_w", "bt_e", "bt_depth"]:
        if var in dataset:
            dataset = dataset.drop_vars([var])
