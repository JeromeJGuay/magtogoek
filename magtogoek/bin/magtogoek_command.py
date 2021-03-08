"""
Author: JeromeJGuay
Date: Mars 2

This module contains the command line applications `mtgk`.
TODO: change process var to sensor_type to avoid confusion
TODO: move add_options here and to _add_options
TODO: pathlib *.ext ? handling
================================================================================
        __  ___    ____    _____ ________ ______ _____  ______ _____  __ __
       /  |/   |  / _  |  / ___//__  ___// __  // ___/ / __  //  __/ / // /
      / /|  /| | / /_| | / /_ \   / /   / /_/ // /_ \ / /_/ //  __/ / _  /
     /_/ |_/ |_|/_/  |_|/_____|  /_/   /_____//_____|/_____//_____//_/ \_\.

================================================================================

Descriptions:
  FIXME

Usage:
    $ mtgk config [adcp, ] [CONFIG_NAME] [OPTIONS]

    $ mtgk process [adcp, ] [CONFIG_FILE] [OPTIONS]

Helps:
    $ mtgk

    $ mtgk [config, process, ]

    $ mtgk [config, process] [adcp, ]
"""
import click
import typing as tp
import subprocess

from pathlib import Path
from magtogoek.metadata.toolbox import json2dict
from magtogoek.bin.configparser_templates import ConfigFile  # make_configparser
from magtogoek.bin.command_options import adcp_options, add_options

### Global variable used by some of the module functions.
_magtogoek_version = "0.0.2"
_valid_sensor_types = ["adcp"]
_logo_path = "../files/logo.json"


_CONTEXT_SETTINGS = dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
    help_option_names=["-h", "--help"],
)


def _print_info(ctx, callback):
    """Show command information"""
    if callback:
        subprocess.run(["printf", "\e[8;40;80t"])
        click.clear()
        _print_logo(
            logo_path=_logo_path, group=ctx.info_name, version=_magtogoek_version
        )
        click.secho("\nDescriptions:", fg="red")
        _print_description(ctx.info_name)
        click.secho("\nUsage:", fg="red")
        _print_usage(ctx.info_name, ctx.parent.info_name)
        if ctx.info_name in ["mtgk", "config", "process"]:
            click.secho("\nCommands:", fg="red")
        else:
            click.secho("\nArguments:", fg="red")
        _print_arguments(ctx.info_name)
        click.secho("\nOptions", fg="red")
        click.echo("  Use  -h/--help to show the options")
        click.echo("\n")
        exit()


# ---------------------------#
#      mtgk entry point      #
# ---------------------------#
@click.group(context_settings=_CONTEXT_SETTINGS)
@click.option(
    "--info", is_flag=True, callback=_print_info, help="Show command information"
)
def magtogoek(info):
    pass


### config sub-group
@magtogoek.group(context_settings=_CONTEXT_SETTINGS)
@click.option(
    "--info", is_flag=True, callback=_print_info, help="Show command information"
)
def config(info):
    pass


### process sub-group
@magtogoek.group(context_settings=_CONTEXT_SETTINGS)
@click.option(
    "--info", is_flag=True, callback=_print_info, help="Show command information"
)
def process(info):
    pass


### adcp: config sub-command
@config.command("adcp")
@click.option(
    "--info", is_flag=True, callback=_print_info, help="Show command information"
)
@click.argument(
    "config_name", metavar="[config_file]", required=False, default=None, type=str
)
@add_options(adcp_options())
@click.pass_context
def config_adcp(
    ctx,
    config_name,
    **options,
):
    """Command to make an adcp config files. The [OPTIONS] can be added
    before or after the [config_name]."""

    _print_passed_options(options)

    config_name = _validate_config_name(config_name)

    options = _translate_options_name(options)

    # make the ConfigFile.
    config = ConfigFile(filename=config_name)
    config.make(
        sensor_type="adcp",
        options=options,
    )
    config.save()
    click.echo(
        click.style(
            f"Config file created for adcp processing -> {config_name}", bold=True
        )
    )


