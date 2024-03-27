"""This script contains the functions to process adcp data.

    These functions are called by the app command `process` (magtogoek.app)

    Use the function: magtogoek.config_handler.get_config_taskparser(process = 'adcp').as_dict() to get a config to
    input to magtogoek.adcp.process.process_adcp_data(config). Replace the following value in the `config` the
    appropriate value:
        -config['INPUT']['input_files']: str or list(str) = 'path/to/file'

Script to process adcp data. # NOTE maybe no up to date
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
    The manufacturer is automatically added to the dataset by the loader. However, the value given in the platform file
    will overwrite it.



Notes
-----
Note DATA_TYPES: Missing for ship adcp. Set to adcp for now
FIXME SOURCE : moored adcp ?
"""


import typing as tp

import numpy as np
import xarray as xr

import magtogoek.logger as l
from magtogoek.platforms import PlatformMetadata
from magtogoek.adcp.plots import make_adcp_figure
from magtogoek.adcp.loader import load_adcp_binary
from magtogoek.adcp.correction import apply_motion_correction, apply_magnetic_correction
from magtogoek.adcp.odf_exporter import make_odf
from magtogoek.adcp.quality_control import (adcp_quality_control,
                                            no_adcp_quality_control)
from magtogoek.adcp.transform import coordsystem2earth
from magtogoek.attributes_formatter import format_variables_names_and_attributes, _add_data_min_max_to_var_attrs
from magtogoek.process_common import BaseProcessConfig, resolve_output_paths, add_global_attributes, \
    write_log, write_netcdf, netcdf_raw_exist, load_netcdf_raw, write_netcdf_raw, \
    add_processing_timestamp, clean_dataset_for_nc_output, format_data_encoding, add_navigation, add_platform_metadata_to_dataset
from magtogoek.tools import (
    regrid_dataset, _prepare_flags_for_regrid, _new_flags_bin_regrid,
    _new_flags_interp_regrid, cut_bin_depths, cut_times)

l.get_logger('adcp_processing')

STANDARD_GLOBAL_ATTRIBUTES = {
    "featureType": "timeSeriesProfile",
}

VARIABLES_TO_DROP = [
    "binary_mask"
]
GLOBAL_ATTRS_TO_DROP = [
    "xducer_depth",
    "sonar",
    "binary_mask_tests",
    "binary_mask_tests_values",
]

BEAM_VEL_CODES = { # BODC REAL CODE NOT FOUND
    'v1': 'vel_beam_1',
    'v2': 'vel_beam_2',
    'v3': 'vel_beam_3',
    'v4': 'vel_beam_4',
    'v1_QC': 'vel_beam_1_QC',
    'v2_QC': 'vel_beam_2_QC',
    'v3_QC': 'vel_beam_3_QC',
    'v4_QC': 'vel_beam_4_QC',
    'bt_v1': 'bt_vel_beam_1',
    'bt_v2': 'bt_vel_beam_2',
    'bt_v3': 'bt_vel_beam_3',
    'bt_v4': 'bt_vel_beam_4'
}

XYZ_VEL_CODES = { # BODC REAL CODE NOT FOUND
    'u': 'vel_x_axis',
    'v': 'vel_y_axis',
    'w': 'vel_z_axis',
    'u_QC': "vel_x_axis_QC",
    'v_QC': "vel_y_axis_QC",
    'w_QC': "vel_z_axis_QC",
    'bt_u': 'bt_vel_x_axis',
    'bt_v': 'bt_vel_y_axis',
    'bt_w': 'bt_vel_z_axis'
}

