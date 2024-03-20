import os
import platform
from pathlib import Path

from magtogoek.__version__ import VERSION
import magtogoek.logger as l
from magtogoek.utils import resolve_relative_path

from magtogoek.adcp import SENSOR_TYPES as ADCP_SENSOR_TYPES, GENERIC_PARAMETERS as ADCP_GENERIC_PARAMETERS
from magtogoek.wps import SENSOR_TYPES as WPS_SENSOR_TYPES
from magtogoek.metoce import SENSOR_TYPES as METOCE_SENSOR_TYPES, GENERIC_PARAMETERS as METOCE_GENERIC_PARAMETERS

l.set_level(0)

REPOSITORY_ADDRESS = "https://github.com/iml-gddaiss/magtogoek"

TERMINAL_WIDTH = 80

PROCESSES = ['adcp', 'metoce']

SENSOR_TYPES = ADCP_SENSOR_TYPES + WPS_SENSOR_TYPES + METOCE_SENSOR_TYPES

GENERIC_PARAMETERS = list(
    dict.fromkeys(ADCP_GENERIC_PARAMETERS + METOCE_GENERIC_PARAMETERS)
)


PLATFORM_TYPES = ["buoy", "mooring", "ship", "lowered"]
DEFAULT_PLATFORM_TYPE = "buoy"


### MAGTOGOEK CONFIGURATION FILES PATH ###
DEFAULT_CONFIGURATION_PATH = resolve_relative_path("files/", __file__)

if platform.system() == 'Windows':
    LOCAL_CONFIGURATION_PATH = Path(os.getenv('LOCALAPPDATA') + '/magtogoek/')
else:
    LOCAL_CONFIGURATION_PATH = Path(os.getenv('HOME') + '/magtogoek/')

LOCAL_CONFIG_EXISTS = False
if Path(LOCAL_CONFIGURATION_PATH).is_dir():
    LOCAL_CONFIG_EXISTS = True
    if set(os.listdir(DEFAULT_CONFIGURATION_PATH)) - set(os.listdir(LOCAL_CONFIGURATION_PATH)) == set():
        CONFIGURATION_PATH = LOCAL_CONFIGURATION_PATH
    else:
        print('\n\t!!! Warning. Local magtogoek configuration is missing some files. Reverting to default configurations. !!!\n')
        CONFIGURATION_PATH = DEFAULT_CONFIGURATION_PATH
else:
    CONFIGURATION_PATH = DEFAULT_CONFIGURATION_PATH
