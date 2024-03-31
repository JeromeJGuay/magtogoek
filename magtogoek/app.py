"""
Author: JeromeJGuay
Date: March 2 2021

This module contains the entry point for magtogoek CLI app `mtgk`.

Descriptions:
  FIXME

Usage (use the helper to get more informations):
    $ mtgk -h
    or
    $ mtgk --help

Notes:
    Some module are imported by function since loading pandas, for example, is time consuming. Doing makes the
    navigation in the app quicker.
"""

import os
import logging
import sys
import shutil
import typing as tp
from pathlib import Path
from subprocess import run as subp_run

import click

from magtogoek import LOCAL_CONFIGURATION_PATH, DEFAULT_CONFIGURATION_PATH, LOCAL_CONFIG_EXISTS, VERSION, TERMINAL_WIDTH
from magtogoek.exceptions import MagtogoekExit
from magtogoek.app_options import general_options, adcp_options, add_options
from magtogoek.utils import is_valid_filename, json2dict, resolve_relative_path

from magtogoek.metoce import FIGURES_VARIABLES as METOCE_FIGURES_VARIABLES


LOGO_PATH = resolve_relative_path("static/logo.json", __file__)

CONTEXT_SETTINGS = dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
    help_option_names=["-h", "--help"],
)


def _print_info(ctx, callback, info_called):
    """Show command information"""
    if info_called is True:
        subp_run(["printf", r"\e[8;40;" + str(TERMINAL_WIDTH + 1) + "t"], check=True)
        click.clear()
        _print_logo(logo_path=LOGO_PATH, group=ctx.info_name)
        click.secho("\nDescriptions:", fg="red")
        _print_description(ctx.info_name)
        click.secho("\nUsage:", fg="red")
        _print_usage(ctx.info_name, ctx.parent)
        if ctx.info_name in ["mtgk", "config", "process", "quick", "check"]:
            click.secho("\nCommands:", fg="red")
        else:
            click.secho("\nArguments:", fg="red")
        _print_arguments(ctx.info_name, ctx.parent)
        click.secho("\nOptions:", fg="red")
        click.echo("  Use  -h/--help to show the options")
        if LOCAL_CONFIG_EXISTS:
            click.secho("\nConfigurations:", fg="red")
            click.echo(f"  {LOCAL_CONFIGURATION_PATH}")
        click.echo("\n")
        sys.exit()


common_options = [
    click.option("--info", is_flag=True, callback=_print_info, help="Show command information"),
    click.version_option(VERSION)
]


def magtogoek(*args):
    _magtogoek(*args)
    #try:
    #    _magtogoek(*args)
    #except Exception as err:
    #    click.secho(f'{err}\nAn Unexpected Error as occurred', color='red', err=True)

# --------------------------- #
#      mtgk entry point       #
# --------------------------- #
@click.group(context_settings=CONTEXT_SETTINGS)
@add_options(common_options)
@click.option('-v', '--verbosis', is_flag=True, default=False)
def _magtogoek(info, verbosis):
    if verbosis is True:
        logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                            level=logging.INFO)
    pass


# --------------------------- #
#        mtgk command         #
# --------------------------- #

@_magtogoek.command("init")
@add_options(common_options)
@click.option('-r', '--repair', is_flag=True, default=False, help="Add missing files")
@click.option('-f', '--force', is_flag=True, default=False, help="Overwrite existing files")
def init(info, repair, force):
    """Command to create a local magtogoek configuration"""
    _init_magtogoek(repair, force)


@_magtogoek.command("process")
@add_options(common_options)
@click.argument("config_file", metavar="[config_file]", type=click.Path(exists=True))
@click.option("--mk-fig/--no-fig",
              type=bool,
              help="""Make figures to inspect the data. Use to overwrite the value in the config_file""",
              default=None)
@click.option("--headless",
              is_flag=True,
              help="""Using remotely with no display capability""")
@click.option("--from-raw",
              is_flag=True,
              help="""Reload data from raw files (input files)""")
