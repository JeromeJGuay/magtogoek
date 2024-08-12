## INCOMPLETE

# Magtogoek
*Name origin: Magtogoek is Algonquin for the Saint-Lawrence River and means "the path that walks".*

## Installation

TODO:

Install within a directory, of your choosing, with 
```shell
python3.10 -m venv .venv
```
[//]: # (### Installing `Anaconda3`.)

[//]: # (If you don't have anaconda or if you are not using a python env install Anaconda3.)

[//]: # (Go to the [anaconda page]&#40;https://repo.anaconda.com/archive/Anaconda3-2021.05-Linux-x86_64.sh&#41; and download the latest version for Linux.)

[//]: # (To install it run:)

[//]: # (```shell)

[//]: # (    $ ~/cd Download)

[//]: # (    $ bash Anaconda3-2021.05-Linux-x86_64.sh)

[//]: # (```)

[//]: # (Note that the file name will change depending on the version.)

[//]: # (Once Anaconda is installed, the terminal command line should look something like:)

[//]: # (```shell)

[//]: # (    &#40;base&#41;:$ )

[//]: # (```   )

[//]: # (This means that the installation worked, and you are in the `base` anaconda environment.)

[//]: # (If `base` does not show up try this:)

[//]: # (```shell)

[//]: # (    $ cd )

[//]: # (    $ source anaconda3/bin/activate)

[//]: # (```)

[//]: # (Next, create an Anaconda environment where you can use magtogoek without any dependency or version issues.)

[//]: # (To do so run:)

[//]: # (```shell)

[//]: # (    $ conda create -n mtgk python=3.8 numpy )

[//]: # (    $ conda activate mtgk )

[//]: # (```)

[//]: # (Now the terminal command line should look like:)

[//]: # (```shell)

[//]: # (    &#40;mtgk&#41;:$ )
[//]: # (```)

From here, any installation must be done within the `mtgk` environment.
Use the command `conda active [env-name]` to change between anaconda environment.
### Installing `mercurial` and `git`.
Both `mercurial` and `git` must be installed to install `Magtogoek`. 

[//]: # (### Install via `pip`)

[//]: # (First make sure you are in the desired python environment.)

[//]: # (```shell)

[//]: # (pip install git+https://github.com/iml-gddaiss/magtogoek@develop_3.10)

[//]: # (```)

[//]: # (To update the package, run)

[//]: # (```shell)

[//]: # (pip install -U git+https://github.com/iml-gddaiss/magtogoek@develop_3.10)

[//]: # (```)
### Install via `git clone`
First make sure you are in the desired python environment.
Clone the repository from the [github repository](https://github.com/JeromeJGuay/magtogoek) and install it with `pip install`. 
```shell
    $ git clone -b develop_3.10 https://github.com/iml-gddaiss/magtogoek
    $ pip install -e magtogoek
```
The `-e` option will not copy the project to the pip package directory. 
Instead, python will import the package from the `git` folder.
Running the `git pull` command within the project folder will update the
package from the GitHub main branch to the latest version.

### Requirements
Magtogoek uses the external python package pycurrents made by UH Currents Group at the University of Hawaii to process Teledyne ADCP data. 
Pycurrents is only available on unix systems.
Pycurrents can be cloned from their [mercurial repository](https://currents.soest.hawaii.edu/hgstage/pycurrents) and installed with `pip install`.
```shell
    $ hg clone https://currents.soest.hawaii.edu/hgstage/pycurrents
    $ pip install pycurrents
```


### Configuration file guide
A guide for the configurations file entries is available [here](docs/config_user_guide.md)

### Metadata storage: platform files
Magtogoek uses `json` files to store sensor (instruments) and platform metadata which are referred to as `platform_files`.
When processing data, a `platform_file`, `platform_id` and `sensor_id` have to be provided to add platform and sensor metadata.
A platform file is made with the `config platform` command:
```Shell
    $ mtgk config platform FILENAME 
```
Platform files are structured as follows:
```json
{
    "__enter_a_platform_id_here__": {
        "platform_type": "buoy",
        "platform_name": null,
        "platform_model": null,
        "sounding": null,
        "longitude": null,
        "latitude": null,
        "description": null,
        "chief_scientist": null,
        "buoy_specs": {
            "type": null,
            "model": null,
            "height": null,
            "diameter": null,
            "weight": null,
            "description": null
        },
        "instruments": {
            "__enter_an_instrument_ID_here__": {
                "sensor_type": null,
                "sensor_height": null,
                "sensor_depth": null,
                "serial_number": null,
                "manufacturer": null,
                "model": null,
                "firmware_version": null,
                "chief_scientist": null,
                "description": null,
                "comments": null,
                "sensors": {
                    "__sensor_name__": {
                        "name": null,
                        "code": null,
                        "description": null,
                        "comments": null,
                        "calibration": {
                            "date": null,
                            "number_of_coefficients": null,
                            "coefficients": null,
                            "calibration_equation": null,
                            "calibration_units": null,
                            "archiving_units": null,
                            "conversion_factor": null,
                            "comments": null
                        }
                    }
                }
            }
        }
    }
}
```

