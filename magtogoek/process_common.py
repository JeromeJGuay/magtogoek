"""
Date: February 2023
Made by jeromejguay

Common function used for processing data.
"""
import sys
import click

import pandas as pd
import typing as tp
import xarray as xr
from pathlib import Path

from magtogoek import TERMINAL_WIDTH, DEFAULT_PLATFORM_TYPE
from magtogoek import logger as l
from magtogoek.exceptions import MagtogoekExit
from magtogoek.attributes_formatter import compute_global_attrs
from magtogoek.navigation import load_navigation
from magtogoek.platforms import PlatformMetadata, load_platform_metadata
from magtogoek.utils import ensure_list_format


CONFIG_GLOBAL_ATTRS_SECTIONS = ["NETCDF_CF", "PROJECT", "CRUISE", "GLOBAL_ATTRIBUTES"]

ADCP_DATA_TYPES = { # SHOULDN'T THIS BE IN THE adcp/__init__.py FIXME
    "buoy": "madcp",
    "mooring": "madcp",
    "ship": "adcp",
    "lowered": "adcp"
}
METOCE_DATA_TYPE = "MMOB" # SHOULDN'T THIS BE IN THE adcp/__init__.py FIXE

DATA_SUBTYPES = {
    "buoy": "BUOY",
    "mooring": "MOORED",
    "ship": "SHIPBORNE",
    'lowered': 'LOWERED'
}

TIME_ENCODING = {
    "units": "seconds since 1970-1-1 00:00:00Z",
    "calendar": "gregorian",
    "_FillValue": None,
    "dtype": "i4"
}
TIME_STRING_ENCODING = {"dtype": "S1"}
DEPTH_ENCODING = {
    "_FillValue": -9999.0,
    "dtype": "float32",
}
QC_FILL_VALUE = 127
QC_ENCODING = {"dtype": "int8", "_FillValue": QC_FILL_VALUE}

DATA_FILL_VALUE = -9999.0
DATA_ENCODING = {"dtype": "float32", "_FillValue": DATA_FILL_VALUE}