def process(info, config_file: str, **options):
    """Process data by reading configfile"""
    from configparser import ParsingError
    from magtogoek.process_configurations import load_configfile

    cli_options = {}
    if options['mk_fig'] is not None:
        cli_options['mk_fig'] = options['mk_fig']

    try:
        configuration = load_configfile(config_file, cli_options=cli_options)
    except (ParsingError, UnicodeDecodeError):
        raise MagtogoekExit("Failed to open the given configfile. mtgk process aborted.")

    if configuration['HEADER']['process'] == "adcp":
        from magtogoek.adcp.process import process_adcp
        process_adcp(configuration, headless=options['headless'], from_raw=options["from_raw"])
    elif configuration['HEADER']['process'] == "metoce":
        from magtogoek.metoce.process import process_metoce
        process_metoce(configuration, headless=options['headless'], from_raw=options["from_raw"])


# --------------------------- #
#        mtgk groups          #
# --------------------------- #
@_magtogoek.group("config", context_settings=CONTEXT_SETTINGS)
@add_options(common_options)
def config(info):
    """Make configuration files or platform files"""


@_magtogoek.group("quick", context_settings=CONTEXT_SETTINGS)
@add_options(common_options)
def quick(info):
    """Quick data process without configfile"""


@_magtogoek.group("check", context_settings=CONTEXT_SETTINGS)
@add_options(common_options)
def check(info):
    """Get info on raw data files"""


@_magtogoek.group("compute", context_settings=CONTEXT_SETTINGS)
@add_options(common_options)
def compute(info):
    """Command to compute certain quantities."""


@_magtogoek.group("plot", context_settings=CONTEXT_SETTINGS)
@add_options(common_options)
def plot(info):
    """Command to make plot from nc data."""

@_magtogoek.command("flagdata", context_settings=CONTEXT_SETTINGS)
@add_options(common_options)
@click.pass_context
@click.argument("input_file", metavar="[input_file]", nargs=1, type=click.Path(exists=True), required=True)
@click.argument("variable", metavar="[variable]", type=click.STRING, default=None, required=True)
@click.argument("save_path", metavar="[save_path]", nargs=1, type=click.Path(dir_okay=True), required=False)
def flag_data(ctx, info, input_file, variable, save_path):
    """Command to manually flag data in netcdf file.

    \b
    Arguments:
        [input_file] path/to/netcdf_file.
        [variable] bodc or generic variable name. The variable must have an ancillary variable (variable_QC).
        [save_path] (default=None) If not provided, a new file is made with a `_manual_QC` added to the file name.
    """

    from magtogoek.misc.manual_quality_control import manuel_qc_plots
    click.secho('Plot commands:')
    click.echo('\tIn the variable (upper) subplot the ' + click.style("click", fg="red", bold=True) + ' and ' + click.style("drag", fg="red", bold=True) + ' to select data.')
    click.echo('\tPress ' + click.style("a", fg="red", bold=True) + ' to append selected data to buffer.')
    click.echo('\tPress  ' + click.style("r", fg="red", bold=True) + ' to remove selected data from buffer.')
    click.echo('\tPress  ' + click.style("[0-4]", fg="red", bold=True) + ' to set the flag value of the data in the current selection and in the buffer.')
    click.echo('\tPress  ' + click.style("Enter", fg="red", bold=True) + ' to save and exit.')
    click.echo('\tPress  ' + click.style("Escape", fg="red", bold=True) + ' to cancel.')
    click.echo('\t'+ click.style("Scroll", fg="red", bold=True) + ' to zoom in an out.')

    manuel_qc_plots(filename=input_file, variable=variable, save_path=save_path)



# --------------------------- #
#       config command        #
# --------------------------- #
@config.command("platform")
@add_options(common_options)
@click.argument("filename", metavar="[filename]", type=str)
@click.pass_context
def config_platform(ctx, info, filename):
    """Command to make platform files."""
    from magtogoek.platforms import make_platform_template

    filename = is_valid_filename(filename, ext=".json")
    make_platform_template(filename)
    click.echo(click.style(f"Platform file created for -> {filename}", bold=True))


@config.command("adcp")
@add_options(common_options)
@click.argument("config_name", metavar="[config_name]", type=str)
@click.option("-T", "--platform", type=(click.Path(exists=True), str, str),
              help="platform_file, platform_id, adcp_id", default=(None, None, None), nargs=3)
@add_options(general_options())
@add_options(adcp_options())
@click.pass_context
def config_adcp(
        ctx, info, config_name, **options,
):
    """Command to make an adcp config files. The [OPTIONS] can be added
    before or after the [config_name]."""

    from magtogoek.process_configurations import write_configfile

    _print_passed_options(options)
    config_name = is_valid_filename(config_name, ext=".ini")
    options['process'] = 'adcp'
    options.update({k: v for k, v in zip(("platform_file", "platform_id", "adcp_id"), options.pop('platform'))})

    write_configfile(filename=config_name, process="adcp", cli_options=options)
    click.secho(f"Config file created for adcp processing -> {config_name}", bold=True)