P01_VEL_CODES = {
    'lowered': {
        'u': "LCEWLW01",
        'v': "LCNSLW01",
        'w': "LRZALW01",
        'e': "ERRVLDCP",
        'u_QC': "LCEWAP01_QC",
        'v_QC': "LCNSAP01_QC",
        'w_QC': "LRZAAP01_QC"
    },
    'buoy': {
        'u': "LCEWAP01",
        'v': "LCNSAP01",
        'w': "LRZAAP01",
        'e': "LERRAP01",
        'u_QC': "LCEWAP01_QC",
        'v_QC': "LCNSAP01_QC",
        'w_QC': "LRZAAP01_QC"
    },
    'mooring': {
        'u': "LCEWAP01",
        'v': "LCNSAP01",
        'w': "LRZAAP01",
        'e': "LERRAP01",
        'u_QC': "LCEWAP01_QC",
        'v_QC': "LCNSAP01_QC",
        'w_QC': "LRZAAP01_QC"
    },
    'ship': {
        'u': "LCEWAS01",
        'v': "LCNSAS01",
        'w': "LRZAAS01",
        'e': "LERRAS01",
        'u_QC': "LCEWAS01_QC",
        'v_QC': "LCNSAS01_QC",
        'w_QC': "LRZAAS01_QC"
    }
}

P01_CODES_MAP = {
    'time': "ELTMEP01",
    'depth': "PPSAADCP",
    'pg': "PCGDAP01",
    'pg1': "PCGDAP00",
    'pg2': "PCGDAP02",
    'pg3': "PCGDAP03",
    'pg4': "PCGDAP04",
    'corr1': "CMAGZZ01",
    'corr2': "CMAGZZ02",
    'corr3': "CMAGZZ03",
    'corr4': "CMAGZZ04",
    'amp1': "TNIHCE01",
    'amp2': "TNIHCE02",
    'amp3': "TNIHCE03",
    'amp4': "TNIHCE04",
    'bt_u': "LCEWBT01",
    'bt_v': "LCNSBT01",
    'bt_w': "LRZABT01",
    'bt_e': "LERRBT01",
    'vb_vel': "LRZUVP01",
    'vb_vel_QC': "LRZUVP01_QC",
    'vb_pg': "PCGDAP05",
    'vb_cor': "CMAGZZ05",
    'vb_amp': "TNIHCE05",
    'lon': "ALONZZ01",
    'lat': "ALATZZ01",
    'heading': "HEADCM01",
    'roll_': "ROLLGP01",
    'pitch': "PTCHGP01",
    'u_ship': "APEWZZ01",
    'v_ship': "APNSZZ01",
    'pres': "PRESPR01",
    'pres_QC': "PRESPR01_QC",
    'temperature': "TEMPPR01",
    'temperature_QC': "TEMPPR01_QC",
    'xducer_depth': "ADEPZZ01",
    'time_string': "DTUT8601",
    'bt_depth': "BATHDPTH"
}

VARIABLES_TO_ADD_SENSOR_METADATA = [
    'v1',
    'v2',
    'v3',
    'v4',
    'v1_QC',
    'v2_QC',
    'v3_QC',
    'v4_QC',
    'bt_v1',
    'bt_v2',
    'bt_v3',
    'bt_v4',
    'u',
    'v',
    'w',
    'e',
    'bt_u',
    'bt_v',
    'bt_w',
    'bt_e',
    'pg',
    'pg1',
    'pg2',
    'pg3',
    'pg4',
    'corr1',
    'corr2',
    'corr3',
    'corr4',
    'amp1',
    'amp2',
    'amp3',
    'amp4',
    'vb_vel',
    'vb_pg',
    'vb_cor',
    'vb_amp',
    'temperature',
    'pres',
    'xducer_depth',
    'bt_depth'
]


