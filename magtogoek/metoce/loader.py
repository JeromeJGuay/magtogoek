"""
Date: April 2022
Made by jeromejguay

Module that contains function to load meteoc variable into a dataset.


Notes
-----
[March 2023] JeromeJGuay
    The WXT wind measurements are less accurate than the wmt700. Furthermore, the WXT520
    is more likely to malfunction and not send data while the WMT700 always work.

[March 2023] JeromeJGuay
    GPS bearing and course data seem to be bad. We believe that the bearing and course data are instant measurements.
    Thus wave induced rapid horizontal oscillation and the rocking of the buoy, the GPS being located about ~2-3 meters
    above the floating line, result in higher oscillation and amplitude in the speed values. Since speed dependent values
    are average over ~ 1 minutes, we need at least ~1 minutes average values from the gps.
[January 2024] JeromeJGuay
    Wind direction max is the max value (angle) not the direction of wind gust.
"""

import numpy as np
import xarray as xr
from typing import *

import magtogoek.logger as l
from magtogoek.exceptions import MagtogoekExit
from magtogoek.utils import get_files_from_expression, format_filenames_for_print
from magtogoek.tools import is_unique, nan_unique

from magtogoek.metoce.viking_dat_reader import RawVikingDatReader, VikingData
from magtogoek.metoce.metis_dat_reader import RawMetisDatReader, MetisData

import pint_xarray # pint_xarray modify the xr.Dataset Object


KNOTS_TO_METER_PER_SECONDS = 0.5144444444 # mps/knots
MILLIMETER_TO_METER = 1 / 1000 # m / 1000 mmm
CENTIMETER_TO_METER = 1 / 100  # m / 100 cm

RTI_FILL_VALUE = 88888
RDI_FILL_VALUE = -32768.0

def load_metoce_data(
        filenames: Union[str, List[str]],
        buoy_name: str = None,
        data_format: str = 'viking',
) -> xr.Dataset:
    """

    Parameters
    ----------
    filenames
    buoy_name
    data_format :
        One of [raw_dat]

    Returns
    -------

    """
    l.section('Loading metoce data', t=True)

    filenames = get_files_from_expression(filenames)

    l.log(format_filenames_for_print('raw_data', filenames))

    if data_format == "viking":
        buoy_data = RawVikingDatReader().read(filenames)
    elif data_format == "metis":
        buoy_data = RawMetisDatReader().read(filenames)
    else:
        l.warning(f'Invalid data_format: {data_format}')
        raise MagtogoekExit("Invalid metoce data format. Exiting")

    if isinstance(buoy_data, Dict):
        l.warning(f'More than one buoy name was found in the file {filenames}.\n'
                  f' Buoy names fround: {list(buoy_data.keys())}\n'
                  f' Specify a buoy_name\n Exiting')
        raise MagtogoekExit(f'More than one buoy (buoy_name) was found in the file {filenames}. Exiting')

    if buoy_name is not None and buoy_data.buoy_name != buoy_name:
        l.log(f'Buoy Name found in files is different from the one provided.')

    if data_format == "viking":
        metoce_data, global_attrs = _load_viking_metoce_data(buoy_data)
    else: #if data_format == "metis": # not required. Also remove a variable reference warning.
        metoce_data, global_attrs = _load_metis_metoce_data(buoy_data)

    _add_time_coords(metoce_data)

    coords = {'time': np.asarray(buoy_data.time)}

    dataset = xr.Dataset(metoce_data, coords=coords, attrs=global_attrs)

    dataset = dataset.sortby('time')

    if data_format == "viking":
        dataset = _average_duplicates(dataset, 'time')

    if is_unique(dataset['magnetic_declination']):
        dataset.attrs["magnetic_declination"] = nan_unique(dataset['magnetic_declination'])[0]
        dataset.attrs["magnetic_declination_units"] = "degree east"
        dataset = dataset.drop_vars('magnetic_declination')

    l.log('Data Loaded.')

    return dataset


