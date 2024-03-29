"""
Tools that allow for manually flagging data with a manual plot.
Made to be used from the app.py.

Interactive Plot Commands
-------------------------
    Data Colors
    -----------
     Blue: Unselected
     Orange: Current selection
     Green: List of selected points.

    Commands
    --------
     <a>: Append the current selection to the list of selected points.
     <r>: Remove the current selection from the list of selected points.
     <[0-4]>: Append the current selection to the list of selected points and set the data flags of
              the selected points to [0-4].
     <enter>: Exit the interactive plot.

"""
import sys

import numpy as np
import xarray as xr

from datetime import datetime
import matplotlib.colors as mcolors
import matplotlib.widgets as mwidgets
import matplotlib.backend_bases as mevent
from pathlib import Path

import matplotlib.pyplot as plt



BLUE = mcolors.to_rgba('deepskyblue')
GREEN = mcolors.to_rgba('lime')
ORANGE = mcolors.to_rgba('orange')

def get_qc_colormap():
    cmap = mcolors.ListedColormap([
        'darkblue', 'darkgreen', 'gold', 'orange', 'red', 'k', 'k', 'k', 'k', 'k'
    ])
    norm = mcolors.BoundaryNorm(np.arange(0, 10), cmap.N)
    return cmap, norm

QC_CMAP, QC_NORM = get_qc_colormap()

class SelectFromCollection:
    def __init__(self, axe, collection):
        self.canvas = axe.figure.canvas
        self.collection = collection

        self.xys = collection.get_offsets()
        self.Npts = len(self.xys)

        # Ensure that we have separate colors for each object

        self.default_fc = list(BLUE)
        self.default_fc[-1] = self.collection.get_alpha()
        self.fc = np.tile(self.default_fc, (self.Npts, 1))
        self.collection.set_facecolors(self.fc)
        self.collection.set_edgecolor('k')
        self.collection.set_linewidth(.25)

        self.rect_selection = mwidgets.RectangleSelector(axe, onselect=self.onselect, useblit=True)

        self.selection_buffer = None

        self.selected_indices = set()

    def onselect(self, click_event, release_event): #MouseEvent

        # reset to selections colors
        self.fc[:, :] = self.default_fc
        self.fc[list(self.selected_indices), :-1] = GREEN[:-1]

        _ext = list(self.rect_selection.extents)
        xx, yy = np.array(self.collection.get_offsets()).T
        self.selection_buffer = np.where((xx >= _ext[0]) & (xx <= _ext[1]) & (yy >= _ext[2]) & (yy <= _ext[3]))[0]

        if click_event.button == mevent.MouseButton.RIGHT:
            self.selection_buffer = []

        self.fc[self.selection_buffer, :-1] = ORANGE[:-1]

        self.collection.set_facecolors(self.fc)
        self.canvas.draw_idle()

    def disconnect(self):
        self.rect_selection.disconnect_events()
        self.fc[:, :] = self.default_fc
        self.collection.set_facecolors(self.fc)
        self.canvas.draw_idle()


    def append(self): # 'a'
        if self.selection_buffer is not None:
            self.selected_indices = set(list(self.selected_indices) + list(self.selection_buffer))
            self.selection_buffer = []

            # set selection colors
            self.fc[:, :] = self.default_fc
            self.fc[list(self.selected_indices), :-1] = GREEN[:-1]

            self.collection.set_facecolors(self.fc)
            self.canvas.draw_idle()

    def remove(self): # 'r'
        self.selected_indices -= set(self.selection_buffer)
        self.selection_buffer = []

        self.fc[:, :] = self.default_fc
        self.fc[list(self.selected_indices), :-1] = GREEN[:-1]
        self.collection.set_facecolors(self.fc)
        self.canvas.draw_idle()

    def reset(self):
        self.selected_indices = set()
        self.selection_buffer = []

        self.fc[:,:] = self.default_fc
        self.collection.set_facecolors(self.fc)
        self.canvas.draw()

