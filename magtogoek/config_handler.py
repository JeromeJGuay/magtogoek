"""
*** NOTE NOT UP TO DATE ***
author: JérômeJGuay
date: March 4, 2021

This make_configparser is called by magtogoek_command.py
    $ mtgk config ...

ADCP PROCESSING:
-yearbase: year that the sampling started. ex: `1970`
-adcp_orientation: `down` or `up`. (horizontal no supported)
-sonar:  Must be one of `wh`, `os`, `bb`, `nb` or `sw`

ADCP_QUALITY_CONTROL:
If quality_control is `False`, no quality control is carried out.
Blanks are omitted or set False.

ADCP_OUTPUT:
Set True or False.
If bodc_name False, generic variable names are used.

"""
import getpass
from typing import Dict, List, Union, Optional
from magtogoek.taskparser import TaskParser
from datetime import datetime
from pathlib import Path

StrIntFloatBool = Union[str, int, float, bool]
ListStrIntFloatBool = Union[StrIntFloatBool, List[StrIntFloatBool]]
ParserDict = Dict[str, Dict[str, ListStrIntFloatBool]]

REFERENCE = "https://github.com/JeromeJGuay/magtogoek"
VALID_SENSOR_TYPES = ['ADCP']

CONFIG_TO_CLI_MAPS = dict(
    adcp=dict(
        quality_control="qc",
        sidelobes_correction="sidelobes",
        merge_output_files="merge",
        drop_percent_good="drop_pg",
        drop_correlation="drop_corr",
        drop_amplitude="drop_amp",
        make_figures="mk_fig",
        make_log="mk_log",
        odf_data="odf_dtype"
    )
)


def _format_cli_options_to_config_dict(sensor_type: str, tparser: TaskParser, cli_options: dict) -> ParserDict:
    """Put the cli_options dict into a config_dict (ParserDict) structure.

    Put the options under the correction sections.
    """
    _map_cli_options_names_to_config_names(sensor_type, cli_options)
    config_struct = _get_configparser_structure(tparser.as_dict())
    cli_config = {section: {} for section in tparser.sections}
    for option, value in cli_options.items():
        if value is not None and option in config_struct.keys():
            cli_config[config_struct[option]][option] = str(value)
    return cli_config


def _map_cli_options_names_to_config_names(sensor_type: str, cli_options: dict):
    for key, item in CONFIG_TO_CLI_MAPS[sensor_type].items():
        if item in cli_options:
            cli_options[key] = cli_options.pop(item)


def _get_configparser_structure(configparser: Dict) -> Dict:
    parser_struct = dict()
    for section, items in configparser.items():
        for item in items:
            parser_struct[item] = section
    return parser_struct


def write_configfile(filename: str, sensor_type: str, cli_options: Optional[dict] = None):
    """Make a configfile for the given sensor_type.

    Parameters
    ----------
    filename :
    sensor_type :
    cli_options :
        command line options.
    """
    tparser = get_config_taskparser(sensor_type)

    cli_config = None
    if cli_options is not None:
        cli_config = _format_cli_options_to_config_dict(sensor_type, tparser, cli_options)

    tparser.write_from_dict(filename=filename, parser_dict=cli_config, add_missing=True, format_options=False)


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

    sensor_type = _get_sensor_type(filename)
    tparser = get_config_taskparser(sensor_type)

    cli_config = None
    if cli_options is not None:
        cli_config = _format_cli_options_to_config_dict(sensor_type, tparser, cli_options)

    config = tparser.load(filename, add_missing=True, new_values_dict=cli_config, format_options=True)

    return config, sensor_type


def cli_options_to_config(sensor_type: str, cli_options: dict, cwd: Optional[str] = None) -> ParserDict:
    """

    Parameters
    ----------
    sensor_type :
    cli_options :
        command line options.
    cwd :
       current working directory.
    """
    tparser = get_config_taskparser(sensor_type)
    config = tparser.as_dict(with_default=True)
    cli_config = _format_cli_options_to_config_dict(sensor_type, tparser, cli_options)

    tparser.format_parser_dict(parser_dict=cli_config, add_missing=True, format_options=True, file_path=cwd)

    return cli_config


def _get_sensor_type(filename):
    tparser = get_config_taskparser()
    return tparser.load(filename)["HEADER"]["sensor_type"]


