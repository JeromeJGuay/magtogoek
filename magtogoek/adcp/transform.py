"""Module that contains transformation function for adcp data.

"""

from typing import *
import numpy as np
import xarray as xr
from pycurrents.adcp import transform

import magtogoek.logger as l


def coordsystem2earth(dataset: xr.Dataset) -> xr.Dataset:
    """Transforms beam or xyz coordinates to enu coordinates

    Replace velocities variables in the dataset.

    #FIXME NEEDS SOME MORE TESTING

    Parameters
    ----------
    dataset :
        Required Variables:
            Velocities: ('v1','v2','v3','v4') or ('u', 'v', 'w', 'e').
            'heading'
            'pitch'
            'roll_'
        Required Attributes:
            'beam_angle': int
            'beam_pattern': 'convex' or 'concave'
            'orientation': 'up' or 'down'
    Returns
    -------
    dataset with either:
        beam velocities ('v1','v2','v3','v4') replaced by xyz velocities ('u', 'v', 'w', 'e')
        or
        xyz velocities ('u', 'v', 'w', 'e') replaced by enu velocities ('u', 'v', 'w', 'e').

    Notes
    -----
    UHDAS transform functions are used to transform for beam coordinates and xyz to east-north-up (enu).
    These function can use a three-beam solution by faking a fourth beam.

    beam coordinates : Velocity measured along beam axis.
    xyz coordinates : Velocity in a cartesian coordinate system in the ADCP frame of reference.
    enu coordinates : East North Up measured using the heading, pitch, roll of the ADCP.
    """

    if dataset.attrs['coord_system'] == "beam" and dataset.attrs['beam_angle'] is not None:
        dataset = beam2xyze(dataset)
        dataset = percent_good_beam2xyz(dataset=dataset)

    if dataset.attrs['coord_system'] == 'xyz':
        if 'heading' in dataset and 'roll_' in dataset and 'pitch' in dataset:
            if any([
                (dataset['heading'].values == 0).all(),
                (dataset['roll_'].values == 0).all(),
                (dataset['pitch'].values == 0).all()
            ]):
                l.warning(
                    "One or more of Pitch, Roll and Heading values are all 0.")
            xyz2enu(dataset)
        else:
            l.warning(
                "One or more of Pitch, Roll and Heading data are missing.")

    return dataset


def beam2xyze(dataset: xr.Dataset) -> xr.Dataset:
    """Transform xyze velocities from beam velocities.

    Parameters
    ----------
    dataset :
        Required Variables
            Beam Velocities: ('v1', 'v2', 'v3','v4')
        Required Coordinates
            ["depth", "time"]
        Required Attributes:
            `beam_angle`: int
            `beam_pattern`: `convex` or `concave`
    Returns
    -------
    dataset with beam velocities ('v1','v2','v3','v4') replaced by xyz ('u', 'v', 'w', 'e').
    """
    trans = transform.Transform(angle=dataset.attrs['beam_angle'], geometry=dataset.attrs['beam_pattern'])

    beam_velocities = ('v1', 'v2', 'v3', 'v4')
    xyze_velocities = ('u', 'v', 'w', 'e')

    trans_vel = trans.beam_to_xyz(np.stack([dataset[v].T for v in beam_velocities], axis=2))
    for i, v in enumerate(xyze_velocities):
        dataset[v] = (["depth", "time"], np.round(trans_vel[:, :, i].T, decimals=3))
    l.log('Water velocities transformed from beam to xyz coordinates.')
    dataset = dataset.drop_vars(beam_velocities)

    bt_beam_velocities = ('bt_v1', 'bt_v2', 'bt_v3', 'bt_v4')
    bt_xyze_velocities = ('bt_u', 'bt_v', 'bt_w', 'bt_e')

    if all(v in dataset for v in bt_beam_velocities):
        trans_vel = trans.beam_to_xyz(np.stack([dataset[v].T for v in bt_beam_velocities], axis=1))
        for i, v in enumerate(bt_xyze_velocities):
            dataset[v] = (["time"], np.round(trans_vel[:, i].T, decimals=3))
        l.log('Bottom velocities transformed from beam to xyz coordinates.')
        dataset = dataset.drop_vars(bt_beam_velocities)

    dataset.attrs['coord_system'] = "xyz"

    return dataset