def zoom_control(axe, base_scale = 1.2, max_zoom_in = 10):

    max_left, max_right = axe.get_xlim()

    zoom_count = 0

    def zoom_func(event):
        nonlocal zoom_count
        # get the current x and y limits
        cur_xlim = axe.get_xlim()

        # get cursor location
        xdata = event.xdata  # get event x location

        if xdata is None:
            return None

        # set the range
        # Get distance from the cursor to the edge of the figure frame

        x_left = xdata - cur_xlim[0]
        x_right = cur_xlim[1] - xdata

        scale_factor = 1
        if event.button == 'up':
            # deal with zoom in
            if zoom_count < max_zoom_in:
                scale_factor = 1/base_scale
                zoom_count += 1
        elif event.button == 'down':
            # deal with zoom out
            if zoom_count > 0:
                scale_factor = base_scale
                zoom_count -= 1
            else:
                scale_factor = 10

        if scale_factor != 1:
            new_x_left = xdata - x_left * scale_factor
            new_x_right = xdata + x_right * scale_factor

            if new_x_left < max_left:
                new_x_left = max_left
            if new_x_right > max_right:
                new_x_right = max_right

            # set new limits
            axe.set_xlim([new_x_left, new_x_right])


            axe.figure.canvas.draw_idle() # force re-draw the next time the GUI refreshes

    fig = axe.get_figure() # get the figure of interest
    # attach the call back
    fig.canvas.mpl_connect('scroll_event',zoom_func)

class QcPlot:
    """
    Data Colors
    -----------
     Blue: Unselected
     Orange: Current selection
     Green: List of selected points.

    Commands
    --------
     <a>: Append the current selection to the list of selected points.
     <r>: Remove the current selection from the list of selected points.
     <[0-4]>: Append the current selection to the list of selected points and set the data flags of
              the selected points to [0-4].
     <delete>: Append the current selection to the list of selected points and set the data value of
              the selected points to `nan` and the corresponding data flags to 9.
     <enter>: Exit the interactive plot.

    """
    def __init__(self, dataset: xr.Dataset, variable: str, gen_name = True):
        self.dataset = dataset
        self.selected_variable = variable
        self.gen_name = gen_name

        self.selected_qc_variable = self.dataset[self.selected_variable].attrs["ancillary_variables"]

        self.fig, self.axes = None, None
        self.axes, self.ax0, self.ax1 = None, None, None

        self.pts_collection = None

        self.flag_button = None

        self.selected_indices: set = {}

    def run(self):
        self.fig, self.axes = plt.subplots(2, 1, sharex=True, squeeze=True, figsize=(12, 8))  # set fig size
        self.ax0, self.ax1 = self.axes

        self._plot_variable_ancillary_flag()
        self._plot_variable_data()

        self._selector_tool()
        zoom_control(self.ax0, base_scale=2)

        self._add_keymap_textbox()

        self.fig.tight_layout()

        plt.show()

    def _plot_variable_data(self):
        self.ax0.clear()

        self._plot_variable_ancillary_flag()

        self.pts_collection = self.ax0.scatter(self.dataset.time, self.dataset[self.selected_variable].values, zorder=1,
                                               edgecolors="k",
                                               alpha=.75)

        if self.gen_name is True:
            var_name = self.dataset[self.selected_variable].attrs['generic_name']
        else:
            var_name = self.selected_variable
        ylabel = f"{var_name} [{self.dataset[self.selected_variable].attrs['units']}]"
        self.ax0.set_ylabel(ylabel)

        self.ax0.scatter([], [], color='deepskyblue', edgecolors="k", linewidth=0.25, label='Unselected')
        self.ax0.scatter([], [], color='orange', edgecolors="k", linewidth=0.25, label='Selected')
        self.ax0.scatter([], [], color='lime', edgecolors="k", linewidth=0.25, label='In Buffer')
        self.ax0.legend()

        self.ax0.get_xlim()
        self.ax0.get_ylim()

    def _plot_variable_ancillary_flag(self):
        self.ax1.clear()

        self.ax1.set_ylim(-.9, 9,9)

        self.ax1.scatter(
            self.dataset.time, self.dataset[self.selected_qc_variable],
            c=self.dataset[self.selected_qc_variable], cmap=QC_CMAP, norm=QC_NORM
        )
        self.ax1.scatter([], [], color='darkblue', label='No Quality Control')
        self.ax1.scatter([], [], color='darkgreen', label='Good')
        self.ax1.scatter([], [], color='gold', label='Probably good')
        self.ax1.scatter([], [], color='orange', label='Probably bad')
        self.ax1.scatter([], [], color='red', label='Bad')

        self.ax1.set_xlabel("time")
        self.ax1.set_ylabel("qc flag")
        self.ax1.legend()

    def _flag_data(self, indices: list, flag_value: int):
        _date = datetime.now().strftime("%Y-%m-%d")
        self.dataset[self.selected_qc_variable][indices] = flag_value
        self.dataset[self.selected_qc_variable].attrs['quality_date'] = _date
        if "manual flagging" not in self.dataset[self.selected_qc_variable].attrs['quality_test']:
            self.dataset[self.selected_qc_variable].attrs['quality_test'] += "Manual flagging." + "\n"

        if f"{self.selected_variable} manual flagging" not in self.dataset.attrs["quality_comments"]:
            self.dataset.attrs["quality_comments"] += f"{self.selected_variable} manual flagging." + "\n"

        self.dataset['date_modified'] = _date

    def _selector_tool(self):
        selector = SelectFromCollection(self.ax0, self.pts_collection)

        def point_selection_event(event):
                _xlim = self.ax0.get_xlim()
                if event.key == "enter":
                    selector.disconnect()
                    plt.close()

                elif event.key == "a":
                    selector.append()

                elif event.key == "r":
                    selector.remove()

                for i in range(5):
                    if event.key == str(i):
                        selector.append()
                        self._flag_data(list(selector.selected_indices), i)
                        selector.reset()
                        self._plot_variable_ancillary_flag()
                        break

                self.ax0.set_xlim(_xlim)

        self.fig.canvas.mpl_connect("key_press_event", point_selection_event)

    def _add_keymap_textbox(self):
        # + Zoom with the scroll wheel.
        # + Select points with left drag-click.
        _text = (" [a/r]: append/remove points from buffer"
                 " [0-4]: Set flag values."
                 " [Enter]: Close and save.")

        #anchored_text = AnchoredText(_text, loc=2)
        #self.ax0.add_artist(anchored_text)
        self.ax0.set_title(_text)


