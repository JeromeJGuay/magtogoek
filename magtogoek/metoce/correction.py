"""
Date: February 2023
Made by jeromejguay

Module containing the correction functions for metoce data processing.

import gsw
"""
import numpy as np
import xarray as xr
from typing import List, TYPE_CHECKING

from magtogoek import logger as l
from magtogoek.metoce.computation import compute_rinko_raw_data_from_dissolved_oxygen, compute_dissolved_oxygen_from_raw, \
    compute_pressure_at_sampling_depth
from magtogoek.process_common import add_correction_attributes_to_dataarray
from magtogoek.sci_tools import rotate_heading, xy_vector_magnetic_correction, \
    north_polar2cartesian, cartesian2north_polar, time_drift_correction, data_calibration_correction
from magtogoek.wps.sci_tools import dissolved_oxygen_correction_for_salinity_SCOR_WG_142, \
    dissolved_oxygen_correction_for_pressure_JAC, pH_correction_for_salinity

if TYPE_CHECKING:
    from magtogoek.metoce.process import ProcessConfig


# 'salinity' and 'temperature' corrections are carried out separately
DRIFT_VARIABLES: List[str] = [
    'dissolved_oxygen',
    'ph',
    'fluorescence',
    'chlorophyll',
    'fdom'
]


CALIBRATION_VARIABLES: List[str] = [ # with post calibration (A*x+B)
    'dissolved_oxygen',
    'ph',
    'fluorescence',
    'chlorophyll',
    'fdom'
]


def apply_motion_correction(dataset: xr.Dataset, pconfig: "ProcessConfig"):
    """Carry motion correction"""

    if pconfig.wind_motion_correction is True:
        _wind_motion_correction(dataset=dataset)

    if pconfig.adcp_motion_correction is True:
        _adcp_motion_correction(dataset=dataset)


def apply_magnetic_correction(dataset: xr.Dataset, pconfig: "ProcessConfig"):
    """Carry magnetic declination correction for metoce variables

    [-180, 180]: heading
    [0, 360 ]: wind_direction, wave_direction

    """
    _set_magnetic_correction_to_apply(dataset, pconfig)

    if pconfig.magnetic_correction_to_apply is not None:
        # '-180, 180'
        if 'heading' in dataset.variables:
            add_correction_attributes_to_dataarray(dataset['heading'])
            dataset.heading.values = rotate_heading(dataset.heading.data, pconfig.magnetic_correction_to_apply)
            dataset['heading'].attrs['corrections'] += 'Corrected for magnetic declination.\n'
            l.log(f"Heading transformed to true north.")

        # '0, 360'
        for variable in {'wind_direction', 'wave_direction'} & set(dataset.variables):
            add_correction_attributes_to_dataarray(dataset[variable])
            dataset[variable].values = (dataset[variable].values + pconfig.magnetic_correction_to_apply) % 360
            dataset[variable].attrs['corrections'] += 'Corrected for magnetic declination.\n'
            l.log(f"{variable} transformed to true north.")

    if pconfig.magnetic_declination is not None: # ADCP is corrected by the instrument. Set the adcp_magnetic_declination_preset if a magnetic_declination value is used.
        _adcp_magnetic_correction(dataset=dataset, pconfig=pconfig)


