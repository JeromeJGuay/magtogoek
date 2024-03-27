"""
Metoce Data Computation.
"""
from typing import TYPE_CHECKING

import gsw
import numpy as np
import xarray as xr

from magtogoek import logger as l

from magtogoek.navigation import compute_speed_and_course, compute_uv_ship
from magtogoek.process_common import add_correction_attributes_to_dataarray
from magtogoek.wps.sci_tools import dissolved_oxygen_ml_per_L_to_umol_per_L, dissolved_oxygen_umol_per_L_to_umol_per_kg, \
    rinko_raw_data_from_dissolved_oxygen, dissolved_oxygen_from_rinko_raw_measurement, compute_in_situ_density, \
    air_pco2_from_xco2, water_pco2_from_wet_xco2, water_pco2_temperature_compensation

if TYPE_CHECKING:
    from magtogoek.metoce.process import ProcessConfig


def compute_buoy_speed_and_course(dataset: xr.Dataset):
    if all(v in dataset for v in ['lon', 'lat']):
        l.log('Platform `speed` and `course` computed from longitude and latitude data.')
        compute_speed_and_course(dataset=dataset)
    else:
        l.warning("Could not compute `speed` and `course`. `lon`/`lat` data not found.")


def compute_buoy_u_ship_and_v_ship(dataset: xr.Dataset):
    if all(x in dataset for x in ('speed', 'course')):
        l.log('Platform `u_ship`, `v_ship` computed from speed and course data.')
        compute_uv_ship(dataset=dataset)

    elif all(v in dataset for v in ['lon', 'lat']):
        l.log('Platform velocities (u_ship, v_ship) computed from longitude and latitude data.')
        compute_speed_and_course(dataset=dataset)
        compute_uv_ship(dataset=dataset)
    else:
        l.warning("Could not compute `u_ship` and `v_ship`. GPS data not found.")


def compute_rinko_raw_data_from_dissolved_oxygen(dataset: xr.Dataset, pconfig: "ProcessConfig"):
    _required_variables = ['temperature']

    if all(var in dataset.variables for var in _required_variables):
        if len(pconfig.dissolved_oxygen_rinko_coeffs) == 6:
            if len(pconfig.dissolved_oxygen_winkler_coeffs) == 2:
                dataset['raw_dissolved_oxygen'] = (['time'], rinko_raw_data_from_dissolved_oxygen(
                    dissolved_oxygen=dataset.dissolved_oxygen.values,
                    temperature=dataset.temperature.values,
                    coeffs=pconfig.dissolved_oxygen_rinko_coeffs
                ))
                pconfig.variables_to_drop.append('raw_dissolved_oxygen')
            else:
                l.warning(f'Winkler dissolved oxygen correction aborted. Wrong number of Winkler coefficient. Expected 2.')
        else:
            l.warning(f'Winkler dissolved oxygen correction aborted. Wrong number of Rinko coefficient. Expected 6.')
    else:
        l.warning(f'Winkler dissolved oxygen correction aborted. Temperature data missing.')


def compute_dissolved_oxygen_from_raw(dataset: xr.Dataset, pconfig: "ProcessConfig"):

    coeffs = [i for i in pconfig.dissolved_oxygen_rinko_coeffs]
    coeffs[1:3] = pconfig.dissolved_oxygen_winkler_coeffs

    dataset['dissolved_oxygen'].values = dissolved_oxygen_from_rinko_raw_measurement(
        raw=dataset.raw_dissolved_oxygen.values,
        temperature=dataset.temperature.values,
        coeffs=coeffs
    )

    l.log(f"Dissolved oxygen Winkler correction was carried out.")

    pconfig.p01_codes_map.update({'dissolved_oxygen': "DOXYCZ01", 'dissolved_oxygen_QC': "DOXYCZ01_QC"})

    add_correction_attributes_to_dataarray(dataset['dissolved_oxygen'])
    dataset['dissolved_oxygen'].attrs["corrections"] += 'Winkler correction carried out.\n'
    dataset['dissolved_oxygen'].attrs["rinko_coefficients"] = pconfig.dissolved_oxygen_rinko_coeffs
    dataset['dissolved_oxygen'].attrs["winkler_coefficients"] = pconfig.dissolved_oxygen_winkler_coeffs


def compute_pressure_at_sampling_depth(dataset: xr.Dataset, pconfig: "ProcessConfig"):
    """Compute pressure in [dbar].
    Uses latitude (`lat`) in data if available and `pconfig.sampling_depth` from config if available.
    """
    if pconfig.sampling_depth is None:
        return 0

    if "lat" in dataset.variables:
        latitude = dataset.lat.data
    elif isinstance(pconfig.platform_metadata.platform.latitude, (int, float)):
        latitude = pconfig.platform_metadata.platform.latitude
    else:
        latitude = 0

    return gsw.p_from_z(z=-pconfig.sampling_depth, lat=latitude)


