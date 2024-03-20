import os
from pathlib import Path
import numpy as np
import xarray as xr
import pytest
import pandas as pd

from magtogoek.utils import json2dict
from magtogoek.process_configurations import load_configfile, cli_options_to_config
from magtogoek.adcp.process import process_adcp

TIMESTAMP = pd.Timestamp.now().strftime("%Y-%m-%d")

CONFIG_FILENAME = "files/process_test/adcp_iml4_2017.ini"
PROCESS_OUTPUT_FILES = [
    "files/process_test/iml4_2017_sw_raw.nc",
    "files/process_test/iml4_2017_sw.nc",
    "files/process_test/iml4_2017_sw.log"
]

PLATFORM_FILE = "files/process_test/iml_platforms.json"
RAW_ADCP_FILE = "data/raw_adcp_data/iml6_2017_wh.000"
QUICK_OUTPUT_FILES = ["data/raw_adcp_data/iml6_2017_wh.nc", "data/raw_adcp_data/iml6_2017_wh_raw.nc"]

SENSOR_METADATA = {
    'sensor_type': 'adcp',
    'sensor_depth': 1,
    'serial_number': "01400000000000000000000000000553",
    'sensor_depth_units': 'meters',
    "chief_scientist": "adcp chief scientist"
}


def test_process_adcp():
    """Files are deleted when `test_process_adcp_variables_sensor_metadata` is run"""
    configuration = load_configfile(CONFIG_FILENAME)

    process_adcp(configuration, drop_empty_attrs=False, headless=False)


def test_process_adcp_global_attributes():
    """Requires `test_process_adcp` to be run first"""
    dataset = xr.open_dataset("files/process_test/iml4_2017_sw.nc")

    test_global_attributes = json2dict('data/global_attributes/adcp_process_expected_global_attributes.json')
    test_global_attributes["date_created"] = TIMESTAMP
    test_global_attributes["date_modified"] = TIMESTAMP

    for key, value in test_global_attributes.items():
        if isinstance(dataset.attrs[key], (list, tuple, np.ndarray)):
            assert list(value) == list(dataset.attrs[key])
        else:
            assert value == dataset.attrs[key]
    dataset.close()


def test_process_adcp_variables_sensor_metadata():
    """Requires `test_process_adcp` to be run first"""
    dataset = xr.open_dataset("files/process_test/iml4_2017_sw.nc")

    for var in ['u', 'v', 'w', 'e', 'temperature']:
        temp_dict = {}
        for key, value in SENSOR_METADATA.items():
            temp_dict[key] = dataset[var].attrs[key]
        assert temp_dict == SENSOR_METADATA

    dataset.close()

    for fn in PROCESS_OUTPUT_FILES:
        os.remove(fn)


def test_quick_adcp():
    """Only testing for crash"""
    options = {"input_files": RAW_ADCP_FILE,
               "process": "adcp",
               "sonar": "wh",
               "platform_file": PLATFORM_FILE,
               "platform_id": "IML6_2017",
               "adcp_id": "ADCP_01",
               "no_fig": True,
               "bodc_name": True
               }
    configuration = cli_options_to_config('adcp', options, cwd=str(Path().cwd()))

    process_adcp(configuration, drop_empty_attrs=True, headless=False)

    for fn in QUICK_OUTPUT_FILES:
        os.remove(fn)




