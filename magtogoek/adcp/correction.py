import numpy as np
import xarray as xr

from magtogoek import logger as l
from magtogoek.process_common import add_correction_attributes_to_dataarray
from magtogoek.sci_tools import xy_vector_magnetic_correction, rotate_heading


def apply_motion_correction(dataset: xr.Dataset, mode: str):
    """Carry motion correction on velocities.

    If mode is 'bt' the motion correction is along x, y, z.
    If mode is 'nav' the motion correction is along x, y.
    """
    if mode == "bt":
        _msg = "Motion correction carried was out with bottom track data"
        if all(f"bt_{v}" in dataset for v in ["u", "v", "w"]):
            for field in ["u", "v", "w"]:
                dataset[field].values -= dataset[f"bt_{field}"].values
                add_correction_attributes_to_dataarray(dataset[field])
                dataset[field].attrs['corrections'] += _msg + '\n'
        else:
            l.warning("Motion correction aborted. Bottom velocity (bt_u, bt_v, bt_w) missing")
            return

    elif mode == "nav":
        _msg = "Motion correction was carried out with navigation data. Data rounded to mm precision (3 decimal places)."
        if all(f"{v}_ship" in dataset for v in ["u", "v"]):
            for field in ["u", "v"]:
                velocity_correction = dataset[field + "_ship"]

                if 'depth' in dataset[field].coords:
                    velocity_correction = np.tile(velocity_correction, (dataset.depth.size, 1))

                dataset[field] += np.round(velocity_correction, 3) # rounding to millimeter. (ADCP precision)
                add_correction_attributes_to_dataarray(dataset[field])
                dataset[field].attrs['corrections'] += _msg + '\n'


        else:
            l.warning("Motion correction aborted. Navigation velocity (u_ship, v_ship) missing")
            return
    else:
        l.warning("Motion correction aborted. Motion correction mode invalid. ('bt' or 'nav')")
        return

    l.log(_msg)


def apply_magnetic_correction(dataset: xr.Dataset, magnetic_declination: float):
    """Correct velocities and heading to true north and east if required.

    If the `magnetic_declination` parameter values differs from the one in the
    dataset global attribute, an additional correction is applied.

    Rotates velocities vector clockwise by `magnetic_declination` angle effectively
    rotating the frame fo reference by the `magnetic_declination` anti-clockwise.

    Corrects the heading with the `magnetic_declination`:

    Equation for the heading: (heading + 180 + magnetic_declination) % 360 - 180
        [-180, 180[ -> [0, 360[ -> [MD, 360+MD[
        -> [MD, 360+MD[ -> [0, 360[ -> [-180, 180[

    Dataset variables needed:
        `u`, `v` (optional: `bt_u`, `bt_v`), `heading`.


    Parameters
    ----------
    dataset :

    magnetic_declination:
        Absolute magnetic declination

    """

    magnetic_correction = _compute_relative_magnetic_declination(dataset, magnetic_declination)

    if dataset.attrs['coord_system'] == 'earth':
        dataset.u.values, dataset.v.values = xy_vector_magnetic_correction(dataset.u, dataset.v, magnetic_correction)
        l.log(f"Velocities transformed to true north and true east.")
        for v in ["u", "v"]:
            add_correction_attributes_to_dataarray(dataset[v])
            dataset[v].attrs['corrections'] += "Velocities transformed to true north and true east.\n"

        if all(v in dataset for v in ["bt_u", "bt_v"]):
            dataset.bt_u.values, dataset.bt_v.values = xy_vector_magnetic_correction(
                dataset.bt_u, dataset.bt_v, magnetic_correction
            )
            l.log(f"Bottom velocities transformed to true north and true east.")
            for v in ["bt_u", "bt_v"]:
                add_correction_attributes_to_dataarray(dataset[v])
                dataset[v].attrs['corrections'] += "Bottom velocities transformed to true north and true east.\n"
    else:
        l.warning('Velocities correction for magnetic declination was not carried out since '
                  'they are not in earth coordinates.')

    # heading goes from -180 to 180
    if "heading" in dataset:
        dataset.heading.values = rotate_heading(dataset.heading.data, magnetic_correction)
        l.log(f"Heading transformed to true north.")
        add_correction_attributes_to_dataarray(dataset['heading'])
        dataset['heading'].attrs['corrections'] += "Heading transformed to true north.\n"

    dataset.attrs["magnetic_declination"] = magnetic_declination

    l.log(f"Absolute magnetic declination: {dataset.attrs['magnetic_declination']} degree north.")


def _compute_relative_magnetic_declination(dataset: xr.Dataset, magnetic_declination: float):
    """Return the difference between the absolute magnetic declination and
    the correction already applied on the data.

    The correction already applied needs to be stored as a global attribute of the dataset.
        dataset.attrs['magnetic_declination'] = ...

    Parameters
    ----------
    dataset :
        Requires global attribute : "magnetic_declination"
    magnetic_declination:
        Absolute magnetic declination

    """
    if dataset.attrs["magnetic_declination"] and dataset.attrs["magnetic_declination"] != "NA":
        angle = round((magnetic_declination - dataset.attrs["magnetic_declination"]), 4)
        l.log(f"An additional correction of {angle} degree north was applied.")
        return angle
    return magnetic_declination