@config.command("metoce")
@add_options(common_options)
@click.argument("config_name", metavar="[config_name]", type=str)
@add_options(general_options())
@click.pass_context
def config_metoce(
        ctx, info, config_name, **options,
):
    """Command to make a metoce config files. The [OPTIONS] can be added
    before or after the [config_name]."""

    from magtogoek.process_configurations import write_configfile

    _print_passed_options(options)
    config_name = is_valid_filename(config_name, ext=".ini")
    options['process'] = 'metoce'

    write_configfile(filename=config_name, process="metoce", cli_options=options)
    click.secho(f"Config file created for metoce buoy processing -> {config_name}", bold=True)


@config.command("list_gen_vars")
@add_options(common_options)
@click.option("--adcp/-", help="""List generic variable for adcp""", default=False, show_default=True)
@click.option("--metoce/-", help="""List generic variable for adcp""", default=False, show_default=True)
@click.pass_context
def config_list_generic_variables(ctx, info, **options):
    """list the name of the generic variables."""
    generic_parameters = []
    if options['adcp'] is True:
        from magtogoek.adcp import GENERIC_PARAMETERS
        generic_parameters += GENERIC_PARAMETERS
    if options['metoce'] is True:
        from magtogoek.metoce import GENERIC_PARAMETERS
        generic_parameters += GENERIC_PARAMETERS

    if not generic_parameters:
        from magtogoek import GENERIC_PARAMETERS
        generic_parameters += GENERIC_PARAMETERS

    for i in generic_parameters:
        print(f"`{i}`")


@config.command("list_outlier_regions")
@add_options(common_options)
@click.pass_context
def config_list_outlier_regions(ctx, info, **options):
    """list the name of the outlier region."""
    from magtogoek import CONFIGURATION_PATH
    outlier_regions = json2dict(CONFIGURATION_PATH.joinpath("impossible_parameter_values.json"))
    print(f"Regions:")
    for key in outlier_regions.keys():
        print(f"  {key}")


# ---------------------------- #
#       quick commands         #
# ---------------------------- #
@quick.command("adcp")
@add_options(common_options)
@click.argument("input_files", metavar="[input_files]", nargs=-1, type=click.Path(exists=True), required=True)
@add_options(general_options(input_files=False))
@add_options(adcp_options(sonar=False))
@click.option(
    "-s", "--sonar", type=click.Choice(["wh", "sv", "os", "sw", "sw_pd0"]),
    help="String designating type of adcp. This  is fed to CODAS Multiread or switches to the magtogoek RTIReader.",
    required=True,
)
@click.option("--headless",
              is_flag=True,
              help="""Using remotely with no display capability""")
@click.pass_context
def quick_adcp(ctx, info, input_files: tuple, sonar: str, yearbase: int, **options: dict):
    """Command to quickly process adcp files. The [OPTIONS] can be added
    before or after the [inputs_files]."""
    from magtogoek.process_configurations import cli_options_to_config
    from magtogoek.adcp.process import process_adcp
    options.update({"input_files": input_files, "process": "adcp", "yearbase": yearbase, "sonar": sonar})
    _print_passed_options(options)
    configuration = cli_options_to_config('adcp', options, cwd=str(Path().cwd()))

    process_adcp(configuration,
                 drop_empty_attrs=True,
                 headless=options['headless'])


# ---------------------------- #
#       check commands         #
# ---------------------------- #
@check.command("rti")
@add_options(common_options)
@click.argument("input_files", metavar="[input_files]", nargs=-1, type=click.Path(exists=True), required=True)
@click.pass_context
def check_rti(ctx, info, input_files, **options):
    """Prints info about RTI .ENS files."""
    from magtogoek.adcp.rti_reader import RtiReader

    try:
        RtiReader(input_files).check_files()
    except IndexError:
        print(f'Error, could not read the file. {input_files}')