def get_config_taskparser(sensor_type: Optional[str] = None):
    tparser = TaskParser()

    section = "HEADER"
    tparser.add_option(section, "made_by", dtypes=["str"], default=getpass.getuser())
    tparser.add_option(section, "last_updated", dtypes=["str"], default=datetime.now().strftime("%Y-%m-%d"))
    tparser.add_option(section, "sensor_type", dtypes=["str"], default=sensor_type, is_required=True, choice=["adcp"], comments='One of [adcp, ].')
    tparser.add_option(section, "platform_type", dtypes=["str"], choice=["buoy", "mooring", "ship"], comments='One of [buoy, mooring, ship, ].')

    section = "INPUT"
    tparser.add_option(section, "input_files", dtypes=["str"], default="", nargs_min=1, is_file=True, is_required=True)
    tparser.add_option(section, "platform_file", dtypes=["str"], default=None, is_file=True)
    tparser.add_option(section, "platform_id", dtypes=["str"], default=None)
    tparser.add_option(section, "sensor_id", dtypes=["str"], default=None)

    section = "OUTPUT"
    tparser.add_option(section, "netcdf_output", dtypes=["str", "bool"], default="", is_path=True, null_value=False)
    tparser.add_option(section, "odf_output", dtypes=["str", "bool"], default="", is_path=True, null_value=False)

    section = "NETCDF_CF"
    tparser.add_option(section, "Conventions", dtypes=["str"], default="CF 1.8")
    tparser.add_option(section, "title", dtypes=["str"], default="")
    tparser.add_option(section, "institution", dtypes=["str"], default="")
    tparser.add_option(section, "summary", dtypes=["str"], default="")
    tparser.add_option(section, "references", dtypes=["str"], default=REFERENCE)
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
    tparser.add_option(section, "start_date", dtypes=["str", "int"], default="", is_time_stamp=True)
    tparser.add_option(section, "end_date", dtypes=["str", "int"], default="", is_time_stamp=True)
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

    if sensor_type == 'adcp':
        section = "ADCP_PROCESSING"
        tparser.add_option(section, "yearbase", dtypes=["int"], default="", is_required=True)
        tparser.add_option(section, "adcp_orientation", dtypes=["str"], default="down", choice=["up", "down"], comments='up or down')
        tparser.add_option(section, "sonar", dtypes=["str"], choice=["wh", "sv", "os", "sw", "sw_pd0"], comments='[wh, sv, os, sw, sw_pd0, ]', is_required=True)
        tparser.add_option(section, "navigation_file", dtypes=["str"], default="", is_file=True)
        tparser.add_option(section, "leading_trim", dtypes=["int", "str"], default="", is_time_stamp=True)
        tparser.add_option(section, "trailing_trim", dtypes=["int", "str"], default="", is_time_stamp=True)
        tparser.add_option(section, "sensor_depth", dtypes=["float"], default="")
        tparser.add_option(section, "depth_range", dtypes=["float"], nargs_min=0, nargs_max=2)
        tparser.add_option(section, "bad_pressure", dtypes=["bool"], default=False, null_value=False)
        tparser.add_option(section, "magnetic_declination", dtypes=["float"], default="")
        tparser.add_option(section, "magnetic_declination_preset", dtypes=["float"], default=None, comments="Found in the ADCP configuration file.")
        tparser.add_option(section, "keep_bt", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, "start_time", dtypes=["str"], default="", is_time_stamp=True)
        tparser.add_option(section, "time_step", dtypes=["float"], default="")
        tparser.add_option(section, "grid_depth", dtypes=["str"], default="", null_value=None, comments='Path to column grid file (m).', is_path=True)
        tparser.add_option(section, "grid_method", dtypes=["str"], default="interp", choice=["interp", "bin"], comments='[interp, bin].')

        section = "ADCP_QUALITY_CONTROL"
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
        tparser.add_option(section, "motion_correction_mode", dtypes=["str"], default="bt", choice=["bt", "nav", "off"], comments='[bt, nav, off, ].')

        section = "ADCP_OUTPUT"
        tparser.add_option(section, "merge_output_files", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, "bodc_name", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, "force_platform_metadata", dtypes=["bool"], default=False, null_value=False)
        tparser.add_option(section, "drop_percent_good", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, "drop_correlation", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, "drop_amplitude", dtypes=["bool"], default=True, null_value=False)
        tparser.add_option(section, "odf_data", dtypes=["str"], default="both", choice=["vel", "anc", "both"], comments='One of [vel, anc, both,].')
        tparser.add_option(section, "make_figures", dtypes=["bool", "str"], default=True, null_value=False)
        tparser.add_option(section, "make_log", dtypes=["bool"], default=True, null_value=False)

    return tparser


if __name__ == "__main__":
    FILENAME = "../test/data/adcp_iml6_2017.ini"

    configuration = load_configfile(FILENAME)

    write_configfile("test", "adcp", configuration)
