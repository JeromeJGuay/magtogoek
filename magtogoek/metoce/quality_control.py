"""
Date: February 2023
Made by jeromejguay

Module that contains functions for metoce data quality control.


Notes
-----
    + Absolute outliers get a flag of 4

   SeaDataNet Quality Control Flags Value
   * 0: no_quality_control
   * 1: good_value
   * 2: probably_good_value
   * 3: probably_bad_value
       - Unusual data value, inconsistent with real phenomena.
   * 4: bad_value
       - Obviously erroneous data value.
   * 5: changed_value
   * 6: value_below_detection
   * 7: value_in_excess
   * 8: interpolated_value
   * 9: missing_value


"""
import numpy as np
import xarray as xr
from typing import List, Dict, TYPE_CHECKING

from magtogoek import logger as l
from magtogoek.quality_control_common import IMPOSSIBLE_PARAMETERS_VALUES, values_outliers_detection, \
    add_ancillary_QC_variable_to_dataset, add_flags_values, merge_flags, \
    find_missing_values, data_spike_detection_tests
from magtogoek.process_common import FLAG_ATTRIBUTES

if TYPE_CHECKING:
    from magtogoek.metoce.process import ProcessConfig


# If modified, carry the modification to `metoce.process.ProcessConfig` and to `process_configurations.py`.
SPIKE_QC_VARIABLES = [
    "salinity", "temperature", "dissolved_oxygen", "ph", "scattering", "chlorophyll", "fdom"
]


VARIABLES_WITH_QC = { # 1: QC(default flag = 1) , 0: No Qc (default flag = 0)
    "wind_speed":0,
    "wind_direction":0,
    "wind_gust":0,
    "wind_gust_direction":0,
    'atm_temperature': 1,
    'atm_humidity': 1,
    'atm_pressure': 1,
    'wave_mean_height': 0,
    'wave_maximal_height': 0,
    'wave_period': 0,
    'wave_direction': 0,
    'temperature': 1,
    'conductivity': 0,
    'salinity': 1,
    'density': 1,
    'dissolved_oxygen': 1,
    'ph': 1,
    'par': 0,
    'scattering': 1,
    'chlorophyll': 1,
    'fdom': 1,
    'pco2_air': 0,
    'pco2_water': 0
    }

QC_VARIABLES = [k for k, v in VARIABLES_WITH_QC.items() if v == 1]


NO_QC_VARIABLES = [k for k, v in VARIABLES_WITH_QC.items() if v == 0]


def no_metoce_quality_control(dataset: xr.Dataset):
    """
    Notes
    -----
        SeaDataNet Quality Control Flags Value
        * 0: no_quality_control
    """
    l.section("Metoce Quality Control")

    l.log("No quality control carried out")

    _add_ancillary_variables_to_dataset(dataset, variables=VARIABLES_WITH_QC, default_flag=0)

    dataset.attrs.update(FLAG_ATTRIBUTES)
    dataset.attrs["quality_comments"] = "No quality control."


def metoce_quality_control(dataset: xr.Dataset, pconfig: "ProcessConfig"):
    l.section("Metoce Quality Control")

    _add_ancillary_variables_to_dataset(dataset, variables=QC_VARIABLES, default_flag=1)
    _add_ancillary_variables_to_dataset(dataset, variables=NO_QC_VARIABLES, default_flag=0)

    if pconfig.regional_outlier is not None:
        if pconfig.regional_outlier in IMPOSSIBLE_PARAMETERS_VALUES:
            _impossible_values_tests(dataset, region=pconfig.regional_outlier, flag=3)
        else:
            l.warning(f'Region {pconfig.regional_outlier} not found in the impossible parameters values file {IMPOSSIBLE_PARAMETERS_VALUES}')

    if pconfig.absolute_outlier is True:
        _impossible_values_tests(dataset, region='global', flag=4)


    _spike_detection_tests(dataset, pconfig=pconfig)

    _flag_missing_values(dataset)

    if pconfig.propagate_flags is True:
        _propagate_flag(dataset, pconfig=pconfig)

    _print_percent_of_good_values(dataset)

    dataset.attrs["quality_comments"] = l.logbook.split("[Metoce Quality Control]\n")[1]
    dataset.attrs.update(FLAG_ATTRIBUTES)