def apply_sensors_corrections(dataset: xr.Dataset, pconfig: "ProcessConfig"):
    """
    The order here is important.

    - `raw_dissolved_oxygen` needs to be computed first using the raw `temperature` values.
    - Then the corrections needs to be applied to the `temperature` before computing the dissolved_oxygen
      with the Rinko-Winkler coefficients.
    - Then were apply the corrections for the `salinity` before doing the `dissolved_oxygen` `salinity` and
      pressure(`pres`) compensation correction.
    - Then we
    """
    if "dissolved_oxygen" in dataset and pconfig.dissolved_oxygen_winkler_correction is True:
            compute_rinko_raw_data_from_dissolved_oxygen(dataset=dataset, pconfig=pconfig)


    if "temperature" in dataset:
        if pconfig.__getattribute__("temperature_drift") is not None:
            _time_drift_correction(dataset=dataset, variable="temperature", pconfig=pconfig)

        if pconfig.__getattribute__("temperature_calibration_correction") is not None:
            _data_calibration_correction(dataset=dataset, variable="temperature", pconfig=pconfig)


    if "raw_dissolved_oxygen" in dataset:
        compute_dissolved_oxygen_from_raw(dataset=dataset, pconfig=pconfig)


    if "salinity" in dataset:
        if pconfig.__getattribute__("salinity_drift") is not None:
            _time_drift_correction(dataset=dataset, variable="temperature", pconfig=pconfig)

        if pconfig.__getattribute__("salinity_calibration_correction") is not None:
            _data_calibration_correction(dataset=dataset, variable="salinity", pconfig=pconfig)


    if "dissolved_oxygen" in dataset:
        if pconfig.dissolved_oxygen_salinity_correction is True:
            _dissolved_oxygen_salinity_correction(dataset=dataset, pconfig=pconfig)
        if pconfig.dissolved_oxygen_pressure_correction is True:
            _dissolved_oxygen_pressure_correction(dataset=dataset, pconfig=pconfig)


    if "ph" in dataset and pconfig.ph_salinity_correction is True and pconfig.ph_is_corrected is False:
            _correct_ph_for_salinity(dataset=dataset, pconfig=pconfig)


    for variable in set(DRIFT_VARIABLES) & set(dataset.variables):
        if pconfig.__getattribute__(variable + "_drift") is not None:
            _time_drift_correction(dataset=dataset,variable=variable,pconfig=pconfig)


    for variable in set(CALIBRATION_VARIABLES) & set(dataset.variables):
        if pconfig.__getattribute__(variable + "_calibration_correction") is not None:
            _data_calibration_correction(dataset=dataset, variable=variable, pconfig=pconfig)


def _wind_motion_correction(dataset:xr.Dataset):
    """ Correct wind_speed and wind_gust with u_ship and v_ship.

    Required variable in dataset:
        wind_speed: (wind_speed, wind_direction)
        wind_gust: (wind_gust, wind_gust_direction)

    ```Correction
    wind_x' = wind_x + u_ship
    wind_y' = wind_y + v_ship
    ```
    """
    if all(v in dataset for v in ("u_ship", "v_ship")):
        l.log("Wind motion correction was carried out with gps data.")
        _msg = "Motion correction was carried out with gps data."
        if all(v in dataset for v in ("wind_speed", "wind_direction")):
            wind_x, wind_y = north_polar2cartesian(dataset.wind_speed, dataset.wind_direction - 180)
            wind_x += dataset.u_ship
            wind_y += dataset.v_ship
            dataset.wind_direction.values, dataset.wind_speed.values = cartesian2north_polar(wind_x, wind_y)
            dataset.wind_direction.values = (dataset.wind_direction.values + 180 ) % 360

            for v in ("wind_speed", "wind_direction"):
                add_correction_attributes_to_dataarray(dataset[v])
                dataset[v].attrs["corrections"] += _msg + "\n"

        if all(v in dataset for v in ("wind_gust", "wind_gust_direction")):
            gust_x, gust_y = north_polar2cartesian(dataset.wind_gust, dataset.wind_gust_direction - 180)
            gust_x += dataset.u_ship
            gust_y += dataset.v_ship
            dataset.wind_gust_direction.values, dataset.wind_gust.values = cartesian2north_polar(gust_x, gust_y)
            dataset.wind_gust_direction.values = (dataset.wind_gust_direction.values + 180) % 360
            for v in ("wind_gust", "wind_gust_direction"):
                add_correction_attributes_to_dataarray(dataset[v])
                dataset[v].attrs["corrections"] += _msg + "\n"


def _adcp_motion_correction(dataset: xr.Dataset):
    l.log("Adcp motion correction was carried out with gps data.")
    _msg = "Motion correction was carried out with gps data. Data rounded to mm precision (3 decimal places)."
    if all(f"{v}_ship" in dataset for v in ["u", "v"]):
        for field in ["u", "v"]:
            dataset[field] += np.round(dataset[field + "_ship"], 3) # rounding to millimeter. (ADCP precision)
            add_correction_attributes_to_dataarray(dataset[field])


