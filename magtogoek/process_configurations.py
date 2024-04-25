"""
author: JérômeJGuay
date: 2024

"""
import getpass
from typing import Dict, List, Union, Optional, Tuple
from magtogoek import PROCESSES, REPOSITORY_ADDRESS
from magtogoek.taskparser import TaskParser
from datetime import datetime
from pathlib import Path

StrIntFloatBool = Union[str, int, float, bool]
ListStrIntFloatBool = Union[StrIntFloatBool, List[StrIntFloatBool]]
ParserDict = Dict[str, Dict[str, ListStrIntFloatBool]]

CONFIG_TO_CLI_MAPS = {
    'global': {
        'merge_output_files': "merge",
        'quality_control': "qc",
        'make_figures': "mk_fig",
        'make_log': "mk_log",
        'use_bodc_name': "bodc_name"
    },
    'adcp': {
        'sidelobes_correction': "sidelobes",
        'drop_percent_good': "drop_pg",
        'drop_correlation': "drop_corr",
        'drop_amplitude': "drop_amp",
        'coord_transform': "ct"
    },
    'metoce': {
        # TODO
    }
}


def _format_cli_options_to_config_dict(process: str, tparser: TaskParser, cli_options: dict) -> ParserDict:
    """Put the cli_options dict into a config_dict (ParserDict) structure.

    Put the options under the correction config sections and map options names to config names.

    Parameters
    ----------
    process

    tparser :
        TaskParser instance.

    cli_options :
        Options received from the cli.

    """
    _map_cli_options_names_to_config_names("global", cli_options)
    _map_cli_options_names_to_config_names(process, cli_options)

    config_struct = _get_configparser_structure(tparser.as_dict())
    cli_config = {section: {} for section in tparser.sections}
    for option, value in cli_options.items():
        if value is not None and option in config_struct.keys():
            cli_config[config_struct[option]][option] = str(value)
    return cli_config


def _map_cli_options_names_to_config_names(process: str, cli_options: dict):
    for key, item in CONFIG_TO_CLI_MAPS[process].items():
        if item in cli_options:
            cli_options[key] = cli_options.pop(item)


def _get_configparser_structure(configparser: Dict) -> Dict:
    parser_struct = dict()
    for section, items in configparser.items():
        for item in items:
            parser_struct[item] = section
    return parser_struct


def write_configfile(filename: str, process: str, cli_options: Optional[dict] = None):
    """Make a configfile for the given process.

    Parameters
    ----------
    filename :
    process :
    cli_options :
        command line options.
    """
    tparser = get_config_taskparser(process=process)

    cli_config = {}
    if cli_options is not None:
        cli_config = _format_cli_options_to_config_dict(process, tparser, cli_options)

    tparser.write(
        filename=filename,
        new_values_dict=cli_config,
        with_default=True,
        with_comments=True
    )


def load_configfile(filename: str, cli_options: Optional[dict] = None) -> ParserDict:
    """load a configfile.

    Returns parser as a dictionary with the appropriate types.

    - Add the missing expected sections and options with empty string as value.
    - Updates the value if dictionary is passed as `updated_params`.
    - saves the edited configuration files.
    - convert the options from string to the correct type for processing.

    """
    if not Path(filename).exists():
        raise FileNotFoundError(f"{filename} not found")

    raw_config = _load_raw_config(filename)
    version = _get_config_version(raw_config)
    process = _get_config_process(raw_config, version)

    tparser = get_config_taskparser(process=process, version=version)

    cli_config = None
    if cli_options is not None:
        cli_config = _format_cli_options_to_config_dict(process, tparser, cli_options)

    config = tparser.load(filename, add_missing=True, new_values_dict=cli_config, format_options=True)

    version_control(config_dict=config, version=version)

    config['HEADER']['config_file'] = filename

    return config


def cli_options_to_config(process, cli_options: dict, cwd: Optional[str] = None) -> ParserDict:
    """

    Parameters
    ----------
    process :
    cli_options :
        command line options.
    cwd :
       current working directory.
    """
    tparser = get_config_taskparser(process=process)
    
    cli_config = _format_cli_options_to_config_dict(process, tparser, cli_options)

    tparser.format_parser_dict(parser_dict=cli_config, add_missing=True, format_options=True, file_path=cwd)

    return cli_config


def _load_raw_config(filename: Union[str, Path]):
    tparser = get_config_taskparser()
    return tparser.load(filename, add_missing=False)


def _get_config_version(raw_config: dict):
    if "version" not in raw_config["HEADER"]:
        return 0
    else:
        return raw_config["HEADER"]["version"]


