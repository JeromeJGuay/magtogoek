# Magtogoek
*Name origin: Magtogoek is Algonquin for the Saint-Lawrence River and means "the path that walks".*
## Description
Magtogoek is a Linux python package and command line application (CLI) for processing ocean data. 
At the moment, only Acoustic Doppler Current Profiler (ADCP) data can be processed. 
This package is developed by the Scientific Advice, Information and Support Branch at the Fisheries and Ocean Canada Maurice-Lamontagne Institute.

Supported data type:

* ADCP : Acoustic Doppler Current Profiler
  - RDI Teledyne: WorkHorse, Sentinel V, OceanSurveyor 
    Magtogoek uses the Pycurrents package made by the UH Currents Group of the University of Hawaii.
    Since Pycurrents is only available on unix systems, a Linux/macOS virtual machine is needed on Windows machines to use this package.
    Pycurrents is automatically installed during the Magtogoek installation.
    Visit [pycurrents website](https://currents.soest.hawaii.edu/ocn_data_analysis/installation.html) for more details.
  - RTI (Rowe Technology Inc.) : 
    Magtogoek has a custom reader for RTI ENS files made using functions provided by RTI on
    their [repository](https://github.com/rowetechinc/RTI).
* More to come.

## Installation
### Installing `Anaconda3`.
If you don't have anaconda or if you are not using a python env install Anaconda3.
Go to the [anaconda page](https://repo.anaconda.com/archive/Anaconda3-2021.05-Linux-x86_64.sh) and download the latest version for Linux.
To install it run:
```shell
    $ ~/cd Download
    $ bash Anaconda3-2021.05-Linux-x86_64.sh
```
Note that the file name will change depending on the version.
Once Anaconda is installed, the terminal command line should look something like:
```shell
    (base):$ 
```   
This means that the installation worked, and you are in the `base` anaconda environment.
If `base` does not show up try this:
```shell
    $ cd 
    $ source anaconda3/bin/activate
```
Next, create an Anaconda environment where you can use magtogoek without any dependency or version issues.
To do so run:
```shell
    $ conda create -n mtgk python=3.8 numpy 
    $ conda activate mtgk 
```
Now the terminal command line should look like:
```shell
    (mtgk):$ 
```
From here, any installation must be done within the `mtgk` environment.
Use the command `conda active [env-name]` to change between anaconda environment.
### Installing `mercurial` and `git`.
Both `mercurial` and `git` must be installed to install `Magtogoek`. 

### Install via `pip`
First make sure you are in the desired python environment.
```shell
pip install git+https://github.com/JeromeJGuay/magtogoek
```
To update the package, run
```shell
pip install -U git+https://github.com/JeromeJGuay/magtogoek
```
### Install via `git clone`
First make sure you are in the desired python environment.
Clone the repository from the [github repository](https://github.com/JeromeJGuay/magtogoek) and install it with `pip install`. 
```shell
    $ git clone https://github.com/JeromeJGuay/magtogoek
    $ pip install -e magtogoek
```
The `-e` option will not copy the project to the pip package directory. 
Instead, python will import the package from the `git` folder.
Running the `git pull` command within the project folder will update the
package from the GitHub main branch to the latest version.
<!---
### Requirements
Magtogoek uses the external python package pycurrents made by UH Currents Group at the University of Hawaii to process Teledyne ADCP data. 
Pycurrents is only available on unix systems.
Pycurrents can be cloned from their [mercurial repository](https://currents.soest.hawaii.edu/hgstage/pycurrents) and installed with `pip install`.
```shell
    $ hg clone https://currents.soest.hawaii.edu/hgstage/pycurrents
    $ pip install pycurrents
```
-->
## Quick start

# New init feature for local setup and metadata files. TODO

From the terminal, within the same python environment it was installed in, type `mtgk` to run the CLI application. 
Using the command -h/--help and --info will give you information on the different commands.

Magtogoek's main purpose is to process raw instrument data and export them in the netCDF format following the CF metadata conventions. 
Magtogoek can also read, modify and export to Ocean data format (ODF).
ODF is a text format used by Fisheries an Oceans, Canada.

### Processing data
Data can be processed in two ways: Using the `quick` command or the `process` command. 
Both commands will produce a `.log` text files of the processing history.
The `quick` commands allows processing of instrument data directly from the command line where the default processing parameters/values can be modified using optionnal arguments.
```Shell
    $ mtgk quick [adcp,] [input_files] [OPTIONS]
```
The `process` commands allows the users to add more metadata to the output
netCDF files using configuration files with the `.ini` extension.
```Shell
    $ mtgk config [adcp,] [config_name] [OPTIONS]
```
Configuration files are made with the `config` command followed by a
specific sensors name. 
Optional arguments can also be used with the `config` command to preset some values in the configuration file.
Once filled out, configuration files have to be passed to the `process` command:
```Shell
    $ mtgk process [config_file]
```
### Configuration guide
A guide for the configurations file entries is available [here](docs/config_user_guide.md)

### Metadata storage: platform files
Magtogoek uses `json` files to store sensor (instruments) and platform metadata which are referred to as `platform_files`.
A platform can be anything that is equiped with oceanographic instruments/sensors, e.g., ships, moorings, buoys, drifters, rosettes, etc.
Platforms are json objects containing a json object for each sensor. 
The `PLATFORM_ID` for the platform should include the year or the version of the platform and a new platform should be added if modifications are made to a sensor or to the platform.
When processing data, a `platform_file`, `platform_id` and `sensor_id` have to be provided to add platform and sensor metadata.
A platform file is made with the `config platform` command:
```Shell
    $ mtgk config platform FILENAME 
```
Platform files are structured as follows:

```json
{
    "__PLATFORM_ID__": {
        "platform_name": null,
        "platform_type": null,
        "platform_model": null,
        "sounding": null,
        "longitude": null,
        "latitude": null,
        "description": null,
        "buoy_specs": {
            "type": null,
            "model": null,
            "height": null,
            "diameter": null,
            "weight": null,
            "description": null
            },
        "sensors": {
            "__SENSOR_ID__": {
                "sensor_type": null,
                "sensor_depth": null,
                "serial_number": null,
                "manufacturer": null,
                "model": null,
                "firmware_version": null,
                "chief_scientist": null,
                "description": null,
                "comments": null
            }
        }
    }
}
```
In future versions of Magtogoek, a single platform file could be used to store all the sensors' metadata. 
That way, only the platform\_id and sensor\_id would be required to add sensors and platform metadata. 
The `"platform_specs"` object is used by the ODF exporter to write the `BUOY_HEADER` metadata.
To add platforms or sensors, copy and paste sections with all the keys.
### Examples
Examples of platform and configuration files are available in the `test` section of the Magtogoek project. 
Data are also included to test the `quick` and `process` command.
Supposing you are in the test/files directory of the project, the `iml4_2017_sw_01.ENS` and `iml4_2017_sw_02.ENS` RTI files can be processed using the `adcp_iml4_2017.ini` config file and the `process` command:
```shell
../magtogoek/test/files$ mtgk process adcp_iml4_2017.ini
```
or with the `quick` command:
```shell
../magtogoek/test/files$ mtgk quick adcp iml4_2017_sw_0*.ENS -s sw -y 2017 -n iml4_2017_sw_quick
```

### Notes

#### Bodc parameter codes
Parameter codes for adcp bottom velocity up and bottom velocity error (bt_w, bt_e) do not yet exist in the BODC vocabulary. 
Those use were made up but following the BODC semantic bt_w: LRZABT01 and bt_e: LERRBT01".


### Other commands

Magtogoek has additional functionalities under the `check` and `compute` commands.
To come: the `odf2nc` command transforms ODF files to netcdf.
You can get info and help on these commands using the --info or -h options.

## More tools
Information on the usage of the following functions and objects is accessible with the `help()` function.
#### Navigation 
```python
from magtogoek.navigation import load_navigation
from magtogoek.navigation import compute_navigation
```
#### ODF file format
```python
from magtogoek.odf_format import Odf
```
## Acknowledgement
A special thank goes to UH Currents Group for their work on Pycurrents.

