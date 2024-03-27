"""
Module that contains function for adcp data quality control.

Based on the adcp2nc package by jeanlucshaw: https://github.com/jeanlucshaw/adcp2nc/

Notes
-----
   Tests return `True` where cells fail a test.

   - Cells that haven't failed any test are given a flag value of `1` (probably_good_value).
   - Velocities in any direction are set to NaN if greater than 15 meters per second gets a 4.
   - Failing amplitude, correlation, percentgood, roll, pitch, side_lobe, horizontal
   velocity or vertical velocity test returns a flag_value of `3` (probably_bad_value)
   for the corresponding velocity cells.
   - Temperatures outside [-2, 32] Celsius have a flag_value of `4` (bad_value).
   - Pressures outside [0, 180] dbar value have a flag_value of `4` (bad_value).
   and the corresponding velocity cells have a flag_value of `3` (probably_bad_value)
   - The amplitude, correlation and percentgood thresholds are also applied to
   sentinelV fifth beam data.


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

NOTE
IML flags meaning : (Basically the same)
   * 0: no_quality_control
   * 1: value_seems_correct
   * 2: value_appears_inconsistent_with_other_values
   * 3: values_seems_doubtful
   * 4: value_seems_erroneous
   * 5: value_was_modified
   * 9: value_missing

"""
import numpy as np
import typing as tp
import xarray as xr
from scipy.stats import circmean

from magtogoek import logger as l
from magtogoek.quality_control_common import find_missing_values, IMPOSSIBLE_PARAMETERS_VALUES, values_outliers_detection, \
    add_flags_values, add_ancillary_QC_variable_to_dataset
from magtogoek.process_common import FLAG_ATTRIBUTES
from magtogoek.sci_tools import circular_distance

ABSOLUTE_IMPOSSIBLE_VELOCITY = 15

GLOBAL_IMPOSSIBLE_PARAMETERS = IMPOSSIBLE_PARAMETERS_VALUES["global"]


def no_adcp_quality_control(dataset: xr.Dataset, velocity_only: bool = False):
    """Adds var_QC ancillary variables to dataset with value 0.

    Ancillary variables:  temperature, pres, u, v, w.

    SeaDataNet Quality Control Flags Value
    * 0: no_quality_control

    Parameters
    ----------
    dataset :
        ADCP dataset formatted as done by adcp_init.
    velocity_only :
        If True, only velocities will receive quality variables.
    """
    l.section("Adcp Quality Controlled")

    l.log("No quality control carried out")

    variables = ['v1', 'v2', 'v3', 'v4', 'u', 'v', 'w']
    if velocity_only is False:
        variables += ["temperature", "pres"]

    for var in set(variables).intersection(set(dataset.variables)):
        add_ancillary_QC_variable_to_dataset(
            dataset=dataset,
            variable=var,
            default_flag=0
        )

    dataset.attrs.update(FLAG_ATTRIBUTES)
    dataset.attrs["quality_comments"] = "No quality control."