@compute.command("nav", context_settings=CONTEXT_SETTINGS)
@add_options(common_options)
@click.argument("input_files", metavar="[input_files]", nargs=-1, type=click.Path(exists=True), required=True)
@click.option("-o", "--output-name", type=click.STRING, default=None, help="Name for the output file.")
@click.option("-w", "--window", type=click.INT, default=1, help="Length of the averaging window.")
@click.pass_context
def navigation(ctx, info, input_files, **options):
    """Command to compute u_ship, v_ship, bearing from gsp data."""
    from magtogoek.navigation import compute_navigation

    compute_navigation(
        filenames=input_files,
        output_name=options["output_name"],
        window=options["window"],
    )


@_magtogoek.command('odf2nc', context_settings=CONTEXT_SETTINGS)
@click.argument('input_files',
                metavar="[input_files]",
                nargs=-1,
                type=click.STRING,
                required=True)
@click.option(
    "-d",
    "--dims",
    type=click.STRING,
    multiple=True,
    default=None,
    help='Name of the variable to use as dimensions (coordinates).`-d` has to be called for every dimensions.')
@click.option(
    '-t',
    '--time',
    type=click.STRING,
    multiple=True,
    default=None,
    help='Name of the variables that need to be converted to datetime64. SYTM_01 time variable is automatically '
         'converted.')
@click.option('-m', '--merge', is_flag=True, default=False, help='Use the option to merge the output files.')
@click.option('-o', '--output_name', type=click.STRING, default=None)
@add_options(common_options)
@click.pass_context
def odf2nc(ctx, info, input_files, output_name, **options):
    from magtogoek.odf_format import convert_odf_to_nc
    convert_odf_to_nc(
        input_files=input_files,
        output_name=output_name,
        dims=options['dims'],
        time=options['time'],
        merge=options['merge'])


# ------------------------ #
#        plot commands     #
# ------------------------ #
@plot.command("adcp", context_settings=CONTEXT_SETTINGS)
@add_options(common_options)
@click.argument("input_file", metavar="[input_files]", nargs=1, type=click.Path(exists=True), required=True)
@click.option("-t", "--flag-thres", help="""Set threshold value for flagging""", default=2, show_default=True)
@click.option("-v", "--vel-only", help="""Only plots 2D velocity fields and polar histogram.""", is_flag=True,
              default=False)
@click.option("-s", "--save_fig", help="""Path to save figures to.""", type=click.Path(exists=True), default=None)
@click.option("--headless", help="""If True, figures are displayed""", is_flag=True, default=False)
@click.pass_context
def plot_adcp(ctx, info, input_file, **options):
    """Command to compute u_ship, v_ship, bearing from gsp data."""
    import xarray as xr
    from magtogoek.adcp.plots import make_adcp_figure
    dataset = xr.open_dataset(input_file)
    try:
        make_adcp_figure(dataset, flag_thres=options['flag_thres'], vel_only=options["vel_only"],
                         save_path=options['save_fig'], show_fig=not options['headless'])
    except KeyError:
        print("Wrong format. The netcdf file is missing some attributes or doesn't have the expected variables name.")


@plot.command("metoce", context_settings=CONTEXT_SETTINGS)
@add_options(common_options)
@click.argument("input_file", metavar="[input_files]", nargs=1, type=click.Path(exists=True), required=True)
@click.option("-s", "--save_fig", help="""Path to save figures to.""", type=click.Path(exists=True), default=None)
@click.option("-v", "--vars", type=click.Choice(list(METOCE_FIGURES_VARIABLES.keys())), multiple=True,
              help=f"""Specify which plot(s).""", default=None)
@click.option("--headless", help="""If True, figures are displayed""", is_flag=True, default=False)
@click.option("-r", "--plot-raw", help="""If True, data are plotted against raw data if available.""", is_flag=True, default=False)
@click.pass_context
def plot_metoce(ctx, info, input_file, **options):
    import xarray as xr
    from magtogoek.metoce.plots import make_metoce_figure
    dataset = xr.open_dataset(input_file)
    try:
        raw_dataset = None
        if options['plot_raw'] is True:
            _path = Path(input_file)
            raw_data_path = _path.parent / (_path.stem + "_raw" + _path.suffix)
            if raw_data_path.exists():
                raw_dataset = xr.open_dataset(raw_data_path).sel(time=slice(dataset.time[0], dataset.time[-1]))
            else:
                print(f"Raw data file not found ({raw_dataset}).")
        make_metoce_figure(dataset, variables_groupes=options['vars'] or None, save_path=options['save_fig'],
                           show_fig=not options['headless'], dataset_raw=raw_dataset)

    except KeyError:
        print("Wrong format. The netcdf file is missing some attributes or doesn't have the expected variables name.")