def _get_config_process(raw_config: dict, version: int):
    if version == 0:
        process = raw_config["HEADER"]["sensor_type"]
    else:
        process = raw_config["HEADER"]["process"]
    return process


def version_control(config_dict: Dict, version: int):
    """Updates the config_dict to the current version."""
    if version == 0:
        config_dict['HEADER']['process'] = config_dict['HEADER'].pop('sensor_type')

    process = config_dict['HEADER']['process']

    if process == "adcp":
        if version == 0:
            config_dict['ADCP_PROCESSING']['adcp_id'] = config_dict['ADCP_PROCESSING'].pop('sensor_id')
            config_dict["ADCP_OUTPUT"]['use_bodc_name'] = config_dict["ADCP_OUTPUT"].pop('bodc_name')

            config_dict['ADCP_PROCESSING']['start_trim_time'], config_dict['ADCP_PROCESSING']['start_trim_index'] \
                = _unpack_trim_args(config_dict['ADCP_PROCESSING'].pop('leading_trim'))

            config_dict['ADCP_PROCESSING']['end_trim_time'], config_dict['ADCP_PROCESSING']['end_trim_index'] \
                = _unpack_trim_args(config_dict['ADCP_PROCESSING'].pop('trailing_trim'))


def _unpack_trim_args(trim: Union[str, int]) -> Tuple[Optional[str], Optional[int]]:
    """Unpack _trim parameter into .

    Use to convert Version=0 configuration leading_trim and trailing_trim
    to Version>0 configuration `<start/end>_time_trim` and `<start/end>_index_trim`.

    If `trim` is None:
        return (None, None)
    Elif `trim` is instance int:
        return (None, trim)
    Else:
        return (trim, None)

    """
    if trim is None:
        return None, None
    elif isinstance(trim, int):
        return None, trim
    else:
        return trim, None


