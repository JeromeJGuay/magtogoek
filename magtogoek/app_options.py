"""
Script that contains different click options and the functions to add them to the click command.

"""

import click


def add_options(options):
    """decorator to pass list of options to click commands."""

    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func

    return _add_options


def general_options(input_files=True):
    """Return shared general options. They can be passed to Click using @add_options()

     Parameters:
    ----------
    inputs_files:
        Adds input_options

        """
    options = []
    if input_files:
        options += [
            click.option(
                "-i",
                "--input-files",
                multiple=True,
                type=click.Path(exists=True),
                help="Expression identifying adcp files. Call `-i` for each files.",
            )
        ]
    options += [
        click.option(
            "-n",
            "--netcdf-output",
            nargs=1,
            type=click.STRING,
            help="Expression for netcdf output file or files name",
        ),
        click.option(
            "-o",
            "--odf-output",
            nargs=1,
            type=click.STRING,
            help="Expression for odf file or files name",
        ),
        click.option(
            "--merge/--no-merge",
            help="""Merge input into one output file.,
        Default --merge""",
            default=True,
        ),
        click.option(
            "-N",
            "--navigation_file",
            type=click.Path(exists=True),
            help="""path/to/netcdf4 file containing the nav data made with
                the `make_navigation` function. (`from magtogoek.utils import make_navigation`)""",
        ),
        click.option(
            "--mk-log/--no-log",
            help="""Make an output log of the processing.""",
            default=True,
            show_default=True,
        ),
        click.option(
            "--mk-fig/--no-fig",
            help="""Make figures to inspect the data.""",
            default=True,
            show_default=True,
        ),
        click.option(
            "--bodc-name/--gen-name",
            help="""Name of the output variables. Using --gen-name
        outputs generic variables names instead of BODC P01 name.
        [default: --bodc-name]""",
            default=True,
        ),
        click.option(
            "--qc/--no-qc", help="Do quality control.", default=True, show_default=True,
        ),
    ]

    return options