def manuel_qc_plots(filename: str, variable: str, save_path=None) -> None:

    dataset = xr.load_dataset(filename)

    if variable not in dataset:
        # if the given variable is generic but the dataset in bodc
        gen_to_bodc_map = {} #{dataset[v].attrs['generic_name']: v for v in dataset.variables.keys()}
        for _v in dataset.variables.keys():
            if "generic_name" in dataset[_v].attrs:
                gen_to_bodc_map[dataset[_v].attrs['generic_name']] = _v

        bodc_to_gen_map = {}
        for _v in dataset.variables.keys():
            if 'snd_parameter_urn' in dataset[_v].attrs:
                bodc_to_gen_map[dataset[_v].attrs['snd_parameter_urn']] = _v

        if variable in gen_to_bodc_map:
            variable = gen_to_bodc_map[variable]
        elif variable in bodc_to_gen_map:
            variable = bodc_to_gen_map[variable]
        else:
            print(f"Error: `{variable}` not in dataset.")
            sys.exit()

    if 'ancillary_variables' in dataset[variable].attrs and dataset[variable].attrs['ancillary_variables'] in dataset:
        if all(dataset[dataset[variable].attrs['ancillary_variables']].values == 0):
            # check if variable is 1D
            dataset[dataset[variable].attrs['ancillary_variables']].values[:] = 1
        QcPlot(dataset=dataset, variable=variable).run()

    if save_path is None:
        _path=Path(filename)
        save_path = _path.with_name(f'{_path.stem}_manual_QC.nc')

    dataset.to_netcdf(save_path)
    print(f"Dataset saved -> `{save_path}`.")