def get_config_taskparser(process: Optional[str] = None, version: Optional[int] = None):
    if version is None:
        version = 1

    tparser = TaskParser()

    section = "HEADER"
    tparser.add_option(section, "version", dtypes=["int"], default=version)
    tparser.add_option(section, "made_by", dtypes=["str"], default=getpass.getuser())
    tparser.add_option(section, "last_updated", dtypes=["str"], default=datetime.now().strftime("%Y-%m-%d"))

    if version == 0:
        tparser.add_option(section, "sensor_type", dtypes=["str"], default=process, is_required=True, choice=PROCESSES, comments=f'One of {PROCESSES}.')
    else:
        tparser.add_option(section, "process", dtypes=["str"], default=process, is_required=True, choice=PROCESSES, comments=f'One of {PROCESSES}.')

    section = "INPUT"
    tparser.add_option(section, "input_files", dtypes=["str"], default="", nargs_min=1, is_file=True, is_required=True)
    tparser.add_option(section, "platform_file", dtypes=["str"], default=None, is_file=True)
    tparser.add_option(section, "platform_id", dtypes=["str"], default=None)

    section = "OUTPUT"
    tparser.add_option(section, "netcdf_output", dtypes=["str", "bool"], default="", is_path=True, null_value=False)
    tparser.add_option(section, "odf_output", dtypes=["str", "bool"], default="", is_path=True, null_value=False)
    tparser.add_option(section, "make_figures", dtypes=["str", "bool"], default=True, is_path=True, null_value=False)
    tparser.add_option(section, "make_log", dtypes=["bool"], default=True, null_value=False)
    tparser.add_option(section, "force_platform_metadata", dtypes=["bool"], default=False, null_value=False)
    tparser.add_option(section, "use_bodc_name", dtypes=["bool"], default=True, null_value=False)
    tparser.add_option(section, "merge_output_files", dtypes=["bool"], default=True, null_value=False)

    section = "NETCDF_CF"
    tparser.add_option(section, "Conventions", dtypes=["str"], default="CF 1.8")
    tparser.add_option(section, "title", dtypes=["str"], default="")
    tparser.add_option(section, "institution", dtypes=["str"], default="")
    tparser.add_option(section, "summary", dtypes=["str"], default="")
    tparser.add_option(section, "references", dtypes=["str"], default=REPOSITORY_ADDRESS)
    tparser.add_option(section, "comments", dtypes=["str"], default="")
    tparser.add_option(section, "naming_authority", dtypes=["str"], default="BODC, SDC, CF, MEDS")
    tparser.add_option(section, "source", dtypes=["str"], default="")

    section = "PROJECT"
    tparser.add_option(section, "project", dtypes=["str"], default=""),
    tparser.add_option(section, "sea_name", dtypes=["str"], default="")
    tparser.add_option(section, "sea_code", dtypes=["str"], default="")

    section = "CRUISE"
    tparser.add_option(section, "country_institute_code", dtypes=["str"], default="")
    tparser.add_option(section, "cruise_number", dtypes=["str"], default="", null_value="")
    tparser.add_option(section, "cruise_name", dtypes=["str"], default="")
    tparser.add_option(section, "cruise_description", dtypes=["str"], default="")
    tparser.add_option(section, "organization", dtypes=["str"], default="")
    tparser.add_option(section, "chief_scientist", dtypes=["str"], default="")
    tparser.add_option(section, "start_date", dtypes=["str", "int"], default="", is_time_stamp=True, comments="Format: %Y-%m-%dT%H:%M:%S")
    tparser.add_option(section, "end_date", dtypes=["str", "int"], default="", is_time_stamp=True, comments="Format: %Y-%m-%dT%H:%M:%S")
    tparser.add_option(section, "event_number", dtypes=["str"], default="", null_value="")
    tparser.add_option(section, "event_qualifier1", dtypes=["str"], default="", null_value="")
    tparser.add_option(section, "event_comments", dtypes=["str"], default="")

    section = "GLOBAL_ATTRIBUTES"
    tparser.add_option(section, "date_created", dtypes=["str"], default="")
    tparser.add_option(section, "cdm_data_type", dtypes=["str"], default="")
    tparser.add_option(section, "country_code", dtypes=["str"], default="")
    tparser.add_option(section, "publisher_email", dtypes=["str"], default="")
    tparser.add_option(section, "creator_type", dtypes=["str"], default="")
    tparser.add_option(section, "publisher_name", dtypes=["str"], default="")
    tparser.add_option(section, "keywords", dtypes=["str"], default="")
    tparser.add_option(section, "keywords_vocabulary", dtypes=["str"], default="")
    tparser.add_option(section, "standard_name_vocabulary", dtypes=["str"], default="CF v.52")
    tparser.add_option(section, "acknowledgment", dtypes=["str"], default="")

    if version > 0:
        section = "PROCESSING"
        tparser.add_option(section, "navigation_file", dtypes=["str"], default="", is_file=True)
        tparser.add_option(section, "start_trim_index", dtypes=["int"], default="", value_min=0, comments="Int. Number of point to remove from the start.")
        tparser.add_option(section, "end_trim_index", dtypes=["int"], default="", value_min=0, comments="Int. Number of point to remove from the end.")
        tparser.add_option(section, "start_trim_time", dtypes=["str"], default="", is_time_stamp=True, comments="TimeStamp. Format: %Y-%m-%dT%H:%M:%S")
        tparser.add_option(section, "end_trim_time", dtypes=["str"], default="", is_time_stamp=True, comments="TimeStamp. Format: %Y-%m-%dT%H:%M:%S")
        tparser.add_option(section, "quality_control", dtypes=["bool"], default=True, null_value=False)

    if process == 'adcp':
        section = "ADCP_PROCESSING"
        tparser.add_option(section, "platform_type", dtypes=["str"], choice=["buoy", "mooring", "ship", "lowered"],
                           comments='One of [buoy, mooring, ship, lowered]. Superseded by `platform_type` in the platform file.')
        if version == 0:
            tparser.add_option(section, "sensor_id", dtypes=["str"], default=None) # convert to adcp_id ?
        else:
            tparser.add_option(section, "adcp_id", dtypes=["str"], default=None, comments="Needs to match instrument_id in platform files.")  # convert to adcp_id ?
        tparser.add_option(section, "yearbase", dtypes=["int"], default="", is_required=False)
        tparser.add_option(section, "adcp_orientation", dtypes=["str"], default="down", choice=["up", "down"], comments='up or down')
        tparser.add_option(section, "sonar", dtypes=["str"], choice=["wh", "sv", "os", "sw", "sw_pd0"], comments='One of [wh, sv, os, sw, sw_pd0, ]', is_required=True)

        if version == 0:
            tparser.add_option(section, "navigation_file", dtypes=["str"], default="", is_file=True)
            tparser.add_option(section, "leading_trim", dtypes=["int", "str"], value_min=0, default="", is_time_stamp=True)
            tparser.add_option(section, "trailing_trim", dtypes=["int", "str"], value_min=0, default="", is_time_stamp=True)
        tparser.add_option(section, "sensor_depth", dtypes=["float"], default="", comments="Sensor depth in meter. Will overwrite the one found in the adcp file.")
        tparser.add_option(section, "depth_range", dtypes=["float"], nargs_min=0, nargs_max=2,
                           comments="Value in meter. Cut the bin outside this range. Either `min` or `min, max`.")
        tparser.add_option(section, "bad_pressure", dtypes=["bool"], default=False, null_value=False,
                           comments="If True, XducerDepth is set to 0 or to `sensor_depth` if provided.")
        tparser.add_option(section, "magnetic_declination", dtypes=["float"], default=None)
        tparser.add_option(section, "magnetic_declination_preset", dtypes=["float"], default=None, comments="Found in the ADCP configuration file. (Used for RTI)")
        tparser.add_option(section, "keep_bt", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, "start_time", dtypes=["str"], default="", is_time_stamp=True, comments="If provided, a new time coordinate vector, starting at `start_time`, is used instead of the one found in the raw adcp file.")
        tparser.add_option(section, "time_step", dtypes=["float"], default="", comments="Time step in seconds. Only use if a `start_time` value is provided.")
        tparser.add_option(section, "grid_depth", dtypes=["str"], default="", null_value=None,
                           comments='Path of grid txt file. Single column of bin depth (center) in meter. Can be irregularly spaced.',
                           is_path=True)
        tparser.add_option(section, "grid_method", dtypes=["str"], default="interp", choice=["interp", "bin"], comments='One of [interp, bin].')
        tparser.add_option(section, "coord_transform", dtypes=["bool"], default=True, null_value=False, comments="Transforms to ENU (earth) if in Beam of XYZ.")
        tparser.add_option(section, "motion_correction_mode", dtypes=["str"], default="bt", choice=["bt", "nav", "off"], comments='One of [bt, nav, off].')

        section = "ADCP_QUALITY_CONTROL"
        if version == 0:
            tparser.add_option(section, "quality_control", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, "amplitude_threshold", dtypes=["int"], default=0, value_min=0, value_max=255, comments='Value between 0 and 255.')
        tparser.add_option(section, "percentgood_threshold", dtypes=["int"], default=64, value_min=0, value_max=100, comments='Value between 0 and 100.')
        tparser.add_option(section, "correlation_threshold", dtypes=["int"], default=90, value_min=0, value_max=255, comments='Value between 0 and 255.')
        tparser.add_option(section, "horizontal_velocity_threshold", dtypes=["float"], default=5)
        tparser.add_option(section, "vertical_velocity_threshold", dtypes=["float"], default=5)
        tparser.add_option(section, "error_velocity_threshold", dtypes=["float"], default=5)
        tparser.add_option(section, "sidelobes_correction", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, "bottom_depth", dtypes=["float"])
        tparser.add_option(section, "pitch_threshold", dtypes=["int"], default=20, value_min=0, value_max=180, comments='Value between 0 and 180.')
        tparser.add_option(section, "roll_threshold", dtypes=["int"], default=20, value_min=0, value_max=180, comments='Value between 0 and 180.')

        section = "ADCP_OUTPUT"
        tparser.add_option(section, "drop_percent_good", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, "drop_correlation", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, "drop_amplitude", dtypes=["bool"], default=True, null_value=False)
        if version == 0:
            tparser.add_option(section, "force_platform_metadata", dtypes=["bool"], default=False, null_value=False)
            tparser.add_option(section, "merge_output_files", dtypes=["bool"], default=True, null_value=False)
            tparser.add_option(section, "bodc_name", dtypes=["bool"], default=True, null_value=False)
            tparser.add_option(section, "make_figures", dtypes=["bool", "str"], default=True, null_value=False)
            tparser.add_option(section, "make_log", dtypes=["bool"], default=True, null_value=False)

    elif process == "metoce":
        section = "METOCE_PROCESSING"
        tparser.add_option(section, "data_format", dtypes=["str"], default="viking", choice=['viking', 'metis'])
        tparser.add_option(section, "buoy_name", dtypes=["str"],  comments='Name of the buoy in the raw file.', is_required=False)
        tparser.add_option(section, "sampling_depth", dtypes=["float"], comments="Use for water sensor data corrections/computations (oxygen, density).")
        tparser.add_option(section, "adcp_id", dtypes=["str"], default=None, comments="Needs to match instrument_id in platform files.")
        tparser.add_option(section, "ctd_id", dtypes=["str"], default=None, comments="Needs to match instrument_id in platform files.")
        tparser.add_option(section, "ctdo_id", dtypes=["str"], default=None, comments="Needs to match instrument_id in platform files.")
        tparser.add_option(section, "ph_id", dtypes=["str"], default=None, comments="Needs to match instrument_id in platform files.")
        tparser.add_option(section, "par_id", dtypes=["str"], default=None, comments="Needs to match instrument_id in platform files.")
        tparser.add_option(section, "eco_id", dtypes=["str"], default=None, comments="Needs to match instrument_id in platform files.")
        tparser.add_option(section, "pco2_id", dtypes=["str"], default=None, comments="Needs to match instrument_id in platform files.")
        tparser.add_option(section, "wave_id", dtypes=["str"], default=None, comments="Needs to match instrument_id in platform files.")
        tparser.add_option(section, "wind_id", dtypes=["str"], default=None, comments="Needs to match instrument_id in platform files.")
        tparser.add_option(section, "meteo_id", dtypes=["str"], default=None, comments="Needs to match instrument_id in platform files.")

        tparser.add_option(section, "recompute_speed_course", dtypes=["bool"], default=False, null_value=False)
        tparser.add_option(section, "compute_uv_ship", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, "recompute_density", dtypes=["bool"], default=True, null_value=False)

        tparser.add_option(section, "magnetic_declination", dtypes=["float"], default=None, comments="If set, also se the adcp_magnetic_declination_preset since the ADCP already corrects it.")
        tparser.add_option(section, "adcp_magnetic_declination_preset", dtypes=["float"], default=None, comments="Found in the ADCP configuration file. (Used for RTI)")


        section = "METOCE_CORRECTION"
        tparser.add_option(section, "adcp_motion_correction", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, "wind_motion_correction", dtypes=["bool"], default=True, null_value=False)

        tparser.add_option(section, "ph_salinity_correction", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, 'ph_salinity_coeffs', dtypes=["float"], nargs=3, default="", comments="Calibration coefficient: [psal, k0, k2]")
        tparser.add_option(section, "dissolved_oxygen_winkler_correction", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, 'dissolved_oxygen_winkler_coeffs', dtypes=["float"], nargs=2, default="", comments="Calibration coefficient: d1_w, d2_w")
        tparser.add_option(section, 'dissolved_oxygen_rinko_coeffs', dtypes=["float"], nargs=6, default="", comments="Calibration coefficient: d0, d1, d2, c0, c1, c2")
        tparser.add_option(section, "dissolved_oxygen_pressure_correction", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, "dissolved_oxygen_salinity_correction", dtypes=["bool"], default=True, null_value=False)

        for var in ["salinity", "temperature", "dissolved_oxygen", "ph", "scattering", "chlorophyll", "fdom"]:
            tparser.add_option(section, f'{var}_drift', dtypes=["float"], default="", comments="Total drift")
            tparser.add_option(section, f'{var}_drift_start_time', dtypes=["str"], is_time_stamp=True, default="", comments="Format: %Y-%m-%dT%H:%M:%S")
            tparser.add_option(section, f'{var}_calibration_correction', dtypes=["float"], nargs=2, default="", comments="Linear regression coefficients: A, B | [Corrected_Data] = A * [Data] + B")

        section = "METOCE_QUALITY_CONTROL"
        tparser.add_option(section, "absolute_outlier", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, "regional_outlier", dtypes=["str"], default="", comments="Name of the region defined in the `impossible_parameters_values.json`")
        tparser.add_option(section, "propagate_flags", dtypes=["bool"], default=True, null_value=False)

        for var in ["salinity", "temperature", "dissolved_oxygen", "ph", "scattering", "chlorophyll", "fdom"]:
            tparser.add_option(section, f'{var}_spike_threshold', dtypes=["float"], default=None)
            tparser.add_option(section, f'{var}_spike_window', dtypes=["int"], default=3, comments="Window size")

        tparser.add_option(section, "adcp_horizontal_velocity_threshold", dtypes=["float"], default=5)
        tparser.add_option(section, "adcp_vertical_velocity_threshold", dtypes=["float"], default=5)
        tparser.add_option(section, "adcp_error_velocity_threshold", dtypes=["float"], default=5)
        tparser.add_option(section, "adcp_pitch_threshold", dtypes=["int"], default=20, value_min=0, value_max=180, comments='Value between 0 and 180.')
        tparser.add_option(section, "adcp_roll_threshold", dtypes=["int"], default=20, value_min=0, value_max=180, comments='Value between 0 and 180.')


    return tparser


if __name__ == "__main__":
    FILENAME = "../test/data/adcp_iml6_2017.ini"

    configuration = load_configfile(FILENAME)

    write_configfile("test", "adcp", configuration)