def adcp_options(sonar=True):
    """Return shared adcp options. They can be passed to Click using @add_options()

    Parameters:
    ----------
    yearbase:
        Adds yearbase
    sonar:
        Adds sonar
    """
    options = []

    if sonar:
        options += [
            click.option(
                "-s",
                "--sonar",
                type=click.Choice(["wh", "sv", "os", "sw", "sw_pd0"]),
                help="""String designating the type of adcp. Use --info option for more information.""",
            )
        ]
    options += [
        click.option(
            "-y",
            "--yearbase",
            type=click.INT,
            help="""Year when the adcp sampling started. ex: `1970`""",
            required=False
        ),
        click.option("-T", "--platform_type", type=click.Choice(["buoy", "mooring", "ship", "lowered"]),
                     help="Used for Proper BODC variables names", default="buoy"),
        click.option(
            "-O",
            "--adcp-orientation",
            type=click.Choice(["up", "down"]),
            help="""Vertical orientation of the adcp.""",
            default=None,
            show_default=True,
        ),
        click.option(
            "-m",
            "--magnetic-declination",
            type=click.FLOAT,
            help="""Declination of the magnetic north in degree east.
            Corrects from magnetic to true (geographic) coordinates.""",
            default=None,
            show_default=True,
        ),
        click.option(
            "-l",
            "--leading-trim",
            type=click.STRING,
            help="""Removes a count of leading data or data before a given date or datetime.
    Formats: Date "YYYY-MM-DD" or "YYYY-MM-DDThh:mm:ss.ssss",  Count (int): """,
            nargs=1,
            default=None,
        ),
        click.option(
            "-t",
            "--trailing-trim",
            type=click.STRING,
            help="""Removes a count of trailing data or data after a given date or datetime.
    Formats: Date "YYYY-MM-DD" or "YYYY-MM-DDThh:mm:ss.ssss",  Count (int): """,
            nargs=1,
            default=None,
        ),
        click.option(
            "--sidelobes/--no-sidelobes",
            help="Do side lobe correction. Uses bottom_track if available. See option `--bottom-depth` "
                 "to force a bottom_depth.",
            default=True,
            show_default=True,
        ),
        click.option(
            "-b",
            "--bottom-depth",
            type=click.FLOAT,
            help="""If provided, this constant bottom_depth will be
            used for sidelobes correction.""",
            default=None,
            show_default=True,
        ),
        click.option(
            "-d",
            "--sensor-depth",
            type=click.FLOAT,
            help="""If provided, the adcp depth (XducerDepth) will be adjusted so that its median value equal the 
            given `sensor_depth` value.""",
            default=None,
            show_default=True,
        ),
        click.option(
            "--bad-pressure/-",
            help="""Use the `--bad-pressure` flag to discard pressure data from the processing.
            This will in turn discard the adcp depth (XducerDepth) measured by the ADCP.
            Use the option `--sensor-depth` to enter a constant xducer depth.""",
            default=False,
            show_default=True,
        ),
        click.option(
            "-r",
            "--depth_range",
            type=click.FLOAT,
            nargs=1,
            help="""Specify, 1 or 2 value. Either `-r min`, or `-r min -r max` in meter.
            All bin outside this range will be cut.""",
            default=None,
            multiple=True,
        ),
        click.option("--ct/--no-ct", help="Use to do Coordinate Transformation (ct)", default=True),
        click.option(
            "--start_time",
            type=click.STRING,
            help="""Format 'YYYY-MM-DDThh:mm:ss.ssss'.
        If provided, a new time coordinate vector, starting at `start_time`, is used instead of the one found in the 
        raw adcp file. Use the parameter `time_step` to use a different time step than the one found in the 
        adcp raw adcp file.
        """,
            nargs=1,
            default=None,
        ),
        click.option(
            "--time_step",
            type=click.FLOAT,
            help="Time step in seconds. Only use if a `start_time` value is provided.",
            nargs=1,
            default=None,
        ),
        click.option(
            "-a",
            "--amplitude-threshold",
            type=click.FloatRange(0, 255),
            help="Amplitude threshold (0-255). Defaults to 0.",
            nargs=1,
            default=0,
            show_default=True,
        ),
        click.option(
            "-p",
            "--percentgood-threshold",
            type=click.FloatRange(0, 100),
            help="Percentage of 4 beam threshold (0-100). Defaults to 90.",
            default=90,
            show_default=True,
        ),
        click.option(
            "-c",
            "--correlation-threshold",
            type=click.FloatRange(0, 255),
            help="Correlation threshold (0-255).",
            nargs=1,
            default=64,
            show_default=True,
        ),
        click.option(
            "-u",
            "--horizontal-velocity-threshold",
            type=click.FloatRange(0),
            help="Horizontal velocity threshold (u,v). [m/s]",
            nargs=1,
            default=5,
            show_default=True,
        ),
        click.option(
            "-w",
            "--vertical-velocity-threshold",
            type=click.FloatRange(0),
            help="Vertical velocity threshold (w).  [m/s]",
            nargs=1,
            default=5,
            show_default=True,
        ),
        click.option(
            "-e",
            "--error-velocity-threshold",
            type=click.FloatRange(0),
            help="Error velocity threshold. [m/s]",
            nargs=1,
            default=5,
            show_default=True,
        ),
        click.option(
            "-P",
            "--pitch-threshold",
            type=click.FloatRange(0, 180),
            help="Pitch threshold (0-180).",
            nargs=1,
            default=20,
            show_default=True,
        ),
        click.option(
            "-R",
            "--roll-threshold",
            type=click.FloatRange(0, 180),
            help="Roll threshold (0-180).Defaults to 20.",
            nargs=1,
            default=20,
            show_default=True,
        ),
        click.option(
            "--drop-pg/--keep-pg",
            help="""Drop the percent good data from the output dataset.
        [default: --drop-pg]""",
            default=True,
        ),
        click.option(
            "--drop-corr/--keep-corr",
            help="""Drop the correlation data from the output dataset.
        [default: --drop-corr]""",
            default=True,
        ),
        click.option(
            "--drop-amp/--keep-amp",
            help="""Drop the amplitude data from the output dataset.
        [default: --drop-amp]""",
            default=True,
        ),
        click.option(
            "--keep_bt/--discard-bt",
            help="""Weather to use or discard the bottom (bt) track data.""",
            default=True,
            show_default=True,
        ),
        click.option(
            "-M",
            "--motion_correction_mode",
            help="""Corrects motion with bottomTrack `bt` or navigation `nav`. Use
                `off` turn off motion correction mode.
                For `nav`, a netcdf file made with `magtogoek.navigation` needs to be
                with options `-N` for the `nav` option.""",
            default="bt",
            type=click.Choice(["bt", "nav", "off"]),
        ),
    ]

    return options