def adcp_quality_control(
    dataset: xr.Dataset,
    amp_th: int = 30,
    corr_th: int = 64,
    pg_th: int = 90,
    roll_th: float = 20,
    pitch_th: float = 20,
    horizontal_vel_th: float = 5,
    vertical_vel_th: float = 5,
    error_vel_th: float = 5,
    sidelobes_correction: bool = False,
    bottom_depth: float = None,
    bad_pressure: bool = False
):
    """
    Perform ADCP quality control.

    This was adapted from jeanlucshaw adcp2nc package.

    Parameters
    ----------
    dataset :
        ADCP dataset formatted as done by adcp_init.
    amp_th :
        Require more than this amplitude values.
    pg_th :
        Require more than this percentage of good 4-beam transformations.
    corr_th :
        Require more than this beam correlation value.
    roll_th :
        Require roll values be smaller than this value (degrees).
    pitch_th :
        Require pitch values be smaller than this value (degrees).
    horizontal_vel_th:
        Require u, v  values be smaller than this value (meter per seconds).
    vertical_vel_th :
        Require w values be smaller than this value (meter per seconds).
    error_vel_th :
        Require e values be smaller than this value (meter per seconds).
    sidelobes_correction :
        Use fixed depth or bottom track range to remove side lobe
        contamination. Set to either "dep" or "bt" or None.
    bottom_depth :
        If not `None`, this depth used for removing side lobe contamination.
    bad_pressure:
        If True, XducerDepth is set to 0 or to `sensor_depth` if provided.

    Notes
    -----
       Tests return `True` where cells fail a test.

       - Cells that haven't failed any test are given a flag value of `2` (probably_good_value).
       - Failing amplitude, correlation, percentgood, roll, pitch, side_lobe, horizontal
       velocity or vertical velocity test returns a flag_value of `3` (probably_bad_value)
       for the corresponding velocity cells.
       - Temperatures outside [-2, 32] Celsius have a flag_value of `4` (bad_value).
       - Pressures outside [0, 180] dbar value have a flag_value of `4` (bad_value).
       and the corresponding velocity cells have a flag_value of `3` (probably_bad_value)
       - The amplitude, correlation and percentgood thresholds are also applied to
       sentinelV fifth beam data.


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
    l.section("Adcp Quality Control")

    vel_flags = np.ones(dataset.depth.shape + dataset.time.shape).astype(int)
    binary_mask = np.zeros(dataset.depth.shape + dataset.time.shape).astype(int)

    vel_qc_test = []
    binary_mask_tests_value: tp.List[tp.Optional[int, float]] = [None] * 9

    if amp_th is not None:
        l.log(f"amplitude threshold {amp_th}")
        amp_flag = amplitude_test(dataset, amp_th)
        add_flags_values(vel_flags, amp_flag * 3)
        vel_qc_test.append(f"amplitude_threshold:{amp_th} (flag=3).")
        binary_mask[amp_flag] += 2 ** 0
        binary_mask_tests_value[0] = amp_th

    if corr_th is not None:
        l.log(f"correlation threshold {corr_th}")
        corr_flag = correlation_test(dataset, corr_th)
        add_flags_values(vel_flags, corr_flag * 3)
        vel_qc_test.append(f"correlation_threshold:{corr_th} (flag=3).")
        binary_mask[corr_flag] += 2 ** 1
        binary_mask_tests_value[1] = corr_th

    if pg_th is not None:
        l.log(f"percentgood threshold {pg_th}")
        pg_flag = percentgood_test(dataset, pg_th)
        add_flags_values(vel_flags, pg_flag * 3)
        vel_qc_test.append(f"percentgood_threshold:{pg_th} (flag=3).")
        binary_mask[pg_flag] += 2 ** 2
        binary_mask_tests_value[2] = pg_th

    if dataset.attrs['coord_system'] == "earth":
        if horizontal_vel_th is not None:
            l.log(f"horizontal velocity threshold {horizontal_vel_th} m/s")
            horizontal_vel_flag = horizontal_vel_test(dataset, horizontal_vel_th)
            add_flags_values(vel_flags, horizontal_vel_flag * 3)
            vel_qc_test.append(f"horizontal_velocity_threshold:{horizontal_vel_th} m/s (flag=3).")
            binary_mask[horizontal_vel_flag] += 2 ** 3
            binary_mask_tests_value[3] = horizontal_vel_th

        if vertical_vel_th is not None:
            l.log(f"vertical velocity threshold {vertical_vel_th} m/s")
            vertical_vel_flag = vertical_vel_test(dataset, vertical_vel_th)
            add_flags_values(vel_flags, vertical_vel_flag * 3)
            vel_qc_test.append(f"vertical_velocity_threshold:{vertical_vel_th} m/s (flag=3).")
            binary_mask[vertical_vel_flag] += 2 ** 4
            binary_mask_tests_value[4] = vertical_vel_th

    if dataset.attrs['coord_system'] in ["xyz", "earth"]:
        if error_vel_th is not None:
            l.log(f"error velocity threshold {error_vel_th} m/s")
            error_vel_flag = error_vel_test(dataset, error_vel_th)
            add_flags_values(vel_flags, error_vel_flag * 3)
            vel_qc_test.append(f"velocity_error_threshold:{error_vel_th} m/s (flag=3).")
            binary_mask[error_vel_flag] += 2 ** 5
            binary_mask_tests_value[5] = error_vel_th

    if roll_th is not None:
        l.log(f"Roll threshold {roll_th} degree")
        roll_flag = np.tile(roll_test(dataset, roll_th), dataset.depth.shape + (1,))
        add_flags_values(vel_flags, roll_flag * 3)
        vel_qc_test.append(f"roll_threshold:{roll_th} degree (flag=4).")
        binary_mask[roll_flag] += 2 ** 6
        binary_mask_tests_value[6] = roll_th

    if pitch_th is not None:
        l.log(f"Pitch threshold {pitch_th} degree")
        pitch_flag = np.tile(pitch_test(dataset, pitch_th), dataset.depth.shape + (1,))
        add_flags_values(vel_flags, pitch_flag * 3)
        vel_qc_test.append(f"pitch_threshold:{pitch_th} degree (flag=3).")
        binary_mask[pitch_flag] += 2 ** 7
        binary_mask_tests_value[7] = pitch_th

    if sidelobes_correction is True:
        sidelobe_flag, msg = sidelobe_test(dataset, bottom_depth)
        if isinstance(sidelobe_flag, np.ndarray):
            l.log(f"Sidelobe correction carried out. {msg}. (flag=3).")
            add_flags_values(vel_flags, sidelobe_flag * 3)
            vel_qc_test.append("sidelobes")
            binary_mask[sidelobe_flag] += 2 ** 8
            binary_mask_tests_value[8] = sidelobes_correction

    if "pres" in dataset:
        add_ancillary_QC_variable_to_dataset(dataset=dataset, variable='pres', default_flag=1)
        if bad_pressure is True:
            l.log("Pressure were flagged as bad (4) by the user.")
            dataset["pres_QC"].values *= 4
            dataset["pres_QC"].attrs[
                "quality_test"] = "Flagged as bad (4) by the user."
        else:
            _msg = f"Pressure_threshold: less than {GLOBAL_IMPOSSIBLE_PARAMETERS['pres']['min']} dbar and greater than {GLOBAL_IMPOSSIBLE_PARAMETERS['pres']['max']} dbar (flag=4)."

            pressure_flag = pressure_test(dataset)
            l.log(_msg)
            add_flags_values(dataset["pres_QC"].data, pressure_flag * 4)
            dataset["pres_QC"].attrs["quality_test"] += _msg + '\n'

            tiled_pressure_flag = np.tile(pressure_flag, dataset.depth.shape + (1,))
            add_flags_values(vel_flags, tiled_pressure_flag * 3)
            vel_qc_test.append(_msg)

    if "temperature" in dataset:
        add_ancillary_QC_variable_to_dataset(dataset=dataset, variable='temperature', default_flag=1)

        _msg = f"Good temperature range {GLOBAL_IMPOSSIBLE_PARAMETERS['temperature']['min']} to {GLOBAL_IMPOSSIBLE_PARAMETERS['temperature']['max']} celsius (flag=4)"

        temperature_flags = temperature_test(dataset)
        add_flags_values(dataset['temperature_QC'].data, temperature_flags*4)
        dataset["temperature_QC"].attrs["quality_test"] += _msg + '\n'
        l.log(_msg)

    if "vb_vel" in dataset:
        l.log(
            "Fifth beam quality control carried out with"
            + f"amplitude_threshold: {amp_th}" * ("vb_amp" in dataset)
            + f", correlation_threshold: {corr_th}" * ("vb_corr" in dataset)
            + f", percentgood_threshold: {pg_th}" * ("vb_pg" in dataset)
            + "."
        )
        vb_flag = vertical_beam_test(dataset, amp_th, corr_th, pg_th)

        add_ancillary_QC_variable_to_dataset(dataset=dataset, variable='vb_vel', default_flag=1)
        # FIXME ------------------ (March 2023 I forgot what was the problem)
        add_flags_values(dataset["vb_vel_QC"].data, vb_flag * 3)
        dataset["vb_vel_QC"].attrs["quality_test"] = (
            f"amplitude_threshold: {amp_th}\n" * ("vb_amp" in dataset)
            + f"correlation_threshold: {corr_th}\n" * ("vb_corr" in dataset)
            + f"percentgood_threshold: {pg_th}\n" * ("vb_pg" in dataset)
        )

    if dataset.attrs['coord_system'] != "beam":
        impossible_vel_flag = flag_implausible_vel(dataset, threshold=ABSOLUTE_IMPOSSIBLE_VELOCITY)
        add_flags_values(vel_flags, impossible_vel_flag * 4)
        l.log(f"Implausible velocity, greater than {ABSOLUTE_IMPOSSIBLE_VELOCITY}, were flagged as bad (4).")

    if dataset.attrs['coord_system'] == "beam":
        velocity_variables = ("v1", "v2", "v3", "v4")
    else:
        velocity_variables = ("u", "v", "w")

    missing_vel = np.sum(
        np.stack(
            [find_missing_values(dataset[v].values) for v in velocity_variables]
        ), axis=0, dtype=bool)

    add_flags_values(vel_flags, missing_vel*9)

    for v in velocity_variables:
        add_ancillary_QC_variable_to_dataset(dataset=dataset, variable=v, default_flag=1)
        dataset[v + "_QC"].data = vel_flags
        # dataset[v + "_QC"] = (["depth", "time"], vel_flags)
        dataset[v + "_QC"].attrs["quality_test"] = "\n".join(vel_qc_test)

    dataset.attrs["quality_comments"] = l.logbook.split("[Adcp Quality Control]\n")[1]

    percent_good_vel = (np.sum(vel_flags == 1) + np.sum(vel_flags == 2)) / (len(dataset.depth) * len(dataset.time))
    l.log(f"{round(percent_good_vel * 100, 2)}% of the velocities have flags of 1 or 2.")

    dataset.attrs.update(FLAG_ATTRIBUTES)

    dataset["binary_mask"] = (["depth", "time"], binary_mask)

    dataset.attrs["binary_mask_tests"] = [
        "amp",
        "corr",
        "pg",
        "horizontal vel",
        "vertical vel",
        "error",
        "roll",
        "pitch",
        "sidelobe",
    ]
    dataset.attrs["binary_mask_tests_values"] = binary_mask_tests_value


def flag_implausible_vel(
    dataset: xr.Dataset, threshold: float = 15
) -> tp.Type[np.array]:
    """Abs(Values) greater than `threshold` return True"""
    return (
        (abs(dataset.u) > threshold) & (abs(dataset.v) > threshold) & (abs(dataset.w) > threshold)
    ).data


def correlation_test(dataset: xr.Dataset, threshold: int):
    """
    Value must be greater than the threshold to be good. (True fails)
    NOTE JeanLucShaw used absolute but is it needed ?"""

    if all(f"corr{i}" in dataset for i in range(1, 5)):
        return (
            (dataset.corr1 < threshold)
            & (dataset.corr2 < threshold)
            & (dataset.corr3 < threshold)
            & (dataset.corr4 < threshold)
        ).data
    else:
        l.warning("Correlation test aborted. Missing one or more corr data")
        return np.full(dataset.depth.shape + dataset.time.shape, False)


def amplitude_test(dataset: xr.Dataset, threshold: int):
    """
    Value must be greater than the threshold to be good. (True fails)
    NOTE JeanLucShaw used absolute but is it needed ?"""
    if all(f"amp{i}" in dataset for i in range(1, 5)):
        return (
            (dataset.amp1 < threshold)
            & (dataset.amp2 < threshold)
            & (dataset.amp3 < threshold)
            & (dataset.amp4 < threshold)
        ).data
    else:
        l.warning("Amplitude test aborted. Missing one or more amp data")
        return np.full(dataset.depth.shape + dataset.time.shape, False)


def percentgood_test(dataset: xr.Dataset, threshold: int):
    """
    Value must be greater than the threshold to be good. (True fails)
    NOTE JeanLucShaw used absolute but is it needed ?"""
    if "pg" in dataset:
        return (dataset.pg < threshold).data
    else:
        l.warning("Percent Good test aborted. Missing one or more pg data")
        return np.full(dataset.depth.shape + dataset.time.shape, False)


def roll_test(dataset: xr.Dataset, threshold: float) -> tp.Type[np.array]:
    """
    Roll conditions (True fails)
    Distance from mean"""
    if "roll_" in dataset:
        roll_mean = circmean(dataset.roll_.values, low=-180, high=180, nan_policy='omit')
        roll_from_mean = circular_distance(dataset.roll_.values, roll_mean, units="deg")
        return roll_from_mean > threshold
    else:
        l.warning("Roll test aborted. Missing roll data")
        return np.full(dataset.time.shape, False)


def pitch_test(dataset: xr.Dataset, threshold: float) -> tp.Type[np.array]:
    """
    Pitch conditions (True fails)
    Distance from Mean
    """
    if "pitch" in dataset:
        pitch_mean = circmean(dataset.pitch.values, low=-180, high=180, nan_policy='omit')
        pitch_from_mean = circular_distance(dataset.pitch.values, pitch_mean, units="deg")
        return pitch_from_mean > threshold

    else:
        l.warning("Pitch test aborted. Missing pitch data")
        return np.full(dataset.time.shape, False)


def horizontal_vel_test(dataset: xr.Dataset, threshold: float) -> tp.Type[np.array]:
    """
    None finite value value will also fail"""

    horizontal_velocity = np.sqrt(dataset.u ** 2 + dataset.v ** 2)

    return np.greater(horizontal_velocity.values, threshold)


def vertical_vel_test(dataset: xr.Dataset, threshold: float) -> tp.Type[np.array]:
    """
    None finite value value will also fail"""
    return np.greater(abs(dataset.w.values), threshold)


def error_vel_test(dataset: xr.Dataset, threshold: float) -> tp.Type[np.array]:
    """
    None finite value value will also fail"""
    return np.greater(abs(dataset.e.values), threshold)


def vertical_beam_test(
    dataset: xr.Dataset,
    amp_threshold: float,
    corr_threshold: float,
    pg_threshold: float,
) -> tp.Type[np.array]:

    vb_test = np.full(dataset.depth.shape + dataset.time.shape, False)
    if "vb_amp" in dataset.variables and amp_threshold:
        vb_test[dataset.vb_amp < amp_threshold] = True
    if "vb_corr" in dataset.variables and corr_threshold:
        vb_test[dataset.vb_corr < corr_threshold] = True
    if "vb_pg" in dataset.variables and pg_threshold:
        vb_test[dataset.vb_pg < pg_threshold] = True

    return vb_test


def sidelobe_test(dataset: xr.Dataset, bottom_depth: float = None) -> tp.Union[tp.Tuple[np.ndarray, str],
                                                                               tp.Tuple[bool, None]]:
    """
    Test for sidelobe contamination (True fails).

    Returns a boolean array or a False statement if the test cannot be carried out.

    Downward equation:
        bin_depth + 0.5*bin_size > XducerDepth + (bottom_depth - XducerDepth)*cos(beam_angle)
    Upward equation:
        bin_depth - 0.5*bin_size < XducerDepth * ( 1 - cos(beam_angle))

    Parameters
    ----------
    dataset :
    bottom_depth : optional
        Fixed bottom depth to use for sidelobe correction
    Returns
    -------
    sidelobe_flags : Boolean Array
    msg :
    """
    msg = ""
    if dataset.attrs["beam_angle"] and dataset.attrs["orientation"]:
        angle_cos = np.cos(np.radians(dataset.attrs["beam_angle"]))
        depth_array = np.tile(dataset.depth.data, dataset.time.shape + (1,))
        if "xducer_depth" in dataset:
            xducer_depth = dataset["xducer_depth"].data
            msg += "xducer_depth: time dependent"
        elif "xducer_depth" in dataset.attrs:
            xducer_depth = np.tile(dataset.attrs["xducer_depth"], dataset.time.shape)
            msg += f"xducer_depth: constant {xducer_depth[0]}"
        else:
            l.warning(
                "Sidelobes correction aborted. Adcp depth `xducer_depth` not found and one was not provided."
            )
            return False, None

        if dataset.attrs["orientation"] == "down":
            if "bt_depth" in dataset:
                sounding = dataset.bt_depth.data
                msg += ", sounding: bottom range"
            elif bottom_depth is not None:
                sounding = bottom_depth
                msg += f", sounding: constant {sounding}"
            else:
                l.warning(
                    "Sidelobes correction aborted. Bottom depth not found and one was not provided."
                )
                return False, None

            max_depth = xducer_depth + (sounding - xducer_depth) * angle_cos
            return depth_array.T + dataset.attrs["bin_size_m"] / 2 > max_depth, msg

        elif dataset.attrs["orientation"] == "up":
            min_depth = xducer_depth * (1 - angle_cos)
            return depth_array.T - dataset.attrs["bin_size_m"] / 2 < min_depth.T, msg

        else:
            l.warning(
                "Can not correct for sidelobes, `adcp_orientation` parameter not set. Must be `up` or `down`."
            )
            return False, None
    else:
        l.warning("Can not correct for sidelobes, beam_angle not found in raw file.")
        return False, None


def temperature_test(dataset: xr.Dataset) -> np.ndarray:
    """"""
    return values_outliers_detection(
        dataset.temperature.data,
        lower_limit=GLOBAL_IMPOSSIBLE_PARAMETERS['temperature']['min'],
        upper_limit=GLOBAL_IMPOSSIBLE_PARAMETERS['temperature']['max']
    )


def pressure_test(dataset: xr.Dataset) -> np.ndarray:
    """FIXME"""
    return values_outliers_detection(
        dataset.pres.data,
        lower_limit=GLOBAL_IMPOSSIBLE_PARAMETERS['pres']['min'],
        upper_limit=GLOBAL_IMPOSSIBLE_PARAMETERS['pres']['max']
        )