def compute_potential_density(dataset: xr.Dataset, pconfig: "ProcessConfig"):
    """Compute potential density as sigma_t:= Density(S,T,P) - 1000

    Density computed using TEOS-10 polynomial (Roquet et al., 2015)

    """

    required_variables = ['temperature', 'salinity']
    if all((var in dataset for var in required_variables)):
        _log_msg = 'Potential density computed using TEOS-10 polynomial (absolute salinity and conservative temperature'

        longitude = 0
        latitude = 0

        if "lon" in dataset.variables:
            _lon = np.round(dataset.lon.mean('time', skipna=True).data, 4)
        else:
            if isinstance(pconfig.platform_metadata.platform.longitude, (int, float)):
                longitude = pconfig.platform_metadata.platform.longitude
        _log_msg += f', longitude = {longitude}'


        if "lat" in dataset.variables:
            _lat = np.round(dataset.lat.mean('time', skipna=True).data, 4)
            if np.isfinite(_lat):
                latitude = _lat
        else:
            if isinstance(pconfig.platform_metadata.platform.latitude, (int, float)):
                latitude = pconfig.platform_metadata.platform.latitude
        _log_msg += f', latitude = {latitude}'


        if 'pres' in dataset.variables:
            pres = dataset.pres.values
            _log_msg += f', pressure'
        else:
            pres = compute_pressure_at_sampling_depth(dataset=dataset, pconfig=pconfig)
            _log_msg += f', pressure at depth = {pconfig.sampling_depth or 0} m'

        density = compute_in_situ_density(
            temperature=dataset.temperature.data,
            salinity=dataset.salinity.data,
            pres=pres,
            latitude=latitude,
            longitude=longitude
        )

        dataset['density'] = (['time'], density - 1000)

        l.log(_log_msg + ').')
    else:
        l.warning(f'Potential density computation aborted. One of more variables in {required_variables} was missing.')


def compute_air_and_water_pco2(dataset: xr.Dataset):
    if 'pco2_air' not in dataset:
        _compute_air_pco2(dataset=dataset)

    if 'pco2_water' not in dataset:
        _compute_water_pco2(dataset=dataset)


def _compute_air_pco2(dataset: xr):
    required_variables = [f'xco2_air', 'atm_pressure']
    if all((var in dataset for var in required_variables)):
        # atmospheric pressure is in mbar. Needs to be in atm.
        _pressure = dataset[f'atm_pressure'].pint.quantify().pint.to('atm').pint.dequantify().values
        pco2 = air_pco2_from_xco2(xco2 = dataset['xco2_air'].values, atmospheric_pressure=_pressure)
        dataset[f'pco2_air'] = (['time'], pco2, {'units': 'uatm'})
        l.log(f'pco2_air computed from atmospheric pressure and xco2 (air) concentrations ppm.')
    else:
        l.warning(f'pco2_air computation aborted. One of more variables in {required_variables} was missing.')


def _compute_water_pco2(dataset: xr):
    required_variables = [f'xco2_water', 'atm_pressure'] # maybe we need the cell pressure
    if all((var in dataset for var in required_variables)):
        # atmospheric pressure is in mbar. Needs to be in atm.
        _pressure = dataset['atm_pressure'].pint.quantify().pint.to('atm').pint.dequantify().values
        _pco2 = water_pco2_from_wet_xco2(xco2=dataset['xco2_water'].values, atmospheric_pressure=_pressure)

        # Any correction to the partial pressure value could/should be done here.
        # None seems to be needed for Pro-Oceanus.

        dataset[f'pco2_water'] = (['time'], _pco2, {'units': 'uatm'})
        l.log(f'pco2_water computed from atmospheric pressure and xco2 (water) concentrations ppm.')

    else:
        l.warning(f'pco2_water computation aborted. One of more variables in {required_variables} was missing.')


# Not used. All oxygen data are loaded output in [umol/L]
def convert_dissolved_oxygen_ml_per_L_to_umol_per_L(dataset: xr.Dataset):
    """
    """
    if dataset.dissolved_oxygen.attrs['units'] == ['ml/L']:
        dataset.dissolved_oxygen.values = dissolved_oxygen_ml_per_L_to_umol_per_L(dataset.dissolved_oxygen)
        dataset.dissolved_oxygen.attrs['units'] = 'umol/L'
        l.log('Dissolved Oxygen converted from [ml/L] to [umol/L].')
    else:
        l.warning(
            f"Wrong dissolved oxygen units {dataset.dissolved_oxygen.attrs['units']} for conversion from [ml/L] to [umol/L].")

# Not used. All oxygen data are loaded output in [umol/L]
def convert_dissolved_oxygen_umol_per_L_to_umol_per_kg(dataset: xr.Dataset):
    if dataset.dissolved_oxygen.attrs['units'] == ['umol/L']:
        if 'density' in dataset.variables:
            dataset.dissolved_oxygen.values = dissolved_oxygen_umol_per_L_to_umol_per_kg(
                dataset.dissolved_oxygen.dataset.density
            )
            dataset.dissolved_oxygen.attrs['units'] = 'umol/kg'
            l.log('Dissolved Oxygen converted from [umol/L] to [umol/kg].')
        else:
            l.warning(f"Density missing for oxygen conversion from [umol/L] to [umol/kg].")
    else:
        l.warning(
            f"Wrong dissolved oxygen units {dataset.dissolved_oxygen.attrs['units']} for conversion from [umol/L] to [umol/kg].")
