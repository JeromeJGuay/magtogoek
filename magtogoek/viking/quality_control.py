"""
Module that contains function for viking data quality control.


Tests Flags
-----------

Notes
-----
    + Spike return a flag of 3
    + Climatology outliers get a flag of 3
    + Absolute outliers get a flag of 4


   Tests return `True` where cells fail a test.

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
from typing import *
import numpy as np
from pandas import Timestamp
import xarray as xr
from magtogoek import logger as l, FLAG_VALUES, FLAG_MEANINGS, FLAG_REFERENCE, IMPOSSIBLE_PARAMETERS_VALUES
from magtogoek.tools import outlier_values_test, climatology_outlier_test


QC_VARIABLES = [
    'atm_pressure',  # Need since atm_pressure is used for correction Dissolved Oxygen or compute Density
    'atm_temperature',
    'atm_humidity',
    'temperature',
    'salinity',
    'density',
    'dissolved_oxygen',
    'ph',
    'par',
    'fluorescence',
    'chlorophyll',
    'fdom',
    'co2_w',
]


NO_QC_VARIABLES = [
    'wave_mean_height', 'wave_maximal_height', 'wave_period',
    'wind_mean', 'wind_max', 'wind_direction_mean', 'wind_direction_max',
]


def no_meteoce_quality_control(dataset: xr.Dataset):
    """
    Notes
    -----
        SeaDataNet Quality Control Flags Value
        * 0: no_quality_control
    """
    l.section("Meteoce Quality Control")

    l.log("No quality control carried out")

    _add_ancillary_variables_to_dataset(dataset, variables=dataset.variables, default_flag=0)

    dataset.attrs["flags_reference"] = FLAG_REFERENCE
    dataset.attrs["flags_values"] = FLAG_VALUES
    dataset.attrs["flags_meanings"] = FLAG_MEANINGS
    dataset.attrs["quality_comments"] = "No quality control."


def meteoce_quality_control(
        dataset: xr.Dataset,

        regional_outlier: str = None,
        absolute_outlier: bool = True,

        climatology_variables: List[str] = None,
        climatology_dataset: xr.Dataset = None,
        climatology_threshold: float = None,
        climatology_depth_interpolation_method: str = None,

        propagate_flags: bool = True,
):
    """

    Flag propagation:

    Pressure -> Depth |
    Depth, Temperature, Salinity -> Density
    Pressure, Temperature, Salinity -> Dissolved Oxygen
    Temperature, Salinity -> pH


    Parameters
    ----------
    dataset

    regional_outlier
    absolute_outlier

    climatology_variables
    climatology_dataset
    climatology_threshold
    climatology_depth_interpolation_method

    propagate_flags


    Notes
    -----
       Tests return `True` where cells fail a test.

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


    Todos
    -----
    + spike detection
    + absolute limit detection
    + Flag propagation
    + Flag Comments attrs.

    """
    l.section("Meteoce Quality Control")

    l.warning('QUALITY CONTROL NOT TESTED.')

    _add_ancillary_variables_to_dataset(dataset, variables=QC_VARIABLES, default_flag=1)
    _add_ancillary_variables_to_dataset(dataset, variables=NO_QC_VARIABLES, default_flag=0)

    if climatology_variables is not None and climatology_dataset is not None:
        _climatology_outlier_tests(
            dataset=dataset,
            climatology_dataset=climatology_dataset,
            variables=climatology_variables,
            threshold=climatology_threshold,
            depth_interpolation_method=climatology_depth_interpolation_method
        )

    if regional_outlier in IMPOSSIBLE_PARAMETERS_VALUES:
        _impossible_values_tests(dataset, region=regional_outlier, flag=3)
    else:
        l.warning(f'Region {regional_outlier} not found in the impossible parameters values file {IMPOSSIBLE_PARAMETERS_VALUES}')

    if absolute_outlier is True:
        _impossible_values_tests(dataset, region='global', flag=4)

    if propagate_flags is True:
        _flag_propagation(dataset, use_atm_pressure=True)

    _print_percent_of_good_values(dataset)

    dataset.attrs["quality_comments"] = l.logbook.split("[Meteoce Quality Control]\n")[1]
    dataset.attrs["flags_reference"] = FLAG_REFERENCE
    dataset.attrs["flags_values"] = FLAG_VALUES
    dataset.attrs["flags_meanings"] = FLAG_MEANINGS


def _add_ancillary_variables_to_dataset(dataset: xr.Dataset, variables: str, default_flag: int = 1):
    for variable in set(dataset.variables).intersection(set(variables)):
        dataset[variable + "_QC"] = (
            ['time'], np.ones(dataset.time.shape).astype(int) * default_flag,
            {
                'quality_test': "",
                "quality_date": Timestamp.now().strftime("%Y-%m-%d"),
                "flag_meanings": FLAG_MEANINGS,
                "flag_values": FLAG_VALUES,
                "flag_reference": FLAG_REFERENCE
            }
        )


def _climatology_outlier_tests(
        dataset: xr.Dataset,
        climatology_dataset: xr.Dataset,
        variables: str,
        threshold: float,
        depth_interpolation_method: str,
):
    for variable in variables:
        try:
            outliers_flag = climatology_outlier_test(
                dataset=dataset,
                climatology_dataset=climatology_dataset,
                variable=variable,
                threshold=threshold,
                depth_interpolation_method=depth_interpolation_method
            )
            dataset[variable + "_QC"].where(~outliers_flag, other=3)

            test_comment = f"Climatology outlier test. (flag=3)"
            l.log(f"{variable}" + test_comment)
            dataset[variable + "_QC"].attrs['quality_test'].append(test_comment + "\n")

        except ValueError as msg:
            l.warning(f'Unable to carry out climatology outlier qc on {variable}.\n\t Error: {msg}')
    pass


def _impossible_values_tests(dataset: xr.Dataset, region: str, flag: int):
    """
    Iterates over the values in impossible_parameter_values.json for the region.
    """
    outliers_values = IMPOSSIBLE_PARAMETERS_VALUES[region]

    for variable in set(dataset.variables).intersection(set(outliers_values.keys())):
        outliers_flag = outlier_values_test(
            dataset[variable].data,
            lower_limit=outliers_values[variable]['min'],
            upper_limit=outliers_values[variable]['max']
        )
        dataset[variable + "_QC"][outliers_flag] = flag

        test_comment = \
            f"{region} outlier threshold: less than {outliers_values[variable]['min']} {outliers_values[variable]['units']} " \
            f"and greater than {outliers_values[variable]['max']} {outliers_values[variable]['units']} (flag={flag})."

        l.log(f"{variable} :" + test_comment)
        dataset[variable+"_QC"].attrs['quality_test'].append(test_comment + "\n")


def _flag_propagation(dataset: xr.Dataset, use_atm_pressure: bool = False):
    """ Maybe move to wps

    Parameters
    ----------
    dataset :

    use_atm_pressure :
        if True, atm_pressure flag will be used instead of pres for propagation. (surface data).

    Pressure -> Depth
    Depth, Temperature, Salinity -> Density
    Pressure, Temperature, Salinity -> Dissolved Oxygen
    Temperature, Salinity -> pH
    """
    pressure = 'atm_pressure' if use_atm_pressure is True else 'pres'
    flag_propagation_rules = {
        'depth': [pressure],
        'density': ['pres', 'temperature', 'salinity'],
        'dissolved_oxygen': [pressure, 'temperature', 'salinity'],
        'ph': ['temperature', 'salinity'],
        }

    for variable in set(dataset.variables).intersection(set(flag_propagation_rules.keys())):
        _flags = flag_propagation_rules[variable] + [variable]
        dataset[variable+"_QC"] = np.stack([dataset[v+'_QC'].data for v in _flags], axis=-1).max(axis=-1)
        propagation_comment = f'Flags propagation {flag_propagation_rules[variable]} -> {variable}.\n'
        l.log(propagation_comment)
        dataset[variable].attrs['quality_test'].append(propagation_comment)


def _print_percent_of_good_values(dataset: xr.Dataset):
    """Only check for variables in QC_VARIABLES"""
    for variable in set(dataset.variables).intersection(set(QC_VARIABLES)):
        if "_QC" in variable:
            percent_of_good_values = np.sum(dataset.variables <= 2) / len(dataset.time)
            l.log(f"{round(percent_of_good_values * 100, 2)}% of {variable.strip('_QC')} have flags of 1 or 2.")