def _load_viking_metoce_data(viking_data: VikingData) -> Tuple[Dict[str, Tuple[np.ma.MaskedArray, dict]], Dict]:
    """

    Parameters
    ----------
    viking_data

    Returns
    -------
        {variable_name: str -> (data: np.ma.MaskedArray, attributes: Dict)}

    """
    global_attrs = {
        'platform': viking_data.buoy_name,
        'buoy_controller_firmware_version': viking_data.firmware,
        'buoy_controller_serial_number': list(set(viking_data.controller_sn))
    }

    data = {'lon': (viking_data.longitude, {}),
             'lat': (viking_data.latitude, {}),
             }

    if viking_data.gps is not None:
        data.update(
            {'speed': (np.round(viking_data.gps['speed'] * KNOTS_TO_METER_PER_SECONDS, 3), {"units": "m/s"}),
             'course': (viking_data.gps['course'], {}),
             'magnetic_declination': (viking_data.gps['variation_E'], {})}
        )
        l.log('Gps data loaded.')

    if viking_data.comp is not None:
        data.update(
            {'heading': (viking_data.comp['heading'], {}),
             'pitch': (viking_data.comp['pitch'], {}),
             'roll_': (viking_data.comp['roll'], {}),
             'pitch_std': (viking_data.comp['pitch_std'], {}),
             'roll_std': (viking_data.comp['roll_std'], {})}
        )
        l.log('Comp data loaded.')

    if viking_data.wmt700 is not None:
        """
        Sm: wind speed average
        Sn: wind speed min
        Sx: wind speed max
        
        Dm: wind direction average
        Dn: wind direction min
        Dx: wind direction max        
        """
        data.update(
            {

                'wind_speed': (np.round(viking_data.wmt700['Sm'] * KNOTS_TO_METER_PER_SECONDS, 3), {'units': 'm/s'}),
                'wind_direction': (viking_data.wmt700['Dm'], {}),
                'wind_gust': (np.round(viking_data.wmt700['Sx'] * KNOTS_TO_METER_PER_SECONDS, 3), {'units': 'm/s'}),
            }
        )
        l.log('wmt700 data loaded.')

    if viking_data.wxt520 is not None:
        data.update(
            {'atm_temperature': (viking_data.wxt520['Ta'], {"units": "degree_C"}),
             'atm_humidity': (viking_data.wxt520['Ua'], {"units": "percent"}),
             'atm_pressure': (viking_data.wxt520['Pa'], {"units": "mbar"}),
             }
        )

        l.log('wxt520 data loaded.')

    if viking_data.ctd is not None:
        data.update(
            {'temperature': (viking_data.ctd['temperature'], {"units": "degree_C"}),
             'conductivity': (viking_data.ctd['conductivity'], {'units': 'S/m'}),
             'salinity': (viking_data.ctd['salinity'], {'units': 'PSU'}),
             'density': (viking_data.ctd['density'], {'units': 'kg/m**3'})}
        )
        l.log('Ctd data loaded.')

    elif viking_data.ctdo is not None:
        data.update(
            {'temperature': (viking_data.ctdo['temperature'], {"units": "degree_C"}),
             'conductivity': (viking_data.ctdo['conductivity'], {'units': 'S/m'}),
             'salinity': (viking_data.ctdo['salinity'], {'units': 'PSU'}),
             'dissolved_oxygen': (viking_data.ctdo['dissolved_oxygen'], {'units': 'umol/L'})}
        )
        l.log('Ctdo data loaded.')

    if viking_data.wph is not None:
        mask = np.isfinite(viking_data.wph['ext_ph'])
        _serial_number = viking_data.wph['serial_number'][mask][0]
        _model = viking_data.wph['model'][mask][0]
        _attrs = {'serial_number': _serial_number, 'model': _model}
        global_attrs.update({'ph_serial_number': _serial_number, 'ph_model': _model, 'is_corrected': 0})
        data.update(
            {
                'ph': (viking_data.wph['ext_ph'], {**_attrs, **{"units": "NBS_scale"}}),
                'ph_temperature': (viking_data.wph['ph_temperature'], {**_attrs, **{"units": "degree_C"}})}
        )
        l.log('Wph data loaded.')

    if viking_data.triplet is not None:
        mask = np.isfinite(viking_data.triplet['scatter_calculated'])
        _serial_number = viking_data.triplet['serial_number'][mask][0]
        _model = viking_data.triplet['model_number'][mask][0]
        _attrs = {'serial_number': _serial_number, 'model': _model}
        global_attrs.update({'triplet_serial_number': _serial_number, 'triplet_model': _model})

        data.update(
            {
                'scattering': (viking_data.triplet['scatter_calculated'], {**_attrs, **{"units": "/m", "wavelength": "700nm"}}), #ppb ?
                'chlorophyll': (viking_data.triplet['chloro_calculated'], {**_attrs, **{"units": "mg/m**3", "wavelength": "695nm"}}), #ug/L -> mg/m**3
                'fdom': (viking_data.triplet['fdom_calculated'], {**_attrs, **{"units": "ppb", "wavelength": "460nm"}}) #ppb
            }
        )
        l.log('Eco-Triplet data loaded.')

    if viking_data.par_digi is not None:
        mask = np.isfinite(viking_data.par_digi['par'])
        _serial_number = viking_data.par_digi['serial_number'][mask][0]
        _model = viking_data.par_digi['model_number'][mask][0]

        _attrs = {'serial_number': _serial_number, 'model': _model}
        global_attrs.update({'par_serial_number': _serial_number, 'par_triplet_model': _model})

        data['par'] = (viking_data.par_digi['par'], {**_attrs, **{"units": "umol/m**2/s"}})
        l.log('Par Digi data loaded.')

    if viking_data.co2_a is not None:
        data.update({
            'xco2_air': (viking_data.co2_a['co2_ppm'], {'units': 'ppm'}),
            # 'co2_air_cell_temperature': (viking_data.co2_a['irga_temperature'], {'units': 'degree_C'}),
            # 'co2_air_humidity': (viking_data.co2_a['cell_gas_pressure_mbar'], {'units': 'mbar'}),
            # 'co2_air_humidity_temperature': (viking_data.co2_a['humidity_sensor_temperature'], {'units': 'degree_C'}),
            # 'co2_air_cell_pressure': (viking_data.co2_a['cell_gas_pressure_mbar'], {'units': 'mbar'}),
        })
        l.log('Co2_a data loaded.')

    if viking_data.co2_w is not None:
        data.update({
            'xco2_water': (viking_data.co2_w['co2_ppm'], {'units': 'ppm'}),
            # 'co2_water_cell_temperature': (viking_data.co2_w['irga_temperature'], {'units': 'degree_C'}),
            # 'co2_water_humidity': (viking_data.co2_w['cell_gas_pressure_mbar'], {'units': 'mbar'}),
            # 'co2_water_humidity_temperature': (viking_data.co2_w['humidity_sensor_temperature'], {'units': 'degree_C'}),
            # 'co2_water_cell_pressure' : (viking_data.co2_w['cell_gas_pressure_mbar'], {'units': 'mbar'}),
        })
        l.log('Co2_w data loaded.')

    if viking_data.wave_m is not None:
        data.update(
            {'wave_mean_height': (viking_data.wave_m['average_height'], {}),
             'wave_maximal_height': (viking_data.wave_m['maximal_height'], {}),
             'wave_period': (viking_data.wave_m['period'], {})}
        )
        l.log('Wave_m data loaded.')

    elif viking_data.wave_s is not None:
        _attrs = {'comments': 'Height values were truncated at the first decimal.\n'}
        data.update(
            {'wave_mean_height': (viking_data.wave_s['average_height'], _attrs),
             'wave_maximal_height': (viking_data.wave_s['Hmax'], _attrs),
             'wave_period': (viking_data.wave_s['dominant_period'], {}),
             'wave_direction': (viking_data.wave_s['direction'], {})}
        )
        l.log('Wave_s data loaded.')

    if viking_data.rdi is not None and viking_data.rti is not None:
        l.warning('Both RDI and RTI tag found in dataset.')
        _adcp_data = dict()
        # load RDI data
        for _name in ['u', 'v', 'w', 'e']:
            viking_data.rdi[_name][viking_data.rdi[_name] == RDI_FILL_VALUE] = np.nan
            _adcp_data[_name] = viking_data.rdi[_name]

        rti_mask = np.isfinite(viking_data.rti['u'])
        rdi_mask = np.isfinite(viking_data.rdi['u'])

        if not any(rti_mask & rdi_mask):
            l.warning('Merging RDI and RTI data')
            # load RTI data
            for _name in ['u', 'v', 'w', 'e']:
                viking_data.rti[_name][viking_data.rti[_name] == RTI_FILL_VALUE] = np.nan
                _adcp_data[_name][rti_mask] = viking_data.rti[_name][rti_mask]

        else:
            l.warning('There is a time overlap between RDI and RTI data. RTI data were discarded.')


        for _name in ['u', 'v', 'w', 'e']:
            data[_name] = (_adcp_data[_name] * MILLIMETER_TO_METER, {"units": "m/s"}) #rounded to mm.

    else:
        if viking_data.rdi is not None:
            for _name in ['u', 'v', 'w', 'e']:
                viking_data.rdi[_name][viking_data.rdi[_name] == RDI_FILL_VALUE] = np.nan
                data[_name] = (viking_data.rdi[_name] * MILLIMETER_TO_METER, {"units": "m/s"}) #rounded to mm.
            l.log('Rdi data loaded.')

        if viking_data.rti is not None:
            for _name in ['u', 'v', 'w', 'e']:
                viking_data.rti[_name][viking_data.rti[_name] == RTI_FILL_VALUE] = np.nan
                data[_name] = (viking_data.rti[_name] * MILLIMETER_TO_METER, {"units": "m/s"}) #rounded to mm.
            l.log('Rti data loaded.')

    return data, global_attrs