def _set_magnetic_correction_to_apply(dataset: xr.Dataset, pconfig: "ProcessConfig"):
    """Set the magnetic_correction_to_apply and "magnetic_declination" global attribute.

    Either from the GPS (dataset variable) or the ProcessConfig.magnetic_declination .

    For `metis` data, the correction takes into account the one already carried out by the buoy
    controller.
    """

    if pconfig.data_format == "viking":
        if isinstance(pconfig.magnetic_declination, (int, float)):
            pconfig.magnetic_correction_to_apply = pconfig.magnetic_declination
            dataset.attrs['magnetic_declination'] = pconfig.magnetic_declination
            dataset.attrs["magnetic_declination_units"] = "degree east"
            if 'magnetic_declination' in dataset.variables:
                pconfig.variables_to_drop.append('magnetic_declination')
        else:
            if 'magnetic_declination' in dataset.variables:
                pconfig.magnetic_correction_to_apply = dataset['magnetic_declination'].values

            elif "magnetic_declination" in dataset.attrs and dataset.attrs["magnetic_declination"] != "NA":
                pconfig.magnetic_correction_to_apply = dataset.attrs["magnetic_declination"]

            else:
                l.warning('Unable to carry magnetic declination correction. No magnetic declination value found.')

    elif pconfig.data_format == "metis":
        if isinstance(pconfig.magnetic_declination, (int, float)):
            if 'magnetic_declination' in dataset.variables:
                pconfig.magnetic_correction_to_apply = pconfig.magnetic_declination - dataset['magnetic_declination']
                pconfig.variables_to_drop.append('magnetic_declination')

            elif dataset.attrs["magnetic_declination"] and dataset.attrs["magnetic_declination"] != "NA":
                pconfig.magnetic_correction_to_apply = pconfig.magnetic_declination - dataset.attrs["magnetic_declination"]

            else:
                pconfig.magnetic_correction_to_apply = pconfig.magnetic_declination

            dataset.attrs['magnetic_declination'] = pconfig.magnetic_declination
            dataset.attrs["magnetic_declination_units"] = "degree east"


def _adcp_magnetic_correction(dataset: xr.Dataset, pconfig: "ProcessConfig"):
    """
    Carry magnetic declination correction and motion correction.
    """

    angle = pconfig.magnetic_declination
    if pconfig.adcp_magnetic_declination_preset is not None:
        angle = round((pconfig.magnetic_declination - pconfig.adcp_magnetic_declination_preset), 4)
        l.log(f"An additional magnetic correction of {angle} degree east was applied to the ADCP velocities.")
    else:
        l.log(f"A magnetic correction of {angle} degree east was applied to the ADCP velocities.")

    if all(v in dataset for v in ("u", "v")):
        dataset.u.values, dataset.v.values = xy_vector_magnetic_correction(dataset.u, dataset.v, angle)
        l.log(f"Velocities transformed to true north and true east.")
        for variable in ("u", "v"):
            add_correction_attributes_to_dataarray(dataset[variable])
            dataset[variable].attrs['corrections'] += 'Corrected for magnetic declination.\n'


def _correct_ph_for_salinity(dataset: xr.Dataset, pconfig: "ProcessConfig"):
    """pH correction for salinity.

    ph_temperature is used to find the voltage measured by the probe, but the CTD
    temperature is used to find the ph.
    """
    required_variables = ['ph_temperature', 'temperature', 'salinity']
    if pconfig.ph_salinity_coeffs is not None:
        if all((var in dataset for var in required_variables)):
            [psal, k0, k2] = pconfig.ph_salinity_coeffs
            ph = pH_correction_for_salinity(
                ph=dataset.ph.data,
                temperature=dataset.temperature.data,
                salinity=dataset.salinity.data,
                ph_temperature=dataset.ph_temperature.data,
                cal_psal=psal,
                k0=k0,
                k2=k2
            )
            dataset['ph'].values = ph
            add_correction_attributes_to_dataarray(dataset['ph'])
            dataset['ph'].attrs['corrections'] += 'ph values corrected using in-situ salinity.\n'
            l.log('pH correction using in-situ salinity was carried out')
        else:
            l.warning(f'pH correction aborted. Missing one or more variables in {required_variables}.')
    else:
        l.warning(f'pH correction aborted. `ph_coeffs` were not provided.')