def _add_ancillary_variables_to_dataset(dataset: xr.Dataset, variables: List[str], default_flag: int = 1):
    for variable in set(dataset.keys()) & set(variables):
        add_ancillary_QC_variable_to_dataset(dataset=dataset, variable=variable, default_flag=default_flag)


def _impossible_values_tests(dataset: xr.Dataset, region: str, flag: int):
    """
    Iterates over the values in impossible_parameter_values.json for the region.
    """
    outliers_values = IMPOSSIBLE_PARAMETERS_VALUES[region]

    for variable in set(dataset.keys()) & set(outliers_values.keys()) & set(QC_VARIABLES):
        _data = dataset[variable].values

        if 'units' in dataset[variable].attrs:
            if dataset[variable].attrs['units'] != outliers_values[variable]['units']:
                _data = dataset[variable].pint.quantify().pint.to(
                    outliers_values[variable]['units']
                ).pint.dequantify().values
        else:
            l.warning(f"(outlier test, region: {region}) Could not verify units for {variable} due missing units on loaded variable.")

        outliers_flag = values_outliers_detection(
            _data,
            lower_limit=outliers_values[variable]['min'],
            upper_limit=outliers_values[variable]['max']
        )
        add_flags_values(dataset[variable + "_QC"].values, outliers_flag * flag)

        test_comment = \
            f"{region} outlier threshold: less than {outliers_values[variable]['min']} {outliers_values[variable]['units']} " \
            f"and greater than {outliers_values[variable]['max']} {outliers_values[variable]['units']} (flag={flag})."

        l.log(f"{variable} " + test_comment)

        dataset[variable+"_QC"].attrs['quality_test'] += test_comment + "\n"


def _spike_detection_tests(dataset: xr.Dataset, pconfig: "ProcessConfig"):
    spike_tests = {
        var: {
            'threshold': pconfig.__getattribute__(var + "_spike_threshold"),
            'window': pconfig.__getattribute__(var + "_spike_window")}
        for var in SPIKE_QC_VARIABLES
    }
    for var in set(dataset.keys()) & set(spike_tests.keys()):
        if spike_tests[var]['threshold'] is not None:
            data_spike_detection_tests(
                dataset=dataset,
                variable=var,
                threshold=spike_tests[var]['threshold'],
                window=spike_tests[var]['window']
            )


def _flag_missing_values(dataset: xr.Dataset):
    """Flag missing values for all metoce variables."""
    for variable in set(dataset.keys()).intersection(set(VARIABLES_WITH_QC.keys())):
        add_flags_values(dataset[variable + "_QC"].data, find_missing_values(dataset[variable].values) * 9)


def _propagate_flag(dataset: xr.Dataset, pconfig: "ProcessConfig"):
    """
    Propagation Rules
    -----------------
        Pressure -> Depth
        Depth, Temperature, Salinity -> Density
        Pressure, Temperature, Salinity -> Dissolved Oxygen
        Temperature, Salinity -> pH

    Parameters
    ----------
    dataset

    """

    flag_propagation_rules = {
        'density_QC': ['temperature_QC', 'salinity_QC', 'density_QC'],
        'dissolved_oxygen_QC': ['temperature_QC', 'salinity_QC', 'dissolved_oxygen_QC'],
        }

    if pconfig.ph_is_corrected is True:
        flag_propagation_rules['ph_QC'] = ['temperature_QC', 'salinity_QC', 'ph_QC']


    for variable in set(dataset.keys()) & set(flag_propagation_rules.keys()):

        qc_variables = [dataset[_var].data for _var in set(flag_propagation_rules[variable]) & set(dataset.variables)]

        dataset[variable].data = merge_flags(flags_arrays=qc_variables)

        propagation_comment = f'Flags propagation {flag_propagation_rules[variable]} -> {variable}.'

        l.log(propagation_comment)

        dataset[variable].attrs['quality_test'] += propagation_comment + "\n"


def _print_percent_of_good_values(dataset: xr.Dataset):
    """Only check for variables in QC_VARIABLES"""
    for variable in set(dataset.keys()).intersection(set(QC_VARIABLES)):
        if "_QC" in variable:
            percent_of_good_values = np.sum(dataset[variable + "_QC"] <= 2) / len(dataset.time)
            l.log(f"{round(percent_of_good_values * 100, 2)}% of {variable.strip('_QC')} have flags of 1 or 2.")