def percent_good_beam2xyz(dataset: xr.Dataset) -> xr.Dataset:
    """Compute the Percent Good as the average of each beam Percent Good"""
    _beam_pg_good = [f'pg{i + 1}' for i in range(4)]
    _pg_good = np.mean([dataset[v].values for v in _beam_pg_good], axis=0)
    dataset['pg'] = (["depth", "time"], np.round(_pg_good, decimals=0))
    l.warning("Percent Good was computed as the averaged of the Beams Percent Good.")
    dataset = dataset.drop_vars(_beam_pg_good)
    return dataset


def xyz2beam(dataset: xr.Dataset) -> xr.Dataset:
    """Transform beam velocities from xyz velocities.

    Parameters
    ----------
    dataset :
        Required Variables
            Beam Velocities: ('u', 'v', 'w', 'e')
        Required Coordinates
            ["depth", "time"]
        Required Attributes:
            `beam_angle`: int
            `beam_pattern`: `convex` or `concave`
    Returns
    -------
    dataset with xyz ('u', 'v', 'w', 'e') replaced by beam velocities ('v1','v2','v3','v4').
    """
    trans = transform.Transform(angle=dataset.attrs['beam_angle'], geometry=dataset.attrs['beam_pattern'])

    xyze_velocities = ('u', 'v', 'w', 'e')
    beam_velocities = ('v1', 'v2', 'v3', 'v4')

    trans_vel = trans.xyz_to_beam(np.stack([dataset[v].T for v in xyze_velocities], axis=2))
    for i, v in enumerate(beam_velocities):
        dataset[v] = (["depth", "time"], np.round(trans_vel[:, :, i].T, decimals=3))

    l.log('Water velocities transformed from xyz to beam coordinates.')
    dataset = dataset.drop_vars(xyze_velocities)

    bt_xyze_velocities = ('bt_u', 'bt_v', 'bt_w', 'bt_e')
    bt_beam_velocities = ('bt_v1', 'bt_v2', 'bt_v3', 'bt_v4')

    if all(v in dataset for v in bt_xyze_velocities):
        trans_vel = trans.xyz_to_beam(np.stack([dataset[v].T for v in bt_xyze_velocities], axis=1))
        for i, v in enumerate(bt_beam_velocities):
            dataset[v] = (["time"], np.round(trans_vel[:, i].T, decimals=3))

        l.log('Bottom velocities transformed from xyz to beam coordinates.')
        dataset = dataset.drop_vars(bt_xyze_velocities)

    dataset.attrs['coord_system'] = "beam"

    return dataset


def xyz2enu(dataset: xr.Dataset):
    """Transform velocities from xyz velocities to enu.

    Parameters
    ----------
    dataset :
        Required Variables:
            'u', 'v', 'w', 'e'
            'heading'
            'pitch'
            'roll_'
        Required Attributes:
            `orientation`: 'up' or 'down
    """
    velocities = ('u', 'v', 'w', 'e')
    bt_velocities = ('bt_u', 'bt_v', 'bt_w', 'bt_e')

    enu = transform.rdi_xyz_enu(
        np.stack([dataset[v].T for v in velocities], axis=2),
        dataset['heading'], dataset['pitch'], dataset['roll_'],
        orientation=dataset.attrs['orientation'],
    )
    for i, v in enumerate(velocities):
        dataset[v].values = np.round(enu[:, :, i].T, decimals=3)

    l.log('Water velocities transformed from xyze to earth coordinates.')
    if all(v in dataset for v in bt_velocities):
        bt_enu = transform.rdi_xyz_enu(
            np.stack([dataset[v].T for v in bt_velocities], axis=1),
            dataset['heading'], dataset['pitch'], dataset['roll_'],
            orientation=dataset.attrs['orientation'],
        )
        for i, v in enumerate(bt_velocities):
            dataset[v].values = np.round(bt_enu[:, i].T, decimals=3)
        l.log('Bottom velocities transformed from xyze to earth coordinates.')

    dataset.attrs['coord_system'] = "earth"

