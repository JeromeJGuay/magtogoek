import numpy as np
import xarray as xr
from typing import List
from pandas import Timestamp

from magtogoek import logger as l, CONFIGURATION_PATH
from magtogoek.process_common import FLAG_ATTRIBUTES
from magtogoek.sci_tools import data_spike_detection
from magtogoek.utils import json2dict

IMPOSSIBLE_PARAMETERS_VALUES_FILE_PATH = CONFIGURATION_PATH.joinpath("impossible_parameter_values.json")
IMPOSSIBLE_PARAMETERS_VALUES = json2dict(IMPOSSIBLE_PARAMETERS_VALUES_FILE_PATH)



CLIMATOLOGY_TIME_FORMATS = {
        'dayofyear': 'time.dayofyear',
        'weekofyear': 'time.week',
        'monthofyear': 'time.month',
        'season': 'time.season'
    }
SEASONS_ID = ('DJF', 'JJA', 'MAM', 'SON')


def find_missing_values(data: np.ndarray) -> np.ndarray:
    return ~np.isfinite(data)


def values_outliers_detection(data: np.ndarray, lower_limit: float, upper_limit: float) -> np.ndarray:
    """Check for data outlier

    Parameters
    ----------
    data :
        Data to check
    lower_limit :
        Outlier need to be smaller than the `lower_limit`.
    upper_limit :
        Outlier need to be greater than the `upper_limit`.

    Returns
    -------
    Boolean array of the same shape as `data`
    """
    return np.bitwise_or(data < lower_limit, data > upper_limit)


def find_climatology_outlier(
        dataset: xr.Dataset,
        climatology_dataset: xr.Dataset,
        variable: str,
        threshold: float,
        depth_interpolation_method='linear'
) -> xr.DataArray:
    """Flag data that are outside the climatology.

    # FIXME Test needs to be carried out for:  different resolutions, missing values
    # TODO CHECK CF CONVENTION FOR CLIMATOLOGY DATASET. variable attributes: Cell_Method

    Parameters
    ----------
    dataset :
        Dataset containing the data to compare.
    climatology_dataset :
        Dataset containing the climatology.
        For any give `variable_name` to compare with the climatology,
        the climatology dataset should be structured as follow:
            Variables:
                variable_name + '_mean'
                variable_name + '_std'
            Time coords:
                'dayofyear': 1 .. 366
                'weekofyear': 1 .. 52
                'monthofyear': 1 .. 12
                'season': 'DJF', 'JJA', 'MAM', 'SON'
    variable :
        Variable to carry climatology test on.
    threshold :
        factor that is multiplier to the standard deviation.
    depth_interpolation_method :
        Only use when the data has a depth component.
        "linear", "nearest", "zero", "slinear", "quadratic", "cubic" (See xarray documentation)

    Returns
    -------
    Return boolean dataarray with values of:

        [True] < (mean - threshold * std) <= [False] <= (mean + threshold * std) < [True]
    """
    # Check for the variable in the dataset
    if variable not in dataset:
        raise KeyError(f'Variable not found in dataset {variable}')

    # Check for climatology variables `mean` and `std
    for var in [variable + s for s in ('_mean', '_std')]:
        if var not in climatology_dataset:
            raise KeyError(f'variable not in climatology dataset {var}')

    clim_time = _get_climatology_time_coord(climatology_dataset, variable)

    # Group Data into clim_time
    grouped_data = dataset[variable].groupby(clim_time)

    # Interpolation of the climatology to over the dataset depths.
    if 'depth' in dataset.variables and 'depth' in climatology_dataset:
        climatology_dataset = climatology_dataset.interp(depth=dataset.depth, method=depth_interpolation_method)

    # Defining upper and lower limits
    lower_limits = climatology_dataset[variable + '_mean'] - threshold * climatology_dataset[variable + '_std']
    upper_limits = climatology_dataset[variable + '_mean'] + threshold * climatology_dataset[variable + '_std']

    # Returns boolean array where outlier return True.
    return (grouped_data > upper_limits) | (grouped_data < lower_limits)


def _get_climatology_time_coord(dataset: xr.Dataset, variable: str) -> str:
    """TODO"""
    mean_clim_time = _find_climatology_variable_time_coord(dataset[variable + '_mean'])
    std_clim_time = _find_climatology_variable_time_coord(dataset[variable + '_std'])
    if mean_clim_time != std_clim_time:
        raise ValueError(f'The mean and std climatology for {variable} have different climatological time coords.')

    clim_time = mean_clim_time

    if clim_time == 'time.season':
        if set(dataset.season.values) != set(SEASONS_ID):
            raise ValueError("Invalid season ID for climatology. Season IDs: ['DJF', 'JJA', 'MAM', 'SON'].")

    return clim_time


