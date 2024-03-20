"""
"""

from pathlib import Path
from typing import List, Union, Dict, Tuple


import xarray as xr
import matplotlib.pyplot as plt

from magtogoek.tools import get_flagged_data
from magtogoek.metoce import FIGURES_VARIABLES

FONT = {"family": "serif", "color": "darkred", "weight": "normal", "size": 12}
BINARY_CMAP = plt.get_cmap("viridis_r", 2)

plt.style.use("seaborn-dark-palette")

def _map_gen_to_bodc(varnames: Union[List[str], Tuple[str, ...]], varname_map: Dict) -> List[str]:
    return [varname_map[varname] for varname in varnames if (varname in varname_map)]


def make_metoce_figure(
        dataset: xr.Dataset,
        variables_groupes: List[str] = None,
        single: bool = False,
        save_path: str = None,
        show_fig: bool = True,
        dataset_raw: xr.Dataset = None,
):
    """

    Looks for 'ancillary_variables' attributes on variables for QC flagging.

    Parameters
    ----------
    dataset: Dataset containing the processed data.
    variables_groupes:
        Which of the plot to make. One of:
        ['gsp_position', 'gps_motion', 'compass', 'velocity', 'wind',
         'meteo', 'wave', 'ctdo', 'ph', 'par', 'eco', 'pco2']
    single:
        If True, figures are plotted one at a time.
    save_path:
        Write figures to file.
    show_fig:
         Show figure if True.
    dataset_raw:
        Dataset containing the raw data. Use to plot process data against raw.

    Returns
    -------

    """
    figures = {}

    var_name_map = {}
    for var in dataset:
        if 'generic_name' in dataset[var].attrs:
            var_name_map[dataset[var].attrs['generic_name']] = var

    for group, variables in FIGURES_VARIABLES.items():
        if variables_groupes is not None and group not in variables_groupes:
            continue
        _variables = _map_gen_to_bodc(variables, var_name_map)
        if any(x in dataset.variables for x in _variables):
            figures[group] = plot_sensor_data(dataset, _variables, dataset_raw, fig_name=group)

    if single is True and show_fig is True:
        for count, fig in enumerate(figures.values()):
            fig.show()
            input(f"({count + 1}/{len(figures.keys())}) Press [enter] to plot the next figure.\033[1A \033[9C")

    if save_path is not None:
        stem = ''
        if Path(save_path).is_dir():
            path = Path(save_path)
        else:
            path = Path(save_path).parent
            stem = str(Path(save_path).stem) + '_'

        print(f'Figure saved at: {path}/')
        for name, fig in figures.items():
            fig.savefig(path.joinpath(stem + f'{name}.png'))

    if show_fig is True:
        plt.ion()
        plt.show(block=False)
        input("Press Enter to continue ...")
        plt.close('all')

    else:
        plt.close('all')


def plot_sensor_data(dataset: xr.Dataset, varnames: List[str], dataset_raw: xr.Dataset = None, fig_name: str = None):
    varnames = [var for var in varnames if var in dataset.variables]
    # noinspection PyTypeChecker
    fig, axes = plt.subplots(figsize=(12, 8), nrows=len(varnames), ncols=1, sharex=True, squeeze=False, num=fig_name)
    axes = axes.flatten()
    for var, ax in zip(varnames, axes):
        da = dataset[var]
        gen_var = dataset[var].attrs['generic_name']
        if dataset_raw is not None and gen_var in dataset_raw:
            ax.plot(dataset_raw.time, dataset_raw[gen_var], linestyle="--", marker='.', color='cyan')
        if 'ancillary_variables' in dataset[var].attrs:
            if dataset[var].attrs['ancillary_variables'] in dataset:
                ax.plot(da.time, get_flagged_data(dataset=dataset, var=var, flag_value=0), marker='.', color='darkblue')
                ax.plot(da.time, get_flagged_data(dataset=dataset, var=var, flag_value=1), marker='.', color='darkgreen')
                ax.plot(da.time, get_flagged_data(dataset=dataset, var=var, flag_value=2), marker='.', color='gold')
                ax.plot(da.time, get_flagged_data(dataset=dataset, var=var, flag_value=3), marker='X', color='orange')
                ax.plot(da.time, get_flagged_data(dataset=dataset, var=var, flag_value=4), marker='X', color='red')
        else:
            ax.plot(da.time, da, marker='.', color='darkblue')
        ax.set_ylabel(f"{var}\n[{dataset[var].units}]", fontdict=FONT)
        ax.tick_params(labelbottom=False)
    axes[-1].tick_params(labelbottom=True)
    axes[-1].set_xlabel("time", fontdict=FONT)
    if dataset_raw is not None:
        axes[0].plot([], [], linestyle="--", marker='.', color='cyan', label="raw")
    axes[0].plot([],[], marker='.', color='darkblue', label='No Quality Control')
    axes[0].plot([], [], marker='.', color='darkgreen', label='Good')
    axes[0].plot([], [], marker='.', color='gold', label='Probably good')
    axes[0].plot([], [], marker='X', color='orange', label='Probably bad')
    axes[0].plot([], [], marker='X', color='red', label='Bad')
    axes[0].legend()

    return fig
