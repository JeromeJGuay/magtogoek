"""
module to export adcp dataset to Odf
"""
import xarray as xr
from typing import List, Union, Tuple, Dict, Optional
from magtogoek import CONFIGURATION_PATH

from magtogoek.odf_format import Odf
from magtogoek.odf_exporter_common import make_cruise_header, make_event_header, make_odf_header, \
    make_instrument_header, make_buoy_header, make_buoy_instrument_headers,  make_quality_header, make_history_header, \
    make_parameter_headers, build_comments_string, write_odf
from magtogoek.platforms import PlatformMetadata
from magtogoek.utils import json2dict


BEAM_PARAMETERS = ("time", "depth", "v1", "v2", "v3", "v4")
VEL_PARAMETERS = ("time", "depth", "u", "v", "w", "e")
ANC_PARAMETERS = ('time', 'pitch', 'roll_', 'heading', 'pres', 'temperature', 'lon', 'lat')
QC_PARAMETERS = ('u', 'v', 'w', 'pres', 'temperature')

PARAMETERS_METADATA_PATH = CONFIGURATION_PATH.joinpath("odf_parameters_metadata.json")
PARAMETERS_METADATA = json2dict(PARAMETERS_METADATA_PATH)


def make_odf(
        dataset: xr.Dataset,
        platform_metadata: PlatformMetadata,
        adcp_id: str,
        global_attributes: dict,
        p01_codes_map: dict,
        use_bodc_name: bool = True,
        odf_dtype: str = 'VEL',
        output_path: Optional[str] = None
):
    """

    Parameters
    ----------
    dataset :
        Dataset to which add the navigation data.
    platform_metadata :
        Metadata from the platform file.
    adcp_id :
        instrument_id of the adcp in the platform_metadata.
    global_attributes :
        Global attributes parameter from the configFile.
    p01_codes_map :
        generic name to bodc p01_code mapping.
    use_bodc_name:
        If True, map from the generic to the BODC p01 variables names.
    odf_dtype:
        Either `'VEL'` or `'ANC'`.
    output_path:
        If a path(str) is provided, there are two possibilities: if the path is only a directory, the file name
        will be made from the odf['file_specification']. If a file name is also provided, the 'event_qualifier2'
        will be appended to it if it's not present in the `output_path`.

    """
    odf = Odf()

    make_cruise_header(odf=odf, platform_metadata=platform_metadata, config_attrs=global_attributes)
    make_event_header(odf=odf, dataset=dataset, config_attrs=global_attributes, event_qualifier2=odf_dtype)
    _set_event_header_depths(odf, dataset, p01_codes_map=p01_codes_map)
    make_odf_header(odf)

    if platform_metadata.platform.platform_type == "buoy":
        make_buoy_header(odf, platform_metadata)
        make_buoy_instrument_headers(odf, platform_metadata)
        _make_adcp_buoy_instrument_header(odf=odf, dataset=dataset, platform_metadata=platform_metadata, adcp_id=adcp_id)
    else:
        make_instrument_header(odf, dataset)

    make_quality_header(odf, dataset)
    make_history_header(odf)

    if odf_dtype == 'VEL':
        if dataset.attrs['coord_system'] == 'beam':
            parameters = BEAM_PARAMETERS
        else:
            parameters = VEL_PARAMETERS
    else:
        parameters = ANC_PARAMETERS

    make_parameter_headers(odf=odf, dataset=dataset, variables=parameters, qc_variables=QC_PARAMETERS, p01_codes_map=p01_codes_map, bodc_name=use_bodc_name)

    if output_path is not None:
        write_odf(odf=odf, output_path=output_path)

    return odf


def _make_adcp_buoy_instrument_header(
        odf: Odf, dataset: xr.Dataset,
        platform_metadata: PlatformMetadata,
        adcp_id
        : str,
):

    if adcp_id not in odf.buoy_instrument:
        odf.add_buoy_instrument(adcp_id)

    key_map = [
        ('type', 'manufacturer'),
        ('model', 'model'),
        ('serial_number', 'serial_number'),
        ('description', 'description')
    ]

    for (odf_key, netcdf_key) in key_map:
        if netcdf_key in dataset.attrs:
            odf.buoy_instrument[adcp_id][odf_key] = dataset.attrs[netcdf_key]

    _make_adcp_buoy_instrument_comments(odf, adcp_id, dataset, platform_metadata)


