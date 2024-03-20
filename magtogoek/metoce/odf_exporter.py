"""
Module to map xarray dataset to Odf

Date: July 25 2022
Made by: jeromejguay


METOCE BODC:
        Time                                                 : SYTM_01 : SDN:P01::ELTMEP01
        Longitude (East +ve)                                 : LOND_01 : SDN:P01::ALONZZ01
        Latitude (North +ve)                                 : LATD_01 : SDN:P01::ALATZZ01
        Horizontal Wind Speed                                : WSPD_01 : SDN:P01::EWSBSS01
        Gust Wind Speed                                      : GSPD_01 : SDN:P01::EGTSSS01
        Wind Direction relative to North (T)                 : WDIR_01 : SDN:P01::EWDASS01
        Dry Bulb Temperature                                 : DRYT_01 : SDN:P01::CTMPZZ01
        Relative Humidity                                    : RELH_01 : SDN:P01::CRELZZ01
        Atmospheric pressure                                 : ATMP_01 : SDN:P01::CAPHZZ01
        Temperature (1990 scale)                             : TE90_01 : SDN:P01::TEMPPR01
        Electrical Conductivity                              : CNDC_01 : SDN:P01::CNDCZZ01
        Practical Salinity                                   : PSAL_01 : SDN:P01::PSLTZZ01
        Sea Density                                          : DENS_01 : SDN:P01::SIGTEQ01
        Hydrogen Ion Concentration (pH)                      : PHPH_01 : SDN:P01::PHXXZZXX
        par                                                  : PSAR_01 : SDN:P01::PFDPAR01 (new)
        chlorophyll                                          : FLOR_01 : SDN:P01::CPHLPR01
        Partial pressure of carbon dioxide in the atmosphere : ACO2_01 : SDN:P01::ACO2XXXX
        Partial pressure of carbon dioxide in the water body : PCO2_01 : SDN:P01::PCO2XXXX
        Wave mean height                                     : VRMS_01 : SDN:P01::GAVHZZ01
        Wave maximum height                                  : VMXL_01 : SDN:P01::GCMXZZ01
        Wave period                                          : VTCA_01 : SDN:P01::GTAMZZ01
Notes
-----

"""

import xarray as xr
from typing import List, Union, Tuple, Dict, Optional
from magtogoek import CONFIGURATION_PATH

from magtogoek.odf_format import Odf
from magtogoek.odf_exporter_common import make_cruise_header, make_event_header, make_odf_header, \
    make_buoy_header, make_buoy_instrument_headers,  make_quality_header, make_history_header, \
    make_parameter_headers, write_odf
from magtogoek.platforms import PlatformMetadata
from magtogoek.utils import json2dict

PARAMETERS = (
    'time',
    'lon',
    'lat',
    'wind_speed',
    'wind_direction',
    'wind_gust',
    'atm_temperature',
    'atm_humidity',
    'atm_pressure',
    'temperature',
    'conductivity',
    'salinity',
    'density',
    'dissolved_oxygen',
    'ph',
    'chlorophyll',
    'par',
    'pco2_air',
    'pco2_water',
    'wave_mean_height',
    'wave_maximal_height',
    'wave_period'
)

QC_PARAMETERS = ( # Note: commented variables have no quality control. (March 2024)
    # 'wind_speed',
    # 'wind_direction',
    # 'wind_gust',
    'atm_temperature',
    'atm_humidity',
    'atm_pressure',
    'temperature',
    # 'conductivity',
    'salinity',
    'density',
    'dissolved_oxygen',
    'ph',
    # 'chlorophyll',
    # 'par',
    # 'pco2_air',
    # 'pco2_water',
    # 'wave_mean_height',
    # 'wave_maximal_height',
    # 'wave_period',
)

PARAMETERS_METADATA_PATH = CONFIGURATION_PATH.joinpath("odf_parameters_metadata.json")
PARAMETERS_METADATA = json2dict(PARAMETERS_METADATA_PATH)

EVENT_QUALIFIER2 = 'METOCE'


def make_odf(
        dataset: xr.Dataset,
        platform_metadata: PlatformMetadata,
        global_attributes: dict,
        p01_codes_map: dict,
        use_bodc_name: bool = True,
        output_path: Optional[str] = None
):
    """
    Parameters
    ----------
    dataset :
        Dataset to which add the navigation data.
    platform_metadata :
        Metadata from the platform file.
    global_attributes :
        Global attributes parameter from the configFile.
    p01_codes_map :
        generic name to bodc p01_code mapping.
    use_bodc_name:
        If True, map from the generic to the BODC p01 variables names.
    output_path:
        If a path(str) is provided, there are two possibilities: if the path is only a directory, the file name
        will be made from the odf['file_specification']. If a file name is also provided, the 'event_qualifier2'
        will be appended to it if it's not present in the `output_path`.
    """
    odf = Odf()

    make_cruise_header(odf, platform_metadata, global_attributes)
    make_event_header(odf, dataset, global_attributes, EVENT_QUALIFIER2)
    _set_event_header_depths(odf, dataset)
    make_odf_header(odf)

    make_buoy_header(odf, platform_metadata)
    make_buoy_instrument_headers(odf, platform_metadata)

    make_quality_header(odf, dataset)
    make_history_header(odf)

    make_parameter_headers(odf=odf, dataset=dataset, variables=PARAMETERS, qc_variables=QC_PARAMETERS,
                           p01_codes_map=p01_codes_map, bodc_name=use_bodc_name)

    if output_path is not None:
        write_odf(odf=odf, output_path=output_path)

    return odf


def _set_event_header_depths(odf: Odf, dataset: xr.Dataset):
    """ Set even header depths metadata from dataset.

    Sets :
     - min_depth, max_depth
     - depth_off_bottom

    Parameters
    ----------
    odf :
    dataset :
    """

    if 'sampling_depth_m' in dataset.attrs:
        odf.event['min_depth'] = dataset.attrs['sampling_depth_m']
        odf.event['max_depth'] = dataset.attrs['sampling_depth_m']

    if all(odf.event[key] is not None for key in ('sounding', 'max_depth')):
        odf.event["depth_off_bottom"] = odf.event['sounding'] - odf.event['max_depth']