class ProcessConfig(BaseProcessConfig):
    adcp_id: str = None
    yearbase: int = None
    adcp_orientation: str = None
    sonar: str = None

    sensor_depth: float = None
    depth_range: list = None
    magnetic_declination: float = None
    magnetic_declination_preset: float = None
    keep_bt: bool = None
    bad_pressure: bool = None
    start_time: str = None
    time_step: float = None
    quality_control: bool = None

    coord_transform: bool = None
    motion_correction_mode: str = None

    amplitude_threshold: int = None
    percentgood_threshold: int = None
    correlation_threshold: int = None
    horizontal_velocity_threshold: float = None
    vertical_velocity_threshold: float = None
    error_velocity_threshold: float = None
    pitch_threshold: float = None
    roll_threshold: float = None

    sidelobes_correction: bool = None
    bottom_depth: float = None

    drop_percent_good: bool = None
    drop_correlation: bool = None
    drop_amplitude: bool = None

    grid_depth: tp.Union[str, bool] = None
    grid_method: str = None

    def __init__(self, config_dict: dict = None):
        super().__init__(config_dict)
        self.p01_codes_map = P01_CODES_MAP

        self.variables_to_drop = VARIABLES_TO_DROP
        self.global_attributes_to_drop = GLOBAL_ATTRS_TO_DROP


def process_adcp(config: dict, drop_empty_attrs: bool = False,
                 headless: bool = False, from_raw: bool = False):
    """Process adcp data with parameters from a config file.

    If `pconfig.merge_output_files` is False, each input file is process individually.

    Parameters
    ----------
    config :
        Dictionary make from a configfile (see config_handler.load_config).
    drop_empty_attrs :
        If true, all netcdf empty ('') global attributes will be dropped from
        the output.
    headless :
        If true, figures are not displayed but are saved in the output directory.
    from_raw :
        If true, data is loaded from the raw files (input_files).

    The actual data processing is carried out by _process_adcp_data.
    """
    l.reset()

    pconfig = ProcessConfig(config)
    pconfig.drop_empty_attrs = drop_empty_attrs
    pconfig.headless = headless
    pconfig.from_raw = from_raw

    _process_adcp_data(pconfig)