def _validate_config_name(config_name: str) -> str:
    """Check if directory or/and file name exist.

    Ask to make the directories if they don't exist.
    Ask  to ovewrite the file if a file already exist.

    Appends a `.ini` suffix (extension) none was given.
    But keeps other suffixes.
    Ex. path/to/file.ext1.ext2.ini

    """
    if Path(config_name).suffix != ".ini":
        config_name += ".ini"

    while not Path(config_name).parents[0].is_dir():
        if click.confirm(
            click.style(
                "Directory does not exist. Do you want to create it ?", bold=True
            ),
            default=False,
        ):
            Path(config_name).parents[0].mkdir(parents=True)
        else:
            config_name = _ask_for_config_name()

    if Path(config_name).is_file():
        if not click.confirm(
            click.style(
                "A `.ini` file with this name already exists. Overwrite ?", bold=True
            ),
            default=True,
        ):
            return _validate_config_name(_ask_for_config_name())
    return config_name


def _translate_options_name(options):
    """Translate options name from commad names to the config file names"""
    translator_dict = dict(
        GPS_file="gps",
        quality_control="qc",
        side_lobe_correction="side_lobe",
        trim_leading_data="start_time",
        trim_trailling_data="end_time",
        platform_motion_correction="m_corr",
        merge_output_file="merge",
        drop_percent_good="drop_pg",
        drop_correlation="drop_corr",
        drop_amplitude="drop_amp",
        make_figures="mk_fig",
        make_log="mk_log",
    )
    for key, item in translator_dict.items():
        options[key] = options.pop(item)
    return options


def _ask_for_config_name() -> str:
    """ckick.prompt that ask for `config_name`"""
    return click.prompt(
        click.style(
            "\nEnter a filename (path/to/file) for the config `.ini` file. ", bold=True
        )
    )


def _print_passed_options(ctx_params: tp.Dict):
    """print pass and default options/paramsd"""
    click.secho("Options:", fg="green")
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


def _print_logo(
    logo_path: str = "files/logo.json",
    group: str = "",
    version: str = "unavailable",
):
    """open and print logo from logo.json
    If a process is given, prints the process logo.
    """
    logos = json2dict(Path(__file__).parents[0] / Path(logo_path))
    click.secho("=" * 80, fg="white", bold=True)

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
            f"version: {_magtogoek_version}" + f" {group} ".rjust(67, " "),
            fg="green",
            bold=True,
        )
    )
    click.echo(click.style("=" * 80, fg="white", bold=True))


def _print_arguments(group):
    """print group(command) command(arguments)"""
    if group == "mtgk":
        click.secho(
            "  config".ljust(20, " ") + "Command to make configuration files",
            fg="white",
        )
        click.secho("  process".ljust(20, " ") + "Command to process data", fg="white")
    if group == "config":
        click.secho("  adcp".ljust(20, " ") + "Config file for adcp data. ", fg="white")
    if group == "process":
        click.secho("FIXME")
    if group == "adcp":
        click.secho(
            "  [config_name]".ljust(20, " ")
            + "File name (path/to/file) for the new configuration file.",
            fg="white",
        )


def _print_description(group):
    """print group/command desciptions"""
    if group == "mtgk":
        click.echo("""FIXME""")
    if group == "config":
        click.echo(
            """  The config command creates a `.ini`  configuration file. After the command is
  called, a `sensor_type` (type of date to be process) and  a `config_name` for
  the configuration file. The configuration file  can then be passed to  to the
  process command.

  The configuration `.ini` files  contain global and sensor specific parameters.
  These parameters can be edited afterward in a text editor  or set here with
  optionals arguments.""",
        )
    if group == "process":
        click.echo("""FIXME""")
    if group == "adcp":
        click.echo(""" FIXME""")


def _print_usage(group, parent):
    """print group/command usage"""
    if group in ["mtgk", "config"]:
        click.echo("""    mtgk config [adcp, ] [CONFIG_NAME] [OPTIONS]""")
    if group in ["mtgk", "process"]:
        click.echo("""    mtgk process [adcp, ] [CONFIG_FILE] [OPTIONS]""")
    if group in ["adcp", "process"]:
        if parent == "config":
            click.echo("""    mtgk process [adcp, ] [CONFIG_FILE] [OPTIONS]""")