def _make_adcp_buoy_instrument_comments(
        odf: Odf,
        adcp_id: str,
        dataset: xr.Dataset,
        platform_metadata: PlatformMetadata
):
    """

    BUOY_INSTRUMENT_HEADER
      .
      .
      BUOY_INSTRUMENT_COMMENTS= '',
      .
      .

    """
    configuration = "CONFIGURATION_01"
    buoy_instrument_comments = []
    key_map = [
        ("Mode", "orientation"),
        ("Ping_Type", "ping_type"),
        ("Frequency", "frequency"),
        ("Firmware_Version", "firmware_version"),
        ("Ping_per_Ensemble", "ping_per_ensemble"),
        ("Ensemble_Length_s", "delta_t_sec"),
        ("ADCP_Depth_m", "sensor_depth"),
        ("Distance_ADCP_to_First_Bin_Center_m", "bin1dist"),
        ("Bin_Size_m", "bin_size"),
        ("Blank_m", "blank"),
        ("Transmit_Pulse_Length_m", "transmit_pulse_length_m")
    ]

    for odf_key, netcdf_key in key_map:
        if netcdf_key in dataset.attrs:
            buoy_instrument_comments.append((odf_key, dataset.attrs[netcdf_key]))

    if "ping_per_ensemble" in dataset.attrs and "delta_t_sec" in dataset.attrs:
        if dataset.attrs["ping_per_ensemble"] and dataset.attrs["delta_t_sec"]:
            ping_interval_s = dataset.attrs["ping_per_ensemble"] / dataset.attrs["delta_t_sec"]
            buoy_instrument_comments.append(("Ping_Interval_s", round(ping_interval_s, 2)))

    if "magnetic_declination" in dataset.attrs and "magnetic_declination_units" in dataset.attrs:
        magnetic_declination = f"{dataset.attrs['magnetic_declination']} {dataset.attrs['magnetic_declination_units']}"

        buoy_instrument_comments.append(("Magnetic_Declination", magnetic_declination))

    buoy_instrument_comments += [
        ("Bin_Count", len(dataset.depth)),
        ("Comments", platform_metadata.instruments[adcp_id].comments)
    ]

    odf.buoy_instrument[adcp_id
    ]["buoy_instrument_comments"] = []
    for (key, value) in buoy_instrument_comments:
        odf.buoy_instrument[adcp_id
        ]["buoy_instrument_comments"].append(
            build_comments_string([configuration, key], value)
        )


def _set_event_header_depths(odf: Odf, dataset: xr.Dataset, p01_codes_map: dict) -> None:
    """ Set even header depths metadata from dataset.

    Sets :
     - min_depth, max_depth
     - depth_off_bottom

    Parameters
    ----------
    odf :
    dataset :
    """
    if odf.event['event_qualifier2'] == 'ANC':
        if 'xducer_depth' in dataset:
            odf.event['min_depth'] = dataset['xducer_depth'].values.min()
            odf.event['max_depth'] = dataset['xducer_depth'].values.max()
        elif p01_codes_map['xducer_depth'] in dataset:
            odf.event['min_depth'] = dataset[p01_codes_map['xducer_depth']].values.min()
            odf.event['max_depth'] = dataset[p01_codes_map['xducer_depth']].values.max()
        else:
            odf.event['min_depth'] = dataset.attrs['sensor_depth']
            odf.event['max_depth'] = dataset.attrs['sensor_depth']
    elif 'depth' in dataset.variables:
        odf.event['min_depth'] = dataset.depth.values.min()
        odf.event['max_depth'] = dataset.depth.values.max()

    if all(odf.event[key] is not None for key in ('sounding', 'max_depth')):
        odf.event["depth_off_bottom"] = odf.event['sounding'] - odf.event['max_depth']