@resolve_output_paths
def _process_adcp_data(pconfig: ProcessConfig):
    """Process adcp data
;
    This is not good documentation...
    However, the code is pretty explicit. Go check it out if need be.

    Notes
    -----
    pconfig.sensor_depth`:
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
    # ----------------- #
    # LOADING ADCP DATA #
    # ----------------- #

    dataset = _load_adcp_data(pconfig)

    # ----------------------------------------- #
    # ADDING THE NAVIGATION DATA TO THE DATASET #
    # ----------------------------------------- #
    if pconfig.navigation_file:
        l.section("Navigation data")
        add_navigation(dataset, pconfig.navigation_file)

    # -------------- #
    # TRANSFORMATION #
    # -------------- #
    l.section('Data Transformation')

    if dataset.attrs['coord_system'] != 'earth' and pconfig.coord_transform is True:
        dataset = _coordinate_system_transformation(dataset)
    else:
        l.log('Nothing to do')

    # ---------- #
    # CORRECTION #
    # ---------- #
    l.section("Data Correction")

    # magnetic declination #
    if dataset.attrs['magnetic_declination'] != "NA":
        l.log(f"Magnetic declination found in the raw file: {dataset.attrs['magnetic_declination']} degree east.")
    else:
        l.log(f"No magnetic declination found in the raw file.")

    # >>>> ADCP SPECIFIC
    if pconfig.magnetic_declination is not None:
        #if dataset.attrs['coord_system'] == 'earth':
        apply_magnetic_correction(dataset, pconfig.magnetic_declination)
        #else:
        #    l.warning('Correction for magnetic declination was not carried out since '
        #              'the velocity data are not in earth coordinates.')

    # motion correction #
    if pconfig.motion_correction_mode in ["bt", "nav"]:
        apply_motion_correction(dataset, pconfig.motion_correction_mode)
    # <<<<

    # --------------- #
    # QUALITY CONTROL #
    # --------------- #

    if pconfig.quality_control:
        _quality_control(dataset, pconfig)
    else:
        no_adcp_quality_control(dataset)

    # >>>> ADCP SPECIFIC
    dataset = _drop_beam_metadata(dataset, pconfig)  # needs to be done before renaming the variables.
    # <<<<

    # ------------------------ #
    # ADDING GLOBAL ATTRIBUTES #
    # ------------------------ #

    l.section("Adding Global Attributes")

    add_global_attributes(dataset, pconfig, STANDARD_GLOBAL_ATTRIBUTES)

    add_platform_metadata_to_dataset(dataset=dataset, pconfig=pconfig)

    # >>>> ADCP SPECIFIC
    if pconfig.platform_type in ["mooring", "buoy"]:
        if "bt_depth" in dataset:
            dataset.attrs["sounding"] = np.round(np.median(dataset.bt_depth.data), 2)

    dataset.attrs['sensor_type'] = 'adcp'

    _set_xducer_depth_as_sensor_depth(dataset)

    _add_platform_adcp_metadata_to_dataset(dataset, pconfig)
    # <<<<

    # ------------- #
    # DATA ENCODING #
    # ------------- #
    l.section("Data Encoding")

    format_data_encoding(dataset)

    # -------------------- #
    # VARIABLES ATTRIBUTES #
    # -------------------- #
    l.section("Variables attributes")

    # >>>> ADCP SPECIFIC
    _update_p01_codes_map(dataset, pconfig)
    # <<<<

    dataset = format_variables_names_and_attributes(
        dataset=dataset,
        use_bodc_name=pconfig.use_bodc_name,
        p01_codes_map=pconfig.p01_codes_map,
        cf_profile_id='time'
    )

    # >>>> ADCP SPECIFIC
    _add_platform_adcp_metadata_to_variables(dataset, pconfig, VARIABLES_TO_ADD_SENSOR_METADATA)

    _add_sensor_metadata_to_variables(dataset, VARIABLES_TO_ADD_SENSOR_METADATA)
    # <<<<

    # ------------ #
    # MAKE FIGURES #
    # ------------ #
    if pconfig.figures_output is True:
        make_adcp_figure(dataset, flag_thres=2, save_path=pconfig.figures_path, show_fig=not pconfig.headless)

    # --------------- #
    # POST-PROCESSING #
    # --------------- #
    l.section("Post-processing")
    if pconfig.grid_depth is not None:
        dataset = _regrid_dataset(dataset, pconfig)

    # ---------- #
    # ODF OUTPUT #
    # ---------- #

    l.section("Output")
    if pconfig.odf_output is True:
        _write_odf(dataset, pconfig)

    # ----------------- #
    # NETCDF FORMATTING #
    # ------------------#

    add_processing_timestamp(dataset)

    dataset = clean_dataset_for_nc_output(dataset, pconfig)

    dataset.attrs["history"] = l.logbook

    # ------------- #
    # NETCDF OUTPUT #
    # ------------- #
    if pconfig.netcdf_output is True:
        write_netcdf(dataset, pconfig)

    # ---------- #
    # LOG OUTPUT #
    # ---------- #

    if pconfig.make_log is True:
        write_log(pconfig)


def _load_adcp_data(pconfig: ProcessConfig) -> xr.Dataset:
    """
    Load and trim the adcp data into a xarray.Dataset.
    Drops bottom track data if `keep_bt` is False.
    """
    if netcdf_raw_exist(pconfig) and pconfig.from_raw is not True:
        dataset = load_netcdf_raw(pconfig)
    else:
        dataset = load_adcp_binary(
            filenames=pconfig.input_files,
            yearbase=pconfig.yearbase,
            sonar=pconfig.sonar,
            start_trim=pconfig.start_trim_index,
            end_trim=pconfig.end_trim_index,
            orientation=pconfig.adcp_orientation,
            sensor_depth=pconfig.sensor_depth,
            bad_pressure=pconfig.bad_pressure,
            start_time=pconfig.start_time,
            time_step=pconfig.time_step,
            magnetic_declination_preset=pconfig.magnetic_declination_preset,
        )

        write_netcdf_raw(dataset=dataset, pconfig=pconfig)

    dataset = cut_bin_depths(dataset, pconfig.depth_range)

    dataset = cut_times(dataset, pconfig.start_trim_time, pconfig.end_trim_time)

    l.log(
        (
                f"Bin counts : {len(dataset.depth.data)}, "
                + f"Min depth : {np.round(dataset.depth.min().data, 3)} m, "
                + f"Max depth : {np.round(dataset.depth.max().data, 3)} m, "
                + f"Bin size : {dataset.attrs['bin_size_m']} m"
        )
    )
    l.log(
        (
                f"Ensemble counts : {len(dataset.time.data)}, "
                + f"Start time : {np.datetime_as_string(dataset.time.min().data, unit='s')}, "
                + f"End time : {np.datetime_as_string(dataset.time.max().data, unit='s')}"
        )
    )
    if not pconfig.keep_bt:
        dataset = _drop_bottom_track(dataset)

    return dataset


def _coordinate_system_transformation(dataset: xr.Dataset):
    """
    """
    if dataset.attrs['coord_system'] not in ["beam", "xyz"]:
        l.log(f"Coordsystem value of {dataset.attrs['coord_system']} not recognized. "
              f"Conversion to enu not available.")
    else:
        l.warning('Coordinate transformation methods are taken from Pycurrents and seems to work. '
                  'However, no rigorous testing was done.')
        dataset = coordsystem2earth(dataset)
    return dataset


def _quality_control(dataset: xr.Dataset, pconfig: ProcessConfig):
    """Carries quality control.

    Wrapper for adcp_quality_control"""

    adcp_quality_control(
        dataset=dataset,
        amp_th=pconfig.amplitude_threshold,
        corr_th=pconfig.correlation_threshold,
        pg_th=pconfig.percentgood_threshold,
        roll_th=pconfig.roll_threshold,
        pitch_th=pconfig.pitch_threshold,
        horizontal_vel_th=pconfig.horizontal_velocity_threshold,
        vertical_vel_th=pconfig.vertical_velocity_threshold,
        error_vel_th=pconfig.error_velocity_threshold,
        sidelobes_correction=pconfig.sidelobes_correction,
        bottom_depth=pconfig.bottom_depth,
        bad_pressure=pconfig.bad_pressure
    )


def _set_xducer_depth_as_sensor_depth(dataset: xr.Dataset):
    """Set xducer_depth value to dataset global attributes sensor_depth
    """
    if "xducer_depth" in dataset.attrs:  # OCEAN SURVEYOR
        dataset.attrs["sensor_depth"] = dataset.attrs["xducer_depth"]

    if "xducer_depth" in dataset.variables:  # dataset -> dataset.variables (same but more readable)
        dataset.attrs["sensor_depth"] = np.round(
            np.median(dataset["xducer_depth"].data), 2
        )

    dataset.attrs["sensor_depth_units"] = "meters"


def _add_platform_adcp_metadata_to_dataset(dataset: xr.Dataset, pconfig: ProcessConfig):
    """Add sensor metadata found in the platform instrument to the dataset

    Overwrites global_attributes if pconfig.force_platform_metadata is True.
    """
    if pconfig.platform_metadata is not None:
        if pconfig.adcp_id in pconfig.platform_metadata.instruments:
            instrument_metadata = {
                    'sensor_type': pconfig.platform_metadata.instruments[pconfig.adcp_id].sensor_type,
                    'sensor_height': pconfig.platform_metadata.instruments[pconfig.adcp_id].sensor_height,
                    'sensor_depth': pconfig.platform_metadata.instruments[pconfig.adcp_id].sensor_depth,
                    'serial_number': pconfig.platform_metadata.instruments[pconfig.adcp_id].serial_number,
                    'manufacturer': pconfig.platform_metadata.instruments[pconfig.adcp_id].manufacturer,
                    'model': pconfig.platform_metadata.instruments[pconfig.adcp_id].model,
                    'firmware_version': pconfig.platform_metadata.instruments[pconfig.adcp_id].firmware_version
            }

            for key, value in instrument_metadata.items():
                if value is None:
                    continue

                if key in dataset.attrs and not pconfig.force_platform_metadata:
                    if not dataset.attrs[key]:
                        dataset.attrs[key] = value
                else:
                    dataset.attrs[key] = value


def _add_platform_adcp_metadata_to_variables(dataset: xr.Dataset, pconfig: ProcessConfig, variables: tp.List[str]):
    """Add sensor metadata found in the platform instrument to the variables

    Overwrites global_attributes if pconfig.force_platform_metadata is True.
    """
    if pconfig.platform_metadata is not None:
        if pconfig.adcp_id in pconfig.platform_metadata.instruments:
            instrument_metadata = {
                'sensor_type': pconfig.platform_metadata.instruments[pconfig.adcp_id].sensor_type,
                'sensor_height': pconfig.platform_metadata.instruments[pconfig.adcp_id].sensor_height,
                'sensor_depth': pconfig.platform_metadata.instruments[pconfig.adcp_id].sensor_depth,
                'serial_number': pconfig.platform_metadata.instruments[pconfig.adcp_id].serial_number,
                'manufacturer': pconfig.platform_metadata.instruments[pconfig.adcp_id].manufacturer,
                'model': pconfig.platform_metadata.instruments[pconfig.adcp_id].model,
                'firmware_version': pconfig.platform_metadata.instruments[pconfig.adcp_id].firmware_version,
                'chief_scientist': pconfig.platform_metadata.instruments[pconfig.adcp_id].chief_scientist,
                'description': pconfig.platform_metadata.instruments[pconfig.adcp_id].description,
                'comments': pconfig.platform_metadata.instruments[pconfig.adcp_id].comments,
            }

            for var in set(variables).intersection(set(dataset.variables)):
                for key, value in instrument_metadata.items():
                    if value is None:
                        continue

                    if key in dataset[var].attrs and not pconfig.force_platform_metadata:
                        if not dataset.attrs[key]:
                            dataset[var].attrs[key] = value
                    else:
                        dataset[var].attrs[key] = value


def _add_sensor_metadata_to_variables(dataset: xr.Dataset, variables: tp.List[str]):
    """Add sensor metadata found in the raw data to the variables"""
    sensor_attrs = {'sensor_type': '', 'sensor_depth': '', 'serial_number': '', 'sensor_depth_units': ''}
    for attr in set(sensor_attrs.keys()).intersection(set(dataset.attrs.keys())):
        if dataset.attrs[attr] is not None:
            sensor_attrs[attr] = dataset.attrs[attr]

    for var in set(variables).intersection(set(dataset.variables)):
        dataset[var].attrs.update(sensor_attrs)


def _drop_beam_metadata(dataset: xr.Dataset, pconfig: ProcessConfig):
    """Drop beam metadata if their respective flag in `pconfig` is True.

    flags: `pconfig.drop_percent_good`, `pconfig.drop_correlation`, `pconfig.drop_amplitude`

    """
    for var, name, flag in zip(
            ["pg", "corr", "amp"],
            ["percent_good", "correlation", "amplitude"],
            [pconfig.drop_percent_good, pconfig.drop_correlation, pconfig.drop_amplitude]
    ):
        if flag is True:
            for v in [var + i for i in ["", "1", "2", "3", "4"]]:
                if v in dataset:
                    dataset = dataset.drop_vars([v])
            l.log(f"{name} data dropped.")

    return dataset


def _update_p01_codes_map(dataset: xr.Dataset, pconfig: ProcessConfig):
    """
    Update the p01_codes_map for the velocities based of the coordinate system.
    """
    if dataset.attrs['coord_system'] == 'earth':
        pconfig.p01_codes_map.update((P01_VEL_CODES[pconfig.platform_type]))
    elif dataset.attrs['coord_system'] == 'xyz':
        pconfig.p01_codes_map.update(XYZ_VEL_CODES)
    elif dataset.attrs['coord_system'] == 'beam':
        pconfig.p01_codes_map.update(BEAM_VEL_CODES)


def _regrid_dataset(dataset: xr.Dataset, pconfig: ProcessConfig) -> xr.Dataset:
    """ Wrapper for regrid_dataset

    Note
    ----
    The `interp` method performs linear interpolation. The `bin` method
    performs averaging of input data strictly within the bin boundaries
    and with equal weights for all data inside each bin.

    """
    # Read new depths
    _new_depths = np.loadtxt(pconfig.grid_depth)

    # Pre-process flags
    for var_ in 'uvw':
        _flag_name = dataset[var_].attrs['ancillary_variables']
        dataset[_flag_name].values = _prepare_flags_for_regrid(dataset[_flag_name].data)

    # Make new quality flags if grid_method is `bin`. Must happen before averaging.
    if pconfig.grid_method == 'bin':
        _new_flags = dict()
        for var_ in 'uvw':
            _flag_name = dataset[var_].attrs['ancillary_variables']
            _new_flags[_flag_name] = _new_flags_bin_regrid(dataset[_flag_name], _new_depths)
        new_flags = xr.Dataset(_new_flags)

    # Apply quality control
    for var_ in 'uvw':
        _flag_name = dataset[var_].attrs['ancillary_variables']
        dataset[var_] = dataset[var_].where(dataset[_flag_name] == 8)

    # Regridding
    msg = f"to grid from file: {pconfig.grid_depth}"
    l.log(f"Regrided dataset with method {pconfig.grid_method} {msg}")
    dataset = regrid_dataset(dataset,
                             grid=_new_depths,
                             dim='depth',
                             method=pconfig.grid_method)

    # Make new flags and replace interpolated/binned values
    for var_ in 'uvw':
        _flag_name = dataset[var_].attrs['ancillary_variables']
        if pconfig.grid_method == 'bin':
            dataset[_flag_name] = new_flags[_flag_name]
        elif pconfig.grid_method == 'interp':
            dataset[_flag_name] = _new_flags_interp_regrid(dataset, var_)

    # Change min and max values
    _add_data_min_max_to_var_attrs(dataset)

    return dataset


def _write_odf(dataset: xr.Dataset, pconfig: ProcessConfig):
    if pconfig.platform_metadata is None:
        pconfig.platform_metadata = PlatformMetadata()
        pconfig.platform_metadata.platform.platform_type = pconfig.platform_type

    if pconfig.adcp_id is None:
        pconfig.adcp_id = "adcp_01"
        pconfig.platform_metadata.add_instrument(instrument_id=pconfig.adcp_id, instrument_meta={"sensor_type": 'adcp'})

    for qualifier in ('VEL', 'ANC'):
        _ = make_odf(
            dataset=dataset,
            platform_metadata=pconfig.platform_metadata,
            adcp_id=pconfig.adcp_id,
            global_attributes=pconfig.global_attributes,
            p01_codes_map=pconfig.p01_codes_map,
            use_bodc_name=pconfig.use_bodc_name,
            odf_dtype=qualifier,
            output_path=pconfig.odf_path,
        )


def _drop_bottom_track(dataset: xr.Dataset) -> xr.Dataset:
    """Drop `bt_u`, `bt_v`, `bt_w`, `bt_e`, `bt_depth`"""
    for var in ["bt_u", "bt_v", "bt_w", "bt_e", "bt_depth"]:
        if var in dataset:
            dataset = dataset.drop_vars([var])
    return dataset