def _find_climatology_variable_time_coord(dataarray: xr.DataArray) -> str:
    """TODO"""
    intersection = list(set(dataarray.coords).intersection(set(CLIMATOLOGY_TIME_FORMATS.keys())))
    if len(intersection) == 1:
        return CLIMATOLOGY_TIME_FORMATS[intersection[0]]
    else:
        raise ValueError(f'Climatology time not found in climatology dataset for variable: {dataarray.name}.')


def climatology_outlier_test(
        dataset: xr.Dataset,
        climatology_dataset: xr.Dataset,
        variable: str,
        threshold: float,
        depth_interpolation_method: str,
):
    """Find climatology outlier and add an ancillary variable to the dataset
    named : <variable>_QC_climatology_outlier

    Parameters
    ----------
    dataset :
        Dataset containing the data to compare.
    climatology_dataset :
        Dataset containing the climatology.
        For any give `variable_name` to compare with the climatology,
        the climatology dataset should be structured as follow:
            Variables:
                variable_name + '_mean'
                variable_name + '_std'
            Time coords:
                'dayofyear': 1 .. 366
                'weekofyear': 1 .. 52
                'monthofyear': 1 .. 12
                'season': 'DJF', 'JJA', 'MAM', 'SON'
    variable :
        Variable to carry climatology test on.
    threshold :
        factor that is multiplier to the standard deviation.
    depth_interpolation_method :
        Only use when the data has a depth component.
        "linear", "nearest", "zero", "slinear", "quadratic", "cubic" (See xarray documentation)
    """
    outliers_flag = find_climatology_outlier(
        dataset=dataset,
        climatology_dataset=climatology_dataset,
        variable=variable,
        threshold=threshold,
        depth_interpolation_method=depth_interpolation_method
    )

    _add_climatology_qc_variable(dataset, variable)

    dataset[variable + "_QC_climatology_outlier"] = dataset[variable + "_QC_climatology_outlier"].where(~outliers_flag, other=3)

    test_comment = f"Climatology outlier test. Range: {threshold} times the standard deviation around the mean. (flag=3)"
    l.log(f"{variable}: " + test_comment)
    dataset[variable + "_QC_climatology_outlier"].attrs['quality_test'] += test_comment + "\n"


def _add_climatology_qc_variable(dataset: xr.Dataset, variable: str):
    """"""
    dataset[variable + "_QC_climatology_outlier"] = (
        dataset[variable].dims, np.ones(dataset[variable].shape).astype(int),
        {'quality_test': "", "quality_date": Timestamp.now().strftime("%Y-%m-%d")}
    )
    dataset[variable + "_QC_climatology_outlier"].attrs.update(FLAG_ATTRIBUTES)


def data_spike_detection_tests(dataset: xr.Dataset, variable: str, threshold: float, window: int):
    """
    Carry spike detection for inner and other threshold.

    Adds add an ancillary variable named <variable>_QC to dataset if one does not exist.
        Set ancillary Set new_flag of 3 for spikes.

    Parameters
    ----------
    dataset:

    variable:

    threshold:

    See Also
    --------
    magtogoek/quality_control_common/data_spike_detection()
    """
    spikes_flag = data_spike_detection(
        dataset[variable].data,
        threshold=threshold,
        window=window
    )
    if variable + "_QC" not in dataset.variables:
        add_ancillary_QC_variable_to_dataset(dataset=dataset, variable=variable, default_flag=1)

    add_flags_values(dataset[variable + "_QC"].values, spikes_flag * 3)

    test_comment = \
        f"Spike detection threshold {threshold} {dataset[variable].attrs['units']} (flag=3)"

    l.log(f"{variable}: " + test_comment)
    dataset[variable+"_QC"].attrs['quality_test'] += test_comment + "\n"


def add_ancillary_QC_variable_to_dataset(dataset: xr.Dataset, variable: str, default_flag=1):
    """Add an ancillary variable named <variable>_QC to dataset."""
    dataset[variable + "_QC"] = (
        dataset[variable].dims, np.ones(dataset[variable].shape).astype(int) * default_flag,
        {'quality_test': "", "quality_date": Timestamp.now().strftime("%Y-%m-%d")}
    )
    dataset[variable + "_QC"].attrs.update(FLAG_ATTRIBUTES)


def add_flags_values(flag_variable: np.ndarray, new_flags: np.ndarray):
    """Add `new_flags` values if it's greater than the current `ancillary_variable` values.

    Parameters
    ----------
    flag_variable :
        Variable to add `flag` value to.
    new_flags :
        Flag value to add.

    Returns
    -------

    """
    np.maximum(flag_variable, new_flags, out=flag_variable)


def merge_flags(flags_arrays: List[np.ndarray]) -> np.ndarray:
    """Merge flags_arrays keeping the greatest values"""
    return np.stack(flags_arrays, axis=-1).max(axis=-1)