# ------------------------ #
#        Functions         #
# ------------------------ #

def _init_magtogoek(repair: bool, force: bool):
    if repair is True and LOCAL_CONFIG_EXISTS:
        missing_files = set(os.listdir(DEFAULT_CONFIGURATION_PATH)).difference(
            set(os.listdir(LOCAL_CONFIGURATION_PATH)))
        if missing_files:
            for file in missing_files:
                shutil.copyfile(DEFAULT_CONFIGURATION_PATH.joinpath(file), LOCAL_CONFIGURATION_PATH.joinpath(file))
            click.echo(f'Magtogoek is missing files were written.')
        else:
            click.echo(f'Nothing to do. Local config has no missing files.')
    else:
        try:
            shutil.copytree(DEFAULT_CONFIGURATION_PATH, LOCAL_CONFIGURATION_PATH, dirs_exist_ok=force)
            click.echo(f'Magtogoek configuration written to {LOCAL_CONFIGURATION_PATH}.')
        except FileExistsError:
            click.echo(f'Magtogoek is already initialized.')


def _print_passed_options(ctx_params: tp.Dict):
    """print pass and default options/params"""
    click.secho("Options:", fg="green")
    click.echo(click.style("=" * TERMINAL_WIDTH, fg="white", bold=True))
    for key, item in ctx_params.items():
        if item is not None:
            if item is True:
                click.echo(key + ": " + click.style(str(item), fg="green"))
            elif item is False:
                click.echo(key + ": " + click.style(str(item), fg="red"))
            elif type(item) is str:
                click.echo(key + ": " + click.style(str(item), fg="yellow"))
            else:
                click.echo(key + ": " + click.style(str(item), fg="blue"))
    click.echo(click.style("=" * TERMINAL_WIDTH, fg="white", bold=True))


def _print_logo(logo_path: str = "files/logo.json", group: str = ""):
    """open and print logo from logo.json
    If a process is given, prints the process logo.
    """
    logos = json2dict(Path(__file__).parents[0] / Path(logo_path))
    click.secho("=" * TERMINAL_WIDTH, fg="white", bold=True)

    try:
        click.echo(click.style(logos["magtogoek"], fg="blue", bold=True))
        if group == "adcp":
            click.echo(click.style(logos["adcp"], fg="red", bold=True))

    except FileNotFoundError:
        click.echo(click.style("WARNING: logo.json not found", fg="yellow"))
    except KeyError:
        click.echo(click.style("WARNING: key in logo.json not found", fg="yellow"))

    click.echo(
        click.style(
            f"version: {VERSION}" + f" {group} ".rjust(67, " "), fg="green", bold=True,
        )
    )
    click.echo(click.style("=" * TERMINAL_WIDTH, fg="white", bold=True))


def _print_arguments(group, parent):
    """print group(command) command(arguments)"""
    _parent = parent.info_name if parent else ""
    messages = {
        "mtgk": '\n'.join([
            "  init".ljust(20, " ") + "Command to create a local magtogoek configuration",
            "  config".ljust(20, " ") + "Command to make configuration files",
            "  quick".ljust(20, " ") + "Command to quickly process data files",
            "  process".ljust(20, " ") + "Command to process data with configuration files",
            "  check".ljust(20, " ") + "Command to check the information on some file type",
            "  compute".ljust(20, " ") + "Command to compute certain quantities",
            "  odf2nc".ljust(20, " ") + "Command to convert odf to netcdf"
        ]),
        "init":
            "[takes no arguments]",
        "config":
            '\n'.join(["  adcp".ljust(20, " ") + "Config file for adcp data. ",
                       "  platform".ljust(20, " ") + "Creates a platform.json file"]),
        "quick":
            "  adcp".ljust(20, " ") + "Process adcp data.",

        "process": ("  [config_name]".ljust(20, " ")
                    + "Filename (path/to/file) of the configuration file."),
        "compute":
            "  nav".ljust(20, " ")
            + "Command to compute u_ship, v_ship, bearing from gsp data.",

        "nav": (
                "  [file_name]".ljust(20, " ")
                + "Filename (path/to/file, or expression) of the GPS files."

        ),
        "check": "  rti".ljust(20, " ") + "Print information on the rti .ens files. ",

        "adcp": "  [config_name]".ljust(20, " ")
                + "Filename (path/to/file) for the new configuration file.",
        "platform": "  [filename]".ljust(20, " ")
                    + "Filename (path/to/file) for the new platform file.",
        }
    if group in messages:
        click.secho(messages[group], fg="white")