def _dissolved_oxygen_salinity_correction(dataset: xr.Dataset, pconfig: "ProcessConfig"):
    if all(var in dataset.variables for var in ['temperature', 'salinity']):
        dataset.dissolved_oxygen.values = dissolved_oxygen_correction_for_salinity_SCOR_WG_142(
            dissolved_oxygen=dataset.dissolbed_oxygen.data,
            temperature=dataset.temperature.data,
            salinity=dataset.salinity.data
        )
        l.log(f'Dissolved oxygen correction for salinity was carried out.')
        add_correction_attributes_to_dataarray(dataset['dissolved_oxygen'])
        dataset['dissolved_oxygen'].attrs["corrections"] += 'Salinity correction carried out.\n'
        pconfig.dissolved_oxygen_is_corrected_for_salinity = True
    else:
        l.warning(f'Dissolved oxygen correction for salinity aborted. `temperature` and/or `salinity` not found.')


def _dissolved_oxygen_pressure_correction(dataset: xr.Dataset, pconfig: "ProcessConfig"):
    """Apply `magtogoek.wps.correction.dissolved_oxygen_correction_for_pressure_JAC`

    """
    if 'pres' not in dataset:
        pres = compute_pressure_at_sampling_depth(dataset=dataset, pconfig=pconfig)
        l.log(f'Dissolved oxygen correction for pressure using a depth of {pconfig.sampling_depth or 0} m')
    else:
        pres = dataset['pres'].values

    dataset.dissolved_oxygen.values = dissolved_oxygen_correction_for_pressure_JAC(
        dissolved_oxygen=dataset.dissolved_oxygen.values,
        pressure=pres
    )
    l.log(f'Dissolved oxygen correction for pressure was carried out.')
    add_correction_attributes_to_dataarray(dataset['dissolved_oxygen'])
    dataset['dissolved_oxygen'].attrs["corrections"] += 'Pressure correction carried out.\n'


def _time_drift_correction(dataset: xr.Dataset, variable: str, pconfig: "ProcessConfig"):
    """Apply `magtogoek.wps.correction.time_drift_correction`
    """
    drift = pconfig.__dict__[variable + "_drift"]
    start_time = pconfig.__dict__[variable + "_drift_start_time"]
    try:
        dataset[variable].data = time_drift_correction(
            data=dataset[variable].values,
            data_time=dataset.time.values,
            drift=drift,
            start_time=start_time
        )
        l.log(f'Time drift correction applied to {variable}.')
        add_correction_attributes_to_dataarray(dataset[variable])
        dataset[variable].attrs['corrections'] += f"Correction applied for sensor drift. Drift: {drift}, Start time: {start_time}\n"
    except ValueError as msg:
        l.warning(f'Time drift correction for {variable} failed. Error: {msg}.')


def _data_calibration_correction(dataset: xr.Dataset, variable: str, pconfig: "ProcessConfig"):
    """Apply `magtogoek.sci_tools.data_calibration_correction`
    """
    if len(pconfig.__dict__[variable + "_calibration_correction"]) == 2:
        slope = pconfig.__dict__[variable + "_calibration_correction"][0]
        offset = pconfig.__dict__[variable + "_calibration_correction"][1]

        dataset[variable].data = data_calibration_correction(
            data=dataset[variable].values,
            slope=slope,
            offset=offset
        )
        l.log(f'Calibration correction applied to {variable}. Slope: {slope}, Offset: {offset}.')
        add_correction_attributes_to_dataarray(dataset[variable])
        dataset[variable].attrs['corrections'] += "Calibration correction.\n"
    else:
        l.warning(f"Calibration correction for {variable} failed. Requires 2 coefficients (slope, offset).")