def _load_metis_metoce_data(metis_data: MetisData) -> Tuple[Dict[str, Tuple[np.ma.MaskedArray, dict]], Dict]:
    global_attrs = {}
    data = {
        'lon': (metis_data.init['longitude'], {}),
        'lat': (metis_data.init['latitude'], {}),
        'speed': (metis_data.init['sog'] * KNOTS_TO_METER_PER_SECONDS, {}),
        'course': (metis_data.init['cog'], {}),
        'magnetic_declination': (metis_data.init['magnetic_declination'], {}),
        'heading': (metis_data.init['heading'], {'corrections': 'Corrected for magnetic declination at sampling.\n'}),
        'pitch': (metis_data.init['pitch'], {}),
        'roll_': (metis_data.init['roll'], {}),
        'pitch_std': (metis_data.init['pitch_std'], {}),
        'roll_std': (metis_data.init['roll_std'], {})
        }

    if metis_data.eco1 is not None:
        data.update(
            {
                'scattering': (metis_data.eco1['scattering'], {"units": "/m", "wavelength": "700nm"}),
                'chlorophyll': (metis_data.eco1['chlorophyll'], {"units": "mg/m**3", "wavelength": "695nm"}), # ug/L -> mg/m**3
                'fdom': (metis_data.eco1['fdom'], {"units": "ppb", "wavelength": "460nm"})# ppb
            }
        )
        l.log('Eco1 data loaded.')

    if metis_data.ctd is not None:
        data.update(
                {'temperature': (metis_data.ctd['temperature'], {"units": "degree_C"}),
                 'conductivity': (metis_data.ctd['conductivity'], {'units': 'S/m'}),
                 'salinity': (metis_data.ctd['salinity'], {'units': 'PSU'}),
                 'density': (metis_data.ctd['density'], {'units': 'kg/m**3'})
             }
        )
        l.log('ctd data loaded.')

    if metis_data.ph is not None:
        if any(np.isfinite(metis_data.ph['ext_ph_calc'])):
            _ph_attrs = {
                'units': 'NBS_scale',
                'corrections': 'pH values were computed with the in-situ salinity (at sampling).\n'
            }
            data.update({'ph': (metis_data.ph['ext_ph_calc'], _ph_attrs)})
            global_attrs['is_corrected'] = 1
        else:
            _ph_attrs = {
                'units': 'NBS_scale'
            }
            data.update({'ph': (metis_data.ph['ext_ph'], _ph_attrs)})
            global_attrs['is_corrected'] = 0
            l.warning("pH values were not computed with the in-situ salinity (at sampling).")
        l.log('pH data loaded')

    # if metis_data.no3 is not None:
      # Nitrate Data are not loaded since the correction algorithm are not yet implemented.

    if metis_data.wind is not None:
        _s, _c = np.unique(metis_data.wind['source'], return_counts=True)
        _counts = {k: round(100 * v / len(metis_data.wind['source']), 2) for k, v in zip(_s, _c)}

        if '5' in _counts and '7' in _counts: # 'nan could also be there a source. Meaning no data was sampled.
            _msg = f"Wind data were sampled by both the wmt700 ({_counts['7']}%), wxt536 ({_counts['5']}%)"
            if 'nan' in _s:
                _msg += f" (missing: {_counts['nan']}%)"
            l.warning(_msg +'.')

        data.update(
            {
                'wind_speed': (np.round(metis_data.wind['wind_spd_ave'] * KNOTS_TO_METER_PER_SECONDS, 3), {'units': 'm/s'}),
                'wind_direction': (metis_data.wind['wind_dir_ave'], {'corrections': 'Corrected for magnetic declination at sampling.\n'}),
                'wind_gust': (np.round(metis_data.wind['wind_spd_max'] * KNOTS_TO_METER_PER_SECONDS, 3), {'units': 'm/s'}),
            }
        )

        l.log('Wind Data Loaded')

    if metis_data.atms is not None:
        data.update(
            {
                'atm_temperature': (metis_data.atms['air_temperature'], {"units": "degree_C"}),
                'atm_humidity': (metis_data.atms['air_humidity'], {"units": "percent"}),
                'atm_pressure': (metis_data.atms['air_pressure'], {"units": "mbar"}),
             }
        )
        l.log('Atmospheric Data Loaded')

    if metis_data.wave is not None:
        data.update(
            {
                'wave_mean_height': (metis_data.wave['hm0'], {}), #CHECK IF THIS IS OK FIXME
                'wave_maximal_height': (metis_data.wave['hmax'], {}),
                'wave_period': (metis_data.wave['period'], {})
             }
        )
        l.log("Wave Data Loaded")

    if metis_data.adcp is not None:
        data.update(
            {
                'u': (metis_data.adcp['u'] * MILLIMETER_TO_METER, {"units": "m/s"}),
                'v': (metis_data.adcp['v'] * MILLIMETER_TO_METER, {"units": "m/s"}),
                'w': (metis_data.adcp['w'] * MILLIMETER_TO_METER, {"units": "m/s"}),
                'e': (metis_data.adcp['e'] * MILLIMETER_TO_METER, {"units": "m/s"}),
            }
        )
        l.log('ADCP Data Loaded')


    if metis_data.pco2 is not None:

        data.update(
            {
                'xco2_air': (metis_data.pco2['co2_ppm_air'], {'units': 'ppm'}),
                'xco2_water': (metis_data.pco2['co2_ppm_water'], {'units': 'ppm'}),
             }
        )
        l.log('PCO2 Data Loaded')

    return data, global_attrs


def _add_time_coords(data: Dict[str, Tuple[np.ndarray, Dict]]) -> Dict[str, Tuple[List[str], np.ndarray, dict]]:
    """Add the time coords according to the Xarray data format."""
    for var, (_data, _attrs) in data.items():
        data[var] = (['time'], _data, _attrs)


def _average_duplicates(dataset: xr.Dataset, coord: str) -> xr.Dataset:
    """Average data_array values of duplicates time coords index.
    """

    # average any duplicate value along coord by grouping according to coord value.
    df = dataset.to_dataframe()
    df = df.groupby(coord).mean(numeric_only=False)

    # get the subset of the dataset with all unique coord value.
    _dataset = dataset[{coord: np.unique(dataset[coord], return_index=True)[1]}]

    # replace values by the averaged (if duplicated coord index) values.
    for var in _dataset.keys():
        _dataset[var].values[:] = df[var][:]

    l.log('Duplicate timestamp data averaged.')
    return _dataset


if __name__ == "__main__":
    filename = "/home/jeromejguay/ImlSpace/Data/pmza_2023/IML-4/PMZA-RIKI_FileTAGS_2023.dat"
    ds = load_metoce_data(filenames=filename, data_format='metis')