FLAG_ATTRIBUTES = {
    "flag_meanings": "BODC SeaDataNet",
    "flag_values": (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    "flag_reference": (
        "no_quality_control",
        "good_value",
        "probably_good_value",
        "probably_bad_value",
        "bad_value",
        "changed_value",
        "value_below_detection",
        "value_in_excess",
        "interpolated_value",
        "missing_value"
    )
}


class BaseProcessConfig:
    config_file: str = None
    process: str = None
    platform_type: str = None
    platform_file: str = None
    platform_id: str = None

    input_files: tp.Union[str, tp.List[str]] = None
    netcdf_output: tp.Union[str, bool] = None
    odf_output: tp.Union[str, bool] = None

    navigation_file: str = None
    start_trim_time: str = None
    end_trim_time: str = None
    start_trim_index: int = None
    end_trim_index: int = None
    merge_output_files: bool = None
    use_bodc_name: bool = None
    force_platform_metadata: bool = None

    make_figures: tp.Union[str, bool] = None
    make_log: bool = None

    from_raw: bool = None

    # Variables set internally for processing.
    netcdf_raw_path: str = None
    netcdf_path: str = None
    odf_path: str = None
    log_path: str = None
    figures_path: str = None
    figures_output: bool = None

    headless: bool = False

    variables_to_drop: tp.List[str] = None
    global_attributes_to_drop: tp.List[str] = None
    drop_empty_attrs: bool = False
    p01_codes_map: tp.Dict[str, str] = None
    global_attributes: dict = None

    # platform metadata object
    platform_metadata: tp.Optional[PlatformMetadata] = None

    def __init__(self, config_dict: dict = None):
        self.global_attributes: dict = {}

        if config_dict is not None:
            self._load_config_dict(config_dict)

        if isinstance(self.input_files, str):
            self.input_files = ensure_list_format(self.input_files)

        if len(self.input_files) == 0:
            raise ValueError("No input file was provided in the configfile.")

        self._load_platform_metadata()

        if self.platform_type is None:
            self.platform_type = DEFAULT_PLATFORM_TYPE

    def _load_config_dict(self, config: dict):
        """Split and flattens"""
        for section, options in config.items():
            if section in CONFIG_GLOBAL_ATTRS_SECTIONS:
                for option in options:
                    self.global_attributes[option] = config[section][option]
            else:
                for option in options:
                    if hasattr(self, option):
                        self.__dict__[option] = config[section][option]

    def _load_platform_metadata(self):
        if self.platform_file is not None:
            if Path(self.platform_file).is_file():
                self.platform_metadata = load_platform_metadata(self.platform_file, self.platform_id)
            else:
                raise MagtogoekExit(f"platform_file, {self.platform_file}, not found. Exiting")

            self.platform_type = self.platform_metadata.platform.platform_type
        else:
            self.platform_metadata = None


def add_global_attributes(dataset: xr.Dataset, pconfig: BaseProcessConfig, standard_global_attributes: dict):
    """w
    pconfig.global_attributes values will overwrite any values in the dataset global attributes previously set.
    That is values in the configfile headers ["NETCDF_CF", "PROJECT", "CRUISE", "GLOBAL_ATTRIBUTES"].

    Parameters
    ----------
    dataset
    pconfig
    standard_global_attributes :
        Used to update the dataset attributes

    Returns
    -------

    """

    dataset.attrs.update(standard_global_attributes)

    dataset.attrs["data_type"] = _get_data_type(pconfig.process, pconfig.platform_type)
    dataset.attrs["data_subtype"] = DATA_SUBTYPES[pconfig.platform_type]

    compute_global_attrs(dataset)  # already common

    source = pconfig.platform_type
    if "source" in pconfig.global_attributes:
        source = pconfig.global_attributes.pop('source') or source
    dataset.attrs["source"] = source

    dataset.attrs.update(pconfig.global_attributes)


def add_platform_metadata_to_dataset(dataset: xr.Dataset, pconfig: BaseProcessConfig):
    """Add pconfig.platform_metadata.platform attributes not Instrument or buoy.

    Attributes are only added if they are not null.

    """
    if pconfig.platform_metadata is not None:
        metadata_map = {
            'platform': pconfig.platform_metadata.platform.platform_name,
            'platform_model': pconfig.platform_metadata.platform.platform_model,
            'sounding': pconfig.platform_metadata.platform.sounding,
            'longitude': pconfig.platform_metadata.platform.longitude,
            'latitude': pconfig.platform_metadata.platform.latitude,
            'platform_description': pconfig.platform_metadata.platform.description
        }

        for key, value in metadata_map.items():
            if value is None:
                continue

            if key in dataset.attrs and not pconfig.force_platform_metadata:
                if dataset.attrs[key] is None or dataset.attrs[key] in ["NA", ""]:
                    dataset.attrs[key] = value
            else:
                dataset.attrs[key] = value


def _get_data_type(process: str, platform_type: str = None):
    """Return data_type for the given process and platform_type.
    """
    if process == 'metoce':
        return METOCE_DATA_TYPE
    elif process == "adcp":
        if platform_type is None:
            platform_type = DEFAULT_PLATFORM_TYPE
        return ADCP_DATA_TYPES[platform_type]
    raise ValueError(f"Invalid process type. {process}")


def resolve_output_paths(process_function: tp.Callable[[BaseProcessConfig], None]):
    """Decorator that wraps around a process_function e.g. metoce.process.process_viking.

    If `pconfig.merge_output_files` is False, each input file is process individually and output
    names suffixes are made for each file if needed, before calling the process_function.

    Then paths are figures out. See `magtogoek.process_common._resolve_outputs`.

    Parameters
    ----------
    process_function

    """
    def inner(pconfig: BaseProcessConfig, *args):
        if pconfig.merge_output_files is True:
            _resolve_outputs(pconfig)
            process_function(pconfig, *args)

        else:
            config_file = pconfig.config_file
            input_files = [fn for fn in pconfig.input_files]
            odf_output = pconfig.odf_output
            netcdf_output = pconfig.netcdf_output

            if 'event_qualifier1' not in pconfig.global_attributes:
                pconfig.global_attributes['event_qualifier1'] = "" # Maybe that is not the best way to do it. Required for ODF

            event_qualifier1 = pconfig.global_attributes['event_qualifier1']

            for count, filename in enumerate(input_files):
                pconfig.input_files = [filename]
                pconfig.odf_output = odf_output
                pconfig.netcdf_output = netcdf_output

                # If the user set path ...
                if isinstance(netcdf_output, str):
                    # If the path is a filename ...
                    if not Path(netcdf_output).is_dir():
                        # An incrementing suffix is added to the filename
                        pconfig.netcdf_output = str(Path(netcdf_output).with_suffix("")) + f"_{count}"

                    else:
                        pconfig.config_file = str(Path(config_file).with_suffix("")) + f"_{count}"
                elif netcdf_output is True:
                    pconfig.config_file = str(Path(config_file).with_suffix("")) + f"_{count}"

                # If the user set path ...
                if isinstance(odf_output, str):
                    # If the path is a filename ...
                    if not Path(odf_output).is_dir():
                        # An incrementing suffix is added to the filename
                        pconfig.odf_output = str(Path(odf_output).with_suffix("")) + f"_{count}"
                    # If it's a directory
                    else:
                        # A suffix (input filename) is added to the event_qualifier that builds the filename
                        # PREVENTS FROM OVERWRITING THE SAME FILE
                        pconfig.global_attributes['event_qualifier1'] = event_qualifier1 + f"_{count}"
                        pconfig.config_file = str(Path(config_file).with_suffix("")) + f"_{count}"
                elif odf_output is True:
                    # A suffix (input filename) is added to the event_qualifier that builds the filename
                    # PREVENTS FROM OVERWRITING THE SAME FILE
                    pconfig.global_attributes['event_qualifier1'] = event_qualifier1 + f"_{count}"
                    pconfig.config_file = str(Path(config_file).with_suffix("")) + f"_{count}"

                _resolve_outputs(pconfig)

                process_function(pconfig, *args)

                click.echo(click.style("=" * TERMINAL_WIDTH, fg="white", bold=True))
    return inner


def _resolve_outputs(pconfig: BaseProcessConfig):
    """Figure out what outputs to make and their respective paths.

    ~~~ To whom ever reads the code that follows, I'm sorry. ~~~

    There is three parameters the user can set in the `pconfig`:

        [`netcdf_output`, `odf_output`,  `figure_output`]

    They can all have values of:
        - None
        - bool
        - `file name`
        - `path to directory`
        - `path to directory` + `file name`

    --- Logic Flow ---

    1. `default_path` and `default_filename` are defined. if the processing was done with
        a) a config file (.ini) they are respectively to path to the config file its name.
        b) the `quick` command, they are respectively the path to the first input file and its name.

    2. If both `netcdf_output`, `odf_output` are `False`, `nc_output` is set True.

    3. If `netcdf_output` is not `None` or `False`:
        a) Depending on the value of `netcdf_output`: True, a filename, a path to directory or a path to a filename,
           an output path is build using `default_path` and `default_filename` if needed.

        b) Updates `default_path` and `default_filename` using `netcdf_path` value.

    4. If `odf_output` is not `None` or `False`:
        a) Depending on the value of `odf_output`: True, a filename, a path to directory or a path to a filename,
           an output path is build using `default_path` if needed. ODF doesn't require a filename since it is built
           by default using metadata in the ODF file. Thus, `default_filename` is not used and will only be updated
           if `netcdf_output` is False and `odf_output` contains a filename.

        b) If `netcdf_output` is `False`:
           Updates `default_path` using `odf_path` value. Updates `default_filename` if `odf_path` has a filename
           otherwise it stays the same.

    5. If `make_figure` is not `None` or `False`:
        a) If `make_figure` is True, `figure_output` is set True.
            If `headless` is `True`. `figure_path` is build using `default_path` and `default_filename`.
        b) A path to directory or a path to a filename is build using `default_path` and `default_filename` if needed.
            Every figure filename will have a suffix added to it.


    6. `log_path` is made using `default_path` and `default_filename`.

    ...

    """

    if pconfig.config_file is not None:
        default_path, default_filename = Path(pconfig.config_file).parent, Path(pconfig.config_file).stem
    else:
        default_path, default_filename = Path(pconfig.input_files[0]).parent, Path(pconfig.input_files[0]).stem

    if not pconfig.odf_output and not pconfig.netcdf_output:
        pconfig.netcdf_output = True

    if pconfig.netcdf_output:
        _make_netcdf_output_path(pconfig, default_path, default_filename)
        default_path, default_filename = Path(pconfig.netcdf_path).parent, Path(pconfig.netcdf_path).stem

    if pconfig.odf_output:
        _make_odf_output_path(pconfig, default_path)
        if not pconfig.netcdf_output:
            if not is_directory(pconfig.odf_path):
                default_path, default_filename = Path(pconfig.odf_path).parent, Path(pconfig.odf_path).stem
            else:
                default_path = Path(pconfig.odf_path)

    if pconfig.make_figures:
        _make_figure_output_path(pconfig, default_path, default_filename)

    pconfig.log_path = str(default_path.joinpath(default_filename))
    pconfig.netcdf_raw_path = str(default_path.joinpath(default_filename + '_raw'))


def _make_netcdf_output_path(pconfig: BaseProcessConfig, default_path: Path, default_filename: Path):
    if not pconfig.netcdf_output:
        pass
    elif pconfig.netcdf_output is True:
        pconfig.netcdf_path = str(default_path.joinpath(default_filename))
    else:
        if is_only_filename(pconfig.netcdf_output):
            netcdf_path = default_path.joinpath(Path(pconfig.netcdf_output)).resolve()
        elif is_directory(pconfig.netcdf_output):
            netcdf_path = Path(pconfig.netcdf_output).joinpath(default_filename)
        elif parent_is_dir(pconfig.netcdf_output):
            netcdf_path = Path(pconfig.netcdf_output)
        else:
            raise ValueError(f'Netcdf output path to, {pconfig.netcdf_output}, does not exists.')

        pconfig.netcdf_path = str(netcdf_path)
        pconfig.netcdf_output = True


def _make_odf_output_path(pconfig: BaseProcessConfig, default_path: Path):
    if not pconfig.odf_output:
        pass
    elif pconfig.odf_output is True:
        pconfig.odf_path = str(default_path)
    else:
        if is_only_filename(pconfig.odf_output):
            odf_path = default_path.joinpath(Path(pconfig.odf_output)).resolve()
        elif is_directory(pconfig.odf_output):
            odf_path = Path(pconfig.odf_output)
        elif parent_is_dir(pconfig.odf_output):
            odf_path = Path(pconfig.odf_output)
        else:
            raise ValueError(f'Odf output path, {pconfig.odf_output}, does not exists.')

        pconfig.odf_path = str(odf_path)
        pconfig.odf_output = True


def _make_figure_output_path(pconfig: BaseProcessConfig, default_path: Path, default_filename: Path):
    if not pconfig.make_figures:
        pass
    elif pconfig.make_figures is True:
        pconfig.figures_output = True
        if pconfig.headless is True:
            pconfig.figures_path = str(default_path.joinpath(default_filename))
    else:
        pconfig.figures_output = True
        if is_only_filename(pconfig.make_figures):
            figures_path = default_path.joinpath(Path(pconfig.make_figures)).resolve()
        elif is_directory(pconfig.make_figures):
            figures_path = Path(pconfig.make_figures).joinpath(default_filename)
        elif parent_is_dir(pconfig.make_figures):
            figures_path = Path(pconfig.make_figures)
        else:
            raise ValueError(f'Figure output path, `{pconfig.make_figures}`, does not exists.')

        pconfig.figures_path = str(figures_path)
        pconfig.figures_output = True


def is_only_filename(path: str):
    return Path(path).name == path


def is_directory(path: str):
    return Path(path).is_dir()


def parent_is_dir(path: str):
    return Path(path).parent.is_dir()


def write_netcdf(dataset: xr.Dataset, pconfig: BaseProcessConfig):
    netcdf_path = Path(pconfig.netcdf_path).with_suffix('.nc')
    dataset.to_netcdf(netcdf_path)
    l.log(f"netcdf file made -> {netcdf_path}")


def netcdf_raw_exist(pconfig: BaseProcessConfig):
    return Path(pconfig.netcdf_raw_path).with_suffix('.nc').exists()


def load_netcdf_raw(pconfig: BaseProcessConfig) -> xr.Dataset:
    netcdf_raw_path = Path(pconfig.netcdf_raw_path).with_suffix('.nc')
    dataset = xr.open_dataset(netcdf_raw_path)

    l.append_to_logbook(dataset.attrs.pop('history'))

    return dataset


def write_netcdf_raw(dataset: xr.Dataset, pconfig: BaseProcessConfig):
    netcdf_raw_path = Path(pconfig.netcdf_raw_path).with_suffix('.nc')

    dataset.attrs['history'] = l.logbook

    dataset.to_netcdf(netcdf_raw_path)
    dataset.close()
    l.log(f"netcdf raw file made -> {netcdf_raw_path}")


def write_log(pconfig: BaseProcessConfig):
    log_path = Path(pconfig.log_path).with_suffix(".log")
    l.write(log_path)


def add_processing_timestamp(dataset: xr.Dataset):
    if not dataset.attrs["date_created"]:
        dataset.attrs["date_created"] = pd.Timestamp.now().strftime("%Y-%m-%d")
    dataset.attrs["date_modified"] = pd.Timestamp.now().strftime("%Y-%m-%d")


def clean_dataset_for_nc_output(dataset: xr.Dataset,
                                pconfig: BaseProcessConfig,
                                ) -> xr.Dataset:
    """ Clean dataset for netcdf output.

    Drops variables in `pconfig.variables_to_drop`
    Drops global attributes in `pconfig.global_attributes_to_drop.`
    Drops empty/null global attributes if `pconfig.drop_empty_attrs` is True.
        else sets them to an empty string.

    """
    dataset = dataset.drop_vars(
        set(pconfig.variables_to_drop).intersection(set(dataset.variables))
    )

    for attr in set(pconfig.global_attributes_to_drop).intersection(set(dataset.attrs)):
        del dataset.attrs[attr]

    for attr in list(dataset.attrs.keys()):
        if not dataset.attrs[attr]:
            if pconfig.drop_empty_attrs is True:
                del dataset.attrs[attr]
            else:
                dataset.attrs[attr] = ""
    return dataset


def format_data_encoding(dataset: xr.Dataset):
    """Format data encoding with default value in module. Requires generic variable names."""

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


def add_navigation(dataset: xr.Dataset, navigation_files: str):
    """Load navigation data to `dataset` from nmea, gpx or netcdf files.

    Returns the dataset with the added navigation data. Data from the navigation file
    are interpolated on the dataset time vector.

    Use to load:
        `lon, `lat`,
        `u_shp`, `v_ship`
        `roll_`, `pitch`, `heading`

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
    try:
        nav_ds = load_navigation(navigation_files)
    except ValueError as msg:
        l.warning(f'Unable to load the navigation file.\n\t Error: {msg}')
        nav_ds = None # FIXME test ADDED on JUNE 7 2023. Seemed necessary.

    if nav_ds is not None:
        if 'time' in nav_ds.coords:
            nav_ds = nav_ds.interp(time=dataset.time)
            if all([var in nav_ds for var in ('lon', 'lat')]):
                dataset['lon'] = nav_ds['lon']
                dataset['lat'] = nav_ds['lat']
                l.log("Platform GPS data (longitude, latitude) loaded.")

            if all([var in nav_ds for var in ('u_ship', 'v_ship')]):
                dataset['u_ship'] = nav_ds['u_ship']
                dataset['v_ship'] = nav_ds['v_ship']
                l.log("Platform velocity data (u_ship, v_ship) loaded.")

            if all([var in nav_ds for var in ('heading', 'pitch', 'roll_')]):
                dataset['heading'] = nav_ds['heading']
                dataset['pitch'] = nav_ds['pitch']
                dataset['roll_'] = nav_ds['roll_']
                l.log("Platform inertial data (heading, pitch, roll) loaded.")
            nav_ds.close()
        else:
            l.warning('Could not load navigation data file. `time` coordinate was massing.')
    else:
        l.warning('Could not load navigation data file.')


def add_correction_attributes_to_dataarray(dataarray: xr.DataArray):
    """Add corrections (str) attributes to dataarray if it does not exist.
    """
    attr_name = "corrections"
    if attr_name not in dataarray.attrs:
        dataarray.attrs[attr_name] = ""