def _print_description(group):
    """print group/command descriptions"""
    messages = {"mtgk": (
        "Magtogoek is a Linux python package and command line application (CLI) for"
        " processing ocean data. At the moment, only Acoustic Doppler Current Profiler (ADCP)"
        " data can be processed. This package is developed by the Scientific"
        " Advice, Information and Support Branch at the Fisheries and Ocean Canada"
        " Maurice-Lamontagne Institute."),
        "init": (
            "Creates a local magtogoek configurations: "
            "   - ODF and Netcdf variables meta data files."
            "   - Quality control test thresholds."
        ),
        "config": (
            "The config command is used to create `.ini` configuration files or `.json`"
            " platform files. Configuration `.ini` files are used to write the desired"
            " processing configuration for different types of sensor (adcp, wps, etc). Once"
            " created the configuration file   can be filled in any text editor or via"
            " optional arguments. Platform files are used to store platform metadata."
        ),
        "quick": "Quick way to process files.",
        "process": (
            "Command to execute the processing orders from a configuration file. If"
            " relative path where used in the configuration file, they are relative to directory"
            " where the command is called and not where the configuration file is located."
        ),
        "check": (
            "Print some raw files information. Only available for adcp RTI .ENS files."
        ),
        "adcp": (
            "\n"
            "        sonar\n"
            "        -----\n"
            "           os : OceanSurveyor (RDI)\n"
            "           wh : WorkHorse (RDI)\n"
            "           sv : SentinelV (RDI)\n"
            "           sw : SeaWatch (RTI)\n"
            "           sw_pd0 : SeaWatch (RTI in RDI pd0 file format)\n"
            "\n"
            "        quality control\n"
            "        ---------------\n"
            "           - velocity, amplitude, correlation, percentgood, roll, pitch, \n"
            "             side_lobe.\n"
            "           - Temperatures outside [-2, 32] Celsius. \n"
            "           - Pressures outside [0, 180] dbar.\n"
            "\n"
            "        plots\n"
            "        -----\n"
            "           - 2D velocity fields (u,v), time-series,\n"
            "           - Polar Histogram of the Velocities amplitude and direction,\n"
            "           - Pearson Correlation of velocity for consecutive bins,\n"
        ),
        "nav": (
            " Compute u_ship (eastward velocity), v_ship (northward velocity) and the bearing"
            " of the input gps data. The GPS input files can be nmea text file, gpx XML files or"
            " a netcdf files with `lon`, `lat` variables and `time` coordinates. Using the command"
            " `-w`, an averaging window can be use to smooth the computed navigation data."
            " A matplotlib plot is made after each computation."
        ),
        "platform": "Creates an empty platform.json file",
        "odf2nc": "Converts odf files to netcdf",
    }
    if group in messages:
        if "\n" in messages[group]:
            click.echo(messages[group])
        else:
            click.echo(click.wrap_text(messages[group], width=TERMINAL_WIDTH, initial_indent=''))


def _print_usage(group, parent):
    """print group/command usage"""
    _parent = parent.info_name if parent else ""

    if group == "mtgk":
        click.echo("  mtgk [config, process, quick, check]")
    if group == "init":
        click.echo("  mtgk init")
    if group == "config":
        click.echo("  mtgk config [adcp, platform,] [CONFIG_NAME] [OPTIONS]")
    if group == "platform":
        click.echo("  mtgk config platform [FILENAME] [OPTIONS]")
    if group == "process":
        click.echo("  mtgk process [CONFIG_FILE] [OPTIONS]")
    if group == "quick":
        click.echo("  mtgk quick [adcp, ] [FILENAME,...] [OPTIONS]")
    if group == "adcp":
        if _parent == "config":
            click.echo("  mtgk config adcp [CONFIG_NAME] [OPTIONS]")
        if _parent == "quick":
            click.echo("  mtgk quick adcp [INPUT_FILES] [SONAR] [YEARBASE] [OPTIONS]")
    if group == "check":
        click.echo("  mtgk check [rti,] [INPUT_FILES] ")
    if group == "rti":
        click.echo("  mtgk check rti [INPUT_FILES] ")
    if group == "nav":
        click.echo("  mtgk compute nav [INPUT_FILES] ")
